from __future__ import annotations

import asyncio
import json
from typing import Optional

from pydantic_ai import RunContext

from src.models.state import FocusMode, UnifiedState, tool_meta
from src.tools.db.adapter_holder import get_adapter


@tool_meta(focus_modes=[FocusMode.EXECUTION], permission="execute", compress="summary", db_target=True)
async def db_create_collection(
    ctx: RunContext[UnifiedState],
    collection_name: str,
    dimension: int = 128,
    index_type: str = "IVF_FLAT",
    metric_type: str = "L2",
) -> str:
    adapter = get_adapter()
    result = await adapter.create_collection(
        name=collection_name, dimension=dimension,
        index_type=index_type, metric_type=metric_type,
    )
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.EXECUTION], permission="execute", compress="summary", db_target=True)
async def db_insert_data(
    ctx: RunContext[UnifiedState],
    collection_name: str,
    data: str,
) -> str:
    adapter = get_adapter()
    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError as e:
        return json.dumps({"success": False, "error": f"Invalid JSON data: {e}"})
    result = await adapter.insert(collection=collection_name, data=parsed_data)
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.EXECUTION, FocusMode.VERIFICATION], permission="read", compress="results_only", db_target=True)
async def db_search(
    ctx: RunContext[UnifiedState],
    collection_name: str,
    vector: str,
    top_k: int = 10,
    metric_type: str = "L2",
) -> str:
    adapter = get_adapter()
    try:
        parsed_vector = json.loads(vector) if isinstance(vector, str) else vector
    except json.JSONDecodeError as e:
        return json.dumps({"success": False, "error": f"Invalid JSON vector: {e}"})
    result = await adapter.search(
        collection=collection_name, vector=parsed_vector,
        top_k=top_k, metric_type=metric_type,
    )
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.EXECUTION, FocusMode.VERIFICATION], permission="read", compress="results_only", db_target=True)
async def db_query(
    ctx: RunContext[UnifiedState],
    collection_name: str,
    filter_expr: str,
    output_fields: str = "id",
    limit: int = 100,
) -> str:
    adapter = get_adapter()
    fields = [f.strip() for f in output_fields.split(",")]
    result = await adapter.query(
        collection=collection_name, filter_expr=filter_expr,
        output_fields=fields, limit=limit,
    )
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.EXECUTION], permission="execute", compress="summary", db_target=True)
async def db_delete_data(
    ctx: RunContext[UnifiedState],
    collection_name: str,
    ids: Optional[str] = None,
    filter_expr: Optional[str] = None,
) -> str:
    adapter = get_adapter()
    id_list = [x.strip() for x in ids.split(",")] if ids else []
    result = await adapter.delete(
        collection=collection_name, ids=id_list,
        filter_expr=filter_expr,
    )
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.EXECUTION], permission="execute", compress="summary", db_target=True)
async def db_upsert_data(
    ctx: RunContext[UnifiedState],
    collection_name: str,
    data: str,
) -> str:
    adapter = get_adapter()
    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError as e:
        return json.dumps({"success": False, "error": f"Invalid JSON data: {e}"})
    result = await adapter.upsert(collection=collection_name, data=parsed_data)
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.EXECUTION], permission="execute", compress="minimal", db_target=True)
async def db_flush(
    ctx: RunContext[UnifiedState],
    collection_name: str,
) -> str:
    adapter = get_adapter()
    result = await adapter.flush(collection=collection_name)
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.EXECUTION], permission="read", compress="minimal", db_target=True)
async def db_load_collection(
    ctx: RunContext[UnifiedState],
    collection_name: str,
) -> str:
    adapter = get_adapter()
    result = await adapter.load_collection(name=collection_name)
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.EXECUTION], permission="read", compress="minimal", db_target=True)
async def db_release_collection(
    ctx: RunContext[UnifiedState],
    collection_name: str,
) -> str:
    adapter = get_adapter()
    result = await adapter.release_collection(name=collection_name)
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING, FocusMode.EXECUTION, FocusMode.VERIFICATION], permission="read", compress="summary", db_target=True)
async def db_get_collection_info(
    ctx: RunContext[UnifiedState],
    collection_name: str,
) -> str:
    adapter = get_adapter()
    result = await adapter.get_collection_info(name=collection_name)
    return json.dumps(result, ensure_ascii=False, default=str)


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING, FocusMode.EXECUTION], permission="read", compress="minimal", db_target=True)
async def db_list_collections(
    ctx: RunContext[UnifiedState],
) -> str:
    adapter = get_adapter()
    result = await adapter.list_collections()
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.EXECUTION], permission="admin", compress="minimal", db_target=True)
async def db_drop_collection(
    ctx: RunContext[UnifiedState],
    collection_name: str,
) -> str:
    adapter = get_adapter()
    result = await adapter.drop_collection(name=collection_name)
    return json.dumps(result, ensure_ascii=False)


@tool_meta(focus_modes=[FocusMode.UNDERSTANDING, FocusMode.EXECUTION], permission="read", compress="minimal", db_target=True)
async def db_health_check(
    ctx: RunContext[UnifiedState],
) -> str:
    adapter = get_adapter()
    result = await adapter.health_check()
    return json.dumps(result, ensure_ascii=False)
