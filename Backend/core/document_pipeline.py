from __future__ import annotations

import io
import json
import re
from typing import Any

from core.evidence_storage import EvidenceStorageService
from core.s3_manager import get_s3_manager

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None

try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover
    pdfplumber = None

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None


DOCUMENT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "selfie": {"category": "identity", "required": True},
    "aadhaar": {"category": "identity", "required": True},
    "pan": {"category": "identity", "required": False},
    "ug_marksheet": {"category": "education", "required": True},
    "pg_marksheet": {"category": "education", "required": False},
    "marksheet_10": {"category": "education", "required": True},
    "marksheet_12": {"category": "education", "required": True},
    "passport": {"category": "travel", "required": False},
}

INDIAN_STATES = [
    "andhra pradesh",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh",
    "jharkhand",
    "karnataka",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha",
    "punjab",
    "rajasthan",
    "sikkim",
    "tamil nadu",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
    "west bengal",
    "delhi",
]


def document_definition(document_type: str) -> dict[str, Any]:
    return DOCUMENT_DEFINITIONS.get(document_type, {"category": "other", "required": True})


def document_storage(db_session) -> EvidenceStorageService:
    return EvidenceStorageService(get_s3_manager(), db_session)


async def store_document_bytes(
    db_session,
    *,
    session_token: str,
    document_type: str,
    filename: str,
    mime_type: str,
    payload: bytes,
) -> tuple[str, int]:
    storage = document_storage(db_session)
    storage_key = await storage.upload_evidence(
        session_token=session_token,
        evidence_type="document",
        file_data=payload,
        mime_type=mime_type or "application/octet-stream",
        metadata={"document_type": document_type, "filename": filename},
    )
    if not storage_key:
        raise RuntimeError(f"Failed to store document: {document_type}")
    return storage_key, len(payload)


def _extract_text_pdf(payload: bytes) -> str:
    if pdfplumber is None:
        return ""
    try:
        text_parts = []
        with pdfplumber.open(io.BytesIO(payload)) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(part for part in text_parts if part).strip()
    except Exception:
        return ""


def _ocr_image_bytes(payload: bytes) -> str:
    if Image is None or pytesseract is None:
        return ""
    try:
        with Image.open(io.BytesIO(payload)) as image:
            return pytesseract.image_to_string(image) or ""
    except Exception:
        return ""


def _ocr_pdf_images(payload: bytes, *, max_pages: int = 3) -> str:
    if fitz is None or Image is None or pytesseract is None:
        return ""
    try:
        text_parts = []
        with fitz.open(stream=payload, filetype="pdf") as pdf:
            for page_index in range(min(len(pdf), max_pages)):
                page = pdf.load_page(page_index)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                text_parts.append(pytesseract.image_to_string(image) or "")
        return "\n".join(part for part in text_parts if part).strip()
    except Exception:
        return ""


def _line_value(text: str, labels: list[str]) -> str:
    for label in labels:
        match = re.search(rf"{label}\s*[:\-]\s*(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_structured_fields(text: str) -> dict[str, Any]:
    compact = " ".join(str(text or "").split())
    state = ""
    lowered = compact.lower()
    for value in INDIAN_STATES:
        if value in lowered:
            state = value.title()
            break
    pincode_match = re.search(r"\b(\d{6})\b", compact)
    pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", compact.upper())
    aadhaar_match = re.search(r"\b([0-9]{4}\s?[0-9]{4}\s?[0-9]{4})\b", compact)

    address = _line_value(compact, ["address", "addr"])
    name = _line_value(compact, ["name", "candidate name", "holder name", "student name"])
    city = ""
    if address:
        address_parts = [part.strip() for part in re.split(r"[,|]", address) if part.strip()]
        if len(address_parts) >= 2:
            city = address_parts[-2]
    if not city and state:
        city_match = re.search(rf"([A-Za-z ]+)\s+{re.escape(state)}", compact, re.IGNORECASE)
        if city_match:
            city = city_match.group(1).strip(" ,")

    return {
        "name": name,
        "address": address,
        "city": city,
        "state": state,
        "pincode": pincode_match.group(1) if pincode_match else "",
        "pan": pan_match.group(1) if pan_match else "",
        "aadhaar": re.sub(r"\s+", "", aadhaar_match.group(1)) if aadhaar_match else "",
    }


def extract_document_text(filename: str, mime_type: str, payload: bytes) -> dict[str, Any]:
    name = (filename or "").lower()
    mime = (mime_type or "").lower()
    status = "not_supported"
    text = ""
    method = ""

    if name.endswith(".pdf") or "pdf" in mime:
        text = _extract_text_pdf(payload)
        if text:
            status = "embedded_text"
            method = "pdfplumber"
        else:
            text = _ocr_pdf_images(payload)
            if text:
                status = "ocr_complete"
                method = "pymupdf+pytesseract"
            else:
                status = "ocr_runtime_missing" if (fitz is None or pytesseract is None) else "ocr_empty"
                method = "pymupdf+pytesseract" if fitz and pytesseract else "missing_runtime"
    elif any(ext in name for ext in [".png", ".jpg", ".jpeg", ".webp"]) or mime.startswith("image/"):
        text = _ocr_image_bytes(payload)
        if text:
            status = "ocr_complete"
            method = "pytesseract"
        else:
            status = "ocr_runtime_missing" if pytesseract is None else "ocr_empty"
            method = "pytesseract" if pytesseract else "missing_runtime"

    fields = extract_structured_fields(text)
    return {
        "text": (text or "").strip(),
        "ocr_status": status,
        "ocr_method": method,
        "fields": fields,
    }


def json_value(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=True)
