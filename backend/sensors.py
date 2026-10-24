import struct
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional, Tuple

import numpy as np

DEPTH_MAGIC = b"DPT1"
HEADER = struct.Struct("<4sHHdffffB3x")
MAX_DEPTH_BYTES = 1024 * 1024
PAIR_WINDOW_MS = 60
LINE_MEMORY_S = 1.0
FRESH_S = 1.0


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


PHONE_FIELDS = {
    "ar_tracking": lambda v: isinstance(v, str) and len(v) <= 40,
    "ar_pose": lambda v: isinstance(v, list) and len(v) == 16 and all(_num(x) for x in v),
    "heading_deg": _num,
    "has_lidar": lambda v: isinstance(v, bool),
    "ts_capture_ms": _num,
}


@dataclass
class Sensors:
    phone: Dict[str, object] = field(default_factory=dict)
    phone_at: Optional[float] = None
    lines: Deque[tuple] = field(default_factory=deque)
    depth: Optional[Dict[str, Optional[float]]] = None
    depth_at: Optional[float] = None
    depth_frames_received: int = 0
    depth_dropped: int = 0
    depth_unpaired: int = 0

    def pose_xz(self) -> Tuple[Optional[float], Optional[float]]:
        pose = self.phone.get("ar_pose")
        return (pose[12], pose[14]) if pose else (None, None)

    def snapshot(self) -> dict:
        """Newest pose + depth for a vision event; fields are null when older than 1 s."""
        now = time.time()
        fresh_phone = self.phone_at is not None and now - self.phone_at <= FRESH_S
        fresh_depth = self.depth_at is not None and now - self.depth_at <= FRESH_S
        x, z = self.pose_xz() if fresh_phone else (None, None)
        d = self.depth if fresh_depth else {}
        return {
            "pos_x": x, "pos_z": z,
            "heading_deg": self.phone.get("heading_deg") if fresh_phone else None,
            "ar_tracking": self.phone.get("ar_tracking") if fresh_phone else None,
            "depth_left": d.get("left"), "depth_centre": d.get("centre"), "depth_right": d.get("right"),
        }


SENSORS: Dict[str, Sensors] = {}


def sensors_for(attempt_id: str) -> Sensors:
    return SENSORS.setdefault(attempt_id, Sensors())


def on_phone_line(attempt_id: str, obj: dict):
    s = sensors_for(attempt_id)
    for name, valid in PHONE_FIELDS.items():
        if name in obj and valid(obj[name]):
            s.phone[name] = obj[name]
    now = time.time()
    s.phone_at = now
    if _num(obj.get("ts_capture_ms")):
        s.lines.append((float(obj["ts_capture_ms"]), now, s.phone.get("ar_pose"), s.phone.get("ar_tracking")))
    while s.lines and now - s.lines[0][1] > LINE_MEMORY_S:
        s.lines.popleft()


def _median_m(part: np.ndarray) -> Optional[float]:
    v = part[part > 0]
    return round(float(np.median(v)) / 1000, 3) if v.size else None


def parse_depth(data: bytes):
    """Returns (ts_capture_ms, (fx, fy, cx, cy), depth_mm array h×w) or None if the frame is invalid."""
    if len(data) > MAX_DEPTH_BYTES or len(data) < HEADER.size:
        return None
    _, w, h, ts, fx, fy, cx, cy, fmt = HEADER.unpack_from(data, 0)
    if fmt != 1 or w == 0 or h == 0 or len(data) != HEADER.size + 2 * w * h:
        return None
    return ts, (fx, fy, cx, cy), np.frombuffer(data, dtype="<u2", count=w * h, offset=HEADER.size).reshape(h, w)


def summarise_array(arr: np.ndarray) -> Dict[str, Optional[float]]:
    h, w = arr.shape
    rows = arr[h // 3: h - h // 3]
    c1, c2 = w // 3, w - w // 3
    return {"left": _median_m(rows[:, :c1]), "centre": _median_m(rows[:, c1:c2]), "right": _median_m(rows[:, c2:])}


def summarise(data: bytes) -> Optional[Tuple[float, Dict[str, Optional[float]]]]:
    parsed = parse_depth(data)
    return None if parsed is None else (parsed[0], summarise_array(parsed[2]))


def on_depth(attempt_id: str, data: bytes):
    """Updates counters and the depth summary; returns (array, intrinsics, pose, tracking) of the paired line, or None."""
    s = sensors_for(attempt_id)
    parsed = parse_depth(data)
    if parsed is None:
        s.depth_dropped += 1
        return None
    s.depth_frames_received += 1
    ts, intr, arr = parsed
    now = time.time()
    near = [ln for ln in s.lines if now - ln[1] <= LINE_MEMORY_S and abs(ln[0] - ts) <= PAIR_WINDOW_MS]
    if not near:
        s.depth_unpaired += 1
        return None
    line = min(near, key=lambda ln: abs(ln[0] - ts))
    s.depth, s.depth_at = {**summarise_array(arr), "ts_capture_ms": ts}, now
    return arr, intr, line[2], line[3]
