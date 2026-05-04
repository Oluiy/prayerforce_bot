from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.prisma_connect import db
import datetime
import pytz


async def reset_weekly_leaderboard(context: ContextTypes.DEFAULT_TYPE):
    """
    Clears the leaderboard by ensuring old scores from previous weeks
    are no longer being surfaced.
    (Managed by get_leaderboard_content in quiz_user.py filtering for active quizzes).
    Separately, this job can perform actual data cleanup if desired, but
    filtering is safer for record keeping.
    """
    print("Weekly leaderboard reset period reached.")
    # No manual deletion needed if we use the filter 'isActive=True' in user queries.

async def open_weekly_quiz(context: ContextTypes.DEFAULT_TYPE):
    """
    Opens the weekly quiz on Sunday at 12:00 AM.
    """
    print("Running open_weekly_quiz job...")

    # Check if a Monthly Quiz is currently active
    active_monthly = await db.quiz.find_first(
        where={"type": "monthly", "isActive": True}
    )
    if active_monthly:
        print("Monthly quiz is active, skipping weekly quiz open.")
        return

    # Find the pending quiz created recently
    quiz = await db.quiz.find_first(
        where={
            "isActive": False,
            "isClosed": False,
            "type": "weekly",
        },
        order={"weekStart": "desc"},  # Get the latest created one
    )

    if quiz:
        print(f"Opening quiz {quiz.id}")
        await db.quiz.update(where={"id": quiz.id}, data={"isActive": True})

        # Broadcast to all users
        users = await db.user.find_many()
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.chatId,
                    text="📢 *The Weekly Family Quiz is now OPEN!* 📢\n\n"
                    "Test your knowledge of yesterday's meeting notes.\n"
                    "You have until Friday 10:00 PM to participate.\n\n"
                    "👉 Type /take_quiz to start!",
                    parse_mode="Markdown",
                )
            except Exception as e:
                print(f"Failed to send open quiz msg to {user.chatId}: {e}")


async def open_daily_quiz(context: ContextTypes.DEFAULT_TYPE):
    """
    Opens the daily quiz at a specified time.
    """
    print("Running open_daily_quiz job...")

    # Check if a Monthly Quiz is currently active
    active_monthly = await db.quiz.find_first(
        where={"type": "monthly", "isActive": True}
    )
    active_monthly = (
        await db.quiz.update(data={"isActive": False}, where={"id": active_monthly.id})
        if active_monthly
        else None
    )
    # if active_monthly:
    #     print("Monthly quiz is active, skipping daily quiz open.")
    #     return

    # Find the pending quiz created recently
    quiz = await db.quiz.find_first(
        where={
            "isActive": False,
            "isClosed": False,
            "type": "daily",
        },
        order={"createdAt": "desc"},  # Get the latest created one
    )

    if quiz:
        print(f"Opening quiz {quiz.id}")
        await db.quiz.update(where={"id": quiz.id}, data={"isActive": True})

        # Broadcast to all users
        users = await db.user.find_many()
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.chatId,
                    text="📢 *The Daily Family Quiz is now OPEN!* 📢\n\n"
                    "Test your knowledge of daily bible study.\n"
                    "You have until tonight 11:30PM to participate.\n\n"
                    "👉 Type /take_quiz to start!",
                    parse_mode="Markdown",
                )
            except Exception as e:
                print(f"Failed to send open quiz msg to {user.chatId}: {e}")


async def close_daily_quiz(context: ContextTypes.DEFAULT_TYPE):
    """
    Closes the daily quiz at 11:00 PM.
    Updates cumulative scores and prepares for next day.
    """
    print("Running close_daily_quiz job...")

    # 1. Find the currently active daily quiz
    active_quiz = await db.quiz.find_first(
        where={"isActive": True, "type": "daily"},
        order={"createdAt": "desc"},
        include={"userScores": {"include": {"user": True}}},
    )

    if not active_quiz:
        print("No active daily quiz found to close.")
        return

    # Fetch scores separately to guarantee ordering
    scores = await db.userscore.find_many(
        where={"quizId": active_quiz.id},
        include={"user": True},
        order={"score": "desc"},
    )

    # 2. Lock the Quiz so no more answers are accepted
    await db.quiz.update(
        where={"id": active_quiz.id}, data={"isActive": False, "isClosed": True}
    )
    print(f"Quiz '{active_quiz.id}' successfully closed.")

    # 3. Update cumulative scores for the current month
    current_date = datetime.datetime.now(datetime.timezone.utc)
    month_year = current_date.strftime("%Y-%m")

    for score_entry in scores:
        # Get or create cumulative record for this month
        cumulative = await db.dailyquizcumulative.find_unique(
            where={
                "userId_monthYear": {
                    "userId": score_entry.userId,
                    "monthYear": month_year
                }
            }
        )

        if cumulative:
            # Update existing cumulative record
            await db.dailyquizcumulative.update(
                where={"id": cumulative.id},
                data={
                    "cumulativeScore": cumulative.cumulativeScore + score_entry.score,
                    "timeTakenSeconds": cumulative.timeTakenSeconds + score_entry.timeTakenSeconds,
                    "totalQuizzesCompleted": cumulative.totalQuizzesCompleted + 1,
                    "lastUpdated": datetime.datetime.now(datetime.timezone.utc)
                }
            )
        else:
            # Create new cumulative record
            await db.dailyquizcumulative.create(
                data={
                    "userId": score_entry.userId,
                    "monthYear": month_year,
                    "cumulativeScore": score_entry.score,
                    "timeTakenSeconds": score_entry.timeTakenSeconds,
                    "totalQuizzesCompleted": 1
                }
            )
        print(f"Updated cumulative score for {score_entry.user.firstName}")

    # 4. Send daily result notification (optional: show today's top scorer)
    if scores:
        top_scorer = scores[0]
        result_text = f"🏆 *Today's Winner!* 🏆\n\n{top_scorer.user.firstName}: {top_scorer.score} points"
        
        users = await db.user.find_many()
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.chatId,
                    text=result_text,
                    parse_mode="Markdown",
                )
            except Exception as e:
                print(f"Failed to send result msg to {user.firstName}: {e}")


async def send_monthly_cumulative_leaderboard(context: ContextTypes.DEFAULT_TYPE):
    """
    Sends the cumulative monthly leaderboard on the last day at 11:30 PM.
    Shows top 15 users with their cumulative scores for the month.
    """
    today = datetime.datetime.now(datetime.timezone.utc)
    tomorrow = today + datetime.timedelta(days=1)

    # Check if tomorrow is the first day of next month => today is last day
    if tomorrow.month != today.month:
        print("Sending monthly cumulative leaderboard...")

        month_year = today.strftime("%Y-%m")

        # Fetch all users' cumulative scores for this month
        all_cumulative = await db.dailyquizcumulative.find_many(
            where={"monthYear": month_year},
            include={"user": True}
        )

        if not all_cumulative:
            print(f"No cumulative scores found for {month_year}")
            return

        # Sort by cumulative score (desc), then by time taken (asc) as tie-breaker
        cumulative_scores = sorted(
            all_cumulative,
            key=lambda entry: (-entry.cumulativeScore, entry.timeTakenSeconds if entry.timeTakenSeconds else 10**9)
        )[:15]  # Take top 15

        # Format leaderboard message
        leaderboard_msg = f"🎊 *MONTHLY BIBLE QUIZ CHAMPIONS!* 🎊\n\n"
        leaderboard_msg += f"🕯️ Final Standings for {today.strftime('%B %Y')}\n\n"

        medals = ["🥇", "🥈", "🥉"]
        for idx, entry in enumerate(cumulative_scores):
            medal = medals[idx] if idx < 3 else f"{idx + 1}."
            user_name = entry.user.firstName
            if entry.user.lastName:
                user_name += f" {entry.user.lastName}"
            
            time_text = f"{entry.timeTakenSeconds // 3600}h {(entry.timeTakenSeconds % 3600) // 60}m" if entry.timeTakenSeconds else "--"
            leaderboard_msg += (
                f"{medal} {user_name}\n"
                f"    📊 Score: {entry.cumulativeScore} pts | "
                f"📝 Quizzes: {entry.totalQuizzesCompleted} | "
                f"⏱️ Time: {time_text}\n\n"
            )

        # leaderboard_msg += "🎁 Winners will receive recognition at the next family meeting!\n"
        leaderboard_msg += "💪 Keep improving for next month's challenge!"

        # Broadcast to all users
        users = await db.user.find_many()
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.chatId,
                    text=leaderboard_msg,
                    parse_mode="Markdown",
                )
            except Exception as e:
                print(f"Failed to send monthly leaderboard to {user.firstName}: {e}")

        print(f"Monthly cumulative leaderboard sent for {month_year}")


async def close_weekly_quiz(context: ContextTypes.DEFAULT_TYPE):
    """
    Scheduled job to run every Friday.
    Tally scores, broadcast to the group, and lock the quiz.
    """
    print("Running close_weekly_quiz job...")

    # 1. Find the currently active weekly quiz
    active_quiz = await db.quiz.find_first(
        where={"isActive": True, "type": "weekly"},
        order={"weekStart": "desc"},
        include={"userScores": {"include": {"user": True}}},
    )

    if not active_quiz:
        print("No active quiz found to close.")
        return

    # Fetch scores separately to guarantee ordering
    scores = await db.userscore.find_many(
        where={"quizId": active_quiz.id},
        include={"user": True},
        order={"score": "desc"},
    )

    # 2. Lock the Quiz so no more answers are accepted
    await db.quiz.update(
        where={"id": active_quiz.id}, data={"isActive": False, "isClosed": True}
    )
    print(f"Quiz '{active_quiz.id}' successfully closed and leaderboard published.")

    # 3. Format the Teaser Message
    quiz_title = f"Weekly Quiz ({active_quiz.weekStart.strftime('%Y-%m-%d')})"
    teaser_text = "🏆 *Weekly Quiz Closed!* 🏆\n\nThe results are in! Tap the button below to see who won! 👇"

    keyboard = [
        [
            InlineKeyboardButton(
                f"View Results 📜", callback_data=f"view_leaderboard_{active_quiz.id}"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 4. Broadcast to all users
    users = await db.user.find_many()
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user.chatId,
                text=teaser_text,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"Failed to send leaderboard to {user.firstName}: {e}")


async def generate_monthly_recap(context: ContextTypes.DEFAULT_TYPE):
    """
    Checks if today is the last day of the month.
    If so, generates a Monthly Recap Quiz from past questions.
    """
    today = datetime.datetime.now()
    tomorrow = today + datetime.timedelta(days=1)

    # Check if tomorrow is the first day of next month => today is last day
    if tomorrow.month != today.month:
        print("Generating Monthly Recap Quiz...")

        # Close any active weekly quiz
        await db.quiz.update_many(
            where={"type": "weekly", "isActive": True},
            data={"isActive": False, "isClosed": True},
        )

        # 1. Fetch questions from past 4 weeks (weekly quizzes)
        # We find active or closed quizzes from last 30 days
        past_month_date = today - datetime.timedelta(days=30)

        past_quizzes = await db.quiz.find_many(
            where={"type": "weekly", "weekStart": {"gte": past_month_date}},
            include={"questions": {"include": {"options": True}}},
        )

        all_questions = []
        for q in past_quizzes:
            all_questions.extend(q.questions)

        if not all_questions:
            print("No questions found for monthly recap.")
            return

        import random

        # Monthly recap should target 40 questions since weekly generates 40
        sample_size = min(len(all_questions), 40)
        selected_questions = random.sample(all_questions, sample_size)

        monthly_quiz = await db.quiz.create(
            data={
                "weekStart": today,
                "isActive": True,
                "isClosed": False,
                "type": "monthly",
            }
        )

        for old_q in selected_questions:
            # Create new question copy
            new_q = await db.question.create(
                data={
                    "text": f"[Monthly Recap] {old_q.text}",
                    "quizId": monthly_quiz.id,
                }
            )

            for old_opt in old_q.options:
                await db.option.create(
                    data={
                        "text": old_opt.text,
                        "isCorrect": old_opt.isCorrect,
                        "questionId": new_q.id,
                    }
                )

        # 4. Broadcast
        users = await db.user.find_many()
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.chatId,
                    text=f"🌟 *MONTHLY MEGA-QUIZ RELEASED!* 🌟\n\n"
                    f"Test your retention of this month's topics!\n"
                    f"Contains {sample_size} questions from past weeks.\n\n"
                    f"👉 /take_quiz to start!",
                    parse_mode="Markdown",
                )
            except Exception as e:
                print(f"Failed to send monthly quiz msg: {e}")
