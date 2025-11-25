import pytest
import beets_flask.server.routes.config as config_mod


@pytest.mark.asyncio
async def test_get_all(client):
    # Basic smoke test that the endpoint responds
    response = await client.get("/api_v1/config/all")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_basic(client):
    response = await client.get("/api_v1/config/")

    assert response.status_code == 200

    data = await response.get_json()

    assert "gui" in data
    assert "import" in data
    assert "match" in data


@pytest.mark.asyncio
async def test_get_metadata_plugins(client, monkeypatch):
    fake_plugins = {
        "discogs": {"enabled": True, "settings": {"user_agent": "ua"}},
        "spotify": {"enabled": False, "settings": {}},
    }

    class DummyService:
        def get_metadata_plugins_config(self):
            return fake_plugins

    # Route will call ConfigService(), so replace it with our dummy
    monkeypatch.setattr(config_mod, "ConfigService", DummyService)

    response = await client.get("/api_v1/config/metadata_plugins")
    assert response.status_code == 200

    data = await response.get_json()
    assert data == fake_plugins


@pytest.mark.asyncio
async def test_update_metadata_plugin_success(client, monkeypatch):
    calls = []

    class DummyService:
        def update_metadata_plugin_config(self, plugin_name, settings, enabled):
            calls.append((plugin_name, settings, enabled))

    monkeypatch.setattr(config_mod, "ConfigService", DummyService)

    payload = {
        "plugin": "discogs",
        "enabled": True,
        "settings": {"token": "abc123"},
    }

    response = await client.post(
        "/api_v1/config/metadata_plugins",
        json=payload,
    )

    assert response.status_code == 200
    data = await response.get_json()
    assert data == {"status": "ok"}
    assert calls == [("discogs", {"token": "abc123"}, True)]


@pytest.mark.asyncio
async def test_update_metadata_plugin_missing_plugin_name(client):
    payload = {
        "enabled": True,
        "settings": {},
    }

    response = await client.post(
        "/api_v1/config/metadata_plugins",
        json=payload,
    )

    assert response.status_code == 400
    data = await response.get_json()
    assert "error" in data


@pytest.mark.asyncio
async def test_update_metadata_plugin_invalid_enabled_type(client):
    payload = {
        "plugin": "discogs",
        "enabled": "yes",  # should be boolean
        "settings": {},
    }

    response = await client.post(
        "/api_v1/config/metadata_plugins",
        json=payload,
    )

    assert response.status_code == 400
    data = await response.get_json()
    assert "error" in data


@pytest.mark.asyncio
async def test_update_metadata_plugin_service_500(client, monkeypatch):
    class DummyService:
        def update_metadata_plugin_config(self, plugin_name, settings, enabled):
            raise RuntimeError("boom")

    monkeypatch.setattr(config_mod, "ConfigService", DummyService)

    payload = {
        "plugin": "discogs",
        "enabled": True,
        "settings": {},
    }

    response = await client.post(
        "/api_v1/config/metadata_plugins",
        json=payload,
    )

    assert response.status_code == 500
    data = await response.get_json()
    assert "error" in data
