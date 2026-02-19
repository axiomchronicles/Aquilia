import type { Route } from "./+types/home";
import { Link } from "react-router";
import { Navbar } from "~/components/Navbar";
import { Footer } from "~/components/Footer";
import { CodeBlock } from "~/components/CodeBlock";
import { PythonIcon, NodejsIcon } from "~/components/SdkIcons";
import { DataFlowAnimation, ArchitectureDiagram } from "~/components/ArchitectureSvg";
import { useState } from "react";
import {
  Zap,
  Shield,
  Binary,
  ArrowRight,
  Copy,
  Check,
  Database,
  Cpu,
  Lock,
  MemoryStick,
  Server,
  Gamepad2,
  Radio,
  Activity,
  Gauge,
  FileCode2,
  ShieldCheck,
  CircuitBoard,
} from "lucide-react";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Crous - Deterministic Binary Document Format | Python & Node.js" },
    {
      name: "description",
      content:
        "High-performance binary serialization library with Python and Node.js bindings. Smaller than JSON, faster encoding, no schema required. Deterministic output for hashing and caching. Open source C core.",
    },
    {
      name: "keywords",
      content: "binary serialization, data format, python serialization, nodejs serialization, binary encoding, msgpack alternative, protobuf alternative, json alternative, deterministic serialization, high performance serialization, data interchange format, zero-copy encoding",
    },
    // Open Graph
    { property: "og:title", content: "Crous - Deterministic Binary Document Format" },
    { property: "og:description", content: "High-performance binary serialization library for Python and Node.js. Smaller than JSON, no schema required." },
    { property: "og:type", content: "website" },
    { property: "og:url", content: "https://crous.dev/" },
    { property: "og:image", content: "https://crous.dev/logo.png" },
    // Twitter
    { name: "twitter:card", content: "summary_large_image" },
    { name: "twitter:title", content: "Crous - Deterministic Binary Document Format" },
    { name: "twitter:description", content: "High-performance binary serialization library for Python and Node.js. Smaller than JSON, no schema required." },
    { name: "twitter:image", content: "https://crous.dev/logo.png" },
    // Canonical
    { tagName: "link", rel: "canonical", href: "https://crous.dev/" },
  ];
}

/* ─── Benchmark Data (real tests: Python 3.14, ARM64 Apple Silicon, 500 iters) ─── */

const benchmarks = {
  serialization: [
    { label: "Small API Response", crous: 639, json: 366, msgpack: 555, protobuf: 85, unit: "K ops/s" },
    { label: "Config Object", crous: 315, json: 216, msgpack: 392, protobuf: 46, unit: "K ops/s" },
    { label: "Text-Heavy Document", crous: 7.0, json: 4.8, msgpack: 16.3, protobuf: 0.7, unit: "K ops/s" },
    { label: "Numeric Payload", crous: 1.1, json: 0.54, msgpack: 3.2, protobuf: 0.14, unit: "K ops/s" },
  ],
};

export default function Home() {
  const [copied, setCopied] = useState(false);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* Background Effects */}
      <div className="fixed inset-0 bg-grid opacity-15 pointer-events-none" />
      <div className="fixed inset-0 bg-gradient-to-b from-transparent via-[#02040a]/80 to-[#02040a] pointer-events-none" />

      <main className="relative flex-1">
        {/* ════════════════════════════════════════════════════════════
            HERO
        ════════════════════════════════════════════════════════════ */}
        <section className="relative overflow-hidden">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[500px] bg-crous-500/8 rounded-[100%] blur-[120px] pointer-events-none" />
          <div className="absolute top-40 -left-40 w-80 h-80 bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />

          <div className="max-w-7xl mx-auto px-6 lg:px-8 pt-32 pb-20">
            {/* Version badge */}
            <div className="flex justify-center mb-8">
              <div className="inline-flex items-center gap-2 bg-zinc-900/60 border border-white/10 rounded-full px-4 py-1.5 text-sm text-gray-400">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-crous-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-crous-500" />
                </span>
                <span className="font-mono tracking-wide">v2.0.0</span>
                <span className="text-crous-400 text-xs font-semibold bg-crous-500/15 px-2 py-0.5 rounded-full border border-crous-500/20">
                  STABLE
                </span>
              </div>
            </div>

            <h1 className="text-center text-5xl sm:text-6xl md:text-8xl font-extrabold tracking-tighter mb-6 leading-[0.95]">
              <span className="bg-gradient-to-r from-white via-white to-gray-400 bg-clip-text text-transparent">
                A{" "}
              </span>
              <span className="gradient-text">Deterministic</span>
              <span className="bg-gradient-to-r from-white via-white to-gray-400 bg-clip-text text-transparent">
                {" "}Binary
              </span>
              <br />
              <span className="bg-gradient-to-r from-white via-white to-gray-400 bg-clip-text text-transparent">
                Document{" "}
              </span>
              <span className="gradient-text">Format</span>
            </h1>

            <p className="text-center text-lg md:text-xl text-gray-400 font-light max-w-2xl mx-auto mb-4">
              Smaller than JSON. No schema required.
            </p>
            <p className="text-center text-sm text-gray-500 font-light max-w-xl mx-auto mb-12">
              C core with native bindings for Python & Node.js. Arena-allocated,
              zigzag-varint encoded, depth-limited, and thread-safe.
            </p>

            {/* CTA */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-10">
              <Link
                to="/docs"
                className="bg-white text-black hover:bg-crous-400 hover:shadow-[0_0_24px_rgba(74,222,128,0.35)] px-6 py-3 rounded-lg text-sm font-semibold transition-all duration-300 flex items-center gap-2"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="https://github.com/axiomchronicles/crous"
                target="_blank"
                rel="noreferrer"
                className="px-6 py-3 rounded-lg bg-white/5 text-gray-300 text-sm font-medium border border-white/10 hover:border-white/20 hover:bg-white/10 transition-all duration-300"
              >
                View on GitHub
              </a>
            </div>

            {/* Install */}
            <div className="flex justify-center gap-3 flex-wrap mb-20">
              <button
                onClick={() => handleCopy("pip install crous")}
                className="group flex items-center gap-3 px-5 py-3 bg-[#0A0A0A] border border-white/10 rounded-xl hover:border-crous-500/30 transition-all duration-300"
              >
                <PythonIcon className="w-4 h-4 opacity-60" />
                <span className="font-mono text-gray-500 text-sm">$</span>
                <span className="font-mono text-white text-sm">pip install crous</span>
                <span className="border-l border-white/10 pl-3">
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-crous-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 text-gray-500 group-hover:text-crous-400 transition-colors" />
                  )}
                </span>
              </button>
              <button
                onClick={() => handleCopy("npm install crous")}
                className="group flex items-center gap-3 px-5 py-3 bg-[#0A0A0A] border border-white/10 rounded-xl hover:border-crous-500/30 transition-all duration-300"
              >
                <NodejsIcon className="w-4 h-4 opacity-60" />
                <span className="font-mono text-gray-500 text-sm">$</span>
                <span className="font-mono text-white text-sm">npm install crous</span>
              </button>
            </div>

            {/* Code Example */}
            <div className="max-w-3xl mx-auto">
              <CodeBlock
                language="python"
                filename="example.py"
                code={`import crous

# Serialize any Python object
data = {
    "name": "Alice",
    "scores": [98, 95, 100],
    "active": True
}

# Encode → compact binary
binary = crous.dumps(data)   # 42 bytes (vs 76 bytes JSON)

# Decode → original object
result = crous.loads(binary)
assert result == data`}
              />
            </div>
          </div>
        </section>

        {/* ════════════════════════════════════════════════════════════
            BENCHMARKS
        ════════════════════════════════════════════════════════════ */}
        <section className="relative py-32">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-crous-500/[0.02] to-transparent pointer-events-none" />

          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center mb-4">
              <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-crous-400 mb-3">
                Benchmarks
              </span>
              <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-4">
                Measured, not marketed
              </h2>
              <p className="text-gray-400 font-light max-w-xl mx-auto text-sm">
                Real numbers from Python 3.14 on Apple Silicon (ARM64).
                500 iterations per benchmark. No cherry-picking.
              </p>
            </div>

            {/* Serialization Bars */}
            <div className="mt-16">
              <h3 className="text-white font-bold text-lg mb-6 flex items-center gap-2">
                <Gauge className="w-5 h-5 text-crous-400" />
                Serialization Throughput
              </h3>
              <div className="space-y-6">
                {benchmarks.serialization.map((row) => {
                  const max = Math.max(row.crous, row.json, row.msgpack, row.protobuf);
                  return (
                    <div key={row.label} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-400 font-medium">{row.label}</span>
                        <span className="text-xs text-gray-600 font-mono">{row.unit}</span>
                      </div>
                      <div className="space-y-1.5">
                        <BenchBar label="Crous" value={row.crous} max={max} color="bg-crous-500" />
                        <BenchBar label="JSON" value={row.json} max={max} color="bg-gray-500" />
                        <BenchBar label="MsgPack" value={row.msgpack} max={max} color="bg-orange-500" />
                        <BenchBar label="Protobuf" value={row.protobuf} max={max} color="bg-blue-500" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Size Table */}
            <div className="mt-16">
              <h3 className="text-white font-bold text-lg mb-6 flex items-center gap-2">
                <Binary className="w-5 h-5 text-crous-400" />
                Output Size
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left text-gray-500 font-semibold uppercase tracking-wider text-xs py-3 pr-4">Dataset</th>
                      <th className="text-right text-crous-400 font-semibold uppercase tracking-wider text-xs py-3 px-4">Crous</th>
                      <th className="text-right text-gray-500 font-semibold uppercase tracking-wider text-xs py-3 px-4">JSON</th>
                      <th className="text-right text-orange-400 font-semibold uppercase tracking-wider text-xs py-3 px-4">MsgPack</th>
                      <th className="text-right text-blue-400 font-semibold uppercase tracking-wider text-xs py-3 px-4">Protobuf</th>
                    </tr>
                  </thead>
                  <tbody className="font-mono text-xs">
                    <tr className="border-b border-white/5">
                      <td className="py-3 pr-4 text-gray-400 font-sans">Small API</td>
                      <td className="py-3 px-4 text-right text-crous-400 font-bold">227 B</td>
                      <td className="py-3 px-4 text-right text-gray-400">272 B</td>
                      <td className="py-3 px-4 text-right text-gray-400">216 B</td>
                      <td className="py-3 px-4 text-right text-gray-400">346 B</td>
                    </tr>
                    <tr className="border-b border-white/5">
                      <td className="py-3 pr-4 text-gray-400 font-sans">Config Object</td>
                      <td className="py-3 px-4 text-right text-crous-400 font-bold">749 B</td>
                      <td className="py-3 px-4 text-right text-gray-400">955 B</td>
                      <td className="py-3 px-4 text-right text-gray-400">750 B</td>
                      <td className="py-3 px-4 text-right text-gray-400">1,132 B</td>
                    </tr>
                    <tr className="border-b border-white/5">
                      <td className="py-3 pr-4 text-gray-400 font-sans">Large Records</td>
                      <td className="py-3 px-4 text-right text-crous-400 font-bold">224.9 KB</td>
                      <td className="py-3 px-4 text-right text-gray-400">286.3 KB</td>
                      <td className="py-3 px-4 text-right text-gray-400">220.0 KB</td>
                      <td className="py-3 px-4 text-right text-gray-400">334.0 KB</td>
                    </tr>
                    <tr>
                      <td className="py-3 pr-4 text-gray-400 font-sans">Numeric</td>
                      <td className="py-3 px-4 text-right text-crous-400 font-bold">207.1 KB</td>
                      <td className="py-3 px-4 text-right text-gray-400">219.1 KB</td>
                      <td className="py-3 px-4 text-right text-gray-400">156.4 KB</td>
                      <td className="py-3 px-4 text-right text-gray-400">249.9 KB</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="text-[11px] text-gray-600 mt-4 font-light">
                Protobuf measured using schema-less google.protobuf.Struct (fair comparison — all formats used without pre-defined schemas).
                MsgPack wins on raw numeric payloads; Crous wins on structured data.
              </p>
            </div>
          </div>
        </section>

        {/* ════════════════════════════════════════════════════════════
            DESIGN PHILOSOPHY
        ════════════════════════════════════════════════════════════ */}
        <section className="relative py-32">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center mb-16">
              <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-crous-400 mb-3">
                Philosophy
              </span>
              <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-4">
                Built for determinism
              </h2>
              <p className="text-gray-400 font-light max-w-xl mx-auto text-sm">
                Every design decision serves a single goal: the same data must always
                produce the same bytes, fast.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <PhilosophyCard
                icon={<Binary className="w-6 h-6" />}
                title="Schema-Free"
                description="No .proto files. No code generation. Serialize any structure directly — the type system is inferred from the data."
              />
              <PhilosophyCard
                icon={<Zap className="w-6 h-6" />}
                title="Zero-Copy Where Possible"
                description="The C core reads directly from buffer memory. String and bytes values reference the source buffer without allocation."
              />
              <PhilosophyCard
                icon={<Cpu className="w-6 h-6" />}
                title="Single-Pass Encoding"
                description="Data is written in one forward pass. No backpatching, no length-prefix lookups, no two-phase serialization."
              />
              <PhilosophyCard
                icon={<MemoryStick className="w-6 h-6" />}
                title="Arena Allocation"
                description="All memory is allocated from a per-operation arena and freed in one shot. No per-node malloc/free churn."
              />
              <PhilosophyCard
                icon={<Shield className="w-6 h-6" />}
                title="Bounded Recursion"
                description="Configurable nesting depth limit (default: 64). Prevents stack overflow from adversarial or malformed input."
              />
              <PhilosophyCard
                icon={<Lock className="w-6 h-6" />}
                title="Deterministic Output"
                description="Identical input always produces identical bytes. Critical for content-addressable storage and digest verification."
              />
            </div>
          </div>
        </section>

        {/* ════════════════════════════════════════════════════════════
            INTERNAL ARCHITECTURE
        ════════════════════════════════════════════════════════════ */}
        <section className="relative py-32">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-500/[0.02] to-transparent pointer-events-none" />

          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center mb-16">
              <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-crous-400 mb-3">
                Internals
              </span>
              <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-4">
                How it works{" "}
                <span className="gradient-text">under the hood</span>
              </h2>
              <p className="text-gray-400 font-light max-w-xl mx-auto text-sm">
                From Python dict to compact binary — a single-pass pipeline through
                the modular C core.
              </p>
            </div>

            {/* Animated Data Flow */}
            <div className="mb-20">
              <h3 className="text-white font-bold text-lg mb-6 flex items-center gap-2">
                <Activity className="w-5 h-5 text-crous-400" />
                Encoding Pipeline
              </h3>
              <div className="rounded-2xl p-4 sm:p-8">
                <DataFlowAnimation />
              </div>
            </div>

            {/* Architecture Diagram */}
            <div>
              <h3 className="text-white font-bold text-lg mb-6 flex items-center gap-2">
                <CircuitBoard className="w-5 h-5 text-crous-400" />
                Module Architecture
              </h3>
              <div className="rounded-2xl p-4 sm:p-8">
                <ArchitectureDiagram />
              </div>
              <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
                <ArchDetail label="Integers" detail="Zigzag + varint encoding. 0 costs 1 byte, ±63 costs 1 byte, full i64 costs up to 10 bytes." />
                <ArchDetail label="Strings" detail="UTF-8 validated. Length-prefixed with varint. No null terminator stored." />
                <ArchDetail label="Collections" detail="Tag byte + varint count + inline children. No offset tables needed." />
              </div>
            </div>
          </div>
        </section>

        {/* ════════════════════════════════════════════════════════════
            FORMAT COMPARISON
        ════════════════════════════════════════════════════════════ */}
        <section className="relative py-32">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center mb-16">
              <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-crous-400 mb-3">
                Comparison
              </span>
              <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-4">
                Honest trade-offs
              </h2>
              <p className="text-gray-400 font-light max-w-xl mx-auto text-sm">
                Every format has strengths. Here's where Crous fits — and where it doesn't.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left text-gray-500 font-semibold uppercase tracking-wider text-xs py-4 pr-4">Feature</th>
                    <th className="text-center text-crous-400 font-semibold uppercase tracking-wider text-xs py-4 px-3">Crous</th>
                    <th className="text-center text-gray-500 font-semibold uppercase tracking-wider text-xs py-4 px-3">JSON</th>
                    <th className="text-center text-orange-400 font-semibold uppercase tracking-wider text-xs py-4 px-3">MsgPack</th>
                    <th className="text-center text-blue-400 font-semibold uppercase tracking-wider text-xs py-4 px-3">Protobuf</th>
                  </tr>
                </thead>
                <tbody className="text-xs">
                  <CompRow feature="Schema Required" crous="No" json="No" msgpack="No" protobuf="Yes" crousWins />
                  <CompRow feature="Human Readable" crous="CROUT mode" json="Yes" msgpack="No" protobuf="No" />
                  <CompRow feature="Binary Format" crous="Yes" json="No" msgpack="Yes" protobuf="Yes" crousWins />
                  <CompRow feature="Native Tuple/Set" crous="Yes" json="No" msgpack="No" protobuf="No" crousWins />
                  <CompRow feature="Tagged Values" crous="Yes" json="No" msgpack="Ext types" protobuf="Any" crousWins />
                  <CompRow feature="Streaming" crous="Yes" json="No" msgpack="Yes" protobuf="Yes" />
                  <CompRow feature="Deterministic" crous="Yes" json="Impl-dep." msgpack="Mostly" protobuf="No" crousWins />
                  <CompRow feature="Language Support" crous="2 SDKs" json="Universal" msgpack="30+ langs" protobuf="12+ langs" />
                  <CompRow feature="Zero-Copy Decode" crous="Partial" json="No" msgpack="Partial" protobuf="Yes" />
                  <CompRow feature="Depth Limiting" crous="Built-in" json="No" msgpack="No" protobuf="No" crousWins />
                </tbody>
              </table>
            </div>

            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-6 bg-crous-500/5 border border-crous-500/15 rounded-2xl">
                <h4 className="text-crous-400 font-bold text-sm mb-2">Where Crous excels</h4>
                <ul className="text-gray-400 text-sm space-y-1 font-light">
                  <li>• Small-to-medium structured payloads (API responses, configs)</li>
                  <li>• Python-native types: tuple, set, frozenset, bytes, complex</li>
                  <li>• Deterministic encoding for content-addressable storage</li>
                  <li>• Rapid prototyping without schema definition</li>
                </ul>
              </div>
              <div className="p-6 bg-white/[0.02] border border-white/10 rounded-2xl">
                <h4 className="text-gray-400 font-bold text-sm mb-2">Where others win</h4>
                <ul className="text-gray-500 text-sm space-y-1 font-light">
                  <li>• MsgPack: faster on large numeric arrays; broader language ecosystem</li>
                  <li>• Protobuf: schema evolution, strong typing, gRPC integration</li>
                  <li>• JSON: universal compatibility, human readability</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ════════════════════════════════════════════════════════════
            USE CASES
        ════════════════════════════════════════════════════════════ */}
        <section className="relative py-32">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-crous-500/[0.02] to-transparent pointer-events-none" />

          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center mb-16">
              <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-crous-400 mb-3">
                Use Cases
              </span>
              <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-4">
                Where Crous fits
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <UseCaseCard
                icon={<Server className="w-6 h-6" />}
                title="Edge & Embedded"
                description="Small binary footprint on IoT, Raspberry Pi, or edge gateways where every byte counts."
              />
              <UseCaseCard
                icon={<Gamepad2 className="w-6 h-6" />}
                title="Game State & Save Files"
                description="Deterministic serialization of complex game state with native tuple and set support."
              />
              <UseCaseCard
                icon={<Radio className="w-6 h-6" />}
                title="IPC & Microservices"
                description="Fast inter-process communication. Encode in Python, decode in Node.js — identical wire format."
              />
              <UseCaseCard
                icon={<Database className="w-6 h-6" />}
                title="Content-Addressable Storage"
                description="Deterministic output means the same data always hashes to the same digest."
              />
              <UseCaseCard
                icon={<Activity className="w-6 h-6" />}
                title="Telemetry & Logging"
                description="Streaming API for appending records without re-encoding the entire file."
              />
              <UseCaseCard
                icon={<FileCode2 className="w-6 h-6" />}
                title="Config & Data Files"
                description="CROUT text format for human-readable configs; FLUX binary for production deployment."
              />
            </div>
          </div>
        </section>

        {/* ════════════════════════════════════════════════════════════
            SAFETY & RELIABILITY
        ════════════════════════════════════════════════════════════ */}
        <section className="relative py-32">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center mb-16">
              <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-crous-400 mb-3">
                Safety
              </span>
              <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-4">
                Safety is not optional
              </h2>
              <p className="text-gray-400 font-light max-w-xl mx-auto text-sm">
                The C core is written defensively. Every untrusted input path is bounded and validated.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
              <SafetyItem
                icon={<ShieldCheck className="w-5 h-5" />}
                title="Arena Memory Safety"
                description="All allocations go through a per-operation arena. No dangling pointers, no use-after-free — the entire arena is reclaimed in one call."
              />
              <SafetyItem
                icon={<CircuitBoard className="w-5 h-5" />}
                title="Bounded Recursion"
                description="Configurable nesting depth limit (default 64). Prevents stack overflow from deeply nested or adversarial payloads."
              />
              <SafetyItem
                icon={<Lock className="w-5 h-5" />}
                title="Thread Safety"
                description="The Python binding releases the GIL during encode/decode. No shared mutable state between operations."
              />
              <SafetyItem
                icon={<Shield className="w-5 h-5" />}
                title="Input Validation"
                description="UTF-8 strings are validated on decode. Varint overflows are checked. Truncated buffers return structured errors."
              />
            </div>

            <div className="mt-12 max-w-3xl mx-auto">
              <CodeBlock
                language="python"
                filename="safety.py"
                code={`import crous

# Depth limiting — prevents stack overflow
crous.dumps(nested_data, max_depth=32)

# Graceful error handling
try:
    result = crous.loads(untrusted_bytes)
except crous.CrousDecodeError as e:
    print(f"Invalid payload: {e}")

# Thread-safe — GIL released during C operations
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(crous.loads, payloads))`}
              />
            </div>
          </div>
        </section>

        {/* ════════════════════════════════════════════════════════════
            SDKs
        ════════════════════════════════════════════════════════════ */}
        <section className="relative py-32">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-crous-500/[0.02] to-transparent pointer-events-none" />

          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-4">
                Native SDKs
              </h2>
              <p className="text-gray-400 font-light text-sm">
                Same wire format. Same semantics. Pick your runtime.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
              <Link
                to="/docs/python"
                className="group relative p-8 bg-[#0A0A0A] border border-white/10 rounded-2xl hover:-translate-y-1 hover:shadow-2xl hover:shadow-crous-900/20 transition-all duration-300"
              >
                <div className="absolute -inset-0.5 bg-gradient-to-r from-[#3776AB] to-crous-500 rounded-2xl blur opacity-0 group-hover:opacity-20 transition-opacity duration-300" />
                <div className="relative">
                  <div className="flex items-center gap-4 mb-4">
                    <PythonIcon className="w-12 h-12" />
                    <div>
                      <h3 className="text-xl font-bold text-white">Python SDK</h3>
                      <span className="text-xs font-mono text-crous-400">C extension · Python 3.6+</span>
                    </div>
                  </div>
                  <p className="text-gray-400 text-sm font-light mb-4">
                    Full FLUX binary, CROUT text, and streaming support. Custom serializers.
                    Native tuple, set, frozenset, bytes, and complex number support.
                  </p>
                  <span className="text-crous-400 text-sm font-medium flex items-center gap-1">
                    Documentation <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </span>
                </div>
              </Link>

              <Link
                to="/docs/nodejs"
                className="group relative p-8 bg-[#0A0A0A] border border-white/10 rounded-2xl hover:-translate-y-1 hover:shadow-2xl hover:shadow-crous-900/20 transition-all duration-300"
              >
                <div className="absolute -inset-0.5 bg-gradient-to-r from-[#339933] to-crous-500 rounded-2xl blur opacity-0 group-hover:opacity-20 transition-opacity duration-300" />
                <div className="relative">
                  <div className="flex items-center gap-4 mb-4">
                    <NodejsIcon className="w-12 h-12" />
                    <div>
                      <h3 className="text-xl font-bold text-white">Node.js SDK</h3>
                      <span className="text-xs font-mono text-crous-400">N-API addon · ABI stable</span>
                    </div>
                  </div>
                  <p className="text-gray-400 text-sm font-light mb-4">
                    N-API native addon with cross-platform builds. File I/O, custom serializers,
                    and Buffer integration.
                  </p>
                  <span className="text-crous-400 text-sm font-medium flex items-center gap-1">
                    Documentation <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </span>
                </div>
              </Link>
            </div>
          </div>
        </section>

        {/* ════════════════════════════════════════════════════════════
            CTA
        ════════════════════════════════════════════════════════════ */}
        <section className="relative py-32">
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-t from-crous-500/5 to-transparent pointer-events-none" />
          </div>
          <div className="relative max-w-3xl mx-auto text-center px-6">
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white mb-4">
              Start building
            </h2>
            <p className="text-gray-400 font-light text-sm mb-8">
              Read the docs. Run the benchmarks. Build something fast.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/docs"
                className="bg-white text-black hover:bg-crous-400 hover:shadow-[0_0_24px_rgba(74,222,128,0.35)] px-8 py-3.5 rounded-lg text-sm font-semibold transition-all duration-300 flex items-center gap-2"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="https://github.com/axiomchronicles/crous"
                target="_blank"
                rel="noreferrer"
                className="px-8 py-3.5 rounded-lg bg-white/5 text-gray-300 text-sm font-medium border border-white/10 hover:border-white/20 hover:bg-white/10 transition-all duration-300"
              >
                GitHub →
              </a>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}

/* ─── Sub-Components ──────────────────────────────────────────── */

function BenchBar({
  label,
  value,
  max,
  color,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
}) {
  const pct = Math.max((value / max) * 100, 2);
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-500 w-16 text-right font-mono shrink-0">{label}</span>
      <div className="flex-1 h-5 bg-white/[0.03] rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-700 ease-out flex items-center justify-end pr-2`}
          style={{ width: `${pct}%` }}
        >
          <span className="text-[10px] font-mono text-white/90 font-bold whitespace-nowrap">
            {value >= 1 ? value.toLocaleString() : value}
          </span>
        </div>
      </div>
    </div>
  );
}

function PhilosophyCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="group p-7 bg-[#0A0A0A] border border-white/10 rounded-2xl hover:-translate-y-0.5 hover:border-white/15 transition-all duration-300">
      <div className="text-crous-500 mb-4 drop-shadow-[0_0_6px_rgba(34,197,94,0.3)]">
        {icon}
      </div>
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-gray-400 text-sm font-light leading-relaxed">{description}</p>
    </div>
  );
}

function ArchDetail({ label, detail }: { label: string; detail: string }) {
  return (
    <div className="p-4 bg-white/[0.02] border border-white/10 rounded-xl">
      <span className="text-crous-400 text-xs font-bold uppercase tracking-wider">
        {label}
      </span>
      <p className="text-gray-400 text-xs font-light leading-relaxed mt-1">{detail}</p>
    </div>
  );
}

function ModuleBlock({
  name,
  desc,
  color,
}: {
  name: string;
  desc: string;
  color: string;
}) {
  const borderColors: Record<string, string> = {
    crous: "border-crous-500/20 bg-crous-500/5",
    blue: "border-blue-500/20 bg-blue-500/5",
    purple: "border-purple-500/20 bg-purple-500/5",
    yellow: "border-yellow-500/20 bg-yellow-500/5",
    orange: "border-orange-500/20 bg-orange-500/5",
    gray: "border-white/10 bg-white/[0.03]",
  };
  return (
    <div className={`border rounded-xl px-5 py-4 ${borderColors[color] || borderColors.gray}`}>
      <code className="text-xs font-mono text-white font-bold">{name}</code>
      <p className="text-gray-400 text-xs font-light mt-1 leading-relaxed">{desc}</p>
    </div>
  );
}

function CompRow({
  feature,
  crous,
  json,
  msgpack,
  protobuf,
  crousWins = false,
}: {
  feature: string;
  crous: string;
  json: string;
  msgpack: string;
  protobuf: string;
  crousWins?: boolean;
}) {
  return (
    <tr className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
      <td className="py-3 pr-4 text-gray-400 font-medium">{feature}</td>
      <td className={`py-3 px-3 text-center font-mono ${crousWins ? "text-crous-400 font-bold" : "text-gray-400"}`}>
        {crous}
      </td>
      <td className="py-3 px-3 text-center text-gray-500 font-mono">{json}</td>
      <td className="py-3 px-3 text-center text-gray-500 font-mono">{msgpack}</td>
      <td className="py-3 px-3 text-center text-gray-500 font-mono">{protobuf}</td>
    </tr>
  );
}

function UseCaseCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="group p-7 bg-[#0A0A0A] border border-white/10 rounded-2xl hover:-translate-y-0.5 hover:border-crous-500/20 transition-all duration-300">
      <div className="text-crous-500 mb-3">{icon}</div>
      <h3 className="text-white font-bold mb-2">{title}</h3>
      <p className="text-gray-400 text-sm font-light leading-relaxed">{description}</p>
    </div>
  );
}

function SafetyItem({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex gap-4 p-6 bg-white/[0.02] border border-white/10 rounded-2xl">
      <div className="text-crous-400 mt-0.5 shrink-0">{icon}</div>
      <div>
        <h4 className="text-white font-bold text-sm mb-1">{title}</h4>
        <p className="text-gray-400 text-xs font-light leading-relaxed">{description}</p>
      </div>
    </div>
  );
}
