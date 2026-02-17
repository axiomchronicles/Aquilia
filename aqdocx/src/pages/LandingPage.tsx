import { Link } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { useTheme } from '../context/ThemeContext'
import { ArrowRight, Github, BookOpen, Zap, Shield, Database, Layers, Box, Workflow, Code, Terminal, Cpu, Globe } from 'lucide-react'
import { useState } from 'react'

export function LandingPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const [copied, setCopied] = useState(false)

  const copyCmd = () => {
    navigator.clipboard.writeText('pip install aquilia')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-grow pt-16 relative">
        {/* Grid Background */}
        <div className={`fixed inset-0 z-[-1] opacity-20 ${isDark ? '' : 'opacity-5'}`} style={{ backgroundImage: 'linear-gradient(#27272a 1px, transparent 1px), linear-gradient(90deg, #27272a 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        <div className="fixed inset-0 z-[-1] bg-gradient-to-b from-transparent via-[var(--bg-primary)]/80 to-[var(--bg-primary)]" />

        {/* Hero */}
        <section className={`relative pt-16 pb-20 sm:pt-24 sm:pb-24 overflow-hidden ${isDark ? 'bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-aquilia-900/20 via-black to-black' : ''}`}>
          <div className={`absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]`} />

          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-12 items-center">
              {/* Left: Content */}
              <div className="text-left flex flex-col items-start">
                <div className={`inline-flex items-center gap-2 mb-8 px-4 py-1.5 rounded-full border text-sm font-medium backdrop-blur-sm ${isDark ? 'border-aquilia-500/30 bg-aquilia-500/10 text-aquilia-400' : 'border-aquilia-600/30 bg-aquilia-500/10 text-aquilia-600'}`}>
                  <span className="flex h-2 w-2 rounded-full bg-aquilia-500 animate-pulse" />
                  v0.2.0 — Stable Release
                </div>

                <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight mb-6 leading-tight w-full">
                  The Production-Ready<br />
                  <span className="gradient-text relative inline-block">Async Python</span> Web Framework.
                </h1>

                <p className={`mt-6 text-lg mb-10 leading-relaxed max-w-lg ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                  Aquilia is a full-featured, async-native Python web framework with built-in DI, ORM, auth, sessions, caching, WebSockets, MLOps, and more. Everything you need — zero compromises.
                </p>

                <div className="flex flex-col sm:flex-row gap-4 mb-12 w-full lg:w-auto">
                  <Link to="/docs/quickstart" className={`group relative px-8 py-4 font-bold rounded-lg transition-all overflow-hidden text-center flex justify-center ${isDark ? 'bg-white text-black hover:bg-gray-100 hover:scale-105 shadow-[0_0_40px_rgba(255,255,255,0.1)]' : 'bg-aquilia-600 text-white hover:bg-aquilia-700 hover:scale-105'}`}>
                    <span className="relative z-10 flex items-center justify-center gap-2">
                      Get Started Free
                      <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </span>
                  </Link>
                  <a href="https://github.com/axiomchronicles/Aquilia" target="_blank" rel="noopener" className={`px-8 py-4 border rounded-lg font-semibold transition-all flex items-center justify-center gap-2 group ${isDark ? 'bg-zinc-900 border-zinc-800 text-white hover:border-aquilia-500/50' : 'bg-white border-gray-300 text-gray-800 hover:border-aquilia-500/50'}`}>
                    <Github className="w-5 h-5" />
                    View Source
                  </a>
                </div>

                {/* Install command */}
                <div className={`group relative flex items-center gap-4 px-6 py-4 border rounded-xl shadow-2xl cursor-pointer transition-all ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`} onClick={copyCmd}>
                  <span className={`font-mono text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>$</span>
                  <span className={`font-mono text-sm ${isDark ? 'text-white' : 'text-gray-800'}`}>pip install aquilia</span>
                  <div className={`pl-4 border-l transition-colors ${isDark ? 'border-white/10 text-gray-500 group-hover:text-aquilia-400' : 'border-gray-200 text-gray-400 group-hover:text-aquilia-600'}`}>
                    <Code className="w-4 h-4" />
                  </div>
                  {copied && <span className="absolute -top-10 left-1/2 -translate-x-1/2 bg-aquilia-500 text-black text-xs font-bold px-2 py-1 rounded">Copied!</span>}
                </div>
              </div>

              {/* Right: Gyroscope SVG */}
              <div className="hidden lg:flex justify-end items-center relative">
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

        {/* Feature Cards */}
        <section className={`py-20 relative overflow-hidden border-t ${isDark ? 'bg-zinc-950/50 border-white/5' : 'bg-gray-50/50 border-gray-200'}`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-aquilia-500 font-bold tracking-wide uppercase text-sm mb-4">Everything Built-In</h2>
              <h3 className={`text-4xl md:text-5xl font-bold leading-tight ${isDark ? 'text-white' : 'text-gray-900'}`}>One Framework.<br /><span className={isDark ? 'text-white/50' : 'text-gray-400'}>Zero Compromises.</span></h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
              {[
                { icon: <Layers className="w-8 h-8" />, title: 'Controller Architecture', desc: 'Class-based controllers with DI injection, pipelines, and OpenAPI generation. Manifest-first, compile-time optimized.' },
                { icon: <Box className="w-8 h-8" />, title: 'Dependency Injection', desc: 'Hierarchical scoped DI with singleton, app, request, transient, pooled, and ephemeral lifetimes.' },
                { icon: <Database className="w-8 h-8" />, title: 'Full ORM', desc: 'Production-grade async ORM with models, migrations, relationships, signals, and multi-backend support (SQLite, PostgreSQL, MySQL).' },
                { icon: <Shield className="w-8 h-8" />, title: 'Auth & Security', desc: 'OAuth2/OIDC, MFA, API keys, RBAC/ABAC authorization, cryptographic sessions, and security middleware.' },
                { icon: <Zap className="w-8 h-8" />, title: 'Effect System', desc: 'Typed side-effect declarations for DB transactions, cache, queues — with automatic resource lifecycle management.' },
                { icon: <Globe className="w-8 h-8" />, title: 'WebSockets', desc: 'Real-time socket controllers with namespaces, guards, message envelopes, and adapter-based pub/sub.' },
                { icon: <Workflow className="w-8 h-8" />, title: 'Fault System', desc: 'Structured error handling with fault domains, severity levels, recovery strategies, and debug pages.' },
                { icon: <Cpu className="w-8 h-8" />, title: 'MLOps Platform', desc: 'Model packaging, registry, serving, drift detection, and A/B testing — all integrated into the framework.' },
                { icon: <Terminal className="w-8 h-8" />, title: 'CLI & Testing', desc: 'Full CLI with generators and commands. Built-in test infrastructure with TestClient and fixtures.' },
              ].map((f, i) => (
                <div key={i} className={`group relative p-8 rounded-3xl border transition-all duration-300 overflow-hidden hover:-translate-y-1 hover:shadow-2xl ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:shadow-aquilia-900/20' : 'bg-white border-gray-200 hover:shadow-aquilia-100'}`}>
                  <div className={`absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity`} />
                  <div className="text-aquilia-500 mb-6">{f.icon}</div>
                  <h3 className={`text-xl font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{f.title}</h3>
                  <p className={`text-sm leading-relaxed font-light ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{f.desc}</p>
                </div>
              ))}
            </div>

            {/* CTA */}
            <div className="text-center">
              <Link to="/docs" className="inline-flex items-center gap-2 px-8 py-4 bg-aquilia-500 text-black font-bold rounded-lg transition-all hover:bg-aquilia-400 hover:scale-105 shadow-[0_0_40px_rgba(34,197,94,0.2)]">
                <BookOpen className="w-5 h-5" />
                Read the Documentation
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className={`border-t backdrop-blur-sm mt-auto ${isDark ? 'border-[var(--border-color)] bg-[var(--bg-card)]/50' : 'border-gray-200 bg-white/50'}`}>
        <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <img src="/logo.png" alt="Aquilia" className="w-6 h-6 object-contain opacity-80" />
              <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>© 2026 Aquilia Framework.</span>
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
