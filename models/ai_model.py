"""Модель ИИ из каталога OpenRouter и функции работы со списком моделей."""


def parse_price(pricing: object) -> float | None:
    """Суммарная цена токена запроса и ответа, None — цена неизвестна."""
    if not isinstance(pricing, dict):
        return None
    try:
        return float(pricing["prompt"]) + float(pricing["completion"])
    except (KeyError, TypeError, ValueError):
        return None


class AIModel:
    """Модель ИИ, доступная через OpenRouter."""

    FREE_SUFFIX = ":free"

    def __init__(
        self, model_id: str, name: str, price: float | None = None
    ) -> None:
        """Создать модель.

        price — цена токена запроса и ответа вместе, None — цена неизвестна.
        """
        self._id = model_id
        self.name = name
        self.price = price

    @property
    def id(self) -> str:
        """Идентификатор модели в OpenRouter.

        Доступен только для чтения: по нему с моделью связана история.
        """
        return self._id

    @property
    def is_free(self) -> bool:
        """Бесплатная ли модель: суффикс :free или нулевая цена."""
        return self._id.endswith(self.FREE_SUFFIX) or self.price == 0

    def matches(self, query: str) -> bool:
        """Есть ли подстрока query в id или названии без учёта регистра."""
        query = query.lower().strip()
        return query in self._id.lower() or query in self.name.lower()

    def to_data(self) -> dict:
        """Данные модели для сохранения в JSON."""
        return {"id": self._id, "name": self.name}

    @classmethod
    def from_data(cls, data: dict) -> "AIModel":
        """Создать модель из записи списка отслеживания."""
        return cls(data["id"], data["name"])

    @classmethod
    def from_api(cls, data: dict) -> "AIModel":
        """Создать модель из записи каталога OpenRouter."""
        model_id = data.get("id", "")
        name = data.get("name") or model_id
        return cls(model_id, name, parse_price(data.get("pricing")))

    @staticmethod
    def validate_id(model_id: str) -> bool:
        """Проверить формат id: «разработчик/модель» без пробелов."""
        vendor, _, name = model_id.partition("/")
        return bool(vendor) and bool(name) and " " not in model_id

    def __str__(self) -> str:
        """Название, отметка бесплатной модели и id."""
        label = " [бесплатная]" if self.is_free else ""
        return f"{self.name}{label} ({self._id})"


def find_model(models: list[AIModel], model_id: str) -> AIModel | None:
    """Найти модель по точному id."""
    for model in models:
        if model.id == model_id:
            return model
    return None


def search_models(
    models: list[AIModel], query: str, free_only: bool = False
) -> list[AIModel]:
    """Найти модели, в id или названии которых есть подстрока query."""
    return [
        model for model in models
        if model.matches(query) and (model.is_free or not free_only)
    ]


def add_model(models: list[AIModel], model: AIModel) -> bool:
    """Добавить модель в список. Возвращает False, если она уже есть."""
    if find_model(models, model.id) is not None:
        return False
    models.append(model)
    return True


def remove_model(models: list[AIModel], model_id: str) -> bool:
    """Удалить модель из списка. Возвращает False, если её не было."""
    model = find_model(models, model_id)
    if model is None:
        return False
    models.remove(model)
    return True
