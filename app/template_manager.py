from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path
from typing import Dict, List

import openai

TEMPLATE_DIR = Path("templates")
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


def _load_templates() -> List[Dict]:
    templates: List[Dict] = []
    for path in TEMPLATE_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                templates.append(json.load(f))
        except Exception:
            continue
    return templates


def _ocr_text_concat(ocr_json: Dict) -> str:
    texts: List[str] = []
    for page in ocr_json["pages"]:
        texts.extend(word["text"] for word in page["words"])
    return " ".join(texts)


def _jaccard_similarity(a: str, b: str) -> float:
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


async def select_or_generate_template(ocr_json: Dict) -> Dict:
    """Return best matching template or create a new one via OpenAI."""
    text = _ocr_text_concat(ocr_json)

    best_score = 0.0
    best_template = None
    for tpl in _load_templates():
        candidate_text = " ".join(item.get("key", "") for item in tpl.get("content", []))
        score = _jaccard_similarity(text, candidate_text)
        if score > best_score:
            best_score = score
            best_template = tpl

    # If similarity > threshold, re-use existing template
    if best_template and best_score > 0.3:
        return best_template

    # Otherwise, ask OpenAI to create new template
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY env var must be set to generate new templates.")

    prompt = (
        "次のOCRテキストから最適な報告書テンプレートを推測し、JSON 形式で作成してください。"\
        "\n"\
        "出力は以下の構造に従ってください:\n"\
        "{\n  \"title\": \"<タイトル>\",\n  \"content\": [ { \"key\": \"<項目名>\", \"value\": \"\" }, ... ]\n}\n"\
        "OCRテキスト:\n" + text[:4000]  # truncate for token limits
    )

    response = await openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    tpl_str = response.choices[0].message.content.strip()
    try:
        tpl = json.loads(tpl_str)
    except Exception:
        # Fallback minimal template
        tpl = {"title": "Auto Generated", "content": []}

    # Save template for future reuse
    filename = hashlib.sha1(text.encode()).hexdigest()[:10] + ".json"
    with open(TEMPLATE_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(tpl, f, ensure_ascii=False, indent=2)

    return tpl 