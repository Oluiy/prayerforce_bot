"""Admin flow: /generate_quiz -> send notes (text, .txt or PDF) -> AI builds a quiz."""
import logging

import messages
from services import quiz_service
from services.document_service import (
    EmptyPdfError,
    NotTextFileError,
    UnreadablePdfError,
    extract_text,
)
from services.gemini_service import GeminiService
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from utils.auth import is_primary_admin

from handlers.quiz_schedule import SCHEDULE_STATES, ask_quiz_type, cancel_scheduling

logger = logging.getLogger(__name__)

WAITING_NOTES = 1
gemini_service = GeminiService()


async def start_quiz_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_primary_admin(update.effective_user):
        await update.message.reply_text(messages.QUIZ_GEN_NOT_AUTHORIZED)
        return ConversationHandler.END

    await update.message.reply_text(messages.QUIZ_GEN_ASK_NOTES)
    return WAITING_NOTES


async def _read_notes(update: Update) -> str | None:
    """Return the notes text from a message, or None if it has no text or file."""
    document = update.message.document
    if document:
        file = await document.get_file()
        data = await file.download_as_bytearray()
        return extract_text(data, document.file_name, document.mime_type)
    return update.message.text or None


async def receive_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text(messages.QUIZ_GEN_PROCESSING)

    try:
        try:
            notes = await _read_notes(update)
        except EmptyPdfError:
            await status_msg.edit_text(messages.QUIZ_GEN_PDF_EMPTY)
            return WAITING_NOTES
        except UnreadablePdfError as e:
            logger.error("Error processing PDF: %s", e)
            await status_msg.edit_text(messages.QUIZ_GEN_PDF_FAILED)
            return WAITING_NOTES
        except NotTextFileError:
            await status_msg.edit_text(messages.QUIZ_GEN_BAD_TEXT_FILE)
            return WAITING_NOTES

        if notes is None:
            await status_msg.edit_text(messages.QUIZ_GEN_NO_NOTES)
            return WAITING_NOTES

        await status_msg.edit_text(messages.QUIZ_GEN_GENERATING)
        questions_data = gemini_service.generate_quiz_from_notes(notes)

        if not questions_data:
            await status_msg.edit_text(messages.QUIZ_GEN_NO_QUESTIONS)
            return ConversationHandler.END

        logger.debug("Quiz data: %s", questions_data)
        try:
            quiz = await quiz_service.save_generated_quiz(questions_data)
        except Exception as e:
            logger.error("Error saving quiz: %s", e)
            await status_msg.edit_text(messages.quiz_save_failed(e))
            return ConversationHandler.END

        await status_msg.delete()
        # The quiz is saved but has no schedule yet, so it can't open by
        # accident. Next the admin picks its type and its open/close times.
        return await ask_quiz_type(update.message, context, quiz.id, len(questions_data))

    except Exception:
        logger.exception("Unexpected error in receive_notes")
        await status_msg.edit_text(messages.QUIZ_GEN_UNEXPECTED_ERROR)

    return ConversationHandler.END


async def cancel_quiz_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Once a quiz exists, /cancel abandons scheduling rather than generation.
    if context.user_data.get("scheduling_quiz_id"):
        return await cancel_scheduling(update, context)
    await update.message.reply_text(messages.QUIZ_GEN_CANCELLED)
    return ConversationHandler.END


quiz_admin_handler = ConversationHandler(
    entry_points=[CommandHandler("generate_quiz", start_quiz_generation)],
    states={
        # ~COMMAND must apply to both, so /cancel reaches the fallback instead of being read as notes.
        WAITING_NOTES: [MessageHandler((filters.TEXT | filters.Document.ALL) & ~filters.COMMAND, receive_notes)],
        **SCHEDULE_STATES,
    },
    fallbacks=[CommandHandler("cancel", cancel_quiz_gen)],
)
