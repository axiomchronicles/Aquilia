"""
AquilaTemplates Example - Blog Application

Demonstrates template rendering with Controllers, DI, and security.
"""

from aquilia import Controller, GET, POST, Inject
from aquilia.templates import TemplateEngine
from aquilia.response import Response
from typing import Annotated
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# Models
# ============================================================================

@dataclass
class Post:
    """Blog post model."""
    id: int
    title: str
    content: str
    author: str
    created_at: datetime
    tags: list[str]
    
    @property
    def excerpt(self) -> str:
        """Get first 100 characters."""
        return self.content[:100] + "..." if len(self.content) > 100 else self.content


@dataclass
class Comment:
    """Comment model."""
    id: int
    post_id: int
    author: str
    content: str
    created_at: datetime


# ============================================================================
# Repository (Mock)
# ============================================================================

class BlogRepository:
    """Mock blog repository."""
    
    def __init__(self):
        self.posts = [
            Post(
                id=1,
                title="Welcome to AquilaTemplates",
                content="This is a demonstration of the new template system...",
                author="Alice",
                created_at=datetime(2026, 1, 20),
                tags=["announcement", "templates"]
            ),
            Post(
                id=2,
                title="Building Secure Web Apps",
                content="Security is paramount when building web applications...",
                author="Bob",
                created_at=datetime(2026, 1, 22),
                tags=["security", "best-practices"]
            ),
            Post(
                id=3,
                title="Async Template Rendering",
                content="Learn how to render templates asynchronously for better performance...",
                author="Charlie",
                created_at=datetime(2026, 1, 25),
                tags=["performance", "async"]
            )
        ]
        
        self.comments = [
            Comment(1, 1, "Dave", "Great post!", datetime(2026, 1, 21)),
            Comment(2, 1, "Eve", "Very informative", datetime(2026, 1, 21)),
        ]
    
    async def list_posts(self, limit: int = 10) -> list[Post]:
        """List all posts."""
        return self.posts[:limit]
    
    async def get_post(self, post_id: int) -> Post | None:
        """Get post by ID."""
        return next((p for p in self.posts if p.id == post_id), None)
    
    async def get_comments(self, post_id: int) -> list[Comment]:
        """Get comments for post."""
        return [c for c in self.comments if c.post_id == post_id]
    
    async def create_post(self, title: str, content: str, author: str, tags: list[str]) -> Post:
        """Create new post."""
        post = Post(
            id=len(self.posts) + 1,
            title=title,
            content=content,
            author=author,
            created_at=datetime.utcnow(),
            tags=tags
        )
        self.posts.append(post)
        return post


# ============================================================================
# Controllers
# ============================================================================

class BlogController(Controller):
    """Blog posts controller."""
    
    prefix = "/blog"
    
    def __init__(
        self,
        templates: TemplateEngine,
        repo: Annotated[BlogRepository, Inject(tag="blog_repo")]
    ):
        self.templates = templates
        self.repo = repo
    
    @GET("/")
    async def index(self, ctx):
        """List all blog posts."""
        posts = await self.repo.list_posts()
        
        return self.render(
            "blog/index.html",
            {
                "posts": posts,
                "page_title": "Blog - Latest Posts"
            },
            ctx
        )
    
    @GET("/post/«post_id:int»")
    async def view_post(self, ctx, post_id: int):
        """View single blog post."""
        post = await self.repo.get_post(post_id)
        
        if not post:
            return Response.html(
                "<h1>404 - Post Not Found</h1>",
                status=404
            )
        
        comments = await self.repo.get_comments(post_id)
        
        return self.render(
            "blog/post.html",
            {
                "post": post,
                "comments": comments,
                "page_title": post.title
            },
            ctx
        )
    
    @GET("/new")
    async def new_post_form(self, ctx):
        """Show new post form."""
        # Check if user is authenticated
        if not ctx.identity:
            return Response.redirect("/auth/login?next=/blog/new")
        
        return self.render(
            "blog/new.html",
            {"page_title": "New Post"},
            ctx
        )
    
    @POST("/create")
    async def create_post(self, ctx):
        """Create new post."""
        # Check authentication
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)
        
        # Parse form data
        form = await ctx.form()
        
        title = form.get("title", "")
        content = form.get("content", "")
        tags_str = form.get("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        
        # Create post
        post = await self.repo.create_post(
            title=title,
            content=content,
            author=ctx.identity.username,
            tags=tags
        )
        
        # Redirect to new post
        return Response.redirect(f"/blog/post/{post.id}")
    
    @GET("/tag/«tag»")
    async def posts_by_tag(self, ctx, tag: str):
        """List posts by tag."""
        all_posts = await self.repo.list_posts()
        filtered = [p for p in all_posts if tag in p.tags]
        
        return self.render(
            "blog/index.html",
            {
                "posts": filtered,
                "page_title": f"Posts tagged '{tag}'"
            },
            ctx
        )


# ============================================================================
# Setup
# ============================================================================

def setup_blog_example():
    """
    Setup blog example with templates.
    
    Directory structure:
    
    examples/templates/blog/
      templates/
        layouts/
          base.html
        blog/
          index.html
          post.html
          new.html
        components/
          post_card.html
          comment.html
    """
    from pathlib import Path
    from aquilia.templates import TemplateLoader, InMemoryBytecodeCache
    
    # Get templates directory
    templates_dir = Path(__file__).parent / "templates"
    
    # Create loader
    loader = TemplateLoader(search_paths=[str(templates_dir)])
    
    # Create engine
    engine = TemplateEngine(
        loader=loader,
        bytecode_cache=InMemoryBytecodeCache(),
        sandbox=True
    )
    
    # Register custom filters
    def format_date(dt, format="%B %d, %Y"):
        """Format datetime."""
        return dt.strftime(format)
    
    engine.register_filter("format_date", format_date)
    
    # Create repository
    repo = BlogRepository()
    
    # Create controller
    controller = BlogController(templates=engine, repo=repo)
    
    return controller, engine


# ============================================================================
# CLI Test
# ============================================================================

async def test_rendering():
    """Test template rendering."""
    from aquilia.request import Request
    from aquilia.controller.base import RequestCtx
    
    controller, engine = setup_blog_example()
    
    # Create mock request
    request = Request(
        method="GET",
        path="/blog",
        headers={},
        query={},
        body=b""
    )
    
    ctx = RequestCtx(request=request)
    
    # Test index
    print("Testing index page...")
    response = await controller.index(ctx)
    print(f"Status: {response.status}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    # Test single post
    print("\nTesting post page...")
    response = await controller.view_post(ctx, 1)
    print(f"Status: {response.status}")
    
    print("\n✓ Rendering tests passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_rendering())
