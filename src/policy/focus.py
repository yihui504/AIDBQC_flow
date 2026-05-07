from src.models.state import FocusMode, ToolMeta


class FocusAdvisor:
    def __init__(self):
        self._tool_metas: dict[str, ToolMeta] = {}

    def register(self, name: str, meta: ToolMeta) -> None:
        self._tool_metas[name] = meta

    def recommend_tools(self, current_focus: FocusMode) -> list[str]:
        recommended = []
        for name, meta in self._tool_metas.items():
            if current_focus in meta.focus_modes:
                recommended.append(name)
        return recommended

    def is_out_of_focus(self, tool_name: str, current_focus: FocusMode) -> bool:
        meta = self._tool_metas.get(tool_name)
        if meta is None:
            return False
        return current_focus not in meta.focus_modes
