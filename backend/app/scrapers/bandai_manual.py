"""
Scraper for Bandai Hobby instruction manuals.
URL pattern: https://manual.bandai-hobby.net/menus/detail/{id}

The site provides PDF/image-based manuals. We discover available manuals
by iterating IDs and download the pages as a combined PDF stored in MinIO.
"""
import asyncio
import io
import logging
from typing import Optional
from dataclasses import dataclass, field

import httpx
from playwright.async_api import async_playwright, Page
from PIL import Image

logger = logging.getLogger(__name__)

BASE_URL = "https://manual.bandai-hobby.net"
DETAIL_URL = f"{BASE_URL}/menus/detail"


@dataclass
class ScrapedManual:
    bandai_id: int
    title: Optional[str] = None
    source_url: Optional[str] = None
    page_image_urls: list[str] = field(default_factory=list)
    pdf_bytes: Optional[bytes] = None
    page_count: int = 0


async def _get_manual_page_urls(page: Page, manual_id: int) -> Optional[ScrapedManual]:
    url = f"{DETAIL_URL}/{manual_id}"
    try:
        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        if not response or response.status in (404, 403, 410):
            return None

        # Extract title
        title_el = await page.query_selector("h1, h2, .manual-title, title")
        title = None
        if title_el:
            title = (await title_el.inner_text()).strip()

        # Find page images — Bandai manuals display pages as images
        # Common patterns: img with page class, or canvas elements with data-src
        page_urls = []

        # Try data-src attributes (lazy loaded)
        imgs = await page.query_selector_all("img[data-src], img[src]")
        for img in imgs:
            src = await img.get_attribute("data-src") or await img.get_attribute("src")
            if src and any(ext in src.lower() for ext in (".jpg", ".jpeg", ".png", ".webp")):
                if "page" in src.lower() or "manual" in src.lower() or "/p/" in src:
                    if src not in page_urls:
                        page_urls.append(src)

        # Also look for a PDF direct link
        pdf_link = await page.query_selector("a[href$='.pdf']")
        if pdf_link:
            pdf_url = await pdf_link.get_attribute("href")
            if pdf_url:
                if not pdf_url.startswith("http"):
                    pdf_url = BASE_URL + pdf_url
                return ScrapedManual(
                    bandai_id=manual_id,
                    title=title,
                    source_url=url,
                    page_image_urls=[pdf_url],  # Will be treated as PDF download
                    page_count=1,
                )

        if not page_urls:
            return None

        return ScrapedManual(
            bandai_id=manual_id,
            title=title,
            source_url=url,
            page_image_urls=page_urls,
            page_count=len(page_urls),
        )

    except Exception as e:
        logger.warning(f"Error fetching manual {manual_id}: {e}")
        return None


async def _download_pages_as_pdf(page_urls: list[str]) -> Optional[bytes]:
    """Download page images and combine into a single PDF."""
    images = []
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for url in page_urls:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    images.append(img)
            except Exception as e:
                logger.warning(f"Failed to download page {url}: {e}")
                continue

    if not images:
        return None

    pdf_buffer = io.BytesIO()
    images[0].save(
        pdf_buffer,
        format="PDF",
        save_all=True,
        append_images=images[1:],
    )
    return pdf_buffer.getvalue()


async def scrape_manual(manual_id: int) -> Optional[ScrapedManual]:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        manual = await _get_manual_page_urls(page, manual_id)
        await browser.close()

    if not manual or not manual.page_image_urls:
        return None

    # If it's a direct PDF link, download it
    if len(manual.page_image_urls) == 1 and manual.page_image_urls[0].endswith(".pdf"):
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(manual.page_image_urls[0])
            if resp.status_code == 200:
                manual.pdf_bytes = resp.content
                manual.page_count = 1
    else:
        manual.pdf_bytes = await _download_pages_as_pdf(manual.page_image_urls)
        manual.page_count = len(manual.page_image_urls)

    return manual


async def find_manuals_in_range(
    start_id: int,
    end_id: int,
    progress_callback=None,
) -> list[ScrapedManual]:
    """Scan a range of manual IDs and return those that exist."""
    results = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for i, manual_id in enumerate(range(start_id, end_id + 1)):
            manual = await _get_manual_page_urls(page, manual_id)

            if manual:
                results.append(manual)
                logger.info(f"Found manual {manual_id}: {manual.title}")

            if progress_callback:
                progress_callback(i + 1, end_id - start_id + 1, manual_id)

            await asyncio.sleep(0.5)

        await browser.close()

    return results


async def search_manual_by_name(kit_name: str) -> Optional[int]:
    """
    Try to find a Bandai manual ID by searching for the kit name.
    The Bandai site may have a search endpoint we can probe.
    """
    search_url = f"{BASE_URL}/menus/search"
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(search_url, params={"q": kit_name})
            if resp.status_code == 200:
                # Parse search results — implementation depends on site structure
                # For now, return None and rely on manual matching
                pass
        except Exception:
            pass
    return None
