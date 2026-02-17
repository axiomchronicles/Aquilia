import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, Upload } from 'lucide-react'

export function UploadsPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Upload className="w-4 h-4" />
          Request / File Uploads
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          File Uploads
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides <code className="text-aquilia-500">UploadFile</code> and <code className="text-aquilia-500">FormData</code> abstractions for handling multipart file uploads. Files can be streamed, read in-memory, or stored via pluggable backends.
        </p>
      </div>

      {/* UploadFile */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>UploadFile</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Each uploaded file is represented as an <code className="text-aquilia-500">UploadFile</code> dataclass with async read and streaming support.
        </p>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Post


class AvatarController(Controller):
    prefix = "/api/avatars"

    @Post("/upload")
    async def upload_avatar(self, ctx):
        # Access uploaded file from form data
        form = await ctx.request.form()
        avatar = form.files.get("avatar")

        if not avatar:
            return ctx.json({"error": "No file uploaded"}, status=400)

        # File properties
        name = avatar.filename       # → "photo.jpg"
        mime = avatar.content_type   # → "image/jpeg"
        size = avatar.size           # → 204800 (bytes)

        # Read entire file into memory
        content = await avatar.read()

        # Or stream in chunks (64KB default)
        async for chunk in avatar.stream():
            await process_chunk(chunk)

        # Custom chunk size
        async for chunk in avatar.stream(chunk_size=8192):
            ...

        return ctx.json({
            "filename": name,
            "size": size,
            "content_type": mime,
        })`}</CodeBlock>
      </section>

      {/* FormData */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>FormData</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <code className="text-aquilia-500">FormData</code> combines regular form fields (as a <code className="text-aquilia-500">MultiDict</code>) with uploaded files.
        </p>
        <CodeBlock language="python" filename="form_data.py">{`@Post("/profile")
async def update_profile(self, ctx):
    form = await ctx.request.form()

    # Regular form fields (MultiDict)
    username = form.fields.get("username")
    bio = form.fields.get("bio")
    tags = form.fields.get_all("tags")  # multi-value

    # File uploads
    avatar = form.files.get("avatar")
    banner = form.files.get("banner")

    # All files for a field (multi-upload)
    attachments = form.files.get_all("attachments")
    for file in attachments:
        content = await file.read()
        await save_attachment(file.filename, content)`}</CodeBlock>
      </section>

      {/* UploadStore */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>UploadStore</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">UploadStore</code> protocol defines a pluggable storage backend. Aquilia ships with <code className="text-aquilia-500">LocalUploadStore</code>.
        </p>
        <CodeBlock language="python" filename="upload_store.py">{`from aquilia._uploads import LocalUploadStore

# Configure local file storage
store = LocalUploadStore(
    base_dir="/var/uploads",
    max_file_size=10 * 1024 * 1024,  # 10 MB limit
    allowed_types=["image/jpeg", "image/png", "application/pdf"],
)

# Store a file (generates unique filename)
path = await store.save(avatar)
# → "/var/uploads/a1b2c3d4-photo.jpg"

# Retrieve file info
info = await store.get(path)
info.filename     # → "a1b2c3d4-photo.jpg"
info.content_type # → "image/jpeg"
info.size         # → 204800

# Delete a stored file
await store.delete(path)

# Check if file exists
exists = await store.exists(path)  # → False`}</CodeBlock>
      </section>

      {/* Custom Store */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom UploadStore</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Implement the <code className="text-aquilia-500">UploadStore</code> protocol for custom storage backends (S3, GCS, etc.).
        </p>
        <CodeBlock language="python" filename="s3_store.py">{`from aquilia._uploads import UploadStore, UploadFile
from typing import Optional


class S3UploadStore:
    """S3-compatible upload store."""

    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.region = region

    async def save(self, file: UploadFile) -> str:
        content = await file.read()
        key = f"uploads/{uuid4()}-{file.filename}"
        await self._put_object(key, content, file.content_type)
        return key

    async def get(self, path: str) -> Optional[UploadFile]:
        obj = await self._get_object(path)
        if obj:
            return UploadFile(
                filename=path.split("/")[-1],
                content_type=obj["ContentType"],
                size=obj["ContentLength"],
                _content=obj["Body"],
            )
        return None

    async def delete(self, path: str) -> bool:
        return await self._delete_object(path)

    async def exists(self, path: str) -> bool:
        return await self._head_object(path)`}</CodeBlock>
      </section>

      {/* Validation */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Upload Validation</h2>
        <CodeBlock language="python" filename="validation.py">{`@Post("/upload")
async def upload_file(self, ctx):
    form = await ctx.request.form()
    file = form.files.get("document")

    # Validate file type
    allowed = {"application/pdf", "image/jpeg", "image/png"}
    if file.content_type not in allowed:
        return ctx.json(
            {"error": f"Type {file.content_type} not allowed"},
            status=415,
        )

    # Validate file size (5MB max)
    max_size = 5 * 1024 * 1024
    if file.size and file.size > max_size:
        return ctx.json(
            {"error": "File too large (max 5MB)"},
            status=413,
        )

    # Validate file content (read magic bytes)
    header = await file.read(8)
    if not is_valid_magic_bytes(header, file.content_type):
        return ctx.json(
            {"error": "File content does not match declared type"},
            status=422,
        )

    # Hash for deduplication
    import hashlib
    content = await file.read()
    digest = hashlib.sha256(content).hexdigest()

    return ctx.json({"hash": digest, "size": len(content)})`}</CodeBlock>
      </section>

      {/* Nav */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-white/10">
        <Link to="/docs/request-response/data-structures" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          <ArrowLeft className="w-4 h-4" /> Data Structures
        </Link>
        <Link to="/docs/controllers" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          Controllers <ArrowLeft className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
