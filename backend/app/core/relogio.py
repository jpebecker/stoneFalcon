from datetime import datetime, timedelta, timezone

FUSO = timezone(timedelta(hours=-3))   # horário de Brasília


def agora() -> datetime:
    return datetime.now(FUSO).replace(microsecond=0)
