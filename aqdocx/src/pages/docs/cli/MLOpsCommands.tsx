import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Brain, Rocket, Eye, GitBranch, FlaskConical, Package, Zap, Plug } from 'lucide-react'

export function CLIMLOpsCommands() {
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
                    <Brain className="w-4 h-4" />
                    CLI / MLOps
                </div>
                <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                    MLOps Commands
                    <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
                  </span>
                </h1>
                <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Full-lifecycle ML operations from the command line: packaging models, serving inference endpoints, tracking lineage, and running A/B experiments.
                </p>
            </div>

            {/* Packaging */}
            <section id="pack" className={sectionClass}>
                <h2 className={h2Class}><Package className="w-6 h-6 text-purple-500" /> Model Packaging</h2>

                <h3 className={h3Class}>Save</h3>
                <p className={pClass}>
                    Bundles model artifacts and metadata into a portable <span className={codeClass}>.aquilia</span> archive.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq pack save [MODEL_PATH] [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--name, -n" desc="Model name" />
                    <Row opt="--version, -V" desc="Semantic version string" />
                    <Row opt="--framework, -f" desc="Framework (pytorch, tensorflow, sklearn, onnx)" def="custom" />
                    <Row opt="--env-lock" desc="Path to requirements.txt or conda environment file" />
                    <Row opt="--sign-key" desc="Private key for signing the artifact" />
                </Table>

                <h3 className={h3Class}>Inspect & Verify</h3>
                <p className={pClass}>
                    Examine contents and verify cryptographic signatures of model packs.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    {`aq pack inspect my-model.aquilia
aq pack verify my-model.aquilia --key public_key.pem`}
                </CodeBlock>

                <h3 className={h3Class}>Push</h3>
                <p className={pClass}>
                    Uploads a model pack to a remote registry.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq pack push [FILE] --registry=[URL]
                </CodeBlock>
            </section>

            {/* Serving */}
            <section id="serve" className={sectionClass}>
                <h2 className={h2Class}><Rocket className="w-6 h-6 text-green-500" /> Model Serving</h2>

                <h3 className={h3Class}>Serve</h3>
                <p className={pClass}>
                    Starts a high-performance inference server for a model.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq model serve [MODEL_PATH] [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--runtime" desc="Inference runtime (python, onnx, torchscript)" def="python" />
                    <Row opt="--port, -p" desc="Service port" def="9000" />
                    <Row opt="--batch-size" desc="Max batch size for dynamic batching" def="1" />
                    <Row opt="--workers" desc="Number of worker threads" def="auto" />
                </Table>

                <h3 className={h3Class}>Health</h3>
                <CodeBlock language="bash" filename="terminal">
                    aq model health --url http://localhost:9000
                </CodeBlock>
            </section>

            {/* Deployment */}
            <section id="deploy" className={sectionClass}>
                <h2 className={h2Class}><Zap className="w-6 h-6 text-yellow-500" /> Deployment</h2>

                <h3 className={h3Class}>Rollout</h3>
                <p className={pClass}>
                    Orchestrates a progressive delivery strategy (canary/blue-green).
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq deploy rollout [MODEL_NAME] [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--from-version" desc="Current stable version" />
                    <Row opt="--to-version" desc="New candidate version" />
                    <Row opt="--strategy" desc="Rollout strategy (canary, blue-green, shadow)" def="canary" />
                    <Row opt="--steps" desc="Number of incremental steps" def="5" />
                </Table>
            </section>

            {/* Observability */}
            <section id="observe" className={sectionClass}>
                <h2 className={h2Class}><Eye className="w-6 h-6 text-blue-500" /> Observability</h2>

                <h3 className={h3Class}>Drift Detection</h3>
                <p className={pClass}>
                    Analyzes data distributions for covariate shift.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq observe drift [REF_DATA] [CUR_DATA] [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--method" desc="Statistical method (psi, kl-divergence, ks-test)" def="psi" />
                    <Row opt="--threshold" desc="Alert threshold" def="0.1" />
                    <Row opt="--column" desc="Specific column to analyze" />
                </Table>
            </section>

            {/* Lineage */}
            <section id="lineage" className={sectionClass}>
                <h2 className={h2Class}><GitBranch className="w-6 h-6 text-orange-500" /> Lineage</h2>
                <p className={pClass}>
                    Traverse the dependency graph of models and data.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    {`# Show lineage graph
aq lineage show [MODEL_NAME] --format=tree

# Find ancestors (provenance)
aq lineage ancestors [MODEL_NAME]

# Find traceable path between entities
aq lineage path [SOURCE] [TARGET]`}
                </CodeBlock>
            </section>

            {/* Experiments */}
            <section id="experiment" className={sectionClass}>
                <h2 className={h2Class}><FlaskConical className="w-6 h-6 text-pink-500" /> Experiments</h2>
                <p className={pClass}>
                    Manage A/B tests and experimental cohorts.
                </p>

                <h3 className={h3Class}>Create</h3>
                <CodeBlock language="bash" filename="terminal">
                    aq experiment create [NAME] [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--arm" desc="Define variant arm (name:version:traffic_share)" />
                    <Row opt="--description" desc="Experiment description" />
                    <Row opt="--metric" desc="Primary metric to optimize" />
                </Table>

                <h3 className={h3Class}>Conclude</h3>
                <CodeBlock language="bash" filename="terminal">
                    aq experiment conclude [NAME] --winner=[ARM_NAME]
                </CodeBlock>
            </section>

            {/* Plugins */}
            <section id="plugins" className={sectionClass}>
                <h2 className={h2Class}><Plug className="w-6 h-6 text-teal-500" /> Plugins</h2>
                <CodeBlock language="bash" filename="terminal">
                    {`aq plugin list
aq plugin search [QUERY]
aq plugin install [NAME]`}
                </CodeBlock>
            </section>
        </div>
    )
}
