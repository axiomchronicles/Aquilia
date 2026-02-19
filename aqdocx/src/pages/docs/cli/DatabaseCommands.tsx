import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { GitCommit, Search, Terminal, Table as TableIcon, Play } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function CLIDatabaseCommands() {
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
                    CLI / Database
                </div>
                <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                    Database Commands
                    <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
                  </span>
                </h1>
                <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    Comprehensive toolset for schema management, migrations, introspection, and database interaction. Supports multiple database backends via SQLAlchemy.
                </p>
            </div>

            {/* Migrations */}
            <section id="migrations" className={sectionClass}>
                <h2 className={h2Class}><GitCommit className="w-6 h-6 text-purple-500" /> Schema Migrations</h2>

                <h3 className={h3Class}>Make Migrations</h3>
                <p className={pClass}>
                    Generates new migration files by detecting changes in your <span className={codeClass}>Model</span> definitions.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq db makemigrations [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--app" desc="Limit to specific app/module" />
                    <Row opt="--name, -n" desc="Custom name for the migration file" />
                    <Row opt="--empty" desc="Create an empty migration file" def="false" />
                    <Row opt="--dry-run" desc="Preview changes without creating files" def="false" />
                    <Row opt="--no-dsl" desc="Use raw SQL instead of migration DSL" def="false" />
                </Table>

                <h3 className={h3Class}>Migrate</h3>
                <p className={pClass}>
                    Applies pending migrations to the database.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq db migrate [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--database" desc="Target specific database alias" def="default" />
                    <Row opt="--fake" desc="Mark migrations as applied without running SQL" def="false" />
                    <Row opt="--plan" desc="Show execution plan without applying" def="false" />
                    <Row opt="--run-syncdb" desc="Create tables for apps without migrations" def="false" />
                </Table>

                <h3 className={h3Class}>Show Migrations</h3>
                <p className={pClass}>
                    Lists all migrations and their status.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq db showmigrations [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--list, -l" desc="Show only unapplied migrations" def="false" />
                    <Row opt="--database" desc="Target database alias" def="default" />
                </Table>

                <h3 className={h3Class}>SQL Migrate</h3>
                <p className={pClass}>
                    Prints the SQL for a specific migration.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq db sqlmigrate [MIGRATION_NAME]
                </CodeBlock>
            </section>

            {/* Introspection */}
            <section id="inspection" className={sectionClass}>
                <h2 className={h2Class}><Search className="w-6 h-6 text-blue-500" /> Introspection & Dumping</h2>

                <h3 className={h3Class}>Inspect DB</h3>
                <p className={pClass}>
                    Introspects an existing database and generates Python <span className={codeClass}>Model</span> classes.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq db inspectdb [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--database-url" desc="Connection URL (overrides workspace.py)" />
                    <Row opt="--table, -t" desc="Limit to specific tables (repeatable)" />
                    <Row opt="--output, -o" desc="Write to file instead of stdout" />
                </Table>

                <h3 className={h3Class}>Dump</h3>
                <p className={pClass}>
                    Exports the current schema state as SQL or Python code.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq db dump --emit=[sql|python] [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--emit" desc="Output format: sql or python" def="python" />
                    <Row opt="--output-dir" desc="Directory to write dump files" def="." />
                </Table>
            </section>

            {/* Shell */}
            <section id="shell" className={sectionClass}>
                <h2 className={h2Class}><Play className="w-6 h-6 text-green-500" /> Database Shell</h2>
                <p className={pClass}>
                    Opens an interactive Python REPL with database connections established and all models pre-imported.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq db shell [OPTIONS]
                </CodeBlock>
                <Table>
                    <Row opt="--database-url" desc="Override connection string" />
                    <Row opt="--interface" desc="Shell interface (ipython, ptpython, native)" def="auto" />
                </Table>

                <CodeBlock language="python" filename="Shell Session">
                    {`>>> # All models are available
>>> await User.objects.filter(is_active=True).count()
150
>>> # Direct SQL access
>>> await db.execute("SELECT 1")`}
                </CodeBlock>
            </section>

            {/* Status */}
            <section id="status" className={sectionClass}>
                <h2 className={h2Class}><TableIcon className="w-6 h-6 text-orange-500" /> Status</h2>
                <p className={pClass}>
                    Detailed statistics about database tables, row counts, and storage usage.
                </p>
                <CodeBlock language="bash" filename="terminal">
                    aq db status
                </CodeBlock>
            </section>
        
      <NextSteps />
    </div>
    )
}