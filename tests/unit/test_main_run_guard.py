import pytest

from main import (
    _enforce_no_degraded_runtime_paths,
    _enforce_real_run_configuration,
    _is_weaviate_1369_target,
)


class _ConfigStub:
    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        return self.data.get(key, default)

    def get_int(self, key, default=0):
        return int(self.data.get(key, default))

    def get_bool(self, key, default=False):
        return bool(self.data.get(key, default))


def test_is_weaviate_1369_target():
    assert _is_weaviate_1369_target("Weaviate 1.36.9")
    assert _is_weaviate_1369_target("deep test weaviate v1.36.9")
    assert not _is_weaviate_1369_target("Weaviate 1.35.0")
    assert not _is_weaviate_1369_target("Milvus 2.6.12")


def test_enforce_real_run_configuration_requires_iteration_4():
    cfg = _ConfigStub(
        {
            "run_guard.enabled": True,
            "run_guard.enforce_weaviate_1369": True,
            "run_guard.enforce_max_iterations_4": True,
            "run_guard.forbidden_terms": ["mock", "simulate", "fallback", "degraded"],
            "harness.target_db_input": "Weaviate 1.36.9",
            "harness.max_iterations": 5,
        }
    )
    with pytest.raises(RuntimeError, match="max_iterations"):
        _enforce_real_run_configuration(cfg)


def test_enforce_real_run_configuration_rejects_simulated_target_text():
    cfg = _ConfigStub(
        {
            "run_guard.enabled": True,
            "run_guard.enforce_weaviate_1369": True,
            "run_guard.enforce_max_iterations_4": True,
            "run_guard.forbidden_terms": ["mock", "simulate", "fallback", "degraded"],
            "harness.target_db_input": "Weaviate 1.36.9 mock path",
            "harness.max_iterations": 4,
        }
    )
    with pytest.raises(RuntimeError, match="degraded/simulated marker"):
        _enforce_real_run_configuration(cfg)


def test_runtime_guard_blocks_degraded_verifier_output():
    cfg = _ConfigStub(
        {
            "run_guard.enabled": True,
            "run_guard.forbidden_terms": ["mock", "simulate", "fallback", "degraded"],
        }
    )
    state_update = {
        "defect_reports": [
            {
                "case_id": "TC-001",
                "verification_status": "degraded",
                "verifier_verdict": "degraded",
            }
        ]
    }
    with pytest.raises(RuntimeError, match="degraded verifier output"):
        _enforce_no_degraded_runtime_paths("agent6_verifier", state_update, cfg)
