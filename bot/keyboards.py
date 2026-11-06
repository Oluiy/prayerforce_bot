"""Inline keyboards. Kept apart from handlers so jobs can reuse them."""
import messages
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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


def settings_markup(values) -> InlineKeyboardMarkup:
    """`values` is a list of (SettingDef, current_value)."""
    rows = [
        [InlineKeyboardButton(messages.settings_option(d, current), callback_data=f"setting_{d.key}")]
        for d, current in values
    ]
    rows.append([InlineKeyboardButton(messages.SETTINGS_CANCEL_BUTTON, callback_data="setting_done")])
    return InlineKeyboardMarkup(rows)


def member_pick_markup(choices) -> InlineKeyboardMarkup:
    """`choices` is a list of (chat_id, label)."""
    rows = [
        [InlineKeyboardButton(label, callback_data=f"pickadmin_{chat_id}")]
        for chat_id, label in choices
    ]
    rows.append([InlineKeyboardButton(messages.SCHEDULE_CANCEL_BUTTON, callback_data="pickadmin_cancel")])
    return InlineKeyboardMarkup(rows)


def duration_markup(presets) -> InlineKeyboardMarkup:
    """`presets` is a list of (label, minutes)."""
    rows = [
        [InlineKeyboardButton(label, callback_data=f"dur_{minutes}")] for label, minutes in presets
    ]
    rows.append([InlineKeyboardButton(messages.DURATION_CUSTOM_BUTTON, callback_data="dur_custom")])
    rows.append([InlineKeyboardButton(messages.SCHEDULE_CANCEL_BUTTON, callback_data="dur_cancel")])
    return InlineKeyboardMarkup(rows)


def revoke_admin_markup(entries) -> InlineKeyboardMarkup:
    """`entries` is a list of (telegram_id, label)."""
    rows = [
        [InlineKeyboardButton(label, callback_data=f"revokeadmin_{telegram_id}")]
        for telegram_id, label in entries
    ]
    rows.append([InlineKeyboardButton(messages.SCHEDULE_CANCEL_BUTTON, callback_data="revokeadmin_cancel")])
    return InlineKeyboardMarkup(rows)


# --- Love letters ------------------------------------------------------------
def love_letters_hub_markup(letter_count: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("Send to everyone", callback_data="ll_send_all")],
        [InlineKeyboardButton("Send to one member", callback_data="ll_send_one")],
        [InlineKeyboardButton("Add a letter", callback_data="ll_add")],
    ]
    if letter_count:
        rows.append([InlineKeyboardButton("See this week's letters", callback_data="ll_list")])
    rows.append([InlineKeyboardButton("Close", callback_data="ll_cancel")])
    return InlineKeyboardMarkup(rows)


def love_letters_confirm_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Yes, send them", callback_data="ll_go_all")],
            [InlineKeyboardButton("Cancel", callback_data="ll_cancel")],
        ]
    )


def love_letters_back_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Back", callback_data="ll_home")]]
    )


def love_letters_list_markup(letters) -> InlineKeyboardMarkup:
    """`letters` in the same order as the text, so "Remove 1" matches item 1."""
    rows = [
        [InlineKeyboardButton(f"Remove {index}", callback_data=f"lldel_{letter.id}")]
        for index, letter in enumerate(letters, start=1)
    ]
    rows.append([InlineKeyboardButton("Back", callback_data="ll_home")])
    return InlineKeyboardMarkup(rows)


def love_letters_delete_confirm_markup(letter_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Yes, remove it", callback_data=f"lldelok_{letter_id}")],
            [InlineKeyboardButton("Keep it", callback_data="ll_list")],
        ]
    )


def love_letters_member_markup(choices) -> InlineKeyboardMarkup:
    """`choices` is a list of (chat_id, label)."""
    rows = [
        [InlineKeyboardButton(label, callback_data=f"llmem_{chat_id}")]
        for chat_id, label in choices
    ]
    rows.append([InlineKeyboardButton("Cancel", callback_data="ll_cancel")])
    return InlineKeyboardMarkup(rows)


def love_letters_pick_markup(letters) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(messages.letter_option(i, letter.body), callback_data=f"llletter_{letter.id}")]
        for i, letter in enumerate(letters, start=1)
    ]
    rows.append([InlineKeyboardButton(messages.LOVE_LETTERS_RANDOM_BUTTON, callback_data="ll_random")])
    rows.append([InlineKeyboardButton("Cancel", callback_data="ll_cancel")])
    return InlineKeyboardMarkup(rows)
