import { motion } from 'framer-motion'

export const ArchitectureDiagram = ({ isDark, className = "max-w-6xl" }: { isDark: boolean, className?: string }) => {
    const accentColor = '#22c55e' // aquilia-500
    const textColor = isDark ? '#e4e4e7' : '#1f2937'
    const mutedColor = isDark ? '#71717a' : '#9ca3af'

    return (
        <div className="w-full overflow-hidden p-4 md:p-8 my-12 flex justify-center bg-transparent">
            <svg viewBox="0 0 1200 1450" className={`w-full h-auto drop-shadow-2xl ${className}`}>
                <defs>
                    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="4" result="blur" />
                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                    <filter id="boxShadow" x="-10%" y="-10%" width="120%" height="120%">
                        <feDropShadow dx="0" dy="4" stdDeviation="4" floodOpacity="0.2" />
                    </filter>
                    <linearGradient id="gridGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor={accentColor} stopOpacity="0.1" />
                        <stop offset="100%" stopColor={accentColor} stopOpacity="0.02" />
                    </linearGradient>
                    <marker id="arrow-head" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill={accentColor} />
                    </marker>
                </defs>

                {/* --- BACKGROUND CIRCUIT GRID --- */}
                <g opacity="0.1" stroke={accentColor} strokeWidth="0.5">
                    {Array.from({ length: 12 }).map((_, i) => (
                        <line key={`v-${i}`} x1={i * 100} y1="0" x2={i * 100} y2="1450" />
                    ))}
                    {Array.from({ length: 15 }).map((_, i) => (
                        <line key={`h-${i}`} x1="0" y1={i * 100} x2="1200" y2={i * 100} />
                    ))}
                </g>

                {/* --- ZONE 1: BOOTSTRAP (Top Left) --- */}
                <motion.g initial={{ x: 50, y: 50 }} animate={{ y: [50, 40, 50] }} transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}>
                    <rect x="0" y="0" width="320" height="200" rx="16" fill="url(#gridGrad)" stroke={accentColor} strokeWidth="1" strokeDasharray="6,3" />
                    <text x="160" y="-15" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="black" className="font-mono tracking-widest opacity-80">01. BOOTSTRAP PHASE</text>

                    <g transform="translate(20, 30)">
                        <rect x="0" y="0" width="280" height="40" rx="8" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1.5" />
                        <text x="15" y="25" fill={accentColor} fontSize="12" fontWeight="bold">ManifestLoader (manifest.py)</text>
                        <motion.circle cx="260" cy="20" r="3" fill={accentColor} animate={{ opacity: [0, 1, 0] }} transition={{ duration: 1.5, repeat: Infinity }} />
                    </g>

                    <g transform="translate(20, 85)">
                        <rect x="0" y="0" width="280" height="40" rx="8" fill={accentColor} opacity="0.05" stroke={accentColor} strokeWidth="1" />
                        <text x="15" y="25" fill={textColor} fontSize="11" fontWeight="bold">FingerprintGenerator (SHA-256)</text>
                    </g>

                    <g transform="translate(20, 140)">
                        <rect x="0" y="0" width="280" height="40" rx="8" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" />
                        <text x="15" y="25" fill={accentColor} fontSize="11" fontWeight="bold">Aquilary::ValidationReport</text>
                    </g>
                </motion.g>

                {/* --- ZONE 2: AQUILARY CORE (Top Center) --- */}
                <motion.g initial={{ x: 420, y: 40 }} animate={{ scale: [1, 1.01, 1] }} transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}>
                    <rect x="0" y="0" width="360" height="240" rx="24" fill={isDark ? "#09090b" : "#ffffff"} stroke={accentColor} strokeWidth="3" filter="url(#glow)" />
                    <text x="180" y="-15" textAnchor="middle" fill={textColor} fontSize="16" fontWeight="extrabold" className="font-mono">02. CORE ENGINE (AQUILARY)</text>

                    <g transform="translate(30, 30)">
                        <text x="0" y="10" fill={accentColor} fontSize="10" fontWeight="black">DEPENDENCY GRAPH</text>
                        {[0, 1, 2].map(i => (
                            <circle key={i} cx={40 + i * 50} cy={40} r="15" fill={accentColor} opacity={0.2 + i * 0.15} stroke={accentColor} strokeWidth="2" />
                        ))}
                        <path d="M 55 40 H 75 M 105 40 H 125" stroke={accentColor} strokeWidth="2" />
                    </g>

                    <g transform="translate(30, 100)">
                        <rect x="0" y="0" width="300" height="50" rx="8" fill={accentColor} opacity="0.15" />
                        <text x="15" y="30" fill={textColor} fontSize="12" fontWeight="black">LIFECYCLE COORDINATOR</text>
                        <text x="230" y="30" fill={accentColor} fontSize="9" fontWeight="bold">V 1.0.0</text>
                    </g>

                    <g transform="translate(30, 170)">
                        <rect x="0" y="0" width="300" height="50" rx="8" fill={accentColor} opacity="0.05" stroke={accentColor} strokeWidth="1" strokeDasharray="4,2" />
                        <text x="15" y="22" fill={textColor} fontSize="10" fontWeight="bold">RuntimeRegistry::Snapshot</text>
                        <text x="15" y="40" fill={mutedColor} fontSize="9">Optimized Route Mapping & Hot-Reload</text>
                    </g>
                </motion.g>

                {/* --- ZONE 3: DI ECOSYSTEM (Center) --- */}
                <motion.g initial={{ x: 400, y: 350 }}>
                    <rect x="20" y="20" width="360" height="300" rx="24" fill={isDark ? "#121212" : "#f9fafb"} stroke={accentColor} strokeWidth="4" filter="url(#glow)" />
                    <text x="200" y="-20" textAnchor="middle" fill={textColor} fontSize="18" fontWeight="black" className="font-mono tracking-tighter">03. DI HUB (MULTI-TENANT)</text>

                    {/* Provider Stacks */}
                    <g transform="translate(45, 50)">
                        <text x="0" y="-10" fill={accentColor} fontSize="9" fontWeight="black">PROVIDER HIERARCHY</text>
                        {['CLASS', 'FACTORY', 'VALUE', 'POOL', 'LAZY', 'ALIAS'].map((p, i) => (
                            <g key={p} transform={`translate(0, ${i * 35})`}>
                                <rect x="0" y="0" width="140" height="28" rx="4" fill={accentColor} opacity={0.1 + i * 0.05} />
                                <text x="10" y="18" fill={textColor} fontSize="9" fontWeight="bold">{p}_PROVIDER</text>
                            </g>
                        ))}
                    </g>

                    {/* Scopes Stack */}
                    <g transform="translate(210, 50)">
                        <text x="0" y="-10" fill={accentColor} fontSize="9" fontWeight="black">ISOLATION SCOPES</text>
                        <g transform="translate(0, 0)">
                            <rect x="0" y="0" width="140" height="60" rx="8" fill={accentColor} opacity="0.2" />
                            <text x="10" y="25" fill={textColor} fontSize="11" fontWeight="black">SINGLETON</text>
                            <text x="10" y="45" fill={accentColor} fontSize="8">Root Container</text>
                        </g>
                        <g transform="translate(0, 75)">
                            <rect x="0" y="0" width="140" height="60" rx="8" fill={accentColor} opacity="0.15" stroke={accentColor} strokeWidth="1" />
                            <text x="10" y="25" fill={textColor} fontSize="11" fontWeight="black">APP (Module)</text>
                            <text x="10" y="45" fill={mutedColor} fontSize="8">Cross-App Protection</text>
                        </g>
                        <g transform="translate(0, 150)">
                            <rect x="0" y="0" width="140" height="80" rx="8" fill={accentColor} opacity="0.3" stroke={accentColor} strokeWidth="2" filter="url(#glow)" />
                            <text x="10" y="25" fill={textColor} fontSize="11" fontWeight="black">REQUEST</text>
                            <text x="10" y="45" fill={textColor} fontSize="8" opacity="0.7">Transactional Logic</text>
                            <motion.circle cx="120" cy="20" r="4" fill={accentColor} animate={{ scale: [1, 1.5, 1] }} transition={{ duration: 1, repeat: Infinity }} />
                        </g>
                    </g>
                </motion.g>

                {/* --- ZONE 4: REQUEST LIFECYCLE (Left column) --- */}
                <motion.g initial={{ x: 50, y: 300 }}>
                    <text x="140" y="-15" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="black" className="font-mono">04. REQUEST LIFECYCLE</text>

                    <g transform="translate(30, 40)">
                        <rect x="0" y="0" width="220" height="50" rx="12" fill={accentColor} opacity="0.2" stroke={accentColor} strokeWidth="2" />
                        <text x="110" y="32" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="bold">ASGI ADAPTER</text>
                    </g>

                    {/* Middleware Pipe */}
                    <g transform="translate(40, 120)">
                        <rect x="0" y="0" width="200" height="500" rx="16" fill={isDark ? "#0c0c0e" : "#f3f4f6"} stroke={accentColor} strokeWidth="1.5" />
                        <text x="100" y="25" textAnchor="middle" fill={accentColor} fontSize="11" fontWeight="black">DETERMINISTIC STACK</text>

                        {[
                            { name: 'EXCEPTION_MW', p: 1 },
                            { name: 'FAULT_MW', p: 2 },
                            { name: 'REQUEST_ID_MW', p: 10 },
                            { name: 'LOGGING_MW', p: 20 },
                            { name: 'AUTH_AUTH_MW', p: 15 },
                            { name: 'SESSION_MW', p: 15 },
                            { name: 'TEMPLATE_MW', p: 25 },
                            { name: 'SECURITY_MW', p: 7 }
                        ].sort((a, b) => a.p - b.p).map((mw, i) => (
                            <g key={mw.name} transform={`translate(15, ${50 + i * 55})`}>
                                <rect x="0" y="0" width="170" height="42" rx="6" fill={accentColor} opacity={0.1} stroke={accentColor} strokeWidth="0.5" />
                                <text x="10" y="25" fill={textColor} fontSize="9" fontWeight="bold">{mw.name}</text>
                                <text x="155" y="25" textAnchor="middle" fill={accentColor} fontSize="8" fontWeight="bold">{mw.p}</text>
                            </g>
                        ))}
                    </g>

                    <g transform="translate(30, 670)">
                        <rect x="0" y="0" width="220" height="50" rx="12" fill={accentColor} opacity="0.4" stroke={accentColor} strokeWidth="1" filter="url(#glow)" />
                        <text x="110" y="32" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="black">DYNAMIC ROUTER</text>
                    </g>
                </motion.g>

                {/* --- ZONE 5: EXECUTION ENGINE (Right column) --- */}
                <motion.g initial={{ x: 870, y: 300 }}>
                    <rect x="0" y="0" width="280" height="450" rx="28" fill={isDark ? "rgba(34, 197, 94, 0.04)" : "rgba(34, 197, 94, 0.01)"} stroke={accentColor} strokeWidth="2" filter="url(#glow)" />
                    <text x="140" y="-15" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="black" className="font-mono">05. EXECUTION ENGINE</text>

                    <g transform="translate(30, 40)">
                        <rect x="0" y="0" width="220" height="50" rx="10" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1.5" />
                        <text x="110" y="32" textAnchor="middle" fill={textColor} fontSize="12" fontWeight="bold">CONTROLLER FACTORY</text>
                    </g>

                    <g transform="translate(30, 110)">
                        <rect x="0" y="0" width="220" height="240" rx="16" fill="transparent" stroke={accentColor} strokeWidth="1.5" strokeDasharray="5,3" />
                        <text x="110" y="25" textAnchor="middle" fill={accentColor} fontSize="10" fontWeight="black">PIPELINE EXECUTION</text>

                        <g transform="translate(20, 50)">
                            <rect x="0" y="0" width="180" height="40" rx="6" fill={accentColor} opacity="0.15" />
                            <text x="90" y="25" textAnchor="middle" fill={textColor} fontSize="10" fontWeight="bold">GUARDS (Policy Enforcement)</text>
                        </g>

                        <g transform="translate(20, 105)">
                            <rect x="0" y="0" width="180" height="40" rx="6" fill={accentColor} opacity="0.15" />
                            <text x="90" y="25" textAnchor="middle" fill={textColor} fontSize="10" fontWeight="bold">TRANSFORMS (Aquilia Serilizer)</text>
                        </g>

                        <g transform="translate(20, 160)">
                            <rect x="0" y="0" width="180" height="50" rx="10" fill={accentColor} filter="url(#glow)" />
                            <text x="90" y="30" textAnchor="middle" fill={isDark ? "#000" : "#fff"} fontSize="12" fontWeight="black">ASYNC HANDLER</text>
                            <motion.path d="M 15 25 H 40 M 140 25 H 165" stroke={isDark ? "#000" : "#fff"} strokeWidth="2" animate={{ opacity: [0, 1, 0] }} transition={{ duration: 0.5, repeat: Infinity }} />
                        </g>
                    </g>

                    <g transform="translate(30, 370)">
                        <rect x="0" y="0" width="220" height="50" rx="10" fill={accentColor} opacity="0.2" stroke={accentColor} strokeWidth="1" />
                        <text x="110" y="32" textAnchor="middle" fill={textColor} fontSize="12" fontWeight="bold">RESPONSE SERIALIZER</text>
                    </g>
                </motion.g>

                {/* --- ZONE 7: AQUILARY MODELS (Center-Left Gap) --- */}
                <motion.g initial={{ x: 380, y: 820 }} animate={{ y: [820, 825, 820] }} transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}>
                    <rect x="15" y="15" width="330" height="290" rx="24" fill={isDark ? "#0c0c0e" : "#ffffff"} stroke={accentColor} strokeWidth="3" filter="url(#glow)" />
                    <text x="180" y="-15" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="black" className="font-mono">07. AQUILARY MODELS</text>

                    <g transform="translate(35, 45)">
                        <rect x="0" y="0" width="290" height="70" rx="12" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" strokeDasharray="4,4" />
                        <text x="15" y="25" fill={textColor} fontSize="11" fontWeight="black">DECLARATIVE SCHEMA</text>
                        <text x="15" y="45" fill={mutedColor} fontSize="9">Metaclass-driven ModelMeta registration</text>
                        <text x="15" y="58" fill={accentColor} fontSize="9" fontWeight="bold">Typed Fields (FK, M2M, O2O)</text>
                    </g>

                    <g transform="translate(35, 130)">
                        <rect x="0" y="0" width="290" height="140" rx="12" fill={accentColor} opacity="0.2" stroke={accentColor} strokeWidth="2" filter="url(#glow)" />
                        <text x="15" y="30" textAnchor="start" fill={textColor} fontSize="14" fontWeight="black">QUERYSET ENGINE</text>
                        <text x="15" y="55" fill={textColor} fontSize="10" opacity="0.8">Lazy Execution • ModelPack aware</text>
                        <path d="M 15 75 H 275 M 15 105 H 275" stroke={accentColor} strokeWidth="1" opacity="0.3" />
                        <text x="15" y="95" fill={textColor} fontSize="9">Optimized SQL Generation</text>
                        <text x="15" y="125" fill={textColor} fontSize="9">Transaction Context Isolation</text>
                        <motion.circle cx="260" cy="30" r="4" fill={accentColor} animate={{ scale: [1, 1.5, 1] }} transition={{ duration: 1, repeat: Infinity }} />
                    </g>
                </motion.g>

                {/* --- ZONE 6: AQUILARY SERIALIZERS (Center-Right Gap) --- */}
                <motion.g initial={{ x: 790, y: 820 }} animate={{ y: [820, 815, 820] }} transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}>
                    <rect x="15" y="15" width="330" height="290" rx="24" fill={isDark ? "#0c0c0e" : "#ffffff"} stroke={accentColor} strokeWidth="3" filter="url(#glow)" />
                    <text x="180" y="-15" textAnchor="middle" fill={textColor} fontSize="14" fontWeight="black" className="font-mono">06. AQUILARY SERIALIZERS</text>

                    <g transform="translate(35, 45)">
                        <rect x="0" y="0" width="290" height="70" rx="12" fill={accentColor} opacity="0.1" stroke={accentColor} strokeWidth="1" />
                        <text x="15" y="25" fill={textColor} fontSize="11" fontWeight="black">VALIDATION ENGINE</text>
                        <text x="15" y="45" fill={mutedColor} fontSize="9">Deep recursive type checking</text>
                        <text x="15" y="58" fill={accentColor} fontSize="9" fontWeight="bold">Automatic Serilizer Mapping</text>
                    </g>

                    <g transform="translate(35, 130)">
                        <rect x="0" y="0" width="290" height="140" rx="12" fill={accentColor} opacity="0.2" stroke={accentColor} strokeWidth="2" filter="url(#glow)" />
                        <text x="15" y="30" textAnchor="start" fill={textColor} fontSize="14" fontWeight="black">TRANSFORM PIPELINE</text>
                        <text x="15" y="55" fill={textColor} fontSize="10" opacity="0.8">JSON • MsgPack • Protobuf</text>
                        <g transform="translate(10, 75)">
                            {[0, 1, 2].map(i => (
                                <rect key={i} x={i * 90} y="0" width="80" height="25" rx="4" fill={accentColor} opacity={0.1 + i * 0.1} />
                            ))}
                            <text x="40" y="16" textAnchor="middle" fill={textColor} fontSize="7">PARSE</text>
                            <text x="130" y="16" textAnchor="middle" fill={textColor} fontSize="7">MAP</text>
                            <text x="220" y="16" textAnchor="middle" fill={textColor} fontSize="7">EMIT</text>
                        </g>
                        <text x="15" y="125" fill={mutedColor} fontSize="9">Optimized for high-throughput I/O</text>
                        <motion.rect x="250" y="15" width="20" height="20" rx="4" fill={accentColor} opacity="0.4" animate={{ rotate: 180 }} transition={{ duration: 4, repeat: Infinity, ease: "linear" }} />
                    </g>
                </motion.g>

                {/* --- ZONE 8: SATELLITES (Bottom Row) --- */}
                <motion.g initial={{ x: 50, y: 1250 }}>
                    <rect x="0" y="0" width="1100" height="150" rx="24" fill="transparent" stroke={accentColor} strokeWidth="1" strokeDasharray="15,5" opacity="0.4" />
                    <text x="550" y="-25" textAnchor="middle" fill={textColor} fontSize="16" fontWeight="black" className="font-mono tracking-widest opacity-60">08. SATELLITE SUBSYSTEMS (EFFECTS & INTEGRATIONS)</text>

                    <g transform="translate(35, 30)">
                        <rect x="0" y="0" width="160" height="90" rx="12" fill={accentColor} opacity="0.05" stroke={accentColor} strokeDasharray="2,2" />
                        <text x="80" y="25" textAnchor="middle" fill={accentColor} fontSize="12" fontWeight="black">MLOPS</text>
                        <text x="80" y="50" textAnchor="middle" fill={textColor} fontSize="9">ModelPack Registry</text>
                        <text x="80" y="70" textAnchor="middle" fill={textColor} fontSize="9">ONNX/PyTorch Runtime</text>
                    </g>

                    <g transform="translate(215, 30)">
                        <rect x="0" y="0" width="160" height="90" rx="12" fill={accentColor} opacity="0.1" stroke={accentColor} />
                        <text x="80" y="25" textAnchor="middle" fill={accentColor} fontSize="12" fontWeight="black">DATA LAYER</text>
                        <text x="80" y="50" textAnchor="middle" fill={textColor} fontSize="9">PostgreSQL / Redis</text>
                        <text x="80" y="70" textAnchor="middle" fill={textColor} fontSize="9">Transactional UnitOfWork</text>
                    </g>

                    <g transform="translate(395, 30)">
                        <rect x="0" y="0" width="160" height="90" rx="12" fill={accentColor} opacity="0.05" stroke={accentColor} strokeDasharray="2,2" />
                        <text x="80" y="25" textAnchor="middle" fill={accentColor} fontSize="12" fontWeight="black">ASYNC TASKS</text>
                        <text x="80" y="50" textAnchor="middle" fill={textColor} fontSize="9">Celery / RabbitMQ</text>
                        <text x="80" y="70" textAnchor="middle" fill={textColor} fontSize="9">Periodic Jobs (Beat)</text>
                    </g>

                    <g transform="translate(575, 30)">
                        <rect x="0" y="0" width="160" height="90" rx="12" fill={accentColor} opacity="0.1" stroke={accentColor} />
                        <text x="80" y="25" textAnchor="middle" fill={accentColor} fontSize="12" fontWeight="black">OBSERVABILITY</text>
                        <text x="80" y="50" textAnchor="middle" fill={textColor} fontSize="9">OpenTelemetry / Sentry</text>
                        <text x="80" y="70" textAnchor="middle" fill={textColor} fontSize="9">Aquilia Journaling</text>
                    </g>

                    <g transform="translate(755, 30)">
                        <rect x="0" y="0" width="160" height="90" rx="12" fill={accentColor} opacity="0.05" stroke={accentColor} strokeDasharray="2,2" />
                        <text x="80" y="25" textAnchor="middle" fill={accentColor} fontSize="12" fontWeight="black">FAULT ENGINE</text>
                        <text x="80" y="50" textAnchor="middle" fill={textColor} fontSize="9">Error Pattern Matching</text>
                        <text x="80" y="70" textAnchor="middle" fill={textColor} fontSize="9">Subsytem Patching</text>
                    </g>

                    <g transform="translate(935, 30)">
                        <rect x="0" y="0" width="130" height="90" rx="12" fill={accentColor} opacity="0.1" stroke={accentColor} />
                        <text x="65" y="25" textAnchor="middle" fill={accentColor} fontSize="12" fontWeight="black">COMMMS</text>
                        <text x="65" y="50" textAnchor="middle" fill={textColor} fontSize="9">Mail (SMTP/SES)</text>
                        <text x="65" y="70" textAnchor="middle" fill={textColor} fontSize="9">WebSockets (PubSub)</text>
                    </g>
                </motion.g>

                {/* --- CONNECTIONS (Circuit Paths) --- */}
                <g opacity="0.5" stroke={accentColor} strokeWidth="1.5" fill="none" markerEnd="url(#arrow-head)">
                    <path d="M 370 150 H 420" /> {/* Bootstrap -> Core */}
                    <path d="M 600 280 V 350" /> {/* Core -> DI */}
                    <path d="M 800 520 H 870" /> {/* DI -> Execution */}

                    <path d="M 1010 750 V 860" /> {/* Execution -> Serializers */}
                    <path d="M 790 1020 H 740" /> {/* Serializers -> Models */}
                    <path d="M 140 1050 Q 240 1150 400 1090" strokeDasharray="5,5" opacity="0.2" /> {/* Router -> Models (Journaling) */}

                    <path d="M 480 1140 V 1250" /> {/* Models -> Satellites (Shifted X to avoid text) */}
                    <path d="M 970 1180 V 1250" /> {/* Serializers -> Satellites (Cache) */}

                    <path d="M 330 550 Q 360 550 400 520" strokeDasharray="5,5" /> {/* Middleware -> DI */}
                </g>
                {/* --- DYNAMIC DATA PULSES --- */}
                {/* Boot Pulse */}
                <motion.circle r="5" fill={accentColor} filter="url(#glow)"
                    animate={{ cx: [370, 420], cy: 150, opacity: [0, 1, 0] }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                />

                {/* Request Pulse */}
                <motion.path
                    d="M 160 300 V 380"
                    stroke={accentColor} strokeWidth="3" filter="url(#glow)"
                    animate={{ pathLength: [0, 1], opacity: [0, 1, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                />

                {/* Hot Path Pulse (Execution -> Serializers -> Models -> Satellites) */}
                <motion.circle r="6" fill={accentColor} filter="url(#glow)"
                    animate={{
                        cx: [1010, 1010, 790, 480, 480],
                        cy: [390, 1020, 1020, 1020, 1250],
                        opacity: [0, 1, 1, 1, 1, 0]
                    }}
                    transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                />

                {/* Model Sync Pulse */}
                <motion.path
                    d="M 480 1140 V 1250"
                    stroke={accentColor} strokeWidth="2" strokeDasharray="10,10"
                    animate={{ strokeDashoffset: [-20, 0] }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
            </svg>
        </div>
    )
}
