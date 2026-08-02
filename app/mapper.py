from __future__ import annotations

import copy
from typing import Dict, List


def _extract_all_words(ocr_json: Dict) -> List[str]:
    words: List[str] = []
    for page in ocr_json["pages"]:
        words.extend(w["text"] for w in page["words"])
    return words


def _find_value_by_key(key: str, ocr_json: Dict) -> str:
    """Very naive search: returns the text sequence appearing after the key on the same page."""
    key = key.strip()
    for page in ocr_json["pages"]:
        words = page["words"]
        texts = [w["text"] for w in words]
        if key in texts:
            idx = texts.index(key)
            # concatenate a few tokens after the key as candidate value
            follow = texts[idx + 1 : idx + 6]
            return " ".join(follow)
    return ""


def _fill_item(item: Dict, ocr_json: Dict) -> Dict:
    if not isinstance(item, dict):
        return item

    key = item.get("key")

    if isinstance(item.get("value"), list):
        # Recursively handle list items
        filled_list = []
        for element in item["value"]:
            filled_list.append(_fill_item(element, ocr_json))
        item["value"] = filled_list
    elif isinstance(item.get("value"), dict):
        # Complex object: try to fill 'selected' field when options available
        inner = item["value"]
        if "options" in inner and not inner.get("selected"):
            candidate = _find_value_by_key(key, ocr_json)
            if candidate in map(str, inner["options"]):
                inner["selected"] = [candidate]
        item["value"] = inner
    else:
        # Simple string field
        item["value"] = _find_value_by_key(key, ocr_json)

    return item


def populate_template(template: Dict, ocr_json: Dict) -> Dict:
    """Return a deep-copied template with 'value' fields filled from OCR."""
    new_tpl = copy.deepcopy(template)
    new_content = []
    for itm in new_tpl.get("content", []):
        new_content.append(_fill_item(itm, ocr_json))
    new_tpl["content"] = new_content
    return new_tpl 