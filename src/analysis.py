from __future__ import annotations

import decimal
import logging
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src import GOOD_database, artifact, genshin_data, graphing, list_mapper, potential, power_calculator

log = logging.getLogger(__name__)


def evaluate_character(
    database: GOOD_database.GenshinOpenObjectDescriptionDatabase,
    character_key: str,
    slots: list[type] = [artifact.Flower, artifact.Plume, artifact.Sands, artifact.Goblet, artifact.Circlet],
    log_to_file: bool = True,
    plot: bool = True,
    max_artifacts_plotted: int = 10,
):

    # Update module level logger
    if log_to_file:
        # Create output folder if it doesn't exist
        Path(f"./logs").mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(filename=f"./logs/{character_key}.log", mode="w", encoding="utf8")
        log.addHandler(file_handler)
    log.info("-" * 140)
    log.info(f"EVALUATING ARTIFACT POTENTIALS")
    log.info("")

    # Retrieve character from GO database
    character = database.get_character(character_key)

    # Retrieve equipped and potential artifacts from GO database
    equipped_artifacts = database.equipped_artifacts[character]
    alternative_artifacts = database.get_alternative_artifacts(equipped_artifacts)
    # Remove alternative artifacts from slots not being evaluated
    for slot in list(alternative_artifacts.keys()):
        if slot not in slots:
            alternative_artifacts.pop(slot)

    # Log character settings
    log.info(f"CHARACTER: {character.name}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
    log.info(
        f"WEAPON: {character.weapon.name}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}"
    )
    if character.amplifying_reaction is not None:
        log.info(
            f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)"
        )
    log.info("EQUIPPED ARTIFACTS:")
    log.info(
        f" NAME    SLOT STARS         SET LEVEL               MAIN STAT   HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
    )
    for artifact in equipped_artifacts:
        log.info(artifact.to_string_table())
    log.info("")

    # Log character stats
    log.info(f"{character.name.upper()} CURRENT STATS:")
    useful_stats = potential.find_useful_stats(character, equipped_artifacts)
    current_stats = power_calculator.evaluate_stats(character=character, artifacts=equipped_artifacts)
    current_power = power_calculator.evaluate_power(
        character=character, artifacts=equipped_artifacts, stats=current_stats
    )
    human_readable_current_stats = current_stats[useful_stats].rename(genshin_data.stat2output_map)
    log.info(f"CURRENT POWER: {current_power:>7,.0f}")
    log.info(human_readable_current_stats.to_frame().T.to_string(index=False))
    log.info("")
    # Log character future stats
    leveled_stats = power_calculator.evaluate_stats(character=character, artifacts=equipped_artifacts, leveled=True)
    leveled_power = power_calculator.evaluate_power(
        character=character, artifacts=equipped_artifacts, stats=leveled_stats
    )
    if leveled_power > current_power:
        power_delta = 100 * (leveled_power / current_power - 1)
        human_readable_leveled_stats = leveled_stats[useful_stats].rename(genshin_data.stat2output_map)
        log.info(f"{character.name.upper()} LEVELED STATS:")
        log.info(f"LEVELED POWER: {leveled_power:>7,.0f} | {power_delta:>+5.1f}%")
        log.info(human_readable_leveled_stats.to_frame().T.to_string(index=False))
        log.info("")
    log.info("(Stats not shown above do not affect character power and are suppressed in artifact evaluation.)")
    log.info("")

    # Calculate expect damge boost from substat roll
    log.info("DAMAGE INCREASE OF MAX SUBSTAT ROLL WITH LEVELED ARTIFACTS")
    valuable_substats = [
        substat_name for substat_name in genshin_data.substat_roll_values.keys() if substat_name in useful_stats
    ]
    substat_values: dict[str, float] = {}
    for substat_name in valuable_substats:
        substat_stats_increase = {substat_name: genshin_data.substat_roll_values[substat_name][5][-1]}  # Assume 5-star
        substat_stats = power_calculator.evaluate_stats(
            character=character, artifacts=equipped_artifacts, leveled=True, bonus_stats=substat_stats_increase
        )
        substat_power = power_calculator.evaluate_power(
            character=character, artifacts=equipped_artifacts, stats=substat_stats
        )
        substat_power_delta = 100 * (substat_power / leveled_power - 1)
        substat_values[substat_name] = substat_power_delta
    log.info(
        pd.Series(substat_values)
        .rename(genshin_data.stat2output_map)
        .to_frame()
        .T.to_string(float_format="{:+.2}%".format, index=False)
    )
    log.info("")

    # Log number of artifacts
    log.info("Number of alternative artifacts:")
    for slot, artifacts in alternative_artifacts.items():
        log.info(f"{slot.__name__:>7s}: {len(artifacts)}")
    log.info("")

    # Iterate through slots
    slot_potentials: dict[type, pd.DataFrame] = {}
    slot_cumsums: dict[type, pd.Series] = {}
    artifact_potentials: dict[type, dict[artifact.Artifact, pd.DataFrame]] = {slot: {} for slot in slots}
    artifact_cumsums: dict[type, dict[artifact.Artifact, pd.Series]] = {slot: {} for slot in slots}
    artifact_powers: dict[type, dict[artifact.Artifact, float]] = {slot: {} for slot in slots}
    artifact_percentiles: dict[type, dict[artifact.Artifact, float]] = {slot: {} for slot in slots}
    artifact_scores: dict[type, dict[artifact.Artifact, float]] = {slot: {} for slot in slots}
    equipped_potentials: dict[type, pd.DataFrame] = {}
    equipped_cumsums: dict[type, pd.Series] = {}
    equipped_median_power: dict[type, float] = {}
    for slot in slots:

        log.info("-" * 140)
        log.info(f"EVALUATING {slot.__name__.upper()} SLOT POTENTIAL...")

        # Get equipped artifact
        equipped_artifact = equipped_artifacts.get_artifact(slot=slot)
        if equipped_artifact is None:
            log.info(f"No {slot.__name__} equipped on {character.name}.")
            log.info("")
            continue
        log.info(f"    Stars: {equipped_artifact.stars:>d}*")
        set_str_long = re.sub(r"(\w)([A-Z])", r"\1 \2", equipped_artifact.set)  # Add spaces between capitals
        log.info(f"      Set: {set_str_long}")
        log.info(f"Main Stat: {genshin_data.stat2output_map[equipped_artifact.main_stat]}")

        # Evaluate slot potential
        if equipped_artifact.set in genshin_data.dropped_from_world_boss:
            source = "world boss"
        else:
            source = "domain"
        slot_potential_df = potential.individual_potential(
            character=character,
            equipped_artifacts=equipped_artifacts,
            artifact=equipped_artifact,
            source=source,
            ignore_substats=True,
        )
        # Calculate cumsum
        slot_cumsum = slot_potential_df["probability"].cumsum()
        slot_cumsum.index = slot_potential_df["power"]
        # Save potential and cumsum
        slot_potentials[slot] = slot_potential_df
        slot_cumsums[slot] = slot_cumsum
        # Log results
        log_slot_power(slot_cumsum=slot_cumsums[slot], leveled_power=leveled_power)
        log.info("")

        # Evaluate artifact potential
        # Start with the equipped artifact and then iterate through other artifacts, sorted numerically
        log.info(f"EVALUATING ALTERNATIVE {slot.__name__.upper()} SLOT POTENTIAL...")
        log.info("!!! CURRENTLY EQUIPPED ARTIFACT !!!")
        equipped_artifact = equipped_artifacts.get_artifact(slot)
        other_artifacts = [artifact for artifact in alternative_artifacts[slot] if artifact is not equipped_artifact]
        other_artifacts.sort(key=lambda artifact: int(artifact.index))
        alternative_artifacts_slot = [equipped_artifact] + other_artifacts
        for alternative_artifact in alternative_artifacts_slot:
            # Log artifact
            log.info(
                f" NAME    SLOT STARS         SET LEVEL               MAIN STAT   HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
            )
            log.info(alternative_artifact.to_string_table())
            # Calculate potential
            artifact_potential_df = potential.individual_potential(
                character=character,
                equipped_artifacts=equipped_artifacts,
                artifact=alternative_artifact,
                source=source,
            )
            # Save potential
            artifact_potentials[slot][alternative_artifact] = artifact_potential_df
            # Save median power
            artifact_cumsum = artifact_potential_df["probability"].cumsum()
            artifact_cumsum.index = artifact_potential_df["power"]
            artifact_powers[slot][alternative_artifact] = artifact_cumsum.index[artifact_cumsum >= 0.5][0]
            # Save median equipped power
            if slot not in equipped_median_power:
                equipped_median_power[slot] = artifact_powers[slot][alternative_artifact]
                equipped_potentials[slot] = artifact_potential_df
                equipped_cumsums[slot] = artifact_cumsum
            # Log results (and calculate score)
            percentile, score, beat_equipped_chance = log_artifact_power(
                slot_cumsum=slot_cumsums[slot],
                artifact_potential_df=artifact_potential_df,
                artifact_cumsum=artifact_cumsum,
                equipped_median_power=equipped_median_power[slot],
                equipped_cumsum=equipped_cumsums[slot],
                artifact=alternative_artifact,
            )
            # Save excpected percentile
            artifact_percentiles[slot][alternative_artifact] = percentile
            # Save median score
            artifact_scores[slot][alternative_artifact] = (score, beat_equipped_chance)
            log.info("")

    # POST CALCULATION SUMMARY

    # Summarize each slot in a leaderboard
    log.info("-" * 140)
    log.info(f"SLOT SCOREBOARDS...")
    log.info("")
    for slot in slots:
        equipped_artifact = equipped_artifacts.get_artifact(slot=slot)
        set_str_long = re.sub(r"(\w)([A-Z])", r"\1 \2", equipped_artifact.set)
        log.info(f"{equipped_artifact.stars}* {equipped_artifact.main_stat} {slot.__name__} Scoreboard")
        # Calculate space required for percentile
        max_percentile = max(
            [percentile for percentile in artifact_percentiles[slot].values() if percentile != 100] + [3]
        )
        decimal.getcontext().prec = 2
        max_percentile_spaces = len(_high_percentile_to_string(max_percentile))
        percentile_left_spaces = max([0, 10 - max_percentile_spaces])
        # Calculate space required for score
        artifact_scores_sorted = dict(sorted(artifact_scores[slot].items(), key=lambda item: item[1], reverse=True))
        max_score = max([max([score for _, (score, _) in artifact_scores_sorted.items()]), 6])
        max_score_spaces = max(len(f"{max_score:>,.1f}"), 5)
        header_str = (
            f"RANK   NAME    SLOT STARS         SET LEVEL               MAIN STAT   HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
            " |"
            "  ΔPower"
            f"  {f'Percentile'.rjust(max_percentile_spaces)}"
            f"  {'Score'.rjust(max_score_spaces)}"
            "  Chance of Beating Equipped"
        )
        ind = 1
        artifact_powers_sorted = dict(sorted(artifact_powers[slot].items(), key=lambda item: item[1], reverse=True))
        for artifact in artifact_powers_sorted.keys():
            if ind % 10 == 1:
                log.info(header_str)
            log.info(
                f"{ind:>3.0f})  "
                f"{artifact.to_string_table()}"
                " |"
                f"{100 * (artifact_powers[slot][artifact] / slot_potentials[slot]['power'].min() - 1):>+7.1f}%"
                f"  {(' ' * percentile_left_spaces) + f'{_high_percentile_to_string(artifact_percentiles[slot][artifact])}'.ljust(max_percentile_spaces)}"
                f"  {f'{artifact_scores_sorted[artifact][0]:>,.1f}'.rjust(max_score_spaces)}"
                f"  {'EQUIPPED' if artifact is equipped_artifact else _unbounded_percentile_to_string(artifact_scores_sorted[artifact][1])}"
            )
            ind += 1
        log.info("")

    # Plot each slot
    if plot:
        for slot in slots:
            equipped_artifact = equipped_artifacts.get_artifact(slot=slot)
            title = f"Slot and Artifact Potentials for Top {min(len(artifact_potentials[slot]), 10)} {equipped_artifact.stars}* {equipped_artifact._main_stat} {slot.__name__}"
            if title[-1] != "s" and len(artifact_potentials[slot]) > 1:
                title += "s"
            graphing.graph_slot_potential(
                slot_potential=slot_potentials[slot],
                artifact_potentials=artifact_potentials[slot],
                equipped_median_power=equipped_median_power[slot],
                title=title,
                max_artifacts_plotted=max_artifacts_plotted,
            )
        plt.show()

    # Remove file handler from logger
    if log_to_file:
        log.removeHandler(file_handler)


def log_slot_power(slot_cumsum: pd.Series, leveled_power: float):
    """Logs slot potential to console"""
    # Power
    min_power = slot_cumsum.index.min()
    median_power = slot_cumsum.index[slot_cumsum >= 0.5][0]
    max_power = slot_cumsum.index.max()
    # Power Ratio
    min_power_ratio = 100 * min_power / max_power
    median_power_ratio = 100 * median_power / max_power
    max_power_ratio = 100
    leveled_power_ratio = 100 * leveled_power / max_power
    # Power Increase
    # TODO: Scale these off of equipped median power. This will require being patient to get results of later iteration.
    min_power_increase = 100 * (min_power - leveled_power) / leveled_power
    median_power_increase = 100 * (median_power - leveled_power) / leveled_power
    max_power_increase = 100 * (max_power - leveled_power) / leveled_power
    leveled_power_increase = 0.0
    # Percentile
    leveled_power_percentile = 100 * slot_cumsum[slot_cumsum.index <= leveled_power].iloc[-1]
    # Log to console
    log_strings = [
        f"Slot Min Power:         {min_power:>7,.0f} | {min_power_ratio:>5.1f}% | {min_power_increase:>+5.1f}%",
        f"Slot Expected Power:    {median_power:>7,.0f} | {median_power_ratio:>5.1f}% | {median_power_increase:>+5.1f}%",
        f"Slot Max Power:         {max_power:>7,.0f} | {max_power_ratio:>5.1f}% | {max_power_increase:>+5.1f}%",
    ]
    leveled_power_str = (
        f"Artifact Leveled Power: {leveled_power:>7,.0f} | "
        f"{leveled_power_ratio:>5.1f}% | "
        f"{leveled_power_increase:>+5.1f}% | "
        f"{_percentile_str_to_suffix(_unbounded_percentile_to_string(leveled_power_percentile))} Slot Percentile"
    )
    leveled_position = int(leveled_power >= min_power) + int(leveled_power >= median_power)
    log_strings.insert(leveled_position, leveled_power_str)
    for log_string in log_strings:
        log.info(log_string)


def log_artifact_power(
    slot_cumsum: pd.Series,
    artifact_potential_df: pd.DataFrame,
    artifact_cumsum: pd.Series,
    equipped_cumsum: pd.Series,
    equipped_median_power: float,
    artifact: artifact.Artifact,
):
    """Logs artifact potential to console"""
    # Power
    artifact_min_power = artifact_cumsum.index.min()
    artifact_median_power = artifact_cumsum.index[artifact_cumsum >= 0.5][0]
    artifact_max_power = artifact_cumsum.index.max()
    slot_max_power = slot_cumsum.index.max()
    # Power Ratio
    artifact_min_power_ratio = 100 * artifact_min_power / slot_max_power
    artifact_median_power_ratio = 100 * artifact_median_power / slot_max_power
    artifact_max_power_ratio = 100 * artifact_max_power / slot_max_power
    # Power Increase
    artifact_min_power_increase = 100 * (artifact_min_power - equipped_median_power) / equipped_median_power
    artifact_median_power_increase = 100 * (artifact_median_power - equipped_median_power) / equipped_median_power
    artifact_max_power_increase = 100 * (artifact_max_power - equipped_median_power) / equipped_median_power
    # Percentile
    artifact_min_power_percentile = 100 * slot_cumsum[slot_cumsum.index <= artifact_min_power].iloc[-1]
    artifact_median_power_percentile = 100 * slot_cumsum[slot_cumsum.index <= artifact_median_power].iloc[-1]
    artifact_max_power_percentile = 100 * slot_cumsum[slot_cumsum.index <= artifact_max_power].iloc[-1]

    # Prepare artifact log strings
    log_strings = [
        (
            f"Artifact Expected Power: {artifact_median_power:>7,.0f} | "
            f"{artifact_median_power_ratio:>5.1f}% | "
            f"{artifact_median_power_increase:>+5.1f}% | "
            f"{artifact_median_power_percentile:>5.1f}{_suffix(artifact_median_power_percentile)} Slot Percentile"
        )
    ]
    num_child_artifacts = artifact_potential_df.shape[0]
    if num_child_artifacts > 1:
        min_power_str = (
            f"Artifact Min Power:      {artifact_min_power:>7,.0f} | "
            f"{artifact_min_power_ratio:>5.1f}% | "
            f"{artifact_min_power_increase:>+5.1f}% | "
            f"{artifact_min_power_percentile:>5.1f}{_suffix(artifact_min_power_percentile)} Slot Percentile"
        )
        max_power_str = (
            f"Artifact Max Power:      {artifact_max_power:>7,.0f} | "
            f"{artifact_max_power_ratio:>5.1f}% | "
            f"{artifact_max_power_increase:>+5.1f}% | "
            f"{artifact_max_power_percentile:>5.1f}{_suffix(artifact_max_power_percentile)} Slot Percentile"
        )
        log_strings = [min_power_str] + log_strings + [max_power_str]
    # Log to console
    for log_string in log_strings:
        log.info(log_string)

    # Calculate artifact score
    # Chance to drop artifact with same set, slot, and main_stat
    drop_chance = 0.5 * 0.2 * genshin_data.main_stat_drop_rate[type(artifact).__name__][artifact.main_stat] / 100
    # TODO: If flex, raise drop_chance

    # Create map between artifact power and slot power for probabalistic integration
    artifact_probability_by_power = artifact_potential_df["probability"]
    artifact_probability_by_power.index = artifact_potential_df["power"]
    artifact_power_list = artifact_probability_by_power.index.tolist()
    slot_power_list = slot_cumsum.index.tolist()
    artifact2slot_map = list_mapper.map_float_lists(artifact_power_list, slot_power_list)

    # Chance of dropping better artifact
    slot_better_chance = 0.0
    for artifact_power, slot_power in artifact2slot_map.items():
        if slot_power is not None:
            artifact_prob = artifact_probability_by_power.loc[artifact_power]
            if type(artifact_prob) is pd.Series:
                artifact_prob = artifact_prob.iloc[-1]
            slot_cumulative_probability = slot_cumsum.loc[slot_power]
            if type(slot_cumulative_probability) is pd.Series:
                slot_cumulative_probability = slot_cumulative_probability.iloc[-1]
            slot_better_chance += artifact_prob * slot_cumulative_probability

    # Score
    score = 1 / (drop_chance * (1 - slot_better_chance))
    log_str = f"Artifact Score: {score:>6,.1f} Runs"

    # Run if not currently equipped artifact
    if equipped_median_power != artifact_median_power:

        # Create map between artifact power and equipped power for probabalistic integration
        equipped_power_list = equipped_cumsum.index.tolist()
        artifact2equipped_map = list_mapper.map_float_lists(artifact_power_list, equipped_power_list)

        # Chance of beating equipped artifact
        beat_equipped_chance = 0.0
        for artifact_power, equipped_power in artifact2equipped_map.items():
            if equipped_power is not None:
                artifact_prob = artifact_probability_by_power.loc[artifact_power]
                if type(artifact_prob) is pd.Series:
                    artifact_prob = artifact_prob.iloc[-1]
                equipped_cumulative_probability = equipped_cumsum.loc[equipped_power]
                if type(equipped_cumulative_probability) is pd.Series:
                    equipped_cumulative_probability = equipped_cumulative_probability.iloc[-1]
                beat_equipped_chance += artifact_prob * equipped_cumulative_probability

        # Format chance to beat
        if beat_equipped_chance >= 100:
            decimal.getcontext().prec = 4
            beat_equipped_chance_str = str(decimal.getcontext().create_decimal(beat_equipped_chance)) + "%"
        elif 10 >= beat_equipped_chance > 100:
            decimal.getcontext().prec = 3
            beat_equipped_chance_str = " " + str(decimal.getcontext().create_decimal(beat_equipped_chance)) + "%"
        else:
            decimal.getcontext().prec = 2
            beat_equipped_chance_str = "  " + str(decimal.getcontext().create_decimal(beat_equipped_chance)) + "%"
        decimal.getcontext().prec = 2
        beat_equipped_chance_str = _unbounded_percentile_to_string(beat_equipped_chance)
        log_str += f"         Chance of Beating Equipped: {beat_equipped_chance_str}"
    else:
        beat_equipped_chance = None
    log.info(log_str)

    return artifact_median_power_percentile, score, beat_equipped_chance


def _unbounded_percentile_to_string(percentile: float):
    """Converts percentile to string, providing necessary 9s or 0s depending on size"""
    if percentile > 99.9:
        return _high_percentile_to_string(percentile)
    elif percentile < 10:
        return _lower_percentile_to_string(percentile)
    else:
        return f"{percentile:4.1f}%"


def _high_percentile_to_string(percentile: float):
    """Converts high percentile to string, providing necessary 9s"""
    if percentile <= 99.9:
        return f"{percentile:4.1f}%"
    else:
        num_nines = math.floor(-math.log10(100 - percentile)) + 1
        length = num_nines + 3
        return "{percentile:{length}.{num_nines}f}%".format(percentile=percentile, length=length, num_nines=num_nines)


def _lower_percentile_to_string(percentile: float):
    """Converts low percentile to string, providing necessary 0s"""
    if percentile >= 10:
        return f"{percentile:>4.1f}%"
    else:
        decimal.getcontext().prec = 2
        return "  " + str(decimal.getcontext().create_decimal(percentile)) + "%"


def _suffix(value: float) -> str:
    return ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"][round(10 * value) % 10]


def _percentile_str_to_suffix(value: str) -> str:
    return value[:-1] + ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"][int(value[-2])]


def _pandas_float_to_string(value: float) -> str:
    """Formats pandas floats the way I want them"""
    return f"{value:,.1f}"


pd.set_option("float_format", _pandas_float_to_string)
pd.set_option("Colheader_justify", "right")
