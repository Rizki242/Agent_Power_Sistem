"""Tests for pple/agents/ (docs/final.md Phase 18 - Agent Registry)."""

import unittest
from unittest.mock import patch

from pple.agents import AgentRegistry


class AgentRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()

    def test_lists_all_eight_agents(self):
        agents = self.registry.list_agents()
        self.assertEqual(len(agents), 8)
        agent_ids = {a["agent_id"] for a in agents}
        self.assertEqual(agent_ids, {
            "subagent-vib-01", "subagent-mcsa-01", "subagent-dga-01", "subagent-pd-01",
            "subagent-tribo-01", "subagent-therm-01", "subagent-fusion-01", "subagent-safety-01",
        })

    def test_specialist_status_reflects_real_manifest_load_result(self):
        agents = {a["agent_id"]: a for a in self.registry.list_agents()}
        # All 6 manifests are checked-in and valid, so every specialist
        # should report the real ACTIVE status, not a hardcoded one.
        for agent_id in ("subagent-vib-01", "subagent-mcsa-01", "subagent-dga-01",
                          "subagent-pd-01", "subagent-tribo-01", "subagent-therm-01"):
            self.assertEqual(agents[agent_id]["status"], "ACTIVE")

    def test_fusion_and_safety_are_always_online(self):
        agents = {a["agent_id"]: a for a in self.registry.list_agents()}
        self.assertEqual(agents["subagent-fusion-01"]["status"], "ONLINE")
        self.assertEqual(agents["subagent-safety-01"]["status"], "ONLINE")

    def test_status_reflects_a_disabled_module(self):
        with patch.object(
            AgentRegistry, "_module_status_by_id",
            return_value={"vibration": "DISABLED", "mcsa": "ACTIVE", "dga": "ACTIVE",
                          "partial_discharge": "ACTIVE", "tribology": "ACTIVE", "thermal": "ACTIVE"},
        ):
            agents = {a["agent_id"]: a for a in self.registry.list_agents()}
        self.assertEqual(agents["subagent-vib-01"]["status"], "DISABLED")
        self.assertEqual(agents["subagent-mcsa-01"]["status"], "ACTIVE")

    def test_get_agent_known_id(self):
        agent = self.registry.get_agent("subagent-dga-01")
        self.assertIsNotNone(agent)
        self.assertEqual(agent["domain"], "DGA")

    def test_get_agent_unknown_id_returns_none(self):
        self.assertIsNone(self.registry.get_agent("does-not-exist"))


if __name__ == "__main__":
    unittest.main()
