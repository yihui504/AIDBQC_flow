from typing import Callable

from src.tools.registry import ToolRegistry
from src.tools.compression import ToolOutputCompressor, CompressionConfig
from src.tools.db import (
    db_create_collection,
    db_insert_data,
    db_search,
    db_query,
    db_delete_data,
    db_upsert_data,
    db_flush,
    db_load_collection,
    db_release_collection,
    db_get_collection_info,
    db_list_collections,
    db_drop_collection,
    db_health_check,
)
from src.tools.doc import doc_search, doc_validate_reference
from src.tools.code import code_run_mre
from src.tools.source import source_clone_repo, source_search, source_read, source_analyze_module
from src.tools.verify import contract_validate_source, contract_validate_behavior, contract_tri_validate, verify_defect
from src.tools.flow import update_focus, record_defect, generate_feedback

_ALL_TOOL_FUNCS: list[Callable] = [
    db_create_collection, db_insert_data, db_search, db_query,
    db_delete_data, db_upsert_data, db_flush, db_load_collection,
    db_release_collection, db_get_collection_info, db_list_collections,
    db_drop_collection, db_health_check,
    doc_search, doc_validate_reference,
    code_run_mre,
    source_clone_repo, source_search, source_read, source_analyze_module,
    contract_validate_source, contract_validate_behavior, contract_tri_validate, verify_defect,
    update_focus, record_defect, generate_feedback,
]


def collect_all_tools() -> list[Callable]:
    return list(_ALL_TOOL_FUNCS)


def create_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for func in _ALL_TOOL_FUNCS:
        registry.register(func)
    return registry


__all__ = [
    "ToolRegistry",
    "ToolOutputCompressor",
    "CompressionConfig",
    "collect_all_tools",
    "create_registry",
]
