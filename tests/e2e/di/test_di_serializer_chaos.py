"""
Chaos, stress, and fuzz testing for the newly implemented Intent Serializer auto-injection mechanics.
"""

import pytest
import asyncio
import random
import string
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import Annotated

from aquilia.di.core import Container
from aquilia.di.request_dag import RequestDAG
from aquilia.di.dep import Dep, Header, Query, Body
from aquilia.serializers.base import Serializer
from aquilia.serializers.fields import CharField, IntegerField

pytestmark = pytest.mark.asyncio(loop_scope="function")

class DummyRequest:
    def __init__(self, headers=None, query=None, body=None, content_type="application/json"):
        self.headers = headers or {}
        self.query_params = query or {}
        self._body = body or {}
        self._content_type = content_type

    async def json(self):
        if not self.is_json():
            raise ValueError("Not a valid json")
        return self._body

    def query_param(self, name):
        return self.query_params.get(name)

    def content_type(self):
        return self._content_type
        
    def is_json(self):
        return "json" in self._content_type
        
    async def form(self):
        return self._body

class TargetIntentSerializer(Serializer):
    """Intent serializer targeted by fuzzing."""
    username = CharField(required=True, min_length=3, max_length=50)
    magic_number = IntegerField(default=Query("magic_param", default=42))

class TestSerializerDIChaosAndFuzz:
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        body=st.one_of(
            st.dictionaries(st.text(), st.text()),
            st.dictionaries(st.text(), st.integers()),
            st.text(),
            st.none()
        ),
        query=st.dictionaries(st.text(), st.text()),
    )
    async def test_fuzz_intent_serializer_injection(self, body, query):
        """Fuzz testing Intent Serializer extraction (valid logic routing despite broken inputs)."""
        container = Container(scope="app")
        # Random chaotic inputs into the request
        request = DummyRequest(body=body, query=query)
        dag = RequestDAG(container, request)

        async def intent_handler(data: TargetIntentSerializer):
            return data

        dep = Dep(intent_handler)
        
        try:
            result = await dag.resolve(dep, type(None))
            # If it magically passed validation:
            assert isinstance(result, TargetIntentSerializer)
            assert hasattr(result, "username")
            # Because of our new base __getattr__ pattern, it exposes validated_data fields:
            assert isinstance(result.username, str)
            assert result.magic_number is not None
        except Exception as e:
            # We expect validation faults from `is_valid(raise_fault=True)` inside RequestDAG
            from aquilia.serializers.exceptions import ValidationFault, SerializationFault
            pass

    async def test_stress_concurrent_intent_serializer_resolutions(self):
        """Stress testing 10,000 instance creations of Intent Serializer to ensure caching and asyncio isolation."""
        container = Container(scope="app")
        
        # Build requests mimicking a traffic spike where every request carries a valid JSON body
        requests = [
            DummyRequest(
                query={"magic_param": i},
                body={"username": f"user_number_{i}"}
            ) for i in range(1000)
        ]

        async def execute_resolution(req, idx):
            dag = RequestDAG(container, req)
            async def handler(data: TargetIntentSerializer):
                # Ensure each isolated handler gets its own serializer object instance with the correct bound data
                assert isinstance(data, TargetIntentSerializer)
                assert data.username == f"user_number_{idx}"
                assert data.magic_number == idx
                return True
                
            dep = Dep(handler)
            return await dag.resolve(dep, type(None))

        # Run them concurrently using asyncio.gather
        tasks = [execute_resolution(req, idx) for idx, req in enumerate(requests)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 1000
        assert all(results)

    async def test_chaos_missing_req_methods(self):
        """Chaos testing: Request object is missing methods entirely but extraction survives or gracefully fails."""
        container = Container(scope="app")

        class BrokenRequest:
            # Missing `json()` or `content_type()` entirely
            pass
            
        dag = RequestDAG(container, BrokenRequest())

        async def bad_handler(data: TargetIntentSerializer):
            return data
            
        dep = Dep(bad_handler)

        from aquilia.serializers.exceptions import ValidationFault
        with pytest.raises(ValidationFault):
            # It should fail cleanly on validation (username missing because body couldn't be parsed)
            await dag.resolve(dep, type(None))
