import asyncio
import os
import sys

# Add current directory to path
sys.path.insert(0, os.getcwd())

from aquilia.db.engine import AquiliaDatabase
from aquilia.models import ModelRegistry
from modules.auth.models import User

async def debug_db():
    print(f"Current working directory: {os.getcwd()}")
    db_path = "authentication/db.sqlite"
    if not os.path.exists(db_path):
        print(f"CRITICAL: {db_path} does NOT exist!")
        return

    db = AquiliaDatabase(f"sqlite:///{db_path}")
    await db.connect()
    ModelRegistry.set_database(db)
    
    print("\nListing all users in DB:")
    try:
        users = await User.all()
        if not users:
            print("No users found.")
        for user in users:
            print(f"ID: {user.id} | Email: {user.email} | Hash: {user.password_hash[:40]}...")
    except Exception as e:
        print(f"Error querying users: {e}")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_db())
