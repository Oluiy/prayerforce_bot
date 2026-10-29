from datetime import datetime

def is_valid_date(date_string: str) -> bool:
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_entries(entries):
    valid_entries = []
    for entry in entries:
        if entry["ChatId"] and is_valid_date(entry["Birthday"]):
            valid_entries.append(entry)
    return valid_entries
