from __future__ import annotations

import copy
import itertools
import logging
import math

import numpy as np
import pandas as pd

from . import genshin_data, power_calculator
from .artifact import Artifact
from .artifacts import Artifacts
from .character import Character

log = logging.getLogger(__name__)


def individual_potential(
    character: Character,
    equipped_artifacts: Artifacts,
    artifact: Artifact,
    source: str,
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
                roll_level = genshin_data.substat_roll_values[substat][artifact.stars].index(roll)
                seed_pseudo_artifact_rolls["substats"][substat][roll_level] += 1

    # Calculate number of unlocks and increases
    existing_unlocks = len(seed_pseudo_artifact["substats"])
    if substat_rolls is not None:
        remaining_unlocks = min(4, max(0, artifact.stars - 2) + math.floor(artifact.max_level / 4)) - existing_unlocks
        remaining_increases = math.floor(artifact.max_level / 4) - math.floor(artifact.level / 4) - remaining_unlocks
    else:
        remaining_unlocks = min(4, max(0, artifact.stars - 2) + math.floor(artifact.max_level / 4)) - existing_unlocks
        remaining_increases = (
            max(0, artifact.stars - 2) + math.floor(artifact.max_level / 4) - existing_unlocks - remaining_unlocks
        )

    total_rolls_high_chance = genshin_data.extra_substat_probability[source][artifact.stars]

    # Identify useful and condensable stats
    useful_stats = find_useful_stats(character=character, artifacts=equipped_artifacts)
    condensable_substats = [stat for stat in genshin_data.substat_roll_values.keys() if stat not in useful_stats]

    # Identify roll combinations
    substat_values_df, slot_potential_df = _make_children(
        stars=artifact.stars,
        main_stat=artifact.main_stat,
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
    artifact = type(artifact)(
        name="pseudo",
        set_str=artifact.set,
        main_stat=artifact.main_stat,
        stars=artifact.stars,
        level=artifact.max_level,
        substats=substat_values_df,
    )

    # Create artifact list, replacing previous artifact
    other_artifacts_list = [
        other_artifact for other_artifact in equipped_artifacts if type(other_artifact) != type(artifact)
    ]
    other_artifacts_list.append(artifact)
    other_artifacts = Artifacts(other_artifacts_list)

    # Calculate power
    power = power_calculator.evaluate_leveled_power(character=character, artifacts=other_artifacts)

    # Sort slot potnetial by power
    slot_potential_df["power"] = power
    slot_potential_df.sort_values("power", inplace=True)

    # Return results
    return slot_potential_df


def find_useful_stats(character: Character, artifacts: Artifacts):
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
