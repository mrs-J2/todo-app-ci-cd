# Todo App API Documentation

## Authentication

All endpoints except registration and login require authentication via JWT token in the Authorization header.

**Header Format:**
```
Authorization: Bearer <your_jwt_token>
```

---

## Endpoints

### Authentication

#### Register User
Create a new user account.

**Endpoint:** `POST /auth/register`

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:** `201 Created`
```json
{
  "id": "string",
  "username": "string",
  "token": "string"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid input or username already exists
- `422 Unprocessable Entity` - Validation errors

---

#### Login
Authenticate and receive access token.

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "id": "string",
  "username": "string",
  "token": "string"
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
- `400 Bad Request` - Missing required fields

---

### Todos

#### Get All Todos
Retrieve all todos for the authenticated user.

**Endpoint:** `GET /todos`

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `status` (optional): Filter by status (`completed`, `pending`)
- `sort` (optional): Sort order (`createdAt`)
- `order` (optional): `asc` or `desc` (default: `desc`)

**Response:** `200 OK`
```json
{
  "todos": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "completed": false,
      "imageUrl": "string | null",
      "createdAt": "2026-01-26T10:00:00Z"
    }
  ],
  "total": 10
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token

---

#### Get Single Todo
Retrieve a specific todo by ID.

**Endpoint:** `GET /todos/:id`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "completed": false,
  "imageUrl": "string | null",
  "createdAt": "2026-01-26T10:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `404 Not Found` - Todo not found
- `403 Forbidden` - Todo belongs to another user

---

#### Create Todo
Create a new todo item.

**Endpoint:** `POST /todos`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "title": "string",
  "description": "string" // optional
}
```

**Response:** `201 Created`
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "completed": false,
  "imageUrl": null,
  "createdAt": "2026-01-26T10:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `400 Bad Request` - Missing required fields
- `422 Unprocessable Entity` - Validation errors

---

#### Update Todo
Update an existing todo item.

**Endpoint:** `PUT /todos/:id`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "title": "string", // optional
  "description": "string", // optional
  "completed": boolean // optional
}
```

**Response:** `200 OK`
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "completed": false,
  "imageUrl": "string | null",
  "createdAt": "2026-01-26T10:00:00Z",
  "updatedAt": "2026-01-26T10:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `404 Not Found` - Todo not found
- `403 Forbidden` - Todo belongs to another user
- `400 Bad Request` - Invalid input

---

#### Delete Todo
Delete a todo item.

**Endpoint:** `DELETE /todos/:id`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `204 No Content`

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `404 Not Found` - Todo not found
- `403 Forbidden` - Todo belongs to another user

---

### Todo Media

#### Get Pre-signed Upload URL for Todo Image
Get a pre-signed URL to upload an image for a specific todo item directly to S3. The client then uses this URL to upload the file directly to S3.

**Endpoint:** `POST /todos/:id/image/presigned-url`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "filename": "string",      // Original filename
  "content_type": "string"   // MIME type of the file
}
```

**Response:** `200 OK`
```json
{
  "presignedUrl": "string",   // URL to upload the file directly to S3
  "objectKey": "string",      // S3 object key for the file
  "expiresAt": "2026-01-26T11:00:00Z"  // Expiration time of the URL
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `404 Not Found` - Todo not found
- `403 Forbidden` - Todo belongs to another user
- `400 Bad Request` - Invalid file type
- `500 Internal Server Error` - Failed to generate pre-signed URL

---

#### Save Todo Image Metadata
After uploading the file to S3 using the pre-signed URL, call this endpoint to save the metadata in the database.

**Endpoint:** `POST /todos/:id/image`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "object_key": "string"   // S3 object key received from the pre-signed URL endpoint
}
```

**Response:** `200 OK`
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "completed": false,
  "imageUrl": "https://your-bucket.s3.amazonaws.com/todos/user123/todo456.jpg",
  "createdAt": "2026-01-26T10:00:00Z",
  "updatedAt": "2026-01-26T10:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `404 Not Found` - Todo not found
- `403 Forbidden` - Todo belongs to another user
- `500 Internal Server Error` - S3 upload failed

---

#### Get Todo Image
Retrieve a pre-signed URL to access a todo item's image directly from S3. The URL is valid for 1 hour.

**Endpoint:** `GET /todos/:id/image`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "profilePictureUrl": "https://your-bucket.s3.amazonaws.com/todos/user123/todo456.jpg?X-Amz-Signature=...",
  "expiresAt": "2026-01-26T11:00:00Z" // only if using signed URLs
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `404 Not Found` - Todo not found or todo has no image
- `403 Forbidden` - Todo belongs to another user

---

#### Delete Todo Image
Delete the image associated with a todo item.

**Endpoint:** `DELETE /todos/:id/image`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "completed": false,
  "imageUrl": null,
  "createdAt": "2026-01-26T10:00:00Z",
  "updatedAt": "2026-01-26T10:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `404 Not Found` - Todo not found or todo has no image
- `403 Forbidden` - Todo belongs to another user
- `500 Internal Server Error` - S3 deletion failed

---

### Profile Picture Media

#### Get Pre-signed Upload URL for Profile Picture
Get a pre-signed URL to upload a profile picture directly to S3. The client then uses this URL to upload the file directly to S3.

**Endpoint:** `POST /profile/picture/presigned-url`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "filename": "string",      // Original filename
  "content_type": "string"   // MIME type of the file
}
```

**Response:** `200 OK`
```json
{
  "presignedUrl": "string",   // URL to upload the file directly to S3
  "objectKey": "string",      // S3 object key for the file
  "expiresAt": "2026-01-26T11:00:00Z"  // Expiration time of the URL
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `400 Bad Request` - Invalid file type
- `500 Internal Server Error` - Failed to generate pre-signed URL

---

#### Save Profile Picture Metadata
After uploading the file to S3 using the pre-signed URL, call this endpoint to save the metadata in the database.

**Endpoint:** `POST /profile/picture`

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "object_key": "string"   // S3 object key received from the pre-signed URL endpoint
}
```

**Response:** `200 OK`
```json
{
  "id": "string",
  "username": "string",
  "profilePictureUrl": "https://your-bucket.s3.amazonaws.com/profiles/user123/profile.jpg",
  "updatedAt": "2026-01-26T10:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `500 Internal Server Error` - S3 upload failed

---

#### Get Profile Picture
Retrieve a pre-signed URL to access the profile picture directly from S3. The URL is valid for 1 hour.

**Endpoint:** `GET /profile/picture`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "profilePictureUrl": "https://your-bucket.s3.amazonaws.com/profiles/user123/profile.jpg?X-Amz-Signature=...",
  "expiresAt": "2026-01-26T11:00:00Z" // only if using signed URLs
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `404 Not Found` - User has no profile picture

---

#### Delete Profile Picture
Delete the profile picture associated with the authenticated user.

**Endpoint:** `DELETE /profile/picture`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "id": "string",
  "username": "string",
  "profilePictureUrl": null,
  "updatedAt": "2026-01-26T10:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid token
- `404 Not Found` - User has no profile picture to delete
- `500 Internal Server Error` - S3 deletion failed

---

## Error Response Format

All error responses follow this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {} // optional, additional error information
  }
}
```

## Common Error Codes

- `INVALID_CREDENTIALS` - Username or password is incorrect
- `USERNAME_EXISTS` - Username already taken
- `INVALID_TOKEN` - JWT token is invalid or expired
- `MISSING_TOKEN` - Authorization header missing
- `TODO_NOT_FOUND` - Requested todo does not exist
- `UNAUTHORIZED_ACCESS` - User doesn't have permission
- `VALIDATION_ERROR` - Input validation failed
- `INTERNAL_ERROR` - Server error
- `INVALID_FILE_TYPE` - File type not supported
- `FILE_TOO_LARGE` - File exceeds maximum size limit
- `NO_IMAGE_FOUND` - Todo item has no associated image
- `UPLOAD_FAILED` - Failed to upload file to storage
- `DELETE_FAILED` - Failed to delete file from storage
- `PROFILE_PICTURE_NOT_FOUND` - User has no profile picture set

## Database Schema Changes

The User model now includes:

```javascript
{
  id: "string",
  username: "string",
  hashed_password: "string",
  profilePictureUrl: "string | null",  // S3 URL of the profile picture
  profilePictureKey: "string | null",  // S3 object key for deletion
  createdAt: "datetime",
  updatedAt: "datetime"
}
```

The Todo model now includes:

```javascript
{
  id: "string",
  title: "string",
  description: "string",
  completed: "boolean",
  imageUrl: "string | null",      // S3 URL of the image
  imageKey: "string | null",       // S3 object key for deletion
  userId: "string",
  createdAt: "datetime",
  updatedAt: "datetime"
}
```