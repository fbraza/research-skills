# Box / Violin Plot

Publication-ready box or violin plots with individual data points. Use when comparing distributions across experimental groups with small-to-moderate sample sizes.

## When to Use

- Comparing distributions of a continuous variable across 2-6 groups
- Showing individual data points alongside summary statistics (essential for n < 30)
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
import matplotlib.patches as mpatches
from matplotlib.ticker import MultipleLocator, NullLocator

PUBLICATION_PALETTE = [
    "#3A5BA0",  # muted navy blue
    "#D4753C",  # burnt orange
    "#5A8F5A",  # forest green
    "#C44E52",  # brick red
    "#7B5EA7",  # dusty purple
    "#E8A838",  # warm gold
    "#46878F",  # teal
    "#B07AA1",  # mauve
    "#2E86C1",  # steel blue
    "#8C6D31",  # olive/khaki
    "#4E9A9A",  # sage teal
    "#D98880",  # dusty rose
    "#6B8E23",  # olive drab
    "#9B59B6",  # muted violet
    "#1ABC9C",  # muted aquamarine
    "#86714D",  # warm brown
    "#8EC9EB",  # light sky blue
    "#6E2F84",  # deep plum
    "#F5A623",  # bright amber / saffron
    "#7BC657",  # fresh leaf green
    "#708090",  # slate grey
    "#8B4513",  # saddle brown
    "#C5A9D8",  # soft lavender
    "#D35400",  # pumpkin
    "#B8860B",  # dark goldenrod
    "#E2DBA4",  # pale sand
    "#C0D0CB",  # pale sage
    "#E46571",  # coral pink
    "#90141A",  # oxblood
    "#2E5111",  # deep olive green
]

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
        List of hex color strings. If None, uses the publication palette.
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
                x1 = positions[groups.index(g1)]
                x2 = positions[groups.index(g2)]
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
    point_size=2,
    alpha=0.7,
    jitter_width=0.15,
    orient="v",
    groups_to_plot=None,
    order=None,
    uniform_color=None,
    point_color="black",
    legend_loc="upper left",
    legend_bbox_to_anchor=None,
    save_path=None,
):
    """Plot a publication-ready violin plot with optional jitter dots and legend.

    Draws kernel density violin plots for each group with a closed
    rectangular frame and optional overlaid jittered points.

    Layout rules follow the user's reference figures:
    - full rectangular frame (top/right spines visible)
    - optional black jitter dots
    - if more than 5 groups: same color for all violins, no legend,
      group labels shown on x-axis
    - if 5 groups or fewer: one color per group, legend shown,
      x-axis labels hidden

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
        Size of individual data points, by default 2.
    alpha : float, optional
        Transparency for data points, by default 0.7.
    jitter_width : float, optional
        Horizontal spread of jittered points, by default 0.15.
    orient : str, optional
        Orientation: 'v' (vertical) or 'h' (horizontal), by default 'v'.
    groups_to_plot : list of str or None, optional
        Subset of groups to include. If provided, only these groups are
        plotted, in the order given unless `order` overrides it.
    order : list of str or None, optional
        Custom ordering of groups along the categorical axis, by default None.
        Can also be used to reorder a subset selected with `groups_to_plot`.
    uniform_color : str or None, optional
        Fill color used when plotting more than 5 groups. If None, uses
        the first color from the publication palette.
    point_color : str, optional
        Color of jittered data points, by default "black".
    legend_loc : str, optional
        Matplotlib legend location used when 5 groups or fewer are plotted,
        by default "upper left".
    legend_bbox_to_anchor : tuple or None, optional
        Optional legend anchor passed to matplotlib for fine control of
        legend placement, by default None.
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
        palette = PUBLICATION_PALETTE

    available_groups = df[group_col].dropna().unique().tolist()
    if groups_to_plot is not None:
        groups = [g for g in groups_to_plot if g in available_groups]
    else:
        groups = available_groups

    if order is not None:
        groups = [g for g in order if g in groups]

    if len(groups) == 0:
        raise ValueError("No valid groups available to plot. Check `groups_to_plot` / `order`.")

    df = df.loc[df[group_col].isin(groups)].copy()
    df[group_col] = pd.Categorical(df[group_col], categories=groups, ordered=True)

    n_groups = len(groups)
    use_group_legend = n_groups <= 5
    if use_group_legend:
        colors = [palette[i % len(palette)] for i in range(n_groups)]
    else:
        uniform_color = uniform_color or PUBLICATION_PALETTE[0]
        colors = [uniform_color] * n_groups

    group_data = [df.loc[df[group_col] == g, value_col].dropna().values for g in groups]
    positions = np.arange(n_groups)

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    # Draw violins
    parts = ax.violinplot(
        group_data,
        showmeans=False,
        showmedians=False,
        showextrema=False,
        vert=(orient == "v"),
    )

    for i, body in enumerate(parts):
        body.set_facecolor(colors[i])
        body.set_edgecolor("black")
        body.set_linewidth(0.8)
        body.set_alpha(0.35)

    # Overlay jittered points
    if show_points:
        rng = np.random.default_rng(42)
        for i, data in enumerate(group_data):
            jitter = rng.uniform(-jitter_width, jitter_width, size=len(data))
            if orient == "v":
                ax.scatter(
                    positions[i] + jitter, data,
                    s=point_size ** 2, c=point_color, alpha=alpha,
                    edgecolors="none", linewidths=0, zorder=6,
                )
            else:
                ax.scatter(
                    data, positions[i] + jitter,
                    s=point_size ** 2, c=point_color, alpha=alpha,
                    edgecolors="none", linewidths=0, zorder=6,
                )

    # ── Format axes ──────────────────────────────────────────────────
    if orient == "v":
        ax.set_xticks(positions)
        if use_group_legend:
            ax.set_xticklabels([""] * n_groups)
        else:
            ax.set_xticklabels(groups, rotation=45, ha="right")
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
        if use_group_legend:
            ax.set_yticklabels([""] * n_groups)
        else:
            ax.set_yticklabels(groups)
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

    # Closed rectangular frame
    ax.grid(False)
    for side in ["left", "right", "top", "bottom"]:
        ax.spines[side].set_visible(True)
        ax.spines[side].set_linewidth(0.9)
        ax.spines[side].set_color("black")
    ax.tick_params(direction="out", width=0.8, length=3, color="black")
    if orient == "v":
        ax.yaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.xaxis.set_minor_locator(NullLocator())
    else:
        ax.xaxis.set_major_locator(MultipleLocator(1))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.yaxis.set_minor_locator(NullLocator())
    if use_group_legend:
        if orient == "v":
            ax.tick_params(axis="x", length=0)
        else:
            ax.tick_params(axis="y", length=0)

    # Legend only for small group counts
    if use_group_legend:
        if legend_bbox_to_anchor is None:
            legend_bbox_to_anchor = (1.02, 1.0)
        handles = [
            mpatches.Patch(facecolor=color, edgecolor="black", label=group, alpha=0.9)
            for group, color in zip(groups, colors)
        ]
        ax.legend(
            handles=handles,
            loc=legend_loc,
            bbox_to_anchor=legend_bbox_to_anchor,
            ncol=2 if n_groups > 3 else 1,
            frameon=False,
            fontsize=8,
            handlelength=1.0,
            handletextpad=0.5,
            columnspacing=0.8,
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
| Violin groups (default) | `PUBLICATION_PALETTE` | Muted publication-style palette matching the embedding plots |
| >5 violin groups | Single `uniform_color` | Same fill color for all violins; identify groups from x-axis labels |
| Paired/before-after | Two contrasting Okabe-Ito colors (`#0072B2`, `#D55E00`) | Blue vs vermillion for maximum contrast |

## Customization Notes

- **`show_points`**: Keep this available for biological data; black jitter dots are often the clearest choice.
- **`groups_to_plot`**: Pass the exact list of groups you want on the plot. If omitted, all groups are shown.
- **Automatic color logic**: `<=5` groups → one color per group + legend outside the panel + no x-axis labels. `>5` groups → same violin color for all groups + x-axis labels + no legend.
- **`jitter_width`**: Increase to 0.2-0.25 for large n to reduce point overlap. Decrease to 0.08-0.10 for very small n (< 5).
- **`order`**: Use this to reorder categories after filtering with `groups_to_plot`.
- **`orient`**: Horizontal orientation ('h') is useful when group labels are long.
- **Closed frame**: All four spines are visible to preserve the boxed look seen in the reference figures.
- **Minimal ticks**: Use integer-only major ticks on the numeric axis (…, -1, 0, 1, 2, …) and disable intermediate minor ticks.
- **Violin plot sample size**: Violin plots estimate kernel density, which requires sufficient data. For n < 15, prefer box plots. For n < 5, consider jitter-only plots.
