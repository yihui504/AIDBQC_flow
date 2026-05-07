import pytest

from pydantic_ai import RunContext

from src.tools.registry import ToolRegistry
from src.models.state import FocusMode, ToolMeta, tool_meta


@tool_meta(focus_modes=[FocusMode.EXECUTION], permission="read")
async def dummy_tool(ctx: RunContext, query: str) -> str:
    return query


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING], permission="read")
async def plain_tool(query: str) -> str:
    return query


@pytest.fixture
def registry():
    return ToolRegistry()


class TestToolRegistryRegister:
    def test_register_tool(self, registry):
        registry.register(dummy_tool)
        assert "dummy_tool" in registry.get_all_tools()

    def test_register_stores_meta(self, registry):
        registry.register(dummy_tool)
        meta = registry.get_meta("dummy_tool")
        assert meta is not None
        assert FocusMode.EXECUTION in meta.focus_modes
        assert meta.permission == "read"

    def test_register_without_meta(self, registry):
        async def bare_tool(x: int) -> int:
            return x

        registry.register(bare_tool)
        assert "bare_tool" in registry.get_all_tools()
        assert registry.get_meta("bare_tool") is None


class TestToolRegistryGetAllTools:
    def test_returns_all_registered_tools(self, registry):
        registry.register(dummy_tool)
        registry.register(plain_tool)
        tools = registry.get_all_tools()
        assert len(tools) == 2
        assert "dummy_tool" in tools
        assert "plain_tool" in tools

    def test_returns_copy(self, registry):
        registry.register(dummy_tool)
        tools = registry.get_all_tools()
        tools["extra"] = lambda: None
        assert "extra" not in registry.get_all_tools()


class TestToolRegistryGetMeta:
    def test_get_meta_existing(self, registry):
        registry.register(plain_tool)
        meta = registry.get_meta("plain_tool")
        assert meta is not None
        assert FocusMode.UNDERSTANDING in meta.focus_modes

    def test_get_meta_nonexistent(self, registry):
        assert registry.get_meta("no_such_tool") is None


class TestToolRegistryBindFocusAdvisor:
    def test_bind_focus_advisor(self, registry):
        from src.policy.focus import FocusAdvisor

        registry.register(dummy_tool)
        registry.register(plain_tool)

        advisor = FocusAdvisor()
        registry.bind_focus_advisor(advisor)

        recommended = advisor.recommend_tools(FocusMode.EXECUTION)
        assert "dummy_tool" in recommended
        assert "plain_tool" not in recommended


class TestToolRegistryHasRunContext:
    def test_detects_run_context(self, registry):
        assert registry._has_run_context(dummy_tool) is True

    def test_no_run_context(self, registry):
        assert registry._has_run_context(plain_tool) is False


class TestToolRegistryProperties:
    def test_tool_count(self, registry):
        registry.register(dummy_tool)
        registry.register(plain_tool)
        assert registry.tool_count == 2

    def test_tool_names(self, registry):
        registry.register(dummy_tool)
        registry.register(plain_tool)
        names = registry.tool_names
        assert set(names) == {"dummy_tool", "plain_tool"}

    def test_tool_count_empty(self, registry):
        assert registry.tool_count == 0
