import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Info, BarChart2, Search, Layers, Archive } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function CLIInspectionCommands() {
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
                    <Info className="w-4 h-4" />
                    CLI / Inspection
                </div>
                <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                    Inspection & Discovery
                    <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
                  </span>
                </h1>
                <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Deep-dive tools to analyze workspace state, trace runtime behavior, manage artifacts, and debug subsystem configurations.
                </p>
            </div>

            {/* Inspect */}
            <section id="inspect" className={sectionClass}>
                <h2 className={h2Class}><Search className="w-6 h-6 text-aquilia-500" /> Static Inspection</h2>
                <p className={pClass}>
                    The <span className={codeClass}>inspect</span> command reveals the compiled state of your application without running it.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq inspect [TARGET]
                </CodeBlock>

                <h3 className={h3Class}>Targets</h3>
                <ul className={`grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    <li className="flex items-start gap-2"><span className="font-mono text-aquilia-500">routes</span> <span>List all compiled URI routes and handlers</span></li>
                    <li className="flex items-start gap-2"><span className="font-mono text-aquilia-500">di</span> <span>Visualize the Dependency Injection graph</span></li>
                    <li className="flex items-start gap-2"><span className="font-mono text-aquilia-500">modules</span> <span>List detected modules and metadata</span></li>
                    <li className="flex items-start gap-2"><span className="font-mono text-aquilia-500">faults</span> <span>Show fault domain boundaries</span></li>
                    <li className="flex items-start gap-2"><span className="font-mono text-aquilia-500">config</span> <span>View fully resolved configuration</span></li>
                </ul>
            </section>

            {/* Trace */}
            <section id="trace" className={sectionClass}>
                <h2 className={h2Class}><Layers className="w-6 h-6 text-indigo-500" /> Runtime Trace</h2>
                <p className={pClass}>
                    Interact with the <span className={codeClass}>.aquilia/</span> trace directory to debug running or past server instances.
                </p>

                <h3 className={h3Class}>Status</h3>
                <CodeBlock language="bash" filename="terminal">
                    aq trace status [--json]
                </CodeBlock>

                <h3 className={h3Class}>Journal</h3>
                <p className={pClass}>View lifecycle events (boot, shutdown, errors).</p>
                <CodeBlock language="bash" filename="terminal">
                    aq trace journal [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--tail, -n" desc="Show last N events" def="20" />
                    <Row opt="--event, -e" desc="Filter by event type (boot, error, etc)" />
                    <Row opt="--json-output" desc="Output as JSON" def="false" />
                </Table>

                <h3 className={h3Class}>Diff</h3>
                <p className={pClass}>Compare current trace against another instance (useful for regression testing).</p>
                <CodeBlock language="bash" filename="terminal">
                    aq trace diff [OTHER_TRACE_PATH] --section=routes
                </CodeBlock>

                <h3 className={h3Class}>Clean</h3>
                <CodeBlock language="bash" filename="terminal">
                    aq trace clean [--force]
                </CodeBlock>
            </section>

            {/* Artifacts */}
            <section id="artifact" className={sectionClass}>
                <h2 className={h2Class}><Archive className="w-6 h-6 text-yellow-500" /> Artifact Management</h2>
                <p className={pClass}>
                    Manage the local artifact store (build outputs, models, bundles).
                </p>

                <h3 className={h3Class}>List & Inspect</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`# List artifacts
aq artifact list --kind model --tag env=prod

# Inspect metadata
aq artifact inspect my-app-v1.0.0`}
                </CodeBlock>

                <h3 className={h3Class}>Verify</h3>
                <p className={pClass}>Cryptographically verify artifact integrity.</p>
                <CodeBlock language="bash" filename="terminal">
                    {`aq artifact verify my-model
aq artifact verify-all`}
                </CodeBlock>

                <h3 className={h3Class}>Export & Import</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`# Create a transfer bundle
aq artifact export --name my-model -o bundle.aq

# Import from bundle
aq artifact import bundle.aq`}
                </CodeBlock>

                <h3 className={h3Class}>Garbage Collection</h3>
                <CodeBlock language="bash" filename="terminal">
                    aq artifact gc --keep sha256:abc... --dry-run
                </CodeBlock>
            </section>

            {/* Subsystems */}
            <section id="subsystems" className={sectionClass}>
                <h2 className={h2Class}><BarChart2 className="w-6 h-6 text-blue-500" /> Subsystem Utilities</h2>

                <h3 className={h3Class}>WebSockets</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`aq ws inspect
aq ws broadcast --namespace /chat --event message --payload '{"text": "hi"}'
aq ws gen-client --lang ts --out src/socket.ts`}
                </CodeBlock>

                <h3 className={h3Class}>Cache</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`aq cache check
aq cache inspect
aq cache stats
aq cache clear --namespace session_store`}
                </CodeBlock>

                <h3 className={h3Class}>Mail</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`aq mail check
aq mail inspect
aq mail send-test user@example.com`}
                </CodeBlock>

                <h3 className={h3Class}>Analytics</h3>
                <CodeBlock language="bash" filename="terminal">
                    {`aq analytics
aq discover --path src/`}
                </CodeBlock>
            </section>
        
      <NextSteps />
    </div>
    )
}