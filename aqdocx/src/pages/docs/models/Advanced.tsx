import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Database } from 'lucide-react'

export function ModelsAdvanced() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Database className="w-4 h-4" />
          Models / Advanced
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Signals, Transactions & Aggregation
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Advanced ORM features for reactive model events, transactional integrity, and complex data aggregation queries.
        </p>
      </div>

      {/* Signals */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Model Signals</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Signals let you hook into model lifecycle events. They fire before/after create, update, and delete operations.
        </p>
        <CodeBlock language="python" filename="signals.py">{`from aquilia.models import Model, CharField, DateTimeField
from aquilia.models.signals import pre_save, post_save, pre_delete, post_delete


class Article(Model):
    title = CharField(max_length=200)
    slug = CharField(max_length=200)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        table_name = "articles"


# Register signal handlers

@pre_save(Article)
async def generate_slug(instance, **kwargs):
    """Auto-generate slug before save."""
    if not instance.slug:
        instance.slug = slugify(instance.title)


@post_save(Article)
async def notify_subscribers(instance, created: bool, **kwargs):
    """Send notification after article is saved."""
    if created:
        await notification_service.broadcast(
            f"New article: {instance.title}"
        )


@pre_delete(Article)
async def archive_before_delete(instance, **kwargs):
    """Archive article content before deletion."""
    await archive_service.store(instance)


@post_delete(Article)
async def cleanup_after_delete(instance, **kwargs):
    """Clean up related resources."""
    await cache.delete(f"article:{instance.id}")
    await search_index.remove(instance.id)`}</CodeBlock>

        <div className={`mt-6 ${boxClass}`}>
          <h3 className={`text-sm font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Available Signals</h3>
          <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                  <th className={`text-left py-2.5 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Signal</th>
                  <th className={`text-left py-2.5 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Fires</th>
                  <th className={`text-left py-2.5 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Extra kwargs</th>
                </tr>
              </thead>
              <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
                {[
                  { s: 'pre_save', f: 'Before .save()', k: 'is_new: bool' },
                  { s: 'post_save', f: 'After .save()', k: 'created: bool' },
                  { s: 'pre_delete', f: 'Before .delete()', k: '—' },
                  { s: 'post_delete', f: 'After .delete()', k: '—' },
                  { s: 'pre_update', f: 'Before queryset.update()', k: 'fields: dict' },
                  { s: 'post_update', f: 'After queryset.update()', k: 'affected: int' },
                ].map((row, i) => (
                  <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                    <td className="py-2.5 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.s}</code></td>
                    <td className={`py-2.5 px-4 text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.f}</td>
                    <td className={`py-2.5 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.k}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Transactions */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Transactions</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Wrap multiple database operations in an atomic transaction. If any operation fails, all changes are rolled back.
        </p>
        <CodeBlock language="python" filename="transactions.py">{`from aquilia.db import transaction


# Context manager
async def transfer_funds(from_id: int, to_id: int, amount: float):
    async with transaction() as tx:
        sender = await Account.objects.get(id=from_id)
        receiver = await Account.objects.get(id=to_id)

        if sender.balance < amount:
            raise InsufficientFunds()

        sender.balance -= amount
        receiver.balance += amount

        await sender.save()
        await receiver.save()
        # Both saves commit together, or both rollback


# Decorator form
@transaction()
async def create_order(user_id: int, items: list):
    order = await Order.objects.create(user_id=user_id, status="pending")

    for item in items:
        await OrderItem.objects.create(
            order_id=order.id,
            product_id=item["product_id"],
            quantity=item["quantity"],
            price=item["price"],
        )

    # Update inventory
    for item in items:
        product = await Product.objects.get(id=item["product_id"])
        product.stock -= item["quantity"]
        await product.save()

    return order


# Nested transactions (savepoints)
async with transaction() as tx:
    await User.objects.create(name="Alice")

    async with transaction(savepoint=True) as sp:
        await User.objects.create(name="Bob")
        # Rollback only this savepoint
        await sp.rollback()

    # Alice is still committed, Bob is rolled back`}</CodeBlock>
      </section>

      {/* Aggregation */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Aggregation</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Perform aggregate computations (count, sum, avg, min, max) directly on querysets.
        </p>
        <CodeBlock language="python" filename="aggregation.py">{`from aquilia.models import Count, Sum, Avg, Min, Max

# Simple aggregation
total_users = await User.objects.count()
total_revenue = await Order.objects.aggregate(Sum("total"))
avg_price = await Product.objects.aggregate(Avg("price"))
cheapest = await Product.objects.aggregate(Min("price"))
most_expensive = await Product.objects.aggregate(Max("price"))

# Multiple aggregations
stats = await Order.objects.aggregate(
    total=Sum("total"),
    average=Avg("total"),
    count=Count("id"),
    min_order=Min("total"),
    max_order=Max("total"),
)
# → {"total": 15000.0, "average": 150.0, "count": 100, ...}

# Filtered aggregation
active_revenue = await Order.objects.filter(
    status="completed"
).aggregate(Sum("total"))

# Group by
by_status = await Order.objects.values("status").annotate(
    count=Count("id"),
    total=Sum("total"),
)
# → [
#   {"status": "completed", "count": 80, "total": 12000.0},
#   {"status": "pending", "count": 15, "total": 2500.0},
#   {"status": "cancelled", "count": 5, "total": 500.0},
# ]

# Group by with ordering
top_customers = await Order.objects.values("user_id").annotate(
    total_spent=Sum("total"),
    order_count=Count("id"),
).order_by("-total_spent").limit(10)`}</CodeBlock>
      </section>

      {/* Nav */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-white/10">
        <Link to="/docs/models/migrations" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          <ArrowLeft className="w-4 h-4" /> Migrations
        </Link>
        <Link to="/docs/serializers" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          Serializers <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
