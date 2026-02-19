import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Download, Terminal, AlertCircle, CheckCircle, Package } from 'lucide-react'

export function InstallationPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Download className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                Installation
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Set up Aquilia in your Python environment</p>
          </div>
        </div>
      </div>

      {/* Requirements */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>System Requirements</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className={`p-5 rounded-xl border ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-white border-gray-200'}`}>
            <div className="flex items-center gap-3 mb-3">
              <div className={`p-2 rounded-lg ${isDark ? 'bg-blue-500/20 text-blue-400' : 'bg-blue-50 text-blue-600'}`}>
                <Terminal className="w-5 h-5" />
              </div>
              <h3 className={`font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Python Environment</h3>
            </div>
            <ul className={`space-y-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              <li className="flex justify-between items-center bg-zinc-500/5 p-2 rounded-lg">
                <span>Minimum Version</span>
                <span className={`font-mono font-bold ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>3.11</span>
              </li>
              <li className="flex justify-between items-center bg-aquilia-500/10 p-2 rounded-lg border border-aquilia-500/20">
                <span className="text-aquilia-500 font-medium">Recommended</span>
                <span className="font-mono font-bold text-aquilia-500">3.12+</span>
              </li>
            </ul>
            <p className={`text-xs mt-3 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              Aquilia heavily uses modern asyncio features and type hints introduced in recent Python versions.
            </p>
          </div>

          <div className={`p-5 rounded-xl border ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-white border-gray-200'}`}>
            <div className="flex items-center gap-3 mb-3">
              <div className={`p-2 rounded-lg ${isDark ? 'bg-purple-500/20 text-purple-400' : 'bg-purple-50 text-purple-600'}`}>
                <Package className="w-5 h-5" />
              </div>
              <h3 className={`font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Operating System</h3>
            </div>
            <ul className={`space-y-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              <li className="flex items-center gap-3 p-2">
                <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
                <span><strong>macOS / Linux</strong> (Preferred)</span>
              </li>
              <li className="flex items-center gap-3 p-2">
                <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
                <span><strong>Windows</strong> via WSL2</span>
              </li>
              <li className="flex items-center gap-3 p-2 opacity-75">
                <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
                <span>Native Windows (Limited Support)</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Install from PyPI */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Install from PyPI</h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The core package installs the framework, ASGI server (uvicorn), and CLI:
        </p>

        <CodeBlock code={`pip install aquilia`} language="bash" />

        <p className={`mt-4 mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Or with <strong>uv</strong> (recommended for faster installs):
        </p>

        <CodeBlock code={`uv pip install aquilia`} language="bash" />
      </section>

      {/* Extras */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Optional Extras</h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia uses optional dependencies for specialized subsystems. Install only what you need:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Extra</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Installs</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>When to Use</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['redis', 'redis[hiredis]', 'Redis cache backend, Redis session store, Redis socket adapter'],
                ['postgres', 'asyncpg, psycopg2-binary', 'PostgreSQL database backend'],
                ['mysql', 'aiomysql', 'MySQL database backend'],
                ['mail', 'aiosmtplib, boto3', 'SMTP email, AWS SES provider'],
                ['templates', 'jinja2', 'Jinja2 template engine (auto-installed)'],
                ['auth', 'pyjwt, cryptography, argon2-cffi', 'JWT tokens, RS256, Argon2 hashing'],
                ['mlops', 'numpy, scikit-learn', 'MLOps model packaging and drift detection'],
                ['dev', 'pytest, httpx, coverage', 'Development and testing tools'],
                ['all', '(all of the above)', 'Full installation for production'],
              ].map(([extra, installs, when], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>aquilia[{extra}]</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{installs}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{when}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <CodeBlock code={`# Install with multiple extras
pip install "aquilia[redis,postgres,auth]"

# Install everything
pip install "aquilia[all]"`} language="bash" />
      </section>

      {/* Development Install */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Development Install (From Source)</h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          To contribute to Aquilia or test against the latest changes:
        </p>

        <CodeBlock
          code={`git clone https://github.com/your-org/aquilia.git
cd aquilia
python -m venv env
source env/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
pip install -r requirements-dev.txt

# Verify the installation
aq version`}
          language="bash"
        />
      </section>

      {/* Verify */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Verify Installation</h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          After installation, verify that the CLI (<code>aq</code>, also accessible as <code>aquilate</code>) is available:
        </p>

        <CodeBlock
          code={`$ aq version
Aquilia v1.0.0

$ aq doctor
✓ Python 3.12.3 (compatible)
✓ aquilia package installed
✓ CLI entry point registered
✓ uvicorn available
✓ jinja2 available
…`}
          language="bash"
        />

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>aq doctor</code> command checks your environment for common issues — missing optional
          dependencies, incompatible Python versions, and misconfigured workspace files.
        </p>
      </section>

      {/* CLI entry point */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>CLI Entry Points</h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The package registers two console scripts (both identical):
        </p>

        <div className={`rounded-xl border p-4 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
          <ul className={`space-y-2 text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
            <li className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-aquilia-400" />
              <code className="font-mono">aq</code> — Short form (recommended)
            </li>
            <li className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-aquilia-400" />
              <code className="font-mono">aquilate</code> — Long form
            </li>
            <li className="flex items-center gap-2">
              <Package className="w-4 h-4 text-aquilia-400" />
              <code className="font-mono">python -m aquilia.cli</code> — Module invocation (if entry points are broken)
            </li>
          </ul>
        </div>
      </section>

      {/* Troubleshooting */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Troubleshooting</h2>

        <div className="space-y-4">
          <div className={`rounded-xl border p-4 ${isDark ? 'bg-amber-500/10 border-amber-500/20' : 'bg-amber-50 border-amber-200'}`}>
            <div className="flex items-start gap-2">
              <AlertCircle className={`w-4 h-4 mt-0.5 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
              <div>
                <p className={`font-semibold text-sm ${isDark ? 'text-amber-300' : 'text-amber-800'}`}><code>aq: command not found</code></p>
                <p className={`text-sm mt-1 ${isDark ? 'text-amber-200/80' : 'text-amber-700'}`}>
                  Ensure your Python scripts directory is in <code>$PATH</code>. For virtual environments,
                  make sure the venv is activated. Alternatively use <code>python -m aquilia.cli</code>.
                </p>
              </div>
            </div>
          </div>

          <div className={`rounded-xl border p-4 ${isDark ? 'bg-amber-500/10 border-amber-500/20' : 'bg-amber-50 border-amber-200'}`}>
            <div className="flex items-start gap-2">
              <AlertCircle className={`w-4 h-4 mt-0.5 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
              <div>
                <p className={`font-semibold text-sm ${isDark ? 'text-amber-300' : 'text-amber-800'}`}><code>ModuleNotFoundError: No module named 'click'</code></p>
                <p className={`text-sm mt-1 ${isDark ? 'text-amber-200/80' : 'text-amber-700'}`}>
                  Click is a core dependency. Reinstall with <code>pip install aquilia --force-reinstall</code>.
                  If using a locked environment, ensure <code>click</code> and <code>pyyaml</code> are included.
                </p>
              </div>
            </div>
          </div>

          <div className={`rounded-xl border p-4 ${isDark ? 'bg-amber-500/10 border-amber-500/20' : 'bg-amber-50 border-amber-200'}`}>
            <div className="flex items-start gap-2">
              <AlertCircle className={`w-4 h-4 mt-0.5 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
              <div>
                <p className={`font-semibold text-sm ${isDark ? 'text-amber-300' : 'text-amber-800'}`}>Python version incompatibility</p>
                <p className={`text-sm mt-1 ${isDark ? 'text-amber-200/80' : 'text-amber-700'}`}>
                  Aquilia requires Python 3.11 or newer. Check with <code>python --version</code>.
                  If you have multiple Python versions installed, use <code>python3.12 -m pip install aquilia</code>.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Next Steps */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Next Steps</h2>
        <div className="flex flex-col gap-2">
          <Link to="/docs/quickstart" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → Quick Start: Build your first API
          </Link>
          <Link to="/docs/cli/commands" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → CLI Commands: Full command reference
          </Link>
          <Link to="/docs/project-structure" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → Project Structure: Understand the workspace layout
          </Link>
        </div>
      </section>
    </div>
  )
}
