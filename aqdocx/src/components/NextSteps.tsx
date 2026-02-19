
import { useTheme } from '../context/ThemeContext'
import { Link, useLocation } from 'react-router-dom'
import { sections } from './Sidebar'

// Flatten sections into a linear list of { label, path }
const allPages: { label: string; path: string }[] = []
sections.forEach(section => {
    section.items.forEach(item => {
        allPages.push({ label: item.label, path: item.path })
        if (item.children) {
            item.children.forEach(child => {
                allPages.push({ label: child.label, path: child.path })
            })
        }
    })
})

export function NextSteps() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'
    const location = useLocation()

    // Find current index
    const currentIndex = allPages.findIndex(p => p.path === location.pathname)

    // Logic: 
    // 1. Get next 1-2 items in sequence (if available)
    // 2. Fill remaining slots with random items from other sections
    // Target: 3-5 items total

    const suggestions: { label: string; path: string }[] = []

    // Add next sequential items
    if (currentIndex !== -1 && currentIndex < allPages.length - 1) {
        suggestions.push(allPages[currentIndex + 1])
        if (currentIndex < allPages.length - 2) {
            suggestions.push(allPages[currentIndex + 2])
        }
    }

    // Fill with random items until we have 4-5 items
    // Ensure we don't pick current page or already added pages
    const attempts = 0
    const maxItems = Math.floor(Math.random() * 3) + 3 // 3 to 5 items

    while (suggestions.length < maxItems && attempts < 50) {
        const randomIndex = Math.floor(Math.random() * allPages.length)
        const candidate = allPages[randomIndex]

        // Check if valid candidate
        const isCurrent = candidate.path === location.pathname
        const isAlreadyAdded = suggestions.some(s => s.path === candidate.path)

        if (!isCurrent && !isAlreadyAdded) {
            suggestions.push(candidate)
        }
    }

    return (
        <section className="mb-10 mt-16 pt-10 border-t border-dashed border-gray-200 dark:border-white/10">
            <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Next Steps</h2>
            <div className="flex flex-col gap-3">
                {suggestions.map((page, i) => (
                    <Link
                        key={i}
                        to={page.path}
                        className={`text-sm font-medium transition-colors flex items-center gap-2 ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'
                            }`}
                    >
                        <span className="opacity-70">→</span> {page.label}
                    </Link>
                ))}
            </div>
        </section>
    )
}
