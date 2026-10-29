"""All user-facing text the bot sends.

Keep wording changes here so handlers and jobs only deal with logic.
"""
from config.constants import QUESTION_TIME_LIMIT_SECONDS
from utils.formatting import format_duration, format_hours_minutes, full_name, rank_label

# --- Command menu ------------------------------------------------------------
BOT_COMMANDS = [
    ("start", "Get to know Tefillah"),
    ("announcement", "To get all necessary annoucement"),
    ("take_quiz", "Take the current active quiz"),
    ("history", "Want to know the history of Prayer Force?🙂 you can 'use the command'"),
    ("meetings", "Pre-service and Post-service"),
    ("merch", "Want to purchase shirt or food or both?"),
    ("leaderboard", "View quiz leaderboard"),
    ("prayer_request", "Send a private prayer request"),
    ("share_testimony", "Share your testimony with the family"),
]


# --- Welcome & info ----------------------------------------------------------
def welcome(first_name: str) -> str:
    return (
        f"Hi {first_name}! I'm Tefillah, the Prayer Force bot\n\n"
        "I’m here to help you stay connected with the Prayer Force family. Through me, you can get helpful information, learn new things, and even have a little fun along the way.\n\n"
        "You can also share your testimonies, because every testimony reminds us of what God is doing among us. If you need prayers, you can send in a prayer request anonymously, and the family will stand with you in prayer.\n\n"
        "Take a moment to explore. There’s something here for you.\n\n"
        "Remember Prayer Force loves you but Jesus loves you more!!!\n"
        "Don't forget to visit the office today🌚.\n\n"
        "Welcome again❤️"
    )


ANNOUNCEMENT = (
    "Get Edified🥰🙏 !!!\n\n\n"
    "We’ll be going before the Lord by 5:30pm today with hearts ready to seek Him. "
    "Tell a Prayer Force member to tell a Prayer Force member to tell another Prayer Force member "
    "that today's meeting is not one you want to miss."
)

HISTORY = (
    "Prayer Force was founded in 2020 as a spiritual movement dedicated to prayer and intercession. "
    "Since then, we've grown into a community of believers committed to seeking God's presence through prayer."
)

MEETINGS = (
    "Our Sunday meetings schedule:\n\n"
    "1. Pre-service Prayer: 7:00 AM - 7:30 AM\n"
    "2. Post-service Prayer: 8:05 AM - 8:35 AM"
)

MERCH = (
    "To purchase Prayer Force merchandise:\n\n"
    "1. Prayer Force T-shirt - ₦5,000\n"
    "2. Prayer Journal - ₦3,500\n\n"
    "Please use the /donate command to make payment and specify what you're purchasing in the description."
)

OPERATION_CANCELLED = "Operation cancelled."
COMMAND_MENU_REFRESHED = "Command menu refreshed."

# --- Forms -------------------------------------------------------------------
PRAYER_REQUEST_BUTTON = "Let us pray with you"
PRAYER_REQUEST_PROMPT = (
    "Do you have a prayer request? Click the button below to share it with our "
    "prayer team, and we'll pray with you! 🙏"
)
TESTIMONY_BUTTON = "Share your testimony"
TESTIMONY_PROMPT = "Hello beloved, \nWe’d love to celebrate what God is doing in your life 🤍"

# --- Broadcast (admin) -------------------------------------------------------
BROADCAST_NOT_AUTHORIZED = "You are not authorized to broadcast messages."
BROADCAST_ASK_MESSAGE = (
    "Please send the message you want to broadcast to all users.\n\n"
    "Send /cancel to abort."
)
BROADCAST_IN_PROGRESS = "Broadcasting... Please wait."
BROADCAST_CANCELLED = "Broadcast cancelled."


def broadcast_complete(sent: int, failed: int) -> str:
    return (
        f"✅ Broadcast Complete!\n\n"
        f"Successfully sent to: {sent} users.\n"
        f"Failed to send to: {failed} users."
    )


# --- Quiz generation (admin) -------------------------------------------------
QUIZ_GEN_NOT_AUTHORIZED = "Only the primary admin is authorized to regenerate quizzes."
QUIZ_GEN_ASK_NOTES = "Please send the meeting notes for this week's quiz generation."
QUIZ_GEN_PROCESSING = "Processing notes... Please wait."
QUIZ_GEN_PDF_EMPTY = "Error: The PDF file seems to be empty or contains scanned images without text."
QUIZ_GEN_PDF_FAILED = "Error: Failed to process the PDF file."
QUIZ_GEN_BAD_TEXT_FILE = (
    "Error: The file must be a text file (UTF-8 encoded) or a PDF. "
    "Please try again or paste the text directly."
)
QUIZ_GEN_NO_NOTES = "Please send the notes either as text or a PDF/text file."
QUIZ_GEN_GENERATING = "Generating quiz questions with AI... Please wait."
QUIZ_GEN_NO_QUESTIONS = "Failed to generate questions. Please try again with clearer notes."
QUIZ_GEN_UNEXPECTED_ERROR = "An unexpected error occurred. Please try again."
QUIZ_GEN_CANCELLED = "Quiz generation cancelled."


def quiz_save_failed(error: Exception) -> str:
    return f"An error occurred while saving the quiz: {error}"


def quiz_generated(question_count: int) -> str:
    return f"✅ Quiz generated successfully with {question_count} questions! It is scheduled to open on Sunday."


# --- Taking a quiz -----------------------------------------------------------
NO_ACTIVE_QUIZ = "There is no active quiz at the moment. Check back on Sunday!"
QUIZ_HAS_NO_QUESTIONS = "The quiz seems to have no questions. Please contact admin."
QUIZ_CANCELLED = "Quiz cancelled."


def already_taken(score: int) -> str:
    return f"You have already taken this quiz! You scored {score}."


def quiz_starting(quiz_type: str, question_count: int) -> str:
    return f"Starting the {quiz_type} quiz! You'll be asked {question_count} questions. Good luck!"


def question_header(index: int, total: int, text: str) -> str:
    return f"Question {index + 1}/{total}:\n{text}"


def with_full_timer(base_text: str) -> str:
    return f"{base_text}\n\n⏱️ You have {QUESTION_TIME_LIMIT_SECONDS} seconds to answer!"


def with_time_left(base_text: str, seconds_left: int) -> str:
    return f"{base_text}\n\n⏱️ You have {seconds_left} seconds left!"


def times_up(base_text: str) -> str:
    return f"{base_text}\n\n⏰ Time's up!"


def answer_correct(question_text: str, answer_text: str) -> str:
    return f"{question_text}\n\n✅ Correct! ({answer_text})"


def answer_wrong(question_text: str, correct_text: str | None) -> str:
    return f"{question_text}\n\n❌ Wrong! The correct answer was: {correct_text or 'Unknown'}"


def quiz_finished(score: int, total: int, elapsed_seconds: int) -> str:
    return (
        f"Quiz finished! 🏆\n"
        f"Your final score: {score}/{total}\n"
        f"⏱️ Total time: {format_duration(elapsed_seconds)}"
    )


# --- Leaderboards ------------------------------------------------------------
LEADERBOARD_EMPTY = (
    "🏆 *Leaderboard Update*\n\nNo active quiz leaderboard currently. "
    "New quiz results will appear after Sunday 12:00 AM!"
)
LEADERBOARD_TEASER = "🏆 *Leaderboard Update!* 🏆\n\nTap the button below to see who's leading! 👇"
LEADERBOARD_DETAILS_BUTTON = "View Details 📜"
LEADERBOARD_UNAVAILABLE = "Leaderboard unavailable"
LEADERBOARD_POPUP_HEADER = "🎉 Current Standings! 🎉\n\n"
LEADERBOARD_POPUP_EMPTY = "No scores yet!"


def leaderboard_line(rank: int, entry) -> str:
    time_text = format_duration(entry.timeTakenSeconds or 0)
    return f"{rank_label(rank)} {full_name(entry.user)}: {entry.score} pts ({time_text})"


def leaderboard(title_suffix: str, entries) -> str:
    lines = [leaderboard_line(rank, entry) for rank, entry in enumerate(entries)]
    return (
        f"🏆 Leaderboard {title_suffix} 🏆\n\n"
        + "".join(f"{line}\n" for line in lines)
        + "\n🎁 The winner gets their gift at the next family meeting!"
    )


def leaderboard_popup(entries) -> str:
    """Short top-3 summary shown in the Telegram alert popup."""
    lines = [leaderboard_line(rank, entry) for rank, entry in enumerate(entries[:3])]
    if not lines:
        return LEADERBOARD_POPUP_HEADER + LEADERBOARD_POPUP_EMPTY
    return LEADERBOARD_POPUP_HEADER + "".join(f"{line}\n" for line in lines)


def monthly_leaderboard(month_label: str, entries) -> str:
    text = "🎊 *MONTHLY BIBLE QUIZ CHAMPIONS!* 🎊\n\n"
    text += f"🕯️ Final Standings for {month_label}\n\n"
    for rank, entry in enumerate(entries):
        time_text = format_hours_minutes(entry.timeTakenSeconds) if entry.timeTakenSeconds else "--"
        text += (
            f"{rank_label(rank)} {full_name(entry.user)}\n"
            f"    📊 Score: {entry.cumulativeScore} pts | "
            f"📝 Quizzes: {entry.totalQuizzesCompleted} | "
            f"⏱️ Time: {time_text}\n\n"
        )
    text += "💪 Keep improving for next month's challenge!"
    return text


# --- Scheduled quiz announcements --------------------------------------------
WEEKLY_QUIZ_OPEN = (
    "📢 *The Weekly Family Quiz is now OPEN!* 📢\n\n"
    "Test your knowledge of yesterday's meeting notes.\n"
    "You have until Friday 10:00 PM to participate.\n\n"
    "👉 Type /take_quiz to start!"
)

DAILY_QUIZ_OPEN = (
    "📢 *The Daily Family Quiz is now OPEN!* 📢\n\n"
    "Test your knowledge of daily bible study.\n"
    "You have until tonight 11:30PM to participate.\n\n"
    "👉 Type /take_quiz to start!"
)

WEEKLY_QUIZ_CLOSED = "🏆 *Weekly Quiz Closed!* 🏆\n\nThe results are in! Tap the button below to see who won! 👇"
VIEW_RESULTS_BUTTON = "View Results 📜"


def daily_winner(first_name: str, score: int) -> str:
    return f"🏆 *Today's Winner!* 🏆\n\n{first_name}: {score} points"


def monthly_recap_released(question_count: int) -> str:
    return (
        f"🌟 *MONTHLY MEGA-QUIZ RELEASED!* 🌟\n\n"
        f"Test your retention of this month's topics!\n"
        f"Contains {question_count} questions from past weeks.\n\n"
        f"👉 /take_quiz to start!"
    )


# --- Birthdays ---------------------------------------------------------------
def birthday(first_name: str, mate_names: list[str]) -> str:
    text = f"🎉 Happy Birthday, {first_name}!"
    if mate_names:
        text += f"\nYou share your birthday with: {', '.join(mate_names)}!"
    return text
