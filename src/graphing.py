from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from src.artifact import Artifact

# Set plot size preemptively
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["figure.dpi"] = 125


def graph_slot_potential(
    slot_potential: pd.DataFrame,
    artifact_potentials: dict[str, pd.DataFrame],
    equipped_expected_power: float,
    title: str,
    max_artifacts_plotted: int,
):


    # Calculate min and 4-sigma max power (99.93rd percentile) (if truncating)
    min_power = slot_potential["power"].min()
    artifact_power_max = max([artifact_potential["power"].max() for artifact_potential in artifact_potentials.values()])
    # TODO Reevaluate if I want 4 sigma
    # slot_cumsum = slot_potential["probability"].cumsum()
    # slot_four_sigma = slot_potential["power"].loc[(slot_cumsum >= 0.9993).idxmax()]
    # max_power = max([artifact_power_max, slot_four_sigma, equipped_expected_power])
    max_power = max([artifact_power_max, slot_potential["power"].max(), equipped_expected_power])

    # Create percentile-based histogram for slot potential
    nbins = 250
    bin_size = (max_power - min_power) / nbins
    index = np.linspace(min_power + bin_size, max_power, num=nbins)
    slot_histogram = pd.Series(0, index=index)
    previous_bin = -np.Infinity
    for bin_top in index:
        slot_histogram.loc[bin_top] = slot_potential["probability"][
            (previous_bin < slot_potential["power"]) & (slot_potential["power"] <= bin_top)
        ].sum()
        previous_bin = bin_top
    slot_percentile = slot_histogram.cumsum()
    # Apply smoothing
    # slot_histogram = slot_histogram.rolling(window=15, min_periods=1).sum() / 15
    slot_histogram = slot_histogram.rolling(window=10, win_type="blackman", min_periods=1).sum()
    slot_histogram /= slot_histogram.sum()

    # Create axes
    fig, ax1 = plt.subplots()
    if title is not None:
        ax1.set_title(title)
    ax2 = ax1.twinx()
    ax3 = ax1.twiny()

    # Plot slot histogram
    # Select plot color
    plot_color = (179 / 255, 205 / 255, 227 / 255)
    plot_color_dark = _adjust_lightness(plot_color, 0.5)
    # Plot histogram outline and fill
    # ax1.plot(index + bin_size / 2, slot_histogram / bin_size, color=plot_color)
    fill = ax1.fill(
        index.tolist() + [index[0]],
        (slot_histogram / bin_size).to_list() + [0],
        color=plot_color,
        alpha=0.3,
    )
    # Plot percentile line
    ax2.plot(index, slot_percentile, color=plot_color_dark, label="Percentile")

    # Draw vertical expection line
    ax2.plot([equipped_expected_power, equipped_expected_power], [0, 1.02], "r-")

    # Cull artifact list to only the top `max_artifacts_plotted`
    artifact_medians: dict[Artifact, float] = {}
    for artifact_name, artifact_potential in artifact_potentials.items():
        artifact_cumsum = artifact_potential["probability"].cumsum()
        artifact_medians[artifact_name] = artifact_potential["power"].loc[(artifact_cumsum >= 0.5).idxmax()]
    artifact_medians = dict(sorted(artifact_medians.items(), key=lambda item: item[1], reverse=True))
    for ind, artifact in enumerate(list(artifact_medians.keys())):
        if ind >= max_artifacts_plotted:
            artifact_medians.pop(artifact)

    # Plot artifacts
    x_location = []
    y_location = []
    x_1std = []
    x_2std = []
    x_3std = []
    x_extremes = []
    for artifact_name in artifact_medians.keys():
        artifact_potential = artifact_potentials[artifact_name]
        artifact_cumsum = artifact_potential["probability"].cumsum()
        artifact_median = artifact_potential["power"].loc[(artifact_cumsum >= 0.5).idxmax()]
        x_location.append(artifact_median)
        y_location.append(slot_percentile[index[index >= artifact_median][0]])
        x_1std.append(
            [
                -(artifact_potential["power"].loc[(artifact_cumsum >= 0.317).idxmax()] - artifact_median),
                artifact_potential["power"].loc[(artifact_cumsum >= 1 - 0.317).idxmax()] - artifact_median,
            ]
        )
        x_2std.append(
            [
                -(artifact_potential["power"].loc[(artifact_cumsum >= 0.0455).idxmax()] - artifact_median),
                artifact_potential["power"].loc[(artifact_cumsum >= 1 - 0.0455).idxmax()] - artifact_median,
            ]
        )
        x_3std.append(
            [
                -(artifact_potential["power"].loc[(artifact_cumsum >= 0.00267).idxmax()] - artifact_median),
                artifact_potential["power"].loc[(artifact_cumsum >= 1 - 0.00267).idxmax()] - artifact_median,
            ]
        )
        x_extremes.append(
            [
                -(artifact_potential["power"].min() - artifact_median),
                artifact_potential["power"].max() - artifact_median,
            ]
        )

    # Transpose
    x_1std = np.array(x_1std).transpose()
    x_2std = np.array(x_2std).transpose()
    x_3std = np.array(x_3std).transpose()
    x_extremes = np.array(x_extremes).transpose()

    # Plot error bars
    ax2.errorbar(x=x_location, y=y_location, xerr=x_1std, fmt="ok", lw=2, capsize=5)
    ax2.errorbar(x=x_location, y=y_location, xerr=x_2std, fmt=".k", lw=1.5, capsize=5)
    # ax2.errorbar(x=x_location, y=y_location, xerr=x_3std, fmt=".k", lw=1, capsize=5)
    ax2.errorbar(x=x_location, y=y_location, xerr=x_extremes, fmt=".k", lw=0.5, capsize=5)

    # # Plot labels
    # plot_range = ax2.get_xlim()[1] - ax2.get_xlim()[0]
    # mid_point = ax2.get_xlim()[0] + plot_range / 2
    # y_last = 1
    # for ind, artifact_potential in reversed(list(enumerate(artifact_potentials_grouped))):
    #     percentile = (
    #         100
    #         * slot_potential.potential_df[slot_potential.potential_df["power"] <= x_location[ind]][
    #             "probability"
    #         ].sum()
    #     )
    #     delta_power = 100 * (x_location[ind] / ax2.get_xlim()[0] - 1)
    #     label_x_location = x_location[ind]
    #     label_y_location = min(y_last - 0.075, y_location[ind] - 0.06)
    #     y_last = label_y_location
    #     horizontal_allignment = "right" if x_location[ind] >= mid_point else "left"
    #     ax2.annotate(
    #         f"{artifact_potential.name}: ({percentile:.1f}% / {delta_power:+.1f}%)",
    #         (label_x_location, label_y_location),
    #         horizontalalignment=horizontal_allignment,
    #         bbox=dict(facecolor="white", alpha=0.5),
    #     )
    #     ax2.plot(
    #         [label_x_location, label_x_location], [y_location[ind], label_y_location + 0.05], "k--", linewidth=1
    #     )

    # Set axes properties
    ax1.set_xlabel("Power")
    ax1.set_ylabel("Probability Distribution Function")
    ax1.set_xlim(min_power, max_power)
    ax1.set_ylim(0, slot_histogram.max() / bin_size)
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax1.minorticks_on()

    ax2.set_ylabel("Cumulative Distribution Function")
    ax2.set_xlim(ax1.get_xlim())
    ax2.set_ylim(0, 1.02)
    ax2.set_yticks(np.arange(0, 1.1, 0.1))
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax2.minorticks_on()
    ax2.grid(axis="both")

    ax3.set_xlim((0, 100 * (max_power / min_power - 1)))
    ax3.xaxis.set_major_formatter(lambda x, pos=None: f"+{x:.0f}%")
    ax3.xaxis.set_major_locator(mtick.MultipleLocator(5))
    ax3.xaxis.set_minor_locator(mtick.MultipleLocator(1))


def _adjust_lightness(color, amount=0.5):
    import colorsys

    import matplotlib.colors as mc

    try:
        c = mc.cnames[color]
    except:
        c = color
    c = colorsys.rgb_to_hls(*mc.to_rgb(c))
    return colorsys.hls_to_rgb(c[0], max(0, min(1, amount * c[1])), c[2])
