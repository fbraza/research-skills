# Theoretical Foundations of scvi-tools

This document explains the mathematical and statistical principles underlying scvi-tools, with focus on scRNA-seq models: scVI, LDVAE, CellAssign, and VeloVI.

## Core Concepts

### Variational Inference

**What is it?**
Variational inference is a technique for approximating complex probability distributions. In single-cell analysis, we want to understand the posterior distribution p(z|x) — the probability of latent variables z given observed data x.

**Why use it?**
- Exact inference is computationally intractable for complex models
- Scales to large datasets (millions of cells)
- Provides uncertainty quantification
- Enables Bayesian reasoning about cell states

**How does it work?**
1. Define a simpler approximate distribution q(z|x) with learnable parameters
2. Minimize the KL divergence between q(z|x) and true posterior p(z|x)
3. Equivalent to maximizing the Evidence Lower Bound (ELBO)

**ELBO Objective**:
```
ELBO = E_q[log p(x|z)] - KL(q(z|x) || p(z))
       ↑                    ↑
  Reconstruction          Regularization
```

- **Reconstruction term**: Model should generate data similar to observed
- **Regularization term**: Latent representation should match prior

### Variational Autoencoders (VAEs)

**Architecture**:
```
x (observed data)
    ↓
[Encoder Neural Network]
    ↓
z (latent representation)
    ↓
[Decoder Neural Network]
    ↓
x̂ (reconstructed data)
```

**Encoder**: Maps cells (x) to latent space (z)
- Learns q(z|x), the approximate posterior
- Parameterized by neural network with learnable weights
- Outputs mean and variance of latent distribution

**Decoder**: Maps latent space (z) back to gene space
- Learns p(x|z), the likelihood
- Generates gene expression from latent representation
- Models count distributions (Negative Binomial, Zero-Inflated NB)

**Reparameterization Trick**:
- Allows backpropagation through stochastic sampling
- Sample z = μ + σ ⊙ ε, where ε ~ N(0,1)
- Enables end-to-end training with gradient descent

### Amortized Inference

**Concept**: Share encoder parameters across all cells.

**Traditional inference**: Learn separate latent variables for each cell
- n_cells × n_latent parameters
- Does not scale to large datasets

**Amortized inference**: Learn single encoder for all cells
- Fixed number of parameters regardless of cell count
- Enables fast inference on new cells
- Transfers learned patterns across dataset

**Benefits**:
- Scalable to millions of cells
- Fast inference on query data
- Leverages shared structure across cells
- Enables few-shot learning

## Statistical Modeling

### Count Data Distributions

Single-cell data are counts (integer-valued), requiring appropriate distributions.

#### Negative Binomial (NB)
```
x ~ NB(μ, θ)
```
- **μ (mean)**: Expected expression level
- **θ (dispersion)**: Controls variance
- **Variance**: Var(x) = μ + μ²/θ

**When to use**: Gene expression without zero-inflation
- More flexible than Poisson (allows overdispersion)
- Models technical and biological variation

#### Zero-Inflated Negative Binomial (ZINB)
```
x ~ π·δ₀ + (1-π)·NB(μ, θ)
```
- **π (dropout rate)**: Probability of technical zero
- **δ₀**: Point mass at zero
- **NB(μ, θ)**: Expression when not dropped out

**When to use**: Sparse scRNA-seq data
- Models technical dropout separately from biological zeros
- Better fit for highly sparse data (e.g., 10x Chromium)

#### Poisson
```
x ~ Poisson(μ)
```
- Simplest count distribution
- Mean equals variance: Var(x) = μ

**When to use**: Less common for scRNA-seq; appropriate when overdispersion is minimal
- More restrictive than NB
- Faster computation

### Batch Correction Framework

**Problem**: Technical variation confounds biological signal
- Different sequencing runs, protocols, labs
- Must remove technical effects while preserving biology

**scvi-tools approach**:
1. Encode batch as categorical variable s
2. Include s in generative model
3. Latent space z is batch-invariant
4. Decoder conditions on s for batch-specific effects

**Mathematical formulation**:
```
Encoder: q(z|x, s)  - batch-aware encoding
Latent: z           - batch-corrected representation
Decoder: p(x|z, s)  - batch-specific decoding
```

**Key insight**: Batch info flows through decoder, not latent space
- z captures biological variation
- s explains technical variation
- Separable biology and batch effects

### Deep Generative Modeling

**Generative model**: Learns p(x), the data distribution

**Process**:
1. Sample latent variable: z ~ p(z) = N(0, I)
2. Generate expression: x ~ p(x|z)
3. Joint distribution: p(x, z) = p(x|z)p(z)

**Benefits**:
- Generate synthetic cells
- Impute missing values
- Quantify uncertainty
- Perform counterfactual predictions

**Inference network**: Inverts generative process
- Given x, infer z
- q(z|x) approximates true posterior p(z|x)

## Model Architecture Details

### scVI Architecture

**Input**: Gene expression counts x ∈ ℕ^G (G genes)

**Encoder**:
```
h = ReLU(W₁·x + b₁)
μ_z = W₂·h + b₂
log σ²_z = W₃·h + b₃
z ~ N(μ_z, σ²_z)
```

**Latent space**: z ∈ ℝ^d (typically d=10-30)

**Decoder**:
```
h = ReLU(W₄·z + b₄)
μ = softmax(W₅·h + b₅) · library_size
θ = exp(W₆·h + b₆)
π = sigmoid(W₇·h + b₇)  # for ZINB
x ~ ZINB(μ, θ, π)
```

**Loss function (ELBO)**:
```
L = E_q[log p(x|z)] - KL(q(z|x) || N(0,I))
```

### Handling Covariates

**Categorical covariates** (batch, donor, etc.):
- One-hot encoded: s ∈ {0,1}^K
- Concatenate with latent: [z, s]
- Or use conditional layers

**Continuous covariates** (library size, percent_mito):
- Standardize to zero mean, unit variance
- Include in encoder and/or decoder

**Covariate injection strategies**:
- **Concatenation**: [z, s] fed to decoder
- **Deep injection**: s added at multiple layers
- **Conditional batch norm**: Batch-specific normalization

## Advanced Theoretical Concepts

### Transfer Learning (scArches)

**Concept**: Use pretrained model as initialization for new data

**Process**:
1. Train reference model on large dataset
2. Freeze encoder parameters
3. Fine-tune decoder on query data
4. Or fine-tune all with lower learning rate

**Why it works**:
- Encoder learns general cellular representations
- Decoder adapts to query-specific characteristics
- Prevents catastrophic forgetting

**Applications**:
- Query-to-reference mapping
- Few-shot learning for rare cell types
- Rapid analysis of new datasets

### Counterfactual Prediction

**Goal**: Predict outcome under different conditions

**Example**: "What would this cell look like if from a different batch?"

**Method**:
1. Encode cell to latent: z = Encoder(x, s_original)
2. Decode with new condition: x_new = Decoder(z, s_new)
3. x_new is counterfactual prediction

**Applications**:
- Batch effect assessment
- Predicting treatment response
- In silico perturbation studies

### Posterior Predictive Distribution

**Definition**: Distribution of new data given observed data

```
p(x_new | x_observed) = ∫ p(x_new|z) q(z|x_observed) dz
```

**Estimation**: Sample z from q(z|x), generate x_new from p(x_new|z)

**Uses**:
- Uncertainty quantification
- Robust predictions
- Outlier detection

## Differential Expression Framework

### Bayesian Approach

**Traditional methods**: Compare point estimates
- Wilcoxon, t-test, etc.
- Ignore uncertainty
- Require pseudocounts

**scvi-tools approach**: Compare distributions
- Sample from posterior: μ_A ~ p(μ|x_A), μ_B ~ p(μ|x_B)
- Compute log fold-change: LFC = log(μ_B) - log(μ_A)
- Posterior distribution of LFC quantifies uncertainty

### Bayes Factor

**Definition**: Ratio of posterior odds to prior odds

```
BF = P(H₁|data) / P(H₀|data)
     ─────────────────────────
     P(H₁) / P(H₀)
```

**Interpretation**:
- BF > 3: Moderate evidence for H₁
- BF > 10: Strong evidence
- BF > 100: Decisive evidence

**In scvi-tools**: Used to rank genes by evidence for DE

### False Discovery Proportion (FDP)

**Goal**: Control expected false discovery rate

**Procedure**:
1. For each gene, compute posterior probability of DE
2. Rank genes by evidence (Bayes factor)
3. Select top k genes such that E[FDP] ≤ α

**Advantage over p-values**:
- Fully Bayesian
- Natural for posterior inference
- No arbitrary thresholds

## Implementation Details

### Optimization

**Optimizer**: Adam (adaptive learning rates)
- Default lr = 0.001
- Momentum parameters: β₁=0.9, β₂=0.999

**Training loop**:
1. Sample mini-batch of cells
2. Compute ELBO loss
3. Backpropagate gradients
4. Update parameters with Adam
5. Repeat until convergence

**Convergence criteria**:
- ELBO plateaus on validation set
- Early stopping prevents overfitting
- Typically 200-500 epochs

### Regularization

**KL annealing**: Gradually increase KL weight
- Prevents posterior collapse
- Starts at 0, increases to 1 over epochs

**Dropout**: Random neuron dropping during training
- Default: 0.1 dropout rate
- Prevents overfitting
- Improves generalization

**Weight decay**: L2 regularization on weights
- Prevents large weights
- Improves stability

### Scalability

**Mini-batch training**:
- Process subset of cells per iteration
- Batch size: 64-256 cells
- Enables scaling to millions of cells

**Stochastic optimization**:
- Estimates ELBO on mini-batches
- Unbiased gradient estimates
- Converges to optimal solution

**GPU acceleration**:
- Neural networks naturally parallelize
- Order of magnitude speedup
- Essential for large datasets

## Connections to Other Methods

### vs. PCA
- **PCA**: Linear, deterministic
- **scVI**: Nonlinear, probabilistic
- **Advantage**: scVI captures complex structure, handles counts

### vs. t-SNE/UMAP
- **t-SNE/UMAP**: Visualization-focused
- **scVI**: Full generative model
- **Advantage**: scVI enables downstream tasks (DE, imputation)

### vs. Seurat Integration
- **Seurat**: Anchor-based alignment
- **scVI**: Probabilistic modeling
- **Advantage**: scVI provides uncertainty, works for multiple batches

### vs. Harmony
- **Harmony**: PCA + batch correction
- **scVI**: VAE-based
- **Advantage**: scVI handles counts natively, more flexible

## Extended scRNA-seq Models

### LDVAE: Linear Decoder for Interpretability

The Linearly Decoded VAE (LDVAE, Svensson et al. 2020) replaces scVI's non-linear decoder with a linear function:

```
μ = softmax(z · W^T)
```

where W is a gene loadings matrix. Each latent dimension maps directly to a weighted combination of genes, making the factors interpretable as gene programs. The encoder remains non-linear (deep neural network), preserving the model's ability to capture complex relationships during inference. The decoder matrix W can be extracted via `model.get_loadings()` and analyzed like PCA loadings — but with proper count-based likelihood (Gamma-Poisson) instead of Gaussian assumptions.

**Key trade-off**: LDVAE sacrifices some reconstruction accuracy for interpretability. Use when understanding which genes drive which axes of variation matters more than maximizing model fit.

**Practical considerations**:
- Loadings matrix W has shape (n_latent × n_genes); each row is a gene program
- Positive weights indicate genes upregulated along that axis; negative weights indicate downregulated genes
- Unlike PCA, factors are not orthogonal by construction — inspect correlation among loadings
- Combine with `model.get_latent_representation()` to project cells onto interpretable axes

### CellAssign: Marker-Based Probabilistic Annotation

CellAssign (Zhang et al. 2019) uses a hierarchical Bayesian model where gene expression follows a negative binomial distribution with an additional over-expression term δ_gc for marker genes. If gene g is a marker for cell type c, its expression is multiplied by e^δ_gc (learned from data). The model structure is:

- **Prior**: Dirichlet over cell type proportions
- **Likelihood**: Negative binomial with library size normalization
- **Inference**: Expectation-Maximization with mini-batches (stochastic EM in scvi-tools implementation)
- **Output**: Posterior probability P(cell_type | expression) for each cell

**Marker matrix**: The binary matrix ρ (genes × cell types) encodes prior knowledge — ρ_gc = 1 if gene g is a known marker for type c, 0 otherwise. Only marker genes enter the likelihood; non-marker genes are not modeled. Cells not matching any known type can be assigned to an "other" category.

**Key properties**:
- Does not require a pre-trained reference atlas — only a marker gene list
- Outputs calibrated probabilities, not hard labels
- Scales with number of marker genes and cell types, not total gene count
- More appropriate than correlation-based label transfer when marker knowledge is reliable and the reference atlas is absent or mismatched

### VeloVI: Probabilistic RNA Velocity

VeloVI (Gayoso et al. 2023) reformulates RNA velocity as a deep generative model. It models the relationship between spliced (s) and unspliced (u) RNA abundances through gene-specific kinetic parameters and a shared cell representation:

**Kinetic parameters**:
- α_g: Transcription rate (gene-specific)
- β_g: Splicing rate (gene-specific)
- γ_g: Degradation rate (gene-specific)
- t_n: Latent time per cell, derived from low-dimensional cell representation z_n

**Generative model**:
```
z_n ~ N(0, I)                        (cell representation)
t_n = f(z_n)                         (latent time from shared representation)
u_gn ~ NB(u*(t_n, α_g, β_g), φ_g)   (unspliced counts)
s_gn ~ NB(s*(t_n, β_g, γ_g), φ_g)   (spliced counts)
```

The key innovation is tying latent times across genes through the shared cell representation z_n. Rather than fitting kinetics independently per gene (as in scVelo), information is pooled across genes, producing more coherent and robust velocity estimates.

**Uncertainty outputs**: Because the model is generative, it produces posterior distributions over velocities, enabling:
- **Intrinsic uncertainty**: Variance in velocity direction estimates per gene and cell
- **Extrinsic uncertainty**: Variability in predicted future cell states across posterior samples
- **Permutation scores**: Per-gene assessment of whether coherent dynamics are present (distinguishes dynamic from steady-state genes)
- **Velocity coherence**: Per-cell measure of directional consistency across genes

**Practical guidance**:
- Use `model.get_velocity()` to obtain posterior mean velocities
- Use `model.get_permutation_scores()` to filter genes with uninformative dynamics before downstream projection (e.g., with scVelo's `velocity_graph`)
- Intrinsic and extrinsic uncertainty can be used to flag cells in ambiguous transition states

## Mathematical Notation Reference

**Common symbols**:
- x: Observed gene expression (counts)
- z: Latent representation
- θ: Model parameters (context-dependent; also dispersion in NB)
- q(z|x): Approximate posterior (encoder)
- p(x|z): Likelihood (decoder)
- p(z): Prior on latent variables
- μ, σ²: Mean and variance
- π: Dropout probability (ZINB)
- θ (in NB): Dispersion parameter
- s: Batch/covariate indicator
- W: Weight matrix (general); gene loadings matrix (LDVAE)
- ρ: Marker matrix (CellAssign, genes × cell types)
- δ_gc: Log over-expression coefficient for marker gene g in cell type c (CellAssign)
- α_g, β_g, γ_g: Transcription, splicing, degradation rates (VeloVI)
- t_n: Latent time for cell n (VeloVI)

## Further Reading

**Key Papers**:
1. Lopez et al. (2018): "Deep generative modeling for single-cell transcriptomics" — scVI
2. Xu et al. (2021): "Probabilistic harmonization and annotation of single-cell transcriptomics" — scANVI
3. Boyeau et al. (2019): "Deep generative models for detecting differential expression in single cells"
4. Svensson et al. (2020): "Interpretable factor models of single-cell RNA-seq via variational autoencoders" — LDVAE
5. Zhang et al. (2019): "CellAssign: Probabilistic cell type assignment of single-cell RNA-seq data" — CellAssign
6. Gayoso et al. (2023): "Deep generative modeling of transcriptional dynamics for RNA velocity analysis in single cells" — VeloVI

**Concepts to explore**:
- Variational inference in machine learning
- Bayesian deep learning
- Information theory (KL divergence, mutual information)
- Generative models (GANs, normalizing flows, diffusion models)
- Probabilistic programming (Pyro, PyTorch)
- RNA velocity theory (La Manno et al. 2018; Bergen et al. 2020)

**Mathematical background**:
- Probability theory and statistics
- Linear algebra and calculus
- Optimization theory
- Information theory
- Ordinary differential equations (for kinetic models in VeloVI)
