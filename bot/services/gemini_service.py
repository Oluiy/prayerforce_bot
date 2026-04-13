import google.generativeai as genai
import os
import json
import re

MAX_NOTES_CHARS = 50_000

class GeminiService:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
    def _clean_notes(self, notes: str) -> str:
        """Normalize notes for consistent model input."""
        # Normalize line endings
        notes = notes.replace('\r\n', '\n').replace('\r', '\n')

        # Preserve scripture references before cleaning (e.g. "Gal 5:19-21")
        # by protecting colons inside parentheses from period-space fix
        notes = notes.strip()

        # Collapse excessive blank lines
        notes = re.sub(r'\n{3,}', '\n\n', notes)

        # Collapse inline multiple spaces/tabs (but not leading indents)
        notes = re.sub(r'[ \t]{2,}', ' ', notes)

        # Fix missing space after period (but not scripture refs like 5:19)
        notes = re.sub(r'(?<=[a-z])\.(?=[A-Z])', '. ', notes)

        # Normalize bullet variants (–, —, *, •) to a standard dash
        notes = re.sub(r'^[\s]*(–|—|\*|•)\s+', '- ', notes, flags=re.MULTILINE)

        # Strip trailing whitespace per line
        notes = '\n'.join(line.rstrip() for line in notes.splitlines())

        return notes

    def generate_quiz_from_notes(self, notes: str, num_questions: int = 40) -> list[dict]:
        notes = self._clean_notes(notes)

        if not notes:
            raise ValueError("Notes are empty.")

        if len(notes) > MAX_NOTES_CHARS:
            raise ValueError(
                f"Notes too long ({len(notes)} chars). "
                f"Please trim to under {MAX_NOTES_CHARS} characters."
            )

        word_count = len(notes.split())
        max_reasonable = max(20, min(40, word_count // 80))
        num_questions = max_reasonable

        prompt = f"""
You are an expert quiz generator for teaching and study notes.

Your task is to generate exactly {num_questions} multiple-choice questions based ONLY on the notes below.

Rules:
- Every question must be directly and clearly answerable from the notes.
- Do not invent facts, references, or conclusions not stated in the notes.
- Questions should test understanding, not just surface recall.
- Scripture references in the notes (e.g. Galatians 5:16, Romans 8:9) are valid quiz material.
- Each question must have exactly 4 options.
- The correct_answer must exactly match one of the 4 options as a string.
- Distractors (wrong options) should be plausible but clearly wrong based on the notes.
- Return ONLY a valid JSON array. No markdown, no explanation, no preamble.

Format:
[
  {{
    "question": "string",
    "options": ["string", "string", "string", "string"],
    "correct_answer": "string"
  }}
]

Notes:
{notes}
"""

        response = None
        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text.strip()

            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            start = clean_text.find("[")
            end = clean_text.rfind("]") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON array found in model response.")

            questions = json.loads(clean_text[start:end])

            validated = []
            for q in questions:
                if (
                    isinstance(q.get("question"), str)
                    and isinstance(q.get("options"), list)
                    and len(q["options"]) == 4
                    and isinstance(q.get("correct_answer"), str)
                    and q["correct_answer"] in q["options"]
                ):
                    validated.append(q)

            if not validated:
                raise ValueError("Model returned no valid questions after validation.")

            return validated

        except Exception as e:
            raw = getattr(response, "text", "N/A") if response else "No response"
            raise RuntimeError(f"Quiz generation failed: {e} | Raw: {raw[:300]}")