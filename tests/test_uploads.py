"""
Test 4: Uploads (_uploads.py)

Tests UploadFile, FormData, UploadStore, LocalUploadStore.
"""

import pytest
import tempfile
from pathlib import Path

from aquilia._uploads import (
    UploadFile, FormData, LocalUploadStore,
    create_upload_file_from_bytes, create_upload_file_from_path,
)
from aquilia._datastructures import MultiDict


# ============================================================================
# UploadFile
# ============================================================================

class TestUploadFile:

    @pytest.mark.asyncio
    async def test_in_memory_read(self):
        uf = create_upload_file_from_bytes(
            filename="test.txt",
            content=b"hello world",
            content_type="text/plain",
        )
        assert uf.filename == "test.txt"
        assert uf.content_type == "text/plain"
        data = await uf.read()
        assert data == b"hello world"

    @pytest.mark.asyncio
    async def test_read_partial(self):
        uf = create_upload_file_from_bytes(
            filename="data.bin",
            content=b"0123456789",
            content_type="application/octet-stream",
        )
        partial = await uf.read(5)
        assert partial == b"01234"

    @pytest.mark.asyncio
    async def test_file_on_disk(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"disk content")
            tmp_path = Path(f.name)

        try:
            uf = create_upload_file_from_path(
                filename="disk.txt",
                file_path=tmp_path,
                content_type="text/plain",
            )
            data = await uf.read()
            assert data == b"disk content"
        finally:
            tmp_path.unlink(missing_ok=True)


# ============================================================================
# FormData
# ============================================================================

class TestFormData:

    def test_fields_only(self):
        fields = MultiDict([("name", "Alice"), ("age", "30")])
        fd = FormData(fields=fields, files={})
        assert fd.fields.get("name") == "Alice"
        assert fd.fields.get("age") == "30"
        assert len(fd.files) == 0

    def test_with_files(self):
        fields = MultiDict()
        uf = create_upload_file_from_bytes("doc.pdf", b"pdf-data", "application/pdf")
        fd = FormData(fields=fields, files={"document": [uf]})
        assert "document" in fd.files
        assert fd.files["document"][0].filename == "doc.pdf"

    @pytest.mark.asyncio
    async def test_cleanup(self):
        fields = MultiDict()
        fd = FormData(fields=fields, files={})
        await fd.cleanup()  # Should not raise


# ============================================================================
# LocalUploadStore
# ============================================================================

class TestLocalUploadStore:

    def test_init(self):
        with tempfile.TemporaryDirectory() as d:
            store = LocalUploadStore(upload_dir=d)
            assert store.upload_dir == Path(d)
