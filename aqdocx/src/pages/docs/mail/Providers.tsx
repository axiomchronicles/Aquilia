import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Mail } from 'lucide-react'

export function MailProviders() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Mail className="w-4 h-4" />
          Mail / Providers
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Mail Providers
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia ships with five mail provider implementations. All implement the <code className="text-aquilia-400">IMailProvider</code> protocol, making them interchangeable.
        </p>
      </div>

      {/* Provider Comparison */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Provider Comparison</h2>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Provider</th>
                  <th className="text-left pb-3 font-semibold">Use Case</th>
                  <th className="text-left pb-3 font-semibold">Dependencies</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['SMTPProvider', 'Production SMTP relay (Gmail, Mailgun, etc.)', 'aiosmtplib'],
                  ['SendGridProvider', 'SendGrid API (cloud email service)', 'httpx'],
                  ['SESProvider', 'Amazon SES (AWS email)', 'boto3'],
                  ['ConsoleProvider', 'Development — prints emails to console', 'None'],
                  ['FileProvider', 'Development — writes emails to files', 'None'],
                ].map(([name, use, deps], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{name}</td>
                    <td className="py-2 text-xs">{use}</td>
                    <td className="py-2 text-xs font-mono">{deps}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* SMTPProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SMTPProvider</h2>
        <CodeBlock language="python" filename="smtp.py">{`from aquilia.mail import SMTPProvider

provider = SMTPProvider(
    host="smtp.gmail.com",
    port=587,
    username="noreply@myapp.com",
    password="app-password",
    use_tls=True,
    timeout=30,
)`}</CodeBlock>
      </section>

      {/* SendGridProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SendGridProvider</h2>
        <CodeBlock language="python" filename="sendgrid.py">{`from aquilia.mail import SendGridProvider

provider = SendGridProvider(
    api_key="SG.xxxxxxxxxxxx",
    sandbox_mode=False,
)`}</CodeBlock>
      </section>

      {/* SESProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SESProvider</h2>
        <CodeBlock language="python" filename="ses.py">{`from aquilia.mail import SESProvider

provider = SESProvider(
    region_name="us-east-1",
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    configuration_set="my-config-set",
)`}</CodeBlock>
      </section>

      {/* ConsoleProvider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ConsoleProvider (Development)</h2>
        <CodeBlock language="python" filename="console.py">{`from aquilia.mail import ConsoleProvider

# Prints email content to stdout — no actual sending
provider = ConsoleProvider()

# Output:
# ════════════════════════════════════════════
# Subject: Welcome!
# From: noreply@myapp.com
# To: user@example.com
# ────────────────────────────────────────────
# Thank you for signing up.
# ════════════════════════════════════════════`}</CodeBlock>
      </section>

      {/* Custom Provider */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Provider</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Implement <code className="text-aquilia-400">IMailProvider</code> to integrate with any email service.
        </p>
        <CodeBlock language="python" filename="custom.py">{`from aquilia.mail import IMailProvider, ProviderResult, ProviderResultStatus

class PostmarkProvider(IMailProvider):
    def __init__(self, server_token: str):
        self.token = server_token

    async def send(self, envelope) -> ProviderResult:
        # Send via Postmark API
        response = await httpx.post(
            "https://api.postmarkapp.com/email",
            headers={"X-Postmark-Server-Token": self.token},
            json={...},
        )
        if response.status_code == 200:
            return ProviderResult(
                status=ProviderResultStatus.SUCCESS,
                message_id=response.json()["MessageID"],
            )
        return ProviderResult(
            status=ProviderResultStatus.FAILED,
            error=response.text,
        )`}</CodeBlock>
      </section>

      {/* DI Registration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>DI Registration</h2>
        <CodeBlock language="python" filename="di.py">{`from aquilia.mail import register_mail_providers, MailProviderRegistry

# Auto-register all providers based on config
register_mail_providers(container, config)

# Or manually register
registry = MailProviderRegistry()
registry.register("smtp", SMTPProvider(...))
registry.register("sendgrid", SendGridProvider(...))

# Resolve active provider
provider = registry.get(config.mail.provider)  # "smtp" → SMTPProvider`}</CodeBlock>
      </section>
    </div>
  )
}
