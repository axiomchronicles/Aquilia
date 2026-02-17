import { Link, useLocation } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import { Sun, Moon, Github, Menu, X, BookOpen, Zap, Plug, Shield, Cpu, Wrench, ChevronDown } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

const navSections = [
  {
    title: 'Getting Started',
    icon: BookOpen,
    links: [
      { label: 'Introduction', path: '/docs' },
      { label: 'Installation', path: '/docs/installation' },
      { label: 'Quick Start', path: '/docs/quickstart' },
      { label: 'Architecture', path: '/docs/architecture' },
      { label: 'Project Structure', path: '/docs/project-structure' },
    ],
  },
  {
    title: 'Core',
    icon: Zap,
    links: [
      { label: 'Server', path: '/docs/server' },
      { label: 'Configuration', path: '/docs/config' },
      { label: 'Request & Response', path: '/docs/request-response' },
      { label: 'Controllers', path: '/docs/controllers' },
      { label: 'Routing', path: '/docs/routing' },
    ],
  },
  {
    title: 'DI & Data',
    icon: Plug,
    links: [
      { label: 'DI Container', path: '/docs/di' },
      { label: 'Models (ORM)', path: '/docs/models' },
      { label: 'Serializers', path: '/docs/serializers' },
      { label: 'Database', path: '/docs/database' },
    ],
  },
  {
    title: 'Security',
    icon: Shield,
    links: [
      { label: 'Authentication', path: '/docs/auth' },
      { label: 'Sessions', path: '/docs/sessions' },
      { label: 'Middleware', path: '/docs/middleware' },
    ],
  },
  {
    title: 'Advanced',
    icon: Cpu,
    links: [
      { label: 'Aquilary Registry', path: '/docs/aquilary' },
      { label: 'Effects System', path: '/docs/effects' },
      { label: 'Fault System', path: '/docs/faults' },
      { label: 'Cache', path: '/docs/cache' },
      { label: 'WebSockets', path: '/docs/websockets' },
      { label: 'Templates', path: '/docs/templates' },
      { label: 'Mail', path: '/docs/mail' },
      { label: 'MLOps', path: '/docs/mlops' },
    ],
  },
  {
    title: 'Tooling',
    icon: Wrench,
    links: [
      { label: 'CLI', path: '/docs/cli' },
      { label: 'Testing', path: '/docs/testing' },
      { label: 'OpenAPI', path: '/docs/openapi' },
      { label: 'Trace & Debug', path: '/docs/trace' },
    ],
  },
]

export function Navbar() {
  const { theme, toggle } = useTheme()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const isDark = theme === 'dark'
  const menuRef = useRef<HTMLDivElement>(null)

  // Close menu on route change
  useEffect(() => { setMenuOpen(false) }, [location.pathname])

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  return (
    <nav className="fixed w-full z-50 glass border-b border-[var(--border-color)]/50" ref={menuRef}>
      <div className="max-w-[90rem] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex-shrink-0 flex items-center gap-3 group">
            <div className="relative w-9 h-9 rounded-lg bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center border border-aquilia-500/20 shadow-lg shadow-aquilia-500/20 transition-transform group-hover:scale-110 duration-300">
              <span className="text-aquilia-500 font-black text-lg font-mono">A</span>
            </div>
            <span className="font-bold text-xl tracking-tighter gradient-text font-mono hidden sm:inline">Aquilia</span>
          </Link>

          {/* Center: hamburger doc nav */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                menuOpen
                  ? `${isDark ? 'bg-aquilia-500/10 text-aquilia-400 border border-aquilia-500/30' : 'bg-aquilia-50 text-aquilia-700 border border-aquilia-200'}`
                  : `${isDark ? 'text-gray-300 hover:text-white hover:bg-white/5 border border-transparent' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 border border-transparent'}`
              }`}
            >
              {menuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
              <span>Documentation</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${menuOpen ? 'rotate-180' : ''}`} />
            </button>

            <Link
              to="/docs"
              className={`hidden md:flex px-3 py-2 text-sm font-medium transition-colors rounded-lg ${
                location.pathname === '/docs'
                  ? 'text-aquilia-400'
                  : `${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`
              }`}
            >
              Guide
            </Link>
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-2">
            <button onClick={toggle} className={`p-2 rounded-lg transition-colors ${isDark ? 'hover:bg-white/10 text-gray-400' : 'hover:bg-gray-200 text-gray-500'}`} title="Toggle theme">
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <a href="https://github.com/axiomchronicles/Aquilia" target="_blank" rel="noopener" className={`p-2 rounded-lg transition-colors ${isDark ? 'hover:bg-white/10 text-gray-400' : 'hover:bg-gray-200 text-gray-500'}`}>
              <Github className="w-5 h-5" />
            </a>
          </div>
        </div>
      </div>

      {/* Mega-menu dropdown */}
      {menuOpen && (
        <div className={`absolute left-0 right-0 top-16 border-b shadow-2xl ${isDark ? 'bg-[#09090b]/98 border-white/10' : 'bg-white/98 border-gray-200'} backdrop-blur-xl`}>
          <div className="max-w-[90rem] mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8">
              {navSections.map((section) => {
                const Icon = section.icon
                return (
                  <div key={section.title}>
                    <h4 className={`text-xs font-bold uppercase tracking-wider mb-4 flex items-center gap-2 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      <Icon className="w-3.5 h-3.5 text-aquilia-500" />
                      {section.title}
                    </h4>
                    <ul className="space-y-1">
                      {section.links.map((link) => (
                        <li key={link.path}>
                          <Link
                            to={link.path}
                            className={`block px-2 py-1.5 rounded-lg text-sm transition-all ${
                              location.pathname === link.path || location.pathname.startsWith(link.path + '/')
                                ? `font-medium ${isDark ? 'text-aquilia-400 bg-aquilia-500/10' : 'text-aquilia-700 bg-aquilia-50'}`
                                : `${isDark ? 'text-gray-400 hover:text-white hover:bg-white/5' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`
                            }`}
                          >
                            {link.label}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              })}
            </div>
            {/* Footer row */}
            <div className={`mt-8 pt-6 border-t flex items-center justify-between ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
              <p className={`text-xs ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>Aquilia Framework v0.2.0</p>
              <div className="flex items-center gap-4">
                <a href="https://github.com/axiomchronicles/Aquilia" target="_blank" rel="noopener" className={`text-xs flex items-center gap-1.5 transition-colors ${isDark ? 'text-gray-500 hover:text-aquilia-400' : 'text-gray-400 hover:text-aquilia-600'}`}>
                  <Github className="w-3.5 h-3.5" /> GitHub
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </nav>
  )
}
