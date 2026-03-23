import os
import csv
import json
import tarfile
import math
import argparse
from collections import defaultdict

def load_rows(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_scene_tracks_from_archive(archive_path, scene_path):
    tracks = {}
    prefix = scene_path.rstrip("/") + "/"

    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            if not member.name.startswith(prefix):
                continue
            if not member.name.endswith("/track.json"):
                continue

            parts = member.name.split("/")
            if len(parts) < 4:
                continue

            track_type = parts[1]
            track_id = parts[2]

            f = tar.extractfile(member)
            if f is None:
                continue

            try:
                obj = json.load(f)
            except Exception:
                continue

            overview = obj.get("overview", {})
            data = obj.get("track_data", {})

            ts_map = {}
            for _, v in data.items():
                ts = str(v["ts"])
                coords = v["coordinates"]
                ts_map[ts] = {
                    "x": float(coords[0]),
                    "y": float(coords[1]),
                    "z": float(coords[2]),
                    "velocity": v.get("velocity"),
                    "class_prob": v.get("class_prob"),
                    "status": v.get("status"),
                    "source_type": v.get("source_type"),
                    "ground_type": v.get("ground_type"),
                }

            tracks[(track_type, track_id)] = {
                "overview": overview,
                "ts_map": ts_map,
                "member_path": member.name,
            }

    return tracks

def choose_timestamp(ts_sorted, mode):
    if not ts_sorted:
        return None
    if mode == "start":
        return ts_sorted[0]
    if mode == "end":
        return ts_sorted[-1]
    return ts_sorted[len(ts_sorted) // 2]

def main():
    parser = argparse.ArgumentParser(description="Extract future pedestrian trajectories for 3-5 seconds")
    parser.add_argument("--summary-csv", default=os.path.expanduser("~/imptc_project/results/interactions_summary.csv"))
    parser.add_argument("--archives-dir", default=os.path.expanduser("~/imptc_project/data"))
    parser.add_argument("--moment", choices=["start", "middle", "end"], default="middle")
    parser.add_argument("--horizon-sec", type=float, default=5.0)
    parser.add_argument("--limit", type=int, default=0, help="0 = όλα")
    parser.add_argument("--out-points", default=os.path.expanduser("~/imptc_project/results/pedestrian_future_points.csv"))
    parser.add_argument("--out-summary", default=os.path.expanduser("~/imptc_project/results/pedestrian_future_summary.csv"))
    args = parser.parse_args()

    rows = load_rows(args.summary_csv)

    ped_rows = [
        r for r in rows
        if r.get("status") == "ok"
        and r.get("target_type") == "vrus"
        and r.get("target_class_name") == "person"
    ]

    if args.limit > 0:
        ped_rows = ped_rows[:args.limit]

    print(f"Pedestrian samples to process: {len(ped_rows)}")

    grouped = defaultdict(list)
    for r in ped_rows:
        grouped[(r["archive"], r["scene_path"])].append(r)

    future_points = []
    future_summary = []

    horizon_us = int(args.horizon_sec * 1_000_000)

    for (archive_name, scene_path), target_rows in grouped.items():
        archive_path = os.path.join(args.archives_dir, archive_name)
        if not os.path.isfile(archive_path):
            continue

        print(f"[SCENE] {scene_path} ({archive_name})")
        scene_tracks = load_scene_tracks_from_archive(archive_path, scene_path)

        for row in target_rows:
            sample_id = row["sample_id"]
            target_key = (row["target_type"], row["target_id"])

            if target_key not in scene_tracks:
                future_summary.append({
                    "sample_id": sample_id,
                    "scene_path": scene_path,
                    "archive": archive_name,
                    "target_type": row["target_type"],
                    "target_id": row["target_id"],
                    "target_class_name": row["target_class_name"],
                    "moment_mode": args.moment,
                    "start_timestamp": "",
                    "end_timestamp": "",
                    "horizon_sec": args.horizon_sec,
                    "n_future_points": 0,
                    "start_x": "",
                    "start_y": "",
                    "end_x": "",
                    "end_y": "",
                    "displacement": "",
                    "avg_speed_est": "",
                    "status": "target_missing",
                })
                continue

            target = scene_tracks[target_key]
            ts_sorted = sorted(target["ts_map"].keys(), key=int)
            start_ts = choose_timestamp(ts_sorted, args.moment)
            if start_ts is None or start_ts not in target["ts_map"]:
                future_summary.append({
                    "sample_id": sample_id,
                    "scene_path": scene_path,
                    "archive": archive_name,
                    "target_type": row["target_type"],
                    "target_id": row["target_id"],
                    "target_class_name": row["target_class_name"],
                    "moment_mode": args.moment,
                    "start_timestamp": "",
                    "end_timestamp": "",
                    "horizon_sec": args.horizon_sec,
                    "n_future_points": 0,
                    "start_x": "",
                    "start_y": "",
                    "end_x": "",
                    "end_y": "",
                    "displacement": "",
                    "avg_speed_est": "",
                    "status": "timestamp_missing",
                })
                continue

            start_ts_int = int(start_ts)
            end_limit = start_ts_int + horizon_us

            selected_ts = [ts for ts in ts_sorted if start_ts_int <= int(ts) <= end_limit]

            if not selected_ts:
                future_summary.append({
                    "sample_id": sample_id,
                    "scene_path": scene_path,
                    "archive": archive_name,
                    "target_type": row["target_type"],
                    "target_id": row["target_id"],
                    "target_class_name": row["target_class_name"],
                    "moment_mode": args.moment,
                    "start_timestamp": start_ts,
                    "end_timestamp": "",
                    "horizon_sec": args.horizon_sec,
                    "n_future_points": 0,
                    "start_x": "",
                    "start_y": "",
                    "end_x": "",
                    "end_y": "",
                    "displacement": "",
                    "avg_speed_est": "",
                    "status": "no_future_points",
                })
                continue

            start_pt = target["ts_map"][selected_ts[0]]
            end_pt = target["ts_map"][selected_ts[-1]]

            dx = end_pt["x"] - start_pt["x"]
            dy = end_pt["y"] - start_pt["y"]
            displacement = math.sqrt(dx * dx + dy * dy)

            duration_sec = (int(selected_ts[-1]) - int(selected_ts[0])) / 1_000_000.0
            avg_speed = displacement / duration_sec if duration_sec > 0 else 0.0

            for ts in selected_ts:
                pt = target["ts_map"][ts]
                future_points.append({
                    "sample_id": sample_id,
                    "scene_path": scene_path,
                    "archive": archive_name,
                    "target_type": row["target_type"],
                    "target_id": row["target_id"],
                    "target_class_name": row["target_class_name"],
                    "moment_mode": args.moment,
                    "horizon_sec": args.horizon_sec,
                    "timestamp": ts,
                    "relative_time_sec": (int(ts) - start_ts_int) / 1_000_000.0,
                    "x": pt["x"],
                    "y": pt["y"],
                    "z": pt["z"],
                    "velocity": pt.get("velocity"),
                    "class_prob": pt.get("class_prob"),
                    "member_path": target["member_path"],
                })

            future_summary.append({
                "sample_id": sample_id,
                "scene_path": scene_path,
                "archive": archive_name,
                "target_type": row["target_type"],
                "target_id": row["target_id"],
                "target_class_name": row["target_class_name"],
                "moment_mode": args.moment,
                "start_timestamp": selected_ts[0],
                "end_timestamp": selected_ts[-1],
                "horizon_sec": args.horizon_sec,
                "n_future_points": len(selected_ts),
                "start_x": start_pt["x"],
                "start_y": start_pt["y"],
                "end_x": end_pt["x"],
                "end_y": end_pt["y"],
                "displacement": round(displacement, 6),
                "avg_speed_est": round(avg_speed, 6),
                "status": "ok",
            })

    if future_points:
        with open(args.out_points, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(future_points[0].keys()))
            writer.writeheader()
            writer.writerows(future_points)

    if future_summary:
        with open(args.out_summary, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(future_summary[0].keys()))
            writer.writeheader()
            writer.writerows(future_summary)

    print("DONE")
    print(f"Saved points : {args.out_points}")
    print(f"Saved summary: {args.out_summary}")
    print(f"Rows points  : {len(future_points)}")
    print(f"Rows summary : {len(future_summary)}")

if __name__ == "__main__":
    main()
