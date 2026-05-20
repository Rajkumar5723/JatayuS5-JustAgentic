from fastapi import UploadFile
import pdfplumber
import docx
import tempfile
import aiofiles
import os

async def extract_text_from_pdf(filepath: str) -> str:
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

async def extract_text_from_docx(filepath: str) -> str:
    doc = docx.Document(filepath)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

async def extract_text(file: UploadFile) -> str:
    extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    
    # Save UploadFile to a temporary file locally so parsers can read it
    fd, temp_path = tempfile.mkstemp(suffix=f".{extension}")
    os.close(fd)
    
    try:
        async with aiofiles.open(temp_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            
        if extension == 'pdf':
            text = await extract_text_from_pdf(temp_path)
        elif extension in ['doc', 'docx']:
            text = await extract_text_from_docx(temp_path)
        else:
            text = content.decode('utf-8', errors='ignore') # fallback for txt
            
        return text
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
