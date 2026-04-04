# Histogram / Bar Plot with Error Bars

Publication-ready bar plots with SEM or SD error bars for comparing group means. Use when the primary message is the comparison of central tendency across conditions.

## When to Use

- Comparing group means with error bars (SEM or SD)
- Presenting pre-computed summary statistics (mean +/- error)
- When the audience expects bar charts (common in biology/medicine)
- Always overlay individual data points when showing raw data (n < 30)

## Input Data

Two input modes are supported:

### Mode 1: Raw data (long format)

| Column | Type | Description |
|--------|------|-------------|
| `group` | str | Categorical grouping variable |
| `value` | float | Individual numeric measurements |

```
group,value
Control,5.2
Control,4.8
Control,5.5
Treatment,8.1
Treatment,7.6
Treatment,8.3
```

### Mode 2: Pre-computed summary

| Column | Type | Description |
|--------|------|-------------|
| `group` | str | Categorical grouping variable |
| `mean` | float | Group mean |
| `sem` (or `sd`) | float | Standard error of the mean (or standard deviation) |
| `n` (optional) | int | Sample size per group |

```
group,mean,sem,n
Control,5.17,0.20,3
Treatment,8.00,0.21,3
```

## UltraPlot Implementation

```python
import numpy as np
import pandas as pd
import ultraplot as uplt
import matplotlib as mpl

OKABE_ITO = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7", "#000000",
]


def _draw_significance_bracket(ax, x1, x2, y, p_value=None, text=None, h=0.02, lw=0.8):
    """Draw a significance bracket between two x positions.

    Draws a horizontal bracket with vertical drops at each end and a
    significance annotation (asterisks or custom text) centered above.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to draw on.
    x1 : float
        Left x position of the bracket.
    x2 : float
        Right x position of the bracket.
    y : float
        Y position of the bracket bar (in data coordinates).
    p_value : float or None, optional
        P-value to convert to asterisk notation. Ignored if `text` is
        provided, by default None.
    text : str or None, optional
        Custom annotation text. Overrides `p_value` if provided,
        by default None.
    h : float, optional
        Height of the vertical drop lines as a fraction of the y-axis
        range, by default 0.02.
    lw : float, optional
        Line width for the bracket, by default 0.8.
    """
    if text is None and p_value is not None:
        if p_value <= 0.001:
            text = "***"
        elif p_value <= 0.01:
            text = "**"
        elif p_value <= 0.05:
            text = "*"
        else:
            text = "ns"
    elif text is None:
        text = ""

    y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
    drop = h * y_range

    ax.plot([x1, x1, x2, x2], [y - drop, y, y, y - drop], color="black", lw=lw, clip_on=False)
    ax.text(
        (x1 + x2) / 2, y + drop * 0.3, text,
        ha="center", va="bottom", fontsize=8, color="black",
    )


def plot_bar_error(
    df,
    group_col=None,
    value_col=None,
    mean_col=None,
    sem_col=None,
    error_type="sem",
    figsize=(3.5, 3),
    title="",
    ylabel="",
    palette=None,
    show_points=True,
    point_size=4,
    alpha=0.7,
    jitter_width=0.12,
    bar_width=0.6,
    capsize=3,
    comparisons=None,
    stat_results=None,
    order=None,
    save_path=None,
):
    """Plot a publication-ready bar chart with error bars.

    Accepts either raw long-format data (computes mean and error
    automatically) or pre-computed summary statistics. Optionally overlays
    jittered individual data points and significance brackets.

    Parameters
    ----------
    df : pandas.DataFrame
        Input data. Either raw long-format (requires `group_col` and
        `value_col`) or pre-computed summary (requires `group_col`,
        `mean_col`, and `sem_col`).
    group_col : str or None, optional
        Column name for the categorical grouping variable. Required for
        both input modes, by default None.
    value_col : str or None, optional
        Column name for individual numeric measurements (raw data mode).
        If provided, mean and error are computed automatically,
        by default None.
    mean_col : str or None, optional
        Column name for pre-computed group means (summary mode),
        by default None.
    sem_col : str or None, optional
        Column name for pre-computed error values (summary mode),
        by default None.
    error_type : str, optional
        Type of error bars: 'sem' (standard error of the mean) or 'sd'
        (standard deviation). Only used in raw data mode, by default 'sem'.
    figsize : tuple of float, optional
        Figure dimensions in inches (width, height), by default (3.5, 3).
    title : str, optional
        Plot title, by default "".
    ylabel : str, optional
        Y-axis label, by default "".
    palette : list of str or None, optional
        List of hex color strings. If None, uses Okabe-Ito palette.
    show_points : bool, optional
        Whether to overlay jittered individual data points. Only available
        in raw data mode, by default True.
    point_size : float, optional
        Size of individual data points, by default 4.
    alpha : float, optional
        Transparency for data points, by default 0.7.
    jitter_width : float, optional
        Horizontal spread of jittered points, by default 0.12.
    bar_width : float, optional
        Width of each bar, by default 0.6.
    capsize : float, optional
        Width of error bar caps in points, by default 3.
    comparisons : list of tuple or None, optional
        List of group-name pairs for significance brackets,
        by default None.
    stat_results : dict or None, optional
        Dict mapping comparison tuples to p-values or significance strings,
        by default None.
    order : list of str or None, optional
        Custom ordering of groups along the x-axis, by default None.
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.
        If None, saves to ./results/bar_error_plot, by default None.

    Returns
    -------
    fig : ultraplot.Figure
        The figure object.
    ax : ultraplot.Axes
        The axes object.

    Raises
    ------
    ValueError
        If neither (group_col + value_col) nor (group_col + mean_col +
        sem_col) are provided.
    """
    if palette is None:
        palette = OKABE_ITO

    # ── Compute or extract summary statistics ────────────────────────
    raw_mode = value_col is not None

    if raw_mode:
        if group_col is None:
            raise ValueError("group_col is required for raw data mode.")
        groups = order if order is not None else df[group_col].unique().tolist()
        means = []
        errors = []
        ns = []
        raw_data = {}
        for g in groups:
            vals = df.loc[df[group_col] == g, value_col].dropna().values
            raw_data[g] = vals
            means.append(np.mean(vals))
            ns.append(len(vals))
            if error_type == "sem":
                errors.append(np.std(vals, ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0)
            else:
                errors.append(np.std(vals, ddof=1) if len(vals) > 1 else 0)
        means = np.array(means)
        errors = np.array(errors)
    elif mean_col is not None and sem_col is not None:
        if group_col is None:
            raise ValueError("group_col is required for summary data mode.")
        groups = order if order is not None else df[group_col].unique().tolist()
        summary_df = df.set_index(group_col).loc[groups].reset_index()
        means = summary_df[mean_col].values
        errors = summary_df[sem_col].values
        ns = summary_df["n"].values.tolist() if "n" in summary_df.columns else [None] * len(groups)
        show_points = False  # no raw data available
    else:
        raise ValueError(
            "Provide either (group_col + value_col) for raw data "
            "or (group_col + mean_col + sem_col) for pre-computed summary."
        )

    n_groups = len(groups)
    colors = [palette[i % len(palette)] for i in range(n_groups)]
    positions = np.arange(n_groups)

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    # Draw bars
    bars = ax.bar(
        positions, means,
        width=bar_width,
        color=colors,
        edgecolor="black",
        linewidth=0.8,
        alpha=0.6,
        zorder=2,
    )

    # Draw error bars
    ax.errorbar(
        positions, means, yerr=errors,
        fmt="none",
        ecolor="black",
        elinewidth=1.0,
        capsize=capsize,
        capthick=1.0,
        zorder=3,
    )

    # Overlay jittered points (raw data mode only)
    if show_points and raw_mode:
        rng = np.random.default_rng(42)
        for i, g in enumerate(groups):
            vals = raw_data[g]
            jitter = rng.uniform(-jitter_width, jitter_width, size=len(vals))
            ax.scatter(
                positions[i] + jitter, vals,
                s=point_size ** 2, c=colors[i], alpha=alpha,
                edgecolors="black", linewidths=0.3, zorder=4,
            )

    # ── n= labels ────────────────────────────────────────────────────
    if ns[0] is not None:
        tick_labels = [f"{g}\n(n={n})" for g, n in zip(groups, ns)]
    else:
        tick_labels = groups

    # ── Significance brackets ────────────────────────────────────────
    if comparisons is not None:
        y_max = np.max(means + errors)
        y_range = y_max  # since y starts at 0
        bracket_y = y_max + 0.08 * y_range

        for comp in comparisons:
            g1, g2 = comp
            if g1 in groups and g2 in groups:
                x1 = groups.index(g1)
                x2 = groups.index(g2)
                p_val = None
                text = None
                if stat_results is not None:
                    result = stat_results.get(comp, stat_results.get((g2, g1), None))
                    if isinstance(result, (int, float)):
                        p_val = result
                    elif isinstance(result, str):
                        text = result
                _draw_significance_bracket(ax, x1, x2, bracket_y, p_value=p_val, text=text)
                bracket_y += 0.08 * y_range

    # ── Format axes ──────────────────────────────────────────────────
    ax.set_xticks(positions)
    ax.set_xticklabels(tick_labels)

    # y-axis must start at 0 for bar charts
    ax.set_ylim(bottom=0)

    ax.format(
        ylabel=ylabel,
        title=title,
        xlabelsize=9,
        ylabelsize=9,
        xticklabelsize=8,
        yticklabelsize=8,
        titlesize=9,
        titleweight="bold",
    )

    # ── Save ─────────────────────────────────────────────────────────
    if save_path is None:
        save_path = "./results/bar_error_plot"
    fig.savefig(f"{save_path}.svg", dpi=300, bbox_inches="tight")
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax
```

## Colormap Recommendations

| Data encoding | Colormap | Notes |
|---------------|----------|-------|
| Categorical groups | Okabe-Ito palette | Colorblind-safe; up to 8 groups |
| Single-color gradient | One Okabe-Ito hue at varying lightness | Use for ordinal groups (e.g., dose response) |

## Customization Notes

- **`error_type`**: SEM is standard for comparing means across groups in biology. SD is appropriate when characterizing variability within a group. Always state which is used in the figure legend.
- **`show_points`**: Strongly recommended for n < 30. Bar + error bar without points hides the distribution and can be misleading (the "dynamite plot" problem).
- **`bar_width`**: Default 0.6 works for 2-6 groups. Increase to 0.7-0.8 for 2 groups, decrease to 0.4-0.5 for > 6 groups.
- **`capsize`**: Width of horizontal caps on error bars in points. Default 3 provides clear visibility without dominating the plot.
- **y-axis at zero**: Mandatory for bar charts. Truncating the y-axis exaggerates differences and violates visualization best practices.
- **`comparisons`**: Same bracket system as box/violin plots. Provide `stat_results` dict for automatic asterisk conversion.
- **`order`**: Control group ordering, e.g., `['Vehicle', 'Low', 'Medium', 'High']` for dose-response designs.
- **Pre-computed mode**: Use when summary statistics come from an external source or when individual data points are not available. Set `show_points=False` automatically.
