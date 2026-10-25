"""Phase 19 distinct-landmark checker unit cases (no DB writes).
  python3 similarity_check.py          text + photo-hash cases (Q-82..84)
  python3 similarity_check.py suggest  Sonnet distinct texts for demo frames 1 / 8 / 12 (prints only)
"""
import asyncio
import io
import sys

sys.path.insert(0, "/app/backend")
from similarity import HASH_HAMMING, TEXT_JACCARD, alike_pairs, dhash, jaccard  # noqa: E402

OLD_DEMO = [
    "A yellow tactile paving strip runs down the corridor's centre to a closed push-bar door, with a metal handrail along the left wall.",
    "A yellow tactile paving strip runs down the corridor's center to a push-bar exit door, with a metal handrail on the left wall.",
    "A yellow tactile paving strip leads down the corridor's center to a push-bar exit door, with a metal handrail on the left wall.",
]
DISTINCT = [
    "Glass double doors with a steel handrail starting on the right.",
    "The corridor turns right at a square pillar; a RECEPTION sign hangs above the corner.",
    "Long wooden reception desk facing you, a bell on the counter.",
    "Lift doors on the left with a raised call button and a chime.",
    "Floor changes from carpet to tiles where a water fountain hums on the right wall.",
]
FRAMES = {"Entrance": 0, "Hallway turn": 7, "Reception desk": 11}


def items(texts, hashes=None):
    return [{"id": str(i), "order": i + 1, "text": t, "hash": (hashes or [None] * len(texts))[i]} for i, t in enumerate(texts)]


async def frames():
    from db import db
    from storage import get_object
    rec = await db.recordings.find_one({"route_id": "276dc5bb-53b0-4734-83d7-c7743052d09d", "kind": "synthetic"}, {"_id": 0})
    return {k: await get_object(rec["frames"][i]["path"]) for k, i in FRAMES.items()}


async def cases():
    print(f"thresholds: text Jaccard >= {TEXT_JACCARD}, photo Hamming <= {HASH_HAMMING}")
    old = alike_pairs(items(OLD_DEMO))
    print(f"Q-84 old demo texts: {len(old)} of 3 pairs flagged", [(a + 1, b + 1, round(jaccard(OLD_DEMO[a], OLD_DEMO[b]), 2)) for a, b, _ in old])
    d = alike_pairs(items(DISTINCT))
    worst = max(jaccard(a, b) for i, a in enumerate(DISTINCT) for b in DISTINCT[i + 1:])
    print(f"Q-83 5 distinct texts: {len(d)} false warnings (highest Jaccard {worst:.2f})")
    near = "Glass double doors with a steel handrail that starts on the right."
    print("near-identical edit flagged:", bool(alike_pairs(items([DISTINCT[0], near]))), round(jaccard(DISTINCT[0], near), 2))
    from PIL import Image
    fr = await frames()
    hs = {k: dhash(v) for k, v in fr.items()}
    ks = list(hs)
    print("demo frame photo distances:", {f"{a}/{b}": bin(hs[a] ^ hs[b]).count("1") for i, a in enumerate(ks) for b in ks[i + 1:]})
    img = Image.open(io.BytesIO(fr["Entrance"])).convert("RGB")
    out = io.BytesIO()
    img.resize((img.width // 2, img.height // 2)).save(out, "JPEG", quality=70)
    print("same photo re-encoded at half size: distance", bin(hs["Entrance"] ^ dhash(out.getvalue())).count("1"))
    print("photo-only pair (different texts, same photo) flagged:", bool(alike_pairs(items(DISTINCT[:2], [hs["Entrance"], dhash(out.getvalue())]))))


async def suggest():
    from vision import process_image, suggest_landmark
    fr = {k: process_image(v)[0] for k, v in (await frames()).items()}
    first = {k: (await suggest_landmark(v))[1] for k, v in fr.items()}
    print("first pass:", first)
    for k, v in fr.items():
        others = [(i + 1, first[o]) for i, o in enumerate(FRAMES) if o != k]
        print(k, "->", await suggest_landmark(v, others))


asyncio.run(suggest() if sys.argv[1:2] == ["suggest"] else cases())
