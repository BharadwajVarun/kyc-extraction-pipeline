import pytesseract
import cv2
from workers.preprocessor import preprocess

import os
if os.name == 'nt':  # Windows only
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text(image_path, lang="eng+hin"):
    preprocessed = preprocess(image_path)
    text = pytesseract.image_to_string(
        preprocessed,
        lang=lang,
        config="--psm 6 --oem 3"
    )
    return text.strip()


def extract_text_with_confidence(image_path, lang="eng+hin"):
    preprocessed = preprocess(image_path)
    data = pytesseract.image_to_data(
        preprocessed,
        lang=lang,
        config="--psm 6 --oem 3",
        output_type=pytesseract.Output.DICT
    )
    results = []
    for i, word in enumerate(data["text"]):
        if word.strip() == "":
            continue
        confidence = int(data["conf"][i])
        if confidence > 0:
            results.append({
                "word": word,
                "confidence": confidence
            })
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m workers.ocr_engine <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("\n--- RAW TEXT ---")
    text = extract_text(image_path)
    print(text)

    print("\n--- WORD CONFIDENCE SCORES ---")
    words = extract_text_with_confidence(image_path)
    for w in words:
        bar = "#" * (w["confidence"] // 10)
        print(f"{w['word']:20s} {w['confidence']:3d}% {bar}")
import pytesseract
import cv2
from workers.preprocessor import preprocess

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

def extract_text(image_path, lang="eng+hin"):
    preprocessed = preprocess(image_path)
    text = pytesseract.image_to_string(
        preprocessed,
        lang=lang,
        config="--psm 6 --oem 3"
    )
    return text.strip()


def extract_text_with_confidence(image_path, lang="eng+hin"):
    preprocessed = preprocess(image_path)
    data = pytesseract.image_to_data(
        preprocessed,
        lang=lang,
        config="--psm 6 --oem 3",
        output_type=pytesseract.Output.DICT
    )
    results = []
    for i, word in enumerate(data["text"]):
        if word.strip() == "":
            continue
        confidence = int(data["conf"][i])
        if confidence > 0:
            results.append({
                "word": word,
                "confidence": confidence
            })
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m workers.ocr_engine <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print("\n--- RAW TEXT ---")
    text = extract_text(image_path)
    print(text)

    print("\n--- WORD CONFIDENCE SCORES ---")
    words = extract_text_with_confidence(image_path)
    for w in words:
        bar = "#" * (w["confidence"] // 10)
        print(f"{w['word']:20s} {w['confidence']:3d}% {bar}")