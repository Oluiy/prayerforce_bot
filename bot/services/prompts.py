"""Prompt templates sent to the AI model."""


def quiz_generation_prompt(notes: str, num_questions: int) -> str:
    return f"""
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
