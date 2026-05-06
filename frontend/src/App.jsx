import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { Database, Settings, BookOpen } from 'lucide-react'
import HomePage from './pages/HomePage'
import KitPage from './pages/KitPage'
import AdminPage from './pages/AdminPage'
import AddKitPage from './pages/AddKitPage'

export default function App() {
  const { pathname } = useLocation()
  const navLink = (to, label, Icon) => (
    <Link
      to={to}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors
        ${pathname === to
          ? 'bg-gundam-border text-white'
          : 'text-gray-400 hover:text-white hover:bg-gundam-card'}`}
    >
      <Icon size={16} />
      {label}
    </Link>
  )

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-gundam-card border-b border-gundam-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-white">
            <Database size={22} className="text-gundam-red" />
            <span>GunplaDB</span>
          </Link>
          <nav className="flex items-center gap-1">
            {navLink('/', 'Kits', Database)}
            {navLink('/admin', 'Admin', Settings)}
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/kits/:id" element={<KitPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/kits/new" element={<AddKitPage />} />
        </Routes>
      </main>

      <footer className="border-t border-gundam-border py-4 text-center text-xs text-gray-500">
        GunplaDB — All kit data sourced from GunplaCentral & Bandai Hobby
      </footer>
    </div>
  )
}
