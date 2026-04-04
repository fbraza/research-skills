"""
run_metabolomics.py — DECODE Metabolomics Deconvolution

DECODE pipeline for metabolomics (and proteomics without batch correction).
Uses Stage 3 (contrastive learning) only — no Stage 2 adversarial training.

Usage:
    python run_metabolomics.py \
        --data_dir data/processed/ \
        --output_dir results/metabolomics/ \
        --feat_map_w 256 \
        --feat_map_h 10 \
        --epoches 500 \
        --patience 50 \
        --if_pure False

Requires:
    - data_dir/train_X.npy, train_y.npy, test_X.npy, test_y.npy
    - data_dir/metadata.json
    - DECODE_ROOT environment variable pointing to DECODE repo

Notes:
    - Metabolomics typically has far fewer features (e.g., 107 metabolites)
      than transcriptomics (3000+ genes). More epochs are needed.
    - No Stage 2 is used because metabolomics data lacks the donor-level
      batch structure that Stage 2 corrects.
    - For proteomics WITH cross-dataset batch effects, use run_transcriptomics.py
      (which includes Stage 2).
"""

import argparse
import os
import sys
import json
import time
import numpy as np
import pandas as pd
import torch

# ── Add DECODE repo to path ──────────────────────────────────────────────────
DECODE_ROOT = os.environ.get('DECODE_ROOT', os.path.expanduser('~/DECODE'))
sys.path.insert(0, DECODE_ROOT)

from model.deconv_model import MBdeconv
from model.utils import TrainCustomDataset, TestCustomDataset, predict
from torch.utils.data import DataLoader


def parse_args():
    parser = argparse.ArgumentParser(description='DECODE metabolomics deconvolution')
    parser.add_argument('--data_dir', default='data/processed/',
                        help='Directory with train_X.npy, train_y.npy, test_X.npy, test_y.npy')
    parser.add_argument('--output_dir', default='results/metabolomics/',
                        help='Directory to save model and results')
    # Architecture
    parser.add_argument('--feat_map_w', type=int, default=256,
                        help='Feature map width (default: 256)')
    parser.add_argument('--feat_map_h', type=int, default=10,
                        help='Feature map height (default: 10)')
    # Training
    parser.add_argument('--epoches', type=int, default=500,
                        help='Max training epochs (default: 500 for metabolomics)')
    parser.add_argument('--patience', type=int, default=50,
                        help='Early stopping patience (default: 50 for metabolomics)')
    parser.add_argument('--Alpha', type=float, default=1.0,
                        help='NCE loss weight Alpha (default: 1.0)')
    parser.add_argument('--Beta', type=float, default=1.0,
                        help='NCE loss weight Beta (default: 1.0)')
    parser.add_argument('--batchsize', type=int, default=50,
                        help='Batch size (default: 50)')
    parser.add_argument('--lr', type=float, default=0.0001,
                        help='Learning rate (default: 0.0001)')
    # Inference
    parser.add_argument('--if_pure', type=lambda x: x.lower() == 'true',
                        default=False,
                        help='Use standard pathway (True) or denoiser (False, recommended)')
    # Device
    parser.add_argument('--device', default='auto',
                        help='Device: auto, cpu, cuda, cuda:0, etc.')
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


def load_data(data_dir):
    """Load preprocessed numpy arrays and metadata."""
    train_X = np.load(os.path.join(data_dir, 'train_X.npy'))
    train_y = np.load(os.path.join(data_dir, 'train_y.npy'))
    test_X  = np.load(os.path.join(data_dir, 'test_X.npy'))
    test_y  = np.load(os.path.join(data_dir, 'test_y.npy'))

    with open(os.path.join(data_dir, 'metadata.json')) as f:
        meta = json.load(f)

    print(f"Loaded data:")
    print(f"  Train: {train_X.shape[0]} samples × {train_X.shape[1]} features")
    print(f"  Test:  {test_X.shape[0]} samples × {test_X.shape[1]} features")
    print(f"  Cell types ({meta['n_cell_types']}): {meta['cell_types']}")

    # Warn if feature count is high (may need Stage 2)
    if train_X.shape[1] > 500:
        print(f"\n  WARNING: {train_X.shape[1]} features detected.")
        print("  For transcriptomics or cross-dataset proteomics, consider")
        print("  using run_transcriptomics.py (includes Stage 2 batch correction).")

    return train_X, train_y, test_X, test_y, meta


def compute_metrics(pred, gt):
    """Compute CCC, RMSE, and Pearson's r."""
    from scipy.stats import pearsonr

    pred_flat = pred.flatten()
    gt_flat   = gt.flatten()

    mean_pred = np.mean(pred_flat)
    mean_gt   = np.mean(gt_flat)
    var_pred  = np.var(pred_flat)
    var_gt    = np.var(gt_flat)
    cov       = np.mean((pred_flat - mean_pred) * (gt_flat - mean_gt))
    ccc = (2 * cov) / (var_pred + var_gt + (mean_pred - mean_gt) ** 2)

    rmse = np.sqrt(np.mean((pred_flat - gt_flat) ** 2))
    r, _ = pearsonr(pred_flat, gt_flat)

    return {'CCC': ccc, 'RMSE': rmse, 'Pearson_r': r}


def train_model(train_X, train_y, args, device):
    """Stage 3: Contrastive learning (no Stage 2 for metabolomics)."""
    print("\n" + "=" * 50)
    print("Stage 3: Contrastive Learning")
    print("=" * 50)

    n_feat = train_X.shape[1]
    n_types = train_y.shape[1]

    model = MBdeconv(
        num_feat=n_feat,
        feat_map_w=args.feat_map_w,
        feat_map_h=args.feat_map_h,
        num_cell_type=n_types,
        Alpha=args.Alpha,
        Beta=args.Beta
    ).to(device)

    train_dataset = TrainCustomDataset(
        torch.FloatTensor(train_X),
        torch.FloatTensor(train_y)
    )
    train_loader = DataLoader(train_dataset, batch_size=args.batchsize, shuffle=True)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_loss = float('inf')
    patience_counter = 0
    best_state = None

    for epoch in range(args.epoches):
        model.train()
        epoch_loss = 0.0
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            loss = model(batch_X, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        avg_loss = epoch_loss / len(train_loader)
        if (epoch + 1) % 50 == 0:
            print(f"  Epoch {epoch+1:4d}/{args.epoches} | Loss: {avg_loss:.4f}")

        if avg_loss < best_loss:
            best_loss = avg_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"  Early stopping at epoch {epoch+1}")
                break

    if best_state:
        model.load_state_dict(best_state)

    print(f"  Training complete. Best loss: {best_loss:.4f}")
    return model


def run_inference(model, test_X, args, device):
    """Stage 4: Inference."""
    print("\n" + "=" * 50)
    print("Stage 4: Inference")
    print("=" * 50)

    model.eval()
    test_tensor = torch.FloatTensor(test_X).to(device)

    with torch.no_grad():
        pred = predict(model, test_tensor, if_pure=args.if_pure)

    pred = pred.cpu().numpy() if hasattr(pred, 'cpu') else np.array(pred)
    print(f"  Predictions shape: {pred.shape}")
    print(f"  if_pure={args.if_pure} ({'standard' if args.if_pure else 'denoiser'} pathway)")
    return pred


def save_results(output_dir, pred, gt, metrics, cell_types, model, args):
    """Save predictions, metrics, and model checkpoint."""
    os.makedirs(output_dir, exist_ok=True)

    pred_df = pd.DataFrame(pred, columns=cell_types)
    pred_df.to_csv(os.path.join(output_dir, 'predictions.csv'), index=False)

    gt_df = pd.DataFrame(gt, columns=cell_types)
    gt_df.to_csv(os.path.join(output_dir, 'ground_truth.csv'), index=False)

    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv(os.path.join(output_dir, 'metrics.csv'), index=False)

    torch.save(model.state_dict(), os.path.join(output_dir, 'model.pt'))

    with open(os.path.join(output_dir, 'args.json'), 'w') as f:
        json.dump(vars(args), f, indent=2)

    print(f"\nResults saved to {output_dir}")
    print(f"  predictions.csv: {pred.shape}")
    print(f"  metrics.csv")
    print(f"  model.pt")


def main():
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)

    print("=" * 60)
    print("DECODE Metabolomics Deconvolution")
    print("=" * 60)
    print(f"Device: {device}")
    print(f"if_pure: {args.if_pure}")
    print(f"Epochs: {args.epoches}, Patience: {args.patience}")

    # Load data
    train_X, train_y, test_X, test_y, meta = load_data(args.data_dir)
    cell_types = meta['cell_types']

    t0 = time.time()

    # Stage 3: Contrastive learning (no Stage 2)
    model = train_model(train_X, train_y, args, device)

    # Stage 4: Inference
    pred = run_inference(model, test_X, args, device)

    # Evaluate
    metrics = compute_metrics(pred, test_y)
    print(f"\nResults:")
    print(f"  CCC:       {metrics['CCC']:.4f}")
    print(f"  RMSE:      {metrics['RMSE']:.4f}")
    print(f"  Pearson r: {metrics['Pearson_r']:.4f}")
    print(f"  Total time: {time.time() - t0:.1f}s")

    # Save
    save_results(args.output_dir, pred, test_y, metrics, cell_types, model, args)

    print("\nMetabolomics deconvolution complete.")


if __name__ == '__main__':
    main()
