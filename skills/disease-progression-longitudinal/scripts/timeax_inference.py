"""
TimeAx inference: project new samples onto a trained trajectory model.

This script loads a previously trained TimeAx model (from run_trajectory_analysis.py
or run_timeax.R) and assigns pseudotime values to new/held-out samples without
re-training the model.

Use cases:
- Stage new patient samples on a trained disease trajectory
- Validate the model on a held-out test cohort
- Apply a reference trajectory to an independent dataset

Usage (command line):
    python scripts/timeax_inference.py \\
        --model-dir results/timeax_model/ \\
        --new-data new_samples.csv \\
        --output results/new_pseudotime.csv

Usage (Python API):
    from timeax_inference import project_new_samples, load_timeax_model
    model = load_timeax_model("results/timeax_model/")
    pseudotime_df = project_new_samples(model, new_data_df)
"""

import argparse
import os
import sys
import pickle
import subprocess
import tempfile
import warnings
from typing import Optional, Dict, Tuple

import numpy as np
import pandas as pd


# ── Model loading ──────────────────────────────────────────────────────────────

def load_timeax_model(model_dir: str) -> Dict:
    """
    Load a trained TimeAx model from disk.

    Supports models saved by:
    - run_trajectory_analysis.py  → timeax_model.pkl
    - run_timeax.R                → timeax_model.rds + timeax_seed_features.csv

    Parameters
    ----------
    model_dir : str
        Directory containing the saved model files.

    Returns
    -------
    model : dict
        Model dictionary with keys:
        - 'type': 'python' or 'r'
        - 'seed_features': list of seed feature names
        - 'consensus_trajectory': array (for python models)
        - 'model_path': path to .pkl or .rds file
        - 'robustness': robustness score
        - 'metadata': dict with training metadata

    Raises
    ------
    FileNotFoundError
        If no model files are found in model_dir.
    """
    if not os.path.isdir(model_dir):
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    # Try Python pickle model first
    pkl_path = os.path.join(model_dir, "timeax_model.pkl")
    if os.path.exists(pkl_path):
        print(f"Loading Python TimeAx model from {pkl_path}...")
        with open(pkl_path, "rb") as f:
            model_obj = pickle.load(f)

        # Wrap in standard dict if needed
        if isinstance(model_obj, dict):
            model = model_obj
        else:
            # Handle model objects with .seed_features / .robustness attributes
            model = {
                "type": "python",
                "model_obj": model_obj,
                "seed_features": getattr(model_obj, "seed_features", []),
                "robustness": getattr(model_obj, "robustness", None),
                "model_path": pkl_path,
                "metadata": {}
            }
        model["type"] = "python"
        model["model_path"] = pkl_path
        print(f"  ✓ Python model loaded")
        print(f"  Seed features: {len(model.get('seed_features', []))}")
        if model.get("robustness") is not None:
            print(f"  Robustness score: {model['robustness']:.3f}")
        return model

    # Try R model (RDS + seed features CSV)
    rds_path = os.path.join(model_dir, "timeax_model.rds")
    seed_path = os.path.join(model_dir, "timeax_seed_features.csv")
    if os.path.exists(rds_path):
        print(f"Loading R TimeAx model from {rds_path}...")
        seed_features = []
        if os.path.exists(seed_path):
            seed_df = pd.read_csv(seed_path)
            seed_features = seed_df["feature"].tolist()

        # Load model info if available
        info_path = os.path.join(model_dir, "timeax_model_info.csv")
        robustness = None
        if os.path.exists(info_path):
            info_df = pd.read_csv(info_path)
            rob_row = info_df[info_df["parameter"] == "robustness_score"]
            if len(rob_row) > 0:
                robustness = float(rob_row["value"].values[0])

        model = {
            "type": "r",
            "model_path": rds_path,
            "seed_features": seed_features,
            "robustness": robustness,
            "metadata": {"model_dir": model_dir}
        }
        print(f"  ✓ R model loaded")
        print(f"  Seed features: {len(seed_features)}")
        if robustness is not None:
            print(f"  Robustness score: {robustness:.3f}")
        return model

    raise FileNotFoundError(
        f"No TimeAx model found in {model_dir}. "
        "Expected 'timeax_model.pkl' (Python) or 'timeax_model.rds' (R)."
    )


# ── Projection ─────────────────────────────────────────────────────────────────

def project_new_samples(
    model: Dict,
    new_data: pd.DataFrame,
    output_dir: Optional[str] = None,
    scale_to_training: bool = True
) -> pd.DataFrame:
    """
    Project new samples onto a trained TimeAx trajectory.

    Parameters
    ----------
    model : dict
        Loaded model dict from load_timeax_model().
    new_data : pd.DataFrame
        Feature matrix for new samples.
        - If features are in rows: shape (features x samples)
        - If features are in columns: shape (samples x features)
        The function auto-detects orientation using seed_features.
    output_dir : str, optional
        If provided, save pseudotime CSV to this directory.
    scale_to_training : bool, default=True
        If True, z-score scale new data using per-feature statistics
        before projection (recommended when training data was z-scored).

    Returns
    -------
    pseudotime_df : pd.DataFrame
        DataFrame with columns: sample_id, pseudotime, uncertainty (if available).
        Pseudotime is in [0, 1] range (0 = earliest, 1 = latest disease stage).
    """
    seed_features = model.get("seed_features", [])
    if not seed_features:
        raise ValueError("Model has no seed features — cannot project new samples.")

    # ── Orient data: ensure samples x features ──────────────────────────────
    new_data = _orient_data(new_data, seed_features)

    # ── Validate feature overlap ─────────────────────────────────────────────
    available = [f for f in seed_features if f in new_data.columns]
    missing   = [f for f in seed_features if f not in new_data.columns]

    if len(available) == 0:
        raise ValueError(
            "None of the model's seed features are present in new_data. "
            "Check that feature names match the training data."
        )
    if len(missing) > 0:
        pct_missing = 100 * len(missing) / len(seed_features)
        warnings.warn(
            f"{len(missing)}/{len(seed_features)} seed features ({pct_missing:.1f}%) "
            f"missing from new data. Projecting with {len(available)} available features.",
            UserWarning
        )

    # Subset to available seed features
    data_subset = new_data[available].values.astype(float)

    # ── Scale if requested ───────────────────────────────────────────────────
    if scale_to_training:
        data_subset = _zscore_scale(data_subset)

    # ── Project based on model type ──────────────────────────────────────────
    model_type = model.get("type", "python")

    if model_type == "python":
        pseudotime, uncertainty = _project_python(model, data_subset, new_data.index)
    elif model_type == "r":
        pseudotime, uncertainty = _project_r(model, new_data[available], output_dir)
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    # ── Build output DataFrame ───────────────────────────────────────────────
    result_df = pd.DataFrame({
        "sample_id":   new_data.index,
        "pseudotime":  pseudotime,
        "uncertainty": uncertainty
    })

    # Normalise pseudotime to [0, 1]
    pt_range = result_df["pseudotime"].max() - result_df["pseudotime"].min()
    if pt_range > 0:
        result_df["pseudotime"] = (
            (result_df["pseudotime"] - result_df["pseudotime"].min()) / pt_range
        )

    # ── Save if requested ────────────────────────────────────────────────────
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "projected_pseudotime.csv")
        result_df.to_csv(out_path, index=False)
        print(f"  ✓ Pseudotime saved to {out_path}")

    print(f"\n✓ Projection complete: {len(result_df)} samples")
    print(f"  Pseudotime range: [{result_df['pseudotime'].min():.3f}, "
          f"{result_df['pseudotime'].max():.3f}]")
    print(f"  Mean uncertainty: {result_df['uncertainty'].mean():.3f}")

    return result_df


# ── Internal projection helpers ────────────────────────────────────────────────

def _orient_data(data: pd.DataFrame, seed_features: list) -> pd.DataFrame:
    """Auto-detect and fix data orientation (samples x features)."""
    # Check if seed features are in columns (correct orientation)
    n_col_matches = sum(f in data.columns for f in seed_features[:20])
    n_row_matches = sum(f in data.index  for f in seed_features[:20])

    if n_col_matches >= n_row_matches:
        return data  # Already samples x features
    else:
        print("  Auto-transposing data (detected features-in-rows orientation)...")
        return data.T


def _zscore_scale(data: np.ndarray) -> np.ndarray:
    """Z-score scale each feature (column) independently."""
    means = data.mean(axis=0)
    stds  = data.std(axis=0)
    stds[stds == 0] = 1.0  # Avoid division by zero for constant features
    return (data - means) / stds


def _project_python(model: Dict, data_subset: np.ndarray,
                    sample_names) -> Tuple[np.ndarray, np.ndarray]:
    """Project using Python model object."""
    model_obj = model.get("model_obj")

    if model_obj is not None and hasattr(model_obj, "predict"):
        # Use model's predict method if available
        pseudotime = model_obj.predict(data_subset.T)
    else:
        # Fallback: project onto consensus trajectory via correlation
        consensus = model.get("consensus_trajectory")
        if consensus is not None:
            pseudotime = np.array([
                np.corrcoef(data_subset[i], consensus[:len(data_subset[i])])[0, 1]
                for i in range(len(data_subset))
            ])
        else:
            # Last resort: PCA-based projection onto first PC
            from sklearn.decomposition import PCA
            pca = PCA(n_components=1)
            pseudotime = pca.fit_transform(data_subset).flatten()

    # Uncertainty: std of per-feature correlations with pseudotime
    uncertainty = np.array([
        np.std([
            abs(np.corrcoef(data_subset[i], data_subset[j])[0, 1])
            for j in range(min(10, len(data_subset)))
        ])
        for i in range(len(data_subset))
    ])

    return pseudotime, uncertainty


def _project_r(model: Dict, data_subset: pd.DataFrame,
               output_dir: Optional[str]) -> Tuple[np.ndarray, np.ndarray]:
    """Project using R TimeAx model via subprocess."""
    # Check R availability
    try:
        result = subprocess.run(
            ["Rscript", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            raise RuntimeError("R not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise RuntimeError(
            "R is required to project with an R TimeAx model. "
            "Install R or re-train the model using the Python workflow."
        )

    model_dir = model["metadata"].get("model_dir", os.path.dirname(model["model_path"]))

    with tempfile.TemporaryDirectory(prefix="timeax_infer_") as tmp_dir:
        # Write new data to temp CSV
        data_path = os.path.join(tmp_dir, "new_data.csv")
        data_subset.to_csv(data_path)

        out_path = os.path.join(tmp_dir, "projected_pseudotime.csv")

        # Inline R script for projection
        r_script = f"""
library(TimeAx)
model <- readRDS("{model["model_path"]}")
new_data <- read.csv("{data_path}", row.names=1, check.names=FALSE)
# TimeAx predict: data should be features x samples
if (nrow(new_data) < ncol(new_data)) new_data <- t(new_data)
pred <- predict(model, t(new_data))
result <- data.frame(
  sample_id   = colnames(new_data),
  pseudotime  = pred$pseudotime,
  uncertainty = if (!is.null(pred$uncertainty)) pred$uncertainty else rep(NA, ncol(new_data))
)
write.csv(result, "{out_path}", row.names=FALSE)
cat("DONE\\n")
"""
        r_script_path = os.path.join(tmp_dir, "project.R")
        with open(r_script_path, "w") as f:
            f.write(r_script)

        proc = subprocess.run(
            ["Rscript", r_script_path],
            capture_output=True, text=True, timeout=300
        )

        if proc.returncode != 0 or "DONE" not in proc.stdout:
            raise RuntimeError(
                f"R projection failed:\n{proc.stderr}"
            )

        result_df = pd.read_csv(out_path)
        pseudotime  = result_df["pseudotime"].values
        uncertainty = result_df["uncertainty"].fillna(0).values

    return pseudotime, uncertainty


# ── Validation helpers ─────────────────────────────────────────────────────────

def validate_projection(
    pseudotime_df: pd.DataFrame,
    metadata: pd.DataFrame,
    time_column: str = "timepoint",
    patient_column: str = "patient_id"
) -> Dict:
    """
    Validate projected pseudotime against known timepoints.

    Computes Spearman correlation between pseudotime and clinical timepoints,
    and monotonicity score per patient.

    Parameters
    ----------
    pseudotime_df : pd.DataFrame
        Output of project_new_samples() with sample_id and pseudotime columns.
    metadata : pd.DataFrame
        Metadata with sample_id, timepoint, and patient_id columns.
    time_column : str
        Column name for clinical timepoints.
    patient_column : str
        Column name for patient identifiers.

    Returns
    -------
    dict with keys: spearman_r, spearman_p, monotonicity_score, per_patient_mono
    """
    from scipy.stats import spearmanr

    merged = pseudotime_df.merge(
        metadata[["sample_id", time_column, patient_column]],
        on="sample_id", how="inner"
    )

    if len(merged) == 0:
        raise ValueError("No matching sample IDs between pseudotime and metadata.")

    # Global Spearman correlation
    rho, pval = spearmanr(merged["pseudotime"], merged[time_column])

    # Per-patient monotonicity
    mono_scores = []
    for patient, grp in merged.groupby(patient_column):
        if len(grp) < 2:
            continue
        grp_sorted = grp.sort_values(time_column)
        diffs = np.diff(grp_sorted["pseudotime"].values)
        mono_scores.append(np.mean(diffs > 0))  # Fraction of increasing steps

    mono_mean = np.mean(mono_scores) if mono_scores else np.nan

    print(f"\n=== Projection Validation ===")
    print(f"  Spearman r = {rho:.3f}  (p = {pval:.3e})")
    print(f"  Monotonicity score = {mono_mean:.3f}  (1.0 = perfectly monotone)")
    print(f"  N patients evaluated = {len(mono_scores)}")

    return {
        "spearman_r": rho,
        "spearman_p": pval,
        "monotonicity_score": mono_mean,
        "per_patient_monotonicity": mono_scores,
        "n_samples": len(merged)
    }


# ── CLI entry point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Project new samples onto a trained TimeAx trajectory model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic projection
  python scripts/timeax_inference.py \\
      --model-dir results/timeax_model/ \\
      --new-data new_samples.csv \\
      --output results/

  # With validation against known timepoints
  python scripts/timeax_inference.py \\
      --model-dir results/timeax_model/ \\
      --new-data new_samples.csv \\
      --metadata new_metadata.csv \\
      --time-column timepoint \\
      --patient-column patient_id \\
      --output results/
        """
    )
    parser.add_argument("--model-dir",  required=True,
                        help="Directory containing trained TimeAx model files")
    parser.add_argument("--new-data",   required=True,
                        help="Path to new sample data matrix (CSV/TSV)")
    parser.add_argument("--output",     required=True,
                        help="Output directory for projected pseudotime CSV")
    parser.add_argument("--metadata",   default=None,
                        help="Optional metadata CSV for validation")
    parser.add_argument("--time-column",    default="timepoint",
                        help="Timepoint column in metadata (default: timepoint)")
    parser.add_argument("--patient-column", default="patient_id",
                        help="Patient ID column in metadata (default: patient_id)")
    parser.add_argument("--no-scale",   action="store_true",
                        help="Skip z-score scaling of new data before projection")
    parser.add_argument("--transpose",  action="store_true",
                        help="Transpose new data before projection (features-in-rows)")

    args = parser.parse_args()

    # Load model
    model = load_timeax_model(args.model_dir)

    # Load new data
    sep = "\t" if args.new_data.endswith(".tsv") else ","
    new_data = pd.read_csv(args.new_data, sep=sep, index_col=0)
    if args.transpose:
        new_data = new_data.T
    print(f"New data shape: {new_data.shape[0]} samples x {new_data.shape[1]} features")

    # Project
    pseudotime_df = project_new_samples(
        model,
        new_data,
        output_dir=args.output,
        scale_to_training=not args.no_scale
    )

    # Validate if metadata provided
    if args.metadata is not None:
        sep_meta = "\t" if args.metadata.endswith(".tsv") else ","
        metadata = pd.read_csv(args.metadata, sep=sep_meta)
        if "sample_id" not in metadata.columns:
            metadata.insert(0, "sample_id", metadata.index)
        validate_projection(
            pseudotime_df, metadata,
            time_column=args.time_column,
            patient_column=args.patient_column
        )

    print(f"\n✓ Done. Results saved to {args.output}")


if __name__ == "__main__":
    main()
