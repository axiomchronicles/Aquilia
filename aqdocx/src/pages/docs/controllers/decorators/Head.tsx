import { useTheme } from '../../../../context/ThemeContext'
import { CodeBlock } from '../../../../components/CodeBlock'
import { Zap, ArrowLeft, ArrowRight, Eye } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NextSteps } from '../../../../components/NextSteps'

export function DecoratorHead() {
    const { theme } = useTheme()
    const isDark = theme === 'dark'

    return (
        <div className="max-w-4xl mx-auto">
            <div className="mb-8">
                <Link to="/docs/controllers/decorators" className={`flex items-center gap-2 text-sm mb-4 ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>
                    <ArrowLeft className="w-4 h-4" /> Back to Decorators
                </Link>
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-lg bg-pink-500/10 text-pink-500">
                        <Zap className="w-6 h-6" />
                    </div>
                    <h1 className={`text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        @HEAD
                    </h1>
                </div>
                <p className={`text-xl ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    The <code>@HEAD</code> decorator handles HTTP HEAD requests, which are identical to GET requests except that the <strong>server must not return a message body</strong>.
                    It is useful for efficient checks on resource existence, size, or modification time.
                </p>
            </div>

            {/* Usage */}
            <section className="mb-12">
                <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Basic Usage</h2>
                <CodeBlock
                    code={`from aquilia import Controller, HEAD, GET, RequestCtx, Response

class FileController(Controller):
    
    @GET("/files/«filename»")
    async def download(self, ctx: RequestCtx, filename: str):
        file = await self.storage.get(filename)
        return Response.file(file)

    @HEAD("/files/«filename»")
    async def check_file(self, ctx: RequestCtx, filename: str):
        """Check file metadata without downloading."""
        meta = await self.storage.get_metadata(filename)
        if not meta:
            return Response.status(404)
        
        return Response(
            status=200,
            headers={
                "Content-Length": str(meta.size),
                "Last-Modified": meta.last_modified.isoformat(),
                "Content-Type": meta.content_type
            }
        )`}
                    language="python"
                />
            </section>

            {/* Deep Dive: Performance */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-4">
                    <Eye className="w-5 h-5 text-aquilia-500" />
                    <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Why use HEAD?</h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className={`p-4 rounded border ${isDark ? 'bg-zinc-800/50 border-white/10' : 'bg-white border-gray-200'}`}>
                        <h3 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Etag & Caching</h3>
                        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            Clients can check if their cached version is still valid using <code>If-None-Match</code> headers against the Etag returned by HEAD.
                        </p>
                    </div>
                    <div className={`p-4 rounded border ${isDark ? 'bg-zinc-800/50 border-white/10' : 'bg-white border-gray-200'}`}>
                        <h3 className={`font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Large Resources</h3>
                        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                            Determine the download size (Content-Length) of a large file before committing to download it.
                        </p>
                    </div>
                </div>
            </section>

            {/* Navigation */}
            <div className="flex justify-between mt-8">
                <Link to="/docs/controllers/decorators/delete" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    <ArrowLeft className="w-4 h-4" /> Previous: @DELETE
                </Link>
                <Link to="/docs/controllers/decorators/options" className={`flex items-center gap-2 text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
                    Next: @OPTIONS <ArrowRight className="w-4 h-4" />
                </Link>
            </div>
        
      <NextSteps />
    </div>
    )
}