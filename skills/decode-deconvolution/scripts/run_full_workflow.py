"""
run_full_workflow.py — DECODE End-to-End Pipeline

Unified pipeline that handles data preparation, model training, inference,
and result visualization in a single script. Automatically selects the
appropriate model (with/without Stage 2) based on omics type.

Usage:
    python run_full_workflow.py \
        --input data/reference.h5ad \
        --omics transcriptomics \
        --cell_type_col CellType \
        --donor_col Donor \
        --train_donor 296C \
        --test_donor 302C \
        --cell_types "Type 2 alveolar,Luminal Macrophages,Fibroblasts,Dendritic cells" \
        --noise_type "Neutrophils" \
        --n_hvg 3346 \
        --output_dir results/lung_rna/

    # Metabolomics (no Stage 2, more epochs):
    python run_full_workflow.py \
        --input data/bone_marrow.h5ad \
        --omics metabolomics \
        --cell_type_col CellType \
        --donor_col Donor \
        --train_donor donor1 \
        --test_donor donor2 \
        --cell_types "GMP,B,T,Myeloid,Erythroid" \
        --noise_type "HSC" \
        --n_hvg 107 \
        --epoches 500 \
        --patience 50 \
        --output_dir results/bone_marrow_mb/
"""

import argparse
import os
import sys
import json
import time
import numpy as np
import pandas as pd
import scanpy as sc
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr
from torch.utils.data import DataLoader

# ── Add DECODE repo to path ──────────────────────────────────────────────────
DECODE_ROOT = os.environ.get('DECODE_ROOT', os.path.expanduser('~/DECODE'))
sys.path.insert(0, DECODE_ROOT)

from model.utils import TrainCustomDataset, TestCustomDataset, predict


def parse_args():
    parser = argparse.ArgumentParser(description='DECODE end-to-end deconvolution pipeline')

    # Input
    parser.add_argument('--input', required=True, help='Path to input .h5ad file')
    parser.add_argument('--omics', default='transcriptomics',
                        choices=['transcriptomics', 'proteomics', 'metabolomics', 'spatial'],
                        help='Omics type (determines whether Stage 2 is used)')
    parser.add_argument('--cell_type_col', default='CellType')
    parser.add_argument('--donor_col', default='Donor')
    parser.add_argument('--train_donor', required=True)
    parser.add_argument('--test_donor', required=True)
    parser.add_argument('--cell_types', required=True,
                        help='Comma-separated target cell types')
    parser.add_argument('--noise_type', default=None)
    parser.add_argument('--n_hvg', type=int, default=3000,
                        help='Number of HVGs (or features for metabolomics/proteomics)')

    # Pseudotissue generation
    parser.add_argument('--n_train', type=int, default=6000)
    parser.add_argument('--n_test', type=int, default=1000)
    parser.add_argument('--m', type=int, default=30,
                        help='Cells per pseudotissue')

    # Architecture
    parser.add_argument('--feat_map_w', type=int, default=256)
    parser.add_argument('--feat_map_h', type=int, default=10)

    # Stage 3 training
    parser.add_argument('--epoches', type=int, default=None,
                        help='Max epochs (default: 200 for transcriptomics, 500 for metabolomics)')
    parser.add_argument('--patience', type=int, default=None,
                        help='Early stopping patience (default: 10 for transcriptomics, 50 for metabolomics)')
    parser.add_argument('--Alpha', type=float, default=1.0)
    parser.add_argument('--Beta', type=float, default=1.0)
    parser.add_argument('--batchsize', type=int, default=50)
    parser.add_argument('--lr', type=float, default=0.0001)

    # Stage 2 (transcriptomics/proteomics only)
    parser.add_argument('--stage2_epoches', type=int, default=20)
    parser.add_argument('--stage2_patience', type=int, default=3)
    parser.add_argument('--stage2_lr', type=float, default=0.0001)

    # Inference
    parser.add_argument('--if_pure', type=lambda x: x.lower() == 'true', default=False)

    # Output
    parser.add_argument('--output_dir', default='results/decode_output/')
    parser.add_argument('--device', default='auto')
    parser.add_argument('--seed', type=int, default=42)
    return parser.parse_args()


def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_device(device_str):
    if device_str == 'auto':
        return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return torch.device(device_str)


def use_stage2(omics):
    """Determine whether to use Stage 2 based on omics type."""
    return omics in ('transcriptomics', 'proteomics')


def get_defaults(omics):
    """Return default epochs/patience based on omics type."""
    if omics == 'metabolomics':
        return 500, 50
    return 200, 10


# ── Data preparation ─────────────────────────────────────────────────────────

def prepare_data(args, cell_types, noise_type):
    """Load, split, select features, and generate pseudotissues."""
    print("\n[Step 1] Data Preparation")
    print("-" * 40)

    adata = sc.read_h5ad(args.input)
    print(f"  Loaded: {adata.shape}")

    # Split by donor
    train_adata = adata[adata.obs[args.donor_col] == args.train_donor].copy()
    test_adata  = adata[adata.obs[args.donor_col] == args.test_donor].copy()
    print(f"  Train ({args.train_donor}): {train_adata.shape[0]} cells")
    print(f"  Test  ({args.test_donor}):  {test_adata.shape[0]} cells")

    # Feature selection
    target_train = train_adata[train_adata.obs[args.cell_type_col].isin(cell_types)].copy()
    sc.pp.normalize_total(target_train, target_sum=1e4)
    sc.pp.log1p(target_train)
    sc.pp.highly_variable_genes(target_train, n_top_genes=args.n_hvg)
    hvg_list = target_train.var_names[target_train.var['highly_variable']].tolist()
    print(f"  Selected {len(hvg_list)} features")

    train_adata = train_adata[:, hvg_list].copy()
    test_adata  = test_adata[:, hvg_list].copy()

    # Generate pseudotissues
    def gen_pseudo(adata, n_samples, seed):
        np.random.seed(seed)
        if hasattr(adata.X, 'toarray'):
            X = adata.X.toarray()
        else:
            X = np.array(adata.X)

        type_idx = {ct: np.where(adata.obs[args.cell_type_col] == ct)[0]
                    for ct in cell_types}
        noise_idx = (np.where(adata.obs[args.cell_type_col] == noise_type)[0]
                     if noise_type else None)

        n_feat = X.shape[1]
        n_types = len(cell_types)
        X_bulk = np.zeros((n_samples, n_feat))
        y_prop = np.zeros((n_samples, n_types))

        for s in range(n_samples):
            props = np.random.dirichlet(np.ones(n_types))
            cells = []
            for i, ct in enumerate(cell_types):
                n_ct = max(1, int(args.m * props[i]))
                cells.append(X[np.random.choice(type_idx[ct], n_ct, replace=True)])
            if noise_idx is not None and len(noise_idx) > 0:
                n_noise = max(1, int(args.m * np.random.uniform(0, 0.1)))
                cells.append(X[np.random.choice(noise_idx, n_noise, replace=True)])
            X_bulk[s] = np.vstack(cells).mean(axis=0)
            y_prop[s] = props

        return X_bulk, y_prop

    print(f"  Generating {args.n_train} train pseudotissues...")
    train_X, train_y = gen_pseudo(train_adata, args.n_train, args.seed)
    print(f"  Generating {args.n_test} test pseudotissues...")
    test_X, test_y = gen_pseudo(test_adata, args.n_test, args.seed + 1)

    return train_X, train_y, test_X, test_y, hvg_list


# ── Training ─────────────────────────────────────────────────────────────────

def train_dann(train_X, train_y, test_X, args, device):
    """Stage 2: DANN adversarial batch correction."""
    from model.stage2 import DANN
    print("\n[Step 2] Stage 2: Adversarial Batch Correction")
    print("-" * 40)

    n_feat, n_types = train_X.shape[1], train_y.shape[1]
    dann = DANN(num_feat=n_feat, feat_map_w=args.feat_map_w,
                feat_map_h=args.feat_map_h, num_cell_type=n_types).to(device)

    train_ds = TrainCustomDataset(torch.FloatTensor(train_X), torch.FloatTensor(train_y))
    test_ds  = TestCustomDataset(torch.FloatTensor(test_X))
    train_dl = DataLoader(train_ds, batch_size=args.batchsize, shuffle=True)
    test_dl  = DataLoader(test_ds,  batch_size=args.batchsize, shuffle=False)

    opt = torch.optim.Adam(dann.parameters(), lr=args.stage2_lr)
    best_loss, patience_counter, best_state = float('inf'), 0, None

    for epoch in range(args.stage2_epoches):
        dann.train()
        epoch_loss = sum(
            (opt.zero_grad() or True) and
            (loss := dann(bX.to(device), by.to(device), train_dl, test_dl)) and
            (loss.backward() or True) and
            (opt.step() or True) and
            loss.item()
            for bX, by in train_dl
        )
        avg = epoch_loss / len(train_dl)
        print(f"  Epoch {epoch+1:3d}/{args.stage2_epoches} | Loss: {avg:.4f}")
        if avg < best_loss:
            best_loss, patience_counter = avg, 0
            best_state = {k: v.clone() for k, v in dann.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= args.stage2_patience:
                print(f"  Early stopping at epoch {epoch+1}")
                break

    if best_state:
        dann.load_state_dict(best_state)
    return dann


def train_deconv(train_X, train_y, args, device, init_model=None):
    """Stage 3: Contrastive learning."""
    print("\n[Step 3] Stage 3: Contrastive Learning")
    print("-" * 40)

    if use_stage2(args.omics):
        from model.deconv_model_with_stage_2 import MBdeconv
    else:
        from model.deconv_model import MBdeconv

    n_feat, n_types = train_X.shape[1], train_y.shape[1]
    model = MBdeconv(num_feat=n_feat, feat_map_w=args.feat_map_w,
                     feat_map_h=args.feat_map_h, num_cell_type=n_types,
                     Alpha=args.Alpha, Beta=args.Beta).to(device)

    if init_model is not None:
        model.load_state_dict(init_model.state_dict(), strict=False)
        print("  Initialized from Stage 2 weights")

    train_ds = TrainCustomDataset(torch.FloatTensor(train_X), torch.FloatTensor(train_y))
    train_dl = DataLoader(train_ds, batch_size=args.batchsize, shuffle=True)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_loss, patience_counter, best_state = float('inf'), 0, None
    log_interval = max(1, args.epoches // 10)

    for epoch in range(args.epoches):
        model.train()
        epoch_loss = 0.0
        for bX, by in train_dl:
            bX, by = bX.to(device), by.to(device)
            opt.zero_grad()
            loss = model(bX, by)
            loss.backward()
            opt.step()
            epoch_loss += loss.item()

        avg = epoch_loss / len(train_dl)
        if (epoch + 1) % log_interval == 0:
            print(f"  Epoch {epoch+1:4d}/{args.epoches} | Loss: {avg:.4f}")

        if avg < best_loss:
            best_loss, patience_counter = avg, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"  Early stopping at epoch {epoch+1}")
                break

    if best_state:
        model.load_state_dict(best_state)
    print(f"  Best loss: {best_loss:.4f}")
    return model


# ── Metrics & Visualization ──────────────────────────────────────────────────

def compute_metrics(pred, gt):
    pred_f, gt_f = pred.flatten(), gt.flatten()
    mean_p, mean_g = np.mean(pred_f), np.mean(gt_f)
    var_p, var_g = np.var(pred_f), np.var(gt_f)
    cov = np.mean((pred_f - mean_p) * (gt_f - mean_g))
    ccc = (2 * cov) / (var_p + var_g + (mean_p - mean_g) ** 2)
    rmse = np.sqrt(np.mean((pred_f - gt_f) ** 2))
    r, _ = pearsonr(pred_f, gt_f)
    return {'CCC': ccc, 'RMSE': rmse, 'Pearson_r': r}


def plot_results(pred, gt, cell_types, metrics, output_dir):
    """Generate scatter plots and stacked bar chart."""
    n_types = len(cell_types)
    fig, axes = plt.subplots(1, n_types, figsize=(4 * n_types, 4))
    if n_types == 1:
        axes = [axes]

    for i, (ax, ct) in enumerate(zip(axes, cell_types)):
        ax.scatter(gt[:, i], pred[:, i], alpha=0.4, s=15, color='steelblue')
        lim = [0, max(gt[:, i].max(), pred[:, i].max()) * 1.05]
        ax.plot(lim, lim, 'r--', lw=1)
        ax.set_xlabel('True Proportion')
        ax.set_ylabel('Predicted Proportion')
        ax.set_title(ct, fontsize=10)
        ax.set_xlim(lim); ax.set_ylim(lim)

    plt.suptitle(
        f"DECODE | CCC={metrics['CCC']:.3f}  RMSE={metrics['RMSE']:.3f}  r={metrics['Pearson_r']:.3f}",
        y=1.02, fontsize=11
    )
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'scatter_pred_vs_true.png'), dpi=150, bbox_inches='tight')
    plt.close()

    # Stacked bar (first 30 samples)
    n_show = min(30, len(pred))
    pred_df = pd.DataFrame(pred[:n_show], columns=cell_types)
    fig, ax = plt.subplots(figsize=(max(8, n_show * 0.4), 4))
    pred_df.plot(kind='bar', stacked=True, ax=ax, colormap='tab20', width=0.9)
    ax.set_xlabel('Sample')
    ax.set_ylabel('Proportion')
    ax.set_title('DECODE Predicted Cell Type Proportions')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    plt.xticks(rotation=45, ha='right', fontsize=7)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'stacked_bar.png'), dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  Plots saved to {output_dir}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)

    # Set defaults based on omics type
    default_epoches, default_patience = get_defaults(args.omics)
    if args.epoches is None:
        args.epoches = default_epoches
    if args.patience is None:
        args.patience = default_patience

    cell_types = [ct.strip() for ct in args.cell_types.split(',')]
    noise_type = args.noise_type.strip() if args.noise_type else None

    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 60)
    print(f"DECODE End-to-End Pipeline ({args.omics})")
    print("=" * 60)
    print(f"Device: {device}")
    print(f"Cell types: {cell_types}")
    print(f"Stage 2: {'Yes' if use_stage2(args.omics) else 'No'}")
    print(f"Epochs: {args.epoches}, Patience: {args.patience}")

    t0 = time.time()

    # Step 1: Data preparation
    train_X, train_y, test_X, test_y, hvg_list = prepare_data(args, cell_types, noise_type)

    # Step 2: Stage 2 (if applicable)
    dann = None
    if use_stage2(args.omics):
        dann = train_dann(train_X, train_y, test_X, args, device)

    # Step 3: Stage 3
    model = train_deconv(train_X, train_y, args, device, init_model=dann)

    # Step 4: Inference
    print("\n[Step 4] Inference")
    print("-" * 40)
    model.eval()
    with torch.no_grad():
        pred = predict(model, torch.FloatTensor(test_X).to(device), if_pure=args.if_pure)
    pred = pred.cpu().numpy() if hasattr(pred, 'cpu') else np.array(pred)

    # Evaluate
    metrics = compute_metrics(pred, test_y)
    print(f"\nResults:")
    print(f"  CCC:       {metrics['CCC']:.4f}")
    print(f"  RMSE:      {metrics['RMSE']:.4f}")
    print(f"  Pearson r: {metrics['Pearson_r']:.4f}")
    print(f"  Total time: {time.time() - t0:.1f}s")

    # Save
    pd.DataFrame(pred, columns=cell_types).to_csv(
        os.path.join(args.output_dir, 'predictions.csv'), index=False)
    pd.DataFrame(test_y, columns=cell_types).to_csv(
        os.path.join(args.output_dir, 'ground_truth.csv'), index=False)
    pd.DataFrame([metrics]).to_csv(
        os.path.join(args.output_dir, 'metrics.csv'), index=False)
    torch.save(model.state_dict(), os.path.join(args.output_dir, 'model.pt'))
    with open(os.path.join(args.output_dir, 'args.json'), 'w') as f:
        json.dump(vars(args), f, indent=2)

    # Visualize
    print("\n[Step 5] Visualization")
    print("-" * 40)
    plot_results(pred, test_y, cell_types, metrics, args.output_dir)

    print(f"\nAll outputs saved to: {args.output_dir}")
    print("DECODE pipeline complete.")


if __name__ == '__main__':
    main()
