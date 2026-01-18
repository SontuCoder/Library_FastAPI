from fastapi import APIRouter, Depends, HTTPException
import traceback
from bson import ObjectId
from datetime import datetime, timedelta, timezone


from authentication.auth_function import get_current_user
from db_connection.db_provider import get_db
from models.books_model import Books, Delete_book, approve_Reject_Book_Request, Change_Book_Class

router = APIRouter()

async def admin_check(user =  Depends(get_current_user)) -> bool:
    return user['role'] == 'admin' if user['role'] else False


@router.get("/list-student")
async def list_student(is_admin =Depends(admin_check), db = Depends(get_db)):
    if not is_admin:
        raise HTTPException(status_code=401, detail="Access deny")
    result = []
    try:
        issued = await db.issued_books.find({}).to_list(None)

        if not issued:
            return {"total_students": len(result), "students": [], "message":"Successfull"}
    
        emails = list({record["email"] for record in issued})
    
        students = await db.users.find({"email": {"$in": emails}, "role":"student"}).to_list(None)
    
        for student in students:
            student_issues = [
                item for item in issued if item["email"] == student["email"]
            ]
            result.append({
                "name": student.get("name"),
                "email": student.get("email"),
                "issued_books": student_issues
            })

        return {"total_students": len(result),"students": result, "message":"Successfull"}

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")
    
@router.post("/add-book")
async def add_book(book_data: Books,is_admin = Depends(admin_check), db = Depends(get_db)):
    if not is_admin:
        raise HTTPException(status_code=401, detail="Access deny")
    try:
        if not book_data.title or not book_data.author or not book_data.description or book_data.edition == None or book_data.quantity == None:
            raise HTTPException(status_code=400, detail="Details missing")
        existing_book = await db.books.find_one({"title":book_data.title, "author": book_data.author, "edition":book_data.edition})
        if existing_book:
            new_quantity = existing_book["quantity"] + book_data.quantity
            new_available = existing_book["available"] + book_data.quantity

            await db.books.update_one(
                {"_id": existing_book["_id"]},
                {"$set": {"quantity": new_quantity, "available": new_available}}
            )

            return {
                "status": "success",
                "message": "Book already exists, quantity updated",
                "book_id": str(existing_book["_id"]),
                "book_qty": new_quantity,
                "book_avi": new_available
            }
        
        new_book_dict = book_data.model_dump()
        new_book_dict["available"] = book_data.quantity  # set available initially

        new_book_dict["added_at"] = new_book_dict["added_at"].isoformat()

        new_book_dict["category"] = [cat.value for cat in new_book_dict["category"]]

        result = await db.books.insert_one(new_book_dict)

        new_book_dict["_id"] = str(result.inserted_id)

        return {
            "status": "success",
            "message": "Book added successfully",
            "book": new_book_dict
        }
    
    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")
    
@router.delete("/delete-book")
async def delete_book(book_data: Delete_book, is_admin = Depends(admin_check), db = Depends(get_db)):
    if not is_admin:
        raise HTTPException(status_code=401, detail="Access deny")
    try:
        if not book_data.id or book_data.quantity == None:
            raise HTTPException(status_code=400, detail="Details missing")
        existing_book = await db.books.find_one({"_id": ObjectId(book_data.id)})
        if not existing_book:
            raise HTTPException(status_code=400, detail="Book doesn't found.")
        if(existing_book["quantity"] < book_data.quantity or existing_book["available"] < book_data.quantity):
            raise HTTPException(status_code=400, detail="Book number is not valid")
        
        new_quantity = existing_book["quantity"] - book_data.quantity
        new_available = existing_book["available"] - book_data.quantity

        if new_quantity == 0:
            await db.books.delete_one({"_id": existing_book["_id"]})
            return {
                "status": "success",
                "message": "Book completely removed from library"
            }

        await db.books.update_one(
                {"_id": existing_book["_id"]},
                {"$set": {"quantity": new_quantity, "available": new_available}}
            )
        
        return {
            "status": "success",
            "message": "Book delete successfully, quantity updated",
            "book_id": str(existing_book["_id"]),
            "book_qty": new_quantity,
            "book_avi": new_available
        }
    
    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")
    


async def fetch_books_data(db):
    try:
        total_books = await db.books.count_documents({})

        now = datetime.utcnow()
        # 🔹 Start of current month (1 Jan 00:00:00)
        start_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 🔹 Start of last month (1 Dec 00:00:00)
        start_last_month = (start_current_month - timedelta(days=1)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        
        # ✅ Current Month: 1/1 → today
        current_month_books = await db["books"].count_documents({
            "added_at": {
                "$gte": start_current_month,
                "$lt": now
            }
        })
        
        # ✅ Last Month: 1/12 → 31/12
        last_month_books = await db.books.count_documents({
            "added_at": {
                "$gte": start_last_month,
                "$lt": start_current_month
            }
        })

        percentage_change = 0
        if last_month_books == 0:
            percentage_change = current_month_books
        else:
            percentage_change = round(
                ((current_month_books - last_month_books) / last_month_books) * 100,
                2
            )
        
        total_issued_books = await db.issued_books.count_documents({})
        overdue_issued_books = await db.issued_books.count_documents({
            "return_date": {"$lt": now}
        })

        return {
            "total_books": total_books,
            "books_percentage_change": percentage_change,
            "total_issued_books": total_issued_books,
            "overdue_issued_books": overdue_issued_books
        }

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")

async def fetch_students_data(db):
    try:
        total_students = await db.users.count_documents({"role":"student"})
        return total_students

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")

async def fetch_popular_books(db, limit: int = 5):
    try:
        pipeline = [
            {
                "$group": {
                    "_id": "$book_id",
                    "issued_count": {"$sum": 1}
                }
            },
            {
                "$sort": {"issued_count": -1}
            },
            {
                "$limit": limit
            },
            {
                "$lookup": {
                    "from": "books",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "book"
                }
            },
            {
                "$unwind": "$book"
            },
            {
                "$project": {
                    "_id": 0,
                    "name": "$book.title",
                    "author": "$book.author",
                    "edition": "$book.edition",
                    "issued_count": 1
                }
            }
        ]

        return await db.issued_books.aggregate(pipeline).to_list(length=limit)

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to fetch popular books")

@router.get("/admin-dashboard")
async def admin_dashboard(is_admin = Depends(admin_check), db = Depends(get_db)):
    if not is_admin:
        raise HTTPException(status_code=401, detail="Access deny")
    try:
        books_details = await fetch_books_data(db)
        student_details = await fetch_students_data(db)
        popular_books = await fetch_popular_books(db)

        return {
            "status": "success",
            "total_books": books_details["total_books"],
            "total_students": student_details,
            "popular_books": popular_books,
            "total_issued_books": books_details["total_issued_books"],
            "overdue_issued_books": books_details["overdue_issued_books"],
            "books_percentage_change": books_details["books_percentage_change"],
            "message": "Dashboard data fetched successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")
    

@router.get("/list-books-requested")
async def list_books_requested(is_admin = Depends(admin_check), db = Depends(get_db)):
    if not is_admin:
        raise HTTPException(status_code=401, detail="Access deny")
    
    result = []
    try:
        issued_books = await db.issued_books.find({"status":"requested"}).to_list(None)

        if not issued_books:
            return {"total_requests": len(result), "requests": [], "message":"Successfull"}
    
        book_ids = list({record["book_id"] for record in issued_books})
    
        books = await db.books.find({"_id": {"$in": book_ids}}).to_list(None)
    
        book_dict = {book["_id"]: book for book in books}
    
        for issued in issued_books:
            book_info = book_dict.get(issued["book_id"])
            if book_info:
                result.append({
                    "id": str(issued.get("_id")),
                    "student_email": issued.get("email"),
                    "book_title": book_info.get("title"),
                    "book_author": book_info.get("author"),
                    "issue_date": issued.get("issue_date"),
                    "return_date": issued.get("return_date"),
                    "request_date": issued.get("request_date"),
                    "status": issued.get("status")
                })

        return {"total_requests": len(result),"requests": result, "message":"Successfull"}

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")
    

@router.post("/approve-book-request")
async def approve_book_request(data: approve_Reject_Book_Request, is_admin = Depends(admin_check), db = Depends(get_db)):
    if not is_admin:
        raise HTTPException(status_code=401, detail="Access deny")
    try:
        issued_request = await db.issued_books.find_one({"_id": ObjectId(data.request_id)})

        if not issued_request:
            raise HTTPException(status_code=400, detail="Request not found")

        if issued_request["status"] != "requested":
            raise HTTPException(status_code=400, detail="Request is not in a valid state for approval")

        book = await db.books.find_one({"_id": issued_request["book_id"]})

        if not book or book["available"] <= 0:
            raise HTTPException(status_code=400, detail="Book not available for issuing")

        issue_date = datetime.utcnow()
        return_date = issue_date + timedelta(days=3)

        await db.issued_books.update_one(
            {"_id": issued_request["_id"]},
            {
                "$set": {
                    "status": data.action,
                    "issue_date": issue_date,
                    "return_date": return_date
                }
            }
        )

        await db.books.update_one(
            {"_id": book["_id"]},
            {"$inc": {"available": -1}}
        )

        return {
            "status": "success",
            "message": "Book request approved successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@router.get("/issued-books")
async def issued_books(is_admin = Depends(admin_check), db = Depends(get_db)):
    if not is_admin:
        raise HTTPException(status_code=401, detail="Access deny")
    
    result = []
    try:
        issued_books = await db.issued_books.find({"status":"approved"}).to_list(None)

        if not issued_books:
            return {"total_issued_books": len(result), "issued_books": [], "message":"Successfull"}
    
        book_ids = list({record["book_id"] for record in issued_books})
    
        books = await db.books.find({"_id": {"$in": book_ids}}).to_list(None)
    
        book_dict = {book["_id"]: book for book in books}
    
        for issued in issued_books:
            book_info = book_dict.get(issued["book_id"])
            if book_info:
                result.append({
                    "id": str(issued.get("_id")),
                    "student_email": issued.get("email"),
                    "book_title": book_info.get("title"),
                    "book_author": book_info.get("author"),
                    "issue_date": issued.get("issue_date"),
                    "return_date": issued.get("return_date"),
                    "status": issued.get("status")
                })

        return {"total_issued_books": len(result),"issued_books": result, "message":"Successfull"}

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")


@router.post("/book-details-edit")
async def book_details_edit(book_data: Change_Book_Class, is_admin = Depends(admin_check), db = Depends(get_db)):
    if not is_admin:
        raise HTTPException(status_code=403, detail="Access deny")
    try:
        if not book_data.id:
            raise HTTPException(status_code=400, detail="Book ID is required")
        
        existing_book = await db.books.find_one({"_id": ObjectId(book_data.id)})
        if not existing_book:
            raise HTTPException(status_code=400, detail="Book doesn't found.")
        
        update_data = {k: v for k, v in book_data.model_dump().items() if v is not None and k != "id"}

        if "category" in update_data:
            update_data["category"] = [cat.value for cat in update_data["category"]]

        await db.books.update_one(
            {"_id": existing_book["_id"]},
            {"$set": update_data}
        )

        return {
            "status": "success",
            "message": "Book details updated successfully"
        }
    
    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")

@router.get("/list-books-renew-requested")
async def list_books_renew_requested( is_admin = Depends(admin_check), db = Depends(get_db)):
    try:
        if not is_admin:
            raise HTTPException(status_code=403, detail="Access deny")
        result = []
        issued_books = await db.issued_books.find({"status":"renew_requested"}).to_list(None)
        if not issued_books:
            return {"total_requests": len(result), "requests": [], "message":"Successfull"} 
        book_ids = list({record["book_id"] for record in issued_books})
        books = await db.books.find({"_id": {"$in": book_ids}}).to_list(None)
        book_dict = {book["_id"]: book for book in books}
        for issued in issued_books:
            book_info = book_dict.get(issued["book_id"])
            if book_info:
                result.append({
                    "id": str(issued.get("_id")),
                    "student_email": issued.get("email"),
                    "book_title": book_info.get("title"),
                    "book_author": book_info.get("author"),
                    "issue_date": issued.get("issue_date"),
                    "return_date": issued.get("return_date"),
                    "request_date": issued.get("renew_request_date"),
                    "status": issued.get("status")
                })

        return {"request_details": result, "message":"Successfull"}
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error")

@router.post("/approve-book-renew-request")
async def approve_book_renew_request(data:approve_Reject_Book_Request, is_admin = Depends(admin_check), db = Depends(get_db)):
    try:
        if not is_admin:
            raise HTTPException(status_code=403, detail="Access deny")
        
        if not ObjectId.is_valid(data.request_id):
            raise HTTPException(status_code=400, detail="Invalid request ID")

        issued_request = await db.issued_books.find_one({"_id": ObjectId(data.request_id), "status": "renew_requested"})

        if not issued_request:
            raise HTTPException(status_code=400, detail="Request not found")
        
        if data.action != "renewed" and data.action != "renew_rejected":
            raise HTTPException(status_code=400, detail="Action must be either 'renewed' or 'renew_rejected'")
        
        if data.action == "renew_rejected":
            await db.issued_books.update_one(
                {"_id": issued_request["_id"]},
                {
                    "$set": {
                        "status": "renew_rejected",
                    }
                }
            )
            return {
                "status": "success",
                "message": "Book renew request rejected successfully"
            }
        
        new_return_date = issued_request["return_date"] + timedelta(days=3)

        await db.issued_books.update_one(
            {"_id": issued_request["_id"]},
            {
                "$set": {
                    "status": "renewed",
                    "return_date": new_return_date
                }
            }
        )

        return {
            "status": "success",
            "message": "Book renew request approved successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/list-books-return-requested")
async def list_books_return_requested(is_admin = Depends(admin_check), db = Depends(get_db)):
    try:
        if not is_admin:
            raise HTTPException(status_code=403, detail="Access Deny")
        
        result =[]
        return_reqs = await db.issued_books.find({"status":"return_requested"}).to_list(None)

        if not return_reqs:
            return {"total_requests": len(result), "requests": [], "message":"Successfull"}
        book_ids = list({record["book_id"] for record in return_reqs})
        books = await db.books.find({"_id": {"$in": book_ids}}).to_list(None)
        book_dict = {book["_id"]: book for book in books}
        for req in return_reqs:
            book_info = book_dict.get(req["book_id"])
            if book_info:
                result.append({
                    "id": str(req.get("_id")),
                    "student_email": req.get("email"),
                    "book_title": book_info.get("title"),
                    "book_author": book_info.get("author"),
                    "issue_date": req.get("issue_date"),
                    "return_date": req.get("return_date"),
                    "request_date": req.get("return_request_date"),
                    "status": req.get("status")
                })  

        return { "status": "success", "result": result, "message": "Return requests fetch successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@router.post("/approve-book-return-request/{request_id}")
async def approve_book_return_request(
    request_id:str,
    is_admin = Depends(admin_check),
    db = Depends(get_db)
):
    try:
        if not is_admin:
            raise HTTPException(status_code=403, detail="Access Deny")
        
        if not ObjectId.is_valid(request_id):
            raise HTTPException(status_code=400, detail="Invalid request ID")

        issued_request = await db.issued_books.find_one({"_id": ObjectId(request_id), "status": "return_requested"})

        if not issued_request:
            raise HTTPException(status_code=400, detail="Request not found")
        book = await db.books.find_one( {"_id": ObjectId(issued_request["book_id"])})

        await db.books.update_one(
            {"_id": issued_request["book_id"]},
            {"$inc": {"available_copies": 1}}
        )
        
        await db.issued_books.update_one(
            {"_id": issued_request["_id"]},
            {
                "$set": {
                    "status": "returned",
                    "return_date": datetime.now(timezone.utc),
                    "previous_status":None
                }
            }
        )
        

        return { "status": "success", "message": "Return requests approve successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/student-details/{stu_id}")
async def student_details(
    stu_id: str,
    _=Depends(admin_check),
    db=Depends(get_db)
):
    try:
        if not ObjectId.is_valid(stu_id):
            raise HTTPException(status_code=400, detail="Invalid student ID")

        student = await db.users.find_one({"_id": ObjectId(stu_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        pipeline = [
            {
                "$match": {"email": student["email"]}
            },
            {
            "$addFields": {
                "book_id": { "$toObjectId": "$book_id" }
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
            {
                "$project": {
                    "_id": 0,
                    "status": 1,
                    "issue_date": 1,
                    "return_date": 1,
                    "book_name": "$book.title",
                    "author": "$book.author",
                    "edition": "$book.edition",
                    "category": "$book.category"
                }
            }
        ]

        issued_books = await db.issued_books.aggregate(pipeline).to_list(length=None)

        return {
            "status": "success",
            "data": {
                "stu_email": student["email"],
                "stu_name": student.get("name"),
                "provider": student.get("provider"),
                "books": issued_books
            },
            "message": "Student details fetched successfully"
        }

    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get-all-admins")
async def get_all_admins(
    is_admin = Depends(admin_check),
    db = Depends(get_db)
):
    try:
        if not is_admin:
            raise HTTPException(status_code=403, detail="Access Deny")
        
        admins = await db.users.find({"role":"admin"}).to_list(None)

        result = []
        for admin in admins:
            result.append({
                "id": str(admin["_id"]),
                "name": admin.get("name"),
                "email": admin.get("email"),
                "provider": admin.get("provider"),
                "created_at": admin.get("created_at")
            })

        return {
            "status": "success",
            "admins": result,
            "message": "Admins fetched successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

async def admin_profile(email: str, db):
    try:
        admin = await db.users.find_one({"email": email, "role":"admin"})
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")

        return {
            "status": "success",
            "data": {
                "name": admin.get("name"),
                "email": admin.get("email"),
                "provider": admin.get("provider"),
                "created_at": admin.get("created_at")
            },
            "message": "Admin profile fetched successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

async def admin_profile_update(email: str, data, db):
    try:
        admin = await db.users.find_one({"email": email, "role":"admin"})
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}

        if update_data:
            await db.users.update_one(
                {"_id": admin["_id"]},
                {"$set": update_data}
            )

        return {
            "status": "success",
            "message": "Admin profile updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
