# Forest Plot (HR/OR)

Publication-ready forest plot for hazard ratios (HR) or odds ratios (OR) from survival analysis, Cox regression, or logistic regression. Use when displaying effect sizes with confidence intervals across multiple variables.

## When to Use

- To display results from Cox proportional hazards regression (HR)
- To display results from logistic regression (OR)
- To compare effect sizes across multiple variables in a single figure
- To visualize multivariate model results for publication
- Standard figure in clinical and epidemiological studies

## Input Data

Expected input: a DataFrame with one row per variable/covariate.

| Column | Type | Description |
|--------|------|-------------|
| `variable` | str | Variable name (e.g., "Age (per 10 years)", "Stage III vs I") |
| `estimate` | float | HR or OR point estimate |
| `ci_lower` | float | Lower bound of 95% CI |
| `ci_upper` | float | Upper bound of 95% CI |
| `pvalue` | float or str | P-value for annotation (can include "<0.001") |

Example CSV:
```
variable,estimate,ci_lower,ci_upper,pvalue
Age (per 10 years),1.23,1.05,1.44,0.012
Stage III vs I,2.45,1.67,3.60,<0.001
Treatment B vs A,0.68,0.49,0.94,0.019
Sex (Male vs Female),1.05,0.78,1.41,0.752
BMI (per 5 units),1.12,0.95,1.32,0.168
```

## UltraPlot Implementation

```python
import numpy as np
import pandas as pd
import ultraplot as uplt
import matplotlib as mpl


def plot_forest(
    df,
    estimate_col="estimate",
    ci_lower_col="ci_lower",
    ci_upper_col="ci_upper",
    variable_col="variable",
    pvalue_col="pvalue",
    log_scale=True,
    reference_line=1.0,
    sig_threshold=0.05,
    sort_by="input",
    show_annotations=True,
    marker_size=6,
    figsize=(5, 3),
    title="",
    label="HR (95% CI)",
    save_path=None,
):
    """Plot a publication-ready forest plot for hazard ratios or odds ratios.

    Displays each variable as a point estimate with horizontal confidence
    interval error bars. X-axis uses log scale by default (mandatory for
    HR and OR interpretation). Significant variables are highlighted.

    Parameters
    ----------
    df : pandas.DataFrame
        Summary statistics table with one row per variable. Must contain
        columns for variable names, point estimates, and confidence bounds.
    estimate_col : str, optional
        Column name for point estimates (HR or OR), by default "estimate".
    ci_lower_col : str, optional
        Column name for lower CI bound, by default "ci_lower".
    ci_upper_col : str, optional
        Column name for upper CI bound, by default "ci_upper".
    variable_col : str, optional
        Column name for variable labels, by default "variable".
    pvalue_col : str, optional
        Column name for p-values (float or str), by default "pvalue".
    log_scale : bool, optional
        Whether to use log scale on x-axis. Mandatory for HR/OR.
        Set to False for beta coefficients, by default True.
    reference_line : float, optional
        Position of the null-effect reference line. 1.0 for HR/OR,
        0.0 for beta coefficients, by default 1.0.
    sig_threshold : float, optional
        P-value threshold for significance coloring, by default 0.05.
    sort_by : str, optional
        How to order variables on y-axis. One of "input" (preserve
        DataFrame order), "estimate" (by effect size), or "pvalue"
        (most significant at top), by default "input".
    show_annotations : bool, optional
        Whether to display "HR (95% CI)" and p-value text on the right
        side of the plot, by default True.
    marker_size : float, optional
        Size of point estimate markers, by default 6.
    figsize : tuple of float, optional
        Figure dimensions in inches (width, height). Width should
        accommodate annotations if enabled, by default (5, 3).
    title : str, optional
        Plot title, by default "".
    label : str, optional
        Label for the x-axis and annotation header (e.g., "HR (95% CI)"
        or "OR (95% CI)"), by default "HR (95% CI)".
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.
        If None, saves to ./results/forest_plot, by default None.

    Returns
    -------
    fig : ultraplot.Figure
        The figure object.
    ax : ultraplot.Axes
        The axes object.
    """
    # ── Prepare data ──────────────────────────────────────────────────
    plot_df = df.copy()

    # Parse p-values: handle string entries like "<0.001"
    def _parse_pvalue(p):
        if isinstance(p, str):
            p_clean = p.strip().lstrip("<>")
            try:
                return float(p_clean)
            except ValueError:
                return np.nan
        return float(p)

    plot_df["_pval_numeric"] = plot_df[pvalue_col].apply(_parse_pvalue)

    # ── Sort ──────────────────────────────────────────────────────────
    if sort_by == "pvalue":
        plot_df = plot_df.sort_values("_pval_numeric", ascending=False)
    elif sort_by == "estimate":
        plot_df = plot_df.sort_values(estimate_col, ascending=True)
    else:
        # "input" — reverse so first row appears at the top
        plot_df = plot_df.iloc[::-1]

    plot_df = plot_df.reset_index(drop=True)
    n_vars = len(plot_df)

    # ── Classify significance ─────────────────────────────────────────
    plot_df["_significant"] = plot_df["_pval_numeric"] <= sig_threshold

    color_sig = "#0072B2"    # Okabe-Ito blue
    color_ns = "#BBBBBB"     # neutral grey

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    y_positions = np.arange(n_vars)

    for i, row in plot_df.iterrows():
        color = color_sig if row["_significant"] else color_ns
        ci_low = row[ci_lower_col]
        ci_high = row[ci_upper_col]
        est = row[estimate_col]

        # Horizontal CI line
        ax.plot(
            [ci_low, ci_high], [i, i],
            color=color, linewidth=1.5, solid_capstyle="round", zorder=2,
        )
        # Point estimate
        ax.scatter(
            est, i,
            color=color, s=marker_size ** 2, zorder=3,
            edgecolors="white", linewidths=0.3,
        )

    # ── Reference line ────────────────────────────────────────────────
    ax.axvline(
        reference_line, color="grey", linestyle="--",
        linewidth=0.8, zorder=1,
    )

    # ── Annotations (right side) ──────────────────────────────────────
    if show_annotations:
        # Determine x position for text: right edge of the plot
        all_upper = plot_df[ci_upper_col].max()
        if log_scale:
            text_x = all_upper * 1.6
        else:
            text_x = all_upper + (all_upper - plot_df[ci_lower_col].min()) * 0.15

        for i, row in plot_df.iterrows():
            est = row[estimate_col]
            ci_low = row[ci_lower_col]
            ci_high = row[ci_upper_col]
            pval = row[pvalue_col]

            # Format p-value
            if isinstance(pval, str):
                pval_str = pval
            else:
                if pval < 0.001:
                    pval_str = "<0.001"
                else:
                    pval_str = f"{pval:.3f}"

            annotation = f"{est:.2f} ({ci_low:.2f}\u2013{ci_high:.2f})  p={pval_str}"
            ax.text(
                text_x, i, annotation,
                va="center", ha="left", fontsize=7,
                fontfamily="Arial",
            )

    # ── Y-axis labels ─────────────────────────────────────────────────
    ax.set_yticks(y_positions)
    ax.set_yticklabels(plot_df[variable_col].values, fontsize=8)

    # ── Format axes ───────────────────────────────────────────────────
    xlabel = label.split("(")[0].strip() if "(" in label else label
    format_kwargs = dict(
        xlabel=xlabel,
        ylabel="",
        title=title,
        xlabelsize=9,
        ylabelsize=8,
        xticklabelsize=8,
        yticklabelsize=8,
        titlesize=9,
        titleweight="bold",
    )
    if log_scale:
        format_kwargs["xscale"] = "log"

    ax.format(**format_kwargs)

    # ── Adjust x-limits to accommodate annotations ────────────────────
    if show_annotations:
        x_right = text_x * 3 if log_scale else text_x + (text_x - reference_line) * 2
        current_left = plot_df[ci_lower_col].min()
        x_left = current_left * 0.7 if log_scale else current_left - abs(current_left) * 0.1
        ax.set_xlim(x_left, x_right)

    # Remove top and right spines for cleaner look
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # ── Save ──────────────────────────────────────────────────────────
    if save_path is None:
        save_path = "./results/forest_plot"
    fig.savefig(f"{save_path}.svg", dpi=300, bbox_inches="tight")
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax
```

## Colormap Recommendations

| Data encoding | Colors | Notes |
|---------------|--------|-------|
| Significant vs NS | `#0072B2` (blue) / `#BBBBBB` (grey) | Default 2-color scheme |
| By direction (alternative) | `#0072B2` (protective, <1) / `#D55E00` (risk, >1) / `#BBBBBB` (NS) | Use when direction matters more than significance |

To switch to direction-based coloring, replace the significance classification block:
```python
# Direction-based coloring (alternative)
if row["_significant"] and est < reference_line:
    color = "#0072B2"   # protective (blue)
elif row["_significant"] and est >= reference_line:
    color = "#D55E00"   # risk (vermillion)
else:
    color = "#BBBBBB"   # NS (grey)
```

## Customization Notes

- **`log_scale=True`**: Mandatory for HR and OR. The log scale ensures that protective (HR=0.5) and harmful (HR=2.0) effects are visually symmetric around the reference line. Set to `False` only for linear beta coefficients.
- **`reference_line`**: 1.0 for HR/OR (null = no effect). 0.0 for beta coefficients.
- **`sort_by`**: `"input"` preserves the model's variable order (recommended for multivariate models). `"pvalue"` places the most significant variables at the top. `"estimate"` orders by effect size.
- **`show_annotations`**: Adds formatted "HR (95% CI) p=value" text to the right of each row. Increase `figsize` width (e.g., `(6, 3)`) when enabled to prevent clipping.
- **`marker_size`**: Scaled as `s = marker_size ** 2` in scatter. Default of 6 works for most plots. Increase for emphasis or when few variables are shown.
- **`label`**: Controls both the x-axis label and the annotation format. Set to `"OR (95% CI)"` for logistic regression results.
- **`sig_threshold`**: Uses 0.05 by default. This applies to coloring only; the p-values shown in annotations are the original values from the input data.
- **Confidence interval style**: Lines use `solid_capstyle="round"` for clean endpoints. Points have a thin white edge for separation from the CI line.
