import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Mail } from 'lucide-react'

export function MailTemplates() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Mail className="w-4 h-4" />
          Mail / Templates
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Mail Templates
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia supports template-based email rendering using the same Jinja2 engine as the template system. Create reusable email templates with variables, layouts, and components.
        </p>
      </div>

      {/* TemplateMessage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Using TemplateMessage</h2>
        <CodeBlock language="python" filename="usage.py">{`from aquilia.mail import TemplateMessage

# Simple template email
msg = TemplateMessage(
    template="emails/welcome.html",
    context={
        "user_name": "Asha",
        "activation_url": "https://myapp.com/activate/abc123",
    },
    subject="Welcome to MyApp!",
    to=["asha@example.com"],
    from_email="noreply@myapp.com",
)
await msg.asend()`}</CodeBlock>
      </section>

      {/* Template Structure */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Template Structure</h2>
        <CodeBlock language="html" filename="emails/base.html">{`<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; }
    .container { max-width: 600px; margin: 0 auto; background: white; padding: 32px; }
    .header { text-align: center; padding-bottom: 24px; border-bottom: 1px solid #eee; }
    .footer { text-align: center; color: #999; font-size: 12px; padding-top: 24px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      {% block header %}<h1>MyApp</h1>{% endblock %}
    </div>
    <div class="content">
      {% block content %}{% endblock %}
    </div>
    <div class="footer">
      {% block footer %}&copy; {{ year }} MyApp. All rights reserved.{% endblock %}
    </div>
  </div>
</body>
</html>`}</CodeBlock>

        <CodeBlock language="html" filename="emails/welcome.html">{`{% extends "emails/base.html" %}

{% block content %}
  <h2>Welcome, {{ user_name }}!</h2>
  <p>Thank you for joining us. Click the button below to activate your account.</p>
  <p style="text-align: center; padding: 20px;">
    <a href="{{ activation_url }}"
       style="background: #22c55e; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 6px;">
      Activate Account
    </a>
  </p>
{% endblock %}`}</CodeBlock>
      </section>

      {/* Config Serializers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Mail Config Serializers</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia validates mail configuration using serializer-based schemas. These are auto-applied when using <code className="text-aquilia-400">Integration.mail()</code>.
        </p>
        <CodeBlock language="python" filename="config.py">{`from aquilia.mail import (
    MailConfig,
    ProviderConfig,
    RetryConfig,
    RateLimitConfig,
    SecurityConfig,
    TemplateConfig,
    QueueConfig,
)

config = MailConfig(
    provider=ProviderConfig(backend="smtp", host="smtp.gmail.com", port=587),
    retry=RetryConfig(max_retries=3, backoff_factor=2.0),
    rate_limit=RateLimitConfig(max_per_minute=100),
    security=SecurityConfig(dkim_enabled=True, tls_required=True),
    template=TemplateConfig(directory="templates/emails/"),
    queue=QueueConfig(enabled=False),
)`}</CodeBlock>
      </section>
    </div>
  )
}
