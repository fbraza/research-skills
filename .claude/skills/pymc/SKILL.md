---
id: pymc
name: PyMC Bayesian Modeling
description: >
  Bayesian statistical modeling with PyMC v5. Build hierarchical models, run MCMC
  (NUTS), variational inference (ADVI), and model comparison (LOO/WAIC).
  Use for probabilistic inference on clinical data, hierarchical patient models,
  mixed-effects Bayesian models, uncertainty quantification, and any analysis
  requiring explicit prior specification or full posterior distributions.
  Trigger phrases: "Bayesian model", "PyMC", "hierarchical model", "MCMC",
  "posterior distribution", "probabilistic model", "mixed-effects Bayesian",
  "uncertainty quantification", "prior predictive check", "LOO model comparison".
category: statistics
short-description: "Bayesian hierarchical modeling with PyMC v5 — MCMC, NUTS, model comparison."
detailed-description: "PyMC v5 probabilistic programming for Bayesian analysis. Supports hierarchical/multilevel models, linear/logistic/Poisson regression, time series, MCMC (NUTS), variational inference (ADVI), prior/posterior predictive checks, and LOO/WAIC model comparison via ArviZ. Particularly useful for clinical data with grouped structure (patients, centers), missing data, and uncertainty quantification."
---

# PyMC Bayesian Modeling

Probabilistic programming for rigorous Bayesian inference. Particularly useful for:
- Hierarchical patient data (multiple centers, repeated measures)
- Clinical models requiring uncertainty quantification
- Mixed-effects Bayesian models
- Model comparison and selection
- Missing data handled as model parameters

## Installation

```bash
pip install pymc arviz
```

## Standard Workflow

### 1. Prepare data (always standardize predictors)

```python
import pymc as pm
import arviz as az
import numpy as np
import pandas as pd

# Standardize continuous predictors — critical for efficient sampling
X_mean = X.mean(axis=0)
X_std = X.std(axis=0)
X_scaled = (X - X_mean) / X_std
```

### 2. Build model with weakly informative priors

```python
coords = {
    'predictors': predictor_names,
    'obs_id': np.arange(len(y))
}

with pm.Model(coords=coords) as model:
    # Priors — always weakly informative, never flat
    alpha = pm.Normal('alpha', mu=0, sigma=1)
    beta = pm.Normal('beta', mu=0, sigma=1, dims='predictors')
    sigma = pm.HalfNormal('sigma', sigma=1)  # Scale parameters: always HalfNormal

    # Linear predictor
    mu = alpha + pm.math.dot(X_scaled, beta)

    # Likelihood
    y_obs = pm.Normal('y_obs', mu=mu, sigma=sigma, observed=y, dims='obs_id')
```

### 3. Prior predictive check (always do before fitting)

```python
with model:
    prior_pred = pm.sample_prior_predictive(samples=1000, random_seed=42)

az.plot_ppc(prior_pred, group='prior')
# Check: do prior predictions span plausible values?
```

### 4. Fit with MCMC (NUTS)

```python
with model:
    idata = pm.sample(
        draws=2000,
        tune=1000,
        chains=4,
        target_accept=0.9,   # Increase to 0.95-0.99 if divergences occur
        random_seed=42,
        idata_kwargs={'log_likelihood': True}  # Required for LOO comparison
    )
```

### 5. Check diagnostics

```python
# Key convergence checks
summary = az.summary(idata, var_names=['alpha', 'beta', 'sigma'])
print(summary[['mean', 'sd', 'hdi_3%', 'hdi_97%', 'r_hat', 'ess_bulk']])

# Must pass: R-hat < 1.01, ESS > 400, divergences == 0
print(f"Divergences: {idata.sample_stats.diverging.sum().values}")
az.plot_trace(idata, var_names=['alpha', 'beta'])
```

**If diagnostics fail:**
- Divergences → `target_accept=0.95`, use non-centered parameterization
- Low ESS → more draws, reparameterize
- High R-hat → longer chains, check multimodality

### 6. Posterior predictive check

```python
with model:
    pm.sample_posterior_predictive(idata, extend_inferencedata=True, random_seed=42)

az.plot_ppc(idata)
# Check: do posterior predictions match observed data patterns?
```

### 7. Report results

```python
# Point estimates and credible intervals
az.plot_forest(idata, var_names=['beta'], combined=True)
az.plot_posterior(idata, var_names=['beta'])

# Save
idata.to_netcdf('./results/model_trace.nc')
az.summary(idata).to_csv('./results/model_summary.csv')
```

---

## Common Model Templates

### Hierarchical model (patients nested in centers)

```python
with pm.Model(coords={'centers': center_names, 'patients': patient_ids}) as hier_model:
    # Hyperpriors
    mu_alpha = pm.Normal('mu_alpha', mu=0, sigma=10)
    sigma_alpha = pm.HalfNormal('sigma_alpha', sigma=1)

    # Group-level effects — NON-CENTERED parameterization (avoids divergences)
    alpha_offset = pm.Normal('alpha_offset', mu=0, sigma=1, dims='centers')
    alpha = pm.Deterministic('alpha', mu_alpha + sigma_alpha * alpha_offset, dims='centers')

    # Observation-level
    mu = alpha[center_idx] + pm.math.dot(X_scaled, beta)
    sigma = pm.HalfNormal('sigma', sigma=1)
    y = pm.Normal('y', mu=mu, sigma=sigma, observed=y_obs)
```

**Always use non-centered parameterization for hierarchical models.**

### Logistic regression (binary clinical outcomes)

```python
with pm.Model() as logistic_model:
    alpha = pm.Normal('alpha', mu=0, sigma=10)
    beta = pm.Normal('beta', mu=0, sigma=10, shape=n_predictors)

    logit_p = alpha + pm.math.dot(X_scaled, beta)
    y = pm.Bernoulli('y', logit_p=logit_p, observed=y_obs)
```

### Negative binomial (overdispersed counts — gene expression, cell counts)

```python
with pm.Model() as nb_model:
    alpha = pm.Normal('alpha', mu=0, sigma=1)
    beta = pm.Normal('beta', mu=0, sigma=1, shape=n_predictors)
    alpha_nb = pm.HalfNormal('alpha_nb', sigma=1)  # Overdispersion

    mu = pm.math.exp(alpha + pm.math.dot(X_scaled, beta))
    y = pm.NegativeBinomial('y', mu=mu, alpha=alpha_nb, observed=y_obs)
```

---

## Model Comparison (LOO)

```python
# Compare multiple models
compare_dict = {'model_A': idata_A, 'model_B': idata_B}
comparison = az.compare(compare_dict, ic='loo')
print(comparison)
az.plot_compare(comparison)

# Interpretation:
# Δloo < 2: models similar, prefer simpler
# Δloo 4-10: moderate evidence for better model
# Δloo > 10: strong evidence
```

---

## Prior Selection Guide

| Parameter type | Recommended prior |
|----------------|-------------------|
| Scale (σ, τ) | `pm.HalfNormal('s', sigma=1)` |
| Regression coefficient | `pm.Normal('b', mu=0, sigma=1)` (standardized data) |
| Probability | `pm.Beta('p', alpha=2, beta=2)` |
| Positive value | `pm.LogNormal('x', mu=0, sigma=1)` |
| Correlation matrix | `pm.LKJCorr('R', n=k, eta=2)` |
| Robust likelihood | `pm.StudentT('y', nu=nu, mu=mu, sigma=sigma)` |

**Never use flat priors** (`Uniform` over a wide range). Always weakly informative.

---

## Hard Rules

- **Always standardize predictors** before modeling
- **Always run prior predictive check** before fitting
- **Always check diagnostics** (R-hat < 1.01, ESS > 400, 0 divergences)
- **Always run posterior predictive check** after fitting
- **Use non-centered parameterization** for all hierarchical models
- **Set `random_seed`** for reproducibility
- **Include `log_likelihood=True`** when model comparison is planned
- **Invoke The Reviewer** after model fitting and diagnostics

## References

- [references/distributions.md](references/distributions.md) — Distribution catalog
- [references/sampling_inference.md](references/sampling_inference.md) — NUTS/ADVI/SMC guide
- [references/workflows.md](references/workflows.md) — Extended workflow examples
- [scripts/model_diagnostics.py](scripts/model_diagnostics.py) — Automated diagnostic checking
- [scripts/model_comparison.py](scripts/model_comparison.py) — LOO/WAIC comparison utilities
- [assets/hierarchical_model_template.py](assets/hierarchical_model_template.py) — Hierarchical template
- PyMC docs: https://www.pymc.io/
