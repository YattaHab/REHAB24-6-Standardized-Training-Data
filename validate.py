import pandas as pd
from pathlib import Path

FOLDER = Path(__file__).parent
files = sorted(FOLDER.glob("rehab246_*_positions_standardized.csv"))

total_reps = 0
for f in files:
    df = pd.read_csv(f)
    n_reps = df.groupby(["subject_id", "repetition"]).ngroups
    n_correct = df.groupby(["subject_id", "repetition"]).is_correct.first().sum()
    n_nan = df.isna().sum().sum()
    total_reps += n_reps
    print(f"{f.name}: {n_reps} reps ({n_correct} correct / {n_reps - n_correct} incorrect), "
          f"{len(df)} frames, {n_nan} NaN values")

print(f"\nTOTAL reps across all 6 files: {total_reps}  (dataset docs say ~1,072)")