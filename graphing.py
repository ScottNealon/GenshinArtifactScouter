import itertools
import logging
import math

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd


def graph_potentials(
    artifact_potentials_dfs: list[pd.DataFrame],
    legend_labels: list[str],
    base_power: float = None,
    title: str = None,
    nbins: int = None,
    smooth: bool = False,
):

    log.info("-" * 120)
    log.info(f"Plotting {title}...")

    # Calculate number of bins
    if nbins is None:
        biggest_df = max([artifact_potentials_df.size for artifact_potentials_df in artifact_potentials_dfs])
        nbins = min(250, biggest_df / 100)

    # Prepare histogram
    min_power = min([artifact_potentials_df["power"].min() for artifact_potentials_df in artifact_potentials_dfs])
    max_power = max([artifact_potentials_df["power"].max() for artifact_potentials_df in artifact_potentials_dfs])
    bin_size = (max_power - min_power) / nbins
    bins = pd.DataFrame(
        [
            (min_power + bin * bin_size, min_power + (bin + 1) * bin_size, min_power + (bin + 0.5) * bin_size)
            for bin in range(nbins)
        ],
        columns=["bin bottom", "bin top", "bin mid"],
    )

    # Fill histogram
    for (input_ind, artifact_potentials_df) in enumerate(artifact_potentials_dfs):
        bins[f"pop_{input_ind}"] = np.nan
        for bin_ind, bin in bins.iterrows():
            bins[f"pop_{input_ind}"][bin_ind] = artifact_potentials_df[
                (artifact_potentials_df["power"] >= bin["bin bottom"])
                & (artifact_potentials_df["power"] < bin["bin top"])
            ]["probability"].sum()
        # Calculate percentiles
        bins[f"per_{input_ind}"] = bins[f"pop_{input_ind}"].cumsum()
        # Apply smoothing after percentiles
        if smooth:
            smoothing_period = math.floor(nbins / 50)
            bins[f"pop_{input_ind}"] = (
                bins[f"pop_{input_ind}"].rolling(window=smoothing_period, min_periods=1).sum() / smoothing_period
            )

    # Create axes
    fig, ax1 = plt.subplots()
    ax1.set_title(title)
    ax2 = ax1.twinx()
    ax3 = ax1.twiny()

    # Source: https://colorbrewer2.org/#type=qualitative&scheme=Pastel1&n=5
    plot_colors = [
        (179 / 255, 205 / 255, 227 / 255),
        (204 / 255, 235 / 255, 197 / 255),
        (254 / 255, 217 / 255, 166 / 255),
        (222 / 255, 203 / 255, 228 / 255),
        (251 / 255, 180 / 255, 174 / 255),
    ]
    # plot_colors = [(127/255, 201/255, 127/255), (190/255, 174/255, 212/255), (253/255, 192/255, 134/255), (255/255, 255/255, 153/255), (56/255, 108/255, 176/255)]

    plot_color_iter = itertools.cycle(plot_colors)

    fills = []
    for ind in range(len(artifact_potentials_dfs)):
        # Select plot color
        plot_color = next(plot_color_iter)
        plot_color_dark = _adjust_lightness(plot_color, 0.5)
        # Plot histogram
        # ax1.bar(x=bins['bin bottom'], height=bins[f'pop_{ind}'], width=bin_size, color=plot_color_w_alpha)
        # Plot fill with thick border
        ax1.plot(bins["bin mid"], bins[f"pop_{ind}"], color=plot_color)
        fill = ax1.fill(
            bins["bin mid"].tolist() + [bins["bin mid"].loc[0]],
            bins[f"pop_{ind}"].to_list() + [0],
            color=plot_color,
            alpha=0.3,
        )
        fills.append(fill)
        # Plot percentile line
        ax2.plot(bins["bin mid"], bins[f"per_{ind}"], color=plot_color_dark)

    # Draw base power comparisons
    if base_power is not None:
        ax2.plot([base_power, base_power], [0, 1], "r-")
        percentiles = [
            (artifact_potentials_df[artifact_potentials_df["power"] < base_power]["probability"].sum(), ind)
            for (artifact_potentials_df, ind) in zip(artifact_potentials_dfs, list(range(len(artifact_potentials_dfs))))
        ]
        percentiles = sorted(percentiles, key=lambda x: x[0], reverse=True)
        ax2.scatter([base_power] * len(percentiles), [percentile for (percentile, _) in percentiles], c="k")
        # Determine positions of labels. If far enough fro right hand side, alternate between left and right.
        if (base_power - min_power) / (max_power - min_power) < 0.85:
            x_location = itertools.cycle(
                [base_power - (max_power - min_power) * 0.02, base_power + (max_power - min_power) * 0.02]
            )
            horizontal_allignment = itertools.cycle(["right", "left"])
        else:
            x_location = itertools.cycle([base_power - (max_power - min_power) * 0.02])
            horizontal_allignment = itertools.cycle(["left"])
        max_height = 1
        for (percentile, ind) in percentiles:
            label = legend_labels[ind]
            delta_power = base_power / artifact_potentials_dfs[ind]["power"].min() - 1
            if percentile < 0.15:
                y_location = percentile + 0.05
                max_height = y_location
            else:
                y_location = min(max_height - 0.0375, percentile - 0.05)
                max_height = y_location
            # Plot labels
            ax2.annotate(
                f" {label}: ({100*percentile:.1f}% / {100*delta_power:+.1f}%)",
                (next(x_location), y_location),
                horizontalalignment=next(horizontal_allignment),
                bbox=dict(facecolor="white", alpha=0.5),
            )

    # Legend
    fills = [fill[0] for fill in fills]
    ax3.legend(handles=fills, labels=legend_labels, loc="upper left", framealpha=0.9)

    ax1.set_xlabel("Power")
    ax1.set_ylabel("Probability")
    ax1.set_xlim(min_power, max_power)
    # Ignore first bin in setting ymax. If things are smoothed, this is generally ignored but that's OK.
    y_max = max([bins[f"pop_{ind}"].loc[1:].max() for ind in range(len(artifact_potentials_dfs))])
    ax1.set_ylim(0, y_max)

    ax2.set_ylabel("Power Percentile")
    ax2.set_ylim(0, 1)
    ax2.set_yticks(np.arange(0, 1.1, 0.1))
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax2.grid(axis="both")

    num_x_ticks = math.floor((max_power - min_power) / min_power / 0.05) + 1
    x_tick_locations = min_power + 0.05 * min_power * np.array(list(range(num_x_ticks)))
    ax3.set_xlabel("ΔPower")
    ax3.set_xlim(ax1.get_xlim())
    ax3.set_xticks(x_tick_locations)
    ax3.set_xticklabels([f"{5*num}%" for num in range(num_x_ticks)])

    plt.subplots_adjust(top=0.85)
    plt.subplots_adjust(right=0.85)

    plt.draw()
    plt.pause(0.001)


def _adjust_lightness(color, amount=0.5):
    import colorsys

    import matplotlib.colors as mc

    try:
        c = mc.cnames[color]
    except:
        c = color
    c = colorsys.rgb_to_hls(*mc.to_rgb(c))
    return colorsys.hls_to_rgb(c[0], max(0, min(1, amount * c[1])), c[2])
