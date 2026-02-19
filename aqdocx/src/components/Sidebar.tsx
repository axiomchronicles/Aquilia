import { Link, useLocation } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import { useState, useEffect } from 'react'
import {
  BookOpen, Download, Rocket, Zap, Layers, Database, Shield, Settings,
  AlertCircle, Terminal, GitBranch, ChevronDown, ChevronRight,
  Server, Box, Mail, Palette, TestTube, Brain, BarChart, Plug,
  FileCode, Cpu, Globe, Lock, HardDrive, RefreshCw, Wrench, Layout,
  Blocks, Workflow, Binary, Gauge, Network, Boxes, Cog, Tag
} from 'lucide-react'

interface SidebarSection {
  title: string
  icon: React.ReactNode
  items: SidebarItem[]
}

interface SidebarItem {
  label: string
  path: string
  icon?: React.ReactNode
  children?: SidebarItem[]
}

const sections: SidebarSection[] = [
  {
    title: 'Getting Started',
    icon: <Rocket className="w-3 h-3" />,
    items: [
      { label: 'Introduction', path: '/docs', icon: <BookOpen className="w-3.5 h-3.5" /> },
      { label: 'Installation', path: '/docs/installation', icon: <Download className="w-3.5 h-3.5" /> },
      { label: 'Quick Start', path: '/docs/quickstart', icon: <Zap className="w-3.5 h-3.5" /> },
      { label: 'Architecture', path: '/docs/architecture', icon: <Network className="w-3.5 h-3.5" /> },
      { label: 'Project Structure', path: '/docs/project-structure', icon: <Blocks className="w-3.5 h-3.5" /> },
    ]
  },
  {
    title: 'Core',
    icon: <Zap className="w-3 h-3" />,
    items: [
      {
        label: 'Server', path: '/docs/server', icon: <Server className="w-3.5 h-3.5" />,
        children: [
          { label: 'AquiliaServer', path: '/docs/server/aquilia-server' },
          { label: 'ASGI Adapter', path: '/docs/server/asgi' },
          { label: 'Lifecycle', path: '/docs/server/lifecycle' },
        ]
      },
      {
        label: 'Configuration', path: '/docs/config', icon: <Settings className="w-3.5 h-3.5" />,
        children: [
          { label: 'ConfigLoader', path: '/docs/config/loader' },
          { label: 'Workspace Builder', path: '/docs/config/workspace' },
          { label: 'Module Builder', path: '/docs/config/module' },
          { label: 'Integrations', path: '/docs/config/integrations' },
        ]
      },
      {
        label: 'Request & Response', path: '/docs/request-response', icon: <RefreshCw className="w-3.5 h-3.5" />,
        children: [
          { label: 'Request', path: '/docs/request-response/request' },
          { label: 'Response', path: '/docs/request-response/response' },
          { label: 'Data Structures', path: '/docs/request-response/data-structures' },
          { label: 'File Uploads', path: '/docs/request-response/uploads' },
        ]
      },
      {
        label: 'Controllers', path: '/docs/controllers', icon: <Layout className="w-3.5 h-3.5" />,
        children: [
          { label: 'Overview', path: '/docs/controllers/overview' },
          { label: 'RequestCtx', path: '/docs/controllers/request-ctx' },
          { label: 'Controller Factory', path: '/docs/controllers/factory' },
          { label: 'Controller Engine', path: '/docs/controllers/engine' },
          { label: 'Controller Compiler', path: '/docs/controllers/compiler' },
          { label: 'Controller Router', path: '/docs/controllers/router' },
          { label: 'OpenAPI Generation', path: '/docs/controllers/openapi' },
          {
            label: 'Route Decorators', path: '/docs/controllers/decorators', icon: <Tag className="w-3.5 h-3.5" />,
            children: [
              { label: 'Overview', path: '/docs/controllers/decorators' },
              { label: '@GET', path: '/docs/controllers/decorators/get' },
              { label: '@POST', path: '/docs/controllers/decorators/post' },
              { label: '@PUT', path: '/docs/controllers/decorators/put' },
              { label: '@PATCH', path: '/docs/controllers/decorators/patch' },
              { label: '@DELETE', path: '/docs/controllers/decorators/delete' },
              { label: '@HEAD', path: '/docs/controllers/decorators/head' },
              { label: '@OPTIONS', path: '/docs/controllers/decorators/options' },
              { label: '@WS', path: '/docs/controllers/decorators/ws' },
              { label: '@route', path: '/docs/controllers/decorators/route' },
            ]
          },
        ]
      },
      {
        label: 'Routing', path: '/docs/routing', icon: <GitBranch className="w-3.5 h-3.5" />,
        children: [
          { label: 'Pattern Matching', path: '/docs/routing/patterns' },
          { label: 'Controller Router', path: '/docs/routing/router' },
          { label: 'URL Generation', path: '/docs/routing/urls' },
        ]
      },
    ]
  },
  {
    title: 'Dependency Injection',
    icon: <Plug className="w-3 h-3" />,
    items: [
      {
        label: 'DI System', path: '/docs/di', icon: <Box className="w-3.5 h-3.5" />,
        children: [
          { label: 'Overview', path: '/docs/di' },
          { label: 'Container', path: '/docs/di/container' },
          { label: 'Providers', path: '/docs/di/providers' },
          { label: 'Scopes', path: '/docs/di/scopes' },
          { label: 'Decorators', path: '/docs/di/decorators' },
          { label: 'Lifecycle', path: '/docs/di/lifecycle' },
          { label: 'Diagnostics', path: '/docs/di/diagnostics' },
          { label: 'Advanced', path: '/docs/di/advanced' },
        ]
      },
    ]
  },
  {
    title: 'Data Layer',
    icon: <Database className="w-3 h-3" />,
    items: [
      {
        label: 'Models (ORM)', path: '/docs/models', icon: <Database className="w-3.5 h-3.5" />,
        children: [
          { label: 'Defining Models', path: '/docs/models/defining' },
          { label: 'Fields', path: '/docs/models/fields' },
          { label: 'QuerySet API', path: '/docs/models/queryset' },
          { label: 'Relationships', path: '/docs/models/relationships' },
          { label: 'Migrations', path: '/docs/models/migrations' },
          { label: 'Signals', path: '/docs/models/signals' },
          { label: 'Transactions', path: '/docs/models/transactions' },
          { label: 'Aggregation', path: '/docs/models/aggregation' },
        ]
      },
      {
        label: 'Database Engine', path: '/docs/database', icon: <HardDrive className="w-3.5 h-3.5" />,
        children: [
          { label: 'AquiliaDatabase', path: '/docs/database/engine' },
          { label: 'SQLite Backend', path: '/docs/database/sqlite' },
          { label: 'PostgreSQL Backend', path: '/docs/database/postgresql' },
          { label: 'MySQL Backend', path: '/docs/database/mysql' },
        ]
      },
      {
        label: 'Serializers', path: '/docs/serializers', icon: <Binary className="w-3.5 h-3.5" />,
        children: [
          { label: 'Serializer', path: '/docs/serializers/base' },
          { label: 'ModelSerializer', path: '/docs/serializers/model' },
          { label: 'Fields', path: '/docs/serializers/fields' },
          { label: 'Validators', path: '/docs/serializers/validators' },
          { label: 'Relations', path: '/docs/serializers/relations' },
        ]
      },
    ]
  },
  {
    title: 'Security & Auth',
    icon: <Shield className="w-3 h-3" />,
    items: [
      {
        label: 'Authentication', path: '/docs/auth', icon: <Lock className="w-3.5 h-3.5" />,
        children: [
          { label: 'Identity Model', path: '/docs/auth/identity' },
          { label: 'Credentials', path: '/docs/auth/credentials' },
          { label: 'Auth Manager', path: '/docs/auth/manager' },
          { label: 'OAuth2 / OIDC', path: '/docs/auth/oauth' },
          { label: 'MFA', path: '/docs/auth/mfa' },
          { label: 'Guards', path: '/docs/auth/guards' },
        ]
      },
      {
        label: 'Authorization', path: '/docs/authz', icon: <Shield className="w-3.5 h-3.5" />,
        children: [
          { label: 'RBAC', path: '/docs/authz/rbac' },
          { label: 'ABAC', path: '/docs/authz/abac' },
          { label: 'Policies', path: '/docs/authz/policies' },
        ]
      },
      {
        label: 'Sessions', path: '/docs/sessions', icon: <Cog className="w-3.5 h-3.5" />,
        children: [
          { label: 'Session System', path: '/docs/sessions/overview' },
          { label: 'SessionID', path: '/docs/sessions/session-id' },
          { label: 'Stores', path: '/docs/sessions/stores' },
          { label: 'Policies', path: '/docs/sessions/policies' },
        ]
      },
    ]
  },
  {
    title: 'Middleware',
    icon: <Layers className="w-3 h-3" />,
    items: [
      {
        label: 'Middleware System', path: '/docs/middleware', icon: <Layers className="w-3.5 h-3.5" />,
        children: [
          { label: 'MiddlewareStack', path: '/docs/middleware/stack' },
          { label: 'Built-in Middleware', path: '/docs/middleware/built-in' },
          { label: 'Static Files', path: '/docs/middleware/static' },
          { label: 'CORS', path: '/docs/middleware/cors' },
          { label: 'Rate Limiting', path: '/docs/middleware/rate-limit' },
          { label: 'Security Headers', path: '/docs/middleware/security' },
        ]
      },
    ]
  },
  {
    title: 'Advanced',
    icon: <Cpu className="w-3 h-3" />,
    items: [
      {
        label: 'Aquilary Registry', path: '/docs/aquilary', icon: <Boxes className="w-3.5 h-3.5" />,
        children: [
          { label: 'Overview', path: '/docs/aquilary/overview' },
          { label: 'Manifest System', path: '/docs/aquilary/manifest' },
          { label: 'RuntimeRegistry', path: '/docs/aquilary/runtime' },
          { label: 'Fingerprinting', path: '/docs/aquilary/fingerprint' },
        ]
      },
      {
        label: 'Effects System', path: '/docs/effects', icon: <Workflow className="w-3.5 h-3.5" />,
        children: [
          { label: 'Effects & Providers', path: '/docs/effects/overview' },
          { label: 'DBTx Effect', path: '/docs/effects/dbtx' },
          { label: 'Cache Effect', path: '/docs/effects/cache' },
        ]
      },
      {
        label: 'Fault System', path: '/docs/faults', icon: <AlertCircle className="w-3.5 h-3.5" />,
        children: [
          { label: 'Fault Taxonomy', path: '/docs/faults/taxonomy' },
          { label: 'FaultEngine', path: '/docs/faults/engine' },
          { label: 'Fault Handlers', path: '/docs/faults/handlers' },
          { label: 'Fault Domains', path: '/docs/faults/domains' },
        ]
      },
      {
        label: 'Cache', path: '/docs/cache', icon: <Gauge className="w-3.5 h-3.5" />,
        children: [
          { label: 'CacheService', path: '/docs/cache/service' },
          { label: 'Backends', path: '/docs/cache/backends' },
          { label: 'Decorators', path: '/docs/cache/decorators' },
        ]
      },
      {
        label: 'WebSockets', path: '/docs/websockets', icon: <Globe className="w-3.5 h-3.5" />,
        children: [
          { label: 'Socket Controllers', path: '/docs/websockets/controllers' },
          { label: 'Runtime', path: '/docs/websockets/runtime' },
          { label: 'Adapters', path: '/docs/websockets/adapters' },
        ]
      },
      {
        label: 'Templates', path: '/docs/templates', icon: <Palette className="w-3.5 h-3.5" />,
        children: [
          { label: 'TemplateEngine', path: '/docs/templates/engine' },
          { label: 'Loaders', path: '/docs/templates/loaders' },
          { label: 'Security', path: '/docs/templates/security' },
        ]
      },
      {
        label: 'Mail', path: '/docs/mail', icon: <Mail className="w-3.5 h-3.5" />,
        children: [
          { label: 'MailService', path: '/docs/mail/service' },
          { label: 'Providers', path: '/docs/mail/providers' },
          { label: 'Templates', path: '/docs/mail/templates' },
        ]
      },
      {
        label: 'MLOps', path: '/docs/mlops', icon: <Brain className="w-3.5 h-3.5" />,
        children: [
          { label: 'Modelpack Builder', path: '/docs/mlops/modelpack' },
          { label: 'Registry', path: '/docs/mlops/registry' },
          { label: 'Serving', path: '/docs/mlops/serving' },
          { label: 'Drift Detection', path: '/docs/mlops/drift' },
        ]
      },
    ]
  },
  {
    title: 'Tooling',
    icon: <Wrench className="w-3 h-3" />,
    items: [
      {
        label: 'CLI', path: '/docs/cli', icon: <Terminal className="w-3.5 h-3.5" />,
        children: [
          { label: 'Overview', path: '/docs/cli' },
          { label: 'Core Commands', path: '/docs/cli/core' },
          { label: 'Database', path: '/docs/cli/database' },
          { label: 'MLOps', path: '/docs/cli/mlops' },
          { label: 'Inspection', path: '/docs/cli/inspection' },
          { label: 'Generators', path: '/docs/cli/generators' },
        ]
      },
      {
        label: 'Testing', path: '/docs/testing', icon: <TestTube className="w-3.5 h-3.5" />,
        children: [
          { label: 'TestClient', path: '/docs/testing/client' },
          { label: 'Test Cases', path: '/docs/testing/cases' },
          { label: 'Mocks & Fixtures', path: '/docs/testing/mocks' },
        ]
      },
      {
        label: 'OpenAPI', path: '/docs/openapi', icon: <FileCode className="w-3.5 h-3.5" />,
      },
      {
        label: 'Trace & Debug', path: '/docs/trace', icon: <BarChart className="w-3.5 h-3.5" />,
      },
    ]
  },
]

export function Sidebar() {
  const location = useLocation()
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  // State for expanded items
  // We initialize based on current location to expand relevant sections
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  useEffect(() => {
    // Determine which items should be expanded based on the current URL
    const openItems: Record<string, boolean> = {}

    // Better approach: simply expand everything that is a prefix of current path
    sections.forEach(section => {
      const crawl = (items: SidebarItem[]) => {
        items.forEach(item => {
          if (item.children) {
            // If the current location starts with this item's path, expand it
            // Exception: if path is just prefix for children but not exact match... logic holds.
            if (location.pathname.startsWith(item.path)) {
              openItems[item.path] = true
            }
            crawl(item.children)
          }
        })
      }
      crawl(section.items)
    })

    setExpanded(prev => ({ ...prev, ...openItems }))
  }, [location.pathname])


  const toggleExpand = (e: React.MouseEvent, path: string) => {
    e.preventDefault()
    setExpanded(prev => ({ ...prev, [path]: !prev[path] }))
  }

  const isActive = (path: string) => location.pathname === path
  const isChildActive = (path: string) => location.pathname.startsWith(path) && location.pathname !== path

  // Recursive Item Component
  const SidebarMenuItem = ({ item, depth = 0 }: { item: SidebarItem, depth?: number }) => {
    const hasChildren = item.children && item.children.length > 0
    const isExpanded = expanded[item.path]
    const active = isActive(item.path)
    const childActive = isChildActive(item.path)

    // If it has children, it's a collapsible parent
    if (hasChildren) {
      return (
        <li>
          <button
            onClick={(e) => toggleExpand(e, item.path)}
            className={`w-full group flex items-center justify-between py-2 rounded-lg text-sm transition-all ${depth === 0 ? 'px-3' : 'pl-4 pr-3'} ${active
              ? 'sidebar-link-active'
              : childActive
                ? `font-medium ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`
                : `${isDark ? 'text-gray-400 hover:text-white hover:bg-white/5' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`
              }`}
            style={{
              paddingLeft: depth > 0 ? `${depth * 16 + 12}px` : undefined,
              borderLeft: childActive && depth === 0 ? `2px solid ${isDark ? '#60a5fa' : '#3b82f6'}` : undefined
            }}
          >
            <span className="flex items-center gap-2">
              {item.icon && item.icon}
              {item.label}
            </span>
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
          </button>

          {isExpanded && (
            <ul className={`space-y-0.5 mt-1 border-l ml-5 ${isDark ? 'border-white/10' : 'border-gray-200'}`} style={{ marginLeft: depth > 0 ? `${depth * 16 + 20}px` : '20px' }}>
              {item.children!.map(child => (
                <SidebarMenuItem key={child.path} item={child} depth={depth + 1} />
              ))}
            </ul>
          )}
        </li>
      )
    }

    // Leaf node
    return (
      <li>
        <Link
          to={item.path}
          className={`block py-1.5 text-sm rounded-r-lg transition-all ${active
            ? `font-medium border-l-2 -ml-px ${isDark ? 'text-aquilia-400 border-aquilia-500' : 'text-aquilia-600 border-aquilia-600'}`
            : `${isDark ? 'text-gray-500 hover:text-white' : 'text-gray-500 hover:text-gray-800'}`
            }`}
          style={{ paddingLeft: '16px' }} // Standard indent for list items inside the border-l
        >
          <span className="flex items-center gap-2">
            {item.icon && item.icon}
            {item.label}
          </span>
        </Link>
      </li>
    )
  }

  // Root level item wrapper to handle top-level styling differences
  const RootItem = ({ item }: { item: SidebarItem }) => {
    const hasChildren = item.children && item.children.length > 0
    const isExpanded = expanded[item.path]
    const active = isActive(item.path)
    const childActive = isChildActive(item.path)

    if (hasChildren) {
      return (
        <li>
          <button
            onClick={(e) => toggleExpand(e, item.path)}
            className={`w-full group flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all ${active
              ? 'sidebar-link-active'
              : childActive
                ? `font-medium border-l-2 -ml-px ${isDark ? 'text-white border-aquilia-500' : 'text-gray-900 border-aquilia-600'}`
                : `${isDark ? 'text-gray-400 hover:text-white hover:bg-white/5' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`
              }`}
          >
            <span className="flex items-center gap-2">
              {item.icon && item.icon}
              {item.label}
            </span>
            {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </button>
          {isExpanded && (
            <ul className={`ml-5 mt-1 space-y-0.5 border-l ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              {item.children!.map(child => (
                <SidebarMenuItem key={child.path} item={child} depth={0} />
              ))}
            </ul>
          )}
        </li>
      )
    }

    return (
      <li>
        <Link
          to={item.path}
          className={`group flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${active
            ? 'sidebar-link-active'
            : `${isDark ? 'text-gray-400 hover:text-white hover:bg-white/5' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`
            }`}
        >
          {item.icon && item.icon}
          {item.label}
        </Link>
      </li>
    )
  }

  return (
    <div className={`lg:w-72 flex-shrink-0 border-b lg:border-b-0 lg:border-r ${isDark ? 'border-white/10 bg-black/30' : 'border-gray-200 bg-white/50'} backdrop-blur-xl`}>
      <div className="sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto pt-6 pb-12 px-4">
        {/* SDK Badge */}
        <div className="relative group mb-6">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-aquilia-500 to-blue-500 rounded-xl blur opacity-20 group-hover:opacity-40 transition" />
          <div className={`relative flex items-center gap-3 px-4 py-3 rounded-xl border ${isDark ? 'bg-zinc-900/90 border-white/10' : 'bg-white border-gray-200'}`}>
            <img src="/logo.png" alt="Aquilia" className="w-8 h-8 rounded-lg shadow-lg shadow-aquilia-500/20" />
            <div>
              <div className={`font-bold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>Aquilia Framework</div>
              <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>v0.2.0 • Latest</div>
            </div>
          </div>
        </div>

        <nav className="space-y-6">
          {sections.map(section => (
            <div key={section.title}>
              <h4 className={`text-xs font-bold uppercase tracking-wider mb-3 px-3 flex items-center gap-2 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                {section.icon}
                {section.title}
              </h4>
              <ul className="space-y-0.5">
                {section.items.map(item => (
                  <RootItem key={item.path} item={item} />
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </div>
    </div>
  )
}
