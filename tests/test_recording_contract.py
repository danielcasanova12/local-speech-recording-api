import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.routes.recording import remote_upload_service
from app.schemas.recording import RecordingStartRequest, RecordingStopRequest, UploadRecordingRequest
from app.services import metadata_service
from app.services.remote_upload_service import RemoteUploadService


USER_ID = "eeb16762-def1-45fc-aac6-e71c779b5ad3"


class RecordingSchemaTests(unittest.TestCase):
    def test_recording_requests_accept_uuid_user_id(self):
        common = {
            "user_id": USER_ID,
            "id_recordings": 1784551800469,
            "session_id": 253,
        }
        start = RecordingStartRequest(
            **common,
            dataset_id=1,
            bloco_id=11,
            frase_content="Teste",
            created_at="2026-07-20T00:00:00Z",
        )

        self.assertEqual(start.user_id, UUID(USER_ID))
        self.assertEqual(start.model_dump(mode="json")["user_id"], USER_ID)
        self.assertEqual(RecordingStopRequest(**common).user_id, UUID(USER_ID))
        self.assertEqual(UploadRecordingRequest(user_id=USER_ID).user_id, UUID(USER_ID))

    def test_metadata_paths_support_uuid_user_id(self):
        metadata = {
            "user_id": USER_ID,
            "session_id": 253,
            "id_recordings": 1784551800469,
        }
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            metadata_service, "RECORDINGS_DIR", Path(temp_dir)
        ):
            path = metadata_service.save_metadata(metadata)

            self.assertEqual(path.parent.parent.name, USER_ID)
            self.assertEqual(metadata_service.load_metadata(path), metadata)


class RemoteUploadTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload_matches_remote_multipart_contract(self):
        metadata = {
            "user_id": USER_ID,
            "id_recordings": 1784551800469,
            "session_id": 253,
            "dataset_id": 1,
            "bloco_id": 11,
            "frase_id": None,
            "is_test": False,
            "duration": 2.5,
            "format": "wav",
            "sample_rate": 48000,
            "frase_content": "Teste",
            "room_tone_start": 0.0,
            "room_tone_end": 0.0,
            "created_at": "2026-07-20T00:00:00Z",
            "extra_info": {"source": "local"},
        }

        class FakeAsyncClient:
            request_kwargs = None

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, _url, **kwargs):
                type(self).request_kwargs = kwargs
                return httpx.Response(
                    201,
                    json={"id_recordings": 10},
                    request=httpx.Request("POST", "https://example.test/api/v1/recordings"),
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            wav = Path(temp_dir) / "recording.wav"
            wav.write_bytes(b"RIFF-test")
            with (
                patch.object(metadata_service, "wav_path", return_value=wav),
                patch.object(metadata_service, "save_metadata"),
                patch("app.services.remote_upload_service.httpx.AsyncClient", FakeAsyncClient),
            ):
                result = await RemoteUploadService().upload(
                    Path(temp_dir) / "recording.json",
                    metadata,
                    authorization="Bearer token",
                )

        request_kwargs = FakeAsyncClient.request_kwargs
        self.assertTrue(result["success"])
        self.assertIn("audio_file", request_kwargs["files"])
        self.assertNotIn("file", request_kwargs["files"])
        self.assertNotIn("id_recordings", request_kwargs["data"])
        self.assertNotIn("created_at", request_kwargs["data"])
        self.assertNotIn("frase_id", request_kwargs["data"])
        self.assertEqual(request_kwargs["headers"], {"Authorization": "Bearer token"})


class UploadEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.metadata = {
            "user_id": USER_ID,
            "id_recordings": 1784551800469,
            "session_id": 253,
        }

    def test_upload_accepts_quoted_uuid_and_forwards_bearer_token(self):
        upload = AsyncMock(return_value={"success": True, "remote_status_code": 201})
        with (
            patch.object(metadata_service, "find_by_id_recordings", return_value=(Path("recording.json"), self.metadata)),
            patch.object(remote_upload_service, "upload", upload),
        ):
            response = self.client.post(
                "/api/recordings/1784551800469/upload",
                headers={"Authorization": "Bearer token"},
                json={"user_id": USER_ID},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(upload.await_args.kwargs["authorization"], "Bearer token")

    def test_upload_requires_bearer_token(self):
        response = self.client.post(
            "/api/recordings/1784551800469/upload",
            json={"user_id": USER_ID},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("Authorization", response.json()["detail"])

    def test_upload_keeps_legacy_numeric_recordings_compatible(self):
        legacy_metadata = {**self.metadata, "user_id": 253}
        upload = AsyncMock(return_value={"success": True, "remote_status_code": 201})
        with (
            patch.object(
                metadata_service,
                "find_by_id_recordings",
                return_value=(Path("recording.json"), legacy_metadata),
            ),
            patch.object(remote_upload_service, "upload", upload),
        ):
            response = self.client.post(
                "/api/recordings/1784551800469/upload",
                headers={"Authorization": "Bearer token"},
                json={"user_id": USER_ID},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_unquoted_uuid_is_invalid_json(self):
        response = self.client.post(
            "/api/recordings/1784551800469/upload",
            headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
            content=f'{{"user_id":{USER_ID}}}',
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"][0]["type"], "json_invalid")


if __name__ == "__main__":
    unittest.main()
