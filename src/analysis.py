from __future__ import annotations

import decimal
import logging
import math
import re
from typing import TYPE_CHECKING

import pandas as pd

from . import genshin_data, graphing, power_calculator
from .artifact import Artifact, Circlet, Flower, Goblet, Plume, Sands
from .potential import find_useful_stats, individual_potential

if TYPE_CHECKING:
    from .go_parser import GenshinOptimizerData

log = logging.getLogger(__name__)


def evaluate_character(
    genshin_optimizer_data: GenshinOptimizerData,
    character_name: str,
    character_dmg_type: str,
    character_scaling_stat: str,
    character_passive: dict[str, float],
    character_stat_transfer: dict[str, dict[str, float]],
    weapon_passive: dict[str, float],
    amplifying_reaction: str,
    reaction_percentage: float,
    slots: list[type] = [Flower, Plume, Sands, Goblet, Circlet],
    plot: bool = True,
    smooth_plot: bool = True,
):

    # Fix inputs
    # Singleton type
    if type(slots) is type:
        slots = [slots]

    # Log
    log.info("-" * 140)
    log.info(f"EVALUATING ARTIFACT POTENTIALS")
    log.info("")

    # Retrieve character from GO database
    character = genshin_optimizer_data.get_character(character_name=character_name)
    # Set character and weapon characteristics
    character.dmg_type = character_dmg_type
    character.scaling_stat = character_scaling_stat
    character.passive = character_passive
    character.stat_transfer = character_stat_transfer
    character.weapon.passive = weapon_passive
    character.amplifying_reaction = amplifying_reaction
    character.reaction_percentage = reaction_percentage

    # Retrieve equipped and potential artifacts from GO database
    equipped_artifacts = genshin_optimizer_data.get_characters_artifacts(character_name=character_name)
    alternative_artifacts = genshin_optimizer_data.get_alternative_artifacts(equipped_artifacts=equipped_artifacts)
    # Remove alternative artifacts from slots not being evaluated
    for slot in list(alternative_artifacts.keys()):
        if slot not in slots:
            alternative_artifacts.pop(slot)

    # Log character settings
    log.info(
        f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}"
    )
    log.info(
        f"WEAPON: {character.weapon.name_formated.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}"
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
    current_power = power_calculator.evaluate_power(character=character, artifacts=equipped_artifacts)
    current_stats = power_calculator.evaluate_stats(character=character, artifacts=equipped_artifacts)
    current_stats = current_stats[find_useful_stats(character, equipped_artifacts)]
    log.info(f"CURRENT POWER: {current_power:>7,.0f}")
    log.info(current_stats.to_frame().T)
    log.info("")
    # Log character future stats
    leveled_power = power_calculator.evaluate_leveled_power(character=character, artifacts=equipped_artifacts)
    if leveled_power > current_power:
        log.info(f"{character.name.upper()} LEVELED STATS:")
        power_delta = 100 * (leveled_power / current_power - 1)
        log.info(f"LEVELED POWER: {leveled_power:>7,.0f} | {power_delta:>+5.1f}%")
        leveled_stats = power_calculator.evaluate_leveled_stats(character=character, artifacts=equipped_artifacts)
        leveled_stats = leveled_stats[find_useful_stats(character, equipped_artifacts)]
        log.info(leveled_stats.to_frame().T)
        log.info("")
    log.info("(Stats not shown above do not affect character power and are suppressed in artifact evaluation.)")
    log.info(
        "(If you belive there is a stat missing, double check `character_scaling_stat` and `character_stat_transfer` inputs.)"
    )
    log.info("")

    # TODO: Describe how good one roll of ATK% vs Crit Rate% vs DMG%

    # Log number of artifacts
    log.info("Number of alternative artifacts:")
    for slot, artifacts in alternative_artifacts.items():
        log.info(f"{slot.__name__:>7s}: {len(artifacts)}")
    log.info("")

    # Iterate through slots
    slot_potentials: dict[type, pd.DataFrame] = {}
    artifact_potentials: dict[type, dict[Artifact, pd.DataFrame]] = {slot: {} for slot in slots}
    artifact_powers: dict[type, dict[Artifact, float]] = {slot: {} for slot in slots}
    artifact_percentiles: dict[type, dict[Artifact, float]] = {slot: {} for slot in slots}
    artifact_scores: dict[type, dict[Artifact, float]] = {slot: {} for slot in slots}
    for slot in slots:

        log.info("-" * 140)
        log.info(f"EVALUATING {slot.__name__.upper()} SLOT POTENTIAL...")

        # Get equipped artifact
        equipped_artifact = equipped_artifacts.get_artifact(slot=slot)
        if equipped_artifact is None:
            log.info(f"No {slot.__name__} equipped on {character_name}.")
            log.info("")
            continue
        log.info(f"    Stars: {equipped_artifact.stars:>d}*")
        set_str_long = re.sub(r"(\w)([A-Z])", r"\1 \2", equipped_artifact.set)  # Add spaces between capitals
        log.info(f"      Set: {set_str_long}")
        log.info(f"Main Stat: {equipped_artifact.main_stat}")

        # Evaluate slot potential
        if equipped_artifact.set in genshin_data.dropped_from_world_boss:
            source = "world boss"
        else:
            source = "domain"
        slot_potential_df = individual_potential(
            character=character,
            equipped_artifacts=equipped_artifacts,
            artifact=equipped_artifact,
            source=source,
        )
        slot_potentials[slot] = slot_potential_df
        log_slot_power(slot_potential_df=slot_potential_df, leveled_power=leveled_power)
        log.info("")

        # Evaluate artifact potential
        # Start with the equipped artifact and then iterate through other artifacts, sorted numerically
        log.info(f"EVALUATING ALTERNATIVE {slot.__name__.upper()} SLOT POTENTIAL...")
        log.info("!!! CURRENTLY EQUIPPED ARTIFACT !!!")
        equipped_artifact = equipped_artifacts.get_artifact(slot)
        other_artifacts = [artifact for artifact in alternative_artifacts[slot] if artifact is not equipped_artifact]
        other_artifacts.sort(key=lambda artifact: int(artifact.name))
        alternative_artifacts_slot = [equipped_artifact] + other_artifacts
        equipped_expected_power = None
        for alternative_artifact in alternative_artifacts_slot:
            # Log artifact
            log.info(
                f" NAME    SLOT STARS         SET LEVEL               MAIN STAT   HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
            )
            log.info(alternative_artifact.to_string_table())
            # Calculate potential
            artifact_potential_df = individual_potential(
                character=character,
                equipped_artifacts=equipped_artifacts,
                artifact=alternative_artifact,
                substat_rolls=alternative_artifact.substat_rolls,
                source=source,
            )
            artifact_potentials[slot][alternative_artifact] = artifact_potential_df
            # Save expected power
            cumsum = artifact_potential_df["probability"].cumsum()
            artifact_powers[slot][alternative_artifact] = artifact_potential_df.loc[(cumsum >= 0.5).idxmax()]["power"]
            # Save expected equipped power
            if equipped_expected_power is None:
                equipped_expected_power = artifact_powers[slot][alternative_artifact]
            # Log results (and calculate score)
            percentile, score, beat_equipped_chance = log_artifact_power(
                slot_potential_df=slot_potential_df,
                artifact_potential_df=artifact_potential_df,
                equipped_expected_power=equipped_expected_power,
                artifact=alternative_artifact,
            )
            # Save excpected percentile
            artifact_percentiles[slot][alternative_artifact] = percentile
            # Save expected score
            artifact_scores[slot][alternative_artifact] = (score, beat_equipped_chance)
            log.info("")

    # POST CALCULATION SUMMARY

    # Summarize each slot in a leaderboard
    log.info("-" * 140)
    log.info(f"SLOT SCOREBOARDS...")
    log.info("")
    for slot in slots:
        equipped_artifact = equipped_artifacts.get_artifact(slot=slot)
        artifact_scores_sorted = dict(sorted(artifact_scores[slot].items(), key=lambda item: item[1], reverse=True))
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
        max_score = max([max([score for _, (score, _) in artifact_scores_sorted.items()]), 6])
        max_score_spaces = max(len(f"{max_score:>,.0f}") + 1, 5)
        header_str = (
            f"RANK   NAME    SLOT STARS         SET LEVEL               MAIN STAT   HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
            " |"
            "  ΔPower"
            f"  {f'Percentile'.rjust(max_percentile_spaces)}"
            f"  {'Score'.rjust(max_score_spaces)}"
            "  Chance of Beating Equipped"
        )
        ind = 1
        for artifact, (score, beat_equipped_chance) in artifact_scores_sorted.items():
            if ind % 10 == 1:
                log.info(header_str)
            log.info(
                f"{ind:>3.0f})  "
                f"{artifact.to_string_table()}"
                " |"
                f"{100 * (artifact_powers[slot][artifact] / slot_potentials[slot]['power'].min() - 1):>+7.1f}%"
                f"  {(' ' * percentile_left_spaces) + f'{_high_percentile_to_string(artifact_percentiles[slot][artifact])}'.ljust(max_percentile_spaces)}"
                f"  {f'{score:>,.0f}'.rjust(max_score_spaces)}"
                f"  {'EQUIPPED' if artifact is equipped_artifact else _unbounded_percentile_to_string(beat_equipped_chance)}"
            )
            ind += 1
        log.info("")

    # Plot each slot

    a = 1


def log_slot_power(slot_potential_df: pd.DataFrame, leveled_power: float):
    """Logs slot potential to console"""
    # Minimum Power
    min_power = slot_potential_df["power"].min()
    # Maximum Power
    max_power = slot_potential_df["power"].max()
    max_power_increase = 100 * (max_power / min_power - 1)
    # Median Power
    cumsum = slot_potential_df["probability"].cumsum()
    median_power = slot_potential_df.iloc[(cumsum >= 0.5).idxmax()]["power"]
    median_power_increase = 100 * (median_power / min_power - 1)
    # Base Power
    if leveled_power is not None:
        leveled_power_increase = 100 * (leveled_power / min_power - 1)
        leveled_power_percentile = (
            100 * slot_potential_df["probability"][slot_potential_df["power"] < leveled_power].sum()
        )
    # Log to console
    log_strings = [
        f"Slot Min Power:         {min_power:>7,.0f} |  +0.0%",
        f"Slot Expected Power:    {median_power:>7,.0f} | {median_power_increase:>+5.1f}%",
        f"Slot Max Power:         {max_power:>7,.0f} | {max_power_increase:>+5.1f}%",
    ]
    if leveled_power is not None:
        leveled_power_str = (
            f"Artifact Leveled Power: {leveled_power:>7,.0f} | "
            f"{leveled_power_increase:>+5.1f}% | "
            f"{_percentile_str_to_suffix(_unbounded_percentile_to_string(leveled_power_percentile))} Slot Percentile"
        )
        leveled_position = int(leveled_power >= min_power) + int(leveled_power >= median_power)
        log_strings.insert(leveled_position, leveled_power_str)
    for log_string in log_strings:
        log.info(log_string)


def log_artifact_power(
    slot_potential_df: pd.DataFrame,
    artifact_potential_df: pd.DataFrame,
    equipped_expected_power: float,
    artifact: Artifact,
):
    """Logs artifact potential to console"""

    # Slot Power
    slot_min_power = slot_potential_df["power"].min()
    # Minimum Artifact Power
    artifact_min_power = artifact_potential_df["power"].min()
    min_power_increase = 100 * (artifact_min_power / slot_min_power - 1)
    min_power_slot_percentile = (
        100 * slot_potential_df["probability"][slot_potential_df["power"] < artifact_min_power].sum()
    )
    # Median Artifact Power
    cumsum = artifact_potential_df["probability"].cumsum()
    artifact_median_power = artifact_potential_df.loc[(cumsum >= 0.5).idxmax()]["power"]
    median_power_increase = 100 * (artifact_median_power / slot_min_power - 1)
    median_power_slot_percentile = (
        100 * slot_potential_df["probability"][slot_potential_df["power"] < artifact_median_power].sum()
    )
    # Maximum Artifact Power
    artifact_max_power = artifact_potential_df["power"].max()
    max_power_increase = 100 * (artifact_max_power / slot_min_power - 1)
    max_power_slot_percentile = (
        100 * slot_potential_df["probability"][slot_potential_df["power"] < artifact_max_power].sum()
    )
    # Current Power
    equipped_expected_power_artifact_percentile = (
        100 * artifact_potential_df["probability"][artifact_potential_df["power"] <= equipped_expected_power].sum()
    )  # <= so that "Chance of Beating" doesn't include ties
    equipped_expected_power_increase = 100 * (equipped_expected_power / slot_min_power - 1)
    equipped_expected_power_slot_percentile = (
        100 * slot_potential_df["probability"][slot_potential_df["power"] < equipped_expected_power].sum()
    )

    # Prepare artifact log strings
    log_strings = [
        (
            f"Artifact Expected Power: {artifact_median_power:>7,.0f} | "
            f"{median_power_increase:>+5.1f}% | "
            f"{median_power_slot_percentile:>5.1f}{_suffix(median_power_slot_percentile)} Slot Percentile"
        )
    ]
    num_child_artifacts = artifact_potential_df.shape[0]
    if num_child_artifacts > 1:
        min_power_str = (
            f"Artifact Min Power:      {artifact_min_power:>7,.0f} | "
            f"{min_power_increase:>+5.1f}% | "
            f"{min_power_slot_percentile:>5.1f}{_suffix(min_power_slot_percentile)} Slot Percentile"
        )
        max_power_str = (
            f"Artifact Max Power:      {artifact_max_power:>7,.0f} | "
            f"{max_power_increase:>+5.1f}% | "
            f"{max_power_slot_percentile:>5.1f}{_suffix(max_power_slot_percentile)} Slot Percentile"
        )
        log_strings = [min_power_str] + log_strings + [max_power_str]
    # Prepare equipped artifact log string
    if equipped_expected_power is not None:
        if equipped_expected_power != artifact_median_power:  # Skip if this is the current equippped artifact
            leveled_power_str = (
                f"Equipped Expected Power: {equipped_expected_power:>7,.0f} | "
                f"{equipped_expected_power_increase:>+5.1f}% | "
                f"{equipped_expected_power_slot_percentile:>5.1f}%{_suffix(equipped_expected_power_slot_percentile)} Slot Percentile | "
            )
            if equipped_expected_power >= artifact_max_power:
                leveled_power_str += f">100.0th Artifact Percentile"
            elif equipped_expected_power_artifact_percentile == 100:
                leveled_power_str += f"=100.0th Artifact Percentile"
            else:
                leveled_power_str += f"{_percentile_str_to_suffix(_unbounded_percentile_to_string(equipped_expected_power_artifact_percentile))} Artifact Percentile"

            if num_child_artifacts > 1:
                leveled_position = (
                    int(equipped_expected_power >= artifact_min_power)
                    + int(equipped_expected_power >= artifact_median_power)
                    + int(equipped_expected_power >= artifact_max_power)
                )
            else:
                leveled_position = int(equipped_expected_power > artifact_median_power)
            log_strings.insert(leveled_position, leveled_power_str)
    # Log to console
    for log_string in log_strings:
        log.info(log_string)

    # Calculate artifact score
    # Cost to run domain once
    if artifact.set in genshin_data.dropped_from_world_boss:
        run_cost = 40
    else:
        run_cost = 20
    # Chance to drop artifact with same set, slot, and main_stat
    drop_chance = 0.5 * 0.2 * genshin_data.main_stat_drop_rate[type(artifact).__name__][artifact.main_stat] / 100
    # Chance of dropping better artifact
    better_chance = (100 - median_power_slot_percentile) / 100
    # Score
    score = run_cost / (drop_chance * better_chance)
    log_str = f"Artifact Score: {score:>6,.0f} Resin"
    # Better than equipped chance
    if equipped_expected_power != artifact_median_power:
        beat_equipped_chance = 100 - equipped_expected_power_artifact_percentile
        # Deal with computer floating point error
        if beat_equipped_chance < 0.0:
            beat_equipped_chance = 0.0
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

    return median_power_slot_percentile, score, beat_equipped_chance


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
