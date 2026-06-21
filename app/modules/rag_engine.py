"""
RAG (Retrieval-Augmented Generation) Engine.
Stores knowledge chunks as numpy embedding vectors and retrieves relevant
context for the AI tutor using Gemini embedding API.
"""
import os
import json
import numpy as np
from typing import List
import google.generativeai as genai

_configured = False
_knowledge_base: list = []  # [{text, embedding, metadata}]


def _ensure_configured():
    global _configured
    if not _configured:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
            _configured = True


def _embed(text: str) -> np.ndarray | None:
    """Get embedding vector for text using Gemini."""
    try:
        _ensure_configured()
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
        )
        return np.array(result["embedding"], dtype=np.float32)
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def add_knowledge(text: str, metadata: dict | None = None):
    """Add a knowledge chunk to the in-memory RAG store."""
    embedding = _embed(text)
    if embedding is not None:
        _knowledge_base.append({
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {},
        })


def add_knowledge_batch(texts: List[str], metadatas: List[dict] | None = None):
    """Add multiple knowledge chunks."""
    for i, text in enumerate(texts):
        meta = metadatas[i] if metadatas and i < len(metadatas) else {}
        add_knowledge(text, meta)


def retrieve_context(query: str, top_k: int = 3) -> List[str]:
    """Retrieve top-k most relevant knowledge chunks for a query."""
    if not _knowledge_base:
        return []

    query_emb = _embed(query)
    if query_emb is None:
        return []

    scores = [
        (i, _cosine_sim(query_emb, chunk["embedding"]))
        for i, chunk in enumerate(_knowledge_base)
    ]
    scores.sort(key=lambda x: x[1], reverse=True)
    top = scores[:top_k]
    return [_knowledge_base[i]["text"] for i, _ in top if _ > 0.3]


def augmented_query(question: str, subject: str | None = None) -> str:
    """
    Build an augmented prompt using retrieved context.
    Used by the AI tutor to give grounded answers.
    """
    _ensure_configured()
    context_chunks = retrieve_context(question, top_k=3)

    if context_chunks:
        context_block = "\n\n---\n".join(context_chunks)
        prompt = f"""You are an expert AI tutor. Use the following reference material to answer the student's question accurately.

Reference Material:
{context_block}

{"Subject: " + subject if subject else ""}
Student Question: {question}

Provide a clear, educational answer grounded in the reference material above."""
    else:
        prompt = f"""You are an expert AI tutor.
{"Subject: " + subject if subject else ""}
Student Question: {question}

Provide a clear, accurate, and educational answer."""

    return prompt


def seed_default_knowledge():
    """Seed a small initial knowledge base with common concepts."""
    default_chunks = [
        "Algorithms: Big-O notation describes time complexity. O(1) is constant, O(log n) is logarithmic, O(n) is linear, O(n²) is quadratic.",
        "Data Structures: Arrays offer O(1) access, O(n) search. Linked lists offer O(n) access. Hash tables offer O(1) average search.",
        "Newton's Laws: 1) Objects remain at rest/motion unless acted upon. 2) F=ma. 3) Every action has equal and opposite reaction.",
        "Thermodynamics: First law — energy is conserved. Second law — entropy always increases in an isolated system.",
        "Chemical Bonding: Ionic bonds form between metals and non-metals. Covalent bonds form between non-metals sharing electrons.",
        "Cell Biology: Mitosis produces two identical diploid cells. Meiosis produces four unique haploid gametes.",
        "Calculus: Derivative measures rate of change. Integral measures accumulation. Fundamental theorem links them.",
        "Probability: P(A∪B) = P(A) + P(B) - P(A∩B). For independent events: P(A∩B) = P(A)×P(B).",
    ]
    add_knowledge_batch(default_chunks, [{"source": "default"} for _ in default_chunks])
