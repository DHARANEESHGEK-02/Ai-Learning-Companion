"""
Evaluation Engine — rubric-based, semantic scoring via Gemini.
Supports subject-specific evaluation (CS, Physics, Chemistry, Biology, Maths).
"""
import os
import json
import re
import google.generativeai as genai

_configured = False

SUBJECT_PROMPTS = {
    "cs": "Focus on correctness of algorithms, time/space complexity, data structures, code logic.",
    "physics": "Check formulas, units, numerical accuracy, derivation steps, and physical reasoning.",
    "chemistry": "Verify chemical equations, balancing, reaction mechanisms, and nomenclature.",
    "biology": "Assess accuracy of biological terms, processes, diagrams described, and classifications.",
    "maths": "Check mathematical steps, formula application, calculation accuracy, and proof logic.",
    "default": "Evaluate content accuracy, completeness, and clarity of explanation.",
}


def _ensure_configured():
    global _configured
    if not _configured:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
            _configured = True


def evaluate_answer(
    question_text: str,
    model_answer: str,
    student_answer: str,
    max_marks: int,
    rubric: list | None = None,
    subject_area: str | None = None,
) -> dict:
    """Evaluate a student's answer using Gemini with rubric-based scoring."""
    _ensure_configured()

    if not student_answer or student_answer.strip() == "":
        return {
            "score": 0.0,
            "similarity_score": 0.0,
            "feedback": "No answer provided.",
            "missing_concepts": [],
            "strengths": [],
        }

    subject_hint = ""
    if subject_area:
        key = subject_area.lower()
        for k, v in SUBJECT_PROMPTS.items():
            if k in key:
                subject_hint = v
                break
        if not subject_hint:
            subject_hint = SUBJECT_PROMPTS["default"]

    rubric_text = ""
    if rubric:
        rubric_text = "Rubric criteria:\n" + "\n".join(
            f"- {r.get('criterion', '')}: {r.get('weight', 1)} marks — {r.get('description', '')}"
            for r in rubric
        )

    prompt = f"""You are an expert university examiner. Evaluate the student's answer objectively.

Question: {question_text}

Model Answer: {model_answer}

Student Answer: {student_answer}

Maximum Marks: {max_marks}
{rubric_text}
{subject_hint}

Evaluate based on:
1. Content accuracy and completeness
2. Understanding of concepts
3. Clarity and coherence
4. Adherence to rubric (if provided)

Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "score": <number between 0 and {max_marks}>,
  "similarity_score": <0.0-1.0 semantic similarity>,
  "feedback": "<2-3 sentence constructive feedback>",
  "missing_concepts": ["concept1", "concept2"],
  "strengths": ["strength1", "strength2"]
}}"""

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            score = float(result.get("score", 0))
            score = max(0.0, min(float(max_marks), score))
            return {
                "score": round(score, 2),
                "similarity_score": float(result.get("similarity_score", 0)),
                "feedback": str(result.get("feedback", "")),
                "missing_concepts": result.get("missing_concepts", []),
                "strengths": result.get("strengths", []),
            }
    except Exception as e:
        print(f"Evaluator error: {e}")

    # Fallback: simple keyword-based scoring
    return _fallback_evaluate(student_answer, model_answer, max_marks)


def _fallback_evaluate(student_answer: str, model_answer: str, max_marks: int) -> dict:
    """Simple keyword-overlap fallback when Gemini is unavailable."""
    student_words = set(student_answer.lower().split())
    model_words = set(model_answer.lower().split())
    overlap = len(student_words & model_words) / max(1, len(model_words))
    score = round(overlap * max_marks, 2)
    return {
        "score": min(score, float(max_marks)),
        "similarity_score": round(overlap, 3),
        "feedback": "Automated keyword-based evaluation. Manual review recommended.",
        "missing_concepts": [],
        "strengths": [],
    }


def detect_missing_concepts(student_answer: str, model_answer: str) -> list:
    """Identify key concepts from the model answer missing in the student answer."""
    _ensure_configured()
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""Compare these two answers and identify important concepts from the model answer that are missing or inadequately covered in the student answer.

Model Answer: {model_answer[:1000]}
Student Answer: {student_answer[:1000]}

Return ONLY a JSON array of missing concept strings (max 5):
["concept1", "concept2", ...]"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return []
