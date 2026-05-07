import asyncio
import pytest

from src.runtime.recovery import RecoveryStrategy, RecoveryResult, ErrorCategory, classify_error


class TestClassifyError:
    def test_api_timeout(self):
        err = Exception("request timeout after 30s")
        assert classify_error(err) == ErrorCategory.API_TIMEOUT

    def test_api_timed_out(self):
        err = Exception("connection timed out")
        assert classify_error(err) == ErrorCategory.API_TIMEOUT

    def test_db_connection_lost(self):
        err = Exception("connection refused on port 5432")
        assert classify_error(err) == ErrorCategory.DB_CONNECTION_LOST

    def test_db_unreachable(self):
        err = Exception("host unreachable")
        assert classify_error(err) == ErrorCategory.DB_CONNECTION_LOST

    def test_rate_limited_429(self):
        err = Exception("HTTP 429 Too Many Requests")
        assert classify_error(err) == ErrorCategory.RATE_LIMITED

    def test_rate_limited_text(self):
        err = Exception("rate limit exceeded")
        assert classify_error(err) == ErrorCategory.RATE_LIMITED

    def test_context_overflow(self):
        err = Exception("context overflow detected")
        assert classify_error(err) == ErrorCategory.CONTEXT_OVERFLOW

    def test_context_too_long(self):
        err = Exception("context too long for model")
        assert classify_error(err) == ErrorCategory.CONTEXT_OVERFLOW

    def test_context_exceed(self):
        err = Exception("context exceed maximum length")
        assert classify_error(err) == ErrorCategory.CONTEXT_OVERFLOW

    def test_policy_blocked(self):
        err = Exception("policy blocked this action")
        assert classify_error(err) == ErrorCategory.POLICY_BLOCKED

    def test_policy_skip(self):
        err = Exception("skip due to policy")
        assert classify_error(err) == ErrorCategory.POLICY_BLOCKED

    def test_tool_execution_failure(self):
        err = Exception("tool execution failed")
        assert classify_error(err) == ErrorCategory.TOOL_EXECUTION_FAILURE

    def test_unknown_error(self):
        err = Exception("something completely unexpected")
        assert classify_error(err) == ErrorCategory.UNKNOWN


class TestRecoveryStrategyRetry:
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        strategy = RecoveryStrategy()
        result1 = await strategy.recover(Exception("timeout"))
        assert result1.should_retry is True
        assert result1.delay == 1.0

        result2 = await strategy.recover(Exception("timeout"))
        assert result2.should_retry is True
        assert result2.delay == 2.0

        result3 = await strategy.recover(Exception("timeout"))
        assert result3.should_retry is True
        assert result3.delay == 4.0

    @pytest.mark.asyncio
    async def test_retry_exhausted_returns_notify(self):
        strategy = RecoveryStrategy()
        for _ in range(3):
            await strategy.recover(Exception("timeout"))

        result = await strategy.recover(Exception("timeout"))
        assert result.should_retry is False
        assert "notify" in result.action_taken

    @pytest.mark.asyncio
    async def test_policy_blocked_no_retry(self):
        strategy = RecoveryStrategy()
        result = await strategy.recover(Exception("policy blocked"))
        assert result.should_retry is False
        assert "notify" in result.action_taken


class TestRecoveryStrategyRoundReset:
    @pytest.mark.asyncio
    async def test_on_round_start_resets_counts(self):
        strategy = RecoveryStrategy()
        await strategy.recover(Exception("timeout"))
        await strategy.recover(Exception("timeout"))

        strategy.on_round_start()

        result = await strategy.recover(Exception("timeout"))
        assert result.should_retry is True
        assert result.delay == 1.0


class TestRecoveryStrategyTotalRetries:
    @pytest.mark.asyncio
    async def test_total_retries_cross_round_cap(self):
        strategy = RecoveryStrategy()
        for _ in range(3):
            await strategy.recover(Exception("timeout"))

        strategy.on_round_start()

        for _ in range(3):
            await strategy.recover(Exception("timeout"))

        strategy.on_round_start()

        for _ in range(3):
            await strategy.recover(Exception("timeout"))

        result = await strategy.recover(Exception("timeout"))
        assert result.should_retry is False


class TestRecoveryStrategyContextOverflow:
    @pytest.mark.asyncio
    async def test_context_overflow_triggers_compact_fn(self):
        called = {"count": 0}

        def compact():
            called["count"] += 1

        strategy = RecoveryStrategy(compact_fn=compact)
        result = await strategy.recover(Exception("context overflow"))
        assert result.should_retry is True
        assert called["count"] == 1


class TestRecoveryStrategyDbConnectionLost:
    @pytest.mark.asyncio
    async def test_db_connection_lost_triggers_adapter_reset(self):
        called = {"count": 0}

        async def reset_adapter():
            called["count"] += 1

        strategy = RecoveryStrategy(adapter_reset_fn=reset_adapter)
        result = await strategy.recover(Exception("connection refused"))
        assert result.should_retry is True
        assert called["count"] == 1

    @pytest.mark.asyncio
    async def test_adapter_reset_exception_suppressed(self):
        async def bad_reset():
            raise RuntimeError("reset failed")

        strategy = RecoveryStrategy(adapter_reset_fn=bad_reset)
        result = await strategy.recover(Exception("connection refused"))
        assert result.should_retry is True
