from fastapi import APIRouter, HTTPException, Depends
import traceback
from bson import ObjectId
from datetime import datetime


from authentication.auth_function import get_current_user
from db_connection.db_provider import get_db
from models.books_model import request_Book

router = APIRouter()

async def student_check(user =  Depends(get_current_user)) -> bool:
    return user.get("role") == "student"

@router.post("/book-request")
async def book_request(
    data: request_Book,
    is_student=Depends(student_check),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_student:
        raise HTTPException(status_code=403, detail="Only students can request books")

    email = user.get("email")

    try:
        if not email or not data.book_id:
            raise HTTPException(status_code=400, detail="Details missing")

        book_id = ObjectId(data.book_id)

        # Check for existing active request
        existing_request = await db.issued_books.find_one({
            "email": email,
            "book_id": book_id,
            "status": {"$in": ["requested", "issued"]}
        })

        if existing_request:
            raise HTTPException(
                status_code=400,
                detail="Book already requested or issued"
            )

        await db.issued_books.insert_one({
            "email": email,
            "book_id": book_id,
            "issue_date": None,
            "return_date": None,
            "request_date": datetime.utcnow(),
            "status": "requested"
        })

        return {
            "status": "success",
            "message": "Book requested successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/my-requests")
async def my_requests(
    is_student=Depends(student_check),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_student:
        raise HTTPException(status_code=403, detail="Only students can view their requests")

    email = user.get("email")

    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email missing")

        requests_list = await db.issued_books.find({"email": email, "status": {"$in": ["requested", "rejected"]}}).to_list(length=None)
        # Enrich requests with book details
        for request in requests_list:
            book = await db.books.find_one({"_id": request["book_id"]})
            if book:
                request["book_name"] = book.get("title")
                request["author"] = book.get("author")
                request["edition"] = book.get("edition")
        
        requests = []
        for request in requests_list:
            request["_id"] = str(request["_id"])
            request["book_id"] = str(request["book_id"])
            requests.append(request)

        return {
            "status": "success",
            "data": requests
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@router.get("/issued-books")
async def issued_books(
    is_student=Depends(student_check),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_student:
        raise HTTPException(status_code=403, detail="Only students can view their issued books")

    email = user.get("email")

    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email missing")

        issued_list = await db.issued_books.find({"email": email, "status":"approved"}).to_list(length=None)
        # Enrich issued records with book details
        for record in issued_list:
            book = await db.books.find_one({"_id": record["book_id"]})
            if book:
                record["book_name"] = book.get("title")
                record["author"] = book.get("author")
                record["edition"] = book.get("edition")
        
        issued_books = []
        for record in issued_list:
            record["_id"] = str(record["_id"])
            record["book_id"] = str(record["book_id"])
            issued_books.append(record)

        return {
            "status": "success",
            "data": issued_books
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


