import time
import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_iso)

    def to_mongo(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_mongo(cls, doc: dict):
        doc = dict(doc)
        doc.pop("_id", None)
        return cls(**doc)


class Practice(BaseDocument):
    name: str


class Practitioner(BaseDocument):
    practice_id: str
    name: str
    role: str


class Client(BaseDocument):
    practice_id: str
    display_name: str
    notes: str = ""
    synthetic: Literal[True]


class Route(BaseDocument):
    practice_id: str
    name: str
    current_version: int = 0
    is_test: bool = False
    teach_pending: bool = False


class Checkpoint(BaseDocument):
    # photo_url points to a photo of an empty space only; no client-run frames are stored
    route_id: str
    order: int
    name: str = ""
    photo_url: Optional[str] = None
    landmark_text: str = ""
    ai_suggested: bool = False
    approved: bool = False
    needs_photo: bool = False
    photo_pending: bool = False
    ai_unavailable: bool = False
    position: Optional[List[float]] = None


class CheckpointSnapshot(BaseModel):
    id: str
    order: int
    name: str
    photo_url: str
    landmark_text: str
    position: Optional[List[float]] = None


class RouteVersion(BaseDocument):
    route_id: str
    version: int
    checkpoints: List[CheckpointSnapshot] = Field(default_factory=list)
    known_entities: list = Field(default_factory=list)
    author: str
    memory_id: Optional[str] = None
    note: str = ""


class TeachSession(BaseDocument):
    route_name: str
    route_id: str
    stream_id: str
    key_hash: str
    key: Optional[str] = None
    status: Literal["active", "finished", "cancelled", "expired"] = "active"
    saved: bool = False
    updated_at: str = Field(default_factory=now_iso)


class RouteMemory(BaseDocument):
    # 3D memory of a taught walk; arrays live in object storage, practitioner-only
    route_id: str
    teach_session_id: str
    points_path: str
    json_path: str
    point_count: int
    plane_count: int
    trail_m: float


class Photo(BaseDocument):
    # checkpoint photo of an empty space; bytes live in object storage, never in Mongo
    checkpoint_id: str
    route_id: Optional[str] = None
    storage_path: str
    content_type: str = "image/jpeg"
    width: int
    height: int
    size: int
    is_deleted: bool = False
    storage_deleted: Optional[bool] = None


class SilenceRules(BaseModel):
    stay_silent_on_route: bool = True
    no_repeat: bool = True
    note: Optional[str] = None


class Exercise(BaseDocument):
    route_id: str
    route_version: int
    client_id: str
    goal: str
    cue_style: Literal["minimal", "standard"]
    silence_rules: SilenceRules = Field(default_factory=SilenceRules)
    stop_rule: str = ""


class AttemptPublic(BaseDocument):
    exercise_id: str
    status: Literal["not_started", "running", "paused", "ended", "pending"]
    stream_id: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    active_seconds: float = 0
    running_since: Optional[str] = None
    route_version: Optional[int] = None
    record_demo: bool = False
    replay: bool = False
    recording_id: Optional[str] = None
    public: bool = False


class Recording(BaseDocument):
    route_id: str
    route_version: Optional[int] = None
    attempt_id: Optional[str] = None
    exercise_id: str
    kind: Literal["real", "synthetic"]
    label: str
    frames: list = Field(default_factory=list)
    skipped: dict = Field(default_factory=dict)
    ready: bool = False


class Attempt(AttemptPublic):
    key_hash: str

    def elapsed_seconds(self) -> float:
        total = self.active_seconds
        if self.status == "running" and self.running_since:
            total += (datetime.now(timezone.utc) - datetime.fromisoformat(self.running_since)).total_seconds()
        return round(total, 1)


class TestConfig(BaseDocument):
    # plain key of the seeded test attempt only, read solely by /device-test
    stream_id: str
    attempt_id: str
    key: str


class AttemptEvent(BaseDocument):
    attempt_id: str
    seq: int = Field(default_factory=time.time_ns)
    t: str = Field(default_factory=now_iso)
    type: Literal["start", "pause", "resume", "end", "help", "guide", "repeat", "vision", "vision_error", "vision_stopped", "cue"]
    text: str = ""
    priority: Optional[int] = None
    spoken: bool = False
    suppressed_reason: Optional[str] = None
    checkpoint: Optional[str] = None
    uncertain: bool = False
    result: Optional[dict] = None
    latency_ms: Optional[int] = None
    model: Optional[str] = None
    route_version: Optional[int] = None
    source: Optional[Literal["glasses", "phone"]] = None
    reason: Optional[str] = None
    pos_x: Optional[float] = None
    pos_z: Optional[float] = None
    heading_deg: Optional[float] = None
    ar_tracking: Optional[str] = None
    depth_left: Optional[float] = None
    depth_centre: Optional[float] = None
    depth_right: Optional[float] = None
    depth_prompt: Optional[str] = None
    entity: Optional[str] = None
    for_event_id: Optional[str] = None
    would_have_said: Optional[str] = None
    details: Optional[dict] = None


class Correction(BaseDocument):
    attempt_event_id: str
    action: Literal["confirm", "edit", "dismiss"]
    author: str
    new_route_version: Optional[int] = None
    attempt_id: Optional[str] = None
    before: Optional[dict] = None
    after: Optional[dict] = None


class ProgressNote(BaseDocument):
    attempt_id: str
    client_id: str
    text: str
    ai_draft: str
    model: str
    author: str
    approved_at: str
    route_name: str = ""
    route_version: Optional[int] = None
    attempt_date: Optional[str] = None
    client_name: str = ""


COLLECTIONS = {
    "practices": Practice,
    "practitioners": Practitioner,
    "clients": Client,
    "routes": Route,
    "route_versions": RouteVersion,
    "checkpoints": Checkpoint,
    "exercises": Exercise,
    "attempts": Attempt,
    "attempt_events": AttemptEvent,
    "corrections": Correction,
    "test_config": TestConfig,
    "photos": Photo,
    "teach_sessions": TeachSession,
    "route_memories": RouteMemory,
    "progress_notes": ProgressNote,
    "recordings": Recording,
}

FOREIGN_KEYS = {
    "practitioners": ["practice_id"],
    "clients": ["practice_id"],
    "routes": ["practice_id"],
    "route_versions": ["route_id"],
    "checkpoints": ["route_id"],
    "exercises": ["route_id", "client_id"],
    "attempts": ["exercise_id"],
    "test_config": ["attempt_id"],
    "photos": ["checkpoint_id"],
    "teach_sessions": ["route_id"],
    "route_memories": ["route_id"],
    "attempt_events": ["attempt_id"],
    "corrections": [],
    "progress_notes": ["client_id"],
}
