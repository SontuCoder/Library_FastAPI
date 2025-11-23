from fastapi import Request, HTTPException

async def get_db(request: Request):
    db = request.app.state.db
    if db is None:
        raise HTTPException(500, "Database not initialized")
    return db
