"""
Plagiarism Detection — TF-IDF cosine similarity across submitted answer sheets.
Flags high similarity (>70%) between student submissions.
"""
from typing import List
import re


def _tokenize(text: str) -> list:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text.split()


def _compute_tf(tokens: list) -> dict:
    tf = {}
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1
    total = max(len(tokens), 1)
    return {k: v / total for k, v in tf.items()}


def _cosine_similarity(vec_a: dict, vec_b: dict) -> float:
    if not vec_a or not vec_b:
        return 0.0
    common_keys = set(vec_a.keys()) & set(vec_b.keys())
    dot_product = sum(vec_a[k] * vec_b[k] for k in common_keys)
    mag_a = sum(v ** 2 for v in vec_a.values()) ** 0.5
    mag_b = sum(v ** 2 for v in vec_b.values()) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot_product / (mag_a * mag_b)


def check_plagiarism(new_text: str, existing_texts: List[str], threshold: float = 0.70) -> float:
    """
    Compare new_text against all existing texts.
    Returns the maximum similarity score (0.0 – 1.0).
    Score > threshold suggests potential plagiarism.
    """
    if not new_text or not existing_texts:
        return 0.0

    new_tokens = _tokenize(new_text)
    new_tf = _compute_tf(new_tokens)

    max_similarity = 0.0
    for existing in existing_texts:
        if not existing:
            continue
        ex_tokens = _tokenize(existing)
        ex_tf = _compute_tf(ex_tokens)
        sim = _cosine_similarity(new_tf, ex_tf)
        if sim > max_similarity:
            max_similarity = sim

    return round(max_similarity, 3)


def pairwise_plagiarism_report(texts: List[dict]) -> List[dict]:
    """
    Generate a pairwise plagiarism report for a list of submissions.
    texts: [{"id": int, "student": str, "text": str}, ...]
    Returns: list of flagged pairs above threshold
    """
    flagged = []
    tfs = [_compute_tf(_tokenize(t["text"])) for t in texts]

    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            sim = _cosine_similarity(tfs[i], tfs[j])
            if sim > 0.70:
                flagged.append({
                    "student_a": texts[i]["student"],
                    "student_b": texts[j]["student"],
                    "similarity": round(sim * 100, 1),
                    "risk": "High" if sim > 0.85 else "Medium",
                })

    return sorted(flagged, key=lambda x: x["similarity"], reverse=True)
