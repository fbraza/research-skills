"""
prepare_data.py — DECODE Data Preparation

Loads single-cell reference data (h5ad), filters to target cell types,
splits into train/test donors, and generates pseudotissue samples.

Usage:
    python prepare_data.py \
        --input data/reference.h5ad \
        --cell_type_col CellType \
        --donor_col Donor \
        --train_donor 296C \
        --test_donor 302C \
        --cell_types "Type 2 alveolar,Luminal Macrophages,Fibroblasts,Dendritic cells" \
        --noise_type "Neutrophils" \
        --n_hvg 3346 \
        --n_train 6000 \
        --n_test 1000 \
        --m 30 \
        --output_dir data/processed/
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd
import scanpy as sc
import anndata as ad

# ── Add DECODE repo to path ──────────────────────────────────────────────────
DECODE_ROOT = os.environ.get('DECODE_ROOT', os.path.expanduser('~/DECODE'))
sys.path.insert(0, DECODE_ROOT)
from data.data_process import data_process


def parse_args():
    parser = argparse.ArgumentParser(description='Prepare data for DECODE deconvolution')
    parser.add_argument('--input', required=True, help='Path to input .h5ad file')
    parser.add_argument('--cell_type_col', default='CellType',
                        help='Column in adata.obs with cell type labels')
    parser.add_argument('--donor_col', default='Donor',
                        help='Column in adata.obs with donor/batch labels')
    parser.add_argument('--train_donor', required=True,
                        help='Donor ID to use for training')
    parser.add_argument('--test_donor', required=True,
                        help='Donor ID to use for testing')
    parser.add_argument('--cell_types', required=True,
                        help='Comma-separated list of target cell types')
    parser.add_argument('--noise_type', default=None,
                        help='Cell type to use as noise/impurity (optional)')
    parser.add_argument('--n_hvg', type=int, default=3000,
                        help='Number of highly variable genes to select')
    parser.add_argument('--n_train', type=int, default=6000,
                        help='Number of pseudotissue training samples')
    parser.add_argument('--n_test', type=int, default=1000,
                        help='Number of pseudotissue test samples')
    parser.add_argument('--m', type=int, default=30,
                        help='Cells per pseudotissue sample')
    parser.add_argument('--output_dir', default='data/processed/',
                        help='Directory to save processed data')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility')
    return parser.parse_args()


def load_and_filter(adata_path, cell_type_col, donor_col,
                    train_donor, test_donor, cell_types, noise_type):
    """Load h5ad and split into train/test AnnData objects."""
    print(f"Loading {adata_path}...")
    adata = sc.read_h5ad(adata_path)
    print(f"  Loaded: {adata.shape[0]} cells × {adata.shape[1]} genes")

    # Validate columns
    for col in [cell_type_col, donor_col]:
        if col not in adata.obs.columns:
            raise ValueError(f"Column '{col}' not found in adata.obs. "
                             f"Available: {list(adata.obs.columns)}")

    # Validate donors
    available_donors = adata.obs[donor_col].unique().tolist()
    for donor in [train_donor, test_donor]:
        if donor not in available_donors:
            raise ValueError(f"Donor '{donor}' not found. Available: {available_donors}")

    # Validate cell types
    available_types = adata.obs[cell_type_col].unique().tolist()
    all_types = cell_types + ([noise_type] if noise_type else [])
    for ct in all_types:
        if ct not in available_types:
            raise ValueError(f"Cell type '{ct}' not found. Available: {available_types}")

    # Split by donor
    train_adata = adata[adata.obs[donor_col] == train_donor].copy()
    test_adata  = adata[adata.obs[donor_col] == test_donor].copy()

    print(f"  Train ({train_donor}): {train_adata.shape[0]} cells")
    print(f"  Test  ({test_donor}):  {test_adata.shape[0]} cells")

    return train_adata, test_adata


def select_hvg(train_adata, test_adata, n_hvg, cell_type_col, cell_types, noise_type):
    """Select highly variable genes from training data (target cell types only)."""
    # Use only target cell types for HVG selection (exclude noise)
    target_types = cell_types
    train_target = train_adata[train_adata.obs[cell_type_col].isin(target_types)].copy()

    print(f"\nSelecting {n_hvg} HVGs from {train_target.shape[0]} target cells...")
    sc.pp.normalize_total(train_target, target_sum=1e4)
    sc.pp.log1p(train_target)
    sc.pp.highly_variable_genes(train_target, n_top_genes=n_hvg)

    hvg_list = train_target.var_names[train_target.var['highly_variable']].tolist()
    print(f"  Selected {len(hvg_list)} HVGs")

    # Subset both train and test to HVGs
    train_hvg = train_adata[:, hvg_list].copy()
    test_hvg  = test_adata[:, hvg_list].copy()

    return train_hvg, test_hvg, hvg_list


def generate_pseudotissues(adata, cell_type_col, cell_types, noise_type,
                           n_samples, m, seed):
    """
    Generate pseudotissue bulk samples by random cell aggregation.

    Returns:
        X_bulk: (n_samples, n_features) — pseudobulk expression
        y_prop: (n_samples, n_cell_types) — true cell type proportions
    """
    np.random.seed(seed)
    n_features = adata.shape[1]
    n_types = len(cell_types)

    # Get cell indices per type
    type_indices = {}
    for ct in cell_types:
        idx = np.where(adata.obs[cell_type_col] == ct)[0]
        if len(idx) == 0:
            raise ValueError(f"No cells found for type '{ct}'")
        type_indices[ct] = idx

    noise_indices = None
    if noise_type:
        noise_idx = np.where(adata.obs[cell_type_col] == noise_type)[0]
        if len(noise_idx) > 0:
            noise_indices = noise_idx
            print(f"  Noise type '{noise_type}': {len(noise_idx)} cells")

    # Get expression matrix
    if hasattr(adata.X, 'toarray'):
        X = adata.X.toarray()
    else:
        X = np.array(adata.X)

    X_bulk = np.zeros((n_samples, n_features))
    y_prop = np.zeros((n_samples, n_types))

    for s in range(n_samples):
        # Random Dirichlet proportions for target cell types
        props = np.random.dirichlet(np.ones(n_types))

        # Optionally add noise cells
        if noise_indices is not None:
            noise_frac = np.random.uniform(0, 0.1)  # up to 10% noise
            props = props * (1 - noise_frac)
            n_noise = max(1, int(m * noise_frac))
        else:
            n_noise = 0

        # Sample cells
        cells = []
        for i, ct in enumerate(cell_types):
            n_ct = max(1, int(m * props[i]))
            sampled = np.random.choice(type_indices[ct], size=n_ct, replace=True)
            cells.append(X[sampled])

        if n_noise > 0 and noise_indices is not None:
            sampled_noise = np.random.choice(noise_indices, size=n_noise, replace=True)
            cells.append(X[sampled_noise])

        # Aggregate (mean)
        all_cells = np.vstack(cells)
        X_bulk[s] = all_cells.mean(axis=0)
        y_prop[s] = props

    return X_bulk, y_prop


def save_processed(output_dir, train_X, train_y, test_X, test_y,
                   hvg_list, cell_types, train_donor, test_donor):
    """Save processed data as numpy arrays and metadata."""
    os.makedirs(output_dir, exist_ok=True)

    np.save(os.path.join(output_dir, 'train_X.npy'), train_X)
    np.save(os.path.join(output_dir, 'train_y.npy'), train_y)
    np.save(os.path.join(output_dir, 'test_X.npy'), test_X)
    np.save(os.path.join(output_dir, 'test_y.npy'), test_y)

    # Save metadata
    meta = {
        'n_features': len(hvg_list),
        'n_cell_types': len(cell_types),
        'cell_types': cell_types,
        'hvg_list': hvg_list,
        'train_donor': train_donor,
        'test_donor': test_donor,
        'train_samples': train_X.shape[0],
        'test_samples': test_X.shape[0],
    }
    import json
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as f:
        json.dump(meta, f, indent=2)

    print(f"\nSaved to {output_dir}:")
    print(f"  train_X.npy: {train_X.shape}")
    print(f"  train_y.npy: {train_y.shape}")
    print(f"  test_X.npy:  {test_X.shape}")
    print(f"  test_y.npy:  {test_y.shape}")
    print(f"  metadata.json")


def main():
    args = parse_args()
    np.random.seed(args.seed)

    cell_types = [ct.strip() for ct in args.cell_types.split(',')]
    noise_type = args.noise_type.strip() if args.noise_type else None

    print("=" * 60)
    print("DECODE Data Preparation")
    print("=" * 60)
    print(f"Cell types: {cell_types}")
    print(f"Noise type: {noise_type}")
    print(f"Train donor: {args.train_donor}")
    print(f"Test donor:  {args.test_donor}")
    print(f"HVGs: {args.n_hvg}")
    print(f"Train samples: {args.n_train}, Test samples: {args.n_test}")
    print(f"Cells per pseudotissue (m): {args.m}")

    # Load and split
    train_adata, test_adata = load_and_filter(
        args.input, args.cell_type_col, args.donor_col,
        args.train_donor, args.test_donor, cell_types, noise_type
    )

    # HVG selection
    train_adata, test_adata, hvg_list = select_hvg(
        train_adata, test_adata, args.n_hvg,
        args.cell_type_col, cell_types, noise_type
    )

    # Generate pseudotissues
    print(f"\nGenerating {args.n_train} training pseudotissues...")
    train_X, train_y = generate_pseudotissues(
        train_adata, args.cell_type_col, cell_types, noise_type,
        args.n_train, args.m, args.seed
    )

    print(f"Generating {args.n_test} test pseudotissues...")
    test_X, test_y = generate_pseudotissues(
        test_adata, args.cell_type_col, cell_types, noise_type,
        args.n_test, args.m, args.seed + 1
    )

    # Save
    save_processed(
        args.output_dir, train_X, train_y, test_X, test_y,
        hvg_list, cell_types, args.train_donor, args.test_donor
    )

    print("\nData preparation complete.")


if __name__ == '__main__':
    main()
