import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Binary } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function SerializerFields() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  const fieldGroups = [
    {
      title: 'Primitive Fields',
      fields: [
        { name: 'BooleanField', args: 'required, default', desc: 'Validates boolean values. Coerces truthy/falsy strings.' },
        { name: 'NullBooleanField', args: 'required, default', desc: 'Accepts True, False, or None.' },
        { name: 'CharField', args: 'max_length, min_length, trim, pattern', desc: 'String field with optional regex pattern matching.' },
        { name: 'EmailField', args: 'max_length', desc: 'Validates RFC 5322 email addresses.' },
        { name: 'SlugField', args: 'max_length', desc: 'URL-safe slug strings (letters, numbers, hyphens, underscores).' },
        { name: 'URLField', args: 'max_length, schemes', desc: 'Validates fully-qualified URLs with scheme enforcement.' },
        { name: 'UUIDField', args: 'format', desc: 'UUID v4 strings. Accepts hex or hyphenated format.' },
        { name: 'IPAddressField', args: 'protocol', desc: 'Validates IPv4 and IPv6 addresses.' },
      ],
    },
    {
      title: 'Numeric Fields',
      fields: [
        { name: 'IntegerField', args: 'min_value, max_value', desc: 'Integer validation with optional range constraints.' },
        { name: 'FloatField', args: 'min_value, max_value', desc: 'Floating-point numbers with range validation.' },
        { name: 'DecimalField', args: 'max_digits, decimal_places', desc: 'Precise decimal values for financial calculations.' },
      ],
    },
    {
      title: 'Date/Time Fields',
      fields: [
        { name: 'DateField', args: 'format, auto_now, auto_now_add', desc: 'ISO 8601 date strings (YYYY-MM-DD).' },
        { name: 'TimeField', args: 'format', desc: 'Time strings (HH:MM:SS or HH:MM).' },
        { name: 'DateTimeField', args: 'format, auto_now, auto_now_add', desc: 'ISO 8601 datetime with timezone support.' },
        { name: 'DurationField', args: 'min_value, max_value', desc: 'Time durations as ISO 8601 duration or seconds.' },
      ],
    },
    {
      title: 'Structured Fields',
      fields: [
        { name: 'ListField', args: 'child, min_length, max_length', desc: 'Validates arrays with a typed child field.' },
        { name: 'DictField', args: 'child, key_field', desc: 'Validates dictionaries with optional key/value typing.' },
        { name: 'JSONField', args: 'schema', desc: 'Arbitrary JSON data. Optionally validated against a JSON Schema.' },
      ],
    },
    {
      title: 'Special Fields',
      fields: [
        { name: 'ReadOnlyField', args: '-', desc: 'Included in serialized output only; ignored on deserialization.' },
        { name: 'HiddenField', args: 'default', desc: 'Never shown in output; provides a hidden default during validation.' },
        { name: 'SerializerMethodField', args: 'method_name', desc: 'Calls a method on the serializer to compute the value dynamically.' },
        { name: 'ChoiceField', args: 'choices', desc: 'Restricts input to a predefined set of allowed values.' },
        { name: 'MultipleChoiceField', args: 'choices', desc: 'Accepts a list of values, each validated against allowed choices.' },
        { name: 'FileField', args: 'max_size, allowed_types', desc: 'Validates uploaded files by size and MIME type.' },
        { name: 'ImageField', args: 'max_size, max_width, max_height', desc: 'Extends FileField with image dimension validation.' },
        { name: 'ConstantField', args: 'value', desc: 'Always outputs the same constant value regardless of input.' },
      ],
    },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Binary className="w-4 h-4" />
          Serializers / Fields
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Serializer Fields
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia ships with 25+ built-in field types for validating and coercing every common data shape. Each field supports <code className="text-aquilia-400">required</code>, <code className="text-aquilia-400">default</code>, <code className="text-aquilia-400">allow_null</code>, <code className="text-aquilia-400">help_text</code>, and <code className="text-aquilia-400">source</code> as universal options.
        </p>
      </div>

      {/* Universal Options */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Universal Field Options</h2>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Option</th>
                  <th className="text-left pb-3 font-semibold">Type</th>
                  <th className="text-left pb-3 font-semibold">Default</th>
                  <th className="text-left pb-3 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['required', 'bool', 'True', 'Field must be present in input data'],
                  ['default', 'Any', '-', 'Value used when field is missing from input'],
                  ['allow_null', 'bool', 'False', 'Accept None as a valid value'],
                  ['allow_blank', 'bool', 'False', 'Accept empty strings (CharField only)'],
                  ['source', 'str', 'field_name', 'Attribute name to read from the instance'],
                  ['read_only', 'bool', 'False', 'Include in output only, skip during validation'],
                  ['write_only', 'bool', 'False', 'Accept during validation only, exclude from output'],
                  ['help_text', 'str', '""', 'Description for OpenAPI schema generation'],
                  ['label', 'str', '""', 'Human-readable label for documentation'],
                  ['validators', 'list', '[]', 'Additional validators applied after field validation'],
                  ['error_messages', 'dict', '{}', 'Custom error message overrides'],
                ].map(([opt, type, def_, desc], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{opt}</td>
                    <td className="py-2 text-xs">{type}</td>
                    <td className="py-2 text-xs font-mono">{def_}</td>
                    <td className="py-2 text-xs">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Field Groups */}
      {fieldGroups.map((group) => (
        <section key={group.title} className="mb-16">
          <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>{group.title}</h2>
          <div className="space-y-3">
            {group.fields.map((f) => (
              <div key={f.name} className={box}>
                <div className="flex items-start justify-between mb-2">
                  <h3 className={`font-mono font-bold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{f.name}</h3>
                  <span className={`text-xs font-mono px-2 py-0.5 rounded ${isDark ? 'bg-white/5 text-gray-500' : 'bg-gray-100 text-gray-400'}`}>{f.args}</span>
                </div>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{f.desc}</p>
              </div>
            ))}
          </div>
        </section>
      ))}

      {/* Usage Examples */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Usage Examples</h2>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>CharField with Pattern</h3>
        <CodeBlock language="python" filename="fields.py">{`from aquilia.serializers import Serializer, CharField

class SKUSerializer(Serializer):
    sku = CharField(
        max_length=50,
        pattern=r"^[A-Z]{2}-\\d{4,8}$",
        help_text="Product SKU in format XX-0000",
    )
    name = CharField(max_length=200, min_length=2, trim=True)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mb-3 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>Nested ListField & DictField</h3>
        <CodeBlock language="python" filename="nested.py">{`from aquilia.serializers import (
    Serializer, CharField, IntegerField,
    ListField, DictField, JSONField,
)

class EventSerializer(Serializer):
    title = CharField(max_length=200)
    tags = ListField(
        child=CharField(max_length=30),
        min_length=1,
        max_length=10,
    )
    metadata = DictField(required=False)
    payload = JSONField(required=False)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mb-3 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>SerializerMethodField</h3>
        <CodeBlock language="python" filename="computed.py">{`from aquilia.serializers import Serializer, CharField, SerializerMethodField

class UserSerializer(Serializer):
    first_name = CharField()
    last_name = CharField()
    full_name = SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"`}</CodeBlock>

        <h3 className={`text-lg font-semibold mb-3 mt-8 ${isDark ? 'text-white' : 'text-gray-900'}`}>DI-Aware Defaults</h3>
        <CodeBlock language="python" filename="di_defaults.py">{`from aquilia.serializers import (
    Serializer, CharField, DateTimeField,
    CurrentUserDefault, CurrentRequestDefault, InjectDefault,
)

class AuditSerializer(Serializer):
    """Fields auto-populated from DI context."""
    created_by = CharField(default=CurrentUserDefault())
    ip_address = CharField(default=CurrentRequestDefault("client_ip"))
    trace_id = CharField(default=InjectDefault("trace.id"))`}</CodeBlock>
      </section>

      {/* File & Image Fields */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>File & Image Fields</h2>
        <CodeBlock language="python" filename="uploads.py">{`from aquilia.serializers import Serializer, FileField, ImageField

class UploadSerializer(Serializer):
    document = FileField(
        max_size=10 * 1024 * 1024,  # 10 MB
        allowed_types=["application/pdf", "text/plain"],
    )
    avatar = ImageField(
        max_size=5 * 1024 * 1024,
        max_width=2048,
        max_height=2048,
    )`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}