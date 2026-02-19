import { useTheme } from '../../../context/ThemeContext';
import { CodeBlock } from '../../../components/CodeBlock';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export function ModelsFields() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm mb-4">
          <Link to="/docs" className={isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}>Docs</Link>
          <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>/</span>
          <Link to="/docs/models/overview" className={isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}>Models</Link>
          <span className={isDark ? 'text-gray-500' : 'text-gray-400'}>/</span>
          <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>Fields</span>
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Fields
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Every field type available in Aquilia — from basic text and numbers to PostgreSQL arrays, composite fields, and encrypted storage.
        </p>
      </div>

      {/* Base Field */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Base Field</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          All fields inherit from <code>Field</code>, which is a Python descriptor. Each field defines validation, SQL type generation,
          serialization (<code>to_python</code> / <code>to_db</code>), and migration support (<code>deconstruct</code>).
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parameter</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>null</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>bool</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>False</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Allow NULL in database</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>blank</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>bool</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>False</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Allow empty strings in validation</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>default</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Any</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>UNSET</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default value or callable (e.g. <code>uuid.uuid4</code>)</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>unique</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>bool</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>False</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Add UNIQUE constraint</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>primary_key</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>bool</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>False</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Mark as primary key</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>db_index</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>bool</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>False</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Create a database index on this field</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>db_column</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>str | None</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>None</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Override the database column name</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>choices</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>list | None</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>None</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Enumerated (value, display) pairs</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>validators</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>list | None</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>[]</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>List of validation callables</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>help_text</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>str</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>""</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Documentation string</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>editable</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>bool</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>True</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Whether the field is editable</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Numeric fields */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Numeric Fields</h2>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Field</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Python Type</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>SQL (SQLite / PG)</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Range / Notes</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>AutoField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>int</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>INTEGER</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>32-bit auto PK</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>BigAutoField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>int</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>INTEGER / BIGSERIAL</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>64-bit auto PK (default)</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>IntegerField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>int</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>INTEGER</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>-2B to +2B</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>BigIntegerField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>int</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>INTEGER / BIGINT</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>64-bit signed</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>SmallIntegerField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>int</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>INTEGER / SMALLINT</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>-32768 to 32767</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>PositiveIntegerField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>int</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>INTEGER</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>0 to 2B. Also: PositiveSmallIntegerField, PositiveBigIntegerField</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>FloatField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>float</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>REAL / DOUBLE PRECISION</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>IEEE 754 double</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>DecimalField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Decimal</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>DECIMAL(m,d)</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>max_digits, decimal_places. Stored as string in DB.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`price = DecimalField(max_digits=10, decimal_places=2)
score = FloatField(null=True)
views = PositiveIntegerField(default=0)`}
        </CodeBlock>
      </section>

      {/* Text fields */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Text / String Fields</h2>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Field</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>SQL Type</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Notes</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>CharField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>VARCHAR(n)</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Requires <code>max_length</code> (default 255). Rejects blank unless <code>blank=True</code>.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>TextField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>TEXT</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Unlimited length text.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>SlugField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>VARCHAR(50)</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>URL-safe. Only <code>[a-zA-Z0-9_-]</code>.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>EmailField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>VARCHAR(254)</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>RFC-compliant email validation. Auto-lowercased.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>URLField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>VARCHAR(200)</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Validates http/https URLs.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>UUIDField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>VARCHAR(36) / UUID</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Pass <code>auto=True</code> for auto-generated UUID4.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>FilePathField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>VARCHAR(100)</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>File system path with optional match/recursive params.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`name = CharField(max_length=150)
bio = TextField(blank=True)
slug = SlugField(unique=True)
email = EmailField(unique=True)   # auto-lowercased
website = URLField(null=True)
uuid = UUIDField(auto=True)       # auto-generates UUID4`}
        </CodeBlock>
      </section>

      {/* Date/time fields */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Date / Time Fields</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          All date/time fields support <code>auto_now</code> (update on every save) and <code>auto_now_add</code> (set on creation only) via <code>pre_save()</code> hooks.
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Field</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Python Type</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>SQL (SQLite / PG)</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Storage</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>DateField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>date</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>DATE</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>ISO format string</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>TimeField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>time</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>TIME</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>ISO format string</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>DateTimeField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>datetime</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>TIMESTAMP / TIMESTAMPTZ</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>ISO format string. UTC.</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>DurationField</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>timedelta</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>INTEGER / INTERVAL</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Microseconds (SQLite)</td>
              </tr>
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`created_at = DateTimeField(auto_now_add=True)  # set on creation
updated_at = DateTimeField(auto_now=True)      # updated on every save
birthday = DateField(null=True)
login_time = TimeField(auto_now=True)
session_length = DurationField(null=True)`}
        </CodeBlock>
      </section>

      {/* Boolean / Binary / JSON */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Boolean, Binary & JSON Fields</h2>
        <CodeBlock language="python">
{`# Boolean — stored as INTEGER 0/1 (SQLite) or BOOLEAN (PG)
active = BooleanField(default=True)

# Binary — stored as BLOB
avatar = BinaryField(max_length=1_000_000, null=True)

# JSON — JSONB on PostgreSQL, TEXT elsewhere
# Full JSON serialization/deserialization
metadata = JSONField(default=dict)
settings = JSONField(null=True, encoder=CustomEncoder)`}
        </CodeBlock>
      </section>

      {/* IP / File / Image fields */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>IP, File & Image Fields</h2>
        <CodeBlock language="python">
{`# IP address — validates IPv4/IPv6
ip = GenericIPAddressField(protocol="both")       # VARCHAR(39) / INET
ip4 = GenericIPAddressField(protocol="ipv4")
inet = InetAddressField()  # PostgreSQL INET with netmask

# File — stores upload path
document = FileField(upload_to="docs/", max_length=200)

# Image — extends FileField with dimension tracking
photo = ImageField(
    upload_to="photos/",
    width_field="photo_width",
    height_field="photo_height",
)`}
        </CodeBlock>
      </section>

      {/* PostgreSQL-specific fields */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>PostgreSQL-Specific Fields</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          These fields use native PostgreSQL types when available and fall back to TEXT/JSON on SQLite.
        </p>
        <CodeBlock language="python">
{`# Array — PostgreSQL arrays, JSON fallback on SQLite
tags = ArrayField(CharField(max_length=50), size=10)

# HStore — key-value pairs (all string values)
metadata = HStoreField(null=True)

# Range fields — PostgreSQL range types
age_range = IntegerRangeField()          # INT4RANGE
salary_range = DecimalRangeField()       # NUMRANGE
event_dates = DateRangeField()           # DATERANGE
schedule = DateTimeRangeField()          # TSTZRANGE
big_range = BigIntegerRangeField()       # INT8RANGE

# Case-insensitive text (PostgreSQL CITEXT extension)
username = CICharField(max_length=150)   # CITEXT
ci_email = CIEmailField()               # CITEXT
search_text = CITextField()             # CITEXT`}
        </CodeBlock>
      </section>

      {/* Special / Meta fields */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Special / Meta Fields</h2>
        <CodeBlock language="python">
{`# Generated field — computed by the database
full_name = GeneratedField(
    expression="first_name || ' ' || last_name",
    output_field=CharField(max_length=300),
    db_persist=True,  # STORED (not VIRTUAL)
)

# OrderWrt — internal ordering helper
sort_order = OrderWrt()  # IntegerField(default=0, db_index=True)

# Enum field (from fields submodule)
from aquilia.models.fields import EnumField

class Status(TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"

status = EnumField(enum_class=Status, default=Status.DRAFT)`}
        </CodeBlock>
      </section>

      {/* Field Mixins */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Field Mixins</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Reusable behaviors that can be composed with any field via multiple inheritance:
        </p>
        <div className={`rounded-lg border ${isDark ? 'border-gray-700' : 'border-gray-200'} overflow-hidden mb-4`}>
          <table className="w-full">
            <thead>
              <tr className={isDark ? 'bg-gray-800' : 'bg-gray-50'}>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Mixin</th>
                <th className={`px-4 py-3 text-left text-sm font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Effect</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700' : 'divide-gray-200'}`}>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>NullableMixin</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Sets <code>null=True, blank=True</code> by default</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>UniqueMixin</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Sets <code>unique=True</code> by default</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>IndexedMixin</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Sets <code>db_index=True</code> by default</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>AutoNowMixin</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Sets <code>auto_now=True</code> for date/time fields</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>ChoiceMixin</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Adds <code>get_display(value)</code> and <code>choice_values</code> helpers</td>
              </tr>
              <tr>
                <td className={`px-4 py-3 text-sm font-mono ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>EncryptedMixin</td>
                <td className={`px-4 py-3 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Encrypts on write, decrypts on read. Configure a real backend for production.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <CodeBlock language="python">
{`from aquilia.models.fields import NullableMixin, EncryptedMixin

# Create a custom encrypted text field
class SecretField(EncryptedMixin, TextField):
    pass

# Configure encryption for production
EncryptedMixin.configure_encryption(
    encrypt=my_encrypt_fn,
    decrypt=my_decrypt_fn,
)

api_key = SecretField()`}
        </CodeBlock>
      </section>

      {/* Composite fields */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Composite Fields</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Group multiple primitives into one logical attribute. Two storage strategies: <code>json</code> (single TEXT/JSONB column) or <code>expand</code> (multiple columns with a prefix).
        </p>
        <CodeBlock language="python">
{`from aquilia.models.fields import CompositeField, CompositeAttribute, CompositePrimaryKey

# JSON strategy — stored as one JSONB/TEXT column
coordinates = CompositeField(
    schema={"lat": FloatField(), "lng": FloatField()},
    strategy="json",
)

# Expanded strategy — creates addr_street, addr_city, addr_zip columns
address = CompositeField(
    schema={
        "street": CharField(max_length=200),
        "city": CharField(max_length=100),
        "zip": CharField(max_length=20),
    },
    prefix="addr",
    strategy="expand",
)

# CompositeAttribute — read/write descriptor for grouped columns
class Order(Model):
    _ship_street = CharField(max_length=200)
    _ship_city = CharField(max_length=100)
    shipping = CompositeAttribute(
        fields=["_ship_street", "_ship_city"],
        keys=["street", "city"],
    )

order.shipping  # → {"street": "123 Main", "city": "NYC"}
order.shipping = {"street": "456 Oak", "city": "LA"}

# Composite primary key
class OrderItem(Model):
    order_id = IntegerField()
    product_id = IntegerField()

    class Meta:
        primary_key = CompositePrimaryKey(fields=["order_id", "product_id"])`}
        </CodeBlock>
      </section>

      {/* Indexes / Constraints */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Indexes & Constraints</h2>
        <CodeBlock language="python">
{`from aquilia.models.fields_module import Index, UniqueConstraint
from aquilia.models.constraint import CheckConstraint, ExclusionConstraint, Deferrable
from aquilia.models.index import GinIndex, GistIndex, BrinIndex, HashIndex

class Product(Model):
    table = "products"
    name = CharField(max_length=200)
    sku = CharField(max_length=50, unique=True, db_index=True)
    price = DecimalField(max_digits=10, decimal_places=2)
    category = CharField(max_length=50, db_index=True)

    class Meta:
        indexes = [
            Index(fields=["name", "category"]),
            Index(fields=["sku"], unique=True, name="idx_sku"),
        ]
        constraints = [
            CheckConstraint(check="price > 0", name="positive_price"),
            UniqueConstraint(fields=["name", "category"], name="uq_name_cat"),
        ]

# PostgreSQL-specific indexes
class Document(Model):
    table = "documents"
    content = JSONField()

    class Meta:
        indexes = [
            GinIndex(fields=["content"], name="idx_doc_gin"),
            BrinIndex(fields=["created_at"], name="idx_doc_brin"),
        ]`}
        </CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex justify-between items-center pt-8 mt-8 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <Link
          to="/docs/models/overview"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          <ArrowLeft className="w-4 h-4" /> Overview
        </Link>
        <Link
          to="/docs/models/queryset"
          className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}
        >
          QuerySet <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
