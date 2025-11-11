from pdfminer.high_level import extract_text as pdf_text
from docx import Document
from PIL import Image
import base64, os

OCR_PROVIDER = os.getenv('OCR_PROVIDER', 'local')

def load_text_from_file(f):
    name = f.name.lower()
    if name.endswith('.pdf'):
        return pdf_text(f)
    if name.endswith('.docx'):
        doc = Document(f)
        return '\n'.join(p.text for p in doc.paragraphs)
    return f.read().decode('utf-8', errors='ignore')

def file_to_b64(file) -> str:
    data = file.read()
    return base64.b64encode(data).decode('utf-8')

def ocr_image_to_text(file):
    file.seek(0)
    if OCR_PROVIDER == 'local':
        try:
            import easyocr, numpy as np
            img = Image.open(file).convert('RGB')
            arr = np.array(img)
            reader = easyocr.Reader(['ko','en'], gpu=False)
            res = reader.readtext(arr, detail=0)
            return '\n'.join(res)
        except Exception:
            pass
    # fallback: GPT-4o 비전
    from .utils_openai import client
    file.seek(0)
    b64 = file_to_b64(file)
    return client.vision_to_text('gpt-4o', b64, prompt='한글 문서 사진입니다. 줄바꿈 유지하여 텍스트만 추출해줘.')
