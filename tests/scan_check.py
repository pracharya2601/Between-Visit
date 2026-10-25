"""Phase 18 scan upload checks through the PUBLIC preview URL. Cancels (deletes) every scan route it creates.
  python3 scan_check.py uploads      all test files: accept/reject, units, upright, size, timing, temp files
  python3 scan_check.py cleanup ID…  cancel the given scans
"""
import os
import sys
import time
from pathlib import Path

import requests

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
DIR = Path("/tmp/scan_tests")
TMP = Path("/tmp/bv_scans")
CHUNK = 8 * 1024 * 1024


def upload(path: Path, name=None, empty=True, chunk=CHUNK, claimed=None):
    size = claimed or path.stat().st_size
    r = requests.post(f"{API}/scans", json={"route_name": name or f"Check {path.name}", "empty_space": empty, "filename": path.name, "size": size})
    if r.status_code != 201:
        return None, r.status_code, r.json()["detail"], 0
    sid = r.json()["id"]
    t = time.time()
    with open(path, "rb") as f:
        off = 0
        while True:
            data = f.read(chunk)
            if not data:
                break
            c = requests.put(f"{API}/scans/{sid}/chunk", params={"offset": off}, data=data, headers={"Content-Type": "application/octet-stream"})
            if c.status_code != 200:
                return sid, c.status_code, c.json()["detail"], time.time() - t
            off += len(data)
    up = time.time() - t
    p = requests.post(f"{API}/scans/{sid}/process", timeout=300)
    return sid, p.status_code, p.json() if p.status_code == 200 else p.json()["detail"], (up, time.time() - t - up)


def temp_files():
    return sorted(p.name for p in TMP.iterdir()) if TMP.exists() else []


def main():
    made = []
    print("gate: no checkbox ->", upload(DIR / "corridor.glb", empty=False)[1:3])
    print("wrong type .txt ->", requests.post(f"{API}/scans", json={"route_name": "x", "empty_space": True, "filename": "notes.txt", "size": 10}).json()["detail"])
    print("claimed 101 MB ->", upload(DIR / "corridor.glb", claimed=101 * 1024 * 1024)[1:3])
    sid, code, out, _ = upload(DIR / "corridor.glb", claimed=(DIR / "corridor.glb").stat().st_size - 10)
    made.append(sid)
    print("more bytes than declared ->", code, out, "| temp files", [f for f in temp_files() if f.startswith(sid)])
    for f in ("huge.glb",):
        sid, code, out, _ = upload(DIR / f, claimed=99 * 1024 * 1024)
        made.append(sid)
        print(f"{f} ({(DIR / f).stat().st_size / 1e6:.0f} MB, claims 99 MB) ->", code, out, "| temp files", [x for x in temp_files() if x.startswith(sid or "-")])
    for f in ("empty.glb", "fake.glb", "corridor.glb", "room_cm.obj", "room_zup.ply", "large.glb"):
        sid, code, out, secs = upload(DIR / f)
        made.append(sid)
        left = [x for x in temp_files() if sid and x.startswith(sid)]
        if code == 200:
            print(f"{f} {(DIR / f).stat().st_size / 1e6:.1f} MB -> OK points {out['point_count']} colours {out['colour_source']} unit {out['unit']} up {out['up']} "
                  f"| {out['dimensions']['text']} | upload {secs[0]:.1f}s process {secs[1]:.1f}s | temp files {left}")
            if f == "room_cm.obj":
                v = requests.post(f"{API}/scans/{sid}/orient", json={"unit": "m"}).json()
                print("   unit -> m:", v["dimensions"]["text"], "| back to cm:", requests.post(f"{API}/scans/{sid}/orient", json={"unit": "cm"}).json()["dimensions"]["text"])
            if f == "room_zup.ply":
                v = requests.post(f"{API}/scans/{sid}/orient", json={"turn_upright": True}).json()
                print("   Turn upright ->", v["up"], v["dimensions"]["text"])
        else:
            print(f"{f} -> {code} {out} | temp files {left}")
    print("scan ids:", " ".join(s for s in made if s))
    for s in made:
        if s:
            requests.post(f"{API}/scans/{s}/cancel")
    print("after cancel, temp files:", temp_files())


if __name__ == "__main__":
    if sys.argv[1:2] == ["cleanup"]:
        for s in sys.argv[2:]:
            print(s, requests.post(f"{API}/scans/{s}/cancel").json())
    else:
        main()
