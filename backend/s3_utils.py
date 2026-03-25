import os
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from typing import Optional
import uuid
from datetime import timedelta
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

# Initialize S3 client
def get_s3_client():
    # Use IAM role credentials (no explicit access keys needed)
    return boto3.client('s3', region_name=S3_REGION)

def upload_file_to_s3(file_bytes: bytes, filename: str, user_id: str, folder: str) -> tuple[str, str]:
    """
    Upload a file to S3
    
    Args:
        file_bytes: The file content as bytes
        filename: Original filename
        user_id: ID of the user uploading
        folder: Folder name (e.g., 'todos', 'profiles')
    
    Returns:
        Tuple of (file_url, file_key)
    """
    s3_client = get_s3_client()
    
    # Extract file extension
    file_extension = os.path.splitext(filename)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_FILE_TYPE",
                    "message": f"File type {file_extension} not supported. Supported types: {', '.join(allowed_extensions)}"
                }
            }
        )
    
    # Create a unique key for the file
    unique_filename = f"{folder}/{user_id}/{uuid.uuid4()}{file_extension}"
    
    try:
        s3_client.upload_fileobj(
            file_bytes,
            S3_BUCKET_NAME,
            unique_filename,
            ExtraArgs={'ContentType': get_content_type(file_extension)}
        )
        
        # Generate the public URL
        file_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{unique_filename}"
        return file_url, unique_filename
        
    except ClientError as e:
        print(f"S3 Upload Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "UPLOAD_FAILED",
                    "message": "Failed to upload file to storage"
                }
            }
        )

def delete_file_from_s3(bucket_name: str, file_key: str) -> bool:
    """
    Delete a file from S3
    
    Args:
        bucket_name: The S3 bucket name
        file_key: The S3 object key to delete
    
    Returns:
        True if successful, False otherwise
    """
    s3_client = get_s3_client()
    
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=file_key)
        return True
    except ClientError as e:
        print(f"S3 Delete Error: {e}")
        return False

def get_content_type(extension: str) -> str:
    """Get the content type for a given file extension"""
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    return content_types.get(extension.lower(), 'application/octet-stream')

def is_valid_image_type(content_type: str) -> bool:
    """Check if the content type is a valid image type"""
    valid_types = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/webp'
    ]
    return content_type.lower() in valid_types

def generate_unique_filename(original_filename: str, user_id: str, folder: str) -> tuple[str, str]:
    """
    Generate a unique filename for S3 storage
    
    Args:
        original_filename: Original filename
        user_id: ID of the user
        folder: Folder name (e.g., 'todos', 'profiles')
    
    Returns:
        Tuple of (unique_key, extension)
    """
    file_extension = os.path.splitext(original_filename)[1].lower()
    unique_key = f"{folder}/{user_id}/{uuid.uuid4()}{file_extension}"
    return unique_key, file_extension

def generate_presigned_upload_url(bucket_name: str, object_key: str, content_type: str, expiration: int = 3600) -> str:
    """
    Generate a pre-signed URL for uploading files to S3
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        content_type: Content type of the file
        expiration: Expiration time in seconds (default 1 hour)
    
    Returns:
        Pre-signed URL for upload
    """
    s3_client = get_s3_client()
    
    try:
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
                'ContentType': content_type
            },
            ExpiresIn=expiration
        )
        return presigned_url
    except ClientError as e:
        print(f"Error generating presigned upload URL: {e}")
        raise

def generate_presigned_get_url(bucket_name: str, object_key: str, expiration: int = 3600) -> str:
    """
    Generate a pre-signed URL for retrieving files from S3
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        expiration: Expiration time in seconds (default 1 hour)
    
    Returns:
        Pre-signed URL for download
    """
    s3_client = get_s3_client()
    
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expiration
        )
        return presigned_url
    except ClientError as e:
        print(f"Error generating presigned get URL: {e}")
        raise