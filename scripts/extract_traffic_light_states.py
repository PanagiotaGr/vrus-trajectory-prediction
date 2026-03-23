import os
import csv
import json
import tarfile
import argparse
import traceback

def load_summary_rows(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "ok":
                rows.append(row)
    return rows

def load_signal_json_from_archive(archive_path, scene_path):
    member_name = f"{scene_path}/context/traffic_light_signals.json"
    with tarfile.open(archive_path, "r:gz") as tar:
        try:
            f = tar.extractfile(member_name)
            if f is None:
                return None
            return json.load(f)
        except KeyError:
            return None

def nearest_signal_state(status_data, target_ts):
    target_ts = int(target_ts)
    best_ts = None
    best_diff = None

    for ts_str in status_data.keys():
        ts = int(ts_str)
        diff = abs(ts - target_ts)
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_ts = ts_str

    if best_ts is None:
        return None, None

    return best_ts, status_data[best_ts]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", default=os.path.expanduser("~/imptc_project/results/pedestrian_moments_summary.csv"))
    parser.add_argument("--archives-dir", default=os.path.expanduser("~/imptc_project/data"))
    parser.add_argument("--output-csv", default=os.path.expanduser("~/imptc_project/results/pedestrian_traffic_lights.csv"))
    parser.add_argument("--errors-csv", default=os.path.expanduser("~/imptc_project/results/pedestrian_traffic_lights_errors.csv"))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    rows = load_summary_rows(args.input_csv)
    if args.limit > 0:
        rows = rows[:args.limit]

    out_rows = []
    err_rows = []

    for i, row in enumerate(rows, 1):
        try:
            archive = row["archive"]
            scene_path = row["scene_path"]
            sample_id = row["sample_id"]
            target_ts = row["timestamp"]

            archive_path = os.path.join(args.archives_dir, archive)
            if not os.path.isfile(archive_path):
                out_rows.append({
                    "sample_id": sample_id,
                    "scene_path": scene_path,
                    "archive": archive,
                    "timestamp": target_ts,
                    "matched_signal_ts": "",
                    "signal_count": 0,
                    "signal_keys": "",
                    "signal_states_json": "",
                    "status": "archive_not_found",
                })
                continue

            signal_obj = load_signal_json_from_archive(archive_path, scene_path)
            if signal_obj is None:
                out_rows.append({
                    "sample_id": sample_id,
                    "scene_path": scene_path,
                    "archive": archive,
                    "timestamp": target_ts,
                    "matched_signal_ts": "",
                    "signal_count": 0,
                    "signal_keys": "",
                    "signal_states_json": "",
                    "status": "signal_json_not_found",
                })
                continue

            status_data = signal_obj.get("status_data", {})
            matched_ts, signal_states = nearest_signal_state(status_data, target_ts)

            if signal_states is None:
                out_rows.append({
                    "sample_id": sample_id,
                    "scene_path": scene_path,
                    "archive": archive,
                    "timestamp": target_ts,
                    "matched_signal_ts": "",
                    "signal_count": 0,
                    "signal_keys": "",
                    "signal_states_json": "",
                    "status": "no_signal_state_found",
                })
                continue

            keys_sorted = sorted(signal_states.keys())

            out_rows.append({
                "sample_id": sample_id,
                "scene_path": scene_path,
                "archive": archive,
                "timestamp": target_ts,
                "matched_signal_ts": matched_ts,
                "signal_count": len(keys_sorted),
                "signal_keys": "|".join(keys_sorted),
                "signal_states_json": json.dumps(signal_states, ensure_ascii=False, sort_keys=True),
                "status": "ok",
            })

            if i % 100 == 0:
                print(f"Processed {i}/{len(rows)}")

        except Exception as e:
            err_rows.append({
                "sample_id": row.get("sample_id", ""),
                "scene_path": row.get("scene_path", ""),
                "archive": row.get("archive", ""),
                "timestamp": row.get("timestamp", ""),
                "error": str(e),
            })
            print(f"[ERROR] sample_id={row.get('sample_id','')} scene={row.get('scene_path','')} archive={row.get('archive','')}")
            print(traceback.format_exc())

    if out_rows:
        with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            writer.writeheader()
            writer.writerows(out_rows)

    if err_rows:
        with open(args.errors_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(err_rows[0].keys()))
            writer.writeheader()
            writer.writerows(err_rows)

    print("DONE")
    print("Saved:", args.output_csv)
    print("Rows :", len(out_rows))
    print("Errors:", len(err_rows))

if __name__ == "__main__":
    main()
