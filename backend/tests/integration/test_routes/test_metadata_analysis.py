from __future__ import annotations

from unittest import mock

import pytest
from quart.typing import TestClientProtocol as Client

from beets_flask.invoker.enqueue import run_analyze_attributes


class FakeItem:
    def __init__(self, item_id: int, path: str) -> None:
        self.id = item_id
        self.path = path
        self.bpm: int | None = None
        self.initial_key: str | None = None
        self._store_calls = 0
        self._write_calls = 0

    def store(self) -> None:
        self._store_calls += 1

    def try_write(self) -> None:
        self._write_calls += 1


class FakeLibrary:
    def __init__(self, items: list[FakeItem]) -> None:
        self._items = {itm.id: itm for itm in items}
        self.conn = mock.Mock()
        self._connection = mock.Mock()

    def get_item(self, item_id: int) -> FakeItem | None:
        return self._items.get(item_id)


class TestMetadataAnalysis:
    @pytest.fixture(autouse=True)
    def setup_items(self):
        self.item1 = FakeItem(1, "/tmp/track1.mp3")
        self.item2 = FakeItem(2, "/tmp/track2.mp3")
        self.fake_library = FakeLibrary([self.item1, self.item2])

    @mock.patch("beets_flask.invoker.enqueue._analyze_bpm")
    @mock.patch("beets_flask.invoker.enqueue._analyze_key")
    async def test_run_analyze_attributes(self, mock_analyze_key, mock_analyze_bpm):
        """Verify that the analysis job updates items and stores results."""

        mock_analyze_bpm.side_effect = [128.4, 130.2]
        mock_analyze_key.side_effect = ["Cm", "Gm"]

        results = await run_analyze_attributes(
            [self.item1.id, self.item2.id],
            lib=self.fake_library,
            close_library=False,
        )

        assert len(results["analyzed"]) == 2
        assert not results["errors"]

        assert self.item1.bpm == 128
        assert self.item1.initial_key == "Cm"
        assert self.item1._store_calls == 1
        assert self.item1._write_calls == 1

        assert self.item2.bpm == 130
        assert self.item2.initial_key == "Gm"
        assert self.item2._store_calls == 1
        assert self.item2._write_calls == 1

    @mock.patch(
        "beets_flask.server.routes.library.metadata.enqueue_analyze_attributes"
    )
    async def test_analyze_endpoint(self, mock_enqueue, client: Client):
        """POST /api/library/analyze enqueues a background job."""

        mock_job = mock.Mock()
        mock_job.id = "job-123"
        mock_enqueue.return_value = mock_job

        with mock.patch(
            "beets_flask.server.routes.library._open_library",
            return_value=self.fake_library,
        ):
            response = await client.post(
                "/api_v1/library/analyze",
                json={
                    "item_ids": [self.item1.id, self.item2.id],
                    "analyze_bpm": True,
                    "analyze_key": False,
                },
            )

        body = await response.get_json()
        assert response.status_code == 202
        assert body == {"job_id": "job-123", "status": "queued"}
        mock_enqueue.assert_called_once_with([1, 2], True, False)

    async def test_analyze_endpoint_validation(self, client: Client):
        with mock.patch(
            "beets_flask.server.routes.library._open_library",
            return_value=self.fake_library,
        ):
            response = await client.post("/api_v1/library/analyze", json={})
        assert response.status_code == 400

        with mock.patch(
            "beets_flask.server.routes.library._open_library",
            return_value=self.fake_library,
        ):
            response = await client.post(
                "/api_v1/library/analyze", json={"item_ids": "not-a-list"}
            )
        assert response.status_code == 400

    @mock.patch("beets_flask.invoker.enqueue.shutil.which")
    @mock.patch("beets_flask.invoker.enqueue.subprocess.run")
    async def test_analyze_key_execution(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/keyfinder-cli"
        mock_process = mock.Mock(returncode=0, stdout="file.mp3\tAm", stderr="")
        mock_run.return_value = mock_process

        with mock.patch("beets_flask.invoker.enqueue._analyze_bpm", return_value=None):
            await run_analyze_attributes(
                [self.item1.id],
                analyze_bpm=False,
                analyze_key=True,
                lib=self.fake_library,
                close_library=False,
            )

        assert self.item1.initial_key == "Am"
        mock_run.assert_called_once()

    @mock.patch("beets_flask.invoker.enqueue.shutil.which")
    async def test_analyze_key_missing_binary(self, mock_which):
        mock_which.return_value = None

        with mock.patch("beets_flask.invoker.enqueue._analyze_bpm", return_value=None):
            results = await run_analyze_attributes(
                [self.item1.id],
                analyze_bpm=False,
                analyze_key=True,
                lib=self.fake_library,
                close_library=False,
            )

        assert len(results["analyzed"]) == 1
        assert self.item1.initial_key is None
