# Grouped Plots

Publication-ready grouped visualizations: jitter plots, dot plots, grouped bar charts, and grouped box/violin plots. Use when comparing distributions or means across two categorical dimensions simultaneously.

## When to Use

- Comparing a numeric variable across combinations of two categorical factors (e.g., tissue x treatment)
- Jitter plots: showing all individual data points colored by a grouping variable
- Dot plots: Cleveland-style horizontal comparisons of individual values
- Grouped bars: comparing means across nested experimental designs
- Grouped box/violin: comparing distributions across nested designs

## Input Data

Expected input: a DataFrame in long format with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `group` | str | Primary categorical variable (x-axis groups) |
| `subgroup` | str | Secondary categorical variable (color/hue) |
| `value` | float | Numeric measurement |

Example CSV:
```
group,subgroup,value
Tissue_A,Control,5.2
Tissue_A,Control,4.9
Tissue_A,Treatment,8.1
Tissue_A,Treatment,7.8
Tissue_B,Control,4.1
Tissue_B,Control,3.8
Tissue_B,Treatment,7.3
Tissue_B,Treatment,6.9
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


def plot_jitter(
    df,
    group_col,
    value_col,
    color_col=None,
    figsize=(3.5, 3),
    title="",
    ylabel="",
    palette=None,
    point_size=5,
    alpha=0.7,
    jitter_width=0.2,
    show_mean=True,
    mean_marker="_",
    order=None,
    save_path=None,
):
    """Plot a jitter (strip) plot with points for each group.

    Displays all individual data points with horizontal jitter, optionally
    colored by a secondary variable. Adds a horizontal line at the group
    mean or median for reference.

    Parameters
    ----------
    df : pandas.DataFrame
        Long-format DataFrame containing the data.
    group_col : str
        Column name for the categorical grouping variable (x-axis).
    value_col : str
        Column name for the numeric measurement (y-axis).
    color_col : str or None, optional
        Column name for coloring points by a secondary variable. If None,
        all points within a group share the same color, by default None.
    figsize : tuple of float, optional
        Figure dimensions in inches (width, height), by default (3.5, 3).
    title : str, optional
        Plot title, by default "".
    ylabel : str, optional
        Y-axis label, by default "".
    palette : list of str or None, optional
        List of hex color strings. If None, uses Okabe-Ito palette.
    point_size : float, optional
        Size of data points, by default 5.
    alpha : float, optional
        Transparency for data points, by default 0.7.
    jitter_width : float, optional
        Horizontal spread of jittered points, by default 0.2.
    show_mean : bool, optional
        Whether to show a horizontal line at the group mean, by default True.
    mean_marker : str, optional
        Marker style for the mean indicator, by default "_" (horizontal line).
    order : list of str or None, optional
        Custom ordering of groups along the x-axis, by default None.
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.
        If None, saves to ./results/jitter_plot, by default None.

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
    positions = np.arange(n_groups)
    rng = np.random.default_rng(42)

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    if color_col is not None:
        color_categories = df[color_col].unique().tolist()
        color_map = {cat: palette[i % len(palette)] for i, cat in enumerate(color_categories)}
    else:
        color_map = None

    group_ns = []
    for i, g in enumerate(groups):
        mask = df[group_col] == g
        vals = df.loc[mask, value_col].dropna()
        group_ns.append(len(vals))

        if color_col is not None:
            for cat in color_categories:
                sub_mask = mask & (df[color_col] == cat)
                sub_vals = df.loc[sub_mask, value_col].dropna().values
                if len(sub_vals) == 0:
                    continue
                jitter = rng.uniform(-jitter_width, jitter_width, size=len(sub_vals))
                ax.scatter(
                    positions[i] + jitter, sub_vals,
                    s=point_size ** 2, c=color_map[cat], alpha=alpha,
                    edgecolors="black", linewidths=0.3, zorder=3,
                    label=cat if i == 0 else None,
                )
        else:
            color = palette[i % len(palette)]
            sub_vals = vals.values
            jitter = rng.uniform(-jitter_width, jitter_width, size=len(sub_vals))
            ax.scatter(
                positions[i] + jitter, sub_vals,
                s=point_size ** 2, c=color, alpha=alpha,
                edgecolors="black", linewidths=0.3, zorder=3,
            )

        # Mean indicator
        if show_mean and len(vals) > 0:
            group_mean = vals.mean()
            ax.scatter(
                positions[i], group_mean,
                marker=mean_marker, s=150, c="black", linewidths=2, zorder=4,
            )

    # ── n= labels and formatting ─────────────────────────────────────
    tick_labels = [f"{g}\n(n={n})" for g, n in zip(groups, group_ns)]
    ax.set_xticks(positions)
    ax.set_xticklabels(tick_labels)

    if color_col is not None:
        ax.legend(loc="upper right", fontsize=7, frameon=False, handletextpad=0.3)

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
        save_path = "./results/jitter_plot"
    fig.savefig(f"{save_path}.svg", dpi=300, bbox_inches="tight")
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax


def plot_dotplot(
    df,
    group_col,
    value_col,
    color_col=None,
    figsize=(3.5, 3),
    title="",
    xlabel="",
    palette=None,
    point_size=8,
    order=None,
    save_path=None,
):
    """Plot a Cleveland dot plot for comparing values across groups.

    Displays each observation as a point on a horizontal line per group.
    Groups are arranged vertically and values extend horizontally, making
    it easy to compare individual measurements across categories.

    Parameters
    ----------
    df : pandas.DataFrame
        Long-format DataFrame containing the data.
    group_col : str
        Column name for the categorical grouping variable (y-axis).
    value_col : str
        Column name for the numeric measurement (x-axis).
    color_col : str or None, optional
        Column name for coloring points by a secondary variable,
        by default None.
    figsize : tuple of float, optional
        Figure dimensions in inches (width, height), by default (3.5, 3).
    title : str, optional
        Plot title, by default "".
    xlabel : str, optional
        X-axis label, by default "".
    palette : list of str or None, optional
        List of hex color strings. If None, uses Okabe-Ito palette.
    point_size : float, optional
        Size of data points, by default 8.
    order : list of str or None, optional
        Custom ordering of groups along the y-axis, by default None.
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.
        If None, saves to ./results/dotplot, by default None.

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
    positions = np.arange(n_groups)

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    if color_col is not None:
        color_categories = df[color_col].unique().tolist()
        color_map = {cat: palette[i % len(palette)] for i, cat in enumerate(color_categories)}

    # Draw horizontal reference lines and points
    for i, g in enumerate(groups):
        mask = df[group_col] == g
        ax.axhline(y=positions[i], color="#DDDDDD", linewidth=0.6, zorder=1)

        if color_col is not None:
            for cat in color_categories:
                sub_mask = mask & (df[color_col] == cat)
                sub_vals = df.loc[sub_mask, value_col].dropna().values
                if len(sub_vals) == 0:
                    continue
                ax.scatter(
                    sub_vals, np.full_like(sub_vals, positions[i]),
                    s=point_size ** 2, c=color_map[cat],
                    edgecolors="black", linewidths=0.3, zorder=3,
                    label=cat if i == 0 else None,
                )
        else:
            vals = df.loc[mask, value_col].dropna().values
            color = palette[i % len(palette)]
            ax.scatter(
                vals, np.full_like(vals, positions[i]),
                s=point_size ** 2, c=color,
                edgecolors="black", linewidths=0.3, zorder=3,
            )

    # ── Format ───────────────────────────────────────────────────────
    group_ns = [df.loc[df[group_col] == g, value_col].dropna().shape[0] for g in groups]
    tick_labels = [f"{g} (n={n})" for g, n in zip(groups, group_ns)]
    ax.set_yticks(positions)
    ax.set_yticklabels(tick_labels)

    if color_col is not None:
        ax.legend(loc="upper right", fontsize=7, frameon=False, handletextpad=0.3)

    ax.format(
        xlabel=xlabel,
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
        save_path = "./results/dotplot"
    fig.savefig(f"{save_path}.svg", dpi=300, bbox_inches="tight")
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax


def plot_grouped_bar(
    df,
    group_col,
    subgroup_col,
    value_col,
    figsize=(4, 3),
    title="",
    ylabel="",
    palette=None,
    error_type="sem",
    bar_width=0.35,
    dodge_width=0.0,
    capsize=3,
    order=None,
    subgroup_order=None,
    save_path=None,
):
    """Plot a grouped bar chart with error bars.

    Draws side-by-side bars grouped by a primary categorical variable and
    colored by a secondary categorical variable. Error bars show SEM or SD.
    The y-axis always starts at zero.

    Parameters
    ----------
    df : pandas.DataFrame
        Long-format DataFrame containing the data.
    group_col : str
        Column name for the primary categorical variable (x-axis groups).
    subgroup_col : str
        Column name for the secondary categorical variable (bar colors).
    value_col : str
        Column name for the numeric measurement.
    figsize : tuple of float, optional
        Figure dimensions in inches (width, height), by default (4, 3).
    title : str, optional
        Plot title, by default "".
    ylabel : str, optional
        Y-axis label, by default "".
    palette : list of str or None, optional
        List of hex color strings. If None, uses Okabe-Ito palette.
    error_type : str, optional
        Type of error bars: 'sem' or 'sd', by default 'sem'.
    bar_width : float, optional
        Width of each individual bar, by default 0.35.
    dodge_width : float, optional
        Additional spacing between bars within a group. Total offset per
        bar is bar_width + dodge_width, by default 0.0.
    capsize : float, optional
        Width of error bar caps in points, by default 3.
    order : list of str or None, optional
        Custom ordering of primary groups, by default None.
    subgroup_order : list of str or None, optional
        Custom ordering of subgroups (legend order), by default None.
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.
        If None, saves to ./results/grouped_bar, by default None.

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
    subgroups = subgroup_order if subgroup_order is not None else df[subgroup_col].unique().tolist()
    n_groups = len(groups)
    n_subgroups = len(subgroups)
    colors = [palette[i % len(palette)] for i in range(n_subgroups)]

    # Compute summary statistics
    summary = df.groupby([group_col, subgroup_col])[value_col].agg(["mean", "std", "count"]).reset_index()
    if error_type == "sem":
        summary["error"] = summary["std"] / np.sqrt(summary["count"])
    else:
        summary["error"] = summary["std"]

    # Compute bar positions: center each group at integer positions
    step = bar_width + dodge_width
    total_width = n_subgroups * step
    offsets = np.arange(n_subgroups) * step - (total_width - step) / 2
    group_positions = np.arange(n_groups)

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    for j, sg in enumerate(subgroups):
        sg_data = summary[summary[subgroup_col] == sg].set_index(group_col)
        means = [sg_data.loc[g, "mean"] if g in sg_data.index else 0 for g in groups]
        errors = [sg_data.loc[g, "error"] if g in sg_data.index else 0 for g in groups]
        x_pos = group_positions + offsets[j]

        ax.bar(
            x_pos, means,
            width=bar_width,
            color=colors[j],
            edgecolor="black",
            linewidth=0.8,
            alpha=0.7,
            label=sg,
            zorder=2,
        )
        ax.errorbar(
            x_pos, means, yerr=errors,
            fmt="none",
            ecolor="black",
            elinewidth=1.0,
            capsize=capsize,
            capthick=1.0,
            zorder=3,
        )

    # ── n= labels ────────────────────────────────────────────────────
    group_ns = [df.loc[df[group_col] == g, value_col].dropna().shape[0] for g in groups]
    tick_labels = [f"{g}\n(n={n})" for g, n in zip(groups, group_ns)]
    ax.set_xticks(group_positions)
    ax.set_xticklabels(tick_labels)

    # y-axis must start at 0 for bar charts
    ax.set_ylim(bottom=0)

    ax.legend(loc="upper right", fontsize=7, frameon=False, handletextpad=0.3)

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
        save_path = "./results/grouped_bar"
    fig.savefig(f"{save_path}.svg", dpi=300, bbox_inches="tight")
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax


def plot_grouped_box(
    df,
    group_col,
    subgroup_col,
    value_col,
    figsize=(4, 3),
    title="",
    ylabel="",
    palette=None,
    show_points=True,
    point_size=3,
    alpha=0.7,
    jitter_width=0.06,
    plot_type="box",
    box_width=0.35,
    dodge_width=0.0,
    orient="v",
    order=None,
    subgroup_order=None,
    save_path=None,
):
    """Plot grouped box or violin plots with optional data points.

    Draws side-by-side box or violin plots grouped by a primary categorical
    variable and colored by a secondary categorical variable. Individual
    data points can be overlaid.

    Parameters
    ----------
    df : pandas.DataFrame
        Long-format DataFrame containing the data.
    group_col : str
        Column name for the primary categorical variable (x-axis groups).
    subgroup_col : str
        Column name for the secondary categorical variable (colors).
    value_col : str
        Column name for the numeric measurement.
    figsize : tuple of float, optional
        Figure dimensions in inches (width, height), by default (4, 3).
    title : str, optional
        Plot title, by default "".
    ylabel : str, optional
        Y-axis label, by default "".
    palette : list of str or None, optional
        List of hex color strings. If None, uses Okabe-Ito palette.
    show_points : bool, optional
        Whether to overlay jittered individual data points, by default True.
    point_size : float, optional
        Size of individual data points, by default 3.
    alpha : float, optional
        Transparency for data points, by default 0.7.
    jitter_width : float, optional
        Horizontal spread of jittered points within each sub-box,
        by default 0.06.
    plot_type : str, optional
        Type of plot: 'box' or 'violin', by default 'box'.
    box_width : float, optional
        Width of each individual box or violin, by default 0.35.
    dodge_width : float, optional
        Additional spacing between boxes within a group, by default 0.0.
    orient : str, optional
        Orientation: 'v' (vertical) or 'h' (horizontal), by default 'v'.
    order : list of str or None, optional
        Custom ordering of primary groups, by default None.
    subgroup_order : list of str or None, optional
        Custom ordering of subgroups (legend order), by default None.
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.
        If None, saves to ./results/grouped_box, by default None.

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
    subgroups = subgroup_order if subgroup_order is not None else df[subgroup_col].unique().tolist()
    n_groups = len(groups)
    n_subgroups = len(subgroups)
    colors = [palette[i % len(palette)] for i in range(n_subgroups)]

    # Compute positions: center each group at integer positions
    step = box_width + dodge_width
    total_width = n_subgroups * step
    offsets = np.arange(n_subgroups) * step - (total_width - step) / 2
    group_positions = np.arange(n_groups)

    rng = np.random.default_rng(42)

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    # Track legend handles manually
    legend_handles = []

    for j, sg in enumerate(subgroups):
        sub_data = []
        sub_positions = []
        for i, g in enumerate(groups):
            mask = (df[group_col] == g) & (df[subgroup_col] == sg)
            vals = df.loc[mask, value_col].dropna().values
            sub_data.append(vals)
            sub_positions.append(group_positions[i] + offsets[j])

        if plot_type == "box":
            bp = ax.boxplot(
                sub_data,
                positions=sub_positions,
                widths=box_width * 0.8,
                patch_artist=True,
                showfliers=False,
                medianprops=dict(color="black", linewidth=1.2),
                whiskerprops=dict(color="black", linewidth=0.8),
                capprops=dict(color="black", linewidth=0.8),
                boxprops=dict(linewidth=0.8),
                vert=(orient == "v"),
            )
            for patch in bp["boxes"]:
                patch.set_facecolor(colors[j])
                patch.set_alpha(0.45)
                patch.set_edgecolor("black")
            # Use first box as legend handle
            legend_handles.append(mpl.patches.Patch(facecolor=colors[j], edgecolor="black", alpha=0.45, label=sg))

        elif plot_type == "violin":
            # Filter out empty arrays for violinplot
            valid_data = []
            valid_positions = []
            for d, p in zip(sub_data, sub_positions):
                if len(d) >= 2:
                    valid_data.append(d)
                    valid_positions.append(p)

            if len(valid_data) > 0:
                parts = ax.violinplot(
                    valid_data,
                    positions=valid_positions,
                    widths=box_width * 0.9,
                    showmeans=False,
                    showmedians=False,
                    showextrema=False,
                    vert=(orient == "v"),
                )
                for body in parts["bodies"]:
                    body.set_facecolor(colors[j])
                    body.set_edgecolor("black")
                    body.set_linewidth(0.8)
                    body.set_alpha(0.35)

                # Inner median + IQR
                for d, p in zip(valid_data, valid_positions):
                    q1, median, q3 = np.percentile(d, [25, 50, 75])
                    if orient == "v":
                        ax.vlines(p, q1, q3, color="black", linewidth=2, zorder=4)
                        ax.scatter(p, median, color="white", s=12, zorder=5, edgecolors="black", linewidths=0.5)
                    else:
                        ax.hlines(p, q1, q3, color="black", linewidth=2, zorder=4)
                        ax.scatter(median, p, color="white", s=12, zorder=5, edgecolors="black", linewidths=0.5)

            legend_handles.append(mpl.patches.Patch(facecolor=colors[j], edgecolor="black", alpha=0.35, label=sg))

        # Overlay jittered points
        if show_points:
            for k, (data, pos) in enumerate(zip(sub_data, sub_positions)):
                if len(data) == 0:
                    continue
                jitter = rng.uniform(-jitter_width, jitter_width, size=len(data))
                if orient == "v":
                    ax.scatter(
                        pos + jitter, data,
                        s=point_size ** 2, c=colors[j], alpha=alpha,
                        edgecolors="black", linewidths=0.3, zorder=5,
                    )
                else:
                    ax.scatter(
                        data, pos + jitter,
                        s=point_size ** 2, c=colors[j], alpha=alpha,
                        edgecolors="black", linewidths=0.3, zorder=5,
                    )

    # ── n= labels and formatting ─────────────────────────────────────
    group_ns = [df.loc[df[group_col] == g, value_col].dropna().shape[0] for g in groups]
    tick_labels = [f"{g}\n(n={n})" for g, n in zip(groups, group_ns)]

    if orient == "v":
        ax.set_xticks(group_positions)
        ax.set_xticklabels(tick_labels)
        format_kwargs = dict(ylabel=ylabel)
    else:
        ax.set_yticks(group_positions)
        ax.set_yticklabels(tick_labels)
        format_kwargs = dict(xlabel=ylabel)

    ax.legend(handles=legend_handles, loc="upper right", fontsize=7, frameon=False, handletextpad=0.3)

    ax.format(
        title=title,
        xlabelsize=9,
        ylabelsize=9,
        xticklabelsize=8,
        yticklabelsize=8,
        titlesize=9,
        titleweight="bold",
        **format_kwargs,
    )

    # ── Save ─────────────────────────────────────────────────────────
    if save_path is None:
        save_path = "./results/grouped_box"
    fig.savefig(f"{save_path}.svg", dpi=300, bbox_inches="tight")
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax
```

## Colormap Recommendations

| Data encoding | Colormap | Notes |
|---------------|----------|-------|
| Subgroups (up to 8) | Okabe-Ito palette | Colorblind-safe; assign by subgroup |
| Single group with gradient | Sequential from one Okabe-Ito hue | Useful for ordinal subgroups (e.g., time points) |

## Customization Notes

- **`plot_jitter`**: Best for small-to-moderate sample sizes where showing all individual points is informative. Use `color_col` when points belong to a secondary category. The `show_mean` horizontal line provides a quick visual reference without hiding the distribution.
- **`plot_dotplot`**: Cleveland dot plot — horizontal layout makes it easy to read exact values. Best for comparing a moderate number of items (5-20 groups). When groups have long labels, this layout avoids the angled-text problem of vertical bar charts.
- **`plot_grouped_bar`**: Side-by-side bars with error bars. The `n=` shown below each primary group is the total across all subgroups. Adjust `bar_width` based on the number of subgroups: 0.35 for 2 subgroups, 0.25 for 3, 0.2 for 4.
- **`plot_grouped_box`**: Side-by-side box or violin plots. Set `plot_type='violin'` for larger sample sizes (n >= 15 per subgroup). The `box_width` parameter controls individual box width; adjust alongside `dodge_width` if boxes overlap.
- **`dodge_width`**: Extra spacing between boxes/bars within a group. Default 0.0 places them adjacent. Increase to 0.05-0.1 for visual separation.
- **`order` / `subgroup_order`**: Control the arrangement of groups and subgroups. Essential for meaningful ordering (e.g., `['WT', 'Het', 'KO']` or `['Vehicle', 'Low', 'High']`).
- **Violin minimum n**: `plot_grouped_box` with `plot_type='violin'` requires at least 2 observations per subgroup to estimate density. Groups with fewer observations are silently skipped for the violin but still shown if `show_points=True`.
