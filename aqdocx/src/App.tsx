import { Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import { DocsLayout } from './components/DocsLayout'
import { LandingPage } from './pages/LandingPage'

// Getting Started
import { IntroductionPage } from './pages/docs/getting-started/Introduction'
import { InstallationPage } from './pages/docs/getting-started/Installation'
import { QuickStartPage } from './pages/docs/getting-started/QuickStart'
import { ArchitecturePage } from './pages/docs/getting-started/Architecture'
import { ProjectStructurePage } from './pages/docs/getting-started/ProjectStructure'

// Controllers
import { ControllersOverview } from './pages/docs/controllers/Overview'
import { ControllersDecorators } from './pages/docs/controllers/decorators'
import { ControllersRequestCtx } from './pages/docs/controllers/RequestCtx'
import { ControllersFactory } from './pages/docs/controllers/Factory'
import { ControllersEngine } from './pages/docs/controllers/Engine'
import { ControllersCompiler } from './pages/docs/controllers/Compiler'
import { ControllersRouter } from './pages/docs/controllers/Router'
import { ControllersOpenAPI } from './pages/docs/controllers/OpenAPI'

// Server
import { ServerOverview } from './pages/docs/server/Overview'
import { ServerASGI } from './pages/docs/server/ASGI'
import { ServerLifecycle } from './pages/docs/server/Lifecycle'

// Config
import { ConfigOverview } from './pages/docs/config/Overview'
import { ConfigWorkspace } from './pages/docs/config/Workspace'
import { ConfigModule } from './pages/docs/config/Module'
import { ConfigIntegrations } from './pages/docs/config/Integrations'

// Request / Response
import { RequestPage } from './pages/docs/request-response/Request'
import { ResponsePage } from './pages/docs/request-response/Response'
import { DataStructuresPage } from './pages/docs/request-response/DataStructures'
import { UploadsPage } from './pages/docs/request-response/Uploads'

// Routing
import { RoutingOverview } from './pages/docs/routing/Overview'

// DI
import { DIOverview } from './pages/docs/di/Overview'
import { DIContainer } from './pages/docs/di/Container'
import { DIProviders } from './pages/docs/di/Providers'
import { DIScopes } from './pages/docs/di/Scopes'
import { DIAdvanced } from './pages/docs/di/DIAdvanced'

// Models
import { ModelsOverview } from './pages/docs/models/Overview'
import { ModelsFields } from './pages/docs/models/Fields'
import { ModelsQuerySet } from './pages/docs/models/QuerySet'
import { ModelsRelationships } from './pages/docs/models/Relationships'
import { ModelsMigrations } from './pages/docs/models/Migrations'
import { ModelsAdvanced } from './pages/docs/models/Advanced'

// Serializers
import { SerializersOverview } from './pages/docs/serializers/Overview'

// Database
import { DatabaseOverview } from './pages/docs/database/Overview'

// Auth
import { AuthOverview } from './pages/docs/auth/Overview'
import { AuthIdentity } from './pages/docs/auth/Identity'
import { AuthGuards } from './pages/docs/auth/Guards'
import { AuthAdvanced } from './pages/docs/auth/Advanced'
import { AuthZPage } from './pages/docs/auth/AuthZ'

// Sessions
import { SessionsOverview } from './pages/docs/sessions/Overview'

// Middleware
import { MiddlewareOverview } from './pages/docs/middleware/Overview'
import { MiddlewareBuiltIn } from './pages/docs/middleware/BuiltIn'
import { MiddlewareExtended } from './pages/docs/middleware/Extended'

// Faults
import { FaultsOverview } from './pages/docs/faults/Overview'
import { FaultsEngine } from './pages/docs/faults/Engine'
import { FaultsAdvanced } from './pages/docs/faults/Advanced'

// Cache
import { CacheOverview } from './pages/docs/cache/Overview'

// WebSockets
import { WebSocketsOverview } from './pages/docs/websockets/Overview'

// Templates
import { TemplatesOverview } from './pages/docs/templates/Overview'

// Mail
import { MailOverview } from './pages/docs/mail/Overview'

// Effects
import { EffectsOverview } from './pages/docs/effects/Overview'

// Aquilary
import { AquilaryOverview } from './pages/docs/aquilary/Overview'

// MLOps
import { MLOpsOverview } from './pages/docs/mlops/Overview'

// CLI
import { CLIOverview } from './pages/docs/cli/Overview'

// Testing
import { TestingOverview } from './pages/docs/testing/Overview'

// Trace
import { TraceOverview } from './pages/docs/trace/Overview'

export default function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/docs" element={<DocsLayout />}>
          <Route index element={<IntroductionPage />} />
          <Route path="installation" element={<InstallationPage />} />
          <Route path="quickstart" element={<QuickStartPage />} />
          <Route path="architecture" element={<ArchitecturePage />} />
          <Route path="project-structure" element={<ProjectStructurePage />} />

          {/* Server */}
          <Route path="server" element={<ServerOverview />} />
          <Route path="server/aquilia-server" element={<ServerOverview />} />
          <Route path="server/asgi" element={<ServerASGI />} />
          <Route path="server/lifecycle" element={<ServerLifecycle />} />

          {/* Config */}
          <Route path="config" element={<ConfigOverview />} />
          <Route path="config/loader" element={<ConfigOverview />} />
          <Route path="config/workspace" element={<ConfigWorkspace />} />
          <Route path="config/module" element={<ConfigModule />} />
          <Route path="config/integrations" element={<ConfigIntegrations />} />

          {/* Request/Response */}
          <Route path="request-response" element={<RequestPage />} />
          <Route path="request-response/request" element={<RequestPage />} />
          <Route path="request-response/response" element={<ResponsePage />} />
          <Route path="request-response/data-structures" element={<DataStructuresPage />} />
          <Route path="request-response/uploads" element={<UploadsPage />} />

          {/* Controllers */}
          <Route path="controllers" element={<ControllersOverview />} />
          <Route path="controllers/overview" element={<ControllersOverview />} />
          <Route path="controllers/decorators" element={<ControllersDecorators />} />
          <Route path="controllers/request-ctx" element={<ControllersRequestCtx />} />
          <Route path="controllers/factory" element={<ControllersFactory />} />
          <Route path="controllers/engine" element={<ControllersEngine />} />
          <Route path="controllers/compiler" element={<ControllersCompiler />} />
          <Route path="controllers/router" element={<ControllersRouter />} />
          <Route path="controllers/openapi" element={<ControllersOpenAPI />} />

          {/* Routing */}
          <Route path="routing" element={<RoutingOverview />} />
          <Route path="routing/patterns" element={<RoutingOverview />} />
          <Route path="routing/router" element={<ControllersRouter />} />
          <Route path="routing/urls" element={<RoutingOverview />} />

          {/* DI */}
          <Route path="di" element={<DIOverview />} />
          <Route path="di/container" element={<DIContainer />} />
          <Route path="di/providers" element={<DIProviders />} />
          <Route path="di/scopes" element={<DIScopes />} />
          <Route path="di/decorators" element={<DIAdvanced />} />
          <Route path="di/lifecycle" element={<DIAdvanced />} />
          <Route path="di/diagnostics" element={<DIAdvanced />} />

          {/* Models */}
          <Route path="models" element={<ModelsOverview />} />
          <Route path="models/defining" element={<ModelsOverview />} />
          <Route path="models/fields" element={<ModelsFields />} />
          <Route path="models/queryset" element={<ModelsQuerySet />} />
          <Route path="models/relationships" element={<ModelsRelationships />} />
          <Route path="models/migrations" element={<ModelsMigrations />} />
          <Route path="models/signals" element={<ModelsAdvanced />} />
          <Route path="models/transactions" element={<ModelsAdvanced />} />
          <Route path="models/aggregation" element={<ModelsAdvanced />} />

          {/* Serializers */}
          <Route path="serializers" element={<SerializersOverview />} />
          <Route path="serializers/base" element={<SerializersOverview />} />
          <Route path="serializers/model" element={<SerializersOverview />} />
          <Route path="serializers/fields" element={<SerializersOverview />} />
          <Route path="serializers/validators" element={<SerializersOverview />} />
          <Route path="serializers/relations" element={<SerializersOverview />} />

          {/* Database */}
          <Route path="database" element={<DatabaseOverview />} />
          <Route path="database/engine" element={<DatabaseOverview />} />
          <Route path="database/sqlite" element={<DatabaseOverview />} />
          <Route path="database/postgresql" element={<DatabaseOverview />} />
          <Route path="database/mysql" element={<DatabaseOverview />} />

          {/* Auth */}
          <Route path="auth" element={<AuthOverview />} />
          <Route path="auth/identity" element={<AuthIdentity />} />
          <Route path="auth/credentials" element={<AuthAdvanced />} />
          <Route path="auth/manager" element={<AuthAdvanced />} />
          <Route path="auth/oauth" element={<AuthAdvanced />} />
          <Route path="auth/mfa" element={<AuthAdvanced />} />
          <Route path="auth/guards" element={<AuthGuards />} />
          <Route path="authz" element={<AuthZPage />} />
          <Route path="authz/rbac" element={<AuthZPage />} />
          <Route path="authz/abac" element={<AuthZPage />} />
          <Route path="authz/policies" element={<AuthZPage />} />

          {/* Sessions */}
          <Route path="sessions" element={<SessionsOverview />} />
          <Route path="sessions/overview" element={<SessionsOverview />} />
          <Route path="sessions/session-id" element={<SessionsOverview />} />
          <Route path="sessions/stores" element={<SessionsOverview />} />
          <Route path="sessions/policies" element={<SessionsOverview />} />

          {/* Middleware */}
          <Route path="middleware" element={<MiddlewareOverview />} />
          <Route path="middleware/stack" element={<MiddlewareOverview />} />
          <Route path="middleware/built-in" element={<MiddlewareBuiltIn />} />
          <Route path="middleware/static" element={<MiddlewareExtended />} />
          <Route path="middleware/cors" element={<MiddlewareExtended />} />
          <Route path="middleware/rate-limit" element={<MiddlewareExtended />} />
          <Route path="middleware/security" element={<MiddlewareExtended />} />

          {/* Aquilary */}
          <Route path="aquilary" element={<AquilaryOverview />} />
          <Route path="aquilary/overview" element={<AquilaryOverview />} />
          <Route path="aquilary/manifest" element={<AquilaryOverview />} />
          <Route path="aquilary/runtime" element={<AquilaryOverview />} />
          <Route path="aquilary/fingerprint" element={<AquilaryOverview />} />

          {/* Effects */}
          <Route path="effects" element={<EffectsOverview />} />
          <Route path="effects/overview" element={<EffectsOverview />} />
          <Route path="effects/dbtx" element={<EffectsOverview />} />
          <Route path="effects/cache" element={<EffectsOverview />} />

          {/* Faults */}
          <Route path="faults" element={<FaultsOverview />} />
          <Route path="faults/taxonomy" element={<FaultsOverview />} />
          <Route path="faults/engine" element={<FaultsEngine />} />
          <Route path="faults/handlers" element={<FaultsAdvanced />} />
          <Route path="faults/domains" element={<FaultsAdvanced />} />

          {/* Cache */}
          <Route path="cache" element={<CacheOverview />} />
          <Route path="cache/service" element={<CacheOverview />} />
          <Route path="cache/backends" element={<CacheOverview />} />
          <Route path="cache/decorators" element={<CacheOverview />} />

          {/* WebSockets */}
          <Route path="websockets" element={<WebSocketsOverview />} />
          <Route path="websockets/controllers" element={<WebSocketsOverview />} />
          <Route path="websockets/runtime" element={<WebSocketsOverview />} />
          <Route path="websockets/adapters" element={<WebSocketsOverview />} />

          {/* Templates */}
          <Route path="templates" element={<TemplatesOverview />} />
          <Route path="templates/engine" element={<TemplatesOverview />} />
          <Route path="templates/loaders" element={<TemplatesOverview />} />
          <Route path="templates/security" element={<TemplatesOverview />} />

          {/* Mail */}
          <Route path="mail" element={<MailOverview />} />
          <Route path="mail/service" element={<MailOverview />} />
          <Route path="mail/providers" element={<MailOverview />} />
          <Route path="mail/templates" element={<MailOverview />} />

          {/* MLOps */}
          <Route path="mlops" element={<MLOpsOverview />} />
          <Route path="mlops/modelpack" element={<MLOpsOverview />} />
          <Route path="mlops/registry" element={<MLOpsOverview />} />
          <Route path="mlops/serving" element={<MLOpsOverview />} />
          <Route path="mlops/drift" element={<MLOpsOverview />} />

          {/* CLI */}
          <Route path="cli" element={<CLIOverview />} />
          <Route path="cli/commands" element={<CLIOverview />} />
          <Route path="cli/generators" element={<CLIOverview />} />

          {/* Testing */}
          <Route path="testing" element={<TestingOverview />} />
          <Route path="testing/client" element={<TestingOverview />} />
          <Route path="testing/cases" element={<TestingOverview />} />
          <Route path="testing/mocks" element={<TestingOverview />} />

          {/* OpenAPI */}
          <Route path="openapi" element={<ControllersOpenAPI />} />

          {/* Trace */}
          <Route path="trace" element={<TraceOverview />} />
        </Route>
      </Routes>
    </ThemeProvider>
  )
}
