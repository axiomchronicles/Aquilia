import { useTheme } from '../../../context/ThemeContext'
import { AlertTriangle } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function FaultsDomains() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <AlertTriangle className="w-4 h-4" />
          Faults / Domain Reference
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Fault Domain Reference
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Complete reference of all built-in fault codes organized by domain. Each fault has a unique code, default severity, and structured context.
        </p>
      </div>

      {/* Model Domain */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Model Domain</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Fault Code</th>
                <th className="py-3 px-4 text-left font-semibold">Severity</th>
                <th className="py-3 px-4 text-left font-semibold">HTTP</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['MODEL_NOT_FOUND', 'ERROR', '404', 'Query returned no results'],
                ['MODEL_ALREADY_EXISTS', 'ERROR', '409', 'Unique constraint violation'],
                ['MODEL_VALIDATION_ERROR', 'ERROR', '422', 'Field-level model validation failed'],
                ['MODEL_INTEGRITY_ERROR', 'ERROR', '409', 'Foreign key / check constraint violation'],
                ['MODEL_DEADLOCK', 'WARNING', '503', 'Database deadlock detected (retryable)'],
                ['MODEL_CONNECTION_ERROR', 'CRITICAL', '503', 'Cannot connect to database'],
                ['MODEL_MIGRATION_ERROR', 'CRITICAL', '500', 'Migration file invalid or conflicting'],
                ['MODEL_SCHEMA_MISMATCH', 'ERROR', '500', 'Runtime schema differs from migration'],
                ['MODEL_QUERY_ERROR', 'ERROR', '500', 'Invalid query construction'],
              ].map(([code, sev, http, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{code}</td>
                  <td className={`py-2.5 px-4 font-mono text-xs ${sev === 'CRITICAL' ? 'text-red-400' : sev === 'WARNING' ? 'text-yellow-400' : 'text-orange-400'}`}>{sev}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{http}</td>
                  <td className="py-2.5 px-4 text-xs">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Serializer Domain */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Serializer Domain</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Fault Code</th>
                <th className="py-3 px-4 text-left font-semibold">HTTP</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['VALIDATION_ERROR', '422', 'One or more fields failed validation'],
                ['REQUIRED_FIELD', '422', 'Required field missing from input'],
                ['INVALID_TYPE', '422', 'Field value has wrong type'],
                ['UNIQUE_VIOLATION', '409', 'UniqueValidator constraint failed'],
              ].map(([code, http, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{code}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{http}</td>
                  <td className="py-2.5 px-4 text-xs">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Security Domain */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Security Domain</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Fault Code</th>
                <th className="py-3 px-4 text-left font-semibold">HTTP</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['AUTH_REQUIRED', '401', 'No credentials provided'],
                ['AUTH_INVALID', '401', 'Credentials invalid or expired'],
                ['AUTH_FORBIDDEN', '403', 'Authenticated but not authorized'],
                ['CSRF_VIOLATION', '403', 'CSRF token missing or invalid'],
                ['CORS_REJECTED', '403', 'Origin not in allowed list'],
                ['RATE_LIMITED', '429', 'Too many requests (includes Retry-After)'],
              ].map(([code, http, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{code}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{http}</td>
                  <td className="py-2.5 px-4 text-xs">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Cache Domain */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Cache Domain</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Fault Code</th>
                <th className="py-3 px-4 text-left font-semibold">HTTP</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['CACHE_MISS', '—', 'Key not found (usually silent)'],
                ['CACHE_BACKEND_ERROR', '503', 'Backend unreachable'],
                ['CACHE_SERIALIZATION_ERROR', '500', 'Value cannot be serialized'],
                ['CACHE_KEY_ERROR', '400', 'Invalid cache key format'],
                ['CACHE_TTL_EXPIRED', '—', 'Entry expired (informational)'],
              ].map(([code, http, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{code}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{http}</td>
                  <td className="py-2.5 px-4 text-xs">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    
      <NextSteps />
    </div>
  )
}