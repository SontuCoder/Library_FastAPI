from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("DB_URI")
MONGO_DB = os.getenv("DB_Name")

db = None
client = None

async def connect_to_mongo(app):
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        # Test connection by running a ping command
        await client.admin.command("ping")
        
        app.state.mongo_client = client
        app.state.db = client[MONGO_DB]

        print("MongoDB Connection: Success")
    except Exception as e:
        print("MongoDB Connection: Failed ❌")
        print("Error:", str(e))
