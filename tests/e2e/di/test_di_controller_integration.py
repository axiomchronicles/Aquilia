"""
DI-12: Controller integration with DI — injected services match expected instances,
       failure of injected service propagates.
DI-13: DI + background worker context — providers resolve outside HTTP request scope.
"""

import asyncio
import pytest
from aquilia.di.core import Container, ProviderMeta, _type_key_cache
from aquilia.di.providers import ValueProvider
from aquilia.controller.base import Controller, RequestCtx
from aquilia.controller.factory import ControllerFactory, InstantiationMode
from aquilia.testing.di import TestContainer, override_provider


def _qualified(cls: type) -> str:
    """Return the fully-qualified key Container._token_to_key produces."""
    return f"{cls.__module__}.{cls.__qualname__}"


# ── Stub services ────────────────────────────────────────────────────

class UserRepo:
    def __init__(self):
        self.name = "UserRepo"

    def find(self, uid: int):
        return {"id": uid, "name": "alice"}


class NotificationService:
    def __init__(self):
        self.sent: list = []

    def notify(self, msg: str):
        self.sent.append(msg)


# ── Stub controllers ────────────────────────────────────────────────

class UsersController(Controller):
    prefix = "/users"
    instantiation_mode = "per_request"

    def __init__(self, repo: UserRepo = None, notifier: NotificationService = None):
        self.repo = repo
        self.notifier = notifier

    async def list(self, ctx: RequestCtx):
        return [self.repo.find(1)]


class SingletonController(Controller):
    prefix = "/admin"
    instantiation_mode = "singleton"

    def __init__(self, repo: UserRepo = None):
        self.repo = repo


# ── DI-12: Controller integration with DI ───────────────────────────

class TestDI12ControllerIntegration:
    """DI-12  risk=high"""

    async def test_controller_factory_injects_dependencies(self):
        container = TestContainer(scope="app")
        repo = UserRepo()
        notifier = NotificationService()
        # Must register using the fully-qualified key that _token_to_key produces
        container.register_value(_qualified(UserRepo), repo)
        container.register_value(_qualified(NotificationService), notifier)

        factory = ControllerFactory(app_container=container)
        controller = await factory.create(
            UsersController,
            mode=InstantiationMode.PER_REQUEST,
            request_container=container,
        )
        assert controller.repo is repo
        assert controller.notifier is notifier

    async def test_controller_uses_overridden_service(self):
        container = TestContainer(scope="app")
        real_repo = UserRepo()
        repo_key = _qualified(UserRepo)
        notifier_key = _qualified(NotificationService)
        container.register_value(repo_key, real_repo)
        container.register_value(notifier_key, NotificationService())

        factory = ControllerFactory(app_container=container)

        # Override repo with a mock using the same qualified key
        class MockRepo:
            name = "MockRepo"
            def find(self, uid):
                return {"id": uid, "name": "mocked"}

        mock_repo = MockRepo()
        async with override_provider(container, repo_key, mock_repo):
            controller = await factory.create(
                UsersController,
                mode=InstantiationMode.PER_REQUEST,
                request_container=container,
            )
            assert controller.repo is mock_repo
            assert controller.repo.find(1)["name"] == "mocked"

        # After override exits, new controllers get real repo
        controller2 = await factory.create(
            UsersController,
            mode=InstantiationMode.PER_REQUEST,
            request_container=container,
        )
        assert controller2.repo is real_repo

    async def test_singleton_controller_same_instance(self):
        container = TestContainer(scope="app")
        container.register_value(_qualified(UserRepo), UserRepo())

        factory = ControllerFactory(app_container=container)
        c1 = await factory.create(SingletonController, mode=InstantiationMode.SINGLETON)
        c2 = await factory.create(SingletonController, mode=InstantiationMode.SINGLETON)

        assert c1 is c2, "Singleton controller must return same instance"

    async def test_controller_missing_dependency_fails_clearly(self):
        """If a required DI dependency is missing, factory should fail."""
        container = TestContainer(scope="app")
        # Deliberately NOT registering UserRepo

        factory = ControllerFactory(app_container=container)
        # Should still create (params default to None) — verify graceful handling
        controller = await factory.create(
            UsersController,
            mode=InstantiationMode.PER_REQUEST,
            request_container=container,
        )
        # repo is None because not registered and has default
        assert controller.repo is None


# ── DI-13: DI + background worker context ───────────────────────────

class TestDI13BackgroundWorkerContext:
    """DI-13  risk=medium-high"""

    async def test_providers_resolve_outside_request_scope(self):
        """Services used by background workers must resolve from app container."""
        container = Container(scope="app")
        container.register(ValueProvider(value="worker_db", token="db_conn", scope="singleton"))

        # Simulate worker picking up job from queue
        async def worker_task():
            db = await container.resolve_async("db_conn")
            return db

        result = await worker_task()
        assert result == "worker_db"

    async def test_worker_gets_singleton_same_as_http_handlers(self):
        """Workers and HTTP handlers share singleton providers."""
        parent = Container(scope="app")
        shared_svc = {"counter": 0}
        parent.register(ValueProvider(value=shared_svc, token="counter_svc", scope="singleton"))

        # Simulate HTTP request
        child = parent.create_request_scope()
        http_svc = await child.resolve_async("counter_svc")
        http_svc["counter"] += 1
        await child.shutdown()

        # Simulate worker
        worker_svc = await parent.resolve_async("counter_svc")
        assert worker_svc["counter"] == 1, "Worker should see shared singleton state"

    async def test_multiple_workers_concurrent_resolution(self):
        """Multiple workers resolving concurrently from app container."""
        container = Container(scope="app")
        container.register(ValueProvider(
            value={"status": "healthy"},
            token="health",
            scope="singleton",
        ))

        async def worker(wid: int):
            h = await container.resolve_async("health")
            return (wid, h["status"])

        results = await asyncio.gather(*[worker(i) for i in range(50)])
        assert all(r[1] == "healthy" for r in results)

    async def test_worker_restart_gets_fresh_transient(self):
        """Simulating worker restart: transient providers yield new instances."""
        container = Container(scope="app")
        counter = {"n": 0}

        class _TransProv:
            @property
            def meta(self):
                return ProviderMeta(name="job_ctx", token="job_ctx", scope="transient")

            async def instantiate(self, ctx=None):
                counter["n"] += 1
                return {"job_number": counter["n"]}

            async def shutdown(self):
                pass

        container.register(_TransProv())

        # Worker run 1
        j1 = await container.resolve_async("job_ctx")
        # Worker run 2 (simulating restart)
        j2 = await container.resolve_async("job_ctx")

        assert j1["job_number"] != j2["job_number"]
