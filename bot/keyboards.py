"""Inline keyboards. Kept apart from handlers so jobs can reuse them."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import messages

LEADERBOARD_CALLBACK = "view_leaderboard"


def view_results_markup(button_text: str, quiz_id=None) -> InlineKeyboardMarkup:
    """Button that opens the leaderboard, for a specific quiz if given."""
    data = f"{LEADERBOARD_CALLBACK}_{quiz_id}" if quiz_id else LEADERBOARD_CALLBACK
    return InlineKeyboardMarkup([[InlineKeyboardButton(button_text, callback_data=data)]])


def quiz_type_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Daily", callback_data="qtype_daily")],
            [InlineKeyboardButton("Weekly", callback_data="qtype_weekly")],
            [InlineKeyboardButton(messages.SCHEDULE_CANCEL_BUTTON, callback_data="sched_cancel")],
        ]
    )


def schedule_markup(presets) -> InlineKeyboardMarkup:
    """`presets` is a list of (label, callback_data)."""
    rows = [[InlineKeyboardButton(label, callback_data=data)] for label, data in presets]
    rows.append([InlineKeyboardButton(messages.SCHEDULE_CUSTOM_BUTTON, callback_data="sched_custom")])
    rows.append([InlineKeyboardButton(messages.SCHEDULE_CANCEL_BUTTON, callback_data="sched_cancel")])
    return InlineKeyboardMarkup(rows)


def end_quiz_markup(quizzes) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(messages.end_quiz_option(quiz), callback_data=f"endquiz_{quiz.id}")]
        for quiz in quizzes
    ]
    rows.append([InlineKeyboardButton(messages.SCHEDULE_CANCEL_BUTTON, callback_data="endquiz_cancel")])
    return InlineKeyboardMarkup(rows)


def settings_markup(values) -> InlineKeyboardMarkup:
    """`values` is a list of (SettingDef, current_value)."""
    rows = [
        [InlineKeyboardButton(messages.settings_option(d, current), callback_data=f"setting_{d.key}")]
        for d, current in values
    ]
    rows.append([InlineKeyboardButton(messages.SETTINGS_CANCEL_BUTTON, callback_data="setting_done")])
    return InlineKeyboardMarkup(rows)
