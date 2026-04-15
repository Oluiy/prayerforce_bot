from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from services.gemini_service import GeminiService
from database.prisma_connect import db
import datetime
import os
import io
import pypdf

from dotenv import load_dotenv

# Ensure env vars are loaded
load_dotenv()

# Load admin IDs from env (comma separated list)
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_ID_LEGACY = os.getenv("ADMIN_ID", "")

# robust parsing into a set of integers
ADMIN_IDS = set()

# Combine both strings first
all_ids_str = f"{ADMIN_IDS_STR},{ADMIN_ID_LEGACY}"

for id_part in all_ids_str.split(","):
    clean_id = id_part.strip()
    if clean_id.isdigit():
        ADMIN_IDS.add(int(clean_id))


WAITING_NOTES = 1
gemini_service = GeminiService()

async def start_quiz_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Security check: only 1 explicit admin
    user = update.effective_user
    
    # We restrict this to just the first admin in the set (the primary admin)
    primary_admin_id = list(ADMIN_IDS)[0] if ADMIN_IDS else None
    
    # Check against integer ID directly
    if not user or user.id != primary_admin_id:
        await update.message.reply_text(f"Only the primary admin is authorized to regenerate quizzes.")
        return ConversationHandler.END

    await update.message.reply_text("Please send the meeting notes for this week's quiz generation.")
    return WAITING_NOTES

async def receive_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("Processing notes... Please wait.")
    notes = ""

    try:
        if update.message.document:
            # Handle file upload
            file = await update.message.document.get_file()
            byte_array = await file.download_as_bytearray()
            
            # Check for PDF
            file_name = update.message.document.file_name.lower()
            mime_type = update.message.document.mime_type
            
            if file_name.endswith('.pdf') or (mime_type and 'pdf' in mime_type):
                try:
                    pdf_file = io.BytesIO(byte_array)
                    reader = pypdf.PdfReader(pdf_file)
                    extracted_text = []
                    for page in reader.pages:
                        extracted_text.append(page.extract_text() or "")
                    notes = "\n".join(extracted_text)
                    if not notes.strip():
                         await status_msg.edit_text("Error: The PDF file seems to be empty or contains scanned images without text.")
                         return WAITING_NOTES
                except Exception as e:
                    print(f"Error processing PDF: {e}")
                    await status_msg.edit_text("Error: Failed to process the PDF file.")
                    return WAITING_NOTES
            else:
                # Assume Text File
                try:
                    notes = byte_array.decode("utf-8")
                except UnicodeDecodeError:
                    await status_msg.edit_text("Error: The file must be a text file (UTF-8 encoded) or a PDF. Please try again or paste the text directly.")
                    return WAITING_NOTES
        elif update.message.text:
            # Handle direct text
            notes = update.message.text
        else:
            await status_msg.edit_text("Please send the notes either as text or a PDF/text file.")
            return WAITING_NOTES

        await status_msg.edit_text("Generating quiz questions with AI... Please wait.")
        
        # Generate questions
        questions_data = gemini_service.generate_quiz_from_notes(notes)
        
        if not questions_data:
            await status_msg.edit_text("Failed to generate questions. Please try again with clearer notes.")
            return ConversationHandler.END

        # Save to DB (Manual transaction for stability)
        print(f"DEBUG: Quiz Data: {questions_data}")
        
        try:
            # Create a new weekly quiz (initially inactive, to be opened on Sunday)
            quiz = await db.quiz.create(
                data={
                    "weekStart": datetime.datetime.now(),
                    "isActive": True, # Opens Sunday
                    "isClosed": False,
                    "type": "weekly"
                }
            )

            try:
                for q in questions_data:
                    # Validate keys
                    if "question" not in q or "options" not in q or "correct_answer" not in q:
                        raise ValueError("Invalid question format from AI")

                    question = await db.question.create(
                        data={
                            "text": q["question"],
                            "quizId": quiz.id
                        }
                    )
                    
                    for index, opt_text in enumerate(q["options"]):
                        is_correct = (opt_text == q["correct_answer"])
                        await db.option.create(
                            data={
                                "text": opt_text,
                                "isCorrect": is_correct,
                                "questionId": question.id
                            }
                        )
            except Exception as e:
                # Manual Rollback
                print(f"Error inserting questions: {e}. Rolling back quiz {quiz.id}")
                await db.quiz.delete(where={"id": quiz.id})
                raise e

        except Exception as e:
            print(f"Error saving quiz: {e}")
            await status_msg.edit_text(f"An error occurred while saving the quiz: {str(e)}")
            return ConversationHandler.END

        await status_msg.edit_text(f"✅ Quiz generated successfully with {len(questions_data)} questions! It is scheduled to open on Sunday.")

    except Exception as e:
        print(f"Unexpected error in receive_notes: {e}")
        await status_msg.edit_text("An unexpected error occurred. Please try again.")
        return ConversationHandler.END

    return ConversationHandler.END

async def cancel_quiz_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Quiz generation cancelled.")
    return ConversationHandler.END

quiz_admin_handler = ConversationHandler(
    entry_points=[CommandHandler("generate_quiz", start_quiz_generation)],
    states={
        WAITING_NOTES: [MessageHandler(filters.TEXT | filters.Document.ALL & ~filters.COMMAND, receive_notes)],
    },
    fallbacks=[CommandHandler("cancel", cancel_quiz_gen)]
)
