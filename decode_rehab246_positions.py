from pathlib import Path
import numpy as np
import pandas as pd

FOLDER = Path(__file__).parent


# 1. Setup — load joint names directly from file
def load_joint_names(path: Path) -> list[str]:
    names = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        names.append(line.split(":", 1)[1].strip())
    return names


JOINT_NAMES = load_joint_names(FOLDER / "joints_names.txt")
JOINT_INDEX = {name: i for i, name in enumerate(JOINT_NAMES)}

# 2. MediaPipe mapping
MEDIAPIPE_JOINT_MAP = {
    "LeftShoulder": "LeftArm",
    "RightShoulder": "RightArm",
    "LeftElbow": "LeftForeArm",
    "RightElbow": "RightForeArm",
    "LeftWrist": "LeftHand",
    "RightWrist": "RightHand",
    "LeftKnee": "LeftLeg",
    "RightKnee": "RightLeg",
    "LeftAnkle": "LeftFoot",
    "RightAnkle": "RightFoot",
    "LeftFootIndex": "LeftToeBase",
    "RightFootIndex": "RightToeBase",
}
HIP_SOURCE = "Hips"

# 3. Config
FRAME_RATE_HZ = 30  # confirmed from filename "-30fps"
UNIT_SCALE = 1.0  # verify: sample values already looked like meters, not mm

EXERCISE_ID_TO_NAME = {
    1: "ArmAbduction",
    2: "ArmVW",
    3: "PushUp",
    4: "LegAbduction",
    5: "LegLunge",
    6: "Squat",
}

TARGET_EXERCISE_ID = 1  # Change per exercise


# 4. Position table building & hip recentering
def build_mediapipe_compatible(frames_xyz: np.ndarray) -> dict[str, np.ndarray]:
    out = {}
    for target, source in MEDIAPIPE_JOINT_MAP.items():
        out[target] = frames_xyz[:, JOINT_INDEX[source], :]
    hip_vals = frames_xyz[:, JOINT_INDEX[HIP_SOURCE], :]
    out["LeftHip"] = hip_vals
    out["RightHip"] = hip_vals
    return out


def recenter_on_hip(
    joint_dict: dict[str, np.ndarray], frames_xyz: np.ndarray
) -> dict[str, np.ndarray]:
    hip_center = frames_xyz[:, JOINT_INDEX[HIP_SOURCE], :]
    return {name: values - hip_center for name, values in joint_dict.items()}


# 5. Main loop
seg_path = FOLDER / "Segmentation.csv"
if not seg_path.exists():
    raise SystemExit(f"\nERROR: File not found: {seg_path.resolve()}\n")

seg = pd.read_csv(seg_path, sep=";")
seg = seg[seg["exercise_id"] == TARGET_EXERCISE_ID]

npy_cache: dict[str, np.ndarray] = {}
all_rows = []

for _, row in seg.iterrows():
    video_id = row["video_id"]
    if video_id not in npy_cache:
        npy_path = FOLDER / "3d_joints" / f"Ex{TARGET_EXERCISE_ID}" / f"{video_id}-30fps.npy"
        if not npy_path.exists():
            print(f"WARNING: missing {npy_path.name}, skipping")
            continue
        npy_cache[video_id] = np.load(npy_path)[:, :, :3]  # drop homogeneous column

    frames_xyz = npy_cache[video_id]
    start, end = int(row["first_frame"]), int(row["last_frame"])
    rep_frames = frames_xyz[start : end + 1]

    joints = build_mediapipe_compatible(rep_frames)
    joints = recenter_on_hip(joints, rep_frames)

    n_frames = rep_frames.shape[0]
    rep_df = pd.DataFrame({
        f"{name}_{axis}": joints[name][:, ax] * UNIT_SCALE
        for name in joints
        for ax, axis in enumerate(("X", "Y", "Z"))
    })
    rep_df["frame"] = range(n_frames)
    rep_df["timestamp_offset_ms"] = (
        rep_df["frame"] * (1000 / FRAME_RATE_HZ)
    ).astype(int)
    rep_df["movement"] = EXERCISE_ID_TO_NAME[TARGET_EXERCISE_ID]
    rep_df["subject_id"] = video_id
    rep_df["repetition"] = row["repetition_number"]
    rep_df["is_correct"] = bool(row["correctness"])
    rep_df["source_file"] = f"{video_id}-30fps.npy"
    all_rows.append(rep_df)

# 6. Combine, report, save
if not all_rows:
    raise SystemExit(
        f"No reps found for exercise_id={TARGET_EXERCISE_ID}. Check Segmentation.csv."
    )

combined = pd.concat(all_rows, ignore_index=True)
movement_name = EXERCISE_ID_TO_NAME[TARGET_EXERCISE_ID]

reps_summary = combined.groupby(["subject_id", "repetition"]).is_correct.first()
print(f"Exercise: {movement_name} (id={TARGET_EXERCISE_ID})")
print(f"Reps processed: {len(reps_summary)}")
print(f"Total frames: {len(combined)}")
print(f"Correct reps: {reps_summary.sum()}")
print(f"Incorrect reps: {(~reps_summary).sum()}")

out_name = f"rehab246_{movement_name.lower()}_positions_standardized.csv"
combined.to_csv(FOLDER / out_name, index=False)
print(f"\nSaved: {out_name}")