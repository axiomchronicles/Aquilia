"""
Aquilia Model Manager — descriptor-based QuerySet access.

Provides Django-style Manager that returns QuerySets from the model class:

    class User(Model):
        table = "users"
        name = CharField(max_length=150)

        objects = Manager()

    users = await User.objects.filter(active=True).all()
    users = await User.objects.all()

The default Manager is automatically attached as ``objects`` on every Model
unless overridden.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Model, Q


__all__ = ["Manager", "BaseManager", "QuerySet"]


class QuerySet:
    """
    A reusable set of query methods that can be attached to a Manager.

    Define custom query methods here, then use Manager.from_queryset()
    to create a Manager class that delegates to those methods.

    Usage:
        class UserQuerySet(QuerySet):
            def active(self):
                return self.get_queryset().filter(active=True)

            def adults(self):
                return self.get_queryset().filter(age__gte=18)

        UserManager = Manager.from_queryset(UserQuerySet)

        class User(Model):
            objects = UserManager()

        # Now you can call:
        users = await User.objects.active().adults().all()
    """

    _model_cls: Optional[Type[Model]] = None

    def _get_queryset(self) -> Q:
        if self._model_cls is None:
            raise RuntimeError("QuerySet is not bound to a model")
        return self._model_cls.query()

    def get_queryset(self) -> Q:
        return self._get_queryset()


class BaseManager:
    """
    Minimal manager with descriptor protocol.

    Subclass this to create custom managers with pre-filtered querysets.
    """

    _model_cls: Optional[Type[Model]] = None

    def __set_name__(self, owner: type, name: str) -> None:
        self._model_cls = owner  # type: ignore

    def __get__(self, instance: Any, owner: type) -> BaseManager:
        # Ensure model class is always current (supports inheritance)
        self._model_cls = owner  # type: ignore
        if instance is not None:
            raise AttributeError(
                "Manager is accessible only via the model class, not instances."
            )
        return self

    # ── QuerySet proxy methods ───────────────────────────────────────

    def _get_queryset(self) -> Q:
        """Return a fresh QuerySet for the model."""
        if self._model_cls is None:
            raise RuntimeError("Manager is not bound to a model")
        return self._model_cls.query()

    def get_queryset(self) -> Q:
        """
        Override point for custom managers.

        Example:
            class ActiveManager(Manager):
                def get_queryset(self):
                    return super().get_queryset().filter(active=True)
        """
        return self._get_queryset()

    # ── Forwarded query methods ──────────────────────────────────────

    def filter(self, **kwargs: Any) -> Q:
        return self.get_queryset().filter(**kwargs)

    def exclude(self, **kwargs: Any) -> Q:
        return self.get_queryset().exclude(**kwargs)

    def where(self, clause: str, *args: Any, **kwargs: Any) -> Q:
        return self.get_queryset().where(clause, *args, **kwargs)

    def order(self, *fields: str) -> Q:
        return self.get_queryset().order(*fields)

    def limit(self, n: int) -> Q:
        return self.get_queryset().limit(n)

    def offset(self, n: int) -> Q:
        return self.get_queryset().offset(n)

    async def all(self) -> List[Model]:
        return await self.get_queryset().all()

    async def first(self) -> Optional[Model]:
        return await self.get_queryset().first()

    async def one(self) -> Model:
        return await self.get_queryset().one()

    async def count(self) -> int:
        return await self.get_queryset().count()

    async def exists(self) -> bool:
        return await self.get_queryset().exists()

    async def values(self, *fields: str) -> List[Dict[str, Any]]:
        return await self.get_queryset().values(*fields)

    async def values_list(self, *fields: str, flat: bool = False) -> List[Any]:
        return await self.get_queryset().values_list(*fields, flat=flat)

    async def update(self, values: Optional[Dict[str, Any]] = None, **kwargs: Any) -> int:
        return await self.get_queryset().update(values, **kwargs)

    async def delete(self) -> int:
        return await self.get_queryset().delete()

    # ── Convenience shortcuts ────────────────────────────────────────

    async def get(self, pk: Any = None, **filters: Any) -> Optional[Model]:
        """Shortcut: delegate to model's get()."""
        if self._model_cls is None:
            raise RuntimeError("Manager is not bound to a model")
        return await self._model_cls.get(pk=pk, **filters)

    async def get_or_create(
        self, defaults: Optional[Dict[str, Any]] = None, **lookup: Any
    ) -> Tuple[Model, bool]:
        if self._model_cls is None:
            raise RuntimeError("Manager is not bound to a model")
        return await self._model_cls.get_or_create(defaults=defaults, **lookup)

    async def create(self, **data: Any) -> Model:
        if self._model_cls is None:
            raise RuntimeError("Manager is not bound to a model")
        return await self._model_cls.create(**data)

    async def bulk_create(self, instances: List[Dict[str, Any]]) -> List[Model]:
        if self._model_cls is None:
            raise RuntimeError("Manager is not bound to a model")
        return await self._model_cls.bulk_create(instances)

    def __repr__(self) -> str:
        model_name = self._model_cls.__name__ if self._model_cls else "<unbound>"
        return f"<{self.__class__.__name__} for {model_name}>"


class Manager(BaseManager):
    """
    Default manager — attached as ``objects`` on every Model.

    Override ``get_queryset()`` to create custom managers:

        class PublishedManager(Manager):
            def get_queryset(self):
                return super().get_queryset().filter(status="published")

        class Article(Model):
            table = "articles"
            title = CharField(max_length=200)
            status = CharField(max_length=20, default="draft")

            objects = Manager()          # default
            published = PublishedManager()  # custom

    Or use from_queryset() to compose:

        class ArticleQuerySet(QuerySet):
            def published(self):
                return self.get_queryset().filter(status="published")

            def by_author(self, author_id):
                return self.get_queryset().filter(author_id=author_id)

        ArticleManager = Manager.from_queryset(ArticleQuerySet)
    """

    @classmethod
    def from_queryset(cls, queryset_class: type, class_name: str = None) -> type:
        """
        Create a new Manager class that includes methods from a QuerySet class.

        This allows you to define reusable query methods on a QuerySet and
        have them available directly on the Manager.

        Usage:
            class CustomQuerySet(QuerySet):
                def active(self):
                    return self.get_queryset().filter(active=True)

            CustomManager = Manager.from_queryset(CustomQuerySet)

            class MyModel(Model):
                objects = CustomManager()

            # Now: MyModel.objects.active() works
        """
        if class_name is None:
            class_name = f"{cls.__name__}From{queryset_class.__name__}"

        # Copy QuerySet methods to a new Manager subclass
        attrs: Dict[str, Any] = {}
        for attr_name in dir(queryset_class):
            if attr_name.startswith("_"):
                continue
            attr = getattr(queryset_class, attr_name)
            if callable(attr) and attr_name not in dir(cls):
                # Wrap the method to bind _model_cls
                def _make_proxy(method_name: str):
                    def _proxy(self_mgr, *args, **kwargs):
                        qs_instance = queryset_class()
                        qs_instance._model_cls = self_mgr._model_cls
                        return getattr(qs_instance, method_name)(*args, **kwargs)
                    _proxy.__name__ = method_name
                    _proxy.__qualname__ = f"{class_name}.{method_name}"
                    return _proxy

                attrs[attr_name] = _make_proxy(attr_name)

        new_cls = type(class_name, (cls,), attrs)
        return new_cls
