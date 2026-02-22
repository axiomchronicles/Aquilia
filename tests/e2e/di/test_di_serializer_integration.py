"""
Tests for deep integration between Aquilia's DI system (RequestDAG/Dep)
and Aquilia's Serializer system.
"""

import pytest
import asyncio
from typing import Annotated

from aquilia.di.core import Container
from aquilia.di.request_dag import RequestDAG
from aquilia.di.dep import Dep, Header, Query, Body
from aquilia.serializers.base import Serializer
from aquilia.serializers.fields import CharField, IntegerField

pytestmark = pytest.mark.asyncio(loop_scope="function")

# --- Dummy Request Setup ---

class DummyRequest:
    def __init__(self, headers=None, query=None, body=None):
        self.headers = headers or {}
        self.query_params = query or {}
        self._body = body or {}
        self._body_cache = self._body

    async def json(self):
        return self._body

    def query_param(self, name):
        return self.query_params.get(name)

    def content_type(self):
        return "application/json"
        
    def is_json(self):
        return True

# --- Test Serializers ---

class PaginationSerializer(Serializer):
    """A serializer that extracts its data completely from Query params."""
    page = IntegerField(default=Query("page", default=1))
    limit = IntegerField(default=Query("limit", default=25), max_value=100)
    
class MetadataSerializer(Serializer):
    """A serializer that mixes Header, Query, and Body."""
    user_agent = CharField(default=Header("User-Agent", required=True))
    trace_id = CharField(default=Header("X-Trace-Id", default="no-trace", required=False), required=False)
    search = CharField(default=Query("q", default=""), required=False)
    payload_name = CharField(required=True)  # implicitly from body


# --- Tests ---

class TestSerializerDIIntegration:
    async def test_request_dag_resolves_serializer(self):
        """Test RequestDAG automatically instantiating a Serializer subclass."""
        container = Container(scope="app")
        request = DummyRequest(
            query={"page": "2", "limit": "50"}
        )
        dag = RequestDAG(container, request)

        # A dummy handler that depends on the serializer
        async def my_handler(params: PaginationSerializer):
            return params

        dep = Dep(my_handler)
        
        # When resolving `my_handler` through the DAG, it will identify `params` 
        # as a Serializer, extract 'page' and 'limit' from Query, and return 
        # the validated data dict.
        result = await dag.resolve(dep, type(None))
        
        # It's returned as validated_data because the param name is just "params"
        assert isinstance(result, dict)
        assert result["page"] == 2
        assert result["limit"] == 50
        
    async def test_serializer_instance_injection(self):
        """Test that ending the param with _serializer gives the instance."""
        container = Container(scope="app")
        request = DummyRequest(
            query={"page": "3", "limit": "10"}
        )
        dag = RequestDAG(container, request)

        async def my_handler(pagination_serializer: PaginationSerializer):
            return pagination_serializer

        dep = Dep(my_handler)
        result = await dag.resolve(dep, type(None))
        
        # Should be a full serializer instance
        assert isinstance(result, PaginationSerializer)
        assert result.validated_data["page"] == 3
        assert result.validated_data["limit"] == 10

    async def test_serializer_mixed_extraction(self):
        """Test extraction from Header, Query, and Body simultaneously."""
        container = Container(scope="app")
        request = DummyRequest(
            headers={"user-agent": "Aquilia-Agent/1.0"},
            query={"q": "hello world"},
            body={"payload_name": "My Payload"}
        )
        dag = RequestDAG(container, request)

        async def metadata_handler(data: MetadataSerializer):
            return data

        dep = Dep(metadata_handler)
        try:
            result = await dag.resolve(dep, type(None))
        except Exception as exc:
            if hasattr(exc, "errors"):
                print("Validation Errors:", exc.errors)
            raise exc
        
        assert isinstance(result, dict)
        assert result["user_agent"] == "Aquilia-Agent/1.0"
        assert result["search"] == "hello world"
        assert result["payload_name"] == "My Payload"
        assert result["trace_id"] == "no-trace"  # from default

    async def test_serializer_missing_required_extraction(self):
        """Test missing required Header throws validation error directly in Serializer."""
        container = Container(scope="app")
        # Missing user-agent header
        request = DummyRequest(
            body={"payload_name": "My Payload"}
        )
        dag = RequestDAG(container, request)

        async def failing_handler(data: MetadataSerializer):
            return data

        dep = Dep(failing_handler)
        
        from aquilia.serializers.exceptions import ValidationFault
        with pytest.raises(ValidationFault) as exc:
            await dag.resolve(dep, type(None))
            
        assert "user_agent" in exc.value.errors


