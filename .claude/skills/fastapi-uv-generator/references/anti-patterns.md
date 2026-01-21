# Anti-Patterns to Avoid

## 1. Blocking I/O in Async Routes

### Problem
```python
# BAD: Blocking call in async route
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = db.query(User).get(user_id)  # Blocking!
    return user
```

FastAPI runs async routes on the event loop. Blocking calls freeze the entire application.

### Solution
```python
# GOOD: Use async database driver
@app.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# GOOD: Or use sync route (runs in threadpool)
@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):  # Note: no async
    return db.query(User).get(user_id)
```

---

## 2. Wildcard CORS Origins

### Problem
```python
# BAD: Allows any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # This combination is insecure!
)
```

`allow_origins=["*"]` with credentials is a security vulnerability.

### Solution
```python
# GOOD: Explicit origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com", "https://admin.myapp.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

## 3. Hardcoded Secrets

### Problem
```python
# BAD: Secrets in code
SECRET_KEY = "my-super-secret-key-123"
DATABASE_URL = "postgresql://user:password@localhost/db"
```

Secrets in code end up in version control.

### Solution
```python
# GOOD: Environment variables with pydantic-settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    database_url: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

---

## 4. Missing Input Validation

### Problem
```python
# BAD: No validation
@app.post("/users")
async def create_user(data: dict):
    user = User(**data)  # No validation!
    db.add(user)
```

### Solution
```python
# GOOD: Pydantic validation
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(max_length=100)

@app.post("/users")
async def create_user(data: UserCreate):
    user = User(**data.model_dump())
```

---

## 5. SQLite in Production

### Problem
```python
# BAD: SQLite for production workloads
DATABASE_URL = "sqlite:///./app.db"
```

SQLite lacks concurrent write support, connection pooling, and features needed for production.

### Solution
```python
# GOOD: PostgreSQL or MySQL
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"
```

---

## 6. No Error Handling

### Problem
```python
# BAD: Exceptions leak to client
@app.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    return user.email  # AttributeError if user is None!
```

### Solution
```python
# GOOD: Handle errors explicitly
@app.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

---

## 7. N+1 Query Problem

### Problem
```python
# BAD: N+1 queries
@app.get("/posts")
async def get_posts(db: AsyncSession = Depends(get_db)):
    posts = await db.execute(select(Post))
    result = []
    for post in posts.scalars():
        author = await db.get(User, post.author_id)  # N queries!
        result.append({"post": post, "author": author})
    return result
```

### Solution
```python
# GOOD: Eager loading
from sqlalchemy.orm import selectinload

@app.get("/posts")
async def get_posts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Post).options(selectinload(Post.author))
    )
    return result.scalars().all()  # 1 query
```

---

## 8. Not Using Dependency Injection

### Problem
```python
# BAD: Creating services in routes
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    db = SessionLocal()  # Manual session management
    try:
        service = UserService(db)
        return service.get(user_id)
    finally:
        db.close()
```

### Solution
```python
# GOOD: FastAPI dependency injection
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    return await service.get(user_id)
```

---

## 9. Storing Passwords in Plain Text

### Problem
```python
# BAD: Plain text password
user = User(email=email, password=password)
```

### Solution
```python
# GOOD: Hash passwords
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])

user = User(
    email=email,
    hashed_password=pwd_context.hash(password)
)
```

---

## 10. Not Using Migrations

### Problem
```python
# BAD: Creating tables directly
Base.metadata.create_all(bind=engine)
```

This doesn't track schema changes and can cause data loss.

### Solution
```bash
# GOOD: Use Alembic migrations
alembic revision --autogenerate -m "Add users table"
alembic upgrade head
```

---

## 11. Mixing Business Logic in Routes

### Problem
```python
# BAD: All logic in route
@app.post("/orders")
async def create_order(order_in: OrderCreate, db: AsyncSession = Depends(get_db)):
    # Validation
    user = await db.get(User, order_in.user_id)
    if not user:
        raise HTTPException(404)

    # Calculate totals
    total = sum(item.price * item.quantity for item in order_in.items)

    # Apply discounts
    if user.is_premium:
        total *= 0.9

    # Create order
    order = Order(user_id=user.id, total=total)
    db.add(order)

    # Send notification
    await send_email(user.email, "Order created")

    return order
```

### Solution
```python
# GOOD: Separate concerns
@app.post("/orders")
async def create_order(
    order_in: OrderCreate,
    service: OrderService = Depends(get_order_service)
):
    return await service.create_order(order_in)
```

---

## 12. No Rate Limiting

### Problem
```python
# BAD: No protection against abuse
@app.post("/login")
async def login(credentials: Credentials):
    # Unlimited attempts!
```

### Solution
```python
# GOOD: Rate limiting with slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: Credentials):
    ...
```

---

## 13. Exposing Internal Errors

### Problem
```python
# BAD: Stack traces in production
@app.get("/data")
async def get_data():
    return db.execute("SELECT * FROM secret_table")  # Errors expose internals
```

### Solution
```python
# GOOD: Custom exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

---

## 14. Not Using Async Where Appropriate

### Problem
```python
# BAD: Sync external calls in async route
@app.get("/weather")
async def get_weather(city: str):
    response = requests.get(f"https://api.weather.com/{city}")  # Blocking!
    return response.json()
```

### Solution
```python
# GOOD: Use httpx for async HTTP
import httpx

@app.get("/weather")
async def get_weather(city: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.weather.com/{city}")
        return response.json()
```
