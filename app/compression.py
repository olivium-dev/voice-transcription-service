from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path


class CompressionError(RuntimeError):
    pass


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


async def compress_to_opus(
    data: bytes,
    input_suffix: str = ".bin",
    bitrate: str = "24k",
    sample_rate: int = 16000,
) -> tuple[bytes, str]:
    """Recompress audio with ffmpeg using libopus.

    Opus at 24 kbps mono/16 kHz keeps speech intelligible for Whisper while shrinking
    typical 5–25 MB phone-captured audio by roughly an order of magnitude. The caller
    is responsible only for invoking this when the original payload exceeds the
    configured size threshold.

    Returns (compressed_bytes, new_content_type).
    """
    if not ffmpeg_available():
        raise CompressionError("ffmpeg binary not found on PATH")

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"in{input_suffix}"
        dst = Path(tmp) / "out.ogg"
        src.write_bytes(data)

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "libopus",
            "-b:a",
            bitrate,
            str(dst),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise CompressionError(
                f"ffmpeg exited with {proc.returncode}: {stderr.decode(errors='ignore').strip()}"
            )
        return dst.read_bytes(), "audio/ogg"
