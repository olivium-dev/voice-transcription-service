from __future__ import annotations


def _post(client, *, content=b"FAKE-AUDIO-BYTES", filename="hello.m4a", content_type="audio/mp4"):
    return client.post(
        "/transcribe",
        files={"audio": (filename, content, content_type)},
    )


def test_transcribe_returns_text_for_arabic_audio(client, whisper_stub):
    response = _post(client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["transcription"] == "مرحبا"
    assert body["language"] == "ar"
    assert body["storage_uri"].startswith("s3://jeeb-voice-audio-test/voice/")
    # Whisper was called once with the original audio (well below 5 MB threshold).
    assert len(whisper_stub.calls) == 1
    assert whisper_stub.calls[0]["content_type"] == "audio/mp4"


def test_transcribe_stores_original_audio(client, s3_storage, settings):
    response = _post(client)
    body = response.json()
    key = body["storage_uri"].removeprefix(f"s3://{settings.storage_bucket}/")
    assert s3_storage.head(key) is True


def test_transcribe_queues_when_whisper_unavailable(client, whisper_stub, retry_queue, settings):
    whisper_stub.raise_unavailable = True
    response = _post(client)
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "queued"
    assert body["storage_uri"].startswith("s3://")
    assert "whisper_unavailable" in body["reason"]
    # Original audio still persisted, plus a retry job enqueued.
    assert retry_queue.depth() == 1


def test_transcribe_rejects_empty_payload(client):
    response = _post(client, content=b"")
    assert response.status_code == 400


def test_transcribe_rejects_oversize_payload(client, settings):
    too_big = b"x" * (settings.max_upload_bytes + 1)
    response = _post(client, content=too_big)
    assert response.status_code == 413


def test_transcribe_rejects_non_audio_content_type(client):
    response = _post(client, content_type="text/plain", filename="hello.txt")
    assert response.status_code == 400


def test_health_live_returns_ok(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_ready_returns_degraded_when_whisper_down(client, whisper_stub):
    whisper_stub.raise_unavailable = True
    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["whisper"] == "unreachable"
