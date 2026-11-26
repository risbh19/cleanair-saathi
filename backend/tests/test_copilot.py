import json
import os
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from google.genai import types

from backend.app import gemini
from backend.app.copilot import household_context, live_answer, plan_actions
from backend.app.engine.actions import daily_actions
from backend.app.main import app
from backend.app.saathi import Question
from backend.tests.test_households import PROFILE


def response(data):
    return NS(text=json.dumps(data))


def call_response(*names):
    parts = [types.Part(function_call=types.FunctionCall(name=n, args={}, id="call-" + n)) for n in names]
    content = types.Content(role="model", parts=parts)
    return NS(function_calls=[p.function_call for p in parts], candidates=[NS(content=content)])


class CopilotTests(unittest.TestCase):
    def test_profile_minimization(self):
        p = deepcopy(PROFILE) | {"id": "secret", "session_digest": "token"}
        data = json.dumps(household_context(p))
        for private in ("secret", "token", "Central Delhi", "08:30", "lat", "lon"):
            self.assertNotIn(private, data)
        self.assertIn('"distance_km": 7', data)

    @patch.dict(os.environ, {"LLM_MODE": "live", "GEMINI_API_KEY": "fixture"})
    def test_structured_plan_preserves_catalogue_and_priority(self):
        actions = daily_actions(PROFILE, "Severe")
        result = response({"items": [{"action_id": a["id"], "time_of_day": "evening"} for a in reversed(actions)]})
        with patch.object(gemini, "generate", return_value=result) as generate:
            plan = plan_actions(actions, "Severe", PROFILE, None)
        self.assertEqual(plan[0]["id"], "move_activity_indoors")
        self.assertEqual({a["id"] for a in plan}, {a["id"] for a in actions})
        self.assertEqual(plan[0]["en"], actions[0]["en"])
        self.assertEqual(plan[0]["time_of_day"], "anytime")
        self.assertIn("schema", generate.call_args.kwargs)
        for items in ([{"action_id": "invented", "time_of_day": "morning"}],
                      [{"action_id": actions[0]["id"], "time_of_day": "evening"}] * len(actions),
                      [{"action_id": a["id"], "time_of_day": "night"} for a in actions]):
            with patch.object(gemini, "generate", return_value=response({"items": items})):
                self.assertEqual(plan_actions(actions, "Severe", PROFILE, None), actions)
        with patch.object(gemini, "generate", return_value=None):
            self.assertEqual(plan_actions(actions, "Severe", PROFILE, None), actions)

    def test_native_function_round_trip_and_citations(self):
        with TestClient(app) as client:
            request = NS(app=app)
            first = call_response("search_reviewed_sources", "get_household_context")
            last = response({"passage_ids": ["size"], "include_air": False, "include_room": False})
            with patch.object(gemini, "generate", side_effect=[first, last]) as generate:
                result = live_answer(Question(question="What CADR suits my room?"), request, PROFILE)
            self.assertEqual(result["mode"], "gemini")
            self.assertEqual(result["citations"][0]["id"], "size")
            self.assertEqual(result["tools_used"], ["search_reviewed_sources", "get_household_context"])
            contents = generate.call_args.args[0]
            self.assertEqual(contents[1], first.candidates[0].content)
            self.assertEqual(contents[2].parts[0].function_response.name, "search_reviewed_sources")
            self.assertEqual(contents[2].parts[0].function_response.id, "call-search_reviewed_sources")

    def test_unknown_tool_and_fabricated_citation_fail_closed(self):
        with patch.object(gemini, "generate", return_value=call_response("delete_household")):
            self.assertIsNone(live_answer(Question(question="CADR?"), None, PROFILE))
        with patch.object(gemini, "generate", side_effect=[call_response("search_reviewed_sources"),
                response({"passage_ids": ["invented"], "include_air": False, "include_room": False})]):
            self.assertIsNone(live_answer(Question(question="CADR?"), None, PROFILE))

    def test_http_fallback_privacy_and_medical_refusal(self):
        with TestClient(app) as client, patch.object(gemini, "enabled", return_value=True), patch.object(gemini, "generate", return_value=None):
            reply = client.post("/chat", json={"question": "What is CADR?"})
            self.assertEqual(reply.status_code, 200)
            self.assertEqual(reply.headers["Cache-Control"], "no-store")
            self.assertEqual(reply.json()["mode"], "reference")
            with patch("backend.app.copilot.live_answer") as live:
                self.assertFalse(client.post("/chat", json={"question": "medicine dose?"}).json()["citations"])
                live.assert_not_called()
            self.assertEqual(client.post("/chat", headers={"Authorization": "Bearer invalid"}, json={"question": "CADR?"}).status_code, 401)

    @patch.dict(os.environ, {"LLM_MODE": "live", "GEMINI_API_KEY": "fixture"})
    def test_sdk_configuration_and_failure(self):
        with patch.object(gemini, "provider_slot", return_value=True), patch.object(gemini.genai, "Client") as client:
            model = client.return_value.__enter__.return_value.models
            model.generate_content.return_value = response([])
            self.assertIsNotNone(gemini.generate("question", system="test", schema=list[str]))
            config = model.generate_content.call_args.kwargs["config"]
            self.assertEqual(config.response_mime_type, "application/json")
            self.assertTrue(config.automatic_function_calling.disable)
            self.assertEqual(client.call_args.kwargs["http_options"].retry_options.attempts, 1)
            model.generate_content.side_effect = TimeoutError()
            self.assertIsNone(gemini.generate("question", system="test"))
        with patch.object(gemini, "provider_slot", return_value=False):
            self.assertIsNone(gemini.generate("question", system="test"))

    def test_room_tool_uses_saved_profile_and_blocks_stale_live_air(self):
        from backend.app.copilot import execute_tool
        brief = {"hourly_pm25_ug_m3": 100, "data_mode": "live", "stale": False}
        with patch("backend.app.copilot.air_context", return_value=brief):
            result = execute_tool("simulate_household_room", {}, None, PROFILE, Question(question="room?"))
            self.assertEqual(result["simulation"]["room_volume_m3"], 12 * 2.7)
            self.assertEqual(result["simulation"]["assumptions"]["purifier_cadr_m3_h"], 0)
        with patch("backend.app.copilot.air_context", return_value=brief | {"stale": True}):
            self.assertEqual(execute_tool("simulate_household_room", {}, None, PROFILE, Question(question="room?")), {"unavailable": True})
        self.assertEqual(execute_tool("simulate_household_room", {}, None, None, Question(question="room?")), {"unavailable": True})
