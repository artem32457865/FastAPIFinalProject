from fastapi import UploadFile
from settings import api_config
import uuid
import os
import aiofiles


async def generate_file_url(filename: str, dest_dir:str = api_config.STATIC_IMAGES_DIR) -> str:
    # Dummy implementation, replace with actual file storage logic
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    os.makedirs(dest_dir, exist_ok=True)
    file_path = os.path.join(dest_dir, unique_filename)
    return file_path


async def save_file(file: UploadFile, file_path: str):   
    async with aiofiles.open(file_path, "wb") as buffer:
        content = await file.read()
        await buffer.write(content)

