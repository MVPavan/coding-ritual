import tempfile
import unittest
from pathlib import Path
import sys
import json
import os
import re
from copy import deepcopy
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import agent_matrix

CATALOG_PATH = (
    Path(__file__).parents[2]
    / "docs/research/codebases/subagent-runtimes/agent-matrix-values.yaml"
)


class CatalogLoadingTests(unittest.TestCase):
    def test_duplicate_yaml_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.yaml"
            path.write_text("version: 1\nversion: 2\n", encoding="utf-8")

            with self.assertRaisesRegex(agent_matrix.CatalogError, "duplicate key"):
                agent_matrix.load_catalog(path)

    def test_selection_values_must_be_declared_by_the_catalog(self):
        catalog = agent_matrix.load_catalog(CATALOG_PATH)
        agent_matrix.validate_selection(
            catalog,
            provider="codex",
            model="gpt-5.6-sol",
            effort="ultra",
            context="fresh",
            capabilities={
                "sandbox_mode": "workspace-write",
                "approval_policy": {"granular": {"rules": True}},
                "mcp_servers": "openaiDeveloperDocs",
            },
            skills=["adopt", "ak-guide"],
        )

        invalid_selections = [
            {"provider": "other"},
            {"provider": "codex", "model": "not-a-model"},
            {"provider": "codex", "effort": "extreme"},
            {"provider": "codex", "context": "zero-turns"},
            {
                "provider": "codex",
                "capabilities": {"sandbox_mode": "root-everywhere"},
            },
            {"provider": "codex", "skills": ["not-a-skill"]},
            {"provider": "codex", "skills": ["adopt", "adopt"]},
            {
                "provider": "codex",
                "capabilities": {
                    "mcp_servers": [
                        "openaiDeveloperDocs",
                        "openaiDeveloperDocs",
                    ]
                },
            },
        ]
        for selection in invalid_selections:
            with self.subTest(selection=selection):
                with self.assertRaises(agent_matrix.CatalogError):
                    agent_matrix.validate_selection(catalog, **selection)

    def test_catalog_shape_and_scalar_cardinality_are_strict(self):
        catalog = agent_matrix.load_catalog(CATALOG_PATH)
        invalid_catalogs = []

        wrong_version = deepcopy(catalog)
        wrong_version["version"] = 1
        invalid_catalogs.append(wrong_version)

        duplicate_skill = deepcopy(catalog)
        duplicate_skill["skills"]["codex"].append("agent-matrix")
        invalid_catalogs.append(duplicate_skill)

        missing_granular_shape = deepcopy(catalog)
        del missing_granular_shape["capabilities"]["codex"]["approval_policy"][
            "structured_value"
        ]
        invalid_catalogs.append(missing_granular_shape)

        broken_context = deepcopy(catalog)
        broken_context["context_modes"]["fresh"]["codex"] = []
        invalid_catalogs.append(broken_context)

        for invalid in invalid_catalogs:
            with self.subTest(catalog=invalid):
                with self.assertRaises(agent_matrix.CatalogError):
                    agent_matrix.validate_catalog(invalid)

        with self.assertRaisesRegex(agent_matrix.CatalogError, "scalar"):
            agent_matrix.validate_selection(
                catalog,
                provider="codex",
                capabilities={
                    "sandbox_mode": ["read-only", "workspace-write"]
                },
            )
        agent_matrix.validate_selection(
            catalog,
            provider="codex",
            capabilities={
                "skills": ["agent-matrix", "ak-guide"],
                "mcp_servers": ["openaiDeveloperDocs"],
            },
        )


class CodexInventoryTests(unittest.TestCase):
    def test_model_inventory_parser_accepts_only_strict_json(self):
        payload = {
            "models": [
                {
                    "slug": "gpt-5.6-sol",
                    "visibility": "list",
                    "supported_reasoning_levels": [
                        {"effort": "low"},
                        {"effort": "ultra"},
                    ],
                }
            ]
        }
        models = agent_matrix.parse_codex_models(json.dumps(payload))
        self.assertEqual(models[0]["slug"], "gpt-5.6-sol")
        self.assertEqual(models[0]["efforts"], ["low", "ultra"])

        with self.assertRaisesRegex(agent_matrix.InventoryError, "strict JSON"):
            agent_matrix.parse_codex_models(
                "WARNING: aliases unavailable\n" + json.dumps(payload)
            )
        payload["models"][0]["supported_reasoning_levels"] = []
        with self.assertRaisesRegex(agent_matrix.InventoryError, "no reasoning"):
            agent_matrix.parse_codex_models(json.dumps(payload))

    def test_plan_is_deterministic_and_covers_required_codex_dimensions(self):
        catalog = agent_matrix.load_catalog(CATALOG_PATH)
        models = [
            {
                "slug": "gpt-5.6-terra",
                "visible": True,
                "efforts": ["medium", "low"],
            },
            {
                "slug": "gpt-5.6-sol",
                "visible": True,
                "efforts": ["ultra", "low"],
            },
            {
                "slug": "gpt-5.2",
                "visible": False,
                "efforts": ["low"],
            },
        ]

        plan = agent_matrix.generate_codex_plan(
            catalog, models, tool_models={"gpt-5.6-terra"}
        )
        self.assertEqual(
            plan,
            agent_matrix.generate_codex_plan(
                catalog, list(reversed(models)), tool_models={"gpt-5.6-terra"}
            ),
        )

        model_cases = [
            case for case in plan["cases"] if case["kind"] == "model_effort"
        ]
        self.assertEqual(
            {
                (case["requested"]["model"], case["requested"]["reasoning_effort"])
                for case in model_cases
            },
            {
                ("gpt-5.6-sol", "low"),
                ("gpt-5.6-sol", "ultra"),
                ("gpt-5.6-terra", "low"),
                ("gpt-5.6-terra", "medium"),
            },
        )
        terra = next(
            case
            for case in model_cases
            if case["requested"]["model"] == "gpt-5.6-terra"
        )
        sol = next(
            case
            for case in model_cases
            if case["requested"]["model"] == "gpt-5.6-sol"
        )
        self.assertTrue(terra["catalog_visible"])
        self.assertTrue(terra["tool_exposed"])
        self.assertIsNone(terra["backend_accepted"])
        self.assertFalse(sol["tool_exposed"])

        case_names = [case["task_name"] for case in plan["cases"]]
        self.assertEqual(len(case_names), len(set(case_names)))
        self.assertTrue(
            all(re.fullmatch(r"[a-z0-9_]+", name) for name in case_names)
        )
        context_cases = {
            case["dimension"]
            for case in plan["cases"]
            if case["kind"] == "context"
        }
        self.assertEqual(context_cases, {"fresh", "full", "last_n_turns"})
        granular = {
            (
                case["requested"]["field"],
                case["requested"]["value"],
            )
            for case in plan["cases"]
            if case["kind"] == "config"
            and case["dimension"] == "approval_policy.granular"
        }
        expected_fields = {
            "sandbox_approval",
            "rules",
            "skill_approval",
            "request_permissions",
            "mcp_elicitations",
        }
        self.assertEqual(
            granular,
            {(field, value) for field in expected_fields for value in (False, True)},
        )
        negative_classes = {
            case["dimension"]
            for case in plan["cases"]
            if case["kind"] in {"negative", "spawn_contract"}
        }
        self.assertTrue(
            {
                "invalid_model",
                "invalid_effort",
                "invalid_context",
                "task_name_blank",
                "task_name_reserved",
                "task_name_invalid_characters",
                "message_blank",
                "agent_type_unknown",
                "agent_type_role_pinning",
                "service_tier_per_spawn",
                "full_history_agent_type",
                "full_history_model",
                "full_history_reasoning_effort",
            }
            <= negative_classes
        )
        service_tier = next(
            case
            for case in plan["cases"]
            if case["dimension"] == "service_tier_per_spawn"
        )
        self.assertFalse(service_tier["tool_exposed"])

        two_tool_plan = agent_matrix.generate_codex_plan(
            catalog,
            models,
            tool_models={"gpt-5.6-sol", "gpt-5.6-terra"},
        )
        full_model = next(
            case
            for case in two_tool_plan["cases"]
            if case["dimension"] == "full_history_model"
        )
        self.assertEqual(full_model["requested"]["model"], "gpt-5.6-terra")
        self.assertEqual(full_model["task_name"], "am_full_model_override_terra")

        with self.assertRaisesRegex(
            agent_matrix.CatalogError, "at least one --tool-model"
        ):
            agent_matrix.generate_codex_plan(catalog, models)
        invalid_effort = next(
            case
            for case in plan["cases"]
            if case["dimension"] == "invalid_effort"
        )
        role_pinning = next(
            case
            for case in plan["cases"]
            if case["dimension"] == "agent_type_role_pinning"
        )
        self.assertEqual(invalid_effort["requested"]["model"], "gpt-5.6-terra")
        self.assertEqual(role_pinning["requested"]["model"], "gpt-5.6-terra")
        self.assertEqual(role_pinning["expected"]["outcome"], "untestable")

        tracers = [case for case in plan["cases"] if case["kind"] == "tracer"]
        self.assertEqual(len(tracers), 1)
        self.assertEqual(tracers[0]["task_name"], "am_tracer_terra_low")
        self.assertTrue(tracers[0]["tool_exposed"])
        self.assertEqual(
            tracers[0]["requested"],
            {
                "message": "Reply with exactly: agent_matrix_ok",
                "fork_turns": "none",
                "model": "gpt-5.6-terra",
                "reasoning_effort": "low",
            },
        )
        valid_task_name = next(
            case
            for case in plan["cases"]
            if case["dimension"] == "task_name_valid"
        )
        self.assertEqual(valid_task_name["task_name"], "valid_task_1")
        self.assertEqual(valid_task_name["agent_path"], "/root/valid_task_1")
        self.assertTrue(
            all("tool_accepted" in case for case in plan["cases"])
        )
        self.assertEqual(
            plan["tool_contract_provenance"]["source"],
            "caller_supplied_active_spawn_schema",
        )


class ResultCollectionTests(unittest.TestCase):
    def test_collection_uses_child_rollout_turn_context_as_evidence(self):
        plan = {
            "cases": [
                {
                    "case_id": "matching",
                    "task_name": "matching",
                    "agent_path": "/root/matching",
                    "kind": "model_effort",
                    "requested": {
                        "model": "gpt-5.6-sol",
                        "reasoning_effort": "high",
                    },
                },
                {
                    "case_id": "mismatch",
                    "task_name": "mismatch",
                    "agent_path": "/root/mismatch",
                    "kind": "model_effort",
                    "requested": {
                        "model": "gpt-5.6-sol",
                        "reasoning_effort": "low",
                    },
                },
                {
                    "case_id": "missing",
                    "task_name": "missing",
                    "agent_path": "/root/missing",
                    "kind": "model_effort",
                    "requested": {
                        "model": "gpt-5.6-sol",
                        "reasoning_effort": "low",
                    },
                },
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            sessions = Path(directory)
            for task_name, effort in (("matching", "high"), ("mismatch", "xhigh")):
                rollout = sessions / task_name / "rollout.jsonl"
                rollout.parent.mkdir()
                events = [
                    {
                        "timestamp": "2026-07-23T10:00:00Z",
                        "type": "session_meta",
                        "payload": {"agent_path": f"/root/{task_name}"},
                    },
                    {
                        "timestamp": "2026-07-23T10:00:01Z",
                        "type": "turn_context",
                        "payload": {
                            "model": "gpt-5.6-sol",
                            "effort": effort,
                        },
                    },
                ]
                rollout.write_text(
                    "".join(json.dumps(event) + "\n" for event in events),
                    encoding="utf-8",
                )

            results = agent_matrix.collect_codex_results(plan, sessions)

        by_id = {result["case_id"]: result for result in results}
        self.assertEqual(by_id["matching"]["status"], "pass")
        self.assertEqual(by_id["mismatch"]["status"], "fail")
        self.assertEqual(by_id["missing"]["status"], "untestable")
        self.assertEqual(
            by_id["matching"]["observed"],
            {"model": "gpt-5.6-sol", "reasoning_effort": "high"},
        )
        self.assertFalse(Path(by_id["matching"]["rollout"]).is_absolute())

    def test_collection_prefers_exact_path_and_filters_prior_reruns(self):
        plan = {
            "cases": [
                {
                    "case_id": "rerun",
                    "task_name": "duplicate_leaf",
                    "agent_path": "/root/branch_a/duplicate_leaf",
                    "kind": "model_effort",
                    "catalog_visible": True,
                    "tool_exposed": True,
                    "tool_accepted": None,
                    "backend_accepted": None,
                    "requested": {
                        "model": "gpt-5.6-terra",
                        "reasoning_effort": "low",
                    },
                }
            ]
        }
        rollouts = [
            (
                "old_exact",
                "/root/branch_a/duplicate_leaf",
                "2026-07-23T09:00:00Z",
                "high",
            ),
            (
                "new_exact",
                "/root/branch_a/duplicate_leaf",
                "2026-07-23T11:00:00Z",
                "low",
            ),
            (
                "newer_wrong_branch",
                "/root/branch_b/duplicate_leaf",
                "2026-07-23T12:00:00Z",
                "xhigh",
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            sessions = Path(directory)
            for name, agent_path, timestamp, effort in rollouts:
                path = sessions / name / "rollout.jsonl"
                path.parent.mkdir()
                events = [
                    {
                        "timestamp": timestamp,
                        "type": "session_meta",
                        "payload": {"agent_path": agent_path},
                    },
                    {
                        "timestamp": timestamp,
                        "type": "turn_context",
                        "payload": {
                            "model": "gpt-5.6-terra",
                            "effort": effort,
                        },
                    },
                ]
                path.write_text(
                    "".join(json.dumps(event) + "\n" for event in events),
                    encoding="utf-8",
                )

            results = agent_matrix.collect_codex_results(
                plan,
                sessions,
                not_before="2026-07-23T10:00:00Z",
            )

        self.assertEqual(results[0]["status"], "pass")
        self.assertEqual(results[0]["rollout"], "new_exact/rollout.jsonl")
        self.assertTrue(results[0]["catalog_visible"])
        self.assertTrue(results[0]["tool_exposed"])
        self.assertTrue(results[0]["tool_accepted"])
        self.assertTrue(results[0]["backend_accepted"])

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                agent_matrix.CoverageError, "ISO8601"
            ):
                agent_matrix.collect_codex_results(
                    plan, Path(directory), not_before="yesterday"
                )

    def test_coverage_requires_one_terminal_result_per_planned_case(self):
        plan = {"cases": [{"case_id": "one"}, {"case_id": "two"}]}
        results = [
            {"case_id": "one", "status": "pass"},
            {"case_id": "two", "status": "unsupported"},
        ]
        report = agent_matrix.check_coverage(plan, results)
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["status_counts"]["pass"], 1)
        self.assertEqual(report["status_counts"]["unsupported"], 1)

        invalid_results = [
            results[:1],
            [results[0], results[0], results[1]],
            [results[0], {"case_id": "two", "status": "maybe"}],
        ]
        for invalid in invalid_results:
            with self.subTest(results=invalid):
                with self.assertRaises(agent_matrix.CoverageError):
                    agent_matrix.check_coverage(plan, invalid)

    def test_tool_observations_overlay_rollout_results_strictly(self):
        plan = {
            "cases": [
                {
                    "case_id": "tool_rejected",
                    "task_name": "tool_rejected",
                    "kind": "model_effort",
                    "catalog_visible": True,
                    "tool_exposed": False,
                    "expected": {"outcome": "accept"},
                    "requested": {},
                },
            ]
        }
        observations = [
            {
                "case_id": "tool_rejected",
                "status": "unsupported",
                "tool_accepted": False,
                "backend_accepted": None,
                "reason": "active spawn tool rejected the model",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            results = agent_matrix.collect_codex_results(
                plan, Path(directory), observations=observations
            )

        by_id = {result["case_id"]: result for result in results}
        self.assertEqual(by_id["tool_rejected"]["status"], "unsupported")
        self.assertFalse(by_id["tool_rejected"]["tool_accepted"])
        self.assertIsNone(by_id["tool_rejected"]["backend_accepted"])
        self.assertTrue(by_id["tool_rejected"]["catalog_visible"])
        self.assertFalse(by_id["tool_rejected"]["tool_exposed"])

        invalid = [
            observations + [observations[0]],
            [
                {
                    "case_id": "tool_rejected",
                    "status": "not_terminal",
                }
            ],
        ]
        for values in invalid:
            with self.subTest(observations=values):
                with tempfile.TemporaryDirectory() as directory:
                    with self.assertRaises(agent_matrix.CoverageError):
                        agent_matrix.collect_codex_results(
                            plan, Path(directory), observations=values
                        )

    def test_observation_evidence_contract_rejects_contradictions(self):
        base_case = {
            "task_name": "case",
            "catalog_visible": True,
            "tool_exposed": True,
            "requested": {},
        }
        cases = {
            "model": {
                **base_case,
                "case_id": "model",
                "kind": "model_effort",
                "expected": {"outcome": "accept"},
            },
            "config": {
                **base_case,
                "case_id": "config",
                "kind": "config",
                "expected": {"outcome": "parse_accept"},
            },
            "reject": {
                **base_case,
                "case_id": "reject",
                "kind": "negative",
                "expected": {"outcome": "reject"},
            },
            "accept": {
                **base_case,
                "case_id": "accept",
                "kind": "spawn_contract",
                "expected": {"outcome": "accept"},
            },
            "context": {
                **base_case,
                "case_id": "context",
                "kind": "context",
                "expected": {"outcome": "accept"},
            },
        }
        plan = {"cases": list(cases.values())}
        invalid = [
            {
                "case_id": "model",
                "status": "pass",
                "tool_accepted": True,
                "backend_accepted": True,
            },
            {
                "case_id": "config",
                "status": "pass",
                "tool_accepted": None,
                "backend_accepted": None,
            },
            {
                "case_id": "reject",
                "status": "pass",
                "tool_accepted": True,
                "backend_accepted": True,
            },
            {
                "case_id": "accept",
                "status": "pass",
                "tool_accepted": True,
                "backend_accepted": False,
            },
            {
                "case_id": "context",
                "status": "pass",
                "tool_accepted": True,
                "backend_accepted": True,
            },
            {
                "case_id": "accept",
                "status": "unsupported",
                "tool_accepted": False,
                "backend_accepted": False,
            },
            {
                "case_id": "accept",
                "status": "unsupported",
                "tool_accepted": False,
                "backend_accepted": None,
                "rollout": "forged.jsonl",
            },
            {
                "case_id": "accept",
                "status": "unsupported",
                "tool_accepted": False,
                "backend_accepted": None,
                "evidence_source": "forged",
            },
            {
                "case_id": "accept",
                "status": "unsupported",
                "tool_accepted": False,
                "backend_accepted": None,
                "observed": {"model": "forged"},
            },
            {
                "case_id": "accept",
                "status": "unsupported",
                "tool_accepted": False,
                "backend_accepted": None,
                "tool_exposed": False,
            },
        ]
        for observation in invalid:
            with self.subTest(observation=observation):
                with tempfile.TemporaryDirectory() as directory:
                    with self.assertRaises(agent_matrix.CoverageError):
                        agent_matrix.collect_codex_results(
                            plan,
                            Path(directory),
                            observations=[observation],
                        )

        with tempfile.TemporaryDirectory() as directory:
            rejection = agent_matrix.collect_codex_results(
                plan,
                Path(directory),
                observations=[
                    {
                        "case_id": "reject",
                        "status": "pass",
                        "tool_accepted": False,
                        "backend_accepted": None,
                        "reason": "the tool rejected the invalid request",
                    }
                ],
            )
        by_id = {result["case_id"]: result for result in rejection}
        self.assertEqual(by_id["reject"]["status"], "pass")
        self.assertFalse(by_id["reject"]["tool_accepted"])
        self.assertIsNone(by_id["reject"]["backend_accepted"])

        valid = [
            {
                "case_id": "config",
                "status": "pass",
                "tool_accepted": None,
                "backend_accepted": None,
                "parse_only": True,
            },
            {
                "case_id": "reject",
                "status": "pass",
                "tool_accepted": False,
                "backend_accepted": None,
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            results = agent_matrix.collect_codex_results(
                plan,
                Path(directory),
                observations=valid,
            )
        self.assertEqual(
            {result["case_id"] for result in results if result["status"] == "pass"},
            {"config", "reject"},
        )

    def test_tracer_gate_requires_exactly_one_matching_rollout_pass(self):
        plan = {
            "cases": [
                {
                    "case_id": "tracer",
                    "kind": "tracer",
                    "requested": {
                        "model": "gpt-5.6-terra",
                        "reasoning_effort": "low",
                    },
                }
            ]
        }
        result = {
            "case_id": "tracer",
            "status": "pass",
            "tool_accepted": True,
            "backend_accepted": True,
            "evidence_source": "child_rollout",
            "observed": {
                "model": "gpt-5.6-terra",
                "reasoning_effort": "low",
            },
        }
        report = agent_matrix.check_tracer(plan, [result])
        self.assertEqual(report["case_id"], "tracer")

        invalid_pairs = [
            ({"cases": []}, [result]),
            (
                {"cases": [plan["cases"][0], {**plan["cases"][0], "case_id": "two"}]},
                [result],
            ),
            (plan, [{**result, "status": "untestable"}]),
            (
                plan,
                [
                    {
                        **result,
                        "observed": {
                            "model": "gpt-5.6-sol",
                            "reasoning_effort": "low",
                        },
                    }
                ],
            ),
            (plan, [{**result, "evidence_source": "tool_observation"}]),
        ]
        for invalid_plan, invalid_results in invalid_pairs:
            with self.subTest(plan=invalid_plan, results=invalid_results):
                with self.assertRaises(agent_matrix.CoverageError):
                    agent_matrix.check_tracer(invalid_plan, invalid_results)


class CommandLineTests(unittest.TestCase):
    def test_plan_command_captures_stderr_separately_and_writes_explicit_output(self):
        payload = {
            "models": [
                {
                    "slug": "gpt-5.6-sol",
                    "visibility": "list",
                    "supported_reasoning_levels": [{"effort": "low"}],
                }
            ]
        }
        completed = SimpleNamespace(
            returncode=0,
            stdout=json.dumps(payload),
            stderr="WARNING: PATH aliases unavailable\n",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "plan.json"
            with mock.patch.object(
                agent_matrix.subprocess, "run", return_value=completed
            ) as run:
                exit_code = agent_matrix.main(
                    [
                        "plan-codex",
                        "--output",
                        str(output),
                        "--tool-model",
                        "gpt-5.6-sol",
                    ]
                )

            self.assertEqual(exit_code, 0)
            plan = json.loads(output.read_text(encoding="utf-8"))
            model_case = next(
                case for case in plan["cases"] if case["kind"] == "model_effort"
            )
            self.assertTrue(model_case["tool_exposed"])
            self.assertNotIn("WARNING", output.read_text(encoding="utf-8"))
            self.assertEqual(
                run.call_args.kwargs,
                {"capture_output": True, "text": True, "check": False},
            )

    def test_config_probe_uses_render_only_real_config_overrides(self):
        plan = {
            "cases": [
                {
                    "case_id": "sandbox",
                    "kind": "config",
                    "dimension": "sandbox_mode",
                    "requested": {
                        "field": "sandbox_mode",
                        "value": "danger-full-access",
                    },
                },
                {
                    "case_id": "permission",
                    "kind": "config",
                    "dimension": "permission_profile",
                    "requested": {
                        "field": "permission_profile",
                        "value": ":read-only",
                    },
                },
                {
                    "case_id": "granular",
                    "kind": "config",
                    "dimension": "approval_policy.granular",
                    "requested": {"field": "rules", "value": True},
                },
                {
                    "case_id": "skill",
                    "kind": "config",
                    "dimension": "skills",
                    "requested": {"field": "skills", "value": "agent-matrix"},
                },
                {
                    "case_id": "tools",
                    "kind": "config",
                    "dimension": "tool_access",
                    "requested": {
                        "field": "tool_access",
                        "value": "inherit_parent",
                    },
                },
                {"case_id": "ignored", "kind": "context"},
            ]
        }

        def completed(command, **kwargs):
            stdout = (
                json.dumps(
                    {
                        "prompt": (
                            "<skills_instructions>\n"
                            "- agent-matrix: Select Agent Matrix values.\n"
                            "</skills_instructions>"
                        )
                    }
                )
                if command[-1] == "verify configured skill discovery"
                else "[]"
            )
            return SimpleNamespace(
                returncode=0,
                stdout=stdout,
                stderr="separate warning\n",
            )

        with mock.patch.object(
            agent_matrix.subprocess, "run", side_effect=completed
        ) as run:
            results = agent_matrix.probe_codex_config(plan)

        self.assertEqual(
            {result["case_id"] for result in results},
            {"sandbox", "permission", "granular", "skill", "tools"},
        )
        by_id = {result["case_id"]: result for result in results}
        self.assertEqual(by_id["sandbox"]["status"], "pass")
        self.assertTrue(by_id["sandbox"]["parse_only"])
        self.assertIn("catalog_visible", by_id["sandbox"])
        self.assertIn("tool_exposed", by_id["sandbox"])
        self.assertIn("tool_accepted", by_id["sandbox"])
        self.assertIn("backend_accepted", by_id["sandbox"])
        self.assertEqual(by_id["sandbox"]["stderr"], "separate warning\n")
        self.assertEqual(by_id["skill"]["status"], "pass")
        self.assertEqual(by_id["tools"]["status"], "untestable")
        self.assertEqual(run.call_count, 4)

        commands = [call.args[0] for call in run.call_args_list]
        overrides = [
            command[command.index("-c") + 1]
            for command in commands
            if "-c" in command
        ]
        self.assertIn('sandbox_mode="danger-full-access"', overrides)
        self.assertIn('default_permissions=":read-only"', overrides)
        granular = next(
            override
            for override in overrides
            if override.startswith("approval_policy=")
        )
        self.assertIn("rules = true", granular)
        self.assertIn("sandbox_approval = false", granular)
        self.assertFalse(any("skills.config" in part for command in commands for part in command))
        self.assertTrue(
            all(command[:3] == ["codex", "debug", "prompt-input"] for command in commands)
        )

    def test_skill_probe_requires_exact_rendered_entry_and_honors_explicit_only_policy(self):
        plan = {
            "cases": [
                {
                    "case_id": "present",
                    "kind": "config",
                    "dimension": "skills",
                    "requested": {"field": "skills", "value": "agent-matrix"},
                },
                {
                    "case_id": "prompt_only",
                    "kind": "config",
                    "dimension": "skills",
                    "requested": {"field": "skills", "value": "ghost-skill"},
                },
                {
                    "case_id": "explicit_only",
                    "kind": "config",
                    "dimension": "skills",
                    "requested": {"field": "skills", "value": "deep-research"},
                },
            ]
        }
        rendered = {
            "items": [
                {
                    "role": "developer",
                    "content": (
                        "<skills_instructions>\n"
                        "- agent-matrix: Select Agent Matrix values.\n"
                        "</skills_instructions>"
                    ),
                },
                {
                    "role": "user",
                    "content": "Please invoke $ghost-skill and $deep-research.",
                },
            ]
        }
        completed = SimpleNamespace(
            returncode=0,
            stdout=json.dumps(rendered),
            stderr="",
        )
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            skill_root = repo_root / ".codex/skills/deep-research"
            (skill_root / "agents").mkdir(parents=True)
            (skill_root / "SKILL.md").write_text(
                "---\n"
                "name: deep-research\n"
                "description: Run explicit research.\n"
                "---\n",
                encoding="utf-8",
            )
            (skill_root / "agents/openai.yaml").write_text(
                "policy:\n  allow_implicit_invocation: false\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                agent_matrix.subprocess,
                "run",
                return_value=completed,
            ):
                results = agent_matrix.probe_codex_config(
                    plan,
                    repo_root=repo_root,
                )

        by_id = {result["case_id"]: result for result in results}
        self.assertEqual(by_id["present"]["status"], "pass")
        self.assertEqual(by_id["prompt_only"]["status"], "fail")
        self.assertEqual(by_id["explicit_only"]["status"], "untestable")
        self.assertEqual(
            by_id["explicit_only"]["evidence"],
            "valid_skill_frontmatter_and_explicit_only_policy",
        )

    def test_probe_and_observation_cli_paths_write_explicit_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.json"
            probe_output = root / "probe" / "results.jsonl"
            observations_path = root / "observations.jsonl"
            empty_observations_path = root / "empty-observations.jsonl"
            collected_jsonl = root / "collected" / "results.jsonl"
            collected_markdown = root / "collected" / "results.md"
            codex_home = root / "codex-home"
            (codex_home / "sessions").mkdir(parents=True)
            plan = {
                "cases": [
                    {
                        "case_id": "tools",
                        "task_name": "tools",
                        "kind": "config",
                        "dimension": "tool_access",
                        "expected": {"outcome": "parse_accept"},
                        "requested": {
                            "field": "tool_access",
                            "value": "inherit_parent",
                        },
                    }
                ]
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            self.assertEqual(
                agent_matrix.main(
                    [
                        "probe-codex-config",
                        "--plan",
                        str(plan_path),
                        "--output-jsonl",
                        str(probe_output),
                    ]
                ),
                0,
            )
            probe_result = json.loads(
                probe_output.read_text(encoding="utf-8").strip()
            )
            self.assertEqual(probe_result["status"], "untestable")

            observations_path.write_text(
                json.dumps(
                    {
                        "case_id": "tools",
                        "status": "unsupported",
                        "tool_accepted": False,
                        "backend_accepted": None,
                        "reason": "tool schema has no per-spawn tool access field",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            empty_observations_path.write_text("", encoding="utf-8")
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
                self.assertEqual(
                    agent_matrix.main(
                        [
                            "collect-codex",
                            "--plan",
                            str(plan_path),
                            "--observations",
                            str(observations_path),
                            "--observations",
                            str(empty_observations_path),
                            "--not-before",
                            "2026-07-23T00:00:00Z",
                            "--output-jsonl",
                            str(collected_jsonl),
                            "--output-markdown",
                            str(collected_markdown),
                        ]
                    ),
                    0,
                )
            collected = json.loads(
                collected_jsonl.read_text(encoding="utf-8").strip()
            )
            self.assertEqual(collected["status"], "unsupported")
            self.assertFalse(collected["tool_accepted"])
            self.assertIsNone(collected["backend_accepted"])
            self.assertEqual(collected["evidence_source"], "tool_observation")

    def test_check_tracer_command_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.json"
            results_path = root / "results.jsonl"
            plan_path.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "case_id": "tracer",
                                "kind": "tracer",
                                "requested": {
                                    "model": "gpt-5.6-terra",
                                    "reasoning_effort": "low",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            results_path.write_text(
                json.dumps(
                    {
                        "case_id": "tracer",
                        "status": "untestable",
                        "tool_accepted": None,
                        "backend_accepted": None,
                        "observed": None,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                agent_matrix.main(
                    [
                        "check-tracer",
                        "--plan",
                        str(plan_path),
                        "--results",
                        str(results_path),
                    ]
                ),
                2,
            )


if __name__ == "__main__":
    unittest.main()
