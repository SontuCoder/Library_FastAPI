from fastapi import APIRouter, Depends, HTTPException, Query
import traceback
from bson import ObjectId
from typing import Optional, List


from authentication.auth_function import get_current_user
from db_connection.db_provider import get_db

router = APIRouter()

async def valid_user_check(user =  Depends(get_current_user)) -> bool:
    return user.get("role") in ["admin", "student"]

def serialize_book(book: dict) -> dict:
    book["_id"] = str(book["_id"])
    return book

@router.get("/all")
async def get_all_books( 
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
    book_type: Optional[List[str]] = Query(None),
    book_name: Optional[str] = None,
    book_author: Optional[str] = None,
    edition: Optional[int] = None,


    user = Depends(get_current_user), db=Depends(get_db)):
    try:
        if not await valid_user_check(user):
            raise HTTPException(status_code=403, detail="Access forbidden: Invalid user role")
        
        
        query = {}
    
        # 🔹 Cursor pagination
        if cursor:
            if not ObjectId.is_valid(cursor):
                raise HTTPException(status_code=400, detail="Invalid cursor")
            query["_id"] = {"$gt": ObjectId(cursor)}
    
        # 🔹 Filters
        if book_type:
            query["category"] = {"$in": book_type}
            # query["category"] = {"$in": [book_type]}
    
        if book_name:
            query["title"] = {"$regex": book_name, "$options": "i"}
    
        if book_author:
            query["author"] = {"$regex": book_author, "$options": "i"}

        if edition:
            query["edition"] = edition
    
        books_collection = (
            await db["books"]
            .find(query)
            .sort("_id", 1)
            .limit(limit)
            .to_list(limit)
        )

        next_cursor = str(books_collection[-1]["_id"]) if books_collection else None

        # books_collection = db['books']
        # books = await books_collection.find().to_list(1000)   # Fetch up to 1000 books
        books = [serialize_book(book) for book in books_collection]
        if len(books) == 0:
            books = []
        return {
                "status": "success", 
                "filters": {
                    "category": book_type,
                    "edition": edition,
                    "book_name": book_name,
                    "book_author": book_author
                },
                "nextCursor": next_cursor,
                "hasMore": len(books) == limit,
                "total books":len(books), 
                "data": books
            }
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An error occurred while fetching books")
    

@router.get("/details/{book_id}")
async def get_book_details(book_id: str, is_user_valid = Depends(valid_user_check), db=Depends(get_db)):
    try:
        if not is_user_valid:
            raise HTTPException(status_code=403, detail="Access forbidden: Invalid user role")
        
        if not ObjectId.is_valid(book_id):
            raise HTTPException(status_code=400, detail="Invalid book ID")
        
        book = await db["books"].find_one({"_id": ObjectId(book_id)})
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        return {
            "status": "success",
            "data": serialize_book(book)
        }
    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An error occurred while fetching book details")
    

