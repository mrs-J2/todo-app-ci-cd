from fastapi import FastAPI, Depends, HTTPException, status, Query, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
import models
import schemas
import auth
import os
from database import engine, get_db
from datetime import datetime
import io
from s3_utils import upload_file_to_s3, delete_file_from_s3

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Todo API", version="1.0.0")
security = HTTPBearer()

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)


# Dependency to get current user from token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = auth.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "JWT token is invalid or expired"
                }
            }
        )
    
    user = db.query(models.User).filter(models.User.id == payload.get("user_id")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "User not found"
                }
            }
        )
    return user


@app.get("/")
async def root():
    return {"message": "Todo API is running"}


# Authentication Endpoints
@app.post("/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if username exists
    existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "USERNAME_EXISTS",
                    "message": "Username already taken"
                }
            }
        )
    
    # Create new user
    hashed_password = auth.get_password_hash(user_data.password)
    new_user = models.User(username=user_data.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate token
    token = auth.create_access_token({"user_id": new_user.id})
    
    return schemas.UserResponse(
        id=str(new_user.id),
        username=new_user.username,
        token=token
    )


@app.post("/auth/login", response_model=schemas.UserResponse)
async def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    # Find user
    user = db.query(models.User).filter(models.User.username == user_data.username).first()
    
    if not user or not auth.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Username or password is incorrect"
                }
            }
        )
    
    # Generate token
    token = auth.create_access_token({"user_id": user.id})
    
    return schemas.UserResponse(
        id=str(user.id),
        username=user.username,
        token=token
    )


# Todo Endpoints
@app.get("/todos", response_model=schemas.TodoListResponse)
async def get_todos(
    status_filter: Optional[str] = Query(None, alias="status"),
    sort: Optional[str] = Query("createdAt"),
    order: Optional[str] = Query("desc"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Todo).filter(models.Todo.user_id == current_user.id)
    
    # Filter by status
    if status_filter == "completed":
        query = query.filter(models.Todo.completed == True)
    elif status_filter == "pending":
        query = query.filter(models.Todo.completed == False)
    
    # Sort
    if sort == "createdAt":
        if order == "asc":
            query = query.order_by(models.Todo.created_at.asc())
        else:
            query = query.order_by(models.Todo.created_at.desc())
    
    todos = query.all()
    
    return schemas.TodoListResponse(
        todos=[schemas.TodoResponse.from_orm(todo) for todo in todos],
        total=len(todos)
    )


@app.get("/todos/{todo_id}", response_model=schemas.TodoResponse)
async def get_todo(
    todo_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TODO_NOT_FOUND",
                    "message": "Requested todo does not exist"
                }
            }
        )
    
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "UNAUTHORIZED_ACCESS",
                    "message": "User doesn't have permission"
                }
            }
        )
    
    return schemas.TodoResponse.from_orm(todo)


@app.post("/todos", response_model=schemas.TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(
    title: str,
    description: Optional[str] = None,
    image: UploadFile = File(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create the todo first
    new_todo = models.Todo(
        title=title,
        description=description,
        user_id=current_user.id
    )
    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)
    
    # If an image was provided, upload it to S3
    if image is not None:
        # Validate file size (limit to 5MB)
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes
        image_bytes = await image.read()
        if len(image_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_PAYLOAD_TOO_LARGE,
                detail={
                    "error": {
                        "code": "FILE_TOO_LARGE",
                        "message": "File exceeds maximum size of 5MB"
                    }
                }
            )
        
        # Reset file pointer to beginning after reading
        await image.seek(0)
        
        # Upload to S3
        file_url, file_key = upload_file_to_s3(
            image.file, image.filename, current_user.id, "todos"
        )
        
        # Update the todo with image information
        new_todo.image_url = file_url
        new_todo.image_key = file_key
        db.commit()
        db.refresh(new_todo)
    
    return schemas.TodoResponse.from_orm(new_todo)


@app.put("/todos/{todo_id}", response_model=schemas.TodoResponse)
async def update_todo(
    todo_id: str,
    todo_data: schemas.TodoUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TODO_NOT_FOUND",
                    "message": "Requested todo does not exist"
                }
            }
        )
    
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "UNAUTHORIZED_ACCESS",
                    "message": "User doesn't have permission"
                }
            }
        )
    
    # Update fields
    if todo_data.title is not None:
        todo.title = todo_data.title
    if todo_data.description is not None:
        todo.description = todo_data.description
    if todo_data.completed is not None:
        todo.completed = todo_data.completed
    
    todo.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(todo)
    
    return schemas.TodoResponse.from_orm(todo)


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TODO_NOT_FOUND",
                    "message": "Requested todo does not exist"
                }
            }
        )
    
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "UNAUTHORIZED_ACCESS",
                    "message": "User doesn't have permission"
                }
            }
        )
    
    # If the todo has an associated image, delete it from S3
    if todo.image_key:
        delete_file_from_s3(os.getenv("S3_BUCKET_NAME"), todo.image_key)
    
    db.delete(todo)
    db.commit()
    
    return None


@app.post("/todos/{todo_id}/image", response_model=schemas.TodoResponse)
async def upload_todo_image(
    todo_id: str,
    image: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TODO_NOT_FOUND",
                    "message": "Requested todo does not exist"
                }
            }
        )
    
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "UNAUTHORIZED_ACCESS",
                    "message": "User doesn't have permission"
                }
            }
        )
    
    # Check if todo already has an image - if so, don't allow re-uploading
    if todo.image_key is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "IMAGE_ALREADY_EXISTS",
                    "message": "Todo item already has an image. Cannot update media again."
                }
            }
        )
    
    # Validate file size (limit to 5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes
    image_bytes = await image.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_PAYLOAD_TOO_LARGE,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": "File exceeds maximum size of 5MB"
                }
            }
        )
    
    # Reset file pointer to beginning after reading
    await image.seek(0)
    
    # Upload to S3
    file_url, file_key = upload_file_to_s3(
        image.file, image.filename, current_user.id, "todos"
    )
    
    # Update the todo with image information
    todo.image_url = file_url
    todo.image_key = file_key
    todo.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(todo)
    
    return schemas.TodoResponse.from_orm(todo)


@app.delete("/todos/{todo_id}/image", response_model=schemas.TodoResponse)
async def delete_todo_image(
    todo_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TODO_NOT_FOUND",
                    "message": "Requested todo does not exist"
                }
            }
        )
    
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "UNAUTHORIZED_ACCESS",
                    "message": "User doesn't have permission"
                }
            }
        )
    
    # Check if todo has an image
    if not todo.image_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NO_IMAGE_FOUND",
                    "message": "Todo item has no associated image"
                }
            }
        )
    
    # Delete the image from S3
    success = delete_file_from_s3(os.getenv("S3_BUCKET_NAME"), todo.image_key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DELETE_FAILED",
                    "message": "Failed to delete image from storage"
                }
            }
        )
    
    # Update the todo to remove image information
    todo.image_url = None
    todo.image_key = None
    todo.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(todo)
    
    return schemas.TodoResponse.from_orm(todo)