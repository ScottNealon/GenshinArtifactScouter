from __future__ import annotations

import itertools
import logging
import math
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from .potential import ArtifactPotential, SlotPotential

log = logging.getLogger(__name__)

# Source: https://colorbrewer2.org/#type=qualitative&scheme=Pastel1&n=5
plot_colors = [
    (179 / 255, 205 / 255, 227 / 255),
    (204 / 255, 235 / 255, 197 / 255),
    (254 / 255, 217 / 255, 166 / 255),
    (222 / 255, 203 / 255, 228 / 255),
    (251 / 255, 180 / 255, 174 / 255),
]
# plot_colors = [(127/255, 201/255, 127/255), (190/255, 174/255, 212/255), (253/255, 192/255, 134/255), (255/255, 255/255, 153/255), (56/255, 108/255, 176/255)]


def graph_slot_potentials(
    slot_potentials: list[SlotPotential],
    legend_labels: list[str] = [],
    base_power: float = None,
    title: str = None,
    nbins: int = None,
    smooth: bool = True,
):

    # Calculate number of bins
    if nbins is None:
        biggest_df = max([slot_potential.potential_df.size for slot_potential in slot_potentials])
        nbins = min(250, biggest_df / 100)

    # Prepare histogram
    min_power = min([slot_potential.potential_df["power"].min() for slot_potential in slot_potentials])
    max_power = max([slot_potential.potential_df["power"].max() for slot_potential in slot_potentials])
    bin_size = (max_power - min_power) / nbins
    bins = pd.DataFrame(
        [
            (min_power + bin * bin_size, min_power + (bin + 1) * bin_size, min_power + (bin + 0.5) * bin_size)
            for bin in range(nbins)
        ],
        columns=["bin bottom", "bin top", "bin mid"],
    )

    # Fill histogram
    for (input_ind, slot_potential) in enumerate(slot_potentials):
        bins[f"pop_{input_ind}"] = np.nan
        for bin_ind, bin in bins.iterrows():
            bins[f"pop_{input_ind}"][bin_ind] = slot_potential.potential_df[
                (slot_potential.potential_df["power"] >= bin["bin bottom"])
                & (slot_potential.potential_df["power"] < bin["bin top"])
            ]["probability"].sum()
        # Calculate percentiles
        bins[f"per_{input_ind}"] = bins[f"pop_{input_ind}"].cumsum()
        # Apply smoothing after percentiles
        if smooth:
            smoothing_period = math.floor(nbins / 30)
            bins[f"pop_{input_ind}"] = (
                bins[f"pop_{input_ind}"].rolling(window=smoothing_period, min_periods=1).sum() / smoothing_period
            )

    # Create axes
    fig, ax1 = plt.subplots()
    if title is not None:
        ax1.set_title(title)
    ax2 = ax1.twinx()
    ax3 = ax1.twiny()

    # Prepare color iterable
    plot_color_iter = itertools.cycle(plot_colors)

    fills = []
    for ind in range(len(slot_potentials)):
        # Select plot color
        plot_color = next(plot_color_iter)
        plot_color_dark = _adjust_lightness(plot_color, 0.5)
        # Plot histogram
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
            (slot_potential.potential_df[slot_potential.potential_df["power"] < base_power]["probability"].sum(), ind)
            for (slot_potential, ind) in zip(slot_potentials, list(range(len(slot_potentials))))
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
            if ind < len(legend_labels):
                label = legend_labels[ind]
                delta_power = base_power / slot_potentials[ind].potential_df["power"].min() - 1
                if percentile < 0.15:
                    y_location = percentile + 0.05
                    max_height = y_location
                else:
                    y_location = min(max_height - 0.0375, percentile - 0.05)
                    max_height = y_location
                # Plot labels
                ax2.annotate(
                    f"{label}: ({100*percentile:.1f}% / {100*delta_power:+.1f}%)",
                    (next(x_location), y_location),
                    horizontalalignment=next(horizontal_allignment),
                    bbox=dict(facecolor="white", alpha=0.5),
                )

    # Legend
    fills = [fill[0] for fill in fills]
    if len(fills) == len(legend_labels):
        ax3.legend(handles=fills, labels=legend_labels, loc="lower right", framealpha=0.9)

    ax1.set_xlabel("Power")
    ax1.set_ylabel("Probability")
    ax1.set_xlim(min_power, max_power)
    # Ignore first bin in setting ymax. If things are smoothed, this is generally ignored but that's OK.
    y_max = max([bins[f"pop_{ind}"].loc[1:].max() for ind in range(len(slot_potentials))])
    ax1.set_ylim(0, y_max)

    ax2.set_xlim(ax1.get_xlim())
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

    return fig, ax1, ax2, ax3, bins


def graph_artifact_potentials(
    artifact_potentials: list[ArtifactPotential],
    artifact_labels: list(str),
    base_power: float = None,
    nbins: int = None,
    smooth: bool = True,
):

    # Ensure all artifact potentials share the same slot potential
    # slot_potential = artifact_potentials[0].slot_potential
    # for artifact_potential in artifact_potentials:
    #     if slot_potential != artifact_potential.slot_potential:
    #         raise ValueError("Artifact potentials have different slot potentials. You are comparing apples to oranges.")

    # Group artifact potentials by slot potentials
    slot_potential_groups = dict[object, list]()
    for artifact_potential in artifact_potentials:
        if artifact_potential.slot_potential not in slot_potential_groups:
            slot_potential_groups[artifact_potential.slot_potential] = []
        slot_potential_groups[artifact_potential.slot_potential].append(artifact_potential)

    # Iterate through slot_potential_groups
    for slot_potential, artifact_potentials_grouped in slot_potential_groups.items():

        if slot_potential == None:
            log.warn("No slot potential found for artifacts. Plotting skipped.")
            continue

        # Plot slot potential and extract axes
        title = f"{slot_potential.stars}* {slot_potential.set.title()} {slot_potential.main_stat} {slot_potential.slot.__name__} Artifact Potentials on {slot_potential.character.name.title()}"
        fig, ax1, ax2, ax3, bins = graph_slot_potentials(
            slot_potentials=[slot_potential],
            legend_labels=[],
            title=title,
            base_power=base_power,
            nbins=nbins,
            smooth=smooth,
        )

        # Sort artifacts by average power, and also sort artifact labels
        # artifact_potentials_grouped.sort(key=lambda x: x.potential_df["power"].dot(x.potential_df["probability"]).sum())
        zipped_lists = zip(artifact_labels, artifact_potentials_grouped)
        sorted_pairs = sorted(
            zipped_lists, key=lambda x: x[1].potential_df["power"].dot(x[1].potential_df["probability"]).sum()
        )
        tuples = zip(*sorted_pairs)
        artifact_labels, artifact_potentials_grouped = [list(x) for x in tuples]

        # Determine statistics
        x_location = []
        y_location = []
        x_1std = []
        x_2std = []
        x_3std = []
        x_extremes = []
        for artifact_potential in artifact_potentials_grouped:
            potential_df = artifact_potential.potential_df.sort_values("power")
            cumsum = potential_df["probability"].cumsum()
            median = potential_df["power"].loc[(cumsum >= 0.5).idxmax()]
            x_location.append(median)
            y_location.append(bins.loc[(bins["bin bottom"] > median).idxmax()]["per_0"])
            x_1std.append(
                [
                    -(potential_df["power"].loc[(cumsum >= 0.317).idxmax()] - median),
                    potential_df["power"].loc[(cumsum >= 1 - 0.317).idxmax()] - median,
                ]
            )
            x_2std.append(
                [
                    -(potential_df["power"].loc[(cumsum >= 0.0455).idxmax()] - median),
                    potential_df["power"].loc[(cumsum >= 1 - 0.0455).idxmax()] - median,
                ]
            )
            x_3std.append(
                [
                    -(potential_df["power"].loc[(cumsum >= 0.00267).idxmax()] - median),
                    potential_df["power"].loc[(cumsum >= 1 - 0.00267).idxmax()] - median,
                ]
            )
            x_extremes.append([-(potential_df["power"].min() - median), potential_df["power"].max() - median])

        # Transpose
        x_1std = np.array(x_1std).transpose()
        x_2std = np.array(x_2std).transpose()
        x_3std = np.array(x_3std).transpose()
        x_extremes = np.array(x_extremes).transpose()

        # Plot error bars
        ax2.errorbar(x=x_location, y=y_location, xerr=x_1std, fmt="ok", lw=2, capsize=5)
        ax2.errorbar(x=x_location, y=y_location, xerr=x_2std, fmt=".k", lw=1.5, capsize=5)
        ax2.errorbar(x=x_location, y=y_location, xerr=x_3std, fmt=".k", lw=1, capsize=5)
        ax2.errorbar(x=x_location, y=y_location, xerr=x_extremes, fmt=".k", lw=0.5, capsize=5)

        # Plot labels
        plot_range = ax2.get_xlim()[1] - ax2.get_xlim()[0]
        mid_point = ax2.get_xlim()[0] + plot_range / 2
        y_last = 1
        for ind, artifact_potential in reversed(list(enumerate(artifact_potentials_grouped))):
            percentile = (
                100
                * slot_potential.potential_df[slot_potential.potential_df["power"] <= x_location[ind]][
                    "probability"
                ].sum()
            )
            delta_power = 100 * (x_location[ind] / ax2.get_xlim()[0] - 1)
            label_x_location = x_location[ind]
            label_y_location = min(y_last - 0.075, y_location[ind] - 0.06)
            y_last = label_y_location
            horizontal_allignment = "right" if x_location[ind] >= mid_point else "left"
            ax2.annotate(
                f"{artifact_labels[ind]}: ({percentile:.1f}% / {delta_power:+.1f}%)",
                (label_x_location, label_y_location),
                horizontalalignment=horizontal_allignment,
                bbox=dict(facecolor="white", alpha=0.5),
            )
            ax2.plot(
                [label_x_location, label_x_location], [y_location[ind], label_y_location + 0.05], "k--", linewidth=1
            )

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
