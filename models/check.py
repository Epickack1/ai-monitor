"""Результат проверки модели, история проверок и статистика."""

from collections.abc import Iterator
from datetime import datetime

from utils import format_uptime

from .ai_model import AIModel
from .provider import (
    STATUS_AVAILABLE,
    Provider,
    current_uptime,
    get_model_status,
)

MAX_RECORDS = 1000
TIME_FORMAT = "%Y-%m-%d %H:%M"


class CheckResult:
    """Результат одной проверки доступности модели."""

    def __init__(
        self,
        model: AIModel,
        status: str,
        uptime: float | None,
        checked_at: str | None = None,
        providers: list[Provider] | None = None,
    ) -> None:
        """Создать результат проверки.

        model — объект проверенной модели, providers — провайдеры на момент
        проверки (в JSON не сохраняются). Если время не передано,
        берётся текущее.
        """
        self.model = model
        self.status = status
        self.uptime = uptime
        self.checked_at = checked_at or datetime.now().strftime(TIME_FORMAT)
        self.providers = providers or []

    @property
    def is_available(self) -> bool:
        """Была ли модель доступна при проверке."""
        return self.status == STATUS_AVAILABLE

    @classmethod
    def from_providers(
        cls, model: AIModel, providers: list[Provider] | None
    ) -> "CheckResult":
        """Оценить доступность модели по её провайдерам."""
        return cls(
            model,
            get_model_status(providers),
            current_uptime(providers),
            providers=providers,
        )

    @classmethod
    def from_data(cls, data: dict, model: AIModel) -> "CheckResult":
        """Восстановить результат из записи истории и объекта модели."""
        return cls(model, data["status"], data["uptime"], data["checked_at"])

    def to_data(self) -> dict:
        """Данные для сохранения в JSON: вместо объекта модели — её id."""
        return {
            "model_id": self.model.id,
            "status": self.status,
            "uptime": self.uptime,
            "checked_at": self.checked_at,
        }

    def __str__(self) -> str:
        """Время, статус и аптайм проверки."""
        uptime = format_uptime(self.uptime)
        return f"{self.checked_at}  {self.status:<12} {uptime}"


class ModelStats:
    """Статистика проверок одной модели."""

    def __init__(self, model: AIModel) -> None:
        """Создать пустую статистику модели."""
        self.model = model
        self.checks = 0
        self.available = 0
        self.uptimes: list[float] = []

    def add(self, result: CheckResult) -> None:
        """Учесть результат очередной проверки."""
        self.checks += 1
        if result.is_available:
            self.available += 1
        if result.uptime is not None:
            self.uptimes.append(result.uptime)

    @property
    def percent(self) -> float:
        """Доля проверок, в которых модель была доступна, в процентах."""
        if self.checks == 0:
            return 0.0
        return self.available / self.checks * 100

    @property
    def avg_uptime(self) -> float | None:
        """Средний аптайм по проверкам, где он был известен."""
        if not self.uptimes:
            return None
        return sum(self.uptimes) / len(self.uptimes)

    def __str__(self) -> str:
        """Строка таблицы статистики."""
        percent = f"{self.percent:.0f}%"
        avg_uptime = format_uptime(self.avg_uptime)
        return (
            f"{self.model.id[:36]:<36} {self.checks:>8}  {percent:>8}"
            f"  {avg_uptime:>10}"
        )


def add_result(
    history: list[CheckResult], result: CheckResult, limit: int = MAX_RECORDS
) -> None:
    """Добавить результат в историю.

    Чтобы файл не рос бесконечно, самые старые записи сверх limit удаляются.
    """
    history.append(result)
    if len(history) > limit:
        del history[:len(history) - limit]


def iter_results(
    history: list[CheckResult], model_id: str
) -> Iterator[CheckResult]:
    """Генератор: по одной выдаёт проверки указанной модели."""
    for result in history:
        if result.model.id == model_id:
            yield result


def last_result(
    history: list[CheckResult], model_id: str
) -> CheckResult | None:
    """Последняя проверка модели или None, если проверок не было."""
    last = None
    for result in iter_results(history, model_id):
        last = result
    return last


def collect_stats(history: list[CheckResult]) -> list[ModelStats]:
    """Статистика по всем моделям из истории.

    Модели упорядочены от самой стабильной к самой проблемной:
    по доле успешных проверок, затем по среднему аптайму.
    """
    stats: dict[str, ModelStats] = {}
    for result in history:
        if result.model.id not in stats:
            stats[result.model.id] = ModelStats(result.model)
        stats[result.model.id].add(result)

    ordered = sorted(stats.values(), key=lambda item: item.model.id)
    return sorted(
        ordered,
        key=lambda item: (item.percent, item.avg_uptime or 0.0),
        reverse=True,
    )


def sort_models(
    models: list[AIModel],
    history: list[CheckResult],
    by_uptime: bool = False,
) -> list[AIModel]:
    """Отсортировать модели по названию или по аптайму последней проверки.

    При сортировке по аптайму модели без данных оказываются в конце.
    """
    if not by_uptime:
        return sorted(models, key=lambda model: model.name.lower())

    uptimes = {}
    for model in models:
        result = last_result(history, model.id)
        uptimes[model.id] = None if result is None else result.uptime
    return sorted(
        models,
        key=lambda model: (
            uptimes[model.id] is not None,
            uptimes[model.id] or 0.0,
        ),
        reverse=True,
    )
