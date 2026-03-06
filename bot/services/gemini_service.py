import google.generativeai as genai
import os
import json
from datetime import datetime

class GeminiService:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def generate_quiz_from_notes(self, notes: str) -> list[dict]:
        """
        Generates 5 multiple choice questions from the provided notes.
        Returns a list of dictionaries with structure:
        {
            "question": "What is...",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B"
        }
        """
        prompt = f"""
        You are an expert quiz generator. Based on the following family meeting notes, generate 20 multiple-choice questions.
        The questions should be answerable from the text, but not too easy. They should test understanding.
        
        Notes:
        {notes}

        Return the result strictly as a JSON array of objects. Each object must have:
        - "question": string
        - "options": array of 4 strings
        - "correct_answer": string (must be one of the options)

        Do not include markdown formatting like ```json ... ```. Just the raw JSON string.
        """

        try:
            response = self.model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            questions = json.loads(text)
            return questions
        except Exception as e:
            print(f"Error generating quiz: {e}")
            return []

    def generate_monthly_quiz_prompt(self):
        # returns logic handled in python if we just pick random questions from DB
        pass
