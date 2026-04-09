from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import base64
import io
import tempfile
import asyncio

# PDF and Image processing
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch

# LLM Integration
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Temp directory for files
TEMP_DIR = Path(tempfile.gettempdir()) / "translate_app"
TEMP_DIR.mkdir(exist_ok=True)

# Language codes mapping
LANGUAGES = {
    "es": "Spanish",
    "en": "English",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "cs": "Czech",
    "el": "Greek",
    "he": "Hebrew",
    "id": "Indonesian",
    "ms": "Malay",
    "ro": "Romanian",
    "uk": "Ukrainian",
    "hu": "Hungarian",
    "bg": "Bulgarian",
    "ca": "Catalan",
    "hr": "Croatian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sr": "Serbian",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "et": "Estonian",
    "fa": "Persian",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
    "sw": "Swahili",
    "fil": "Filipino",
}

# AI Provider configurations
AI_PROVIDERS = {
    "openai": {"model": "gpt-5.2", "name": "OpenAI GPT-5.2"},
    "gemini": {"model": "gemini-3-flash-preview", "name": "Gemini 3 Flash"},
    "claude": {"model": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5"},
}

# Models
class TranslationHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    source_lang: str
    target_lang: str
    provider: str
    file_type: str
    status: str = "completed"
    translated_file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TranslationResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str

class LanguageOption(BaseModel):
    code: str
    name: str

class ProviderOption(BaseModel):
    id: str
    name: str
    model: str

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF using PyPDF2"""
    try:
        pdf_reader = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return ""


async def extract_text_from_image(file_content: bytes) -> str:
    """Extract text from image using OCR (pytesseract)"""
    try:
        image = Image.open(io.BytesIO(file_content))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting image text: {e}")
        return ""


async def translate_text_with_ai(text: str, source_lang: str, target_lang: str, provider: str) -> str:
    """Translate text using the selected AI provider"""
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    provider_config = AI_PROVIDERS.get(provider)
    if not provider_config:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    source_name = LANGUAGES.get(source_lang, source_lang)
    target_name = LANGUAGES.get(target_lang, target_lang)
    
    system_message = f"""You are a professional translator. Translate the following text from {source_name} to {target_name}. 
    
Rules:
- Maintain the original formatting, paragraphs, and structure
- Preserve any special characters, numbers, and punctuation
- If the text contains technical terms, translate them appropriately or keep them in the original if commonly used
- Return ONLY the translated text, no explanations or notes
- Preserve line breaks and paragraph structure"""

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"translate-{uuid.uuid4()}",
            system_message=system_message
        ).with_model(provider, provider_config["model"])
        
        user_message = UserMessage(text=f"Translate this text:\n\n{text}")
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        logger.error(f"Translation error with {provider}: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


async def translate_image_with_vision(file_content: bytes, source_lang: str, target_lang: str, provider: str) -> str:
    """Translate text in image using AI vision capabilities"""
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    provider_config = AI_PROVIDERS.get(provider)
    if not provider_config:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    source_name = LANGUAGES.get(source_lang, source_lang)
    target_name = LANGUAGES.get(target_lang, target_lang)
    
    system_message = f"""You are a professional translator with OCR capabilities. Extract and translate ALL text visible in the image from {source_name} to {target_name}.

Rules:
- First identify all text in the image
- Then translate it accurately
- Maintain the structure and format of the original text
- Return ONLY the translated text, preserving line breaks and paragraphs
- If no text is found, respond with "NO_TEXT_FOUND" """

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"vision-translate-{uuid.uuid4()}",
            system_message=system_message
        ).with_model(provider, provider_config["model"])
        
        # Convert to base64
        image_base64 = base64.b64encode(file_content).decode('utf-8')
        image_content = ImageContent(image_base64=image_base64)
        
        user_message = UserMessage(
            text=f"Extract all text from this image and translate it from {source_name} to {target_name}. Return only the translated text.",
            image_contents=[image_content]
        )
        
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        logger.error(f"Vision translation error with {provider}: {e}")
        # Fallback to OCR + text translation
        logger.info("Falling back to OCR + text translation")
        extracted_text = await extract_text_from_image(file_content)
        if extracted_text:
            return await translate_text_with_ai(extracted_text, source_lang, target_lang, provider)
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


def create_translated_pdf(translated_text: str, output_path: Path):
    """Create a PDF with the translated text"""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    # Set font
    c.setFont("Helvetica", 11)
    
    # Text settings
    margin = 72  # 1 inch
    line_height = 14
    max_width = width - 2 * margin
    y_position = height - margin
    
    # Split text into paragraphs and lines
    paragraphs = translated_text.split('\n')
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            y_position -= line_height
            if y_position < margin:
                c.showPage()
                c.setFont("Helvetica", 11)
                y_position = height - margin
            continue
        
        # Word wrap
        words = paragraph.split()
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if c.stringWidth(test_line, "Helvetica", 11) < max_width:
                current_line = test_line
            else:
                if current_line:
                    c.drawString(margin, y_position, current_line)
                    y_position -= line_height
                    if y_position < margin:
                        c.showPage()
                        c.setFont("Helvetica", 11)
                        y_position = height - margin
                current_line = word
        
        if current_line:
            c.drawString(margin, y_position, current_line)
            y_position -= line_height
            if y_position < margin:
                c.showPage()
                c.setFont("Helvetica", 11)
                y_position = height - margin
    
    c.save()


def create_translated_image(translated_text: str, original_image: bytes, output_path: Path):
    """Create an image with the translated text overlay"""
    # Open original image for dimensions
    img = Image.open(io.BytesIO(original_image))
    
    # Create a white background with the same size or minimum
    width = max(img.width, 800)
    height = max(img.height, 600)
    
    # Create new image with white background
    new_img = Image.new('RGB', (width, height), 'white')
    
    # Add text using PIL
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(new_img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
    
    # Word wrap and draw text
    margin = 40
    y = margin
    max_text_width = width - 2 * margin
    
    paragraphs = translated_text.split('\n')
    for paragraph in paragraphs:
        if not paragraph.strip():
            y += 20
            continue
        
        words = paragraph.split()
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width < max_text_width:
                current_line = test_line
            else:
                if current_line:
                    draw.text((margin, y), current_line, fill='black', font=font)
                    y += 24
                current_line = word
        
        if current_line:
            draw.text((margin, y), current_line, fill='black', font=font)
            y += 24
    
    new_img.save(output_path, format='PNG')


# API Routes
@api_router.get("/")
async def root():
    return {"message": "Translation API is running"}


@api_router.get("/languages", response_model=List[LanguageOption])
async def get_languages():
    """Get list of supported languages"""
    return [LanguageOption(code=code, name=name) for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1])]


@api_router.get("/providers", response_model=List[ProviderOption])
async def get_providers():
    """Get list of AI providers"""
    return [
        ProviderOption(id=pid, name=config["name"], model=config["model"]) 
        for pid, config in AI_PROVIDERS.items()
    ]


@api_router.post("/translate", response_model=TranslationResponse)
async def translate_file(
    file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    provider: str = Form(default="openai")
):
    """Translate a PDF or image file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file type
    filename = file.filename.lower()
    is_pdf = filename.endswith('.pdf')
    is_image = any(filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp'])
    
    if not is_pdf and not is_image:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, PNG, JPG, or WEBP")
    
    # Validate languages
    if source_lang not in LANGUAGES and source_lang != "auto":
        raise HTTPException(status_code=400, detail=f"Unsupported source language: {source_lang}")
    if target_lang not in LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported target language: {target_lang}")
    
    # Validate provider
    if provider not in AI_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    
    try:
        file_content = await file.read()
        translation_id = str(uuid.uuid4())
        
        if is_pdf:
            # Extract text from PDF
            extracted_text = await extract_text_from_pdf(file_content)
            if not extracted_text:
                # Try OCR on PDF pages
                try:
                    images = convert_from_bytes(file_content)
                    for img in images:
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        img_bytes = img_byte_arr.getvalue()
                        page_text = await extract_text_from_image(img_bytes)
                        if page_text:
                            extracted_text += page_text + "\n\n"
                except Exception as e:
                    logger.error(f"OCR fallback failed: {e}")
            
            if not extracted_text.strip():
                raise HTTPException(status_code=400, detail="No text could be extracted from the PDF")
            
            # Translate
            translated_text = await translate_text_with_ai(extracted_text, source_lang, target_lang, provider)
            
            # Create translated PDF
            output_filename = f"translated_{translation_id}.pdf"
            output_path = TEMP_DIR / output_filename
            create_translated_pdf(translated_text, output_path)
            file_type = "pdf"
            
        else:
            # Image translation using vision
            translated_text = await translate_image_with_vision(file_content, source_lang, target_lang, provider)
            
            if translated_text == "NO_TEXT_FOUND" or not translated_text.strip():
                raise HTTPException(status_code=400, detail="No text found in the image")
            
            # Create translated image
            output_filename = f"translated_{translation_id}.png"
            output_path = TEMP_DIR / output_filename
            create_translated_image(translated_text, file_content, output_path)
            file_type = "image"
        
        # Save to history
        history_entry = TranslationHistory(
            id=translation_id,
            filename=file.filename,
            source_lang=source_lang,
            target_lang=target_lang,
            provider=provider,
            file_type=file_type,
            translated_file_path=str(output_path)
        )
        
        doc = history_entry.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.translation_history.insert_one(doc)
        
        return TranslationResponse(
            id=translation_id,
            filename=file.filename,
            status="completed",
            message="Translation completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@api_router.get("/history", response_model=List[TranslationHistory])
async def get_history():
    """Get translation history"""
    history = await db.translation_history.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for item in history:
        if isinstance(item.get('created_at'), str):
            item['created_at'] = datetime.fromisoformat(item['created_at'])
    return history


@api_router.get("/download/{translation_id}")
async def download_translation(translation_id: str):
    """Download a translated file"""
    history = await db.translation_history.find_one({"id": translation_id}, {"_id": 0})
    if not history:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    file_path = Path(history.get('translated_file_path', ''))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Translated file not found")
    
    # Determine media type
    media_type = "application/pdf" if history.get('file_type') == 'pdf' else "image/png"
    ext = "pdf" if history.get('file_type') == 'pdf' else "png"
    
    # Create a user-friendly filename
    original_name = Path(history.get('filename', 'document')).stem
    target_lang = LANGUAGES.get(history.get('target_lang', ''), history.get('target_lang', ''))
    download_filename = f"{original_name}_{target_lang}.{ext}"
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=download_filename
    )


@api_router.delete("/history/{translation_id}")
async def delete_history_item(translation_id: str):
    """Delete a translation from history"""
    history = await db.translation_history.find_one({"id": translation_id}, {"_id": 0})
    if history:
        # Delete file if exists
        file_path = Path(history.get('translated_file_path', ''))
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete file: {e}")
    
    result = await db.translation_history.delete_one({"id": translation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    return {"message": "Deleted successfully"}


# Include the router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
