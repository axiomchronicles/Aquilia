import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Cloud, Container, Server, FileText, Activity } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function CLIGenerators() {
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
          <Cloud className="w-4 h-4" />
          CLI / Generators
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Deploy Generators
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Production-ready infrastructure generation. The <code className="text-aquilia-500">aq deploy</code> suite inspects your workspace and generates tailored Dockerfiles, Kubernetes manifests, CI pipelines, and more.
        </p>
      </div>

      {/* Docker */}
      <section id="docker" className={sectionClass}>
        <h2 className={h2Class}><Container className="w-6 h-6 text-blue-500" /> Docker & Compose</h2>

        <h3 className={h3Class}>Dockerfile</h3>
        <p className={pClass}>
          Generates optimized multi-stage Dockerfiles.
        </p>
        <CodeBlock language="bash" filename="terminal">
          aq deploy dockerfile [OPTIONS]
        </CodeBlock>
        <Table>
          <Row opt="--dev" desc="Generate development Dockerfile (hot-reload)" def="false" />
          <Row opt="--mlops" desc="Generate MLOps model serving Dockerfile" def="false" />
          <Row opt="--output, -o" desc="Output directory" def="." />
        </Table>

        <h3 className={h3Class}>Docker Compose</h3>
        <p className={pClass}>
          Generates <span className={codeClass}>docker-compose.yml</span> with auto-detected services (Postgres, Redis, etc.).
        </p>
        <CodeBlock language="bash" filename="terminal">
          aq deploy compose [OPTIONS]
        </CodeBlock>
        <Table>
          <Row opt="--dev" desc="Include docker-compose.dev.yml override" def="false" />
          <Row opt="--monitoring" desc="Include Prometheus & Grafana services" def="false" />
        </Table>
      </section>

      {/* Kubernetes */}
      <section id="k8s" className={sectionClass}>
        <h2 className={h2Class}><Cloud className="w-6 h-6 text-indigo-500" /> Kubernetes</h2>
        <p className={pClass}>
          Generates a full suite of K8s manifests (Deployment, Service, Ingress, HPA, ConfigMap, Secret) and Kustomize configuration.
        </p>
        <CodeBlock language="bash" filename="terminal">
          aq deploy kubernetes [OPTIONS]
        </CodeBlock>
        <Table>
          <Row opt="--output, -o" desc="Output directory" def="k8s" />
          <Row opt="--mlops" desc="Force include MLOps manifests" def="auto" />
        </Table>
      </section>

      {/* CI/CD */}
      <section id="ci" className={sectionClass}>
        <h2 className={h2Class}><Activity className="w-6 h-6 text-green-500" /> CI/CD Pipelines</h2>
        <p className={pClass}>
          Generates workflow files for GitHub Actions or GitLab CI.
        </p>
        <CodeBlock language="bash" filename="terminal">
          aq deploy ci [OPTIONS]
        </CodeBlock>
        <Table>
          <Row opt="--provider" desc="CI Provider (github, gitlab)" def="github" />
          <Row opt="--output, -o" desc="Output directory" def="auto" />
        </Table>
      </section>

      {/* Infrastructure */}
      <section id="infra" className={sectionClass}>
        <h2 className={h2Class}><Server className="w-6 h-6 text-purple-500" /> Infrastructure</h2>

        <h3 className={h3Class}>Nginx</h3>
        <p className={pClass}>
          Generates a production-ready Nginx reverse proxy configuration with security headers and SSL placeholders.
        </p>
        <CodeBlock language="bash" filename="terminal">
          aq deploy nginx
        </CodeBlock>

        <h3 className={h3Class}>Monitoring</h3>
        <p className={pClass}>
          Generates Prometheus configuration and Grafana dashboards tailored to your app's metrics.
        </p>
        <CodeBlock language="bash" filename="terminal">
          aq deploy monitoring
        </CodeBlock>
      </section>

      {/* Utilities */}
      <section id="utils" className={sectionClass}>
        <h2 className={h2Class}><FileText className="w-6 h-6 text-gray-500" /> Utilities</h2>

        <h3 className={h3Class}>Environment Template</h3>
        <p className={pClass}>
          Generates a <span className={codeClass}>.env.example</span> file based on your workspace configuration.
        </p>
        <CodeBlock language="bash" filename="terminal">
          aq deploy env
        </CodeBlock>

        <h3 className={h3Class}>All-in-One</h3>
        <p className={pClass}>
          Generates the entire deployment suite at once.
        </p>
        <CodeBlock language="bash" filename="terminal">
          aq deploy all --monitoring --ci-provider=github --force
        </CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}