# AquilaMail — Architecture Document

> **Status**: Approved for implementation  
> **Version**: 1.0.0  
> **Author**: Aquilia Core Team  
> **Date**: 2026-02-16  

---

## 1. Executive Summary

AquilaMail is a production-ready, async-first mail subsystem for Aquilia.  It delivers
Django-like ergonomics (`send_mail`, `EmailMessage`, `EmailMultiAlternatives`) while adding
first-class Aquilia integrations: DI-scoped providers, manifest-driven wiring, the unique
**Aquilia Template Syntax (ATS)** (`<< expr >>`, `[[% control %]]`), provider plugins,
reliable delivery with retry/backoff, bounce/complaint processing, rate-limiting,
observability (metrics + tracing + structured logs), DKIM signing, and a CLI/admin API.

---

## 2. Component Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Developer API Layer                          │
│  send_mail() / asend_mail() / EmailMessage / TemplateMessage       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                    Template Renderer (ATS)                          │
│  Lexer → Parser → AST → Compiler → Bytecode cache                 │
│  Filters: title, currency, truncate, redact_pii, tojson            │
│  Security: auto-escape, sandbox, typed expression validation       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                    Envelope Builder                                 │
│  Validates addresses, computes digest (dedupe), attaches blobs,    │
│  sets idempotency key, assigns priority & tenant, builds headers   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                    Queue / Envelope Store                           │
│  SQLite (dev) / Postgres (prod) — persistent envelope table        │
│  Blob store (content-addressed attachments)                        │
│  Transactional semantics: commit/rollback with request lifecycle   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                    Dispatcher / Scheduler                           │
│  Min-heap priority dequeue (next_attempt_at, priority)             │
│  Batching engine (time-windowed + size-based flush)                │
│  Rate limiter: per-provider token bucket + per-domain bucket       │
│  Provider selection: round-robin / priority / affinity             │
│  Connection pooling per provider                                   │
└────────────┬────────────────────────────────┬──────────────────────┘
             │                                │
┌────────────▼────────────┐    ┌──────────────▼──────────────────────┐
│   Provider Plugins      │    │   Retry / Backoff Engine            │
│   ├─ SMTPProvider       │    │   base × 2^attempts + jitter        │
│   ├─ SESProvider        │    │   Transient vs permanent classify   │
│   └─ SendGridProvider   │    │   Idempotency key enforcement       │
│   Interface:            │    │   Max attempts + cap at 1h          │
│     send(envelope)      │    └─────────────────────────────────────┘
│     health_check()      │
│     supports_batching   │
└─────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────────────┐
│               Bounce & Complaint Processor                         │
│  Webhook ingestion → classification (permanent/transient)          │
│  Suppression list management with TTL                              │
│  Feedback loop integration                                         │
│  Admin alert on threshold breach                                   │
└─────────────────────────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────────────┐
│               Observability                                        │
│  Prometheus metrics (counters, histograms, gauges)                 │
│  OpenTelemetry trace spans (render → enqueue → dispatch → send)    │
│  Structured JSON logs with envelope_id, provider, attempt          │
│  Delivery event stream for webhooks                                │
└─────────────────────────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────────────┐
│               Security Layer                                       │
│  DKIM signing (per-domain keys)                                    │
│  TLS enforcement (STARTTLS / mandatory)                            │
│  Header normalization, anti-spoof                                  │
│  PII redaction utilities                                           │
│  Allowed-domain validation                                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Sequence Diagram — Happy Path

```
Developer         API          Renderer       Queue/Store     Dispatcher     Provider
   │                │              │              │               │              │
   │  send_mail()   │              │              │               │              │
   │───────────────►│              │              │               │              │
   │                │  render(tpl) │              │               │              │
   │                │─────────────►│              │               │              │
   │                │  html+text   │              │               │              │
   │                │◄─────────────│              │               │              │
   │                │  build_envelope()           │               │              │
   │                │────────────────────────────►│               │              │
   │                │         envelope_id         │               │              │
   │                │◄────────────────────────────│               │              │
   │   envelope_id  │              │              │               │              │
   │◄───────────────│              │              │               │              │
   │                │              │              │  poll()        │              │
   │                │              │              │◄──────────────│              │
   │                │              │              │  envelope      │              │
   │                │              │              │───────────────►│              │
   │                │              │              │               │  send(env)   │
   │                │              │              │               │─────────────►│
   │                │              │              │               │  result      │
   │                │              │              │               │◄─────────────│
   │                │              │              │  update status │              │
   │                │              │              │◄──────────────│              │
```

---

## 4. Data Models (Schema)

### 4.1 `mail_envelopes` — Persistent Queue

| Column              | Type         | Notes                                       |
|---------------------|-------------|---------------------------------------------|
| `id`                | UUID PK     | v4 UUID                                      |
| `created_at`        | TIMESTAMP   | UTC, indexed                                 |
| `status`            | VARCHAR(20) | queued/sending/sent/failed/bounced/cancelled |
| `priority`          | INTEGER     | 0=critical, 50=normal, 100=bulk              |
| `from_email`        | TEXT        | RFC 5322 address                             |
| `to`                | JSON        | `["a@b.com"]`                                |
| `cc`                | JSON        | nullable                                     |
| `bcc`               | JSON        | nullable                                     |
| `reply_to`          | TEXT        | nullable                                     |
| `subject`           | TEXT        |                                              |
| `body_text`         | TEXT        | Plain text body                              |
| `body_html`         | TEXT        | HTML body (nullable)                         |
| `headers`           | JSON        | Extra headers                                |
| `template_name`     | TEXT        | nullable, e.g. `welcome.aqt`                |
| `template_context`  | JSON        | nullable, context used for render            |
| `attachments`       | JSON        | `[{"digest":"sha256...", "filename":"f.pdf", "content_type":"..."}]` |
| `attempts`          | INTEGER     | default 0                                    |
| `max_attempts`      | INTEGER     | default 5                                    |
| `last_attempt_at`   | TIMESTAMP   | nullable                                     |
| `next_attempt_at`   | TIMESTAMP   | indexed (composite with priority)            |
| `provider_name`     | TEXT        | nullable, last/preferred provider            |
| `provider_message_id`| TEXT       | nullable, provider's tracking ID             |
| `idempotency_key`   | TEXT        | nullable, unique                             |
| `tenant_id`         | TEXT        | nullable, for multi-tenant                   |
| `trace_id`          | TEXT        | nullable, OpenTelemetry trace                |
| `digest`            | VARCHAR(64) | SHA-256 for deduplication                    |
| `metadata`          | JSON        | `{"kind":"transactional","tags":[...]}`      |
| `error_message`     | TEXT        | nullable, last error                         |

**Indexes**:
- `ix_envelope_dequeue`: `(status, next_attempt_at, priority)` — efficient dequeue
- `ix_envelope_digest`: `(digest)` — deduplication window
- `ix_envelope_idempotency`: `(idempotency_key)` UNIQUE WHERE NOT NULL
- `ix_envelope_tenant`: `(tenant_id, status)` — tenant queries

### 4.2 `mail_blobs` — Content-Addressed Attachment Store

| Column         | Type        | Notes                          |
|----------------|------------|--------------------------------|
| `digest`       | VARCHAR(64) PK | SHA-256 of content          |
| `storage_path` | TEXT        | FS path or S3 key              |
| `size`         | INTEGER     | bytes                          |
| `content_type` | TEXT        | MIME type                      |
| `created_at`   | TIMESTAMP   |                                |

### 4.3 `mail_providers` — Provider Registry

| Column              | Type        | Notes                         |
|---------------------|------------|-------------------------------|
| `name`              | TEXT PK     | e.g. `smtp_primary`           |
| `type`              | TEXT        | `smtp` / `ses` / `sendgrid`   |
| `config`            | JSON        | connection params (encrypted)  |
| `priority`          | INTEGER     | lower = preferred              |
| `rate_limit_per_min` | INTEGER   | per-provider cap               |
| `enabled`           | BOOLEAN     | soft disable                   |
| `last_health_check` | TIMESTAMP   | nullable                      |
| `health_status`     | TEXT        | `healthy` / `degraded` / `down`|

### 4.4 `mail_suppression` — Suppression List

| Column       | Type        | Notes                            |
|-------------|------------|----------------------------------|
| `email`     | TEXT PK     | normalized lowercase             |
| `reason`    | TEXT        | `hard_bounce` / `complaint` / `unsubscribe` |
| `source`    | TEXT        | provider name or `manual`        |
| `created_at`| TIMESTAMP   |                                  |
| `expires_at`| TIMESTAMP   | nullable (permanent if NULL)     |

### 4.5 `mail_deliveries` — Delivery Log

| Column              | Type      | Notes                         |
|---------------------|----------|-------------------------------|
| `id`                | UUID PK  |                               |
| `envelope_id`       | UUID FK  | → mail_envelopes              |
| `provider_name`     | TEXT     |                               |
| `provider_response` | JSON     | raw response                  |
| `provider_message_id`| TEXT    |                               |
| `delivered_at`      | TIMESTAMP|                               |
| `latency_ms`        | INTEGER  |                               |

### 4.6 `mail_events` — Webhook / Delivery Events

| Column        | Type      | Notes                           |
|--------------|---------|---------------------------------|
| `id`         | UUID PK |                                 |
| `envelope_id`| UUID FK | nullable                        |
| `event_type` | TEXT    | `delivered`/`bounced`/`complained`/`opened`/`clicked` |
| `provider`   | TEXT    |                                 |
| `payload`    | JSON    | raw webhook payload             |
| `created_at` | TIMESTAMP|                                |

---

## 5. Aquilia Template Syntax (ATS) — Grammar

### 5.1 Design Rationale

ATS uses `<< >>` for expressions and `[[% %]]` for control flow — deliberately
distinct from HTML (`< >`), Jinja2 (`{{ }}`), and Django (`{% %}`).  This avoids
any collision with HTML attributes, JavaScript template literals, or embedded JSON.

### 5.2 EBNF Grammar

```ebnf
template       = { text | expression | control_block | comment } ;

(* Expressions *)
expression     = "<<" , ws , expr_chain , ws , ">>" ;
expr_chain     = primary , { "|" , filter_call } ;
primary        = dotted_name | function_call | literal ;
dotted_name    = IDENT , { "." , IDENT } ;
function_call  = IDENT , "(" , [ arg_list ] , ")" ;
arg_list       = expr_chain , { "," , expr_chain } ;
filter_call    = IDENT , [ "(" , arg_list , ")" ] ;

(* Control flow *)
control_block  = if_block | for_block | block_block | include_stmt | macro_block ;

if_block       = "[[%" , ws , "if" , ws , expr_chain , ws , "%]]"
                 , template
                 , { "[[%" , ws , "elif" , ws , expr_chain , ws , "%]]" , template }
                 , [ "[[%" , ws , "else" , ws , "%]]" , template ]
                 , "[[%" , ws , "endif" , ws , "%]]" ;

for_block      = "[[%" , ws , "for" , ws , IDENT , ws , "in" , ws , expr_chain , ws , "%]]"
                 , template
                 , [ "[[%" , ws , "else" , ws , "%]]" , template ]
                 , "[[%" , ws , "endfor" , ws , "%]]" ;

block_block    = "[[%" , ws , "block" , ws , IDENT , ws , "%]]"
                 , template
                 , "[[%" , ws , "endblock" , ws , "%]]" ;

include_stmt   = "[[%" , ws , "include" , ws , STRING , ws , "%]]" ;

macro_block    = "[[%" , ws , "macro" , ws , IDENT , "(" , [ param_list ] , ")" , ws , "%]]"
                 , template
                 , "[[%" , ws , "endmacro" , ws , "%]]" ;

(* Comments *)
comment        = "[[#" , { any_char - "#]]" } , "#]]" ;

(* Inheritance *)
extends_stmt   = "[[%" , ws , "extends" , ws , STRING , ws , "%]]" ;

(* Literals *)
literal        = STRING | NUMBER | "true" | "false" | "none" ;
STRING         = '"' , { any_char - '"' } , '"'
               | "'" , { any_char - "'" } , "'" ;
NUMBER         = DIGIT , { DIGIT } , [ "." , DIGIT , { DIGIT } ] ;
IDENT          = ( LETTER | "_" ) , { LETTER | DIGIT | "_" } ;

ws             = { " " | "\t" | "\n" | "\r" } ;
text           = { any_char - "<<" - "[[" } ;
```

### 5.3 Built-in Filters

| Filter       | Example                              | Description                    |
|-------------|--------------------------------------|--------------------------------|
| `title`     | `<< name \| title >>`                | Title-case string              |
| `upper`     | `<< name \| upper >>`                | Uppercase                      |
| `lower`     | `<< name \| lower >>`                | Lowercase                      |
| `truncate`  | `<< desc \| truncate(100) >>`        | Truncate with ellipsis         |
| `currency`  | `<< price \| currency("USD") >>`     | Format as currency             |
| `date`      | `<< created \| date("Y-m-d") >>`     | Format date                    |
| `tojson`    | `<< data \| tojson >>`               | Safe JSON encode               |
| `raw`       | `<< html \| raw >>`                  | Bypass auto-escaping           |
| `redact_pii`| `<< email \| redact_pii >>`          | Mask PII for logging           |
| `default`   | `<< name \| default("Guest") >>`     | Default if falsy               |
| `nl2br`     | `<< text \| nl2br >>`                | Newlines to `<br>`             |
| `urlencode` | `<< query \| urlencode >>`           | URL-encode                     |
| `pluralize` | `<< count \| pluralize("item") >>`   | English pluralization          |

### 5.4 Security Model

- **Auto-escaping**: All `<< >>` expressions are HTML-escaped by default.
- **`raw` filter**: Explicitly bypass escaping (audit trail logged).
- **Sandbox**: No access to `__dunder__` attributes, `import`, `exec`, `eval`.
- **Typed expressions**: Optional type annotations in template metadata validate
  that context keys match expected shapes at compile time.
- **Compile-time analysis**: Parser warns on missing keys, unreachable branches.

---

## 6. Algorithms

### 6.1 Retry / Backoff

```python
def next_attempt_delay(attempt: int, base: float = 1.0, cap: float = 3600.0) -> float:
    """Exponential backoff with jitter, capped at `cap` seconds."""
    delay = min(base * (2 ** attempt), cap)
    jitter = random.uniform(0, base)
    return delay + jitter
```

### 6.2 Rate Limiting (Token Bucket)

```python
class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens/sec
        self.last_refill = time.monotonic()

    def consume(self, n: int = 1) -> bool:
        self._refill()
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
```

### 6.3 Deduplication

```python
def compute_digest(subject: str, to: list[str], body_hash: str, attachment_digests: list[str]) -> str:
    """SHA-256 digest for deduplication within a configurable time window."""
    canonical = f"{subject}|{'|'.join(sorted(to))}|{body_hash}|{'|'.join(sorted(attachment_digests))}"
    return hashlib.sha256(canonical.encode()).hexdigest()
```

### 6.4 Bounce Classification

| Provider Code / Pattern | Classification | Action                      |
|------------------------|----------------|-----------------------------|
| 5.1.1 (user unknown)  | Permanent      | Suppress immediately         |
| 5.2.x (mailbox full)  | Transient      | Retry with backoff           |
| 5.7.x (policy reject) | Permanent      | Suppress + alert             |
| 4.x.x (temp failure)  | Transient      | Retry                        |
| Complaint (FBL)        | Complaint      | Suppress + record            |

---

## 7. Provider Plugin Interface

```python
from enum import Enum
from dataclasses import dataclass

class ProviderResultStatus(str, Enum):
    SUCCESS = "success"
    TRANSIENT_FAILURE = "transient_failure"
    PERMANENT_FAILURE = "permanent_failure"
    RATE_LIMITED = "rate_limited"

@dataclass
class ProviderResult:
    status: ProviderResultStatus
    provider_message_id: str | None = None
    error_message: str | None = None
    raw_response: dict | None = None

class IMailProvider(Protocol):
    name: str
    supports_batching: bool
    max_batch_size: int

    async def send(self, envelope: "MailEnvelope") -> ProviderResult: ...
    async def send_batch(self, envelopes: list["MailEnvelope"]) -> list[ProviderResult]: ...
    async def health_check(self) -> bool: ...
    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...
```

---

## 8. Aquilia Integration Points

### 8.1 Manifest / Workspace Wiring

```python
# workspace.py
workspace = (
    Workspace("myapp", version="0.1.0")
    .integrate(Integration.mail(
        default_from="noreply@myapp.com",
        template_dir="mail_templates",
        providers=[
            SMTPProvider(host="smtp.gmail.com", port=587, use_tls=True),
        ],
    ))
)
```

### 8.2 DI Registration

`MailService` is registered as `@service(scope="app")` singleton.  
Request-scoped `MailTransaction` available via DI for transactional mail.

### 8.3 Server.py Wiring

During `AquiliaServer.__init__`, the mail subsystem is initialized via
`self._setup_mail()` which reads mail config, creates the `MailService`,
registers DI providers, and hooks lifecycle (startup → connect providers,
shutdown → flush queue + disconnect).

### 8.4 Lifecycle Hooks

- **startup**: Initialize provider connections, run pending queue recovery.
- **shutdown**: Flush pending queue (best-effort), close connections.

### 8.5 Faults

New `FaultDomain.MAIL` with typed faults:
- `MailSendFault` — provider send failure
- `MailTemplateFault` — template render error
- `MailConfigFault` — configuration error
- `MailSuppressedFault` — recipient on suppression list
- `MailRateLimitFault` — rate limit exceeded

---

## 9. File Layout

```
aquilia/mail/
├── __init__.py              # Public API exports
├── message.py               # EmailMessage, EmailMultiAlternatives, TemplateMessage
├── service.py               # MailService (DI singleton, main orchestrator)
├── envelope.py              # MailEnvelope dataclass, builder, digest
├── store.py                 # EnvelopeStore (SQLite/Postgres), BlobStore
├── dispatcher.py            # Dispatcher, Scheduler, batching engine
├── retry.py                 # RetryEngine, backoff algorithm, idempotency
├── rate_limiter.py          # TokenBucket, per-domain + per-provider limits
├── providers/
│   ├── __init__.py          # IMailProvider protocol, ProviderResult
│   ├── smtp.py              # SMTPProvider (aiosmtplib)
│   ├── ses.py               # SESProvider (aiobotocore)
│   └── sendgrid.py          # SendGridProvider (httpx)
├── bounce.py                # BounceProcessor, classification, suppression
├── template/
│   ├── __init__.py          # ATS public API
│   ├── lexer.py             # ATS tokenizer
│   ├── parser.py            # ATS parser → AST
│   ├── compiler.py          # AST → bytecode, cache
│   ├── runtime.py           # Bytecode evaluator, sandbox
│   ├── filters.py           # Built-in filter library
│   └── security.py          # Sandbox, auto-escape, type validation
├── dkim.py                  # DKIM signing module
├── faults.py                # Mail fault domain + typed faults
├── metrics.py               # Prometheus metrics definitions
├── admin.py                 # Admin REST endpoints (controller)
├── cli.py                   # CLI commands (aq mail ...)
├── config.py                # MailConfig dataclass, defaults
└── di_providers.py          # DI registration helpers
```

---

## 10. API Surface

### 10.1 Library API

```python
# Simple send
from aquilia.mail import send_mail, asend_mail

send_mail(
    subject="Order Confirmation",
    body="Your order #123 is confirmed.",
    from_email="noreply@shop.com",
    to=["buyer@example.com"],
)

# Async
await asend_mail(subject="Hi", body="Hello", to=["user@example.com"])

# Rich message
from aquilia.mail import EmailMessage, EmailMultiAlternatives

msg = EmailMessage(
    subject="Invoice",
    body="See attached.",
    to=["finance@corp.com"],
    attachments=[("/tmp/invoice.pdf", "application/pdf")],
)
msg.send()

# Multi-alternative
msg = EmailMultiAlternatives(
    subject="Newsletter",
    body="Plain text fallback",
    to=["subscriber@example.com"],
)
msg.attach_alternative("<h1>HTML version</h1>", "text/html")
await msg.asend()

# Template-based
from aquilia.mail import TemplateMessage

msg = TemplateMessage(
    template="welcome.aqt",
    context={"user": {"name": "Asha", "id": 123}},
    to=["asha@example.com"],
)
await msg.asend()
```

### 10.2 CLI Commands

```bash
# Preview template rendering
aq mail preview --template welcome.aqt --context '{"user":{"name":"Test"}}'

# Queue management
aq mail queue-stats
aq mail requeue --id <uuid>
aq mail cancel --id <uuid>
aq mail flush                    # Flush pending queue immediately

# Suppression list
aq mail suppression add bad@example.com --reason hard_bounce
aq mail suppression list --since 2026-01-01
aq mail suppression remove user@example.com

# Provider health
aq mail providers
aq mail provider-health
```

### 10.3 Admin REST Endpoints

```
GET    /api/mail/queue              # List envelopes (filterable)
GET    /api/mail/queue/:id          # Envelope detail
POST   /api/mail/queue/:id/retry    # Retry failed envelope
POST   /api/mail/queue/:id/cancel   # Cancel queued envelope
GET    /api/mail/stats              # Aggregate statistics
GET    /api/mail/suppression        # Suppression list
POST   /api/mail/suppression        # Add to suppression
DELETE /api/mail/suppression/:email # Remove from suppression
GET    /api/mail/providers          # Provider status
POST   /api/mail/webhook/:provider  # Bounce/complaint webhook sink
GET    /api/mail/templates          # List registered templates
POST   /api/mail/templates/preview  # Preview render
```

---

## 11. Observability

### 11.1 Prometheus Metrics

| Metric                                  | Type      | Labels                        |
|-----------------------------------------|-----------|-------------------------------|
| `aquilia_mail_enqueued_total`           | Counter   | `tenant`, `priority`, `kind`  |
| `aquilia_mail_sent_total`              | Counter   | `provider`, `tenant`          |
| `aquilia_mail_send_latency_seconds`    | Histogram | `provider`                    |
| `aquilia_mail_failed_total`            | Counter   | `provider`, `error_type`      |
| `aquilia_mail_bounced_total`           | Counter   | `bounce_type`, `provider`     |
| `aquilia_mail_retries_total`           | Counter   | `provider`                    |
| `aquilia_mail_queue_depth`             | Gauge     | `status`                      |
| `aquilia_mail_suppression_list_size`   | Gauge     |                               |
| `aquilia_mail_render_latency_seconds`  | Histogram |                               |

### 11.2 Trace Spans

```
[mail.send]
  └── [mail.render_template]
  └── [mail.build_envelope]
  └── [mail.enqueue]
      └── [mail.dispatch]
          └── [mail.provider.send] {provider=smtp_primary}
```

---

## 12. Security

- **DKIM**: Per-domain RSA/Ed25519 key signing via `dkim.py`; keys loaded from env/KMS.
- **TLS**: SMTP STARTTLS enforced; HTTP providers use HTTPS only.
- **Anti-spoof**: Validate `From` matches configured allowed domains.
- **PII redaction**: `redact_pii` filter + log redaction middleware.
- **Encryption at rest**: Blob store supports wrapping with Fernet.

---

## 13. Rollout Plan (Incremental PRs)

| PR# | Scope                              | Dependencies | Tests                 |
|-----|------------------------------------|--------------|-----------------------|
| 1   | Core: faults, config, envelope, message, `__init__.py` | None | Unit tests |
| 2   | ATS template engine (lexer, parser, compiler, runtime, filters) | PR1 | Unit + render tests |
| 3   | Store (SQLite envelope + blob store) | PR1 | Unit + integration |
| 4   | Provider interface + SMTP provider | PR1 | Unit + smtp4dev integration |
| 5   | Dispatcher, retry engine, rate limiter | PR1,3,4 | Unit + integration |
| 6   | Bounce processor, suppression | PR3 | Unit |
| 7   | MailService orchestrator, DI providers | PR1-6 | Integration |
| 8   | Server.py wiring, lifecycle hooks, workspace Integration | PR7 | E2E |
| 9   | CLI commands (`aq mail ...`) | PR7 | CLI tests |
| 10  | Admin REST controller | PR7 | API tests |
| 11  | SES + SendGrid providers | PR4 | Unit |
| 12  | DKIM signing, security hardening | PR7 | Unit |
| 13  | Metrics, tracing | PR7 | Integration |
| 14  | Example app + documentation | All | E2E + docs |
| 15  | Benchmarks + load tests | All | Perf |

---

## 14. Failure Modes & Recovery

| Failure                    | Detection                  | Recovery                           |
|----------------------------|----------------------------|------------------------------------|
| Provider down              | health_check fails         | Failover to next priority provider |
| Queue DB corruption        | Startup integrity check    | WAL recovery, alert               |
| Rate limit exceeded        | Token bucket empty         | Back-pressure, delay dispatch      |
| Duplicate send on retry    | Idempotency key collision  | Skip, log                          |
| Template parse error       | Compile-time exception     | Fault raised, envelope not created |
| Attachment too large       | Size check at build time   | Reject with clear error            |
| Memory pressure            | Queue depth gauge          | Spill to disk, pause acceptance    |

---

*Architecture approved. Implementation begins with PR1: Core types.*
