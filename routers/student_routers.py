from fastapi import APIRouter, HTTPException, Depends
import traceback
from bson import ObjectId
from datetime import datetime
from models.books_model import BookCategori



from authentication.auth_function import get_current_user
from db_connection.db_provider import get_db
from models.books_model import request_Book
from routers.admin_routers import fetch_popular_books, fetch_students_data, fetch_books_data


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
            "status": {"$in": ["requested", "approved", "renewed", "return_requested", "renew_requested"]}
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

        requests_list = await db.issued_books.find({"email": email, "status": {"$in": ["requested", "rejected", "return_requested", "renew_requested"]}}).to_list(length=None)
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

        issued_list = await db.issued_books.find({"email": email, "status": { "$in":["approved", "renewed", "renew_requested"]}}).to_list(length=None)
        # Enrich issued records with book details
        for record in issued_list:
            book = await db.books.find_one({"_id": record["book_id"]})
            if book:
                record["category"] = book.get("category")
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


@router.post("/delete-issued-request/{request_id}")
async def delete_issued_request(request_id: str,
    is_student=Depends(student_check),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_student:
        raise HTTPException(status_code=403, detail="Only students can delete their requests")

    email = user.get("email")

    try:
        if not email or not request_id:
            raise HTTPException(status_code=400, detail="Details missing")
        
        if not ObjectId.is_valid(request_id):
            raise HTTPException(status_code=400, detail="Invalid request ID")

        request_obj_id = ObjectId(request_id)

        result = await db.issued_books.delete_one({
            "_id": request_obj_id,
            "email": email,
            "status": "requested"
        })

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Request not found or cannot be deleted")

        return {
            "status": "success",
            "message": "Request deleted successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/return-book/{issued_id}")
async def return_book(issued_id: str,
    is_student=Depends(student_check),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_student:
        raise HTTPException(status_code=403, detail="Only students can return books")

    email = user.get("email")

    try:
        if not email or not issued_id:
            raise HTTPException(status_code=400, detail="Details missing")
        
        if not ObjectId.is_valid(issued_id):
            raise HTTPException(status_code=400, detail="Invalid issued ID")

        issued_obj_id = ObjectId(issued_id)

        prev_res = await db.issued_books.find_one({
            "_id": issued_obj_id,
            "email": email,
            "status": {"$in":["approved", "renewed"]},
        })

        if not prev_res:
            raise HTTPException(status_code=404, detail="Issued record not found or cannot be returned")

        result = await db.issued_books.find_one_and_update({
            "_id": issued_obj_id,
            "email": email,
            "status": {"$in":["approved", "renewed"]},
        }, {
            "$set": {
                "status": "return_requested",
                "previous_status": prev_res["status"]
            }
        })


        return {
            "status": "success",
            "message": "Book return initiated successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/list-return-request")
async def list_return_request(
    is_student=Depends(student_check),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_student:
        raise HTTPException(
            status_code=403,
            detail="Only students can view their return requests"
        )

    email = user.get("email")

    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email missing")

        return_list = await db.issued_books.find(
            {"email": email, "status": "return_requested"}
        ).to_list(length=None)

        result = []
        for record in return_list:   
            book = await db.books.find_one({"_id": record["book_id"]})

            if book:
                record["book_name"] = book.get("title")
                record["author"] = book.get("author")
                record["edition"] = book.get("edition")

            record["_id"] = str(record["_id"])
            record["book_id"] = str(record["book_id"])

            result.append(record)

        return {
            "status": "success",
            "data": result,
            "message": "Return requests fetched successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/delete-return-request/{issued_id}")
async def delete_return_request(issued_id: str,
    is_student=Depends(student_check),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_student:
        raise HTTPException(
            status_code=403,
            detail="Only students can delete their return requests"
        )

    email = user.get("email")

    try:
        if not email or not issued_id:
            raise HTTPException(status_code=400, detail="Details missing")
        
        if not ObjectId.is_valid(issued_id):
            raise HTTPException(status_code=400, detail="Invalid issued ID")

        issued_obj_id = ObjectId(issued_id)

        prev_res = await db.issued_books.find_one({
            "_id": issued_obj_id,
            "email": email,
            "status": "return_requested",
        })

        if not prev_res:
            raise HTTPException(
                status_code=404,
                detail="Return request not found or cannot be deleted"
            )

        await db.issued_books.find_one_and_update({
            "_id": issued_obj_id,
            "email": email,
            "status": "return_requested"
        },{
            "$set": {
                "status": prev_res["previous_status"],
                "previous_status" : None
            }
        })


        return {
            "status": "success",
            "message": "Return request deleted successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/book-renew-request/{issued_id}")
async def book_renew_request(issued_id: str,
    is_student=Depends(student_check),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_student:
        raise HTTPException(
            status_code=403,
            detail="Only students can request book renewals"
        )

    email = user.get("email")

    try:
        if not email or not issued_id:
            raise HTTPException(status_code=400, detail="Details missing")
        
        if not ObjectId.is_valid(issued_id):
            raise HTTPException(status_code=400, detail="Invalid issued ID")

        issued_obj_id = ObjectId(issued_id)

        prev_res = await db.issued_books.find_one({
            "_id": issued_obj_id,
            "email": email,
            "status": {"$in" :["approved", "renewed" ]},
        })

        if not prev_res:
            raise HTTPException(
                status_code=404,
                detail="Issued record not found or cannot be renewed"
            )

        await db.issued_books.find_one_and_update({
            "_id": issued_obj_id,
            "email": email,
            "status": { "$in" :["approved", "renewed"]},
        },{
            "$set": {
                "status": "renew_requested",
                "previous_status": prev_res["status"]
            }
        })

        return {
            "status": "success",
            "message": "Book renewal requested successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/delete-renew-request/{issued_id}")
async def delete_renew_request(issued_id: str, 
    is_student=Depends(student_check),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_student:
        raise HTTPException(
            status_code=403,
            detail="Only students can delete their renewal requests"
        )

    email = user.get("email")

    try:
        if not email or not issued_id:
            raise HTTPException(status_code=400, detail="Details missing")
        
        if not ObjectId.is_valid(issued_id):
            raise HTTPException(status_code=400, detail="Invalid issued ID")

        issued_obj_id = ObjectId(issued_id)

        prev_res = await db.issued_books.find_one({
            "_id": issued_obj_id,
            "email": email,
            "status": "renew_requested",
        })

        if not prev_res:
            raise HTTPException(
                status_code=404,
                detail="Renewal request not found or cannot be deleted"
            )

        await db.issued_books.find_one_and_update({
            "_id": issued_obj_id,
            "email": email,
            "status": "renew_requested"
        },{
            "$set": {
                "status": prev_res["previous_status"],
                "previous_status" : None
            }
        })

        return {
            "status": "success",
            "message": "Renewal request deleted successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/dashboard")
async def student_dashboard(
    is_student=Depends(student_check),
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    if not is_student:
        raise HTTPException(status_code=403, detail="Only students can access the dashboard")

    email = user.get("email")

    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email missing")
        
        books_details = await fetch_books_data(db)
        student_details = await fetch_students_data(db)
        popular_books = await fetch_popular_books(db)

        return {
            "status": "success",
            "data": {
                "total_books": books_details["total_books"],
                "total_students": student_details,
                "popular_books": popular_books,
                "total_issued_books": books_details["total_issued_books"],
                "books_percentage_change": books_details["books_percentage_change"],
            },
            "message": "Dashboard data fetched successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def student_profile(
    email: str,
    db
):
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email missing")
        
        user = await db.users.find_one({"email": email})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        total_issued_books = await db.issued_books.count_documents({
            "email": email,
            "status": { "$in" :["approved", "renewed"]},
        })

        overdue_issued_books = await db.issued_books.count_documents({
            "email": email,
            "return_date": {"$lt": datetime.utcnow()},
            "status": { "$in" :["approved", "renewed"]},
        })

        old_books_used = await db.issued_books.count_documents({
            "email": email,
            "status": "returned"
        })

        pipeline = [
            {
                "$match": {
                    "email": email,
                    "status": {"$in":["returned", "renewed", "approved"]}
                }
            },
            {
                "$lookup": {
                    "from": "books",
                    "localField": "book_id",
                    "foreignField": "_id",
                    "as": "book"
                }
            },
            {"$unwind": "$book"},
            {"$unwind": "$book.category"},
            {
                "$group": {
                    "_id": "$book.category",
                    "count": {"$sum": 1}
                }
            }
        ]

        interest_stats = {}
        async for row in db.issued_books.aggregate(pipeline):
            interest_stats[row["_id"]] = row["count"]

        for cat in BookCategori:
            interest_stats.setdefault(cat.value, 0)
        return {
            "status": "success",
            "data": {
                "total_issued_books": total_issued_books,
                "overdue_issued_books": overdue_issued_books,
                "old_books_used": old_books_used,
                "name": user.get("name"),
                "email": user.get("email"),
                "role": user.get("role"),
                "interest_stats": interest_stats
            },
            "message": "Student data fetched successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    





