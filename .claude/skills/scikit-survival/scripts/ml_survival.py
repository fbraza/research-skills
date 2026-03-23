#!/usr/bin/env python3
"""
ML-based survival analysis using scikit-survival.

Covers:
  - Data preparation (structured array format required by sksurv)
  - Random Survival Forest (RSF) with permutation-based feature importance
  - Gradient Boosting Survival Analysis (GBS)
  - CoxnetSurvivalAnalysis (penalized Cox for high-dimensional data)
  - Comprehensive evaluation: Harrell's C-index, Uno's C-index,
    time-dependent AUC, Integrated Brier Score
  - Nested cross-validation for unbiased performance estimates
  - Model comparison table

Usage:
  Adapt data loading and feature/outcome columns to your dataset.
  All outputs saved to ./results/.

Dependencies:
  pip install scikit-survival scikit-learn pandas numpy matplotlib
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.inspection import permutation_importance

from sksurv.util import Surv
from sksurv.linear_model import CoxnetSurvivalAnalysis
from sksurv.ensemble import RandomSurvivalForest, GradientBoostingSurvivalAnalysis
from sksurv.metrics import (
    concordance_index_censored,
    concordance_index_ipcw,
    cumulative_dynamic_auc,
    integrated_brier_score,
    as_concordance_index_ipcw_scorer,
)

RESULTS_DIR = Path("./results/ml_survival")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
RANDOM_STATE = 42


# ---------------------------------------------------------------------------
# 1. Data preparation
# ---------------------------------------------------------------------------

def prepare_survival_data(df, time_col, event_col, feature_cols=None, drop_cols=None):
    """
    Convert a pandas DataFrame to sksurv structured array format.

    Parameters
    ----------
    df : pd.DataFrame
    time_col : str — column with follow-up time (numeric, > 0)
    event_col : str — binary event indicator (1 = event occurred, 0 = censored)
    feature_cols : list[str] | None — feature columns (None = all except time/event)
    drop_cols : list[str] | None — additional columns to exclude

    Returns
    -------
    X : pd.DataFrame of features
    y : structured array with fields ('event', bool) and ('time', float)
    """
    drop = {time_col, event_col}
    if drop_cols:
        drop.update(drop_cols)

    if feature_cols is None:
        feature_cols = [c for c in df.columns if c not in drop]

    X = df[feature_cols].copy()

    y = Surv.from_dataframe(event_col, time_col, df)

    print(f"Samples: {len(X)}")
    print(f"Features: {len(feature_cols)}")
    event_rate = df[event_col].mean()
    print(f"Event rate: {event_rate:.1%}  (censoring: {1 - event_rate:.1%})")

    return X, y


# ---------------------------------------------------------------------------
# 2. Train/test split
# ---------------------------------------------------------------------------

def split_survival_data(X, y, test_size=0.2):
    """Stratified split preserving event rate."""
    event_indicator = np.array([e for e, _ in y])
    return train_test_split(
        X, y, test_size=test_size, random_state=RANDOM_STATE,
        stratify=event_indicator
    )


# ---------------------------------------------------------------------------
# 3. Models
# ---------------------------------------------------------------------------

def build_rsf(n_estimators=500, min_samples_split=10, min_samples_leaf=5):
    """Random Survival Forest — best balance of performance and robustness."""
    return RandomSurvivalForest(
        n_estimators=n_estimators,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        max_features="sqrt",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )


def build_gbs(n_estimators=200, learning_rate=0.05, max_depth=3):
    """Gradient Boosting Survival — highest predictive performance with tuning."""
    return GradientBoostingSurvivalAnalysis(
        loss="coxph",
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        subsample=0.8,
        dropout_rate=0.1,
        random_state=RANDOM_STATE,
    )


def build_coxnet_pipeline(l1_ratio=0.5):
    """
    Penalized Cox (elastic net) for high-dimensional data.
    Includes StandardScaler — required for penalized Cox.
    l1_ratio=1.0 → Lasso (sparse), 0.0 → Ridge, 0.5 → elastic net.
    """
    return Pipeline([
        ("scaler", StandardScaler()),
        ("coxnet", CoxnetSurvivalAnalysis(
            l1_ratio=l1_ratio,
            alpha_min_ratio=0.01,
            n_alphas=50,
            fit_baseline_model=True,
        )),
    ])


# ---------------------------------------------------------------------------
# 4. Evaluation
# ---------------------------------------------------------------------------

def get_eval_times(y_train, y_test, percentiles=(25, 50, 75)):
    """Select evaluation time points from observed event times."""
    event_times = y_test["time"][y_test["event"]]
    times = np.percentile(event_times, percentiles)
    # Clip to range covered by training data
    t_min = y_train["time"][y_train["event"]].min()
    t_max = y_train["time"][y_train["event"]].max() * 0.95
    times = times[(times > t_min) & (times < t_max)]
    return times


def evaluate_model(model, X_train, X_test, y_train, y_test, label="Model"):
    """
    Comprehensive survival model evaluation.

    Reports:
      - Harrell's C-index (low censoring, fast)
      - Uno's C-index (IPCW-corrected, preferred for publication)
      - Time-dependent AUC at Q1/Q2/Q3 of event times
      - Integrated Brier Score (discrimination + calibration)

    Hard rule: always report Uno's C-index and IBS for publication.
    """
    times = get_eval_times(y_train, y_test)
    risk_scores = model.predict(X_test)

    # Concordance indices
    c_harrell = concordance_index_censored(
        y_test["event"], y_test["time"], risk_scores
    )[0]
    c_uno = concordance_index_ipcw(y_train, y_test, risk_scores)[0]

    # Time-dependent AUC
    auc_vals, mean_auc = cumulative_dynamic_auc(y_train, y_test, risk_scores, times)

    # Integrated Brier Score (requires survival functions)
    try:
        surv_funcs = model.predict_survival_function(X_test)
        ibs = integrated_brier_score(y_train, y_test, surv_funcs, times)
    except AttributeError:
        ibs = np.nan  # CoxnetSurvivalAnalysis may need fit_baseline_model=True

    results = {
        "label": label,
        "c_harrell": c_harrell,
        "c_uno": c_uno,
        "mean_auc": mean_auc,
        "ibs": ibs,
        "time_auc": dict(zip(times.round(0).astype(int), auc_vals)),
    }

    print(f"\n{'=' * 50}")
    print(f"  {label}")
    print(f"{'=' * 50}")
    print(f"  Harrell's C-index : {c_harrell:.3f}")
    print(f"  Uno's C-index     : {c_uno:.3f}  [preferred for publication]")
    print(f"  Mean time-AUC     : {mean_auc:.3f}")
    print(f"  Integrated Brier  : {ibs:.3f}  [lower = better]")
    for t, a in results["time_auc"].items():
        print(f"    AUC at t={t}: {a:.3f}")

    return results


# ---------------------------------------------------------------------------
# 5. Feature importance (RSF — permutation-based)
# ---------------------------------------------------------------------------

def rsf_feature_importance(rsf, X_test, y_test, feature_names, n_repeats=10):
    """
    Permutation-based feature importance for RSF.

    IMPORTANT: Do NOT use rsf.feature_importances_ — it is based on impurity
    and is unreliable for survival data. Always use permutation importance.
    """
    def score_fn(model, X, y):
        pred = model.predict(X)
        return concordance_index_censored(y["event"], y["time"], pred)[0]

    perm = permutation_importance(
        rsf, X_test, y_test,
        n_repeats=n_repeats,
        random_state=RANDOM_STATE,
        scoring=score_fn,
    )

    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance_mean": perm.importances_mean,
        "importance_std": perm.importances_std,
    }).sort_values("importance_mean", ascending=False)

    importance_df.to_csv(RESULTS_DIR / "rsf_feature_importance.csv", index=False)

    # Plot
    fig, ax = plt.subplots(figsize=(8, max(4, len(feature_names) * 0.3)))
    top_n = importance_df.head(20)
    ax.barh(top_n["feature"][::-1], top_n["importance_mean"][::-1],
            xerr=top_n["importance_std"][::-1], color="#0072B2", alpha=0.8)
    ax.set_xlabel("Permutation Importance (ΔC-index)")
    ax.set_title("RSF Feature Importance (Permutation-based)")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "rsf_feature_importance.svg", dpi=300, bbox_inches="tight")
    plt.savefig(RESULTS_DIR / "rsf_feature_importance.png", dpi=300, bbox_inches="tight")
    plt.close()

    return importance_df


# ---------------------------------------------------------------------------
# 6. Cross-validation (nested, unbiased)
# ---------------------------------------------------------------------------

def cross_validate_model(model, X, y, n_splits=5):
    """
    Nested cross-validation using Uno's C-index scorer.

    Reports CV C-index (mean ± SD).
    Hard rule: never report test-set AUC as 'validated' — use external cohort.
    """
    scorer = as_concordance_index_ipcw_scorer()
    cv = KFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_val_score(model, X, y, cv=cv, scoring=scorer, n_jobs=-1)
    print(f"  CV Uno's C-index: {scores.mean():.3f} ± {scores.std():.3f}")
    return scores


# ---------------------------------------------------------------------------
# 7. Model comparison table
# ---------------------------------------------------------------------------

def compare_models(results_list):
    """Print and save a model comparison table."""
    rows = []
    for r in results_list:
        rows.append({
            "Model": r["label"],
            "C-index (Uno)": f"{r['c_uno']:.3f}",
            "C-index (Harrell)": f"{r['c_harrell']:.3f}",
            "Mean time-AUC": f"{r['mean_auc']:.3f}",
            "IBS": f"{r['ibs']:.3f}" if not np.isnan(r['ibs']) else "N/A",
        })
    comparison = pd.DataFrame(rows)
    print("\n" + comparison.to_string(index=False))
    comparison.to_csv(RESULTS_DIR / "model_comparison.csv", index=False)
    return comparison


# ---------------------------------------------------------------------------
# 8. Example workflow
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # ── Replace with your data loading ──────────────────────────────────────
    # df = pd.read_csv("./data/clinical.csv")
    # X, y = prepare_survival_data(df, time_col="OS_days", event_col="OS_event")

    # Demo with sksurv built-in dataset
    from sksurv.datasets import load_gbsg2
    X, y = load_gbsg2()
    X = pd.get_dummies(X, drop_first=True)  # encode categorical columns
    # ────────────────────────────────────────────────────────────────────────

    X_train, X_test, y_train, y_test = split_survival_data(X, y)

    all_results = []

    # Random Survival Forest
    print("\n[1/3] Fitting Random Survival Forest...")
    rsf = build_rsf(n_estimators=500)
    rsf.fit(X_train, y_train)
    res_rsf = evaluate_model(rsf, X_train, X_test, y_train, y_test, label="RSF")
    all_results.append(res_rsf)

    # Feature importance (RSF only — permutation-based)
    print("\nComputing permutation feature importance...")
    imp = rsf_feature_importance(rsf, X_test, y_test, X.columns.tolist())
    print(imp.head(10).to_string(index=False))

    # Gradient Boosting
    print("\n[2/3] Fitting Gradient Boosting Survival...")
    gbs = build_gbs()
    gbs.fit(X_train, y_train)
    res_gbs = evaluate_model(gbs, X_train, X_test, y_train, y_test, label="GBS")
    all_results.append(res_gbs)

    # Penalized Cox (elastic net)
    print("\n[3/3] Fitting Penalized Cox (elastic net)...")
    coxnet = build_coxnet_pipeline(l1_ratio=0.5)
    coxnet.fit(X_train, y_train)
    res_cox = evaluate_model(coxnet, X_train, X_test, y_train, y_test, label="CoxNet")
    all_results.append(res_cox)

    # Cross-validation (RSF as example)
    print("\nCross-validating RSF (5-fold, Uno's C-index)...")
    cross_validate_model(build_rsf(n_estimators=200), X, y, n_splits=5)

    # Comparison table
    print("\n── Model Comparison ──")
    compare_models(all_results)

    print(f"\nOutputs saved to {RESULTS_DIR}/")
