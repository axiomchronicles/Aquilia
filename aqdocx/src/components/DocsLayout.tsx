import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import { Navbar } from './Navbar'
import { Sidebar } from './Sidebar'
import { useTheme } from '../context/ThemeContext'

export function DocsLayout() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen">
      <Navbar onToggleSidebar={() => setIsSidebarOpen(true)} />
      {/* Ambient Background */}
      <div className="fixed inset-0 -z-10">
        <div className={isDark ? 'absolute inset-0 bg-black' : 'absolute inset-0 bg-[#fafafa]'} />
        <div className={`absolute inset-0 ${isDark ? 'bg-gradient-to-br from-aquilia-500/5 via-transparent to-blue-500/5' : ''}`} />
        <div className={`absolute top-0 left-1/4 w-96 h-96 ${isDark ? 'bg-aquilia-500/10' : 'bg-aquilia-500/5'} rounded-full blur-3xl`} />
        <div className={`absolute bottom-0 right-1/4 w-96 h-96 ${isDark ? 'bg-blue-500/10' : 'bg-blue-500/5'} rounded-full blur-3xl`} />
      </div>

      <div className="relative pt-16 min-h-screen">
        <div className="flex flex-col lg:flex-row max-w-[90rem] mx-auto">
          <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
          <div className="flex-1 min-w-0">
            <div className="max-w-4xl px-4 sm:px-6 lg:px-12 py-12">
              <Outlet />
              {/* Footer */}
              <div className={`mt-24 pt-8 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
                <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
                  <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                    Last updated: February 2026
                  </p>
                  <div className="flex gap-4">
                    <a href="https://github.com/axiomchronicles/Aquilia" target="_blank" rel="noopener" className={`flex items-center gap-2 text-sm transition-colors ${isDark ? 'text-gray-500 hover:text-aquilia-400' : 'text-gray-400 hover:text-aquilia-600'}`}>
                      Crafted with ❤️ using Aquilia
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
