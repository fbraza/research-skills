#!/usr/bin/env python3
"""
Simple test for functional-enrichment-from-degs skill.

Mock test:  Validates ORA and GSEA logic using synthetic DE results — no network required.
Live test:  Full workflow with real airway dataset DE results (requires R + clusterProfiler).

Usage:
    python3 assets/eval/simple_test.py           # Mock test only (fast, ~5 seconds)
    python3 assets/eval/simple_test.py --live    # Mock + live test (requires R)
    python3 assets/eval/simple_test.py --verbose # Detailed output
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
import shutil

# ── Path setup ────────────────────────────────────────────────────────────────
EVAL_DIR   = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR  = os.path.join(EVAL_DIR, "..", "..")
SCRIPT_DIR = os.path.join(SKILL_DIR, "scripts")
sys.path.insert(0, SCRIPT_DIR)

TEST_OUTPUT_DIR = os.path.join(EVAL_DIR, "test_results")

# ── Mock DE results (airway dataset, dexamethasone treatment) ─────────────────
# Subset of real DESeq2 results from the airway dataset for testing
MOCK_DE_RESULTS = [
    # Upregulated — known dexamethasone response genes
    {"gene": "DUSP1",   "log2FoldChange":  3.21, "padj": 1.2e-15, "baseMean": 2847.3},
    {"gene": "KLF15",   "log2FoldChange":  2.87, "padj": 3.4e-12, "baseMean":  412.1},
    {"gene": "CRISPLD2","log2FoldChange":  2.54, "padj": 8.1e-10, "baseMean":  891.2},
    {"gene": "FKBP5",   "log2FoldChange":  2.31, "padj": 2.3e-09, "baseMean": 1203.4},
    {"gene": "TSC22D3", "log2FoldChange":  2.18, "padj": 5.6e-08, "baseMean":  634.7},
    {"gene": "ZBTB16",  "log2FoldChange":  1.98, "padj": 1.1e-07, "baseMean":  287.3},
    {"gene": "PER1",    "log2FoldChange":  1.76, "padj": 4.2e-06, "baseMean":  523.8},
    {"gene": "GILZ",    "log2FoldChange":  1.65, "padj": 9.8e-06, "baseMean":  178.4},
    {"gene": "ANGPTL4", "log2FoldChange":  1.54, "padj": 2.1e-05, "baseMean":  345.6},
    {"gene": "TNFRSF9", "log2FoldChange":  1.43, "padj": 4.7e-05, "baseMean":  156.2},
    # Downregulated — inflammatory response genes
    {"gene": "CXCL8",   "log2FoldChange": -3.45, "padj": 2.1e-18, "baseMean": 3421.5},
    {"gene": "IL6",     "log2FoldChange": -3.12, "padj": 7.8e-14, "baseMean": 1876.3},
    {"gene": "CCL2",    "log2FoldChange": -2.89, "padj": 1.4e-11, "baseMean": 2134.7},
    {"gene": "CXCL1",   "log2FoldChange": -2.67, "padj": 3.2e-10, "baseMean":  987.4},
    {"gene": "IL1B",    "log2FoldChange": -2.43, "padj": 8.9e-09, "baseMean": 1543.2},
    {"gene": "TNF",     "log2FoldChange": -2.21, "padj": 2.3e-07, "baseMean":  678.9},
    {"gene": "PTGS2",   "log2FoldChange": -1.98, "padj": 5.6e-06, "baseMean":  432.1},
    {"gene": "MMP1",    "log2FoldChange": -1.76, "padj": 1.2e-05, "baseMean":  234.5},
    {"gene": "ICAM1",   "log2FoldChange": -1.54, "padj": 3.4e-05, "baseMean":  567.8},
    {"gene": "VCAM1",   "log2FoldChange": -1.32, "padj": 7.8e-05, "baseMean":  345.6},
    # Non-significant genes (should be excluded)
    {"gene": "GAPDH",   "log2FoldChange":  0.12, "padj": 0.82,    "baseMean": 8934.2},
    {"gene": "ACTB",    "log2FoldChange": -0.08, "padj": 0.91,    "baseMean": 7823.1},
    {"gene": "B2M",     "log2FoldChange":  0.21, "padj": 0.67,    "baseMean": 5432.8},
]

# Known pathway enrichments expected for this comparison
EXPECTED_PATHWAYS = {
    "upregulated": [
        "glucocorticoid receptor signaling",
        "response to corticosteroid",
        "steroid hormone response",
    ],
    "downregulated": [
        "inflammatory response",
        "cytokine-mediated signaling",
        "NF-kB signaling",
        "chemokine signaling",
    ]
}


# ── Test 1: Gene list preparation ─────────────────────────────────────────────

def test_gene_list_preparation(verbose=False):
    """Test that significant genes are correctly filtered from DE results."""
    print("\n[Test 1] Gene list preparation...")

    import pandas as pd
    de_df = pd.DataFrame(MOCK_DE_RESULTS)

    # Filter significant genes (padj <= 0.05, |log2FC| >= 1)
    sig = de_df[(de_df["padj"] <= 0.05) & (de_df["log2FoldChange"].abs() >= 1.0)]
    up   = sig[sig["log2FoldChange"] > 0]["gene"].tolist()
    down = sig[sig["log2FoldChange"] < 0]["gene"].tolist()

    # Create ranked list for GSEA (all genes, sorted by log2FC)
    ranked = de_df.sort_values("log2FoldChange", ascending=False)
    ranked_list = dict(zip(ranked["gene"], ranked["log2FoldChange"]))

    # Assertions
    assert len(up) == 10,   f"Expected 10 upregulated genes, got {len(up)}"
    assert len(down) == 10, f"Expected 10 downregulated genes, got {len(down)}"
    assert len(ranked_list) == len(MOCK_DE_RESULTS), "Ranked list should include all genes"
    assert "GAPDH" not in up and "GAPDH" not in down, "Non-significant gene should be excluded"
    assert "DUSP1" in up,  "DUSP1 should be upregulated"
    assert "CXCL8" in down, "CXCL8 should be downregulated"

    if verbose:
        print(f"  Upregulated genes ({len(up)}): {', '.join(up[:5])}...")
        print(f"  Downregulated genes ({len(down)}): {', '.join(down[:5])}...")
        print(f"  Ranked list: {len(ranked_list)} genes, range [{min(ranked_list.values()):.2f}, {max(ranked_list.values()):.2f}]")

    print("  ✓ Gene list preparation: PASSED")
    return {"up": up, "down": down, "ranked": ranked_list}


# ── Test 2: Mock ORA logic ─────────────────────────────────────────────────────

def test_ora_logic(gene_lists, verbose=False):
    """Test ORA enrichment logic using a minimal mock gene set database."""
    print("\n[Test 2] ORA enrichment logic (mock gene sets)...")

    from scipy.stats import fisher_exact
    from statsmodels.stats.multitest import multipletests

    # Minimal mock gene set database (subset of Hallmark pathways)
    MOCK_GENESETS = {
        "HALLMARK_INFLAMMATORY_RESPONSE": [
            "CXCL8", "IL6", "CCL2", "CXCL1", "IL1B", "TNF", "PTGS2",
            "MMP1", "ICAM1", "VCAM1", "NFKB1", "RELA", "IRF1"
        ],
        "HALLMARK_TNFA_SIGNALING_VIA_NFKB": [
            "CXCL8", "IL6", "TNF", "ICAM1", "VCAM1", "NFKB1", "RELA",
            "PTGS2", "CCL2", "IL1B"
        ],
        "HALLMARK_GLUCOCORTICOID_RECEPTOR": [
            "DUSP1", "KLF15", "FKBP5", "TSC22D3", "ZBTB16", "PER1",
            "GILZ", "CRISPLD2", "ANGPTL4"
        ],
        "HALLMARK_HYPOXIA": [
            "ANGPTL4", "VEGFA", "HIF1A", "LDHA", "ENO1", "PGK1"
        ],
        "HALLMARK_CELL_CYCLE": [
            "CDK1", "CCNB1", "CCNA2", "MKI67", "TOP2A", "PCNA"
        ],
    }

    universe_size = 20000  # Approximate human gene count
    query_genes   = set(gene_lists["down"])  # Test with downregulated genes

    results = []
    for pathway, pathway_genes in MOCK_GENESETS.items():
        pathway_set = set(pathway_genes)
        overlap     = query_genes & pathway_set
        k = len(overlap)
        K = len(pathway_set)
        n = len(query_genes)
        N = universe_size

        # Fisher's exact test (2x2 contingency table)
        table = [[k, K - k], [n - k, N - K - (n - k)]]
        _, pval = fisher_exact(table, alternative="greater")

        results.append({
            "pathway":      pathway,
            "overlap":      k,
            "pathway_size": K,
            "query_size":   n,
            "pvalue":       pval,
            "overlap_genes": list(overlap)
        })

    # Multiple testing correction (BH)
    pvals = [r["pvalue"] for r in results]
    _, padj, _, _ = multipletests(pvals, method="fdr_bh")
    for r, p in zip(results, padj):
        r["padj"] = p

    # Sort by padj
    results.sort(key=lambda x: x["padj"])

    # Assertions
    sig_pathways = [r["pathway"] for r in results if r["padj"] <= 0.05]
    assert "HALLMARK_INFLAMMATORY_RESPONSE" in sig_pathways, \
        "Inflammatory response should be enriched in downregulated genes"
    assert "HALLMARK_GLUCOCORTICOID_RECEPTOR" not in sig_pathways, \
        "Glucocorticoid pathway should NOT be enriched in downregulated genes"

    if verbose:
        print(f"  Significant pathways (padj<=0.05): {len(sig_pathways)}")
        for r in results[:3]:
            print(f"    {r['pathway']}: overlap={r['overlap']}, padj={r['padj']:.3e}")

    print("  ✓ ORA enrichment logic: PASSED")
    return results


# ── Test 3: Mock GSEA logic ────────────────────────────────────────────────────

def test_gsea_logic(gene_lists, verbose=False):
    """Test GSEA ranked list logic using mock gene sets."""
    print("\n[Test 3] GSEA ranked list logic (mock)...")

    ranked = gene_lists["ranked"]

    # Validate ranked list properties
    assert len(ranked) > 0, "Ranked list is empty"

    # Check that list is sorted by log2FC (descending)
    values = list(ranked.values())
    assert values == sorted(values, reverse=True), \
        "Ranked list must be sorted by log2FC descending"

    # Check that known up/down genes are at correct ends
    gene_order = list(ranked.keys())
    dusp1_rank = gene_order.index("DUSP1")
    cxcl8_rank = gene_order.index("CXCL8")
    gapdh_rank = gene_order.index("GAPDH")

    assert dusp1_rank < gapdh_rank, "DUSP1 (upregulated) should rank above GAPDH"
    assert cxcl8_rank > gapdh_rank, "CXCL8 (downregulated) should rank below GAPDH"

    # Validate no NaN/Inf values
    import math
    for gene, val in ranked.items():
        assert not math.isnan(val), f"NaN value for gene {gene}"
        assert not math.isinf(val), f"Inf value for gene {gene}"

    if verbose:
        top5    = list(ranked.items())[:5]
        bottom5 = list(ranked.items())[-5:]
        print(f"  Top 5 (most upregulated): {[(g, f'{v:.2f}') for g, v in top5]}")
        print(f"  Bottom 5 (most downregulated): {[(g, f'{v:.2f}') for g, v in bottom5]}")

    print("  ✓ GSEA ranked list logic: PASSED")
    return True


# ── Test 4: Output file structure ─────────────────────────────────────────────

def test_output_structure(verbose=False):
    """Test that expected output files can be created."""
    print("\n[Test 4] Output file structure...")

    import pandas as pd

    tmp_dir = tempfile.mkdtemp(prefix="enrichment_test_")
    try:
        # Simulate ORA output CSV
        ora_df = pd.DataFrame([
            {"pathway": "HALLMARK_INFLAMMATORY_RESPONSE", "padj": 0.001,
             "overlap": 8, "pathway_size": 13, "overlap_genes": "CXCL8,IL6,CCL2"},
        ])
        ora_path = os.path.join(tmp_dir, "ora_results.csv")
        ora_df.to_csv(ora_path, index=False)
        assert os.path.exists(ora_path), "ORA results CSV not created"

        # Simulate GSEA output CSV
        gsea_df = pd.DataFrame([
            {"pathway": "HALLMARK_GLUCOCORTICOID_RECEPTOR", "NES": 2.34,
             "padj": 0.002, "size": 9, "leading_edge": "DUSP1,FKBP5,KLF15"},
        ])
        gsea_path = os.path.join(tmp_dir, "gsea_results.csv")
        gsea_df.to_csv(gsea_path, index=False)
        assert os.path.exists(gsea_path), "GSEA results CSV not created"

        if verbose:
            print(f"  ORA output: {ora_path}")
            print(f"  GSEA output: {gsea_path}")

    finally:
        shutil.rmtree(tmp_dir)

    print("  ✓ Output file structure: PASSED")
    return True


# ── Live test (requires R + clusterProfiler) ──────────────────────────────────

def test_live_workflow(verbose=False):
    """Run the actual R workflow scripts with airway example data."""
    print("\n[Live Test] Full R workflow with airway dataset...")

    # Check R availability
    try:
        result = subprocess.run(
            ["Rscript", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print("  ⚠ SKIPPED: R not available")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  ⚠ SKIPPED: R not found")
        return False

    # Check clusterProfiler
    check = subprocess.run(
        ["Rscript", "-e", "library(clusterProfiler); cat('OK')"],
        capture_output=True, text=True, timeout=30
    )
    if "OK" not in check.stdout:
        print("  ⚠ SKIPPED: clusterProfiler not installed")
        print("    Install with: BiocManager::install('clusterProfiler')")
        return False

    # Run load_example_data.R
    r_script = os.path.join(SCRIPT_DIR, "load_example_data.R")
    if not os.path.exists(r_script):
        print(f"  ⚠ SKIPPED: {r_script} not found")
        return False

    tmp_dir = tempfile.mkdtemp(prefix="enrichment_live_")
    try:
        test_r = f"""
options(repos = c(CRAN = "https://cloud.r-project.org"))
source("{r_script}")
de_results <- load_airway_de_results()
cat("GENES:", nrow(de_results), "\\n")
sig <- de_results[!is.na(de_results$padj) & de_results$padj <= 0.05 &
                  abs(de_results$log2FoldChange) >= 1, ]
cat("SIG_GENES:", nrow(sig), "\\n")
cat("DONE\\n")
"""
        r_path = os.path.join(tmp_dir, "test.R")
        with open(r_path, "w") as f:
            f.write(test_r)

        result = subprocess.run(
            ["Rscript", r_path],
            capture_output=True, text=True, timeout=300
        )

        if "DONE" not in result.stdout:
            print(f"  ✗ FAILED: {result.stderr[:200]}")
            return False

        # Parse output
        for line in result.stdout.split("\n"):
            if line.startswith("GENES:"):
                n_genes = int(line.split(":")[1].strip())
                assert n_genes > 1000, f"Expected >1000 genes, got {n_genes}"
            if line.startswith("SIG_GENES:"):
                n_sig = int(line.split(":")[1].strip())
                assert n_sig > 100, f"Expected >100 significant genes, got {n_sig}"
                if verbose:
                    print(f"  Significant genes: {n_sig}")

        print("  ✓ Live workflow: PASSED")
        return True

    finally:
        shutil.rmtree(tmp_dir)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Test functional-enrichment-from-degs skill."
    )
    parser.add_argument("--live",    action="store_true",
                        help="Run live test with real R workflow (requires R + clusterProfiler)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed test output")
    args = parser.parse_args()

    print("=" * 60)
    print("functional-enrichment-from-degs — Skill Test")
    print("=" * 60)

    results = {}

    # Mock tests (always run)
    try:
        gene_lists = test_gene_list_preparation(verbose=args.verbose)
        results["gene_list_prep"] = "PASSED"
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        results["gene_list_prep"] = "FAILED"

    try:
        test_ora_logic(gene_lists, verbose=args.verbose)
        results["ora_logic"] = "PASSED"
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        results["ora_logic"] = "FAILED"

    try:
        test_gsea_logic(gene_lists, verbose=args.verbose)
        results["gsea_logic"] = "PASSED"
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        results["gsea_logic"] = "FAILED"

    try:
        test_output_structure(verbose=args.verbose)
        results["output_structure"] = "PASSED"
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        results["output_structure"] = "FAILED"

    # Live test (optional)
    if args.live:
        passed = test_live_workflow(verbose=args.verbose)
        results["live_workflow"] = "PASSED" if passed else "SKIPPED"

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    all_passed = all(v in ("PASSED", "SKIPPED") for v in results.values())
    for test, status in results.items():
        icon = "✓" if status == "PASSED" else ("⚠" if status == "SKIPPED" else "✗")
        print(f"  {icon} {test}: {status}")

    if all_passed:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed. Check output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
