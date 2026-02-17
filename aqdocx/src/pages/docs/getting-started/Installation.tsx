import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowRight, Package, AlertCircle, CheckCircle } from 'lucide-react'

export function InstallationPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const Note = ({ children }: { children: React.ReactNode }) => (
    <div className={`flex gap-3 p-4 rounded-xl border mb-6 ${isDark ? 'bg-aquilia-500/5 border-aquilia-500/20' : 'bg-aquilia-50 border-aquilia-200'}`}>
      <AlertCircle className="w-5 h-5 text-aquilia-500 shrink-0 mt-0.5" />
      <div className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{children}</div>
    </div>
  )

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Package className="w-4 h-4" />
          Getting Started
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Installation
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Get Aquilia installed and ready for development in just a few steps.
        </p>
      </div>

      {/* Requirements */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Requirements</h2>
        <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <ul className="space-y-3">
            {[
              { label: 'Python 3.10+', note: 'Aquilia uses modern Python features including type unions, match statements, and async generators.' },
              { label: 'pip or Poetry', note: 'Any Python package manager works. pip is shown in examples.' },
              { label: 'Virtual Environment', note: 'Strongly recommended. Use venv, conda, or poetry environments.' },
            ].map((req, i) => (
              <li key={i} className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-aquilia-500 shrink-0 mt-0.5" />
                <div>
                  <span className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{req.label}</span>
                  <span className={`text-sm ml-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>— {req.note}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Install with pip */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Install with pip</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The recommended way to install Aquilia is using pip in a virtual environment:
        </p>
        <CodeBlock language="bash" filename="Terminal">{`# Create a virtual environment
python -m venv env
source env/bin/activate  # Linux/macOS
# env\\Scripts\\activate   # Windows

# Install Aquilia
pip install aquilia`}</CodeBlock>

        <Note>
          <p>Aquilia will install its core dependencies automatically including <code className="text-aquilia-500">uvicorn</code>, <code className="text-aquilia-500">jinja2</code>, <code className="text-aquilia-500">aiosqlite</code>, and others.</p>
        </Note>
      </section>

      {/* Install from source */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Install from Source</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          To install the latest development version directly from GitHub:
        </p>
        <CodeBlock language="bash" filename="Terminal">{`# Clone the repository
git clone https://github.com/axiomchronicles/Aquilia.git
cd Aquilia

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"`}</CodeBlock>
      </section>

      {/* Optional Dependencies */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Optional Dependencies</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia has optional extras for specific backends and features:
        </p>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Extra</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Packages</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { extra: 'postgres', pkgs: 'asyncpg, psycopg2', desc: 'PostgreSQL database backend' },
                { extra: 'mysql', pkgs: 'aiomysql', desc: 'MySQL/MariaDB database backend' },
                { extra: 'redis', pkgs: 'aioredis', desc: 'Redis cache and session backend' },
                { extra: 'mail', pkgs: 'aiosmtplib', desc: 'SMTP mail provider' },
                { extra: 'mlops', pkgs: 'numpy, scikit-learn', desc: 'MLOps model serving and drift detection' },
                { extra: 'dev', pkgs: 'pytest, coverage, black', desc: 'Development and testing tools' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.extra}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.pkgs}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock language="bash" filename="Terminal">{`# Install with PostgreSQL and Redis support
pip install "aquilia[postgres,redis]"

# Install everything
pip install "aquilia[postgres,mysql,redis,mail,mlops,dev]"`}</CodeBlock>
      </section>

      {/* Verify Installation */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Verify Installation</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Verify that Aquilia is installed correctly:
        </p>
        <CodeBlock language="bash" filename="Terminal">{`python -c "import aquilia; print(aquilia.__version__)"
# Output: 0.2.0`}</CodeBlock>
        <p className={`mt-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Or use the CLI to check:
        </p>
        <CodeBlock language="bash" filename="Terminal">{`aquilia --version`}</CodeBlock>
      </section>

      {/* Next Steps */}
      <section>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link to="/docs/quickstart" className={`flex-1 group p-6 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
            <h3 className={`font-bold mb-2 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Quick Start <ArrowRight className="w-4 h-4 text-aquilia-500 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
            </h3>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Build your first Aquilia application</p>
          </Link>
          <Link to="/docs/architecture" className={`flex-1 group p-6 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
            <h3 className={`font-bold mb-2 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Architecture <ArrowRight className="w-4 h-4 text-aquilia-500 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
            </h3>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Understand how Aquilia is structured</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
