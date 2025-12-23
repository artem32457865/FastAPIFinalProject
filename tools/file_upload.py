from fastapi import UploadFile
from settings import api_config
import uuid
import os
import aiofiles


async def generate_file_url(filename: str, dest_dir: str = api_config.STATIC_IMAGES_DIR) -> str:
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    os.makedirs(dest_dir, exist_ok=True)
    file_path = os.path.join(dest_dir, unique_filename)
    return file_path


async def generate_repair_file_url(filename: str) -> str:
    """Generate file URL for repair photos in static/repair/ directory"""
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    repair_dir = "static/repair"
    os.makedirs(repair_dir, exist_ok=True)
    file_system_path = os.path.join(repair_dir, unique_filename)
    
    # Save the file to the file system
    # Return the URL path that will be used to access the file via FastAPI static mount
    return f"/static/repair/{unique_filename}"


async def save_file(file: UploadFile, file_path: str):   
    # The file_path is the URL path like "/static/repair/filename"
    # We need to convert it to the actual file system path by removing "/static/" and using "static/"
    if file_path.startswith('/static/'):
        actual_file_path = "static/" + file_path[8:]  # Remove "/static/" and prepend "static/"
    else:
        actual_file_path = file_path
    async with aiofiles.open(actual_file_path, "wb") as buffer:
        content = await file.read()
        await buffer.write(content)