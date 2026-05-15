from __future__ import annotations

import pytest

from app.compression import CompressionError, compress_to_opus, ffmpeg_available


@pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg not installed in this environment")
async def test_compress_to_opus_shrinks_synthetic_wav():
    # 1 second of silence at 48 kHz 16-bit mono = ~96 KB raw PCM. ffmpeg accepts raw
    # PCM via the right -f flag, but we use a tiny WAV header to keep this hermetic.
    import struct

    sample_rate = 48000
    duration = 1
    num_samples = sample_rate * duration
    riff = b"RIFF" + struct.pack("<I", 36 + num_samples * 2) + b"WAVE"
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
    data_chunk = b"data" + struct.pack("<I", num_samples * 2) + b"\x00" * (num_samples * 2)
    wav = riff + fmt + data_chunk

    out, content_type = await compress_to_opus(wav, input_suffix=".wav")
    assert content_type == "audio/ogg"
    assert 0 < len(out) < len(wav)


async def test_compress_to_opus_raises_when_ffmpeg_missing(monkeypatch):
    monkeypatch.setattr("app.compression.shutil.which", lambda _: None)
    with pytest.raises(CompressionError):
        await compress_to_opus(b"\x00" * 100)
