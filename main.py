from fastapi import FastAPI
from authentication.auth_function import router as auth_router
from db_connection.db_config import connect_to_mongo
from db_connection.redis_config import test_redis


app = FastAPI()

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo(app)
    test_redis()

@app.on_event("shutdown")
async def shutdown_event():
    client = app.state.mongo_client
    if client:
        client.close()
        print("🔌 MongoDB Connection Closed")

@app.get("/get")
def home():
    return {"message": "FastAPI is working!"}

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])