"""
Tests for aquilia.mlops.release - rollout engine, CI templates.
"""

import pytest

from aquilia.mlops._types import RolloutConfig, RolloutStrategy
from aquilia.mlops.release.rollout import RolloutEngine, RolloutPhase, RolloutState
from aquilia.mlops.release.ci import generate_ci_workflow, generate_dockerfile


class TestRolloutEngine:
    @pytest.fixture
    def config(self):
        return RolloutConfig(
            from_version="v1",
            to_version="v2",
            strategy=RolloutStrategy.CANARY,
            percentage=10,
            auto_rollback=True,
        )

    @pytest.fixture
    def engine(self):
        return RolloutEngine()

    async def test_start_rollout(self, engine, config):
        state = await engine.start(config)
        assert state.phase == RolloutPhase.IN_PROGRESS
        assert state.current_percentage == 10
        assert state.id == "rollout-1"

    async def test_advance_rollout(self, engine, config):
        state = await engine.start(config)
        state = await engine.advance(state.id, percentage=50)
        assert state.current_percentage == 50
        assert state.phase == RolloutPhase.IN_PROGRESS

    async def test_advance_to_100_completes(self, engine, config):
        state = await engine.start(config)
        state = await engine.advance(state.id, percentage=100)
        assert state.phase == RolloutPhase.COMPLETED
        assert state.current_percentage == 100

    async def test_complete_rollout(self, engine, config):
        state = await engine.start(config)
        state = await engine.complete(state.id)
        assert state.phase == RolloutPhase.COMPLETED
        assert state.completed_at > 0

    async def test_rollback(self, engine, config):
        state = await engine.start(config)
        state = await engine.rollback(state.id, reason="High error rate")
        assert state.phase == RolloutPhase.ROLLED_BACK
        assert state.current_percentage == 0
        assert state.error == "High error rate"

    async def test_advance_not_found_raises(self, engine):
        with pytest.raises(KeyError):
            await engine.advance("nonexistent")

    async def test_list_rollouts(self, engine, config):
        await engine.start(config)
        rollouts = engine.list_rollouts()
        assert len(rollouts) == 1

    async def test_get_rollout(self, engine, config):
        state = await engine.start(config)
        found = engine.get_rollout(state.id)
        assert found is not None
        assert found.id == state.id

    async def test_cannot_advance_completed(self, engine, config):
        state = await engine.start(config)
        await engine.complete(state.id)
        with pytest.raises(RuntimeError):
            await engine.advance(state.id)


class TestCITemplates:
    def test_generate_ci_workflow(self, tmp_path):
        path = generate_ci_workflow(output_dir=str(tmp_path / ".github" / "workflows"))
        assert "aquilia-ci.yml" in path

    def test_generate_ci_workflow_content(self, tmp_path):
        from pathlib import Path
        path = generate_ci_workflow(output_dir=str(tmp_path / ".github" / "workflows"))
        content = Path(path).read_text()
        assert "on:" in content
        assert "jobs:" in content

    def test_generate_dockerfile(self, tmp_path):
        from pathlib import Path
        path = generate_dockerfile(output_dir=str(tmp_path))
        content = Path(path).read_text()
        assert "FROM" in content
        assert "COPY" in content
