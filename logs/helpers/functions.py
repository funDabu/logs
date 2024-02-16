import datetime


def strp_date(date: str, format: str) -> datetime.date:
    dt = datetime.datetime.strptime(date, format)
    return dt.date()