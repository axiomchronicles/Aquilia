import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Terminal, Box, Play, Server, CheckCircle2, FileCode, Wrench } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function CLICoreCommands() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    // Styles
    const sectionClass = "mb-16 scroll-mt-24"
    const h2Class = `text-2xl font-bold mb-6 flex items-center gap-3 ${isDark ? 'text-white' : 'text-gray-900'}`
    const h3Class = `text-lg font-semibold mt-8 mb-3 ${isDark ? 'text-gray-200' : 'text-gray-800'}`
    const pClass = `mb-4 leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`
    const codeClass = "text-xs font-mono bg-black/5 dark:bg-white/10 px-1.5 py-0.5 rounded text-aquilia-600 dark:text-aquilia-400"

    const Table = ({ children }: { children: React.ReactNode }) => (
        <div className={`overflow-hidden border rounded-lg mb-6 ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
            <table className="w-full text-sm text-left">
                <thead className={`text-xs uppercase ${isDark ? 'bg-white/5 text-gray-400' : 'bg-gray-50 text-gray-500'}`}>
                    <tr>
                        <th className="px-4 py-3 font-medium">Option</th>
                        <th className="px-4 py-3 font-medium">Description</th>
                        <th className="px-4 py-3 font-medium w-32">Default</th>
                    </tr>
                </thead>
                <tbody className={`divide-y ${isDark ? 'divide-white/10' : 'divide-gray-200'}`}>
                    {children}
                </tbody>
            </table>
        </div>
    )

    const Row = ({ opt, desc, def }: { opt: string, desc: string, def?: string }) => (
        <tr className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
            <td className="px-4 py-3 font-mono text-aquilia-500">{opt}</td>
            <td className={`px-4 py-3 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>{desc}</td>
            <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{def || '-'}</td>
        </tr>
    )

    return (
        <div className="max-w-4xl mx-auto pb-20">
            {/* Header */}
            <div className="mb-12 border-b border-gray-200 dark:border-white/10 pb-8">
                <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
                    <Terminal className="w-4 h-4" />
                    CLI / Core Commands
                </div>
                <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                    Core Commands
                    <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
                  </span>
                </h1>
                <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Primary commands for the Aquilia lifecycle: project creation, module management, running servers, testing, and building for production.
                </p>
            </div>

            {/* Init */}
            <section id="init" className={sectionClass}>
                <h2 className={h2Class}><Box className="w-6 h-6 text-purple-500" /> Project Initialization</h2>
                <p className={pClass}>
                    The <span className={codeClass}>init</span> command creates a new Aquilia workspace with a standardized directory structure.
                </p>

                <CodeBlock language="bash" filename="terminal">
                    aq init workspace [NAME] [OPTIONS]
                </CodeBlock>

                <h3 className={h3Class}>Options</h3>
                <Table>
                    <Row opt="--template, -t" desc="Project template (api, service, monolith)" def="api" />
                    <Row opt="--minimal" desc="Skip generating example modules" def="false" />
                    <Row opt="--no-input" desc="Disable interactive prompts" def="false" />
                    <Row opt="--dry-run" desc="Preview file generation without writing" def="false" />
                </Table>

                <h3 className={h3Class}>Examples</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`# Create a standard API workspace
aq init workspace my-api

# Create a minimal microservice without examples
aq init workspace payment-service --minimal --template=service

# Non-interactive mode for scripts
aq init workspace ci-project --no-input`}
                </CodeBlock>
            </section>

            {/* Add */}
            <section id="add" className={sectionClass}>
                <h2 className={h2Class}><FileCode className="w-6 h-6 text-blue-500" /> Add Components</h2>
                <p className={pClass}>
                    The <span className={codeClass}>add</span> command generates modules, packages, and other structural components.
                </p>

                <CodeBlock language="bash" filename="terminal">
                    aq add module [NAME] [OPTIONS]
                </CodeBlock>

                <h3 className={h3Class}>Options</h3>
                <Table>
                    <Row opt="--depends-on" desc="Declare dependency on another module (repeatable)" />
                    <Row opt="--fault-domain" desc="Assign to specific fault isolation domain" />
                    <Row opt="--route-prefix" desc="Custom URL prefix for module routes" />
                    <Row opt="--with-tests" desc="Generate test scaffolding" def="false" />
                    <Row opt="--package" desc="Add as a Python package instead of Aquilia module" def="false" />
                    <Row opt="--no-docker" desc="Skip generating Dockerfile/compose" def="false" />
                </Table>

                <h3 className={h3Class}>Examples</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`# Add a 'users' module
aq add module users

# Add 'orders' module depending on 'users' and 'inventory'
aq add module orders --depends-on=users --depends-on=inventory

# Add with custom routing and fault isolation
aq add module payments --route-prefix=/v1/pay --fault-domain=PAYMENT_GATEWAY`}
                </CodeBlock>
            </section>

            {/* Generate */}
            <section id="generate" className={sectionClass}>
                <h2 className={h2Class}><FileCode className="w-6 h-6 text-cyan-500" /> Scaffolding</h2>
                <p className={pClass}>
                    The <span className={codeClass}>generate</span> command creates individual code components like controllers from templates.
                </p>

                <CodeBlock language="bash" filename="terminal">
                    aq generate controller [NAME] [OPTIONS]
                </CodeBlock>

                <h3 className={h3Class}>Options</h3>
                <Table>
                    <Row opt="--prefix" desc="Custom route prefix" def="/name" />
                    <Row opt="--resource" desc="Resource name for CRUD (e.g. 'User')" def="name" />
                    <Row opt="--simple" desc="Generate minimal 'Hello World' controller" def="false" />
                    <Row opt="--with-lifecycle" desc="Include on_startup/request/response hooks" def="false" />
                    <Row opt="--test" desc="Generate a demo controller with auth/session examples" def="false" />
                    <Row opt="--output" desc="Output directory" def="controllers" />
                </Table>

                <h3 className={h3Class}>Examples</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`# Generate standard CRUD controller
aq generate controller Products

# Generate minimal controller with custom route
aq generate controller Health --simple --prefix=/health

# Generate demo controller with auth/session examples
aq generate controller Demo --test`}
                </CodeBlock>
            </section>

            {/* Manifest */}
            <section id="manifest" className={sectionClass}>
                <h2 className={h2Class}><FileCode className="w-6 h-6 text-pink-500" /> Manifest Management</h2>
                <p className={pClass}>
                    The <span className={codeClass}>manifest</span> command helps keep your <span className={codeClass}>manifest.py</span> files in sync with your codebase.
                </p>

                <CodeBlock language="bash" filename="terminal">
                    aq manifest update [MODULE] [OPTIONS]
                </CodeBlock>

                <h3 className={h3Class}>Options</h3>
                <Table>
                    <Row opt="--check" desc="Fail if manifest is out of sync (for CI)" def="false" />
                    <Row opt="--freeze" desc="Disable auto-discovery after update" def="false" />
                </Table>

                <h3 className={h3Class}>Examples</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`# Scan module and update manifest.py with found controllers/services
aq manifest update users

# CI check - fail if manifest is outdated
aq manifest update users --check

# Freeze manifest (explicit registration only)
aq manifest update users --freeze`}
                </CodeBlock>
            </section>

            {/* Run */}
            <section id="run" className={sectionClass}>
                <h2 className={h2Class}><Play className="w-6 h-6 text-green-500" /> Development Server</h2>
                <p className={pClass}>
                    <span className={codeClass}>aq run</span> starts the development server with hot-reloading, debug toolbar, and rich logging.
                </p>

                <CodeBlock language="bash" filename="terminal">
                    aq run [OPTIONS]
                </CodeBlock>

                <h3 className={h3Class}>Options</h3>
                <Table>
                    <Row opt="--host" desc="Bind host address" def="127.0.0.1" />
                    <Row opt="--port, -p" desc="Bind port" def="8000" />
                    <Row opt="--reload / --no-reload" desc="Enable/disable hot-reloading" def="true" />
                    <Row opt="--workers, -w" desc="Number of worker processes" def="1" />
                    <Row opt="--env-file" desc="Path to .env file" def=".env" />
                    <Row opt="--mode" desc="Runtime mode (dev, test, prod)" def="dev" />
                    <Row opt="--log-level" desc="Logging verbosity (debug, info, warning, error)" def="info" />
                </Table>
            </section>

            {/* Test */}
            <section id="test" className={sectionClass}>
                <h2 className={h2Class}><CheckCircle2 className="w-6 h-6 text-teal-500" /> Testing</h2>
                <p className={pClass}>
                    <span className={codeClass}>aq test</span> runs the pytest suite with Aquilia-aware configuration (auto-loading `test` environment).
                </p>

                <CodeBlock language="bash" filename="terminal">
                    aq test [PATHS] [OPTIONS]
                </CodeBlock>

                <h3 className={h3Class}>Options</h3>
                <Table>
                    <Row opt="--pattern, -k" desc="Run tests matching pattern string" />
                    <Row opt="--markers, -m" desc="Run tests matching markers" />
                    <Row opt="--coverage" desc="Collect code coverage calculation" def="false" />
                    <Row opt="--coverage-html" desc="Generate HTML coverage report" def="false" />
                    <Row opt="--failfast, -x" desc="Stop immediately on first failure" def="false" />
                </Table>

                <h3 className={h3Class}>Examples</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`# Run all tests
aq test

# Run specific test file
aq test tests/test_users.py

# Run tests matching "login" and stop on error
aq test -k "login" -x

# Generate coverage report
aq test --coverage-html`}
                </CodeBlock>
            </section>

            {/* Diagnostics */}
            <section id="diagnostics" className={sectionClass}>
                <h2 className={h2Class}><Wrench className="w-6 h-6 text-orange-500" /> Diagnostics</h2>

                <h3 className={h3Class}>Doctor</h3>
                <p className={pClass}>Checks workspace health, dependencies, and configuration integrity.</p>
                <CodeBlock language="bash" filename="terminal">aq doctor [--fix]</CodeBlock>

                <h3 className={h3Class}>Validate</h3>
                <p className={pClass}>Static analysis of module manifests, imports, and circular dependencies.</p>
                <CodeBlock language="bash" filename="terminal">aq validate [--strict] [--module=NAME]</CodeBlock>
            </section>

            {/* Build / Production */}
            <section id="production" className={sectionClass}>
                <h2 className={h2Class}><Server className="w-6 h-6 text-indigo-500" /> Production Build</h2>

                <h3 className={h3Class}>Compile</h3>
                <p className={pClass}>
                    Compiles workspace configuration and manifests into optimized artifacts for production.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq compile --output=dist/ [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--output, -o" desc="Output directory" def="dist" />
                    <Row opt="--watch" desc="Recompile on change" def="false" />
                    <Row opt="--clean" desc="Clean output directory before build" def="false" />
                </Table>

                <h3 className={h3Class}>Freeze</h3>
                <p className={pClass}>
                    Creates a cryptographically signed, immutable bundle of the compiled application.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq freeze --sign [KEY_PATH]
                </CodeBlock>

                <h3 className={h3Class}>Serve</h3>
                <p className={pClass}>
                    Starts the optimized production server. Requires compiled artifacts.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq serve [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--bind, -b" desc="Bind address (host:port)" def="0.0.0.0:8000" />
                    <Row opt="--workers, -w" desc="Number of worker processes" def="auto" />
                    <Row opt="--timeout" desc="Worker timeout in seconds" def="30" />
                </Table>
            </section>
        
      <NextSteps />
    </div>
    )
}