from calendar import monthrange
from datetime import date


QUICK_PRESETS = ["Semua", "Bulan Ini", "Bulan Terakhir", "3 Bulan", "6 Bulan", "12 Bulan"]


def _as_date(value):
    if isinstance(value, date):
        return value
    return value.date()


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def month_start(value: date) -> date:
    value = _as_date(value)
    return date(value.year, value.month, 1)


def month_end(value: date) -> date:
    value = _as_date(value)
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def clamp_period(start: date, end: date, min_date: date, max_date: date) -> tuple[date, date]:
    start = _as_date(start)
    end = _as_date(end)
    min_date = _as_date(min_date)
    max_date = _as_date(max_date)

    if start > end:
        start, end = end, start
    if min_date > max_date:
        min_date, max_date = max_date, min_date

    start = max(start, min_date)
    end = min(end, max_date)
    if start > end:
        start, end = min_date, max_date
    return start, end


def preset_period(preset: str, min_date: date, max_date: date) -> tuple[date, date]:
    min_date = _as_date(min_date)
    max_date = _as_date(max_date)
    today = max_date

    if preset == "Semua":
        start, end = min_date, max_date
    elif preset == "Bulan Ini":
        start, end = month_start(today), today
    elif preset == "Bulan Terakhir":
        previous_month = _add_months(month_start(today), -1)
        start, end = month_start(previous_month), month_end(previous_month)
    else:
        months = {"3 Bulan": 3, "6 Bulan": 6, "12 Bulan": 12}.get(preset)
        if months is None:
            start, end = min_date, max_date
        else:
            start, end = _add_months(today, -months), today

    return clamp_period(start, end, min_date, max_date)


def month_period(start_month: date, end_month: date) -> tuple[date, date]:
    start = month_start(start_month)
    end = month_end(end_month)
    if start > end:
        start, end = month_start(end_month), month_end(start_month)
    return start, end
