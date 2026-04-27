import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)

async def upload_image(file_path: str, public_id: str) -> str:
    """
    Uploads an image to Cloudinary and returns the secure URL.
    """
    response = cloudinary.uploader.upload(
        file_path,
        public_id = public_id,
        folder = "ecofil_avatars",
        overwrite = True,
        transformation = [
            {"width": 400, "height": 400, "crop": "fill", "gravity": "face"},
            {"fetch_format": "auto", "quality": "auto"}
        ]
    )
    return response.get("secure_url")
