from __future__ import annotations

import copy
import decimal
import itertools
import logging
import math
import re

import numpy as np
import pandas as pd
from pandas.core.frame import DataFrame

from . import genshin_data, graphing, power_calculator
from .artifact import Artifact, Circlet, Flower, Goblet, Plume, Sands
from .artifacts import Artifacts
from .character import Character
from .go_parser import GenshinOptimizerData

log = logging.getLogger(__name__)


def evaluate_character(
    genshin_optimizer_data: GenshinOptimizerData,
    character_name: str,
    character_dmg_type: str,
    character_scaling_stat: str = "ATK",
    character_passive: dict[str, float] = {},
    character_stat_transfer: dict[str, dict[str, float]] = {},
    weapon_passive: dict[str, float] = {},
    amplifying_reaction: str = None,
    reaction_percentage: float = None,
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
    current_stats = current_stats[_find_useful_stats(character, equipped_artifacts)]
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
        leveled_stats = leveled_stats[_find_useful_stats(character, equipped_artifacts)]
        log.info(leveled_stats.to_frame().T)
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
        slot_potential_df = _individual_potential(
            character=character,
            equipped_artifacts=equipped_artifacts,
            slot=slot,
            set_str=equipped_artifact.set,
            stars=equipped_artifact.stars,
            main_stat=equipped_artifact.main_stat,
            target_level=equipped_artifact.max_level,
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
            artifact_potential_df = _individual_potential(
                character=character,
                equipped_artifacts=equipped_artifacts,
                slot=type(alternative_artifact),
                set_str=alternative_artifact.set,
                stars=alternative_artifact.stars,
                main_stat=alternative_artifact.main_stat,
                target_level=alternative_artifact.max_level,
                substat_rolls=alternative_artifact.substat_rolls,
                source=source,
            )
            artifact_potentials[slot][alternative_artifact] = artifact_potential_df
            # Save expected equipped power
            if equipped_expected_power is None:
                equipped_potential_df_sorted = artifact_potential_df.sort_values("power")
                cumsum = equipped_potential_df_sorted["probability"].cumsum()
                equipped_expected_power = equipped_potential_df_sorted.loc[(cumsum >= 0.5).idxmax()]["power"]
            # Log results (and calculate score)
            score, beat_equipped_chance = log_artifact_power(
                slot_potential_df=slot_potential_df,
                artifact_potential_df=artifact_potential_df,
                equipped_expected_power=equipped_expected_power,
                artifact=alternative_artifact,
            )
            artifact_scores[slot][alternative_artifact] = (score, beat_equipped_chance)
            log.info("")

    # After all slots are run, summarize each slot in a leaderboard
    log.info("-" * 140)
    log.info(f"SLOT SCOREBOARDS...")
    log.info("")
    for slot in slots:
        equipped_artifact = equipped_artifacts.get_artifact(slot=slot)
        artifact_scores_sorted = dict(sorted(artifact_scores[slot].items(), key=lambda item: item[1], reverse=True))
        set_str_long = re.sub(r"(\w)([A-Z])", r"\1 \2", equipped_artifact.set)
        log.info(f"{equipped_artifact.stars}* {equipped_artifact.main_stat} {slot.__name__} Scoreboard")
        header_str = f"RANK   NAME    SLOT STARS         SET LEVEL               MAIN STAT   HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%    Score  Chance of Beating Equipped"
        ind = 1
        for artifact, (score, beat_equipped_chance) in artifact_scores_sorted.items():
            if ind % 10 == 1:
                log.info(header_str)
            log_str = f"{ind:>3.0f})  " + artifact.to_string_table() + f" {score:>8,.0f}  "
            if artifact is equipped_artifact:
                # Mark as equipped
                log_str += "EQUIPPED"
            else:
                # Add decimal with fixed period location
                if beat_equipped_chance == 100:
                    decimal_str = str(f"{beat_equipped_chance:4.1f}") + "%"
                elif 10 <= beat_equipped_chance < 100:
                    decimal_str = " " + str(f"{beat_equipped_chance:3.1f}") + "%"
                else:
                    decimal.getcontext().prec = 2
                    decimal_str = "  " + str(decimal.getcontext().create_decimal(beat_equipped_chance)) + "%"
                log_str += decimal_str
            log.info(log_str)
            ind += 1
        log.info("")

    a = 1


def log_slot_power(slot_potential_df: pd.DataFrame, leveled_power: float):
    """Logs slot potential to console"""
    # Minimum Power
    min_power = slot_potential_df["power"].min()
    # Maximum Power
    max_power = slot_potential_df["power"].max()
    max_power_increase = 100 * (max_power / min_power - 1)
    # Median Power
    slot_potential_df_sorted = slot_potential_df.sort_values("power")
    cumsum = slot_potential_df_sorted["probability"].cumsum()
    median_power = slot_potential_df_sorted.iloc[(cumsum >= 0.5).idxmax()]["power"]
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
            f"{leveled_power_percentile:>5.1f}{_suffix(leveled_power_percentile)} Slot Percentile"
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
    artifact_potential_df_sorted = artifact_potential_df.sort_values("power")
    cumsum = artifact_potential_df_sorted["probability"].cumsum()
    artifact_median_power = artifact_potential_df_sorted.loc[(cumsum >= 0.5).idxmax()]["power"]
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
                f"{equipped_expected_power_slot_percentile:>5.1f}{_suffix(equipped_expected_power_slot_percentile)} Slot Percentile | "
                f"{equipped_expected_power_artifact_percentile:>5.1f}{_suffix(equipped_expected_power_artifact_percentile)} Artifact Percentile"
            )
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
        beat_equipped_chance_str = str(decimal.getcontext().create_decimal(beat_equipped_chance)) + "%"
        log_str += f"         Chance of Beating Equipped: {beat_equipped_chance_str}"
    else:
        beat_equipped_chance = None
    log.info(log_str)

    return score, beat_equipped_chance


def _individual_potential(
    character: Character,
    equipped_artifacts: Artifacts,
    slot: type,
    set_str: str,
    stars: int,
    main_stat: str,
    target_level: int,
    source: str,
    starting_level: int = None,
    substat_rolls: dict[str] = None,
) -> pd.DataFrame:

    # Default substats
    seed_pseudo_artifact = {"substats": {}, "probability": 1.0}
    seed_pseudo_artifact_rolls = {"substats": {}, "probability": 1.0}
    if substat_rolls is not None:
        for substat, rolls in substat_rolls.items():
            seed_pseudo_artifact["substats"][substat] = 0
            seed_pseudo_artifact_rolls["substats"][substat] = [0, 0, 0, 0]
            for roll in rolls:
                roll_level = genshin_data.substat_roll_values[substat][stars].index(roll)
                seed_pseudo_artifact_rolls["substats"][substat][roll_level] += 1

    # Calculate number of unlocks and increases
    existing_unlocks = len(seed_pseudo_artifact["substats"])
    if substat_rolls is not None:
        remaining_unlocks = min(4, max(0, stars - 2) + math.floor(target_level / 4)) - existing_unlocks
        if starting_level is not None:
            remaining_increases = math.floor(target_level / 4) - math.floor(starting_level / 4) - remaining_unlocks
        else:
            existing_increases = sum([len(rolls) for substat, rolls in substat_rolls.items()]) - existing_unlocks
            remaining_increases = (
                max(0, stars - 2)
                + math.floor(target_level / 4)
                - existing_unlocks
                - remaining_unlocks
                - existing_increases
            )
    else:
        remaining_unlocks = min(4, max(0, stars - 2) + math.floor(target_level / 4)) - existing_unlocks
        remaining_increases = max(0, stars - 2) + math.floor(target_level / 4) - existing_unlocks - remaining_unlocks

    total_rolls_high_chance = genshin_data.extra_substat_probability[source][stars]

    # Identify useful and condensable stats
    useful_stats = _find_useful_stats(character=character, artifacts=equipped_artifacts)
    condensable_substats = [stat for stat in genshin_data.substat_roll_values.keys() if stat not in useful_stats]

    # Identify roll combinations
    substat_values_df, slot_potential_df = _make_children(
        character=character,
        stars=stars,
        main_stat=main_stat,
        remaining_unlocks=remaining_unlocks,
        remaining_increases=remaining_increases,
        total_rolls_high_chance=total_rolls_high_chance,
        seed_pseudo_artifact=seed_pseudo_artifact,
        seed_pseudo_artifact_rolls=seed_pseudo_artifact_rolls,
        condensable_substats=condensable_substats,
    )

    # Format output
    for stat in genshin_data.stat_names:
        if stat not in substat_values_df:
            substat_values_df[stat] = 0
    substat_values_df = substat_values_df.fillna(0)

    # Assign to artifact
    artifact = slot(
        name="pseudo", set_str=set_str, main_stat=main_stat, stars=stars, level=target_level, substats=substat_values_df
    )

    # Create artifact list, replacing previous artifact
    other_artifacts_list = [other_artifact for other_artifact in equipped_artifacts if type(other_artifact) != slot]
    other_artifacts_list.append(artifact)
    other_artifacts = Artifacts(other_artifacts_list)

    # Calculate power
    power = power_calculator.evaluate_leveled_power(character=character, artifacts=other_artifacts)

    # Return results
    slot_potential_df["power"] = power
    return slot_potential_df


def _find_useful_stats(character: Character, artifacts: Artifacts):
    """Returns a list of substats that affect power calculation"""
    useful_stats = [
        f"Base {character.scaling_stat}",
        f"{character.scaling_stat}",
        f"{character.scaling_stat}%",
        f"Total {character.scaling_stat}",
    ]
    if character.amplifying_reaction is not None:
        useful_stats.append("Elemental Mastery")
    if character.crits == "avgHit":
        useful_stats.append("Crit Rate%")
        useful_stats.append("Crit DMG%")
    elif character.crits == "always":
        useful_stats.append("Crit DMG%")
    if character.dmg_type == "healing":
        useful_stats.append("Healing Bonus%")
    else:
        useful_stats.append(f"{character.dmg_type.capitalize()} DMG%")
    # Transforming stats
    for destination_stat, source_stats in character.stat_transfer.items():
        if destination_stat in useful_stats:
            for source_stat in source_stats:
                useful_stats.append(source_stat)
                if "Total" in source_stat:
                    source_stat_children = source_stat[7:]
                    useful_stats.append(f"Base {source_stat_children}")
                    useful_stats.append(f"{source_stat_children}")
                    useful_stats.append(f"{source_stat_children}%")
    for destination_stat, source_stats in artifacts.stat_transfer.items():
        if destination_stat in useful_stats:
            for source_stat in source_stats:
                useful_stats.append(source_stat)
                if "Total" in source_stat:
                    source_stat_children = source_stat[7:]
                    useful_stats.append(f"Base {source_stat_children}")
                    useful_stats.append(f"{source_stat_children}")
                    useful_stats.append(f"{source_stat_children}%")
    return useful_stats


def _make_children(
    character: Character,
    stars: int,
    main_stat: str,
    remaining_unlocks: int,
    remaining_increases: int,
    total_rolls_high_chance: float,
    seed_pseudo_artifact: dict[str],
    seed_pseudo_artifact_rolls: dict[str],
    condensable_substats: list[str],
) -> pd.DataFrame:

    # Calculate initial substat count
    initial_substats = len(seed_pseudo_artifact["substats"])

    # Create pseudo artifact list
    pseudo_artifacts = [seed_pseudo_artifact]

    # Create every possible pseudo artifact by unlocking substats
    if remaining_unlocks > 0:
        pseudo_artifacts = _add_substats(
            pseudo_artifacts=pseudo_artifacts,
            remaining_unlocks=remaining_unlocks,
            main_stat=main_stat,
            condensable_substats=condensable_substats,
        )
    # Add extra unlocks (this should only occur for low stars or low target level)
    extra_unlock_chance = total_rolls_high_chance * int(
        (total_rolls_high_chance > 0) and (initial_substats + remaining_unlocks < 4)
    )
    if extra_unlock_chance > 0:
        remaining_unlocks_extra = remaining_unlocks + 1
        pseudo_artifacts_extra = _add_substats(
            pseudo_artifacts=pseudo_artifacts,
            remaining_unlocks=remaining_unlocks_extra,
            main_stat=main_stat,
            condensable_substats=condensable_substats,
        )
        # Fix original probabilities
        for pseudo_artifact in pseudo_artifacts:
            pseudo_artifact["probability"] *= 1 - extra_unlock_chance
        for pseudo_artifact_extra in pseudo_artifacts_extra:
            pseudo_artifact_extra["probability"] *= extra_unlock_chance
            pseudo_artifacts.append(pseudo_artifact_extra)
    if len(pseudo_artifacts) > 1:
        log.info(f"{len(pseudo_artifacts):,.0f} possible ways to roll initial substats...")

    # Create every possible pseudo artifact by assigning substat rolls
    if remaining_increases > 0:
        extra_increase_chance = total_rolls_high_chance * int(
            (total_rolls_high_chance > 0) and (initial_substats + remaining_unlocks >= 4)
        )
        pseudo_artifacts = _add_substat_rolls(
            pseudo_artifacts=pseudo_artifacts,
            remaining_increases=remaining_increases,
            extra_increase_chance=extra_increase_chance,
            condensable_substats=condensable_substats,
        )
    if len(pseudo_artifacts) > 1:
        log.info(f"{len(pseudo_artifacts):,.0f} possible ways to assign substat increases...")

    # Convert pseudo artifacts by calculating roll values
    substat_values_df, pseudo_artifacts_df = _calculate_substats(
        pseudo_artifacts=pseudo_artifacts, stars=stars, seed_pseudo_artifact_rolls=seed_pseudo_artifact_rolls
    )
    if substat_values_df.shape[0] > 1:
        log.info(f"{substat_values_df.shape[0]:,.0f} different ways to roll substat increases...")

    return substat_values_df, pseudo_artifacts_df


def _add_substats(
    pseudo_artifacts: list[dict], remaining_unlocks: int, main_stat: str, condensable_substats: list[str]
) -> list[dict]:
    """Creates pseudo artifacts with every possible combination of revealed substats"""

    # Generate list of possible substats
    valid_substats = set(genshin_data.substat_rarity[main_stat].keys())
    for substat in pseudo_artifacts[0]["substats"]:
        valid_substats.remove(substat)

    # Create list of possible substats
    base_probability = sum([genshin_data.substat_rarity[main_stat][substat] for substat in valid_substats])
    possibilities = []
    for substat in valid_substats:
        possibility = {
            "substat": substat,
            "probability": genshin_data.substat_rarity[main_stat][substat] / base_probability,
        }
        possibilities.append(possibility)

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([possibility["probability"] for possibility in possibilities]) - 1) < 1e-6

    # Create all possible combinations of new substats
    combinations = tuple(itertools.combinations(possibilities, remaining_unlocks))

    # Iterate across combinations
    new_pseudo_artifacts = {}
    for combination in combinations:

        # Create new pseudo artifact
        pseudo_artifact = copy.deepcopy(pseudo_artifacts[0])

        # Assign every new substat a single roll
        for substat in combination:
            pseudo_artifact["substats"][substat["substat"]] = 1

        # Calculate probability of pseudo artifact
        combination_probability = 0
        permutations = tuple(itertools.permutations(combination, len(combination)))
        for permutation in permutations:
            permutation_probability = 1
            remaining_probability = 1
            for substat in permutation:
                permutation_probability *= substat["probability"] / remaining_probability
                remaining_probability -= substat["probability"]
            combination_probability += permutation_probability
        pseudo_artifact["probability"] = combination_probability

        # Consolodate substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
        artifact_condensable_substats = [
            substat for substat in pseudo_artifact["substats"] if substat in condensable_substats
        ]
        for (ind, artifact_condensable_substat) in enumerate(artifact_condensable_substats):
            condensed_substat = condensable_substats[ind]
            pseudo_artifact["substats"][condensed_substat] = 0
        for artifact_condensable_substat in artifact_condensable_substats:
            if artifact_condensable_substat not in condensable_substats[: len(artifact_condensable_substats)]:
                del pseudo_artifact["substats"][artifact_condensable_substat]
        assert len(pseudo_artifact["substats"]) == 4

        # Add pseudo artifact to dict
        pseudo_artifact["substats"] = dict(sorted(pseudo_artifact["substats"].items()))  # sort keys
        key = str(pseudo_artifact["substats"])
        if key not in new_pseudo_artifacts:
            new_pseudo_artifacts[key] = pseudo_artifact
        else:
            new_pseudo_artifacts[key]["probability"] += pseudo_artifact["probability"]

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([possibility["probability"] for possibility in pseudo_artifacts]) - 1) < 1e-6

    # Return new pseudo artifacts
    pseudo_artifacts = [pseudo_artifact for pseudo_artifact in new_pseudo_artifacts.values()]
    return pseudo_artifacts


def _add_substat_rolls(
    pseudo_artifacts: list[dict],
    remaining_increases: int,
    extra_increase_chance: float,
    condensable_substats: list[str],
) -> list[dict]:
    """Creates pseudo artifacts with every possible combination of number of rolls for each substat"""

    # If extra increase chance, run iteration a second time.
    if extra_increase_chance > 0:
        remaining_increases += 1

    # Repeat for each increase required
    for ind in range(remaining_increases):

        # Create new pseudo artifact dict
        new_pseudo_artifacts = {}

        # Iterate over existing pseudo artifacts
        for pseudo_artifact in pseudo_artifacts:

            # Consolodate similar substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
            valid_substats = set(pseudo_artifact["substats"].keys())
            condensable_substats_on_artifact = [
                condensable_substat
                for condensable_substat in condensable_substats
                if condensable_substat in valid_substats
            ]

            # Create list of possible substats
            possibilities = []
            for substat in valid_substats:
                if substat in condensable_substats:
                    if substat == condensable_substats_on_artifact[0]:
                        substat_possibility = len(condensable_substats_on_artifact) / 4
                    else:
                        continue
                else:
                    substat_possibility = 0.25
                possibility = {"substat": substat, "probability": substat_possibility}
                possibilities.append(possibility)

            # Verify probability math (sum of probabilities is almost 1)
            assert abs(sum([possibility["probability"] for possibility in possibilities]) - 1) < 1e-6

            # Create new pseudo artifacts for each possibility
            for possibility in possibilities:
                new_pseudo_artifact = copy.deepcopy(pseudo_artifact)
                if possibility["substat"] not in condensable_substats:
                    new_pseudo_artifact["substats"][possibility["substat"]] += 1
                new_pseudo_artifact["probability"] *= possibility["probability"]
                # Add pseudo artifact to dict
                key = str(new_pseudo_artifact["substats"])
                if key not in new_pseudo_artifacts:
                    new_pseudo_artifacts[key] = new_pseudo_artifact
                else:
                    new_pseudo_artifacts[key]["probability"] += new_pseudo_artifact["probability"]

        # If extra increase, merge with previous list
        if ind == 0 and extra_increase_chance > 0:
            # Update probability of new artifacts
            for new_pseudo_artifact in new_pseudo_artifacts.values():
                new_pseudo_artifact["probability"] *= extra_increase_chance
            # Update probability of old artifacts and add to dict
            for old_pseudo_artifact in pseudo_artifacts:
                old_pseudo_artifact["probability"] *= 1 - extra_increase_chance
                key = str(old_pseudo_artifact["substats"])
                if key not in new_pseudo_artifacts:
                    new_pseudo_artifacts[key] = old_pseudo_artifact
                else:
                    new_pseudo_artifacts[key]["probability"] += old_pseudo_artifact["probability"]

        # Verify probability math (sum of probabilities is almost 1)
        assert (
            abs(sum([new_pseudo_artifact["probability"] for new_pseudo_artifact in new_pseudo_artifacts.values()]) - 1)
            < 1e-6
        )

        # Return overwrite pseudo_artifacts
        pseudo_artifacts = [pseudo_artifact for pseudo_artifact in new_pseudo_artifacts.values()]

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([pseudo_artifact["probability"] for pseudo_artifact in pseudo_artifacts]) - 1) < 1e-6

    return pseudo_artifacts


def _calculate_substats(
    pseudo_artifacts: list[dict], stars: int, seed_pseudo_artifact_rolls: dict[str]
) -> pd.DataFrame:
    """Creates every possible artifact from the given number of substat rolls"""

    ## NOTE: This function is where the vast majority of the computational time is spent

    # Calculate probability of possible expanded substats
    substat_rolls_probabillities_map = _substat_rolls_probabillities(seed_pseudo_artifact_rolls)

    # Creates empty list of pseudo artifacts
    pseudo_artifacts_list = []

    # Iterate over existing pseudo artifacts
    for pseudo_artifact in pseudo_artifacts:

        # Consolodate substats
        valid_substats = set(pseudo_artifact["substats"].keys())

        # Create list of possible roll combinations for each substat
        substat_products = []
        for substat in valid_substats:
            substat_products.append(substat_rolls_probabillities_map[substat][pseudo_artifact["substats"][substat]])

        # Create list of all possible roll combinations across each substat
        pseudo_artifact_list = list(itertools.product(*substat_products))
        pseudo_artifact_df = pd.DataFrame(pseudo_artifact_list, columns=valid_substats)

        # Calculate probabillity of each case
        pseudo_artifact_df["probability"] = pseudo_artifact["probability"]
        for column in pseudo_artifact_df:
            column_df = pd.DataFrame(pseudo_artifact_df[column].tolist())
            if len(column_df.columns) == 2:
                pseudo_artifact_df["probability"] *= column_df[column_df.columns[1]]
                pseudo_artifact_df[column] = column_df[column_df.columns[0]]

        # Verify probability math (sum of probabilities is almost the initial pseudo artifact probabillity)
        assert (
            abs(pseudo_artifact_df["probability"].sum() - pseudo_artifact["probability"])
            < 1e-6 * pseudo_artifact["probability"]
        )

        # Append to list
        pseudo_artifacts_list.append(pseudo_artifact_df)

    # Append dataframes
    pseudo_artifacts_df = pd.concat(pseudo_artifacts_list)

    # Split each substat
    substats_values = {}
    for substat in pseudo_artifacts_df:
        if pseudo_artifacts_df[substat].dtype is np.dtype(object):
            column_names = [f"{substat}_{roll}" for roll in range(4)]
            substat_list = pseudo_artifacts_df[substat].tolist()
            if substat_list[0] is np.nan:
                substat_list[0] = (0, 0, 0, 0)
            rolls_split = pd.DataFrame(substat_list, columns=column_names)
            substat_value = rolls_split.dot(genshin_data.substat_roll_values[substat][stars])
            substats_values[substat] = substat_value
        else:
            substats_values[substat] = pd.Series(pseudo_artifacts_df[substat].tolist())

    substat_values_df = pd.DataFrame(substats_values)

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(substat_values_df["probability"].sum() - 1) < 1e-6

    # Reset pseudo_artifacts index
    pseudo_artifacts_df.index = substat_values_df.index

    return substat_values_df, pseudo_artifacts_df


def _substat_rolls_probabillities(seed_pseudo_artifact_rolls: dict[str]) -> dict[int]:
    """Creates reference of probabillity of rolls being distibuted in a given manner"""

    # Create list of possible expanded substats
    possible_substat_rolls = {
        0: tuple(_sums(4, 0)),
        1: tuple(_sums(4, 1)),
        2: tuple(_sums(4, 2)),
        3: tuple(_sums(4, 3)),
        4: tuple(_sums(4, 4)),
        5: tuple(_sums(4, 5)),
        6: tuple(_sums(4, 6)),
    }

    # Calculates probabillity of each case
    substat_rolls_probabillities = {}
    for num_rolls in possible_substat_rolls:
        substat_rolls_probabillities[num_rolls] = []
        for roll_tuple in possible_substat_rolls[num_rolls]:
            arrangements = 1
            remaining_rolls = sum(roll_tuple)
            for num_substat_rolls in roll_tuple:
                arrangements *= math.comb(remaining_rolls, num_substat_rolls)
                remaining_rolls -= num_substat_rolls
            substat_rolls_probabillities[num_rolls].append(
                (roll_tuple, arrangements / len(roll_tuple) ** sum(roll_tuple))
            )

    # Complicated method for adding in pre-existing substat rolls from the seed artifact
    substat_rolls_probabillities_map = {}
    for substat in genshin_data.substat_roll_values:
        substat_rolls_probabillities_map[substat] = copy.deepcopy(substat_rolls_probabillities)
        if substat in seed_pseudo_artifact_rolls["substats"]:
            for num_rolls in substat_rolls_probabillities_map[substat]:
                new_combinations = []
                for combination in substat_rolls_probabillities_map[substat][num_rolls]:
                    # if combination[0] != (0,):
                    new_combination_rolls = np.array(combination[0]) + np.array(
                        seed_pseudo_artifact_rolls["substats"][substat]
                    )
                    new_combinations.append(
                        (
                            tuple(new_combination_rolls),
                            combination[1],
                        )
                    )
                substat_rolls_probabillities_map[substat][num_rolls] = new_combinations

    return substat_rolls_probabillities_map


# Source: https://stackoverflow.com/questions/7748442/generate-all-possible-lists-of-length-n-that-sum-to-s-in-python
def _sums(length, total_sum) -> tuple:
    if length == 1:
        yield (total_sum,)
    else:
        for value in range(total_sum + 1):
            for permutation in _sums(length - 1, total_sum - value):
                yield (value,) + permutation


def _suffix(value: float) -> str:
    suffix = ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"]
    mod_value = round(10 * value) % 10
    return suffix[mod_value]


def _pandas_float_to_string(value: float) -> str:
    """Formats pandas floats the way I want them"""
    return f"{value:,.1f}"


pd.set_option("float_format", _pandas_float_to_string)
pd.set_option("Colheader_justify", "right")
