"""Провайдер модели и оценка доступности модели по её провайдерам."""

from utils import format_uptime

STABLE_UPTIME = 90.0

STATUS_AVAILABLE = "Доступна"
STATUS_UNSTABLE = "Нестабильна"
STATUS_DOWN = "Недоступна"
STATUS_NOT_FOUND = "Не найдена"


class Provider:
    """Компания, которая обслуживает модель в OpenRouter."""

    def __init__(
        self,
        name: str,
        status: int,
        uptime_5m: float | None = None,
        uptime_30m: float | None = None,
        uptime_1d: float | None = None,
    ) -> None:
        """Создать провайдера.

        status — код состояния OpenRouter: 0 — работает, меньше 0 — сбой.
        uptime_* — процент времени без сбоев за 5 минут, 30 минут и сутки.
        """
        self.name = name
        self.status = status
        self.uptime_5m = uptime_5m
        self.uptime_30m = uptime_30m
        self.uptime_1d = uptime_1d

    @property
    def is_working(self) -> bool:
        """Провайдер работает, если его статус равен 0."""
        return self.status == 0

    @classmethod
    def from_api(cls, data: dict) -> "Provider":
        """Создать провайдера из ответа OpenRouter."""
        return cls(
            name=data.get("provider_name") or "?",
            status=data.get("status", -1),
            uptime_5m=data.get("uptime_last_5m"),
            uptime_30m=data.get("uptime_last_30m"),
            uptime_1d=data.get("uptime_last_1d"),
        )

    def __str__(self) -> str:
        """Строка таблицы: провайдер, состояние, аптайм за 5 минут и сутки."""
        state = "работает" if self.is_working else "сбой"
        uptime_5m = format_uptime(self.uptime_5m)
        uptime_1d = format_uptime(self.uptime_1d)
        return f"{self.name[:24]:<25} {state:<11} {uptime_5m:<9} {uptime_1d}"


def count_working(providers: list[Provider]) -> int:
    """Сколько провайдеров модели сейчас работает."""
    return sum(1 for provider in providers if provider.is_working)


def best_uptime(providers: list[Provider], period: str) -> float | None:
    """Лучший аптайм среди работающих провайдеров.

    period — имя атрибута провайдера: uptime_5m, uptime_30m или uptime_1d.
    """
    values = [
        getattr(provider, period) for provider in providers
        if provider.is_working and getattr(provider, period) is not None
    ]
    return max(values, default=None)


def current_uptime(providers: list[Provider] | None) -> float | None:
    """Текущий аптайм модели.

    Берётся лучший аптайм за 5 минут, а если данных нет — за 30 минут.
    """
    if not providers:
        return None
    uptime = best_uptime(providers, "uptime_5m")
    if uptime is None:
        uptime = best_uptime(providers, "uptime_30m")
    return uptime


def get_model_status(providers: list[Provider] | None) -> str:
    """Определить статус модели по списку её провайдеров."""
    if not providers:
        return STATUS_NOT_FOUND
    if count_working(providers) == 0:
        return STATUS_DOWN

    uptime = current_uptime(providers)
    if uptime is None or uptime >= STABLE_UPTIME:
        return STATUS_AVAILABLE
    return STATUS_UNSTABLE
