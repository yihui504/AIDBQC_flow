from src.adapters.base import VectorDBBase

_current_adapter: VectorDBBase | None = None


def set_adapter(adapter: VectorDBBase) -> None:
    global _current_adapter
    _current_adapter = adapter


def get_adapter() -> VectorDBBase:
    if _current_adapter is None:
        raise RuntimeError("No DB adapter configured")
    return _current_adapter
