import base64
from io import BytesIO
import json
import os
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from backend.app import gemini, retrieval
from backend.app.copilot import execute_tool
from backend.app.main import app
from backend.app.saathi import Question, SOURCES
from backend.app.vision import clean_image, Photo


def photo_body():
    image = Image.new("RGB", (32, 32), "white")
    data = BytesIO()
    image.save(data, "PNG")
    return {"image_base64": base64.b64encode(data.getvalue()).decode(), "mime_type": "image/png"}


class VisionTests(unittest.TestCase):
    def setUp(self):
        self.client = self.enterContext(TestClient(app))

    def test_reference_and_provider_failure(self):
        for enabled in (False, True):
            with patch.object(gemini, "enabled", return_value=enabled), patch.object(gemini, "generate", return_value=None):
                response = self.client.post("/purifier/analyze", json=photo_body())
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertEqual(response.json()["mode"], "reference")
                self.assertIsNone(response.json()["observation"])

    def test_observations_and_explicit_confirmation(self):
        observed = {"purifier_visible": True, "filter_condition": "visible_dust", "clearance": "possibly_blocked",
                    "cadr_label_legible": True, "cadr_m3h": 200}
        with patch.object(gemini, "enabled", return_value=True), patch.object(gemini, "generate", return_value=NS(text=json.dumps(observed))) as generate:
            response = self.client.post("/purifier/analyze", json=photo_body() | {"language": "hi"})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["requires_confirmation"])
            self.assertEqual(response.json()["observation"]["cadr_m3h"], 200)
            self.assertEqual(len(response.json()["guidance"]), 5)
            contents = generate.call_args.args[0]
            self.assertEqual(contents[0].parts[1].inline_data.mime_type, "image/jpeg")
            self.assertNotIn("tools", generate.call_args.kwargs)
        observed["cadr_label_legible"] = False
        with patch.object(gemini, "enabled", return_value=True), patch.object(gemini, "generate", return_value=NS(text=json.dumps(observed))):
            self.assertEqual(self.client.post("/purifier/analyze", json=photo_body()).json()["mode"], "reference")

    def test_invalid_files_and_body_bounds_never_reach_provider(self):
        bad = [photo_body() | {"image_base64": "not-base64"}, photo_body() | {"mime_type": "image/jpeg"},
               {"mime_type": "image/png", "image_base64": base64.b64encode(b'hello').decode()}]
        with patch.object(gemini, "generate") as generate:
            for body in bad:
                self.assertEqual(self.client.post("/purifier/analyze", json=body).status_code, 422)
            response = self.client.post("/purifier/analyze", content=b'x' * 1500001, headers={"Content-Type": "application/json"})
            self.assertEqual(response.status_code, 413)
            generate.assert_not_called()

    def test_image_metadata_removed_and_large_dimensions_rejected(self):
        image = Image.new("RGB", (40, 40))
        exif = Image.Exif()
        exif[270] = "private location and instructions"
        raw = BytesIO()
        image.save(raw, "JPEG", exif=exif)
        photo = Photo(image_base64=base64.b64encode(raw.getvalue()).decode(), mime_type="image/jpeg")
        self.assertFalse(Image.open(BytesIO(clean_image(photo))).getexif())
        image = Image.new("RGB", (3000, 3000))
        raw = BytesIO()
        image.save(raw, "PNG")
        body = {"image_base64": base64.b64encode(raw.getvalue()).decode(), "mime_type": "image/png"}
        self.assertEqual(self.client.post("/purifier/analyze", json=body).status_code, 422)


class GroundingTests(unittest.TestCase):
    @patch.dict(os.environ, {"GEMINI_API_KEY": "fixture", "GEMINI_EMBEDDING_MODEL": "gemini-embedding-001"})
    def test_sdk_embedding_task_dimension_and_normalization(self):
        with patch.object(retrieval, "provider_slot", return_value=True), patch.object(retrieval.genai, "Client") as client:
            models = client.return_value.__enter__.return_value.models
            models.embed_content.return_value = NS(embeddings=[NS(values=[3.0, 4.0] + [0.0] * 766)])
            vector = json.loads(retrieval.embedding("सवाल", "gemini-embedding-001", "RETRIEVAL_QUERY"))
            self.assertEqual(vector[:2], [0.6, 0.8])
            config = models.embed_content.call_args.kwargs["config"]
            self.assertEqual(config.output_dimensionality, 768)
            self.assertEqual(config.task_type, "RETRIEVAL_QUERY")
            for invalid in ([0] * 768, [float("nan")] * 768, [1] * 767, [True] * 768):
                models.embed_content.return_value = NS(embeddings=[NS(values=invalid)])
                with self.assertRaises(ValueError):
                    retrieval.embedding("question", "gemini-embedding-001", "RETRIEVAL_QUERY")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fixture", "GEMINI_EMBEDDING_MODEL": "gemini-embedding-001", "RAG_SIMILARITY_MIN": "0.75"})
    def test_similarity_floor_and_source_version(self):
        with patch.object(retrieval, "connect") as connect, patch.object(retrieval, "embedding", return_value="[1]"):
            db = connect.return_value.__enter__.return_value
            db.execute.return_value.fetchone.return_value = (True,)
            db.execute.return_value.fetchall.return_value = [("size", .9), ("filter", .2), ("unknown", 1), ("aqi", float("nan"))]
            self.assertEqual(retrieval.retrieve("question", SOURCES), ["size"])
            sql, values = db.execute.call_args.args
            self.assertIn("LIMIT 5", sql)
            self.assertIn(retrieval.library_version(SOURCES), values)
            with patch.dict(os.environ, {"RAG_SIMILARITY_MIN": "nan"}):
                self.assertEqual(retrieval.retrieve("question", SOURCES), [])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fixture", "GEMINI_EMBEDDING_MODEL": "gemini-embedding-001"})
    def test_missing_index_and_service_failure_fall_back(self):
        with patch.object(retrieval, "connect") as connect, patch.object(retrieval, "embedding") as embed:
            db = connect.return_value.__enter__.return_value
            db.execute.return_value.fetchone.return_value = (None,)
            self.assertEqual(retrieval.retrieve("question", SOURCES), [])
            embed.assert_not_called()
            connect.side_effect = RuntimeError("provider unavailable")
            self.assertEqual(retrieval.retrieve("question", SOURCES), [])

    def test_copilot_semantic_passages_keep_verified_urls(self):
        with patch.object(gemini, "enabled", return_value=True), patch("backend.app.copilot.retrieve", return_value=["filter"]):
            result = execute_tool("search_reviewed_sources", {}, None, None, Question(question="Is servicing needed?", language="hi"))
            self.assertEqual(list(result), ["filter"])
            self.assertEqual(result["filter"]["url"], SOURCES["filter"][1])
            self.assertEqual(result["filter"]["text"], SOURCES["filter"][4])

class SDKWireTests(unittest.TestCase):
    @patch.dict(os.environ, {"LLM_MODE": "live", "GEMINI_API_KEY": "fixture"})
    def test_real_sdk_serializes_native_tools_and_structured_evidence(self):
        import httpx
        from google import genai
        from backend.app.copilot import live_answer
        from google.genai import types
        sent = []
        def transport(request):
            body = json.loads(request.content)
            sent.append(body)
            if len(sent) == 1:
                payload = {"candidates": [{"content": {"role": "model", "parts": [{"functionCall": {
                    "name": "search_reviewed_sources", "args": {}, "id": "call-1"}}]}, "finishReason": "STOP"}]}
            else:
                payload = {"candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps({
                    "passage_ids": ["size"], "include_air": False, "include_room": False, "include_commute": False})}]}, "finishReason": "STOP"}]}
            return httpx.Response(200, json=payload)
        factory = genai.Client
        def client(**kwargs):
            return factory(api_key="fixture", http_options=types.HttpOptions(client_args={"transport": httpx.MockTransport(transport), "trust_env": False}, async_client_args={"trust_env": False}))
        with patch.object(gemini, "provider_slot", return_value=True), patch.object(gemini.genai, "Client", side_effect=client):
            result = live_answer(Question(question="What is CADR?"), None, None)
        self.assertIsNotNone(result)
        self.assertEqual(result["citations"][0]["id"], "size")
        self.assertIn("tools", sent[0])
        self.assertNotIn("responseSchema", sent[0].get("generationConfig", {}))
        self.assertNotIn("tools", sent[1])
        self.assertEqual(sent[1]["generationConfig"]["responseMimeType"], "application/json")
        self.assertNotIn("responseSchema", sent[1]["generationConfig"])
        schema = sent[1]["generationConfig"]["responseJsonSchema"]
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("additional_properties", json.dumps(schema))
        self.assertEqual(sent[1]["contents"][-1]["parts"][0]["functionResponse"]["id"], "call-1")


class ProviderTimeoutTests(unittest.TestCase):
    def test_configured_timeout_is_bounded_and_shared(self):
        for value, expected in (("20000", 20000), ("999999", 30000), ("0", 1000), ("invalid", 15000)):
            with patch.dict(os.environ, {"GEMINI_TIMEOUT_MS": value}):
                self.assertEqual(gemini.http_options().timeout, expected)
                self.assertEqual(retrieval.http_options().timeout, expected)
                self.assertEqual(gemini.http_options().retry_options.attempts, 1)
