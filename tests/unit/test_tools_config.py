from __future__ import annotations

import json
import os
import tempfile

import pytest

from src.tools.compression import CompressionConfig, ToolOutputCompressor
from src.models.state import ToolMeta
from src.config import AppConfig, DBInstanceConfig, LLMConfig


class TestToolOutputCompressor:
    def setup_method(self):
        self.compressor = ToolOutputCompressor()

    def test_short_output_unchanged(self):
        output = "short output"
        assert self.compressor.compress("any_tool", output) == output

    def test_none_output_unchanged(self):
        assert self.compressor.compress("any_tool", "") == ""

    def test_json_strategy_preserves_error(self):
        data = json.dumps({"success": False, "error": "dimension mismatch", "data": list(range(100))})
        result = self.compressor.compress("db_search", data)
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "error" in parsed

    def test_json_strategy_truncates_data(self):
        config = CompressionConfig(max_chars_per_output=500)
        compressor = ToolOutputCompressor(config)
        data = json.dumps({"success": True, "data": list(range(500)), "results_count": 500})
        result = compressor.compress("db_query", data)
        parsed = json.loads(result)
        assert "results_count" in parsed
        assert isinstance(parsed["data"], str)
        assert "truncated" in parsed["data"]

    def test_json_strategy_preserves_list_within_limit(self):
        data = json.dumps({"success": True, "error": None, "results_count": 3, "data": [1, 2, 3]})
        result = self.compressor.compress("db_query", data)
        parsed = json.loads(result)
        assert parsed["data"] == [1, 2, 3]

    def test_generic_compress_long_text(self):
        lines = [f"Line {i}: " + "x" * 50 for i in range(200)]
        output = "\n".join(lines)
        config = CompressionConfig(max_chars_per_output=100, max_lines_per_output=10)
        compressor = ToolOutputCompressor(config)
        result = compressor.compress("unknown_tool", output)
        assert len(result) <= 300
        assert "compressed" in result or "truncated" in result

    def test_compress_level_minimal(self):
        config = CompressionConfig(max_chars_per_output=100)
        compressor = ToolOutputCompressor(config)
        data = json.dumps({"success": True, "error": None, "data": list(range(50))})
        meta = ToolMeta(focus_modes=[], permission="read", compress="minimal")
        result = compressor.compress("db_query", data, meta)
        assert len(result) < len(data)

    def test_compress_level_full(self):
        data = json.dumps({"success": True, "error": None, "data": [1, 2, 3]})
        meta = ToolMeta(focus_modes=[], permission="read", compress="full")
        result = self.compressor.compress("db_query", data, meta)
        parsed = json.loads(result)
        assert parsed["data"] == [1, 2, 3]

    def test_non_json_falls_back_to_generic(self):
        output = "not json at all " * 200
        result = self.compressor.compress("db_search", output)
        assert isinstance(result, str)

    def test_json_list_root_falls_back_to_generic(self):
        data = json.dumps([1, 2, 3])
        result = self.compressor.compress("db_search", data)
        assert isinstance(result, str)

    def test_enforce_budget(self):
        config = CompressionConfig(max_chars_per_output=100)
        compressor = ToolOutputCompressor(config)
        long_output = "x" * 500
        result = compressor.compress("any_tool", long_output)
        assert len(result) <= 200


class TestAppConfig:
    def test_default_config(self):
        config = AppConfig()
        assert config.llm.pro_model == "deepseek-v4-pro"
        assert config.harness.max_rounds == 4
        assert config.database.default == "milvus"

    def test_from_yaml_nonexistent(self):
        config = AppConfig.from_yaml("nonexistent.yaml")
        assert config.llm.pro_model == "deepseek-v4-pro"

    def test_from_yaml_valid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("llm:\n  pro_model: test-model\n  api_key: sk-test\n")
            f.flush()
            config = AppConfig.from_yaml(f.name)
        os.unlink(f.name)
        assert config.llm.pro_model == "test-model"
        assert config.llm.api_key == "sk-test"

    def test_db_instance_config_literal_type(self):
        inst = DBInstanceConfig(type="milvus")
        assert inst.type == "milvus"
        with pytest.raises(Exception):
            DBInstanceConfig(type="redis")

    def test_get_pro_model_id(self):
        config = AppConfig()
        assert config.get_pro_model_id() == "deepseek-v4-pro"

    def test_get_flash_model_id(self):
        config = AppConfig()
        assert config.get_flash_model_id() == "deepseek-v4-flash"

    def test_extra_fields_ignored(self):
        config = AppConfig(unknown_field="test")
        assert not hasattr(config, "unknown_field")

    def test_resolve_env_with_env_vars(self):
        config = AppConfig()
        config._resolve_env()
        assert isinstance(config.llm.api_key, str)

    def test_database_instances_default_empty(self):
        config = AppConfig()
        assert config.database.instances == []


class TestCompressionConfig:
    def test_defaults(self):
        config = CompressionConfig()
        assert config.max_chars_per_output == 2000
        assert config.max_lines_per_output == 50
        assert config.max_line_chars == 200

    def test_custom(self):
        config = CompressionConfig(max_chars_per_output=500, max_lines_per_output=10)
        assert config.max_chars_per_output == 500
        assert config.max_lines_per_output == 10
