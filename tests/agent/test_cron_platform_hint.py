"""The cron PLATFORM_HINTS text must match the job's real delivery mode.

Companion to tests/cron/test_cron_delivery_mode_hint.py: the system-prompt
platform hint for ``platform="cron"`` claimed automatic delivery for every
job, which is false for ``deliver=local`` jobs (output is archived only).
The scheduler now stamps the job's delivery mode on the agent
(``_cron_deliver_mode``) and the hint resolves per mode.
"""

import types

from agent.prompt_builder import PLATFORM_HINTS, cron_platform_hint
from agent.system_prompt import _default_platform_hint


class TestCronPlatformHint:
    def test_local_mode_is_archived_only(self):
        hint = cron_platform_hint("local")
        assert "NOT delivered" in hint
        assert "automatically delivered" not in hint

    def test_local_mode_requires_explicit_sends(self):
        hint = cron_platform_hint("local")
        assert "perform that send yourself" in hint

    def test_autonomy_preamble_present_in_every_mode(self):
        for mode in (None, "", "local", "origin", "slack", "telegram:-1:2", "all"):
            assert "There is no user present" in cron_platform_hint(mode)

    def test_origin_mode_keeps_auto_delivery(self):
        hint = cron_platform_hint("origin")
        assert "automatically delivered" in hint
        assert "NOT delivered" not in hint

    def test_platform_target_mode_keeps_auto_delivery(self):
        assert "automatically delivered" in cron_platform_hint("slack")
        assert "automatically delivered" in cron_platform_hint("telegram:-100:7")
        assert "automatically delivered" in cron_platform_hint("all")

    def test_unknown_mode_claims_neither(self):
        # No delivery info -> the hint must not assert either behavior.
        for mode in (None, ""):
            hint = cron_platform_hint(mode)
            assert "automatically delivered" not in hint
            assert "NOT delivered" not in hint

    def test_static_dict_entry_makes_no_delivery_claim(self):
        # PLATFORM_HINTS["cron"] is the mode-less fallback; it must not
        # repeat the old false auto-delivery promise.
        assert "automatically delivered" not in PLATFORM_HINTS["cron"]


class TestDefaultPlatformHintResolution:
    def _agent(self, **attrs):
        return types.SimpleNamespace(**attrs)

    def test_cron_local_agent_gets_local_hint(self):
        agent = self._agent(_cron_deliver_mode="local")
        hint = _default_platform_hint(agent, "cron")
        assert "NOT delivered" in hint

    def test_cron_origin_agent_gets_auto_delivery_hint(self):
        agent = self._agent(_cron_deliver_mode="origin")
        hint = _default_platform_hint(agent, "cron")
        assert "automatically delivered" in hint

    def test_cron_agent_without_mode_gets_neutral_hint(self):
        agent = self._agent()
        hint = _default_platform_hint(agent, "cron")
        assert "automatically delivered" not in hint
        assert "NOT delivered" not in hint

    def test_non_cron_platform_unaffected(self):
        agent = self._agent(_cron_deliver_mode="local")
        assert _default_platform_hint(agent, "slack") == PLATFORM_HINTS["slack"]
