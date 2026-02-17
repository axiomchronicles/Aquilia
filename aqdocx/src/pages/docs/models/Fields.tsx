import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Database } from 'lucide-react'

export function ModelsFields() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const fields = [
    { name: 'AutoField', sql: 'INTEGER PRIMARY KEY AUTOINCREMENT', desc: 'Auto-incrementing primary key.' },
    { name: 'BigAutoField', sql: 'BIGINT PRIMARY KEY AUTOINCREMENT', desc: 'Big auto-incrementing PK.' },
    { name: 'CharField', sql: 'VARCHAR(max_length)', desc: 'String with max length. Params: max_length (required).' },
    { name: 'TextField', sql: 'TEXT', desc: 'Unlimited text.' },
    { name: 'SlugField', sql: 'VARCHAR(50)', desc: 'URL-safe slug. Extends CharField with slug validation.' },
    { name: 'EmailField', sql: 'VARCHAR(254)', desc: 'Email with regex validation.' },
    { name: 'URLField', sql: 'VARCHAR(200)', desc: 'URL with validation.' },
    { name: 'IntegerField', sql: 'INTEGER', desc: 'Standard integer.' },
    { name: 'BigIntegerField', sql: 'BIGINT', desc: '64-bit integer.' },
    { name: 'SmallIntegerField', sql: 'SMALLINT', desc: '16-bit integer.' },
    { name: 'PositiveIntegerField', sql: 'INTEGER CHECK(≥0)', desc: 'Non-negative integer.' },
    { name: 'FloatField', sql: 'REAL', desc: 'Floating-point number.' },
    { name: 'DecimalField', sql: 'DECIMAL(digits,places)', desc: 'Fixed-precision decimal. Params: max_digits, decimal_places.' },
    { name: 'BooleanField', sql: 'BOOLEAN', desc: 'True/False.' },
    { name: 'DateField', sql: 'DATE', desc: 'Date. Supports auto_now, auto_now_add.' },
    { name: 'TimeField', sql: 'TIME', desc: 'Time of day.' },
    { name: 'DateTimeField', sql: 'TIMESTAMP', desc: 'Date + time. Supports auto_now, auto_now_add.' },
    { name: 'DurationField', sql: 'REAL (seconds)', desc: 'timedelta stored as seconds.' },
    { name: 'UUIDField', sql: 'VARCHAR(36)', desc: 'UUID value. Use default=uuid.uuid4.' },
    { name: 'JSONField', sql: 'TEXT (JSON)', desc: 'JSON-serialized dict or list.' },
    { name: 'BinaryField', sql: 'BLOB', desc: 'Raw binary data.' },
    { name: 'FilePathField', sql: 'VARCHAR', desc: 'File system path with optional validation.' },
    { name: 'IPAddressField', sql: 'VARCHAR(45)', desc: 'IPv4 or IPv6 address.' },
    { name: 'EnumField', sql: 'VARCHAR', desc: 'Python Enum with DB string storage.' },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Database className="w-4 h-4" />Data Layer</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fields</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Every Aquilia field is production-ready with full validation, SQL generation, and serialization. Fields use a clean, expressive Python API — no prefixes, no AMDL.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Common Field Parameters</h2>
        <CodeBlock language="python" filename="Base Field Parameters">{`class Field:
    def __init__(
        self,
        *,
        null: bool = False,          # Allow NULL in DB
        blank: bool = False,         # Allow empty string in validation
        default: Any = UNSET,        # Default value or callable
        unique: bool = False,        # UNIQUE constraint
        primary_key: bool = False,   # PRIMARY KEY
        db_index: bool = False,      # Create index
        db_column: str | None,       # Override column name
        choices: list | None,        # Enumerated values
        validators: list | None,     # Custom validation callables
        help_text: str = "",         # Documentation
        editable: bool = True,       # Whether field is editable
        verbose_name: str = "",      # Human label
    ): ...`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Field Reference</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead><tr className={`border-b ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
              <th className="text-left py-3 pr-4 text-aquilia-500 whitespace-nowrap">Field</th>
              <th className="text-left py-3 pr-4 text-aquilia-500 whitespace-nowrap">SQL Type</th>
              <th className="text-left py-3 text-aquilia-500">Notes</th>
            </tr></thead>
            <tbody className="divide-y divide-white/5">
              {fields.map((f, i) => (
                <tr key={i}>
                  <td className="py-2 pr-4 font-mono text-xs text-aquilia-400 whitespace-nowrap">{f.name}</td>
                  <td className={`py-2 pr-4 text-xs font-mono whitespace-nowrap ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{f.sql}</td>
                  <td className={`py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{f.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Usage Examples</h2>
        <CodeBlock language="python" filename="Field Examples">{`from aquilia.models import Model
from aquilia.models.fields_module import *
import uuid

class Product(Model):
    table = "products"

    # Auto PK (added automatically if not declared)
    id = BigAutoField(primary_key=True)

    # Strings
    name = CharField(max_length=200, db_index=True)
    slug = SlugField(unique=True)
    description = TextField(blank=True)

    # Numbers
    price = DecimalField(max_digits=10, decimal_places=2)
    stock = PositiveIntegerField(default=0)

    # Dates
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    launch_date = DateField(null=True)

    # Special
    sku = UUIDField(default=uuid.uuid4)
    metadata = JSONField(default=dict)
    active = BooleanField(default=True)

    # Choices
    status = CharField(max_length=20, choices=[
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ], default="draft")`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Validation</h2>
        <CodeBlock language="python" filename="Validators">{`def validate_positive(value):
    if value <= 0:
        raise FieldValidationError("price", "Must be positive", value)

class Product(Model):
    table = "products"
    price = DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[validate_positive],
    )

# full_clean() is called automatically before save
product = Product(price=-5)
product.full_clean()  # raises FieldValidationError`}</CodeBlock>
      </section>
    </div>
  )
}
