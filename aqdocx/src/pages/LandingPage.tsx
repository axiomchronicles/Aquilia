import { Link } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { useTheme } from '../context/ThemeContext'
import { ArrowRight, Github, BookOpen, Zap, Shield, Database, Layers, Box, Workflow, Code, Terminal, Globe, Activity, Rocket, Cpu as CpuIcon } from 'lucide-react'
import { PostgresSQLIcon, RedisIcon, RabbitMQIcon, SentryIcon, OpenTelemetryIcon, AwsS3Icon, ElasticsearchIcon, DockerIcon } from '../components/BrandIcons'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { ArchitectureDiagram } from '../components/ArchitectureDiagram'

export function LandingPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const [copied, setCopied] = useState(false)

  const copyCmd = () => {
    navigator.clipboard.writeText('pip install aquilia')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const containerVariants: any = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants: any = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { duration: 0.5, ease: 'easeInOut' }
    }
  }

  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden">
      <Navbar />
      <main className="flex-grow pt-16 relative">
        {/* Grid Background */}
        <div className={`fixed inset-0 z-[-1] opacity-20 ${isDark ? '' : 'opacity-5'}`} style={{ backgroundImage: 'linear-gradient(#27272a 1px, transparent 1px), linear-gradient(90deg, #27272a 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        <div className="fixed inset-0 z-[-1] bg-gradient-to-b from-transparent via-[var(--bg-primary)]/80 to-[var(--bg-primary)]" />

        {/* Hero */}
        <section className={`relative pt-8 pb-20 sm:pt-12 sm:pb-32 overflow-hidden ${isDark ? 'bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-aquilia-900/20 via-black to-black' : ''}`}>
          <div className={`absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]`} />

          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-12 items-center">
              {/* Left: Content */}
              <motion.div
                initial="hidden"
                animate="visible"
                variants={containerVariants}
                className="text-left flex flex-col items-start"
              >
                <motion.div variants={itemVariants} className={`inline-flex items-center gap-2 mb-8 px-4 py-1.5 rounded-full border text-sm font-medium backdrop-blur-md relative overflow-hidden group ${isDark ? 'border-aquilia-500/30 bg-aquilia-500/10 text-aquilia-400' : 'border-aquilia-600/30 bg-aquilia-500/10 text-aquilia-600'}`}>
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
                  <span className="flex h-2 w-2 rounded-full bg-aquilia-500 animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.5)]" />
                  v1.0.0 — Production Ready
                </motion.div>

                <motion.h1 variants={itemVariants} className="text-4xl sm:text-6xl font-extrabold tracking-tight mb-6 leading-tight w-full">
                  The speed of a microframework.<br />
                  <span className="gradient-text relative inline-block">The reliability</span> of an enterprise engine.
                </motion.h1>

                <motion.p variants={itemVariants} className={`mt-6 text-lg mb-10 leading-relaxed max-w-lg ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                  Stop choosing between developer velocity and production stability. Aquilia’s Manifest-First, async-native architecture removes routing and deployment boilerplate so you can build, test, and ship faster — with production manifests and ML deployment generated automatically.
                </motion.p>

                <motion.div variants={itemVariants} className="space-y-4 mb-12">
                  {[
                    "Auto-discover routes, services, models — zero routing boilerplate.",
                    "Generate Docker / Compose / Kubernetes manifests in one command.",
                    "Native ML model deployment and async performance out of the box."
                  ].map((benefit, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="flex-shrink-0 w-5 h-5 rounded-full bg-aquilia-500/20 flex items-center justify-center">
                        <Zap className="w-3 h-3 text-aquilia-500" />
                      </div>
                      <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{benefit}</span>
                    </div>
                  ))}
                </motion.div>

                <motion.div variants={itemVariants} className="flex flex-col sm:flex-row gap-4 mb-12 w-full lg:w-auto">
                  <Link to="/docs" className={`group relative px-8 py-3.5 font-bold rounded-xl transition-all overflow-hidden text-center flex justify-center items-center shadow-lg hover:shadow-aquilia-500/25 ${isDark ? 'bg-white text-black hover:scale-105' : 'bg-aquilia-600 text-white hover:bg-aquilia-700 hover:scale-105'}`}>
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent translate-x-[-100%] group-hover:animate-shimmer" />
                    <span className="relative z-10 flex items-center justify-center gap-2">
                      Get Started
                      <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </span>
                  </Link>
                  <Link to="/docs/architecture" className={`px-8 py-3.5 border rounded-xl font-semibold transition-all flex items-center justify-center gap-2 group hover:bg-white/5 ${isDark ? 'bg-zinc-900 border-zinc-800 text-white hover:border-aquilia-500/50' : 'bg-white border-gray-300 text-gray-800 hover:border-aquilia-500/50'}`}>
                    Architecture Guide
                  </Link>
                </motion.div>

                {/* Install command */}
                <motion.div variants={itemVariants} className={`group relative flex items-center gap-4 px-6 py-4 border rounded-xl shadow-2xl cursor-pointer transition-all ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`} onClick={copyCmd}>
                  <span className={`font-mono text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>$</span>
                  <span className={`font-mono text-sm ${isDark ? 'text-white' : 'text-gray-800'}`}>pip install aquilia</span>
                  <div className={`pl-4 border-l transition-colors ${isDark ? 'border-white/10 text-gray-500 group-hover:text-aquilia-400' : 'border-gray-200 text-gray-400 group-hover:text-aquilia-600'}`}>
                    <Code className="w-4 h-4" />
                  </div>
                  {copied && <span className="absolute -top-10 left-1/2 -translate-x-1/2 bg-aquilia-500 text-black text-xs font-bold px-2 py-1 rounded shadow-lg">Copied!</span>}
                </motion.div>
              </motion.div>

              {/* Right: Gyroscope SVG */}
              <div className="hidden lg:flex justify-end items-center relative lg:-mt-72">
                <div className="absolute inset-0 bg-aquilia-500/10 blur-[100px] rounded-full animate-breathing" />
                <div className="relative w-full max-w-lg aspect-square flex items-center justify-center animate-float">
                  <svg className="w-full h-full" viewBox="0 0 500 500" fill="none">
                    <defs>
                      <linearGradient id="ring-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#22c55e" stopOpacity="0.1" />
                        <stop offset="50%" stopColor="#22c55e" stopOpacity="0.6" />
                        <stop offset="100%" stopColor="#22c55e" stopOpacity="0.1" />
                      </linearGradient>
                    </defs>
                    <g className="animate-gyro-1 origin-center"><circle cx="250" cy="250" r="220" stroke="url(#ring-grad)" strokeWidth="1" strokeDasharray="1 10" /></g>
                    <g className="animate-gyro-2 origin-center"><ellipse cx="250" cy="250" rx="180" ry="180" stroke="#22c55e" strokeWidth="1" strokeOpacity="0.4" strokeDasharray="20 40" /></g>
                    <g className="animate-gyro-3 origin-center"><circle cx="250" cy="250" r="120" stroke="#22c55e" strokeWidth="2" strokeOpacity="0.6" strokeDasharray="60 100" /><circle cx="130" cy="250" r="3" fill="#86efac" /><circle cx="370" cy="250" r="3" fill="#86efac" /></g>
                    <g className="animate-drift"><circle cx="100" cy="100" r="1.5" fill="#4ade80" opacity="0.6" /><circle cx="400" cy="400" r="2" fill="#4ade80" opacity="0.4" /><circle cx="450" cy="150" r="1" fill="#4ade80" opacity="0.5" /></g>
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="relative w-32 h-32 flex items-center justify-center">
                      <div className="absolute inset-0 bg-aquilia-500/20 blur-xl rounded-full" />
                      <img src="/logo.png" className="relative z-10 w-24 h-auto drop-shadow-2xl" alt="Aquilia" />
                    </div>
                  </div>
                  {/* Floating metrics */}
                  <div className="absolute top-[20%] left-[10%] animate-drift" style={{ animationDelay: '-5s' }}>
                    <div className={`backdrop-blur-sm px-3 py-1.5 rounded-lg flex flex-col items-center ${isDark ? 'bg-black/20 border border-aquilia-500/10' : 'bg-white/80 border border-aquilia-500/20'}`}>
                      <span className="text-[10px] text-aquilia-400 font-mono tracking-widest opacity-80">ASYNC</span>
                      <span className={`font-bold text-sm ${isDark ? 'text-white' : 'text-gray-800'}`}>Native</span>
                    </div>
                  </div>
                  <div className="absolute bottom-[20%] right-[10%] animate-drift" style={{ animationDelay: '-15s' }}>
                    <div className={`backdrop-blur-sm px-3 py-1.5 rounded-lg flex flex-col items-center ${isDark ? 'bg-black/20 border border-aquilia-500/10' : 'bg-white/80 border border-aquilia-500/20'}`}>
                      <span className="text-[10px] text-aquilia-400 font-mono tracking-widest opacity-80">FULL-STACK</span>
                      <span className={`font-bold text-sm ${isDark ? 'text-white' : 'text-gray-800'}`}>Framework</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Performance Section */}
        <section className={`py-24 relative overflow-hidden border-y ${isDark ? 'bg-black border-white/5' : 'bg-gray-50 border-gray-200'}`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
              <div>
                <h2 className="text-aquilia-500 font-bold tracking-wide uppercase text-sm mb-4">Unrivaled Performance</h2>
                <h3 className={`text-4xl md:text-5xl font-bold mb-6 leading-tight ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  Scaling Without<br />Limits.
                </h3>
                <p className={`text-lg mb-8 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                  Aquilia is engineered for high-throughput I/O. Our benchmark report shows that for large JSON payload serialization, Aquilia is nearly <strong>6× faster than FastAPI</strong>.
                </p>
                <div className="space-y-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-aquilia-500/10 flex items-center justify-center text-aquilia-500">
                      <Zap className="w-6 h-6" />
                    </div>
                    <div>
                      <h4 className={`font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>5.7× Throughput Advantage</h4>
                      <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>Superior JSON-large handling over FastAPI (2,747 vs 480 req/s)</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-aquilia-500/10 flex items-center justify-center text-aquilia-500">
                      <Activity className="w-6 h-6" />
                    </div>
                    <div>
                      <h4 className={`font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Consistent Latency</h4>
                      <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>Deterministic request processing with minimal overhead</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className={`p-8`}>
                <div className="mb-8">
                  <h4 className={`text-lg font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Benchmark: JSON-Large (Req/s)</h4>
                  <div className="space-y-6">
                    <div>
                      <div className="flex justify-between mb-2">
                        <span className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Aquilia 1.0.0</span>
                        <span className="text-sm font-bold text-aquilia-500">2,747</span>
                      </div>
                      <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden dark:bg-zinc-800">
                        <motion.div
                          initial={{ width: 0 }}
                          whileInView={{ width: '68%' }}
                          transition={{ duration: 1, ease: 'easeInOut' }}
                          className="h-full bg-aquilia-500"
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-2">
                        <span className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Sanic 23.12.x</span>
                        <span className="text-sm font-bold text-gray-500">4,000</span>
                      </div>
                      <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden dark:bg-zinc-800">
                        <motion.div
                          initial={{ width: 0 }}
                          whileInView={{ width: '100%' }}
                          transition={{ duration: 1, ease: 'easeInOut' }}
                          className={`h-full ${isDark ? 'bg-zinc-600' : 'bg-gray-400'}`}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-2">
                        <span className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>FastAPI 0.110.x</span>
                        <span className="text-sm font-bold text-red-500">480</span>
                      </div>
                      <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden dark:bg-zinc-800">
                        <motion.div
                          initial={{ width: 0 }}
                          whileInView={{ width: '12%' }}
                          transition={{ duration: 1, ease: 'easeInOut' }}
                          className="h-full bg-red-500/50"
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <p className={`text-xs text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                  * Based on median of 3 runs (wrk, 50 connections, durations: 30s).
                  <Link to="/docs" className="text-aquilia-500 hover:underline ml-1">View Full Report</Link>
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Comparison Table Section */}
        <section className={`py-20 relative overflow-hidden border-b ${isDark ? 'bg-black/50 border-white/5' : 'bg-gray-50/30 border-gray-200'}`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h3 className={`text-3xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>The Full Picture</h3>
              <p className={`text-lg ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>How Aquilia stacks up against the Python ecosystem.</p>
            </div>

            <div className={`overflow-x-auto rounded-3xl border ${isDark ? 'bg-zinc-900/30 border-white/10' : 'bg-white border-gray-200 shadow-xl'}`}>
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className={`border-b ${isDark ? 'border-white/10 bg-white/5' : 'border-gray-100 bg-gray-50'}`}>
                    <th className="px-8 py-5 text-sm font-bold uppercase tracking-wider text-aquilia-500">Benchmark / Feature</th>
                    <th className={`px-8 py-5 text-sm font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Aquilia 1.0</th>
                    <th className={`px-8 py-5 text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>FastAPI</th>
                    <th className={`px-8 py-5 text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Sanic</th>
                    <th className={`px-8 py-5 text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Django</th>
                    <th className={`px-8 py-5 text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Flask</th>
                  </tr>
                </thead>
                <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-50'}`}>
                  {[
                    { feature: 'JSON-Large (Req/s)', a: '2,747 (🔥 High)', f: '480 (Pydantic bottleneck)', s: '4,000 (ujson)', d: '~120', fl: '~150' },
                    { feature: 'Architecture', a: 'Compile-time Manifest', f: 'Runtime Hooking', s: 'Runtime Event-loop', d: 'MVT / Middleware', fl: 'WSGI / Minimal' },
                    { feature: 'Dependency Injection', a: 'Built-in (First-class)', f: 'Parameters-only', s: 'Manual / Extension', d: 'Manual / Global', fl: 'Manual / Globals' },
                    { feature: 'Integrated ORM', a: 'Yes (Async Native)', f: 'External (SQLAlchemy)', s: 'External', d: 'Yes (Sync/Bridge)', fl: 'External (SQLAlchemy)' },
                    { feature: 'MLOps Toolkit', a: 'Built-in (ModelPacks)', f: 'Manual Setup', s: 'Manual Setup', d: 'Manual Setup', fl: 'Manual Setup' },
                    { feature: 'Type Safety', a: 'Full (End-to-end)', f: 'Full (Pydantic)', s: 'Partial', d: 'Partial', fl: 'Minimal' },
                  ].map((row, i) => (
                    <tr key={i} className={`group ${isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'} transition-colors`}>
                      <td className={`px-8 py-5 text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{row.feature}</td>
                      <td className="px-8 py-5 text-sm font-bold text-aquilia-500">{row.a}</td>
                      <td className={`px-8 py-5 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.f}</td>
                      <td className={`px-8 py-5 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.s}</td>
                      <td className={`px-8 py-5 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                      <td className={`px-8 py-5 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.fl}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className={`mt-8 text-xs text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              * Benchmarks conducted on Apple Silicon. JSON-Large performance measured with wrk (38KB payload).
            </p>
          </div>
        </section>

        {/* Architecture Section */}
        <section className={`py-24 relative overflow-hidden ${isDark ? 'bg-zinc-950/30' : 'bg-white'}`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-aquilia-500 font-bold tracking-wide uppercase text-sm mb-4">Deeply Engineered</h2>
              <h3 className={`text-4xl md:text-5xl font-bold leading-tight ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Manifest-First Architecture
              </h3>
              <p className={`mt-4 text-lg max-w-2xl mx-auto ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                Unlike discovery-heavy frameworks, Aquilia uses a two-phase <strong>manifest → compile</strong> pipeline, optimizing your application for maximum performance before the first request arrives.
              </p>
            </div>

            <div className="relative">
              <div className={`absolute inset-0 bg-aquilia-500/5 blur-[120px] rounded-full pointer-events-none`} />
              <ArchitectureDiagram isDark={isDark} className="max-w-4xl" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-16">
              <div className={`p-6 rounded-2xl border ${isDark ? 'bg-zinc-900/40 border-white/5' : 'bg-gray-50 border-gray-200'}`}>
                <div className="font-mono text-aquilia-500 text-xs mb-3">PHASE 01</div>
                <h4 className={`text-lg font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Bootstrap</h4>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Validated manifests index application metadata and services with content-addressed fingerprinting.</p>
              </div>
              <div className={`p-6 rounded-2xl border ${isDark ? 'bg-zinc-900/40 border-white/5' : 'bg-gray-50 border-gray-200'}`}>
                <div className="font-mono text-aquilia-500 text-xs mb-3">PHASE 02</div>
                <h4 className={`text-lg font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Compile</h4>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Static compilation of routes, DI graphs, and model schemas into optimized runtime artifacts.</p>
              </div>
              <div className={`p-6 rounded-2xl border ${isDark ? 'bg-zinc-900/40 border-white/5' : 'bg-gray-50 border-gray-200'}`}>
                <div className="font-mono text-aquilia-500 text-xs mb-3">PHASE 03</div>
                <h4 className={`text-lg font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Serve</h4>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>High-speed ASGI delivery through localized DI scopes and deterministic execution pipelines.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Cards */}
        <section className={`py-24 relative overflow-hidden border-t ${isDark ? 'bg-zinc-950 border-white/5' : 'bg-gray-50/50 border-gray-200'}`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-20">
              <h2 className="text-aquilia-500 font-bold tracking-wide uppercase text-sm mb-4">Everything Built-In</h2>
              <h3 className={`text-4xl md:text-5xl font-bold leading-tight ${isDark ? 'text-white' : 'text-gray-900'}`}>One Framework.<br /><span className={isDark ? 'text-white/50' : 'text-gray-400'}>Zero Compromises.</span></h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
              {[
                { icon: <Layers className="w-8 h-8" />, title: 'Controller Architecture', desc: 'Class-based controllers with DI injection, pipelines, and OpenAPI generation. Manifest-first, compile-time optimized.' },
                { icon: <Box className="w-8 h-8" />, title: 'Dependency Injection', desc: 'Hierarchical scoped DI with singleton, app, request, transient, pooled, and ephemeral lifetimes.' },
                { icon: <Database className="w-8 h-8" />, title: 'Full ORM', desc: 'Production-grade async ORM with models, migrations, relationships, signals, and multi-backend support (SQLite, PostgreSQL, MySQL).' },
                { icon: <Shield className="w-8 h-8" />, title: 'Auth & Security', desc: 'OAuth2/OIDC, MFA, API keys, RBAC/ABAC authorization, cryptographic sessions, and security middleware.' },
                { icon: <Zap className="w-8 h-8" />, title: 'Effect System', desc: 'Typed side-effect declarations for DB transactions, cache, queues — with automatic resource lifecycle management.' },
                { icon: <Globe className="w-8 h-8" />, title: 'WebSockets', desc: 'Real-time socket controllers with namespaces, guards, message envelopes, and adapter-based pub/sub.' },
                { icon: <Workflow className="w-8 h-8" />, title: 'Fault System', desc: 'Structured error handling with fault domains, severity levels, recovery strategies, and debug pages.' },
                { icon: <CpuIcon className="w-8 h-8" />, title: 'MLOps Platform', desc: 'Model packaging, registry, serving, drift detection, and A/B testing — all integrated into the framework.' },
                { icon: <Terminal className="w-8 h-8" />, title: 'CLI & Testing', desc: 'Full CLI with generators and commands. Built-in test infrastructure with TestClient and fixtures.' },
              ].map((f, i) => (
                <motion.div
                  key={i}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true }}
                  variants={itemVariants}
                  className={`group relative p-8 rounded-3xl border transition-all duration-300 overflow-hidden hover:-translate-y-1 hover:shadow-2xl ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:shadow-aquilia-900/20' : 'bg-white border-gray-200 hover:shadow-aquilia-100'}`}
                >
                  <div className={`absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-aquilia-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity`} />
                  <div className="text-aquilia-500 mb-6">{f.icon}</div>
                  <h3 className={`text-xl font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{f.title}</h3>
                  <p className={`text-sm leading-relaxed font-light ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{f.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Ecosystem Section */}
        <section className={`py-24 relative overflow-hidden ${isDark ? 'bg-black' : 'bg-white'}`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col lg:flex-row items-center gap-16">
              <div className="flex-1">
                <h2 className="text-aquilia-500 font-bold tracking-wide uppercase text-sm mb-4">Enterprise Ecosystem</h2>
                <h3 className={`text-4xl font-bold mb-6 leading-tight ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  Plays Well With<br />
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-aquilia-400 to-emerald-600">Everything You Use.</span>
                </h3>
                <p className={`text-lg mb-8 leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                  Aquilia ships with first-class, async-native adapters for the industry's standard infrastructure. No hacking required — just drop in your credentials and go.
                </p>

                <div className="grid grid-cols-2 gap-y-4 gap-x-8">
                  {[
                    'PostgreSQL', 'Redis', 'RabbitMQ', 'Sentry',
                    'OpenTelemetry', 'AWS S3', 'Elasticsearch', 'Docker'
                  ].map((item) => (
                    <div key={item} className={`flex items-center gap-3 font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                      <div className={`w-1.5 h-1.5 rounded-full ${isDark ? 'bg-aquilia-500' : 'bg-aquilia-600'}`} />
                      {item}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex-grow w-full lg:w-1/2">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 md:gap-6">
                  {[
                    { Icon: PostgresSQLIcon, name: 'PostgreSQL' },
                    { Icon: RedisIcon, name: 'Redis' },
                    { Icon: RabbitMQIcon, name: 'RabbitMQ' },
                    { Icon: SentryIcon, name: 'Sentry' },
                    { Icon: OpenTelemetryIcon, name: 'OpenTelemetry' },
                    { Icon: AwsS3Icon, name: 'AWS S3' },
                    { Icon: ElasticsearchIcon, name: 'Elasticsearch' },
                    { Icon: DockerIcon, name: 'Docker' },
                  ].map(({ Icon, name }, i) => (
                    <motion.div
                      key={name}
                      initial={{ opacity: 0, scale: 0.9 }}
                      whileInView={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.05 }}
                      whileHover={{ y: -5, transition: { duration: 0.2 } }}
                      className={`aspect-square rounded-2xl flex flex-col items-center justify-center gap-3`}
                    >
                      <Icon className={`w-10 h-10 ${isDark ? 'text-gray-200' : 'text-gray-700'}`} />
                      <span className={`text-xs font-semibold ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{name}</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-24 relative">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className={`p-16 rounded-[3rem] relative overflow-hidden`}
            >
              <div className="absolute top-0 right-0 p-8 opacity-10">
                <Rocket className="w-64 h-64 text-aquilia-500 -rotate-12" />
              </div>

              <h3 className={`text-4xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Ready to build the future?</h3>
              <p className={`text-lg mb-10 max-w-2xl mx-auto ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                Join thousands of developers building scalable, reliable, and production-ready Python applications with Aquilia.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link to="/docs" className="inline-flex items-center gap-2 px-8 py-4 bg-aquilia-500 text-black font-bold rounded-lg transition-all hover:bg-aquilia-400 hover:scale-105 shadow-[0_0_40px_rgba(34,197,94,0.3)]">
                  <BookOpen className="w-5 h-5" />
                  Read the Docs
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <a href="https://github.com/axiomchronicles/Aquilia" target="_blank" rel="noopener" className={`px-8 py-4 border rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${isDark ? 'bg-black border-white/10 text-white hover:bg-zinc-900' : 'bg-white border-gray-200 text-gray-800 hover:bg-gray-50'}`}>
                  <Github className="w-5 h-5" />
                  Star on GitHub
                </a>
              </div>
            </motion.div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className={`border-t backdrop-blur-sm mt-auto ${isDark ? 'border-[var(--border-color)] bg-[var(--bg-card)]/50' : 'border-gray-200 bg-white/50'}`}>
        <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-8">
            <div className="flex items-center gap-2">
              <img src="/logo.png" alt="Aquilia" className="w-6 h-6 object-contain opacity-80" />
              <span className={`text-sm font-bold tracking-tighter ${isDark ? 'text-white' : 'text-gray-900'}`}>AQUILIA</span>
            </div>

            <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              © 2026 Aquilia Framework. Built for the modern web.
            </div>

            <div className="flex space-x-6">
              <a href="https://github.com/axiomchronicles/Aquilia" target="_blank" rel="noopener" className={`transition-colors ${isDark ? 'text-gray-400 hover:text-aquilia-400' : 'text-gray-400 hover:text-aquilia-600'}`}>
                <Github className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
