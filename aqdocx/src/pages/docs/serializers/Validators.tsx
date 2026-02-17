import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Shield } from 'lucide-react'

export function SerializerValidators() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const box = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Shield className="w-4 h-4" />
          Serializers / Validators
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Validators
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Validators enforce constraints beyond basic field types. Aquilia provides field-level validators, object-level validators, and advanced compound/conditional validators for complex business rules.
        </p>
      </div>

      {/* Built-in Validators */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Built-in Validators</h2>
        <div className={box}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                  <th className="text-left pb-3 font-semibold">Validator</th>
                  <th className="text-left pb-3 font-semibold">Args</th>
                  <th className="text-left pb-3 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                {[
                  ['UniqueValidator', 'queryset, field', 'Ensures the value is unique across the model table'],
                  ['UniqueTogetherValidator', 'queryset, fields', 'Ensures the combination of fields is unique'],
                  ['MaxLengthValidator', 'max_length', 'Rejects strings longer than max_length'],
                  ['MinLengthValidator', 'min_length', 'Rejects strings shorter than min_length'],
                  ['MaxValueValidator', 'max_value', 'Rejects numbers greater than max_value'],
                  ['MinValueValidator', 'min_value', 'Rejects numbers less than min_value'],
                  ['RegexValidator', 'pattern, message', 'Validates against a regular expression'],
                  ['RangeValidator', 'min, max', 'Ensures a number falls within a range'],
                  ['CompoundValidator', 'validators, mode', 'Combines multiple validators with AND/OR logic'],
                  ['ConditionalValidator', 'condition, validator', 'Applies a validator only when a condition is met'],
                ].map(([name, args, desc], i) => (
                  <tr key={i} className={`border-t ${isDark ? 'border-white/5' : 'border-gray-100'}`}>
                    <td className="py-2 font-mono text-aquilia-400 text-xs">{name}</td>
                    <td className="py-2 font-mono text-xs">{args}</td>
                    <td className="py-2 text-xs">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Field-Level Validators */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Field-Level Validators</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Attach validators to individual fields via the <code className="text-aquilia-400">validators</code> argument.
        </p>
        <CodeBlock language="python" filename="field_validators.py">{`from aquilia.serializers import (
    Serializer, CharField, IntegerField,
    RegexValidator, RangeValidator, MinLengthValidator,
)

class RegisterSerializer(Serializer):
    username = CharField(
        max_length=30,
        validators=[
            MinLengthValidator(3),
            RegexValidator(
                pattern=r"^[a-zA-Z0-9_]+$",
                message="Only letters, numbers, and underscores allowed",
            ),
        ],
    )
    age = IntegerField(
        validators=[RangeValidator(min=13, max=120)],
    )`}</CodeBlock>
      </section>

      {/* Object-Level Validation */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Object-Level Validation</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Override <code className="text-aquilia-400">validate()</code> to enforce cross-field constraints that involve multiple fields simultaneously.
        </p>
        <CodeBlock language="python" filename="object_validate.py">{`from aquilia.serializers import Serializer, CharField, DateField

class EventSerializer(Serializer):
    title = CharField(max_length=200)
    start_date = DateField()
    end_date = DateField()

    def validate(self, data):
        if data["end_date"] <= data["start_date"]:
            raise self.validation_error(
                "end_date must be after start_date"
            )
        return data`}</CodeBlock>
      </section>

      {/* Unique Validators */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Unique Validators</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Database-aware validators that check uniqueness against the model's queryset.
        </p>
        <CodeBlock language="python" filename="unique.py">{`from aquilia.serializers import (
    ModelSerializer, UniqueValidator, UniqueTogetherValidator,
)
from myapp.models import User

class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "department"]
        validators = [
            UniqueTogetherValidator(
                queryset=User.objects.all(),
                fields=["email", "department"],
                message="This email is already registered in this department",
            ),
        ]

    # Per-field unique check
    username = CharField(
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="Username already taken",
            ),
        ],
    )`}</CodeBlock>
      </section>

      {/* Compound & Conditional */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Compound & Conditional Validators</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          For advanced business rules, compose validators with boolean logic or apply them conditionally.
        </p>
        <CodeBlock language="python" filename="compound.py">{`from aquilia.serializers import (
    Serializer, CharField, IntegerField,
    CompoundValidator, ConditionalValidator,
    MinValueValidator, MaxValueValidator, RegexValidator,
)

class PricingSerializer(Serializer):
    price = IntegerField(
        validators=[
            CompoundValidator(
                validators=[
                    MinValueValidator(0),
                    MaxValueValidator(999999),
                ],
                mode="AND",  # Both must pass
            ),
        ],
    )
    discount_code = CharField(
        required=False,
        validators=[
            ConditionalValidator(
                condition=lambda data: data.get("price", 0) > 100,
                validator=RegexValidator(
                    pattern=r"^DISC-[A-Z0-9]{6}$",
                    message="Discount code format: DISC-XXXXXX",
                ),
            ),
        ],
    )`}</CodeBlock>
      </section>

      {/* Fault Integration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fault Integration</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Validation errors are surfaced as typed faults flowing through the Aquilia fault system. Three fault types cover all serializer errors.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { name: 'SerializationFault', desc: 'General serialization/deserialization failures' },
            { name: 'ValidationFault', desc: 'Object-level validation errors' },
            { name: 'FieldValidationFault', desc: 'Individual field validation errors with field name context' },
          ].map((f, i) => (
            <div key={i} className={box}>
              <h3 className={`font-mono font-bold text-sm mb-1 ${isDark ? 'text-red-400' : 'text-red-600'}`}>{f.name}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
