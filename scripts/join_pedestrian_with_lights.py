import os
import csv
import json

mom_path = os.path.expanduser("~/imptc_project/results/pedestrian_moments_summary.csv")
fut_path = os.path.expanduser("~/imptc_project/results/pedestrian_future_summary.csv")
lights_path = os.path.expanduser("~/imptc_project/results/pedestrian_traffic_lights.csv")
out_path = os.path.expanduser("~/imptc_project/results/pedestrian_full_context.csv")

mom = {}
with open(mom_path, "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        mom[row["sample_id"]] = row

fut = {}
with open(fut_path, "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        fut[row["sample_id"]] = row

lights = {}
with open(lights_path, "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        lights[row["sample_id"]] = row

rows = []
for sid, m in mom.items():
    if sid not in fut:
        continue
    l = lights.get(sid, {})
    row = {
        "sample_id": sid,
        "scene_path": m.get("scene_path", ""),
        "archive": m.get("archive", ""),
        "timestamp": m.get("timestamp", ""),
        "target_id": m.get("target_id", ""),
        "target_class_name": m.get("target_class_name", ""),
        "nearest_type": m.get("nearest_type", ""),
        "nearest_class": m.get("nearest_class", ""),
        "nearest_dist": m.get("nearest_dist", ""),
        "n_neighbors_found": m.get("n_neighbors_found", ""),
        "displacement": fut[sid].get("displacement", ""),
        "avg_speed_est": fut[sid].get("avg_speed_est", ""),
        "light_status": l.get("status", ""),
        "matched_signal_ts": l.get("matched_signal_ts", ""),
        "signal_count": l.get("signal_count", ""),
        "signal_states_json": l.get("signal_states_json", ""),
    }
    rows.append(row)

with open(out_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print("saved:", out_path)
print("rows:", len(rows))
