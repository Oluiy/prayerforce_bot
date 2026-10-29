"""Generates quiz questions from notes using Google Gemini."""
import json
import re

from google import genai

from config import settings
from config.constants import (
    GEMINI_MODEL,
    MAX_GENERATED_QUESTIONS,
    MAX_NOTES_CHARS,
    MIN_GENERATED_QUESTIONS,
    WORDS_PER_GENERATED_QUESTION,
)
from services.prompts import quiz_generation_prompt


class GeminiService:
    def __init__(self, api_key: str | None = None, model_name: str = GEMINI_MODEL):
        api_key = api_key or settings.google_api_key
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    @staticmethod
    def _clean_notes(notes: str) -> str:
        """Normalize notes for consistent model input."""
        # Normalize line endings
        notes = notes.replace('\r\n', '\n').replace('\r', '\n')
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

    @staticmethod
    def _question_count(notes: str) -> int:
        """Scale the number of questions with the length of the notes."""
        word_count = len(notes.split())
        return max(
            MIN_GENERATED_QUESTIONS,
            min(MAX_GENERATED_QUESTIONS, word_count // WORDS_PER_GENERATED_QUESTION),
        )

    @staticmethod
    def _parse_questions(raw_text: str) -> list[dict]:
        """Pull the JSON array out of the model reply and keep only well-formed questions."""
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        start = clean_text.find("[")
        end = clean_text.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON array found in model response.")

        questions = json.loads(clean_text[start:end])

        validated = [
            q for q in questions
            if isinstance(q.get("question"), str)
            and isinstance(q.get("options"), list)
            and len(q["options"]) == 4
            and isinstance(q.get("correct_answer"), str)
            and q["correct_answer"] in q["options"]
        ]
        if not validated:
            raise ValueError("Model returned no valid questions after validation.")
        return validated

    def generate_quiz_from_notes(self, notes: str) -> list[dict]:
        notes = self._clean_notes(notes)

        if not notes:
            raise ValueError("Notes are empty.")

        if len(notes) > MAX_NOTES_CHARS:
            raise ValueError(
                f"Notes too long ({len(notes)} chars). "
                f"Please trim to under {MAX_NOTES_CHARS} characters."
            )

        prompt = quiz_generation_prompt(notes, self._question_count(notes))

        response = None
        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return self._parse_questions(response.text.strip())
        except Exception as e:
            raw = getattr(response, "text", "N/A") if response else "No response"
            raise RuntimeError(f"Quiz generation failed: {e} | Raw: {raw[:300]}")
