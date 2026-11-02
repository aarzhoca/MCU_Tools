import json
import os
from typing import List, Dict, Optional
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _load_json(filename: str) -> List[Dict]:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def get_nuvoton_parts() -> List[Dict]:
    return _load_json("nuvoton_parts.json")


@lru_cache(maxsize=1)
def get_competitor_parts() -> List[Dict]:
    return _load_json("competitor_parts.json")


def _char_similarity(a: str, b: str) -> float:
    """Simple character-overlap score between two strings (both uppercased)."""
    if not a or not b:
        return 0.0
    # Count matching characters at same positions (prefix match bonus)
    matches = sum(ca == cb for ca, cb in zip(a, b))
    # Also count shared characters regardless of position
    shared = sum(min(a.count(c), b.count(c)) for c in set(a))
    return (matches * 2 + shared) / (len(a) + len(b))


def find_competitor_part(part_number: str) -> Optional[Dict]:
    """Exact match first; falls back to best fuzzy match if score > threshold."""
    parts = get_competitor_parts()
    normalized = part_number.strip().upper()

    # 1. Exact match
    exact = next((p for p in parts if p["part_number"].upper() == normalized), None)
    if exact:
        return exact

    # 2. Substring match (e.g. user typed partial number)
    substr = [p for p in parts if normalized in p["part_number"].upper()]
    if len(substr) == 1:
        return substr[0]

    # 3. Best fuzzy match if similarity is high enough (catches 1-2 char typos)
    best = max(parts, key=lambda p: _char_similarity(normalized, p["part_number"].upper()))
    if _char_similarity(normalized, best["part_number"].upper()) >= 0.75:
        return best

    return None


def search_competitor_parts(query: str) -> List[Dict]:
    """Search by part number, family, or manufacturer. Returns ranked results."""
    parts = get_competitor_parts()
    q = query.strip().upper()
    if not q:
        return parts[:20]

    results = []
    for p in parts:
        pn = p["part_number"].upper()
        fam = p.get("family", "").upper()
        mfr = p.get("manufacturer", "").upper()

        # Exact prefix match scores highest
        if pn.startswith(q):
            results.append((3, p))
        elif q in pn:
            results.append((2, p))
        elif q in fam or q in mfr:
            results.append((1, p))
        else:
            # Fuzzy fallback for short typos
            sim = _char_similarity(q, pn)
            if sim >= 0.6:
                results.append((sim, p))

    results.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in results[:20]]


def reload_data() -> None:
    """Clear cache to reload from disk (call after import)."""
    get_nuvoton_parts.cache_clear()
    get_competitor_parts.cache_clear()
