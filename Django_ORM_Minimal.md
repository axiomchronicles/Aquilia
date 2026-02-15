# Django ORM --- Ultra In‑Depth Guide with Extensive Examples

> This document goes **deeper than official docs**. Every section
> includes **real-world usage examples**, anti-patterns, and performance
> notes. This is suitable for **senior backend engineers, framework
> authors, and ORM designers**.

------------------------------------------------------------------------

## 1. Models --- From Simple to Real World

``` python
class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Access patterns

``` python
User.objects.get(username="alice")
User.objects.filter(is_active=True)
User.objects.only("id", "username")
User.objects.defer("email")
```

⚠️ `only()` and `defer()` are **advanced tools**---misuse causes hidden
queries.

------------------------------------------------------------------------

## 2. Field Behavior & Descriptors

``` python
u = User.objects.first()
u.username          # attribute access
User._meta.fields   # field definitions
```

Fields act as **descriptors**, converting DB → Python automatically.

------------------------------------------------------------------------

## 3. Relationships --- Deep Examples

### ForeignKey

``` python
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    total = models.DecimalField(max_digits=10, decimal_places=2)
```

``` python
order = Order.objects.select_related("user").get(id=1)
order.user.email   # no extra query
```

### Reverse FK

``` python
user.orders.all()
```

------------------------------------------------------------------------

## 4. ManyToMany with Through Model

``` python
class Course(models.Model):
    name = models.CharField(max_length=100)

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField()

class Course(models.Model):
    students = models.ManyToManyField(User, through=Enrollment)
```

``` python
Enrollment.objects.create(user=u, course=c, enrolled_at=timezone.now())
```

------------------------------------------------------------------------

## 5. QuerySets --- Internal Mechanics

``` python
qs = User.objects.filter(is_active=True)
qs2 = qs.exclude(email__contains="spam")
```

✔️ QuerySets are **immutable** ✔️ Each chain clones internal `Query`

``` python
qs.query
str(qs.query)
```

------------------------------------------------------------------------

## 6. Filtering --- EVERY Lookup Example

``` python
User.objects.filter(username__iexact="admin")
User.objects.filter(email__icontains="gmail")
User.objects.filter(id__in=[1,2,3])
User.objects.filter(created_at__date=date.today())
User.objects.filter(created_at__range=(a, b))
User.objects.filter(username__regex=r"^[a-z]+$")
```

------------------------------------------------------------------------

## 7. Q Objects --- Complex Conditions

``` python
from django.db.models import Q

User.objects.filter(
    Q(username__startswith="a") |
    Q(email__endswith=".org"),
    is_active=True
)
```

------------------------------------------------------------------------

## 8. F Expressions --- Race‑Safe Updates

``` python
Product.objects.filter(id=1).update(stock=F("stock") - 1)
```

✔️ Happens fully in SQL ❌ Never do read‑modify‑save in Python under
concurrency

------------------------------------------------------------------------

## 9. Annotation & Aggregation --- Practical

``` python
from django.db.models import Count, Sum

User.objects.annotate(
    order_count=Count("orders"),
    total_spent=Sum("orders__total")
).filter(order_count__gt=5)
```

------------------------------------------------------------------------

## 10. Subquery & Exists --- Power Moves

``` python
latest = Order.objects.filter(
    user=OuterRef("pk")
).order_by("-created_at")

User.objects.annotate(
    last_order=Subquery(latest.values("total")[:1])
)
```

``` python
User.objects.filter(
    Exists(Order.objects.filter(user=OuterRef("pk")))
)
```

------------------------------------------------------------------------

## 11. select_related vs prefetch_related (N+1 Killer)

``` python
Order.objects.select_related("user")
Order.objects.prefetch_related("items")
```

Rule: - FK / O2O → select_related - M2M / reverse FK → prefetch_related

------------------------------------------------------------------------

## 12. Prefetch Custom Query

``` python
from django.db.models import Prefetch

User.objects.prefetch_related(
    Prefetch("orders", queryset=Order.objects.filter(total__gt=500))
)
```

------------------------------------------------------------------------

## 13. Bulk Operations --- Performance

``` python
User.objects.bulk_create([
    User(username="a"),
    User(username="b")
], batch_size=1000)
```

❌ No signals\
❌ No `save()`\
✔️ Extremely fast

------------------------------------------------------------------------

## 14. Transactions & Locking

``` python
with transaction.atomic():
    product = Product.objects.select_for_update().get(id=1)
    product.stock -= 1
    product.save()
```

✔️ Prevents overselling

------------------------------------------------------------------------

## 15. Signals --- When (NOT) to Use

``` python
@receiver(post_save, sender=User)
def after_user_create(sender, instance, created, **kwargs):
    if created:
        send_welcome_email(instance)
```

⚠️ Avoid business logic in signals for large systems.

------------------------------------------------------------------------

## 16. Migrations --- Real Examples

``` python
migrations.RunPython(forward_func, reverse_func)
```

``` python
apps.get_model("shop", "Product")
```

✔️ Historical models\
❌ Never import live models

------------------------------------------------------------------------

## 17. Raw SQL --- Hybrid ORM

``` python
with connection.cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM users")
```

``` python
Model.objects.raw("SELECT * FROM table WHERE id=%s", [1])
```

------------------------------------------------------------------------

## 18. Multiple Databases

``` python
User.objects.using("replica").get(id=1)
```

Router decides routing.

------------------------------------------------------------------------

## 19. Custom Fields --- Complete Example

``` python
class UpperCharField(models.CharField):
    def get_prep_value(self, value):
        return value.upper()
```

------------------------------------------------------------------------

## 20. PostgreSQL ORM Superpowers

``` python
Book.objects.filter(metadata__rating__gte=4)
```

``` python
from django.contrib.postgres.search import SearchVector
Book.objects.annotate(search=SearchVector("title")).filter(search="django")
```

------------------------------------------------------------------------

## 21. ORM Internals --- SQL Compiler

Flow:

    QuerySet
     → Query
       → Compiler
         → SQL + params

Backends override: - DatabaseOperations - DatabaseFeatures

------------------------------------------------------------------------

## 22. Performance Engineering

✔️ Index foreign keys\
✔️ Use `exists()` instead of `count()`\
✔️ Inspect `.explain()`\
✔️ Avoid Python loops

``` python
print(qs.explain())
```

------------------------------------------------------------------------

## 23. Testing ORM Code

``` python
class UserTest(TestCase):
    def test_creation(self):
        self.assertEqual(User.objects.count(), 1)
```

------------------------------------------------------------------------

## 24. Admin ORM Hooks

``` python
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username")
    search_fields = ("username",)
```

------------------------------------------------------------------------

## 25. ORM Design Lessons (Framework Authors)

Key ideas Django nailed: - Immutable QuerySets - Compiler abstraction -
Descriptor-based fields - App registry - Declarative schema

This section alone can power a **custom ORM like Aquilia**.

------------------------------------------------------------------------

## END

This document is intentionally **extreme in depth**.
