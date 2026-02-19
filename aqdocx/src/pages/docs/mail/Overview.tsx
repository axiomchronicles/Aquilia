import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Mail } from 'lucide-react'

export function MailOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Mail className="w-4 h-4" />
          Advanced / Mail
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Mail System
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          AquilaMail provides production-grade email sending with pluggable providers (SMTP, SendGrid, Mailgun, SES, Console), template-based composition, DI integration, queued delivery, and a testing outbox for assertions.
        </p>
      </div>

      {/* Configuration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration</h2>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia import Workspace, Integration

workspace = Workspace(
    integrations=[
        Integration.mail(
            provider="smtp",              # "smtp" | "sendgrid" | "mailgun" | "ses" | "console"
            host="smtp.example.com",
            port=587,
            username="apikey",
            password="secret",
            use_tls=True,
            from_email="noreply@example.com",
            from_name="My App",
            reply_to="support@example.com",
            template_dir="templates/email",
            queue_backend="memory",       # Queue for async delivery
        ),
    ],
)`}</CodeBlock>
      </section>

      {/* Sending Mail */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Sending Emails</h2>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Post, Inject
from aquilia.mail import MailService


class AuthController(Controller):
    prefix = "/auth"

    @Inject()
    def __init__(self, mail: MailService):
        self.mail = mail

    @Post("/register")
    async def register(self, ctx):
        body = await ctx.json()
        user = await User.objects.create(**body)

        # Send welcome email
        await self.mail.send(
            to=user.email,
            subject="Welcome to My App!",
            template="welcome.html",
            context={
                "username": user.username,
                "activation_url": f"https://myapp.com/activate/{user.token}",
            },
        )

        return ctx.json({"user": user.to_dict()}, status=201)

    @Post("/forgot-password")
    async def forgot_password(self, ctx):
        body = await ctx.json()
        user = await User.objects.get(email=body["email"])
        token = await generate_reset_token(user)

        # Send with plain text body (no template)
        await self.mail.send(
            to=user.email,
            subject="Password Reset",
            body=f"Reset your password: https://myapp.com/reset/{token}",
        )

        return ctx.json({"sent": True})`}</CodeBlock>
      </section>

      {/* Providers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Mail Providers</h2>
        <div className="space-y-3">
          {[
            { name: 'SMTPProvider', desc: 'Standard SMTP delivery. Supports TLS/SSL, authentication, and connection pooling.' },
            { name: 'SendGridProvider', desc: 'SendGrid API v3 integration. Supports templates, categories, and tracking.' },
            { name: 'MailgunProvider', desc: 'Mailgun API integration with domain-based sending and webhook support.' },
            { name: 'SESProvider', desc: 'Amazon SES integration with IAM authentication and bounce handling.' },
            { name: 'ConsoleProvider', desc: 'Development provider that prints emails to stdout. No network calls.' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <code className="text-aquilia-500 font-mono text-sm font-bold">{item.name}</code>
              <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Template Emails */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Template-Based Emails</h2>
        <CodeBlock language="html" filename="templates/email/welcome.html">{`{% extends "email/base.html" %}

{% block content %}
<h1>Welcome, {{ username }}!</h1>
<p>Thank you for joining our platform.</p>
<a href="{{ activation_url }}" class="button">
    Activate Your Account
</a>
{% endblock %}`}</CodeBlock>
      </section>

      {/* Testing */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Testing Emails</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Use the <code className="text-aquilia-500">MailTestMixin</code> to capture and assert on sent emails without network calls:
        </p>
        <CodeBlock language="python" filename="test_mail.py">{`from aquilia.testing import AquiliaTestCase, MailTestMixin


class TestRegistration(AquiliaTestCase, MailTestMixin):
    async def test_welcome_email_sent(self):
        response = await self.client.post("/auth/register", json={
            "email": "user@example.com",
            "username": "testuser",
            "password": "secure123",
        })
        self.assert_status(response, 201)

        # Assert email was sent
        self.assert_mail_sent(count=1)
        mail = self.get_sent_mail()[0]
        assert mail.to == "user@example.com"
        assert "Welcome" in mail.subject
        assert "testuser" in mail.html_body`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/templates" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Templates
        </Link>
        <Link to="/docs/mlops" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          MLOps <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
