import datetime


def is_last_day_of_month(day: datetime.datetime) -> bool:
    return (day + datetime.timedelta(days=1)).month != day.month


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)
