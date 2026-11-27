from ovas_api.config import get_settings


async def test_health_reports_db_ok_and_unreachable_services(client, monkeypatch):  # M0 AC-3
    settings = get_settings()
    monkeypatch.setattr(settings, "runtime_url", "http://127.0.0.1:9")
    monkeypatch.setattr(settings, "tts_url", "http://127.0.0.1:9")
    monkeypatch.setattr(settings, "stt_url", "http://127.0.0.1:9")
    body = (await client.get("/health")).json()
    assert body["api"]["status"] == "ok"
    assert body["db"]["status"] == "ok"
    assert body["runtime"]["status"] == "unreachable"
    assert body["tts"]["status"] == "unreachable"
    assert body["stt"]["status"] == "unreachable"
