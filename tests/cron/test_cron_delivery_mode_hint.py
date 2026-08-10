"""The cron execution hint must match the job's real delivery mode.

Regression tests for the fleet-wide silent-delivery-skip bug (2026-08-04 /
08-05 / 08-10): the static cron hint told every job "your final response will
be automatically delivered … do NOT use send_message", which is false for
``deliver=local`` jobs — their output is archived only.  Jobs whose prompts
required an explicit ``hermes send`` obeyed the hint instead and never
delivered.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def cron_env(tmp_path, monkeypatch):
    """Isolated cron environment with temp HERMES_HOME."""
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / "cron").mkdir()
    (hermes_home / "cron" / "output").mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    import cron.jobs as jobs_mod
    monkeypatch.setattr(jobs_mod, "HERMES_DIR", hermes_home)
    monkeypatch.setattr(jobs_mod, "CRON_DIR", hermes_home / "cron")
    monkeypatch.setattr(jobs_mod, "JOBS_FILE", hermes_home / "cron" / "jobs.json")
    monkeypatch.setattr(jobs_mod, "OUTPUT_DIR", hermes_home / "cron" / "output")

    return hermes_home


def _prompt_for(deliver, cron_env):
    from cron.jobs import create_job
    from cron.scheduler import _build_job_prompt

    kwargs = {} if deliver is None else {"deliver": deliver}
    job = create_job(prompt="Post the daily numbers to #numbers.",
                     schedule="every 1d", **kwargs)
    return _build_job_prompt(job)


class TestLocalDeliverHint:
    def test_local_job_is_told_output_is_archived_only(self, cron_env):
        prompt = _prompt_for("local", cron_env)
        assert "NOT delivered" in prompt
        assert "archived" in prompt

    def test_local_job_not_told_delivery_is_automatic(self, cron_env):
        prompt = _prompt_for("local", cron_env)
        assert "automatically delivered" not in prompt

    def test_local_job_not_forbidden_from_sending(self, cron_env):
        # The poison line: send suppression must never reach a local job.
        prompt = _prompt_for("local", cron_env)
        assert "do NOT use send_message" not in prompt

    def test_local_job_told_to_send_explicitly(self, cron_env):
        prompt = _prompt_for("local", cron_env)
        assert "perform that send yourself" in prompt

    def test_local_job_gets_no_silent_marker_instruction(self, cron_env):
        # [SILENT] suppresses delivery; a local job has none to suppress.
        prompt = _prompt_for("local", cron_env)
        assert "[SILENT]" not in prompt

    def test_missing_deliver_defaults_to_local_wording(self, cron_env):
        # scheduler treats a missing deliver as "local" — hint must match.
        prompt = _prompt_for(None, cron_env)
        assert "NOT delivered" in prompt
        assert "automatically delivered" not in prompt


class TestAutoDeliverHint:
    @pytest.mark.parametrize("deliver", ["origin", "slack", "telegram:-100123:7", "all"])
    def test_auto_deliver_job_keeps_auto_delivery_wording(self, cron_env, deliver):
        prompt = _prompt_for(deliver, cron_env)
        assert "automatically delivered" in prompt
        assert "do NOT use send_message" in prompt
        assert "[SILENT]" in prompt

    def test_auto_deliver_job_not_told_archived_only(self, cron_env):
        prompt = _prompt_for("origin", cron_env)
        assert "NOT delivered" not in prompt

    def test_list_form_deliver_normalized_before_mode_check(self, cron_env):
        # Legacy list-shaped deliver values must resolve like their string form.
        from cron.jobs import create_job
        from cron.scheduler import _build_job_prompt

        job = create_job(prompt="Report.", schedule="every 1d")
        job["deliver"] = ["slack"]  # legacy shape, see _normalize_deliver_value
        prompt = _build_job_prompt(job)
        assert "automatically delivered" in prompt

    def test_user_prompt_survives_in_both_modes(self, cron_env):
        for deliver in ("local", "origin"):
            prompt = _prompt_for(deliver, cron_env)
            assert "Post the daily numbers to #numbers." in prompt
