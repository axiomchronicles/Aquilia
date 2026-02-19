import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Workflow, Zap, AlertCircle, ArrowRight, CheckCircle } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function ServerLifecycle() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Workflow className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                Lifecycle
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.lifecycle — Dependency-ordered startup and shutdown</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>LifecycleCoordinator</code> manages application startup and shutdown in
          dependency order, ensuring that services are initialized before their dependents
          and torn down in reverse order.
        </p>
      </div>

      {/* Phases */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          Lifecycle Phases
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The server transitions through these phases, defined in the <code>LifecyclePhase</code> enum:
        </p>

        <div className="flex flex-wrap gap-2 mb-6">
          {['INIT', 'STARTING', 'READY', 'STOPPING', 'STOPPED', 'ERROR'].map((phase, i) => {
            const colors: Record<string, string> = {
              INIT: isDark ? 'bg-gray-800 text-gray-300 border-gray-700' : 'bg-gray-100 text-gray-600 border-gray-200',
              STARTING: isDark ? 'bg-blue-900/40 text-blue-300 border-blue-800' : 'bg-blue-50 text-blue-600 border-blue-200',
              READY: isDark ? 'bg-emerald-900/40 text-emerald-300 border-emerald-800' : 'bg-emerald-50 text-emerald-600 border-emerald-200',
              STOPPING: isDark ? 'bg-amber-900/40 text-amber-300 border-amber-800' : 'bg-amber-50 text-amber-600 border-amber-200',
              STOPPED: isDark ? 'bg-gray-800 text-gray-400 border-gray-700' : 'bg-gray-100 text-gray-500 border-gray-200',
              ERROR: isDark ? 'bg-red-900/40 text-red-300 border-red-800' : 'bg-red-50 text-red-600 border-red-200',
            }
            return (
              <div key={phase} className="flex items-center gap-2">
                <span className={`px-3 py-1 rounded-lg border text-xs font-mono font-bold ${colors[phase]}`}>
                  {phase}
                </span>
                {i < 5 && <ArrowRight className={`w-3 h-3 ${isDark ? 'text-gray-600' : 'text-gray-300'}`} />}
              </div>
            )
          })}
        </div>

        <CodeBlock
          code={`from enum import Enum

class LifecyclePhase(str, Enum):
    INIT = "init"           # Server created, components wired
    STARTING = "starting"   # startup() called, hooks executing
    READY = "ready"         # All hooks complete, accepting requests
    STOPPING = "stopping"   # shutdown() called, hooks executing
    STOPPED = "stopped"     # All hooks complete, server down
    ERROR = "error"         # A lifecycle hook failed`}
          language="python"
        />
      </section>

      {/* LifecycleCoordinator */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          LifecycleCoordinator
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The coordinator is created during <code>AquiliaServer.__init__()</code> with a reference
          to the <code>RuntimeRegistry</code> and <code>ConfigLoader</code>:
        </p>

        <CodeBlock
          code={`class LifecycleCoordinator:
    """
    Manages dependency-ordered startup and shutdown of app components.
    
    Uses the RuntimeRegistry's dependency graph to determine execution order.
    Supports event observers for monitoring lifecycle transitions.
    """

    def __init__(self, runtime: RuntimeRegistry, config: ConfigLoader):
        self.runtime = runtime
        self.config = config
        self.phase = LifecyclePhase.INIT
        self._observers: list[Callable] = []
        self._started_apps: list[str] = []  # Track for reverse shutdown

    def on_event(self, callback: Callable) -> None:
        """Register a lifecycle event observer."""
        self._observers.append(callback)

    async def startup(self) -> None:
        """
        Execute startup hooks in dependency order.
        
        If app B depends on app A, A.on_startup() runs before B.on_startup().
        On failure, rolls back already-started apps by calling their on_shutdown().
        """
        self.phase = LifecyclePhase.STARTING
        self._emit_event("startup_begin")

        try:
            # Get apps in dependency order from RuntimeRegistry
            ordered_apps = self.runtime.get_dependency_ordered_apps()

            for app_name in ordered_apps:
                try:
                    await self._start_app(app_name)
                    self._started_apps.append(app_name)
                except Exception as e:
                    self.phase = LifecyclePhase.ERROR
                    self._emit_event("startup_error", app_name=app_name, error=e)
                    # Rollback: shutdown already-started apps in reverse
                    await self._rollback_startup()
                    raise LifecycleError(
                        f"Startup failed for '{app_name}': {e}"
                    ) from e

            self.phase = LifecyclePhase.READY
            self._emit_event("startup_complete")

        except LifecycleError:
            raise
        except Exception as e:
            self.phase = LifecyclePhase.ERROR
            raise

    async def shutdown(self) -> None:
        """
        Execute shutdown hooks in reverse dependency order.
        
        If app A was started before app B, B.on_shutdown() runs before A.on_shutdown().
        Errors in one app's shutdown don't prevent others from shutting down.
        """
        self.phase = LifecyclePhase.STOPPING
        self._emit_event("shutdown_begin")

        # Reverse order of startup
        for app_name in reversed(self._started_apps):
            try:
                await self._stop_app(app_name)
            except Exception as e:
                # Log but don't stop — other apps still need shutdown
                self._emit_event("shutdown_error", app_name=app_name, error=e)

        self.phase = LifecyclePhase.STOPPED
        self._emit_event("shutdown_complete")`}
          language="python"
        />
      </section>

      {/* Lifecycle hooks in controllers */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <CheckCircle className="w-5 h-5 text-aquilia-400" />
          Controller Lifecycle Hooks
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Controllers with <code>instantiation_mode = "singleton"</code> can implement lifecycle hooks
          that are called during startup/shutdown:
        </p>

        <CodeBlock
          code={`class DatabaseController(Controller):
    prefix = "/db"
    instantiation_mode = "singleton"  # Required for startup/shutdown hooks

    def __init__(self, db: Database):
        self.db = db
        self.pool = None

    async def on_startup(self, ctx: RequestCtx) -> None:
        """Called once during server startup."""
        self.pool = await self.db.create_pool(min_size=5, max_size=20)
        print("Database connection pool initialized")

    async def on_shutdown(self, ctx: RequestCtx) -> None:
        """Called once during server shutdown."""
        if self.pool:
            await self.pool.close()
        print("Database connection pool closed")

    async def on_request(self, ctx: RequestCtx) -> None:
        """Called before EVERY request (both singleton and per_request modes)."""
        ctx.state["db_conn"] = await self.pool.acquire()

    async def on_response(self, ctx: RequestCtx, response: Response) -> Response:
        """Called after EVERY request. Can modify the response."""
        conn = ctx.state.get("db_conn")
        if conn:
            await self.pool.release(conn)
        return response

    @GET("/status")
    async def status(self, ctx: RequestCtx) -> Response:
        pool_size = self.pool.size if self.pool else 0
        return Response.json({"pool_size": pool_size})`}
          language="python"
        />

        <div className={`mt-4 rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Hook</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>When Called</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Mode Requirement</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['on_startup(ctx)', 'Once during server startup', 'singleton only'],
                ['on_shutdown(ctx)', 'Once during server shutdown', 'singleton only'],
                ['on_request(ctx)', 'Before every request', 'Both modes'],
                ['on_response(ctx, response)', 'After every request', 'Both modes'],
              ].map(([hook, when, mode], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{hook}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{when}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{mode}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Lifecycle events */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <AlertCircle className="w-5 h-5 text-aquilia-400" />
          Event Observers
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The AquiliaServer registers two default observers on the LifecycleCoordinator:
        </p>

        <CodeBlock
          code={`# 1. Fault observer — logs lifecycle errors as structured faults
def _lifecycle_fault_observer(event):
    if event.error:
        logger.error(
            f"Lifecycle fault in phase {event.phase.value}: "
            f"app={event.app_name}, error={event.error}"
        )

# 2. Trace observer — records lifecycle events in .aquilia/lifecycle.log
def _lifecycle_trace_observer(event):
    self.trace.journal.record_phase(
        f"lifecycle:{event.phase.value}",
        app_name=event.app_name or "",
        error=str(event.error) if event.error else None,
        detail=event.message,
    )

# Register custom observers:
server.coordinator.on_event(my_custom_observer)`}
          language="python"
        />
      </section>

      {/* Rollback */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <AlertCircle className="w-5 h-5 text-rose-400" />
          Startup Rollback
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          If any app fails during startup, the coordinator automatically rolls back by calling
          <code>on_shutdown()</code> on all previously started apps in reverse order:
        </p>

        <CodeBlock
          code={`# Example: 3 apps, app C fails during startup
#
# 1. on_startup(app_A) → ✓ Success
# 2. on_startup(app_B) → ✓ Success
# 3. on_startup(app_C) → ✗ Error!
#
# Rollback:
# 4. on_shutdown(app_B) → Cleanup
# 5. on_shutdown(app_A) → Cleanup
#
# Raises: LifecycleError("Startup failed for 'app_C': ...")`}
          language="python"
        />

        <div className={`mt-4 rounded-lg border p-4 ${isDark ? 'bg-amber-500/10 border-amber-500/20' : 'bg-amber-50 border-amber-200'}`}>
          <p className={`text-sm ${isDark ? 'text-amber-300' : 'text-amber-700'}`}>
            <strong>Important:</strong> Shutdown errors during rollback are logged but do not propagate.
            This ensures that all started apps get a chance to clean up, even if one fails.
          </p>
        </div>
      </section>

      {/* Next */}
      <section className="mb-10">
        <div className="flex flex-col gap-2">
          <Link to="/docs/server/aquilia-server" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → AquiliaServer: Full server orchestration
          </Link>
          <Link to="/docs/di/lifecycle" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            → DI Lifecycle: Container-level lifecycle management
          </Link>
        </div>
      </section>
    
      <NextSteps />
    </div>
  )
}