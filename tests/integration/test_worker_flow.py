# tests/integration/test_worker_flow.py
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.domain.events import EventType, SystemEvent
from app.workers.worker import compile_grammar


@pytest.mark.asyncio
class TestWorkerFlow:
    """
    Integration-style tests for the ARQ job function in app/workers/worker.py.
    """

    async def test_build_requested_event_triggers_compile_job(self):
        event = SystemEvent(
            type=EventType.BUILD_REQUESTED,
            payload={"lang_code": "deu", "strategy": "full"},
        )
        lang_code = event.payload["lang_code"]

        base_dir = "/repo"
        pgf_path = f"{base_dir}/gf/AbstractWiki.pgf"

        with (
            patch.dict(os.environ, {"AW_PGF_PATH": pgf_path}, clear=False),
            patch("app.workers.worker.settings.FILESYSTEM_REPO_PATH", base_dir),
            patch("app.workers.worker._run_indexer", new_callable=AsyncMock) as mock_indexer,
            patch("app.workers.worker._run_orchestrator", new_callable=AsyncMock) as mock_orch,
            patch("app.workers.worker.os.path.exists", return_value=True) as mock_exists,
            patch("app.workers.worker.runtime.reload", new_callable=AsyncMock) as mock_reload,
        ):
            result = await compile_grammar({}, lang_code)

        assert result == "Compiled deu successfully."

        mock_indexer.assert_awaited_once()
        idx_args, idx_kwargs = mock_indexer.call_args
        assert str(idx_args[0]) == str(Path(base_dir))
        assert idx_kwargs == {"langs": [lang_code]}

        mock_orch.assert_awaited_once()
        orch_args, orch_kwargs = mock_orch.call_args
        assert str(orch_args[0]) == str(Path(base_dir))
        assert orch_kwargs == {"langs": [lang_code], "strategy": "AUTO", "clean": False}

        mock_exists.assert_called_once_with(pgf_path)
        mock_reload.assert_awaited_once()

    async def test_pgf_artifact_missing_raises_runtimeerror(self):
        base_dir = "/repo"
        pgf_path = f"{base_dir}/gf/AbstractWiki.pgf"

        with (
            patch.dict(os.environ, {"AW_PGF_PATH": pgf_path}, clear=False),
            patch("app.workers.worker.settings.FILESYSTEM_REPO_PATH", base_dir),
            patch("app.workers.worker._run_indexer", new_callable=AsyncMock) as mock_indexer,
            patch("app.workers.worker._run_orchestrator", new_callable=AsyncMock) as mock_orch,
            patch("app.workers.worker.os.path.exists", return_value=False) as mock_exists,
            patch("app.workers.worker.runtime.reload", new_callable=AsyncMock) as mock_reload,
        ):
            with pytest.raises(RuntimeError) as excinfo:
                await compile_grammar({}, "eng")

        assert "PGF artifact missing" in str(excinfo.value)
        mock_indexer.assert_awaited_once()
        mock_orch.assert_awaited_once()
        mock_exists.assert_called_once_with(pgf_path)
        mock_reload.assert_not_awaited()

    async def test_orchestrator_failure_propagates(self):
        base_dir = "/repo"
        pgf_path = f"{base_dir}/gf/AbstractWiki.pgf"

        with (
            patch.dict(os.environ, {"AW_PGF_PATH": pgf_path}, clear=False),
            patch("app.workers.worker.settings.FILESYSTEM_REPO_PATH", base_dir),
            patch("app.workers.worker._run_indexer", new_callable=AsyncMock) as mock_indexer,
            patch(
                "app.workers.worker._run_orchestrator",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Build orchestrator failed: boom"),
            ) as mock_orch,
            patch("app.workers.worker.os.path.exists", new_callable=AsyncMock) as mock_exists,
            patch("app.workers.worker.runtime.reload", new_callable=AsyncMock) as mock_reload,
        ):
            with pytest.raises(RuntimeError) as excinfo:
                await compile_grammar({}, "eng")

        assert "Build orchestrator failed" in str(excinfo.value)
        mock_indexer.assert_awaited_once()
        mock_orch.assert_awaited_once()
        mock_exists.assert_not_awaited()
        mock_reload.assert_not_awaited()