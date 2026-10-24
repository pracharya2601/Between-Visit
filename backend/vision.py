import asyncio
import base64
import io
import logging
import os
import uuid
from typing import Optional, Tuple

from emergentintegrations.llm.chat import ImageContent, LlmChat, StreamDone, TextDelta, UserMessage
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
TARGET_WIDTH = 1280
AI_TIMEOUT_S = 30
MAX_WORDS = 25
RETAKE = "Retake: a person is in the photo"

SYSTEM = (
    "You help orientation-and-mobility specialists describe route checkpoints for blind and low-vision travellers. "
    "You only describe fixed, stable features of places, never people."
)
PROMPT = (
    "Give one stable landmark description of this place that is useful for orientation by a blind or low-vision person "
    "(for example a door, pillar, railing, wall corner, change in floor surface, or a fixed sound or tactile cue). "
    f"Use at most {MAX_WORDS} words, as a single sentence, with no preamble. "
    f"If any person or part of a person is visible, reply exactly \"{RETAKE}\" and describe no one."
)


def process_image(data: bytes) -> Tuple[bytes, int, int]:
    """Resize to 1280px wide (no upscaling) and re-encode as JPEG without EXIF/GPS."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise ValueError("not an image") from exc
    img = ImageOps.exif_transpose(img).convert("RGB")
    if img.width > TARGET_WIDTH:
        img = img.resize((TARGET_WIDTH, max(1, round(img.height * TARGET_WIDTH / img.width))), Image.LANCZOS)
    clean = Image.new("RGB", img.size)
    clean.paste(img)
    out = io.BytesIO()
    clean.save(out, "JPEG", quality=85, optimize=True)
    return out.getvalue(), clean.width, clean.height


def trim_words(text: str, limit: int = MAX_WORDS) -> str:
    words = text.split()
    return " ".join(words[:limit]) if len(words) > limit else " ".join(words)


async def _ask_claude(jpeg: bytes) -> str:
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"landmark-{uuid.uuid4()}",
        system_message=SYSTEM,
    ).with_model("anthropic", "claude-sonnet-5-5")
    msg = UserMessage(text=PROMPT, file_contents=[ImageContent(image_base64=base64.b64encode(jpeg).decode())])
    parts = []
    async for ev in chat.stream_message(msg):
        if isinstance(ev, TextDelta):
            parts.append(ev.content)
        elif isinstance(ev, StreamDone):
            break
    return "".join(parts).strip()


async def suggest_landmark(jpeg: bytes) -> Tuple[str, Optional[str]]:
    """Returns ("suggested", text), ("retake", None) or ("unavailable", None)."""
    try:
        reply = await asyncio.wait_for(_ask_claude(jpeg), AI_TIMEOUT_S)
    except Exception as exc:
        logger.warning("Landmark suggestion unavailable: %s", type(exc).__name__)
        return "unavailable", None
    if RETAKE.lower().rstrip(".") in reply.lower():
        return "retake", None
    text = trim_words(reply.strip().strip('"'))
    return ("suggested", text) if text else ("unavailable", None)
