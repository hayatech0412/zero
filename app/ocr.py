from __future__ import annotations

import os
from typing import Dict, List

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path

# Allow overriding Tesseract executable path via env var
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")


def _detect_symbols(image: np.ndarray) -> List[Dict]:
    """Detect circles, triangles, and squares in the image. Returns list of dicts."""
    detected: List[Dict] = []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.medianBlur(gray, 5)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 200:  # filter tiny noise
            continue

        approx = cv2.approxPolyDP(cnt, 0.04 * cv2.arcLength(cnt, True), True)
        x, y, w, h = cv2.boundingRect(approx)
        shape = None
        if len(approx) == 3:
            shape = "triangle"
        elif len(approx) == 4:
            shape = "square"
        else:
            # Check circularity
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4 * np.pi * (area / (perimeter * perimeter))
            if 0.7 < circularity < 1.3:
                shape = "circle"

        if shape:
            detected.append({
                "shape": shape,
                "bbox": [int(x), int(y), int(w), int(h)]
            })

    return detected


def process_pdf(pdf_path: str) -> Dict:
    """Convert a PDF to images, run OCR & symbol detection per page, and return JSON."""
    pages = convert_from_path(pdf_path, dpi=300)
    result_pages = []

    for page_num, page in enumerate(pages, start=1):
        cv_img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)

        symbols = _detect_symbols(cv_img)

        # Run Tesseract OCR. Use TSV output to get bounding boxes.
        # Use English only since Japanese language pack is not available
        tsv = pytesseract.image_to_data(cv_img, lang="eng", output_type=pytesseract.Output.DICT)

        words = []
        n_boxes = len(tsv["text"])
        for i in range(n_boxes):
            text = tsv["text"][i].strip()
            if text:
                try:
                    conf = int(tsv["conf"][i])
                except ValueError:
                    conf = -1
                words.append({
                    "text": text,
                    "conf": conf,
                    "bbox": [int(tsv["left"][i]), int(tsv["top"][i]), int(tsv["width"][i]), int(tsv["height"][i])]
                })

        result_pages.append({
            "page": page_num,
            "words": words,
            "symbols": symbols,
        })

    return {"pages": result_pages} 