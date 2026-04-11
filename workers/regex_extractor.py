from workers.validators import validate_extraction
import re
import spacy

nlp = spacy.load("en_core_web_sm")


# ─── Pattern Definitions ───────────────────────────────────────────

AADHAAR_PATTERN = re.compile(
    r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b"
)

PAN_PATTERN = re.compile(
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
)

DOB_PATTERN = re.compile(
    r"\b(\d{2}[\/\-\|\\]\d{2}[\/\-\|\\]\d{4})\b"
)

GENDER_PATTERN = re.compile(
    r"\b(MALE|FEMALE|Male|Female|male|female|"
    r"TRANS|Trans|M a l e|F e m a l e)\b"
)

NAME_KEYWORDS = ["name", "नाम"]


# ─── Individual Extractors ─────────────────────────────────────────

def extract_aadhaar(text):
    match = AADHAAR_PATTERN.search(text)
    if match:
        uid = re.sub(r"\s", "", match.group())
        return {"value": uid, "confidence": 0.95}
    return {"value": None, "confidence": 0.0}


def extract_pan(text):
    match = PAN_PATTERN.search(text)
    if match:
        return {"value": match.group(), "confidence": 0.97}
    return {"value": None, "confidence": 0.0}


def extract_dob(text):
    match = DOB_PATTERN.search(text)
    if match:
        return {"value": match.group(), "confidence": 0.90}
    return {"value": None, "confidence": 0.0}


def extract_gender(text):
    match = GENDER_PATTERN.search(text)
    if match:
        return {"value": match.group().upper(), "confidence": 0.92}
    return {"value": None, "confidence": 0.0}


def extract_name_spacy(text):
    lines = text.split("\n")
    for i, line in enumerate(lines):
        line_lower = line.lower()
        for keyword in NAME_KEYWORDS:
            if keyword in line_lower:
                # Name is usually on the same line or next line
                candidate = line.split(":")[-1].strip()
                if not candidate and i + 1 < len(lines):
                    candidate = lines[i + 1].strip()
                if candidate:
                    return {
                        "value": candidate.title(),
                        "confidence": 0.80
                    }

    # Fallback — use spaCy NER to find a PERSON entity
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return {
                "value": ent.text.title(),
                "confidence": 0.65
            }

    return {"value": None, "confidence": 0.0}


# ─── Document Type Detector ────────────────────────────────────────

def detect_document_type(text):
    text_upper = text.upper()
    # Partial matches to handle OCR cutting first letters
    if any(x in text_upper for x in [
        "AADHAAR", "ADHAAR", "DHAAR", "UIDAI", "UNIQUE IDENTIFICATION"
    ]):
        return "AADHAAR"
    if any(x in text_upper for x in [
        "INCOME TAX", "PAN", "PERMANENT ACCOUNT"
    ]):
        return "PAN"
    if any(x in text_upper for x in [
        "PASSPORT", "REPUBLIC OF INDIA"
    ]):
        return "PASSPORT"
    # Last resort — if UID pattern found, it's likely Aadhaar
    if AADHAAR_PATTERN.search(text):
        return "AADHAAR"
    return "UNKNOWN"

# ─── Main Extractor ────────────────────────────────────────────────

def extract_fields(raw_text):
    doc_type = detect_document_type(raw_text)

    result = {
        "document_type": doc_type,
        "fields": {
            "aadhaar_uid": extract_aadhaar(raw_text),
            "pan_number":  extract_pan(raw_text),
            "date_of_birth": extract_dob(raw_text),
            "gender":      extract_gender(raw_text),
            "name":        extract_name_spacy(raw_text),
        }
    }

    # Overall confidence — average of all found fields
    found = [
        v["confidence"]
        for v in result["fields"].values()
        if v["value"] is not None
    ]
    result["overall_confidence"] = (
        round(sum(found) / len(found), 2) if found else 0.0
    )

    result["validation"] = validate_extraction(result["fields"])
    
    return result


if __name__ == "__main__":
    import sys
    import json
    from workers.ocr_engine import extract_text

    if len(sys.argv) < 2:
        print("Usage: python -m workers.regex_extractor <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("Running OCR...")
    raw_text = extract_text(image_path)

    print("Extracting fields...\n")
    output = extract_fields(raw_text)

    print(json.dumps(output, indent=2, ensure_ascii=False))
=======
from workers.validators import validate_extraction
import re
import spacy

nlp = spacy.load("en_core_web_sm")


# ─── Pattern Definitions ───────────────────────────────────────────

AADHAAR_PATTERN = re.compile(
    r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b"
)

PAN_PATTERN = re.compile(
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
)

DOB_PATTERN = re.compile(
    r"\b(\d{2}[\/\-\|\\]\d{2}[\/\-\|\\]\d{4})\b"
)

GENDER_PATTERN = re.compile(
    r"\b(MALE|FEMALE|Male|Female|male|female|"
    r"TRANS|Trans|M a l e|F e m a l e)\b"
)

NAME_KEYWORDS = ["name", "नाम"]


# ─── Individual Extractors ─────────────────────────────────────────

def extract_aadhaar(text):
    match = AADHAAR_PATTERN.search(text)
    if match:
        uid = re.sub(r"\s", "", match.group())
        return {"value": uid, "confidence": 0.95}
    return {"value": None, "confidence": 0.0}


def extract_pan(text):
    match = PAN_PATTERN.search(text)
    if match:
        return {"value": match.group(), "confidence": 0.97}
    return {"value": None, "confidence": 0.0}


def extract_dob(text):
    match = DOB_PATTERN.search(text)
    if match:
        return {"value": match.group(), "confidence": 0.90}
    return {"value": None, "confidence": 0.0}


def extract_gender(text):
    match = GENDER_PATTERN.search(text)
    if match:
        return {"value": match.group().upper(), "confidence": 0.92}
    return {"value": None, "confidence": 0.0}


def extract_name_spacy(text):
    lines = text.split("\n")
    for i, line in enumerate(lines):
        line_lower = line.lower()
        for keyword in NAME_KEYWORDS:
            if keyword in line_lower:
                # Name is usually on the same line or next line
                candidate = line.split(":")[-1].strip()
                if not candidate and i + 1 < len(lines):
                    candidate = lines[i + 1].strip()
                if candidate:
                    return {
                        "value": candidate.title(),
                        "confidence": 0.80
                    }

    # Fallback — use spaCy NER to find a PERSON entity
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return {
                "value": ent.text.title(),
                "confidence": 0.65
            }

    return {"value": None, "confidence": 0.0}


# ─── Document Type Detector ────────────────────────────────────────

def detect_document_type(text):
    text_upper = text.upper()
    # Partial matches to handle OCR cutting first letters
    if any(x in text_upper for x in [
        "AADHAAR", "ADHAAR", "DHAAR", "UIDAI", "UNIQUE IDENTIFICATION"
    ]):
        return "AADHAAR"
    if any(x in text_upper for x in [
        "INCOME TAX", "PAN", "PERMANENT ACCOUNT"
    ]):
        return "PAN"
    if any(x in text_upper for x in [
        "PASSPORT", "REPUBLIC OF INDIA"
    ]):
        return "PASSPORT"
    # Last resort — if UID pattern found, it's likely Aadhaar
    if AADHAAR_PATTERN.search(text):
        return "AADHAAR"
    return "UNKNOWN"

# ─── Main Extractor ────────────────────────────────────────────────

def extract_fields(raw_text):
    doc_type = detect_document_type(raw_text)

    result = {
        "document_type": doc_type,
        "fields": {
            "aadhaar_uid": extract_aadhaar(raw_text),
            "pan_number":  extract_pan(raw_text),
            "date_of_birth": extract_dob(raw_text),
            "gender":      extract_gender(raw_text),
            "name":        extract_name_spacy(raw_text),
        }
    }

    # Overall confidence — average of all found fields
    found = [
        v["confidence"]
        for v in result["fields"].values()
        if v["value"] is not None
    ]
    result["overall_confidence"] = (
        round(sum(found) / len(found), 2) if found else 0.0
    )

    result["validation"] = validate_extraction(result["fields"])
    
    return result


if __name__ == "__main__":
    import sys
    import json
    from workers.ocr_engine import extract_text

    if len(sys.argv) < 2:
        print("Usage: python -m workers.regex_extractor <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("Running OCR...")
    raw_text = extract_text(image_path)

    print("Extracting fields...\n")
    output = extract_fields(raw_text)

    print(json.dumps(output, indent=2, ensure_ascii=False))
>>>>>>> f530946c4cd212f289bf5f1a8ec9a691424f0225
