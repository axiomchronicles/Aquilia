import { useLocation } from 'react-router-dom'
import { Construction } from 'lucide-react'
import { useTheme } from '../../context/ThemeContext'

interface PlaceholderProps {
  title?: string
  section?: string
}

export function PlaceholderPage({ title: propTitle, section }: PlaceholderProps = {}) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const location = useLocation()
  const parts = location.pathname.split('/').filter(Boolean)
  const title = propTitle || parts[parts.length - 1]
    ?.replace(/-/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase()) || 'Page'

  return (
    <div className="max-w-4xl mx-auto">
      <div className={`flex flex-col items-center justify-center py-20 text-center rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
        <Construction className="w-16 h-16 text-aquilia-500 mb-6 animate-pulse" />
        {section && <span className="text-aquilia-500 text-sm font-semibold tracking-wider uppercase mb-2">{section}</span>}
        <h1 className={`text-3xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{title}</h1>
        <p className={`max-w-md ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          This documentation page is being written. Check back soon for comprehensive coverage of this topic.
        </p>
        <div className="mt-8 flex items-center gap-2 px-4 py-2 rounded-full bg-aquilia-500/10 text-aquilia-500 text-sm font-medium">
          <span className="w-2 h-2 rounded-full bg-aquilia-500 animate-pulse" />
          Coming Soon
        </div>
      </div>
    </div>
  )
}
