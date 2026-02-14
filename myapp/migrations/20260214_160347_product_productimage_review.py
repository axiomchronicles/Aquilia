"""
Migration: 20260214_160347_product_productimage_review
Generated: 2026-02-14T16:03:47.136426+00:00
Models: Product, ProductImage, Review
"""

# Revision identifiers
revision = "20260214_160347"
slug = "product_productimage_review"


async def upgrade(conn):
    """Apply migration — create tables."""
    await conn.execute("""CREATE TABLE IF NOT EXISTS "products" (
  "name" VARCHAR(200) NOT NULL,
  "description" TEXT,
  "price" REAL NOT NULL DEFAULT 0.0,
  "currency" VARCHAR(3) NOT NULL DEFAULT 'USD',
  "sku" VARCHAR(100) UNIQUE NOT NULL,
  "stock" INTEGER NOT NULL DEFAULT 0,
  "category" VARCHAR(100) NOT NULL,
  "is_active" INTEGER NOT NULL DEFAULT 1,
  "created_at" TIMESTAMP NOT NULL,
  "updated_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  UNIQUE ("sku")
);""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_products_category_is_active" ON "products" ("category", "is_active");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_products_price" ON "products" ("price");""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "product_images" (
  "product_id" INTEGER NOT NULL REFERENCES "products"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  "url" VARCHAR(500) NOT NULL,
  "alt_text" VARCHAR(200),
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "created_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "reviews" (
  "product_id" INTEGER NOT NULL REFERENCES "products"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  "rating" INTEGER NOT NULL,
  "comment" TEXT,
  "author_name" VARCHAR(150) NOT NULL,
  "created_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")


async def downgrade(conn):
    """Revert migration — drop tables."""
    await conn.execute('DROP TABLE IF EXISTS "products"')
    await conn.execute('DROP TABLE IF EXISTS "product_images"')
    await conn.execute('DROP TABLE IF EXISTS "reviews"')
