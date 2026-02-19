import { Link, useLocation } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import {
  Sun, Moon, Github, ChevronDown, Rocket, Zap, Box,
  Shield, Layers, Wrench, BookOpen, Download, Cpu,
  Settings, Database, Lock, Key, Code, Bug, Wifi,
  Mail, FileText, Brain, Terminal, TestTube, FileCode, Eye
} from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

const navSections = [
  {
    title: 'Getting Started',
    icon: Rocket,
    links: [
      { label: 'Introduction', path: '/docs', icon: BookOpen },
      { label: 'Installation', path: '/docs/installation', icon: Download },
      { label: 'Quick Start', path: '/docs/quickstart', icon: Zap },
      { label: 'Architecture', path: '/docs/architecture', icon: Cpu },
      { label: 'Project Structure', path: '/docs/project-structure', icon: FileCode },
    ],
  },
  {
    title: 'Core',
    icon: Box,
    links: [
      { label: 'Server', path: '/docs/server', icon: Cpu },
      { label: 'Configuration', path: '/docs/config', icon: Settings },
      { label: 'Request & Response', path: '/docs/request-response', icon: Code },
      { label: 'Controllers', path: '/docs/controllers', icon: Box },
      { label: 'Routing', path: '/docs/routing', icon: Zap },
    ],
  },
  {
    title: 'DI & Data',
    icon: Database,
    links: [
      { label: 'DI Container', path: '/docs/di', icon: Box },
      { label: 'Models (ORM)', path: '/docs/models', icon: Database },
      { label: 'Serializers', path: '/docs/serializers', icon: FileText },
      { label: 'Database', path: '/docs/database', icon: Database },
    ],
  },
  {
    title: 'Security',
    icon: Shield,
    links: [
      { label: 'Authentication', path: '/docs/auth', icon: Lock },
      { label: 'Authorization', path: '/docs/authz', icon: Key },
      { label: 'Sessions', path: '/docs/sessions', icon: Key },
      { label: 'Middleware', path: '/docs/middleware', icon: Shield },
    ],
  },
  {
    title: 'Advanced',
    icon: Layers,
    links: [
      { label: 'Aquilary Registry', path: '/docs/aquilary', icon: Layers },
      { label: 'Effects System', path: '/docs/effects', icon: Zap },
      { label: 'Fault System', path: '/docs/faults', icon: Bug },
      { label: 'Cache', path: '/docs/cache', icon: Zap },
      { label: 'WebSockets', path: '/docs/websockets', icon: Wifi },
      { label: 'Templates', path: '/docs/templates', icon: FileText },
      { label: 'Mail', path: '/docs/mail', icon: Mail },
      { label: 'MLOps', path: '/docs/mlops', icon: Brain },
    ],
  },
  {
    title: 'Tooling',
    icon: Wrench,
    links: [
      { label: 'CLI', path: '/docs/cli', icon: Terminal },
      { label: 'Testing', path: '/docs/testing', icon: TestTube },
      { label: 'OpenAPI', path: '/docs/openapi', icon: FileCode },
      { label: 'Trace & Debug', path: '/docs/trace', icon: Eye },
    ],
  },
]

export function Navbar() {
  const { theme, toggle } = useTheme()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const location = useLocation()
  const isDark = theme === 'dark'
  const dropdownRef = useRef<HTMLDivElement>(null)
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Close on route change
  useEffect(() => { setDropdownOpen(false) }, [location.pathname])

  const handleMouseEnter = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current)
    setDropdownOpen(true)
  }

  const handleMouseLeave = () => {
    hoverTimeout.current = setTimeout(() => setDropdownOpen(false), 250)
  }

  return (
    <nav className="fixed w-full z-50 glass border-b border-[var(--border-color)]/50">
      <div className="max-w-[90rem] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex-shrink-0 flex items-center gap-3 group relative">
            <div className="relative">
              <img
                src="/logo.png"
                alt="Aquilia"
                className="w-9 h-9 rounded-lg shadow-lg shadow-aquilia-500/20 transition-all duration-300 group-hover:scale-110 group-hover:shadow-aquilia-500/40"
              />
              <div className="absolute inset-0 rounded-lg bg-gradient-to-tr from-aquilia-500/0 via-aquilia-400/0 to-aquilia-300/0 group-hover:from-aquilia-500/20 group-hover:via-aquilia-400/10 group-hover:to-transparent transition-all duration-300" />
            </div>
            <span className="font-bold text-xl tracking-tighter gradient-text font-mono hidden sm:inline relative">
              Aquilia
              <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
            </span>
          </Link>

          {/* Center: hover dropdown nav */}
          <div className="flex items-center gap-1">
            <div
              ref={dropdownRef}
              className="relative"
              onMouseEnter={handleMouseEnter}
              onMouseLeave={handleMouseLeave}
            >
              <button
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 relative overflow-hidden group ${dropdownOpen
                    ? `${isDark ? 'bg-aquilia-500/10 text-aquilia-400 border border-aquilia-500/30' : 'bg-aquilia-50 text-aquilia-700 border border-aquilia-200'}`
                    : `${isDark ? 'text-gray-300 hover:text-white hover:bg-white/5 border border-transparent' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 border border-transparent'}`
                  }`}
              >
                <BookOpen className="w-4 h-4" />
                <span>Documentation</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-300 ${dropdownOpen ? 'rotate-180' : ''}`} />
                {/* Shimmer effect */}
                <div className={`absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 bg-gradient-to-r ${isDark ? 'from-transparent via-white/5 to-transparent' : 'from-transparent via-gray-200 to-transparent'}`} />
              </button>

              {/* Mega-menu dropdown — hover-triggered */}
              {dropdownOpen && (
                <div
                  className={`absolute left-1/2 -translate-x-1/2 top-full mt-0 w-[54rem] rounded-2xl border shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-top-2 duration-200 ${isDark ? 'bg-[#09090b]/98 border-white/10' : 'bg-white/98 border-gray-200'}`}
                  style={{ animationDuration: '200ms', animationFillMode: 'forwards' }}
                >
                  {/* Invisible bridge keeps hover connected */}
                  <div className="absolute -top-2 left-0 right-0 h-3" />
                  <div className="p-6">
                    <div className="grid grid-cols-3 gap-6">
                      {navSections.map((section, sectionIdx) => {
                        const SectionIcon = section.icon
                        return (
                          <div
                            key={section.title}
                            className="animate-in fade-in slide-in-from-top-1 duration-300"
                            style={{ animationDelay: `${sectionIdx * 50}ms`, animationFillMode: 'backwards' }}
                          >
                            <div className="flex items-center gap-2 mb-3">
                              <SectionIcon className={`w-3.5 h-3.5 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`} />
                              <h4 className={`text-[10px] font-bold uppercase tracking-widest ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                                {section.title}
                              </h4>
                            </div>
                            <ul className="space-y-0.5">
                              {section.links.map((link) => {
                                const LinkIcon = link.icon
                                const isActive = location.pathname === link.path || location.pathname.startsWith(link.path + '/')
                                return (
                                  <li key={link.path}>
                                    <Link
                                      to={link.path}
                                      className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-sm transition-all duration-200 group/link relative overflow-hidden ${isActive
                                          ? `font-medium ${isDark ? 'text-aquilia-400 bg-aquilia-500/10' : 'text-aquilia-700 bg-aquilia-50'}`
                                          : `${isDark ? 'text-gray-400 hover:text-white hover:bg-white/5' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`
                                        }`}
                                    >
                                      <LinkIcon className={`w-3.5 h-3.5 transition-transform duration-200 group-hover/link:scale-110 ${isActive ? 'animate-pulse' : ''}`} />
                                      <span>{link.label}</span>
                                      {!isActive && (
                                        <div className={`absolute inset-0 -translate-x-full group-hover/link:translate-x-full transition-transform duration-700 bg-gradient-to-r ${isDark ? 'from-transparent via-white/3 to-transparent' : 'from-transparent via-gray-100 to-transparent'}`} />
                                      )}
                                    </Link>
                                  </li>
                                )
                              })}
                            </ul>
                          </div>
                        )
                      })}
                    </div>
                    {/* Footer */}
                    <div className={`mt-5 pt-4 border-t flex items-center justify-between ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                      <div className="flex items-center gap-2">
                        <div className={`w-1.5 h-1.5 rounded-full bg-aquilia-500 animate-pulse shadow-lg shadow-aquilia-500/50`} />
                        <p className={`text-xs ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>Aquilia Framework v1.0.0</p>
                      </div>
                      <a
                        href="https://github.com/axiomchronicles/Aquilia"
                        target="_blank"
                        rel="noopener"
                        className={`text-xs flex items-center gap-1.5 transition-all duration-200 group/gh ${isDark ? 'text-gray-500 hover:text-aquilia-400' : 'text-gray-400 hover:text-aquilia-600'}`}
                      >
                        <Github className="w-3.5 h-3.5 group-hover/gh:rotate-12 transition-transform duration-200" />
                        <span>GitHub</span>
                      </a>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <Link
              to="/docs"
              className={`hidden md:flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-all duration-200 rounded-lg group/guide relative overflow-hidden ${location.pathname === '/docs'
                  ? 'text-aquilia-400'
                  : `${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`
                }`}
            >
              <BookOpen className="w-4 h-4 group-hover/guide:scale-110 transition-transform duration-200" />
              <span>Guide</span>
              <div className={`absolute inset-0 -translate-x-full group-hover/guide:translate-x-full transition-transform duration-700 bg-gradient-to-r ${isDark ? 'from-transparent via-white/5 to-transparent' : 'from-transparent via-gray-200 to-transparent'}`} />
            </Link>
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggle}
              className={`p-2 rounded-lg transition-all duration-200 relative overflow-hidden group ${isDark ? 'hover:bg-white/10 text-gray-400 hover:text-white' : 'hover:bg-gray-200 text-gray-500 hover:text-gray-900'}`}
              title="Toggle theme"
            >
              {isDark ? (
                <Sun className="w-5 h-5 group-hover:rotate-180 transition-transform duration-500" />
              ) : (
                <Moon className="w-5 h-5 group-hover:-rotate-12 transition-transform duration-300" />
              )}
              <div className={`absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r ${isDark ? 'from-transparent via-white/5 to-transparent' : 'from-transparent via-gray-200 to-transparent'}`} />
            </button>
            <a
              href="https://github.com/axiomchronicles/Aquilia"
              target="_blank"
              rel="noopener"
              className={`p-2 rounded-lg transition-all duration-200 relative overflow-hidden group ${isDark ? 'hover:bg-white/10 text-gray-400 hover:text-white' : 'hover:bg-gray-200 text-gray-500 hover:text-gray-900'}`}
              title="View on GitHub"
            >
              <Github className="w-5 h-5 group-hover:scale-110 transition-transform duration-200" />
              <div className={`absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r ${isDark ? 'from-transparent via-white/5 to-transparent' : 'from-transparent via-gray-200 to-transparent'}`} />
            </a>
          </div>
        </div>
      </div>
    </nav>
  )
}
