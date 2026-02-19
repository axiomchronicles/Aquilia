import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Mail } from 'lucide-react'

export function MailService() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Mail className="w-4 h-4" />
          Mail / Service
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Mail Service
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The mail service provides <code className="text-aquilia-400">send_mail()</code> and <code className="text-aquilia-400">asend_mail()</code> convenience functions, plus <code className="text-aquilia-400">EmailMessage</code> and <code className="text-aquilia-400">TemplateMessage</code> classes for composing rich emails.
        </p>
      </div>

      {/* Quick API */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Quick API</h2>
        <CodeBlock language="python" filename="quick.py">{`from aquilia.mail import send_mail, asend_mail

# Synchronous
send_mail(
    subject="Welcome!",
    body="Thank you for signing up.",
    from_email="noreply@myapp.com",
    to=["user@example.com"],
)

# Async
await asend_mail(
    subject="Password Reset",
    body="Click the link to reset your password.",
    from_email="noreply@myapp.com",
    to=["user@example.com"],
)`}</CodeBlock>
      </section>

      {/* EmailMessage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>EmailMessage</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Full-featured message class for composing emails with attachments, CC/BCC, and headers.
        </p>
        <CodeBlock language="python" filename="message.py">{`from aquilia.mail import EmailMessage, EmailMultiAlternatives

# Simple text email
msg = EmailMessage(
    subject="Invoice #1234",
    body="Please find your invoice attached.",
    from_email="billing@myapp.com",
    to=["customer@example.com"],
    cc=["accounts@myapp.com"],
    bcc=["archive@myapp.com"],
    reply_to=["support@myapp.com"],
    headers={"X-Priority": "1"},
)
msg.attach_file("invoice.pdf")
await msg.asend()

# HTML + text fallback
msg = EmailMultiAlternatives(
    subject="Welcome!",
    body="Welcome to our platform.",  # text fallback
    to=["user@example.com"],
)
msg.attach_alternative("<h1>Welcome!</h1><p>...</p>", "text/html")
await msg.asend()`}</CodeBlock>
      </section>

      {/* TemplateMessage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>TemplateMessage</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Render email content from Aquilia templates (.aqt files or standard Jinja2).
        </p>
        <CodeBlock language="python" filename="template.py">{`from aquilia.mail import TemplateMessage

msg = TemplateMessage(
    template="emails/welcome.aqt",
    context={
        "user": {"name": "Asha", "email": "asha@example.com"},
        "activation_url": "https://myapp.com/activate/abc123",
    },
    subject="Welcome to MyApp!",
    to=["asha@example.com"],
)
await msg.asend()`}</CodeBlock>
      </section>

      {/* Envelope & Priority */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Envelope & Priority</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-400">MailEnvelope</code> wraps message metadata for tracking delivery status, retries, and idempotency.
        </p>
        <CodeBlock language="python" filename="envelope.py">{`from aquilia.mail import MailEnvelope, EnvelopeStatus, Priority

envelope = MailEnvelope(
    message=msg,
    priority=Priority.HIGH,
    idempotency_key="welcome-user-42",
    retry_count=0,
    max_retries=3,
)

# Track status
print(envelope.status)  # EnvelopeStatus.PENDING → SENT → DELIVERED
                         # or FAILED / BOUNCED / SUPPRESSED`}</CodeBlock>
      </section>

      {/* Configuration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration</h2>
        <CodeBlock language="python" filename="config.py">{`from aquilia.config_builders import WorkspaceBuilder, Integration

workspace = WorkspaceBuilder("myapp")
workspace.integrations([
    Integration.mail(
        provider="smtp",
        host="smtp.gmail.com",
        port=587,
        username="noreply@myapp.com",
        password="app-password",
        use_tls=True,
        default_from="noreply@myapp.com",
        rate_limit=100,  # emails per minute
        retry_max=3,
        retry_backoff=2.0,
    ),
])`}</CodeBlock>
      </section>

      {/* Faults */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Mail Faults</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { name: 'MailFault', desc: 'Base mail fault' },
            { name: 'MailSendFault', desc: 'Delivery failure' },
            { name: 'MailTemplateFault', desc: 'Template rendering error' },
            { name: 'MailConfigFault', desc: 'Invalid mail configuration' },
            { name: 'MailSuppressedFault', desc: 'Recipient on suppression list' },
            { name: 'MailRateLimitFault', desc: 'Rate limit exceeded' },
            { name: 'MailValidationFault', desc: 'Invalid email address or content' },
          ].map((f, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-xs mb-1 ${isDark ? 'text-red-400' : 'text-red-600'}`}>{f.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
