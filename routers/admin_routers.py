from fastapi import APIRouter, Depends, HTTPException
import traceback
from bson import ObjectId

from authentication.auth_function import get_current_user
from db_connection.db_provider import get_db
from models.books_model import Books, Delete_book

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
    
