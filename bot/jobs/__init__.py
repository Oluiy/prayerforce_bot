from telegram.ext import JobQueue

from config import constants as c
from jobs.birthday_jobs import send_birthday_messages
from jobs.quiz_jobs import (
    close_daily_quiz,
    close_weekly_quiz,
    generate_monthly_recap,
    open_daily_quiz,
    open_weekly_quiz,
    send_monthly_cumulative_leaderboard,
)


def schedule_jobs(job_queue: JobQueue):
    """Register all recurring jobs. Times and days live in config/constants.py."""
    job_queue.run_daily(open_weekly_quiz, time=c.WEEKLY_QUIZ_OPEN_TIME, days=c.WEEKLY_QUIZ_OPEN_DAYS)
    job_queue.run_daily(close_weekly_quiz, time=c.WEEKLY_QUIZ_CLOSE_TIME, days=c.WEEKLY_QUIZ_CLOSE_DAYS)

    job_queue.run_daily(open_daily_quiz, time=c.DAILY_QUIZ_OPEN_TIME)
    job_queue.run_daily(close_daily_quiz, time=c.DAILY_QUIZ_CLOSE_TIME)

    # These run every day; the jobs themselves only act on the last day of the month.
    job_queue.run_daily(send_monthly_cumulative_leaderboard, time=c.MONTHLY_LEADERBOARD_TIME)
    job_queue.run_daily(generate_monthly_recap, time=c.MONTHLY_RECAP_TIME)

    job_queue.run_daily(send_birthday_messages, time=c.BIRTHDAY_MESSAGE_TIME)
