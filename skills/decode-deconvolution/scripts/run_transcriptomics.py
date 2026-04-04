"""
run_transcriptomics.py — DECODE Transcriptomics Deconvolution

Full 4-stage DECODE pipeline for transcriptomics (RNA-seq, scRNA-seq pseudobulk).
Includes Stage 2 (adversarial batch correction) + Stage 3 (contrastive learning).

Usage:
    python run_transcriptomics.py \
        --data_dir data/processed/ \
        --output_dir results/transcriptomics/ \
        --feat_map_w 256 \
        --feat_map_h 10 \
        --epoches 200 \
        --patience 10 \
        --stage2_epoches 20 \
        --stage2_patience 3 \
        --if_pure False

Requires:
    - data_dir/train_X.npy, train_y.npy, test_X.npy, test_y.npy
    - data_dir/metadata.json
    - DECODE_ROOT environment variable pointing to DECODE repo
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

from model.deconv_model_with_stage_2 import MBdeconv
from model.stage2 import DANN
from model.utils import TrainCustomDataset, TestCustomDataset, predict, data2h5ad
from torch.utils.data import DataLoader


def parse_args():
    parser = argparse.ArgumentParser(description='DECODE transcriptomics deconvolution')
    parser.add_argument('--data_dir', default='data/processed/',
                        help='Directory with train_X.npy, train_y.npy, test_X.npy, test_y.npy')
    parser.add_argument('--output_dir', default='results/transcriptomics/',
                        help='Directory to save model and results')
    # Architecture
    parser.add_argument('--feat_map_w', type=int, default=256,
                        help='Feature map width (default: 256)')
    parser.add_argument('--feat_map_h', type=int, default=10,
                        help='Feature map height (default: 10)')
    # Stage 3 training
    parser.add_argument('--epoches', type=int, default=200,
                        help='Max training epochs for Stage 3 (default: 200)')
    parser.add_argument('--patience', type=int, default=10,
                        help='Early stopping patience for Stage 3 (default: 10)')
    parser.add_argument('--Alpha', type=float, default=1.0,
                        help='NCE loss weight Alpha (default: 1.0)')
    parser.add_argument('--Beta', type=float, default=1.0,
                        help='NCE loss weight Beta (default: 1.0)')
    parser.add_argument('--batchsize', type=int, default=50,
                        help='Batch size for Stage 3 (default: 50)')
    parser.add_argument('--lr', type=float, default=0.0001,
                        help='Learning rate for Stage 3 (default: 0.0001)')
    # Stage 2 training
    parser.add_argument('--stage2_epoches', type=int, default=20,
                        help='Max epochs for Stage 2 DANN (default: 20)')
    parser.add_argument('--stage2_patience', type=int, default=3,
                        help='Early stopping patience for Stage 2 (default: 3)')
    parser.add_argument('--stage2_batchsize', type=int, default=50,
                        help='Batch size for Stage 2 (default: 50)')
    parser.add_argument('--stage2_lr', type=float, default=0.0001,
                        help='Learning rate for Stage 2 (default: 0.0001)')
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

    return train_X, train_y, test_X, test_y, meta


def compute_metrics(pred, gt):
    """Compute CCC, RMSE, and Pearson's r."""
    from scipy.stats import pearsonr

    pred_flat = pred.flatten()
    gt_flat   = gt.flatten()

    # Lin's CCC
    mean_pred = np.mean(pred_flat)
    mean_gt   = np.mean(gt_flat)
    var_pred  = np.var(pred_flat)
    var_gt    = np.var(gt_flat)
    cov       = np.mean((pred_flat - mean_pred) * (gt_flat - mean_gt))
    ccc = (2 * cov) / (var_pred + var_gt + (mean_pred - mean_gt) ** 2)

    # RMSE
    rmse = np.sqrt(np.mean((pred_flat - gt_flat) ** 2))

    # Pearson's r
    r, _ = pearsonr(pred_flat, gt_flat)

    return {'CCC': ccc, 'RMSE': rmse, 'Pearson_r': r}


def train_stage2(train_X, train_y, test_X, args, device):
    """Stage 2: Adversarial batch correction (DANN)."""
    print("\n" + "=" * 50)
    print("Stage 2: Adversarial Batch Correction (DANN)")
    print("=" * 50)

    n_feat = train_X.shape[1]
    n_types = train_y.shape[1]

    dann = DANN(
        num_feat=n_feat,
        feat_map_w=args.feat_map_w,
        feat_map_h=args.feat_map_h,
        num_cell_type=n_types
    ).to(device)

    # Create datasets
    train_dataset = TrainCustomDataset(
        torch.FloatTensor(train_X),
        torch.FloatTensor(train_y)
    )
    test_dataset = TestCustomDataset(torch.FloatTensor(test_X))

    train_loader = DataLoader(train_dataset, batch_size=args.stage2_batchsize, shuffle=True)
    test_loader  = DataLoader(test_dataset,  batch_size=args.stage2_batchsize, shuffle=False)

    optimizer = torch.optim.Adam(dann.parameters(), lr=args.stage2_lr)

    best_loss = float('inf')
    patience_counter = 0
    best_state = None

    for epoch in range(args.stage2_epoches):
        dann.train()
        epoch_loss = 0.0
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            loss = dann(batch_X, batch_y, train_loader, test_loader)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        avg_loss = epoch_loss / len(train_loader)
        print(f"  Epoch {epoch+1:3d}/{args.stage2_epoches} | Loss: {avg_loss:.4f}")

        if avg_loss < best_loss:
            best_loss = avg_loss
            best_state = {k: v.clone() for k, v in dann.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= args.stage2_patience:
                print(f"  Early stopping at epoch {epoch+1}")
                break

    if best_state:
        dann.load_state_dict(best_state)

    print(f"  Stage 2 complete. Best loss: {best_loss:.4f}")
    return dann


def train_stage3(train_X, train_y, test_X, dann, args, device):
    """Stage 3: Contrastive learning with noise robustness."""
    print("\n" + "=" * 50)
    print("Stage 3: Contrastive Learning (Noise Robustness)")
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

    # Initialize with Stage 2 encoder weights
    if dann is not None:
        model.load_state_dict(dann.state_dict(), strict=False)
        print("  Initialized from Stage 2 encoder weights")

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
        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1:3d}/{args.epoches} | Loss: {avg_loss:.4f}")

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

    print(f"  Stage 3 complete. Best loss: {best_loss:.4f}")
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

    # Predictions
    pred_df = pd.DataFrame(pred, columns=cell_types)
    pred_df.to_csv(os.path.join(output_dir, 'predictions.csv'), index=False)

    # Ground truth
    gt_df = pd.DataFrame(gt, columns=cell_types)
    gt_df.to_csv(os.path.join(output_dir, 'ground_truth.csv'), index=False)

    # Metrics
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv(os.path.join(output_dir, 'metrics.csv'), index=False)

    # Model checkpoint
    torch.save(model.state_dict(), os.path.join(output_dir, 'model.pt'))

    # Args
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
    print("DECODE Transcriptomics Deconvolution")
    print("=" * 60)
    print(f"Device: {device}")
    print(f"if_pure: {args.if_pure}")

    # Load data
    train_X, train_y, test_X, test_y, meta = load_data(args.data_dir)
    cell_types = meta['cell_types']

    t0 = time.time()

    # Stage 2: Adversarial batch correction
    dann = train_stage2(train_X, train_y, test_X, args, device)

    # Stage 3: Contrastive learning
    model = train_stage3(train_X, train_y, test_X, dann, args, device)

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

    print("\nTranscriptomics deconvolution complete.")


if __name__ == '__main__':
    main()
