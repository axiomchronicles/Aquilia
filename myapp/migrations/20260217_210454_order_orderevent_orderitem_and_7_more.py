"""
Migration: 20260217_210454_order_orderevent_orderitem_and_7_more
Generated: 2026-02-17T21:04:54.735840+00:00
Models: Order, OrderEvent, OrderItem, Category, Product, ProductReview, ProductVariant, User, UserAddress, UserSession
"""

# Revision identifiers
revision = "20260217_210454"
slug = "order_orderevent_orderitem_and_7_more"


async def upgrade(conn):
    """Apply migration — create tables."""
    await conn.execute("""CREATE TABLE IF NOT EXISTS "orders" (
  "order_number" VARCHAR(36) UNIQUE NOT NULL,
  "user_id" INTEGER NOT NULL,
  "status" VARCHAR(20) NOT NULL DEFAULT 'pending',
  "payment_status" VARCHAR(25) NOT NULL DEFAULT 'pending',
  "subtotal" DECIMAL(12,2) NOT NULL DEFAULT 0,
  "tax_amount" DECIMAL(12,2) NOT NULL DEFAULT 0,
  "shipping_amount" DECIMAL(12,2) NOT NULL DEFAULT 0,
  "discount_amount" DECIMAL(12,2) NOT NULL DEFAULT 0,
  "total" DECIMAL(12,2) NOT NULL DEFAULT 0,
  "currency" VARCHAR(3) NOT NULL DEFAULT 'USD',
  "shipping_address" TEXT NOT NULL,
  "billing_address" TEXT NOT NULL,
  "notes" TEXT,
  "metadata" TEXT NOT NULL,
  "payment_method" VARCHAR(50),
  "payment_reference" VARCHAR(255),
  "shipped_at" TIMESTAMP,
  "delivered_at" TIMESTAMP,
  "cancelled_at" TIMESTAMP,
  "created_at" TIMESTAMP NOT NULL,
  "updated_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_orders_order_number" ON "orders" ("order_number");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_orders_user_-created_at" ON "orders" ("user", "-created_at");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_orders_status_-created_at" ON "orders" ("status", "-created_at");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_orders_payment_status" ON "orders" ("payment_status");""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "order_events" (
  "order_id" INTEGER NOT NULL REFERENCES "orders"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  "event_type" VARCHAR(50) NOT NULL,
  "from_status" VARCHAR(20),
  "to_status" VARCHAR(20),
  "actor_id" VARCHAR(255),
  "actor_type" VARCHAR(20) NOT NULL DEFAULT 'system',
  "details" TEXT NOT NULL,
  "created_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_order_events_order_-created_at" ON "order_events" ("order", "-created_at");""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "order_items" (
  "order_id" INTEGER NOT NULL REFERENCES "orders"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  "product_id" INTEGER NOT NULL,
  "variant_sku" VARCHAR(50),
  "product_name" VARCHAR(255) NOT NULL,
  "quantity" INTEGER NOT NULL DEFAULT 1,
  "unit_price" DECIMAL(10,2) NOT NULL,
  "total_price" DECIMAL(12,2) NOT NULL,
  "discount_amount" DECIMAL(10,2) NOT NULL DEFAULT 0,
  "metadata" TEXT NOT NULL,
  "created_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_order_items_order" ON "order_items" ("order");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_order_items_product" ON "order_items" ("product");""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "categories" (
  "name" VARCHAR(100) NOT NULL,
  "slug" VARCHAR(120) UNIQUE NOT NULL,
  "description" TEXT,
  "parent_id" INTEGER REFERENCES "categories"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  "image_url" VARCHAR(500),
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "is_active" INTEGER NOT NULL DEFAULT 1,
  "metadata" TEXT NOT NULL,
  "created_at" TIMESTAMP NOT NULL,
  "updated_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_categories_slug" ON "categories" ("slug");""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "products" (
  "name" VARCHAR(255) NOT NULL,
  "slug" VARCHAR(280) UNIQUE NOT NULL,
  "sku" VARCHAR(50) UNIQUE NOT NULL,
  "description" TEXT,
  "short_description" VARCHAR(500),
  "price" DECIMAL(10,2) NOT NULL,
  "compare_at_price" DECIMAL(10,2),
  "cost_price" DECIMAL(10,2),
  "currency" VARCHAR(3) NOT NULL DEFAULT 'USD',
  "category_id" INTEGER REFERENCES "categories"("id") ON DELETE SET NULL ON UPDATE CASCADE,
  "vendor_id" INTEGER NOT NULL,
  "status" VARCHAR(20) NOT NULL DEFAULT 'draft',
  "stock_quantity" INTEGER NOT NULL DEFAULT 0,
  "low_stock_threshold" INTEGER NOT NULL DEFAULT 10,
  "weight_grams" INTEGER,
  "tags" TEXT NOT NULL,
  "images" TEXT NOT NULL,
  "attributes" TEXT NOT NULL,
  "is_featured" INTEGER NOT NULL DEFAULT 0,
  "is_digital" INTEGER NOT NULL DEFAULT 0,
  "rating_avg" REAL NOT NULL DEFAULT 0.0,
  "rating_count" INTEGER NOT NULL DEFAULT 0,
  "view_count" INTEGER NOT NULL DEFAULT 0,
  "purchase_count" INTEGER NOT NULL DEFAULT 0,
  "created_at" TIMESTAMP NOT NULL,
  "updated_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_products_slug" ON "products" ("slug");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_products_sku" ON "products" ("sku");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_products_category_status" ON "products" ("category", "status");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_products_vendor_status" ON "products" ("vendor", "status");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_products_status_-created_at" ON "products" ("status", "-created_at");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_products_-rating_avg" ON "products" ("-rating_avg");""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "product_reviews" (
  "product_id" INTEGER NOT NULL REFERENCES "products"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  "user_id" INTEGER NOT NULL,
  "rating" INTEGER NOT NULL,
  "title" VARCHAR(200),
  "body" TEXT,
  "is_verified_purchase" INTEGER NOT NULL DEFAULT 0,
  "is_approved" INTEGER NOT NULL DEFAULT 0,
  "helpful_count" INTEGER NOT NULL DEFAULT 0,
  "created_at" TIMESTAMP NOT NULL,
  "updated_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_product_reviews_product_-rating" ON "product_reviews" ("product", "-rating");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_product_reviews_user_product" ON "product_reviews" ("user", "product");""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "product_variants" (
  "product_id" INTEGER NOT NULL REFERENCES "products"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  "sku" VARCHAR(50) UNIQUE NOT NULL,
  "name" VARCHAR(100) NOT NULL,
  "price_modifier" DECIMAL(10,2) NOT NULL DEFAULT 0,
  "stock_quantity" INTEGER NOT NULL DEFAULT 0,
  "attributes" TEXT NOT NULL,
  "is_active" INTEGER NOT NULL DEFAULT 1,
  "created_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "users" (
  "uuid" VARCHAR(36) UNIQUE NOT NULL,
  "email" VARCHAR(255) UNIQUE NOT NULL,
  "username" VARCHAR(150) UNIQUE NOT NULL,
  "password_hash" VARCHAR(255) NOT NULL,
  "first_name" VARCHAR(100) NOT NULL DEFAULT '',
  "last_name" VARCHAR(100) NOT NULL DEFAULT '',
  "role" VARCHAR(20) NOT NULL DEFAULT 'customer',
  "is_active" INTEGER NOT NULL DEFAULT 1,
  "is_verified" INTEGER NOT NULL DEFAULT 0,
  "avatar_url" VARCHAR(500),
  "bio" TEXT,
  "phone" VARCHAR(20),
  "preferences" TEXT NOT NULL,
  "last_login_at" TIMESTAMP,
  "login_count" INTEGER NOT NULL DEFAULT 0,
  "created_at" TIMESTAMP NOT NULL,
  "updated_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_users_email" ON "users" ("email");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_users_username" ON "users" ("username");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_users_role_is_active" ON "users" ("role", "is_active");""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "user_addresses" (
  "user_id" INTEGER NOT NULL REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  "label" VARCHAR(50) NOT NULL DEFAULT 'home',
  "street_address" VARCHAR(255) NOT NULL,
  "city" VARCHAR(100) NOT NULL,
  "state" VARCHAR(100) NOT NULL,
  "postal_code" VARCHAR(20) NOT NULL,
  "country" VARCHAR(2) NOT NULL DEFAULT 'US',
  "is_default" INTEGER NOT NULL DEFAULT 0,
  "created_at" TIMESTAMP NOT NULL,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE TABLE IF NOT EXISTS "user_sessions" (
  "user_id" INTEGER NOT NULL REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  "session_id" VARCHAR(255) UNIQUE NOT NULL,
  "ip_address" VARCHAR(45) NOT NULL,
  "user_agent" VARCHAR(500),
  "device_fingerprint" VARCHAR(255),
  "is_active" INTEGER NOT NULL DEFAULT 1,
  "created_at" TIMESTAMP NOT NULL,
  "last_activity" TIMESTAMP NOT NULL,
  "expires_at" TIMESTAMP,
  "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_user_sessions_session_id" ON "user_sessions" ("session_id");""")
    await conn.execute("""CREATE INDEX IF NOT EXISTS "idx_user_sessions_user_is_active" ON "user_sessions" ("user", "is_active");""")


async def downgrade(conn):
    """Revert migration — drop tables."""
    await conn.execute('DROP TABLE IF EXISTS "orders"')
    await conn.execute('DROP TABLE IF EXISTS "order_events"')
    await conn.execute('DROP TABLE IF EXISTS "order_items"')
    await conn.execute('DROP TABLE IF EXISTS "categories"')
    await conn.execute('DROP TABLE IF EXISTS "products"')
    await conn.execute('DROP TABLE IF EXISTS "product_reviews"')
    await conn.execute('DROP TABLE IF EXISTS "product_variants"')
    await conn.execute('DROP TABLE IF EXISTS "users"')
    await conn.execute('DROP TABLE IF EXISTS "user_addresses"')
    await conn.execute('DROP TABLE IF EXISTS "user_sessions"')
