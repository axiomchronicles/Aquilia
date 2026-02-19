import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Terminal } from 'lucide-react'

export function CLICommands() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Terminal className="w-4 h-4" />
          CLI / Commands
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            CLI Commands
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-400">aq</code> command-line tool provides project scaffolding, development server, module management, migration, and inspection utilities.
        </p>
      </div>

      {/* Command Reference */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Command Reference</h2>
        <div className="space-y-6">
          {[
            { cmd: 'aq init', desc: 'Initialize a new Aquilia project', usage: 'aq init myproject --template=api', details: 'Creates project directory with starter.py, config/, modules/, and pyproject.toml. Templates: api, web, minimal, full.' },
            { cmd: 'aq add', desc: 'Add a module to the project', usage: 'aq add users --with-models --with-auth', details: 'Generates module directory with controller, models, serializers, manifest, and tests. Flags: --with-models, --with-auth, --with-templates, --with-websockets.' },
            { cmd: 'aq serve', desc: 'Start the development server', usage: 'aq serve --reload --port 8000', details: 'Starts AquiliaServer with auto-reload. Options: --host, --port, --workers, --reload, --no-debug.' },
            { cmd: 'aq run', desc: 'Run a custom management command', usage: 'aq run seed_db --count 100', details: 'Executes a custom command registered via @cli_command decorator.' },
            { cmd: 'aq validate', desc: 'Validate project manifests', usage: 'aq validate', details: 'Runs RegistryValidator on all module manifests. Reports errors, warnings, and dependency graph.' },
            { cmd: 'aq compile', desc: 'Compile templates and assets', usage: 'aq compile --optimize', details: 'Pre-compiles Jinja2 templates to bytecode. Optimizes static asset references.' },
            { cmd: 'aq freeze', desc: 'Freeze manifest for production', usage: 'aq freeze', details: 'Generates .aquilia/frozen_manifest.json with registry fingerprint for immutable deployments.' },
            { cmd: 'aq inspect', desc: 'Inspect the dependency graph', usage: 'aq inspect --format=svg', details: 'Outputs DI graph, route table, or middleware stack. Formats: text, json, svg, dot.' },
            { cmd: 'aq migrate', desc: 'Run database migrations', usage: 'aq migrate --target=latest', details: 'Applies pending migrations. Options: --target, --dry-run, --show-sql, --rollback.' },
            { cmd: 'aq makemigrations', desc: 'Generate migrations from model changes', usage: 'aq makemigrations --name="add_email_field"', details: 'Diffs current models against migration state and generates migration files.' },
          ].map((c, i) => (
            <div key={i} className={box}>
              <div className="flex items-center gap-3 mb-2">
                <h3 className={`font-mono font-bold text-sm ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{c.cmd}</h3>
                <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{c.desc}</span>
              </div>
              <CodeBlock language="bash" filename="terminal">{c.usage}</CodeBlock>
              <p className={`mt-3 text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{c.details}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
