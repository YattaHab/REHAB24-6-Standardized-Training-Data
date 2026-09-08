# REHAB24-6 — Standardized Training Data

## What this is
Joint-position training data for exercise correctness scoring, derived from the public **REHAB24-6** dataset. Covers 6 exercises: Arm Abduction, Arm VW, Push-Up, Leg Abduction, Leg Lunge, Squat.

Two of these (Squat, Leg Lunge) overlap with movements already covered by UI-PRMD — that's intentional, not duplication. A second independently-recorded, independently-labeled sample of the same movement makes the model more robust, not redundant.

## Source
- Dataset: REHAB24-6 (Zenodo, record 13305826), CC0 license
- Original format: 3D joint positions (26 joints, BVH-style skeleton), 30fps and 120fps `.npy` files, `Segmentation.csv` for rep boundaries + correctness labels
- We use only the **30fps, 3D joints** files — 120fps and 2D versions are ignored (unnecessary detail / redundant with 3D)
- Raw video files are intentionally excluded — not used anywhere in this pipeline (see note below)

## Why no raw video was used
This dataset (like UI-PRMD and KIMORE) ships both raw video *and* pre-extracted joint positions from motion-capture-grade tracking. The joint positions are the higher-accuracy ground truth — running our own pose estimation on the video would introduce additional error rather than avoid it. Training data always comes from joint positions, never reconstructed from video, whenever a dataset provides both.

## Pipeline summary
1. Loaded joint names from `joints_names.txt` (26 joints, BVH hierarchy — position of each joint represents the *start* of its bone, so e.g. `LeftForeArm`'s position is the elbow, not the forearm midpoint)
2. Mapped 12 of those 26 joints to MediaPipe-equivalent landmarks (shoulders, elbows, wrists, knees, ankles, foot index) — see mapping table below
3. Sliced each subject's full-session `.npy` array into individual repetitions using `first_frame`/`last_frame` from `Segmentation.csv`
4. Recentered every joint's position on the `Hips` joint per frame (so absolute position in the room doesn't matter — only relative body configuration does)
5. Labeled each rep `is_correct` directly from the `correctness` column in `Segmentation.csv` (1 = correct, 0 = incorrect)
6. Saved one CSV per exercise to `data/`

## Joint mapping (source skeleton → MediaPipe-style target)
| Target | Source joint |
|---|---|
| LeftShoulder / RightShoulder | LeftArm / RightArm |
| LeftElbow / RightElbow | LeftForeArm / RightForeArm |
| LeftWrist / RightWrist | LeftHand / RightHand |
| LeftHip / RightHip | Hips *(single joint — see caveat below)* |
| LeftKnee / RightKnee | LeftLeg / RightLeg |
| LeftAnkle / RightAnkle | LeftFoot / RightFoot |
| LeftFootIndex / RightFootIndex | LeftToeBase / RightToeBase |

**This mapping was verified, not assumed.** We checked the height (Y-value) ordering of the full arm chain on a real frame — Shoulder > Elbow > Wrist > Fingertip, descending — which confirmed the BVH joint-to-bone-start convention holds for this skeleton before trusting it across the full dataset.

## Known caveats (read before training)
- **No separate left/right hip joint.** This skeleton only has one central `Hips` joint. Both `LeftHip` and `RightHip` columns in the output contain the *same* value. Unlike UI-PRMD (which had 4 pelvis markers to average), there's no way to recover per-side hip position from this dataset.
- **No built-in angle-validation reference.** UI-PRMD shipped an official Vicon-angle file we could cross-check our computed angles against. REHAB24-6 has no equivalent — there's no independent ground truth to validate the position→angle geometry against *within this dataset*. Cross-validation was instead done qualitatively by comparing Squat/Leg Lunge knee-angle ranges against UI-PRMD's equivalent movements.
- **Units assumed to be meters.** Raw values were in a range consistent with meters (not millimeters), so no unit conversion was applied. Flagged here in case future frames deviate from this pattern.
- **Correctness is binary per rep.** The original dataset also includes free-text mistake-type annotations per incorrect rep (not yet extracted into this pipeline) — a good candidate for enriching the `movementErrors` table later if the DS/AI team wants error-type granularity beyond correct/incorrect.

## File structure
```
REHAB24-6/
├── README.md                          ← this file
├── decode_rehab246_positions.py       ← generates the standardized CSVs from raw data
├── joints_names.txt                   ← joint index reference (from source dataset)
├── Segmentation.csv                   ← rep boundaries + correctness labels (from source dataset)
└── data/
    ├── rehab246_armabduction_positions_standardized.csv
    ├── rehab246_armvw_positions_standardized.csv
    ├── rehab246_pushup_positions_standardized.csv
    ├── rehab246_legabduction_positions_standardized.csv
    ├── rehab246_leglunge_positions_standardized.csv
    └── rehab246_squat_positions_standardized.csv
```
Raw `.npy` files and `3d_joints.zip` are **not included** in this repo (500MB+, and reproducible from the Zenodo link above via `decode_rehab246_positions.py`).

## Output CSV columns
Each row = one frame within one repetition.
- `{Joint}_X`, `{Joint}_Y`, `{Joint}_Z` — for each of the 12 mapped joints, hip-recentered position
- `frame` — frame index within the repetition (starts at 0)
- `timestamp_offset_ms` — time offset from rep start, in milliseconds (30fps → ~33.3ms/frame)
- `movement` — exercise name
- `subject_id` — source video ID
- `repetition` — repetition number within that subject's session
- `is_correct` — boolean, ground-truth correctness label
- `source_file` — original `.npy` filename, for traceability back to raw data

## Repetition counts by exercise
*(fill in from `validate_all.py` output)*

| Exercise | Total reps | Correct | Incorrect | Total frames |
|---|---|---|---|---|
| Arm Abduction | — | — | — | — |
| Arm VW | — | — | — | — |
| Push-Up | — | — | — | — |
| Leg Abduction | — | — | — | — |
| Leg Lunge | — | — | — | — |
| Squat | 195 | 134 | 61 | 19,373 |
| **Total** | — | — | — | — |

## How to regenerate this data from scratch
1. Download `3d_joints.zip`, `joints_names.txt`, `Segmentation.csv` from the Zenodo link above
2. Unzip `3d_joints.zip` — keeps its `Ex1`–`Ex6` subfolder structure, don't flatten it
3. Place everything alongside `decode_rehab246_positions.py` per the file structure above
4. Open the script, set `TARGET_EXERCISE_ID` to 1–6 in turn, run `python decode_rehab246_positions.py` after each change
5. Six CSVs will be generated in the same folder — move them into `data/`
