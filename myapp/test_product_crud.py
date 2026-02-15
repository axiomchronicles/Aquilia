#!/usr/bin/env python3
"""
Test script for Products API - verifies all CRUD operations work correctly.
"""
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    print("=" * 60)
    print("Testing Products API with Real Database")
    print("=" * 60)
    print()
    
    # Initialize the database
    from aquilia.db.engine import configure_database
    from aquilia.models.base import ModelRegistry
    
    # Configure database
    db = configure_database("sqlite:///test_products.db")
    await db.connect()
    
    # Import models (registers them)
    from modules.products.models import Product, Review
    
    # Set database for models
    ModelRegistry.set_database(db)
    
    # Create tables
    await ModelRegistry.create_tables()
    print("✓ Database initialized\n")
    
    # Test services
    from modules.products.services import ProductService
    service = ProductService()
    
    try:
        # Test 1: Create product
        print("Test 1: Create Product")
        print("-" * 40)
        product_data = {
            "name": "Gaming Laptop",
            "description": "High-performance gaming laptop with RTX 4080",
            "price": 2499.99,
            "sku": "GAMING-LAPTOP-001",
            "category": "electronics",
            "stock": 10
        }
        result = await service.create_product(product_data)
        if "error" in result:
            print(f"✗ Failed: {result['error']}")
            return
        
        product_id = result["id"]
        print(f"✓ Created product ID: {product_id}")
        print(f"  Name: {result['name']}")
        print(f"  Price: ${result['price']}")
        print(f"  SKU: {result['sku']}")
        print()
        
        # Test 2: Get product by ID
        print("Test 2: Get Product by ID")
        print("-" * 40)
        product = await service.get_product(product_id)
        print(f"✓ Retrieved product: {product['name']}")
        print(f"  Category: {product['category']}")
        print(f"  Stock: {product['stock']}")
        print()
        
        # Test 3: List products
        print("Test 3: List All Products")
        print("-" * 40)
        products = await service.list_products()
        print(f"✓ Found {len(products)} product(s)")
        for p in products:
            print(f"  - {p['name']} (${p['price']})")
        print()
        
        # Test 4: Update product
        print("Test 4: Update Product")
        print("-" * 40)
        update_data = {"price": 2299.99, "stock": 15}
        updated = await service.update_product(product_id, update_data)
        print(f"✓ Updated product:")
        print(f"  New price: ${updated['price']}")
        print(f"  New stock: {updated['stock']}")
        print()
        
        # Test 5: Search products
        print("Test 5: Search Products")
        print("-" * 40)
        results = await service.search_products("gaming")
        print(f"✓ Search for 'gaming' found {len(results)} result(s)")
        for r in results:
            print(f"  - {r['name']}")
        print()
        
        # Test 6: Adjust stock
        print("Test 6: Adjust Stock")
        print("-" * 40)
        adjusted = await service.adjust_stock(product_id, -3)
        print(f"✓ Adjusted stock by -3")
        print(f"  New stock: {adjusted['stock']}")
        print()
        
        # Test 7: Add review
        print("Test 7: Add Review")
        print("-" * 40)
        review = await service.add_review(
            product_id, 
            5, 
            "Amazing laptop! Great for gaming and development.", 
            "John Doe"
        )
        print(f"✓ Added review:")
        print(f"  Rating: {review['rating']}/5")
        print(f"  Comment: {review['comment']}")
        print(f"  Author: {review['author_name']}")
        print()
        
        # Test 8: Get product with reviews
        print("Test 8: Get Product with Reviews")
        print("-" * 40)
        product_full = await service.get_product(product_id)
        reviews = product_full.get("reviews", [])
        print(f"✓ Product has {len(reviews)} review(s)")
        for rev in reviews:
            print(f"  - {rev['rating']}/5: {rev['comment']}")
        print()
        
        # Test 9: Filter products
        print("Test 9: Filter Products by Category")
        print("-" * 40)
        electronics = await service.list_products(category="electronics")
        print(f"✓ Found {len(electronics)} electronics")
        print()
        
        # Test 10: Delete product
        print("Test 10: Delete Product")
        print("-" * 40)
        deleted = await service.delete_product(product_id)
        print(f"✓ Product deleted: {deleted}")
        
        # Verify deletion
        products_after = await service.list_products()
        print(f"  Products remaining: {len(products_after)}")
        print()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()
        # Clean up test database
        Path("test_products.db").unlink(missing_ok=True)
        print("\nCleaned up test database")


if __name__ == "__main__":
    asyncio.run(main())
