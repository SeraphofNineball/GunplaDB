"""
Scraper for gunplacentral.com/kits

The site uses Next.js SSR. Kit detail pages expose data via __NEXT_DATA__
JSON embedded in the HTML, which we parse directly to avoid fragile DOM queries.
"""
import asyncio
import json
import logging
import re
from typing import Optional
from dataclasses import dataclass, field

import httpx
from playwright.async_api import async_playwright, Page
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

BASE_URL = "https://www.gunplacentral.com"

# Franchises that are NOT Gundam/Gunpla — skip these
NON_GUNDAM_FRANCHISES = {
    "pokemon", "digimon", "dragon ball", "evangelion", "one piece",
    "naruto", "sword art online", "attack on titan", "kamen rider",
    "super sentai", "ultraman", "macross", "full metal alchemist",
}


@dataclass
class ScrapedKit:
    external_id: int
    name: str
    franchise: Optional[str] = None
    series: Optional[str] = None
    grade: Optional[str] = None
    scale: Optional[str] = None
    release_date: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    avg_rating: Optional[float] = None
    total_owners: Optional[int] = None
    source_url: Optional[str] = None
    image_urls: list[str] = field(default_factory=list)


def _is_gundam(franchise: Optional[str]) -> bool:
    if not franchise:
        return True  # assume Gundam if unset
    fl = franchise.lower()
    for non_g in NON_GUNDAM_FRANCHISES:
        if non_g in fl:
            return False
    return True


def _extract_next_data(html: str) -> Optional[dict]:
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _parse_kit_from_next_data(kit_id: int, data: dict) -> Optional[ScrapedKit]:
    try:
        props = data.get("props", {}).get("pageProps", {})

        # The actual kit data key varies; try common patterns
        kit_data = props.get("kit") or props.get("kitData") or props.get("data") or {}

        if not kit_data:
            return None

        name = kit_data.get("name") or kit_data.get("title") or kit_data.get("kit_name")
        if not name:
            return None

        franchise = (
            kit_data.get("franchise") or
            kit_data.get("franchise_name") or
            (kit_data.get("franchise_data") or {}).get("name")
        )
        series = (
            kit_data.get("series") or
            kit_data.get("series_name") or
            (kit_data.get("series_data") or {}).get("name")
        )
        grade = (
            kit_data.get("grade") or
            kit_data.get("grade_name") or
            (kit_data.get("grade_data") or {}).get("name")
        )
        scale = kit_data.get("scale") or kit_data.get("scale_name")
        release_date = kit_data.get("release_date") or kit_data.get("releaseDate")
        brand = (
            kit_data.get("brand") or
            kit_data.get("brand_name") or
            (kit_data.get("brand_data") or {}).get("name")
        )
        description = kit_data.get("description") or kit_data.get("desc")

        avg_rating = None
        for key in ("average_rating", "avg_rating", "rating"):
            v = kit_data.get(key)
            if v is not None:
                try:
                    avg_rating = float(v)
                except (ValueError, TypeError):
                    pass
                break

        total_owners = None
        for key in ("total_owners", "owners", "owner_count"):
            v = kit_data.get(key)
            if v is not None:
                try:
                    total_owners = int(v)
                except (ValueError, TypeError):
                    pass
                break

        # Collect image URLs from various possible locations
        image_urls = []
        for img_key in ("images", "image_urls", "photos", "gallery"):
            imgs = kit_data.get(img_key)
            if isinstance(imgs, list):
                for img in imgs:
                    if isinstance(img, str):
                        image_urls.append(img)
                    elif isinstance(img, dict):
                        url = img.get("url") or img.get("src") or img.get("image_url")
                        if url:
                            image_urls.append(url)
                break

        main_img = kit_data.get("image") or kit_data.get("image_url") or kit_data.get("thumbnail")
        if isinstance(main_img, str) and main_img and main_img not in image_urls:
            image_urls.insert(0, main_img)

        return ScrapedKit(
            external_id=kit_id,
            name=name,
            franchise=franchise,
            series=series,
            grade=grade,
            scale=scale,
            release_date=str(release_date) if release_date else None,
            brand=brand,
            description=description,
            avg_rating=avg_rating,
            total_owners=total_owners,
            source_url=f"{BASE_URL}/kits/{kit_id}",
            image_urls=image_urls,
        )
    except Exception as e:
        logger.warning(f"Failed parsing __NEXT_DATA__ for kit {kit_id}: {e}")
        return None


async def _scrape_kit_page(page: Page, kit_id: int) -> Optional[ScrapedKit]:
    url = f"{BASE_URL}/kits/{kit_id}"
    try:
        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        if response and response.status == 404:
            return None

        html = await page.content()

        # Try __NEXT_DATA__ first (fast, no DOM needed)
        next_data = _extract_next_data(html)
        if next_data:
            kit = _parse_kit_from_next_data(kit_id, next_data)
            if kit:
                return kit

        # Fall back to DOM scraping
        return await _scrape_kit_dom(page, kit_id, url)

    except Exception as e:
        logger.warning(f"Error scraping kit {kit_id}: {e}")
        return None


async def _scrape_kit_dom(page: Page, kit_id: int, url: str) -> Optional[ScrapedKit]:
    """DOM fallback scraper for when __NEXT_DATA__ doesn't contain what we need."""
    try:
        name_el = await page.query_selector("h1")
        name = (await name_el.inner_text()).strip() if name_el else None
        if not name:
            return None

        async def get_field(selectors: list[str]) -> Optional[str]:
            for sel in selectors:
                el = await page.query_selector(sel)
                if el:
                    text = (await el.inner_text()).strip()
                    if text:
                        return text
            return None

        franchise = await get_field(["[data-field='franchise']", ".franchise", "[class*='franchise']"])
        series = await get_field(["[data-field='series']", ".series", "[class*='series']"])
        grade = await get_field(["[data-field='grade']", ".grade", "[class*='grade']"])
        scale = await get_field(["[data-field='scale']", ".scale", "[class*='scale']"])
        release_date = await get_field(["[data-field='release_date']", ".release-date", "[class*='release']"])
        brand = await get_field(["[data-field='brand']", ".brand", "[class*='brand']"])

        # Collect images
        img_elements = await page.query_selector_all("img")
        image_urls = []
        for img in img_elements:
            src = await img.get_attribute("src")
            if src and ("kit" in src.lower() or "gunpla" in src.lower() or "bandai" in src.lower()):
                image_urls.append(src)

        return ScrapedKit(
            external_id=kit_id,
            name=name,
            franchise=franchise,
            series=series,
            grade=grade,
            scale=scale,
            release_date=release_date,
            brand=brand,
            source_url=url,
            image_urls=image_urls[:10],
        )
    except Exception as e:
        logger.warning(f"DOM scrape failed for kit {kit_id}: {e}")
        return None


async def discover_kit_ids(max_id: int = 5000) -> list[int]:
    """
    Discover all valid kit IDs. We probe sequentially and stop after
    finding a configurable number of consecutive 404s.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        ids = []
        consecutive_404 = 0
        max_consecutive_404 = 50

        for kit_id in range(1, max_id + 1):
            url = f"{BASE_URL}/kits/{kit_id}"
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                if response and response.status == 404:
                    consecutive_404 += 1
                    if consecutive_404 >= max_consecutive_404:
                        logger.info(f"Stopping discovery at id={kit_id} after {max_consecutive_404} consecutive 404s")
                        break
                else:
                    consecutive_404 = 0
                    ids.append(kit_id)
                    logger.debug(f"Found kit id={kit_id}")
            except Exception:
                consecutive_404 += 1

            await asyncio.sleep(0.5)

        await browser.close()
        return ids


async def scrape_kits(
    kit_ids: list[int],
    progress_callback=None,
) -> list[ScrapedKit]:
    """Scrape a list of kit IDs, returning only Gundam kits."""
    results = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for i, kit_id in enumerate(kit_ids):
            kit = await _scrape_kit_page(page, kit_id)

            if kit and _is_gundam(kit.franchise):
                results.append(kit)
                logger.info(f"[{i+1}/{len(kit_ids)}] Scraped: {kit.name}")
            elif kit:
                logger.info(f"[{i+1}/{len(kit_ids)}] Skipped non-Gundam kit {kit_id}: {kit.name} ({kit.franchise})")

            if progress_callback:
                progress_callback(i + 1, len(kit_ids), kit)

            await asyncio.sleep(0.8)  # polite delay

        await browser.close()

    return results


async def get_latest_kit_id() -> Optional[int]:
    """Fetch the kits listing page sorted by newest to find the latest external ID."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(
            f"{BASE_URL}/kits?searchSortType=created_at&sortOrder=desc",
            wait_until="networkidle",
            timeout=30000,
        )
        html = await page.content()
        await browser.close()

    next_data = _extract_next_data(html)
    if not next_data:
        return None

    try:
        props = next_data.get("props", {}).get("pageProps", {})
        kits = props.get("kits") or props.get("kitList") or props.get("data") or []
        if kits and isinstance(kits, list):
            ids = []
            for k in kits:
                if isinstance(k, dict):
                    kid = k.get("id") or k.get("kit_id")
                    if kid:
                        ids.append(int(kid))
            return max(ids) if ids else None
    except Exception:
        pass
    return None
