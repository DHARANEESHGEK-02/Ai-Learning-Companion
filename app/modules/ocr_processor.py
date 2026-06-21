"""
OCR Processor — extracts text from uploaded answer sheets (PDF/images)
using Google Gemini Vision API. No tesseract dependency required.
"""
import os
import base64
import google.generativeai as genai
from pathlib import Path

_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
            _configured = True


def extract_text_from_file(file_path: str) -> str:
    """Extract text from a PDF or image file."""
    _ensure_configured()
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return _extract_from_pdf(file_path)
    elif ext in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"):
        return _extract_from_image(file_path)
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""


def _extract_from_image(file_path: str) -> str:
    """Use Gemini Vision to extract handwritten/printed text from an image."""
    try:
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = Path(file_path).suffix.lower().lstrip(".")
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                    "bmp": "image/bmp", "tiff": "image/tiff", "webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/jpeg")

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": image_data,
                }
            },
            """You are an OCR system. Extract ALL text from this answer sheet image exactly as written.
Preserve question numbers, structure, and paragraph breaks.
If it is handwritten, transcribe it faithfully. Output only the extracted text, nothing else."""
        ])
        return response.text.strip()
    except Exception as e:
        return f"[OCR Error: {e}]"


def _extract_from_pdf(file_path: str) -> str:
    """Extract text from a PDF — try pdfplumber first, fall back to Gemini Vision on each page."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        combined = "\n".join(text_parts).strip()
        if combined and len(combined) > 50:
            return combined
    except Exception:
        pass

    # Fallback: convert PDF pages to images via Gemini file upload
    try:
        uploaded = genai.upload_file(file_path, mime_type="application/pdf")
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            uploaded,
            "Extract all text from this answer sheet PDF. Preserve question numbers, answers, and structure. Output only the text content."
        ])
        return response.text.strip()
    except Exception as e:
        return f"[PDF extraction error: {e}]"


def analyze_handwriting_quality(file_path: str) -> dict:
    """Analyze handwriting quality and legibility using Gemini Vision."""
    _ensure_configured()
    try:
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        ext = Path(file_path).suffix.lower().lstrip(".")
        mime_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            {"inline_data": {"mime_type": mime_type, "data": image_data}},
            """Analyze the handwriting quality in this answer sheet. Return a JSON object with:
{
  "legibility_score": <1-10>,
  "neatness_score": <1-10>,
  "overall_quality": "poor/fair/good/excellent",
  "observations": ["observation1", "observation2"]
}
Return ONLY the JSON, no other text."""
        ])
        import json, re
        text = response.text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {"legibility_score": 7, "neatness_score": 7, "overall_quality": "good", "observations": []}
