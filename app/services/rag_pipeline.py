import hashlib
import math
import re
from typing import List, Tuple, Optional

import numpy as np

MIN_TOKENS = 400
MAX_TOKENS = 1200
DEFAULT_OVERLAP = 0.15


def normalize_text(text: str) -> str:
    # basic normalization: strip control chars and collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str, overlap_ratio: float = DEFAULT_OVERLAP) -> List[Tuple[str, int, Optional[str]]]:
    """Chunk text into ~400-1200 token segments with overlap. Returns (chunk, index, section_title)."""
    lines = text.splitlines()
    sections = []
    current_section = {"title": None, "content": []}
    for ln in lines:
        if re.match(r"^(#+\s|\d+\.\s)", ln):
            if current_section["content"]:
                sections.append(current_section)
            current_section = {"title": ln.strip("# ").strip(), "content": []}
        else:
            current_section["content"].append(ln)
    if current_section["content"]:
        sections.append(current_section)

    chunks: List[Tuple[str, int, Optional[str]]] = []
    idx = 0
    for sec in sections:
        sec_text = " ".join(sec["content"]).strip()
        words = sec_text.split()
        max_tokens = MAX_TOKENS
        min_tokens = MIN_TOKENS
        overlap = int(max_tokens * overlap_ratio)
        i = 0
        while i < len(words):
            chunk_tokens = words[i : i + max_tokens]
            if len(chunk_tokens) < min_tokens and i > 0:
                break
            chunk = " ".join(chunk_tokens).strip()
            if chunk:
                chunks.append((chunk, idx, sec["title"]))
                idx += 1
            step = max_tokens - overlap if max_tokens > overlap else max_tokens
            i += step
    return chunks


def embedding_for_text(text: str) -> List[float]:
    """Deterministic pseudo-embedding for offline/test use (hash-based)."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vec = [int.from_bytes(h[i : i + 4], "big") % 1000 / 1000.0 for i in range(0, 32, 4)]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a)
    b = np.array(vec_b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(np.dot(a, b) / denom)
