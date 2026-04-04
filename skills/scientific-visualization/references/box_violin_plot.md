# Box / Violin Plot

Publication-ready box or violin plots with individual data points and statistical comparison brackets. Use when comparing distributions across experimental groups with small-to-moderate sample sizes.

## When to Use

- Comparing distributions of a continuous variable across 2-6 groups
- Showing individual data points alongside summary statistics (essential for n < 30)
- Adding statistical comparison brackets between specific group pairs
- Violin plots when sample size is large enough to estimate density (n >= 15 per group recommended)

## Input Data

Expected input: a DataFrame in long format with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `group` | str | Categorical grouping variable (e.g., 'Control', 'Treatment') |
| `value` | float | Numeric measurement |
| `sample_id` (optional) | str | Sample identifier for paired designs |

Example CSV:
```
group,value,sample_id
Control,5.2,S1
Control,4.8,S2
Control,5.5,S3
Treatment,8.1,S4
Treatment,7.6,S5
Treatment,8.3,S6
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


def plot_boxplot(
    df,
    group_col,
    value_col,
    figsize=(3.5, 3),
    title="",
    ylabel="",
    palette=None,
    show_points=True,
    point_size=4,
    alpha=0.7,
    jitter_width=0.15,
    comparisons=None,
    stat_results=None,
    orient="v",
    order=None,
    save_path=None,
):
    """Plot a publication-ready box plot with optional jittered data points.

    Draws box plots (median, IQR, 1.5*IQR whiskers) for each group with
    optional overlaid individual data points and significance brackets.

    Parameters
    ----------
    df : pandas.DataFrame
        Long-format DataFrame containing the data.
    group_col : str
        Column name for the categorical grouping variable.
    value_col : str
        Column name for the numeric measurement.
    figsize : tuple of float, optional
        Figure dimensions in inches (width, height), by default (3.5, 3).
    title : str, optional
        Plot title, by default "".
    ylabel : str, optional
        Y-axis label, by default "".
    palette : list of str or None, optional
        List of hex color strings. If None, uses Okabe-Ito palette.
    show_points : bool, optional
        Whether to overlay jittered individual data points, by default True.
    point_size : float, optional
        Size of individual data points, by default 4.
    alpha : float, optional
        Transparency for data points, by default 0.7.
    jitter_width : float, optional
        Horizontal spread of jittered points, by default 0.15.
    comparisons : list of tuple or None, optional
        List of group-name pairs for significance brackets, e.g.,
        [('Control', 'Treatment')]. By default None.
    stat_results : dict or None, optional
        Dict mapping comparison tuples to p-values or significance strings,
        e.g., {('Control', 'Treatment'): 0.003}. By default None.
    orient : str, optional
        Orientation: 'v' (vertical) or 'h' (horizontal), by default 'v'.
    order : list of str or None, optional
        Custom ordering of groups along the categorical axis, by default None.
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.
        If None, saves to ./results/boxplot, by default None.

    Returns
    -------
    fig : ultraplot.Figure
        The figure object.
    ax : ultraplot.Axes
        The axes object.
    """
    if palette is None:
        palette = OKABE_ITO

    groups = order if order is not None else df[group_col].unique().tolist()
    n_groups = len(groups)
    colors = [palette[i % len(palette)] for i in range(n_groups)]

    # Prepare data per group
    group_data = [df.loc[df[group_col] == g, value_col].dropna().values for g in groups]
    group_ns = [len(d) for d in group_data]
    positions = np.arange(n_groups)

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    # Draw box plots
    bp = ax.boxplot(
        group_data,
        positions=positions,
        widths=0.5,
        patch_artist=True,
        showfliers=False,
        medianprops=dict(color="black", linewidth=1.2),
        whiskerprops=dict(color="black", linewidth=0.8),
        capprops=dict(color="black", linewidth=0.8),
        boxprops=dict(linewidth=0.8),
        vert=(orient == "v"),
    )

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
        patch.set_edgecolor("black")

    # Overlay jittered points
    if show_points:
        rng = np.random.default_rng(42)
        for i, (data, color) in enumerate(zip(group_data, colors)):
            jitter = rng.uniform(-jitter_width, jitter_width, size=len(data))
            if orient == "v":
                ax.scatter(
                    positions[i] + jitter, data,
                    s=point_size ** 2, c=color, alpha=alpha,
                    edgecolors="black", linewidths=0.3, zorder=3,
                )
            else:
                ax.scatter(
                    data, positions[i] + jitter,
                    s=point_size ** 2, c=color, alpha=alpha,
                    edgecolors="black", linewidths=0.3, zorder=3,
                )

    # ── n= labels ────────────────────────────────────────────────────
    tick_labels = [f"{g}\n(n={n})" for g, n in zip(groups, group_ns)]

    # ── Significance brackets ────────────────────────────────────────
    if comparisons is not None:
        all_values = np.concatenate(group_data)
        y_max = np.max(all_values)
        y_range = np.ptp(all_values)
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
    if orient == "v":
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
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
    else:
        ax.set_yticks(positions)
        ax.set_yticklabels(tick_labels)
        ax.format(
            xlabel=ylabel,
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
        save_path = "./results/boxplot"
    fig.savefig(f"{save_path}.svg", dpi=300, bbox_inches="tight")
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax


def plot_violinplot(
    df,
    group_col,
    value_col,
    figsize=(3.5, 3),
    title="",
    ylabel="",
    palette=None,
    show_points=True,
    show_box=True,
    point_size=3,
    alpha=0.7,
    jitter_width=0.15,
    comparisons=None,
    stat_results=None,
    orient="v",
    order=None,
    save_path=None,
):
    """Plot a publication-ready violin plot with optional inner box and data points.

    Draws kernel density violin plots for each group with optional inner
    box plots showing median and IQR, overlaid individual data points,
    and significance brackets.

    Parameters
    ----------
    df : pandas.DataFrame
        Long-format DataFrame containing the data.
    group_col : str
        Column name for the categorical grouping variable.
    value_col : str
        Column name for the numeric measurement.
    figsize : tuple of float, optional
        Figure dimensions in inches (width, height), by default (3.5, 3).
    title : str, optional
        Plot title, by default "".
    ylabel : str, optional
        Y-axis label, by default "".
    palette : list of str or None, optional
        List of hex color strings. If None, uses Okabe-Ito palette.
    show_points : bool, optional
        Whether to overlay jittered individual data points, by default True.
    show_box : bool, optional
        Whether to show an inner box plot (median + IQR), by default True.
    point_size : float, optional
        Size of individual data points, by default 3.
    alpha : float, optional
        Transparency for data points, by default 0.7.
    jitter_width : float, optional
        Horizontal spread of jittered points, by default 0.15.
    comparisons : list of tuple or None, optional
        List of group-name pairs for significance brackets, by default None.
    stat_results : dict or None, optional
        Dict mapping comparison tuples to p-values or significance strings,
        by default None.
    orient : str, optional
        Orientation: 'v' (vertical) or 'h' (horizontal), by default 'v'.
    order : list of str or None, optional
        Custom ordering of groups along the categorical axis, by default None.
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.
        If None, saves to ./results/violinplot, by default None.

    Returns
    -------
    fig : ultraplot.Figure
        The figure object.
    ax : ultraplot.Axes
        The axes object.
    """
    if palette is None:
        palette = OKABE_ITO

    groups = order if order is not None else df[group_col].unique().tolist()
    n_groups = len(groups)
    colors = [palette[i % len(palette)] for i in range(n_groups)]

    group_data = [df.loc[df[group_col] == g, value_col].dropna().values for g in groups]
    group_ns = [len(d) for d in group_data]
    positions = np.arange(n_groups)

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    # Draw violins
    parts = ax.violinplot(
        group_data,
        positions=positions,
        showmeans=False,
        showmedians=False,
        showextrema=False,
        vert=(orient == "v"),
    )

    for i, body in enumerate(parts["bodies"]):
        body.set_facecolor(colors[i])
        body.set_edgecolor("black")
        body.set_linewidth(0.8)
        body.set_alpha(0.35)

    # Inner box plot (median + IQR)
    if show_box:
        for i, data in enumerate(group_data):
            if len(data) == 0:
                continue
            q1, median, q3 = np.percentile(data, [25, 50, 75])
            if orient == "v":
                ax.vlines(positions[i], q1, q3, color="black", linewidth=2.5, zorder=4)
                ax.scatter(positions[i], median, color="white", s=15, zorder=5, edgecolors="black", linewidths=0.5)
            else:
                ax.hlines(positions[i], q1, q3, color="black", linewidth=2.5, zorder=4)
                ax.scatter(median, positions[i], color="white", s=15, zorder=5, edgecolors="black", linewidths=0.5)

    # Overlay jittered points
    if show_points:
        rng = np.random.default_rng(42)
        for i, (data, color) in enumerate(zip(group_data, colors)):
            jitter = rng.uniform(-jitter_width, jitter_width, size=len(data))
            if orient == "v":
                ax.scatter(
                    positions[i] + jitter, data,
                    s=point_size ** 2, c=color, alpha=alpha,
                    edgecolors="black", linewidths=0.3, zorder=3,
                )
            else:
                ax.scatter(
                    data, positions[i] + jitter,
                    s=point_size ** 2, c=color, alpha=alpha,
                    edgecolors="black", linewidths=0.3, zorder=3,
                )

    # ── n= labels ────────────────────────────────────────────────────
    tick_labels = [f"{g}\n(n={n})" for g, n in zip(groups, group_ns)]

    # ── Significance brackets ────────────────────────────────────────
    if comparisons is not None:
        all_values = np.concatenate(group_data)
        y_max = np.max(all_values)
        y_range = np.ptp(all_values)
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
    if orient == "v":
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
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
    else:
        ax.set_yticks(positions)
        ax.set_yticklabels(tick_labels)
        ax.format(
            xlabel=ylabel,
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
        save_path = "./results/violinplot"
    fig.savefig(f"{save_path}.svg", dpi=300, bbox_inches="tight")
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax
```

## Colormap Recommendations

| Data encoding | Colormap | Notes |
|---------------|----------|-------|
| Categorical groups | Okabe-Ito palette | Colorblind-safe; up to 8 groups |
| Paired/before-after | Two contrasting Okabe-Ito colors (`#0072B2`, `#D55E00`) | Blue vs vermillion for maximum contrast |

## Customization Notes

- **`show_points`**: Always True for small sample sizes (n < 30). Individual data points are essential for transparency in biological publications.
- **`show_box`**: Inner box in violin plots shows median (white dot) and IQR (thick black line). Disable if overlaid points provide sufficient summary.
- **`jitter_width`**: Increase to 0.2-0.25 for large n to reduce point overlap. Decrease to 0.08-0.10 for very small n (< 5).
- **`comparisons`**: Provide a list of tuples, e.g., `[('Control', 'Treatment')]`. Brackets are drawn in order from bottom to top.
- **`stat_results`**: Map each comparison tuple to a p-value (float) for automatic asterisk conversion, or a string ('ns', '*', '**', '***') for manual annotation. Threshold mapping: `*** p <= 0.001`, `** p <= 0.01`, `* p <= 0.05`, `ns p > 0.05`.
- **`order`**: Pass a list to control group ordering on the x-axis, e.g., `['WT', 'Het', 'KO']` for genotype progression.
- **`orient`**: Horizontal orientation ('h') is useful when group labels are long.
- **Violin plot sample size**: Violin plots estimate kernel density, which requires sufficient data. For n < 15, prefer box plots. For n < 5, consider jitter-only plots.
