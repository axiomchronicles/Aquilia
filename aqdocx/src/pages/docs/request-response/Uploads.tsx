import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Upload, HardDrive, FileUp } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function UploadsPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Upload className="w-4 h-4" />
          Request / File Uploads
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            File Uploads
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides <code className="text-aquilia-500">UploadFile</code>, <code className="text-aquilia-500">FormData</code>,
          and <code className="text-aquilia-500">UploadStore</code> abstractions in <code className="text-aquilia-500">aquilia._uploads</code> for handling multipart file uploads.
          Files can be kept in memory, streamed from disk, saved to local filesystem, or routed to pluggable storage backends.
          The framework handles disk spilling, filename sanitization, and cleanup automatically.
        </p>
      </div>

      {/* ================================================================ */}
      {/* UploadFile */}
      {/* ================================================================ */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <FileUp className="w-6 h-6 text-aquilia-500" />
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>UploadFile</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A <code className="text-aquilia-500">@dataclass</code> representing a single uploaded file. Supports two storage modes: in-memory
          (content stored as bytes in <code className="text-aquilia-500">_content</code>) and on-disk (file path stored in
          <code className="text-aquilia-500"> _file_path</code>). The multipart parser automatically chooses the mode based on the
          <code className="text-aquilia-500"> form_memory_threshold</code> setting.
        </p>

        <h3 className={`text-lg font-semibold mt-6 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fields</h3>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Field</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { f: 'filename', t: 'str', d: 'Original filename (sanitized by parser)' },
                { f: 'content_type', t: 'str', d: 'MIME type (e.g. "image/jpeg", default: "application/octet-stream")' },
                { f: 'size', t: 'int | None', d: 'File size in bytes (known after reading or from stat)' },
                { f: '_content', t: 'bytes | None', d: 'In-memory file content (for small files)' },
                { f: '_file_path', t: 'Path | None', d: 'Disk path (for large files that were spilled to disk)' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.f}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Methods</h3>
        <CodeBlock language="python" filename="upload_file_api.py">{`# Read entire file content into memory
content: bytes = await upload.read()

# Stream file in chunks (memory-efficient for large files)
async for chunk in upload.stream():
    process(chunk)
# For on-disk files: uses aiofiles if available, falls back to executor
# For in-memory files: yields _content in a single chunk

# Save to destination path
saved_path: Path = await upload.save(
    "/uploads/avatars/photo.jpg",
    overwrite=False,  # Raises FileExistsError if True and file exists
)
# For in-memory files: writes _content to dest
# For on-disk files: moves (renames) the temp file to dest

# Cleanup (remove temp file if on disk)
await upload.close()`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Usage Example</h3>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Post
from aquilia.response import Response


class AvatarController(Controller):
    prefix = "/api/avatars"

    @Post("/upload")
    async def upload_avatar(self, ctx):
        form = await ctx.request.multipart()
        avatar = form.get_file("avatar")

        if not avatar:
            return Response.json({"error": "No file"}, status=400)

        # Check properties
        print(avatar.filename)       # → "photo.jpg"
        print(avatar.content_type)   # → "image/jpeg"
        print(avatar.size)           # → 204800

        # Validate
        if avatar.size > 5 * 1024 * 1024:
            return Response.json({"error": "Too large"}, status=413)

        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        if avatar.content_type not in allowed_types:
            return Response.json({"error": "Invalid type"}, status=415)

        # Save to disk
        path = await avatar.save(f"/uploads/avatars/{avatar.filename}")

        return Response.json({
            "path": str(path),
            "size": avatar.size,
        }, status=201)`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* FormData */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>FormData</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A <code className="text-aquilia-500">@dataclass</code> containing both regular form fields and uploaded files from a parsed request body.
          Returned by both <code className="text-aquilia-500">request.form()</code> (URL-encoded) and <code className="text-aquilia-500">request.multipart()</code>.
        </p>

        <h3 className={`text-lg font-semibold mt-6 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fields</h3>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Field</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { f: 'fields', t: 'MultiDict', d: 'Regular form fields (text key-value pairs). Supports repeated keys.' },
                { f: 'files', t: 'Dict[str, List[UploadFile]]', d: 'Uploaded files grouped by field name. Each field can have multiple files.' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.f}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Methods</h3>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Returns</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { m: 'get(name)', t: 'str | UploadFile | None', d: 'Get first field or file by name (fields checked first)' },
                { m: 'get_field(name)', t: 'str | None', d: 'Get first value for a text field' },
                { m: 'get_all_fields(name)', t: 'List[str]', d: 'Get all values for a text field (repeated keys)' },
                { m: 'get_file(name)', t: 'UploadFile | None', d: 'Get first uploaded file for a field name' },
                { m: 'get_all_files(name)', t: 'List[UploadFile]', d: 'Get all uploaded files for a field name' },
                { m: 'cleanup()', t: 'async None', d: 'Close all UploadFile instances and remove temp files' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <CodeBlock language="python" filename="formdata_usage.py">{`form = await request.multipart()

# Text fields
title = form.get_field("title")                 # → "My Article"
tags = form.get_all_fields("tags")              # → ["python", "async"]

# File uploads
cover = form.get_file("cover_image")            # → UploadFile | None
attachments = form.get_all_files("attachments") # → [UploadFile, ...]

# Generic access (checks fields first, then files)
value = form.get("title")        # → "My Article" (string)
value = form.get("cover_image")  # → UploadFile

# Always clean up when done
await form.cleanup()`}</CodeBlock>

        <div className={`${boxClass} mt-6`}>
          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <strong>Note:</strong> For URL-encoded forms (<code className="text-aquilia-500">request.form()</code>), the
            <code className="text-aquilia-500"> files</code> dict is always empty. Only <code className="text-aquilia-500">request.multipart()</code> populates files.
            The Request object automatically calls <code className="text-aquilia-500">cleanup()</code> in its own <code className="text-aquilia-500">cleanup()</code> method.
          </p>
        </div>
      </section>

      {/* ================================================================ */}
      {/* UploadStore Protocol */}
      {/* ================================================================ */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <HardDrive className="w-6 h-6 text-aquilia-500" />
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>UploadStore Protocol</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A <code className="text-aquilia-500">Protocol</code> class defining the interface for pluggable upload storage backends.
          Implement this to store uploads in S3, GCS, Azure Blob, or any custom backend.
        </p>
        <CodeBlock language="python" filename="upload_store_protocol.py">{`from aquilia._uploads import UploadStore
from typing import Protocol, Dict, Any, Optional
from pathlib import Path


class UploadStore(Protocol):
    """Protocol for upload storage backends."""

    async def write_chunk(self, upload_id: str, chunk: bytes) -> None:
        """Write a chunk of data for an in-progress upload.
        
        Called multiple times as file data streams in.
        Must handle creating/appending to the upload storage.
        """
        ...

    async def finalize(
        self, upload_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Finalize an upload and return the final storage path.
        
        Called once after all chunks have been written.
        metadata includes: filename, content_type, size.
        Should move data from temp to permanent storage.
        """
        ...

    async def abort(self, upload_id: str) -> None:
        """Abort an in-progress upload and clean up resources.
        
        Called on error during upload.
        Should remove any partially written data.
        """
        ...`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Backend Example</h3>
        <CodeBlock language="python" filename="s3_store.py">{`import boto3
from io import BytesIO


class S3UploadStore:
    """Upload store for AWS S3."""

    def __init__(self, bucket: str, prefix: str = "uploads/"):
        self.bucket = bucket
        self.prefix = prefix
        self.s3 = boto3.client("s3")
        self._buffers: dict[str, BytesIO] = {}

    async def write_chunk(self, upload_id: str, chunk: bytes) -> None:
        if upload_id not in self._buffers:
            self._buffers[upload_id] = BytesIO()
        self._buffers[upload_id].write(chunk)

    async def finalize(self, upload_id: str, metadata=None) -> Path:
        buf = self._buffers.pop(upload_id)
        buf.seek(0)

        filename = metadata.get("filename", f"{upload_id}.bin")
        key = f"{self.prefix}{upload_id}/{filename}"

        self.s3.upload_fileobj(
            buf, self.bucket, key,
            ExtraArgs={"ContentType": metadata.get("content_type", "application/octet-stream")},
        )
        return Path(f"s3://{self.bucket}/{key}")

    async def abort(self, upload_id: str) -> None:
        self._buffers.pop(upload_id, None)`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* LocalUploadStore */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>LocalUploadStore</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The built-in <code className="text-aquilia-500">UploadStore</code> implementation for local filesystem storage.
          Writes chunks to temporary files, then atomically moves to the final location on finalize.
        </p>

        <h3 className={`text-lg font-semibold mt-6 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Constructor</h3>
        <CodeBlock language="python" filename="local_store_init.py">{`from aquilia._uploads import LocalUploadStore

store = LocalUploadStore(
    upload_dir="/data/uploads",         # Final storage directory (default: ./uploads)
    use_hash_prefix=True,               # Prefix files with SHA-256 hash (default: True)
    temp_dir="/tmp/aquilia_uploads",     # Temp directory for in-progress uploads
)
# Both directories are created automatically (mkdir -p)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Behavior</h3>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Behavior</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { m: 'write_chunk(id, chunk)', d: 'Appends chunk to temp file at temp_dir/{id}.part. Creates file on first call. Uses aiofiles if available.' },
                { m: 'finalize(id, metadata)', d: 'Gets filename from metadata (or uses {id}.bin). Optionally prepends SHA-256 hash prefix. Atomically renames temp file to upload_dir/{hash}_{filename}.' },
                { m: 'abort(id)', d: 'Deletes the temp .part file and removes tracking entry.' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Filename Sanitization</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Both <code className="text-aquilia-500">LocalUploadStore</code> and Request's multipart parser sanitize filenames:
        </p>
        <ul className={`list-disc pl-6 space-y-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <li>Removes path components via <code className="text-aquilia-500">os.path.basename()</code> — prevents directory traversal</li>
          <li>Strips null bytes (<code className="text-aquilia-500">\x00</code>)</li>
          <li>Replaces dangerous characters: <code className="text-aquilia-500">&lt; &gt; : " / \ | ? *</code> → <code className="text-aquilia-500">_</code></li>
          <li>Limits filename length to 200 characters (store) or 255 characters (parser)</li>
          <li>Falls back to <code className="text-aquilia-500">"unnamed"</code> if filename is empty</li>
        </ul>
      </section>

      {/* ================================================================ */}
      {/* Request Integration */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Request Integration</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The Request class provides two convenience methods for working with uploads:
        </p>
        <CodeBlock language="python" filename="request_upload_helpers.py">{`# Save a single upload to disk
path = await request.save_upload(
    upload,                # UploadFile instance
    "/uploads/avatars/",   # Destination path
    overwrite=False,       # Raise if file exists
)
# Delegates to upload.save()

# Stream to custom storage backend
from myapp.storage import S3UploadStore

store = S3UploadStore(bucket="my-uploads")
final_path = await request.stream_upload_to_store(upload, store)
# Internally:
# 1. Generates UUID as upload_id
# 2. Iterates upload.stream() → store.write_chunk(id, chunk)
# 3. Calls store.finalize(id, {filename, content_type, size})
# 4. On error: calls store.abort(id) and re-raises`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Factory Functions */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Factory Functions</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Two utility functions for creating UploadFile instances (used internally by the multipart parser):
        </p>
        <CodeBlock language="python" filename="factory_functions.py">{`from aquilia._uploads import create_upload_file_from_bytes, create_upload_file_from_path

# Create in-memory UploadFile
upload = create_upload_file_from_bytes(
    filename="test.txt",
    content=b"Hello, World!",
    content_type="text/plain",
)
# → UploadFile(filename="test.txt", size=13, _content=b"Hello, World!")

# Create disk-backed UploadFile
upload = create_upload_file_from_path(
    filename="large_video.mp4",
    file_path=Path("/tmp/aquilia_uploads/abc123_large_video.mp4"),
    content_type="video/mp4",
)
# → UploadFile(filename="large_video.mp4", size=<from stat>, _file_path=<Path>)`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Disk Spilling */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Disk Spilling Strategy</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The multipart parser automatically manages memory by spilling large files to disk:
        </p>
        <CodeBlock language="python" filename="disk_spilling.py">{`# Configuration (on Request)
Request(scope, receive,
    form_memory_threshold=1024 * 1024,  # 1 MB threshold (default)
    max_file_size=50 * 1024 * 1024,     # 50 MB max per file
    upload_tempdir=Path("/tmp/uploads"), # Custom temp directory
)

# During multipart parsing, for each file part:
# 1. Data starts accumulating in a bytearray (in-memory)
# 2. When cumulative size exceeds form_memory_threshold:
#    a. Creates temp file: {tempdir}/{uuid}_{filename}
#    b. Flushes buffered data to disk
#    c. Subsequent chunks written directly to disk file
# 3. On part end:
#    - In-memory: creates UploadFile with _content=bytes(data)
#    - On-disk:   creates UploadFile with _file_path=temp_path
# 4. Temp files tracked in request._temp_files for cleanup`}</CodeBlock>

        <div className={`${boxClass} mt-6`}>
          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <strong>aiofiles support:</strong> When <code className="text-aquilia-500">aiofiles</code> is installed, disk I/O
            operations (read, write, stream) use truly async file I/O. Without it, sync I/O is used with
            <code className="text-aquilia-500"> loop.run_in_executor()</code> as a fallback. Install with: <code className="text-aquilia-500">pip install aiofiles</code>.
          </p>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Complete Example */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Complete Example</h2>
        <CodeBlock language="python" filename="upload_controller.py">{`from aquilia import Controller, Post, Get
from aquilia.response import Response
from aquilia._uploads import LocalUploadStore
from pathlib import Path


# Configure upload store
upload_store = LocalUploadStore(
    upload_dir="/data/uploads/documents",
    use_hash_prefix=True,
)


class DocumentController(Controller):
    prefix = "/api/documents"

    @Post("/upload")
    async def upload_document(self, ctx):
        """Handle single file upload with validation."""
        form = await ctx.request.multipart()

        doc = form.get_file("document")
        if not doc:
            return Response.json({"error": "No document"}, status=400)

        # Validate file type
        allowed = {"application/pdf", "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        if doc.content_type not in allowed:
            return Response.json({"error": "Invalid file type"}, status=415)

        # Stream to storage backend
        final_path = await ctx.request.stream_upload_to_store(doc, upload_store)

        return Response.json({
            "filename": doc.filename,
            "size": doc.size,
            "path": str(final_path),
        }, status=201)

    @Post("/bulk-upload")
    async def bulk_upload(self, ctx):
        """Handle multiple file uploads."""
        form = await ctx.request.multipart()

        # Get metadata fields
        project = form.get_field("project")
        description = form.get_field("description")

        # Get all uploaded files
        files = form.get_all_files("documents")
        if not files:
            return Response.json({"error": "No files"}, status=400)

        results = []
        for f in files:
            path = await f.save(
                Path(f"/data/uploads/{project}/{f.filename}"),
                overwrite=True,
            )
            results.append({
                "filename": f.filename,
                "size": f.size,
                "path": str(path),
            })

        # Clean up temp files
        await form.cleanup()

        return Response.json({
            "project": project,
            "description": description,
            "files": results,
            "count": len(results),
        }, status=201)`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-gray-200 dark:border-white/10">
        <Link to="/docs/request-response/data-structures" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span>Data Structures</span>
        </Link>
        <Link to="/docs/di" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition-colors">
          <span>Dependency Injection</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    
      <NextSteps />
    </div>
  )
}