# 📚 Library Management System – Backend API

A high-performance backend built using **FastAPI** for managing a complete Library Management System.
This API handles authentication, book management, user management, and borrowing operations.

---

## 🚀 Tech Stack

* ⚡ FastAPI
* 🐍 Python
* 🗄️ PostgreSQL / MySQL
* 🔄 SQLAlchemy
* 📦 Pydantic
* 🔐 JWT Authentication
* 🚀 Uvicorn

---

## 📌 Features

### 👤 Authentication & Authorization

* User Registration
* Secure Login (JWT Token)
* Role-based Access (Admin / Student)
* Protected Routes

### 📖 Book Management

* Add new books
* Update book details
* Delete books
* Search books
* Check availability

### 🔄 Borrow & Return System

* Issue books
* Return books
* Due date tracking
* Status management

---

## 📂 Project Structure

```
library-fastapi/
│
├── app/
│   ├── main.py
│   ├── models/        # Database models
│   ├── schemas/       # Request & response schemas
│   ├── routes/        # API endpoints
│   ├── services/      # Business logic
│   ├── database/      # DB configuration
│   └── core/          # Security & settings
│
├── requirements.txt
├── .env
└── README.md
```

---

## 🗄️ Database Tables

### Users

* id
* name
* email
* password
* role

### Books

* id
* title
* author
* category
* quantity
* available_count

### Borrow

* id
* user_id
* book_id
* issue_date
* return_date
* status

---

## ▶️ Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/library-fastapi.git
cd library-fastapi
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Configure Environment Variables

Create a `.env` file:

```
DATABASE_URL=postgresql://username:password@localhost/library
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 5️⃣ Run the Server

```bash
uvicorn app.main:app --reload
```

Server runs at:

```
http://127.0.0.1:8000
```

---

## 📖 API Documentation

FastAPI provides automatic interactive documentation:

* Swagger UI → `http://127.0.0.1:8000/docs`
* ReDoc → `http://127.0.0.1:8000/redoc`

---

## 🧪 Testing Tools

You can test APIs using:

* Swagger UI
* Postman
* Insomnia

---

## 🚀 Deployment Options

* Render
* Railway
* AWS
* DigitalOcean

---

## 🔮 Future Improvements

* Email notifications
* Book reservation system
* Fine calculation automation
* Admin dashboard
* Docker support
* CI/CD integration

---

## 👨‍💻 Author

**Subhadip Maity**
Backend Developer | Associate Software Developer
