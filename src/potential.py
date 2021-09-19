from __future__ import annotations

import copy
import itertools
import json
import math
import os

import numpy as np
import pandas as pd

from src import genshin_data, power_calculator
from src.artifact import Artifact
from src.artifacts import Artifacts
from src.character import Character


def individual_potential(
    character: Character,
    equipped_artifacts: Artifacts,
    artifact: Artifact,
    source: str,
    ignore_substats: bool = False,
) -> pd.DataFrame:

    # Generate seed substats object
    seed_substats = {"substats": [], "probability": 1.0}
    if not ignore_substats:
        seed_substats["substats"] = [copy.deepcopy(substat) for substat in artifact.substats if substat["key"] != ""]
        current_level = artifact.level
    else:
        current_level = 0

    # Calculate number of unlocks and increases
    level_threasholds = math.ceil((artifact.max_level - current_level) / 4)
    if ignore_substats:
        starting_unlocks = max(0, artifact.stars - 2)
        leveling_unlocks = min(4 - starting_unlocks, level_threasholds)
        remaining_unlocks = starting_unlocks + leveling_unlocks - len(seed_substats["substats"])
        remaining_increases = level_threasholds - leveling_unlocks
        extra_substat_chance = genshin_data.extra_substat_probability[source] if ignore_substats else 0
    else:
        substats_unlocked = len(seed_substats["substats"])
        remaining_unlocks = min(level_threasholds, 4 - substats_unlocked)
        remaining_increases = level_threasholds - remaining_unlocks
        extra_substat_chance = 0

    # Identify useful and condensable stats
    useful_stats = find_useful_stats(character=character, artifacts=equipped_artifacts)
    condensable_substats = [stat for stat in genshin_data.substat_roll_values.keys() if stat not in useful_stats]

    # Identify roll combinations
    substat_instances_df = _make_children(
        stars=artifact.stars,
        main_stat=artifact.main_stat,
        remaining_unlocks=remaining_unlocks,
        remaining_increases=remaining_increases,
        extra_substat_chance=extra_substat_chance,
        seed_substats=seed_substats,
        condensable_substats=condensable_substats,
    )

    # Assign to artifact
    artifact = type(artifact)(
        setKey=artifact.set,
        rarity=artifact.stars,
        level=artifact.max_level,
        mainStatKey=artifact.main_stat,
        substats=substat_instances_df,
    )

    # Create artifact list, replacing previous artifact
    other_artifacts_list = [
        other_artifact for other_artifact in equipped_artifacts if type(other_artifact) != type(artifact)
    ]
    other_artifacts_list.append(artifact)
    other_artifacts = Artifacts(other_artifacts_list)

    # Calculate power
    power = power_calculator.evaluate_power(character=character, artifacts=other_artifacts, leveled=True)

    # Sort slot potnetial by power
    substat_instances_df["power"] = power
    substat_instances_df.sort_values("power", inplace=True)

    # Return results
    return substat_instances_df


def find_useful_stats(character: Character, artifacts: Artifacts):
    """Returns a list of substats that affect power calculation"""
    useful_stats = [
        f"base{character.scaling_stat.capitalize()}",
        f"{character.scaling_stat}",
        f"{character.scaling_stat}_",
        # f"total{character.scaling_stat.capitalize()}",
    ]
    if character.amplifying_reaction is not None:
        useful_stats.append("eleMas")
    if character.crits == "avgHit":
        useful_stats.append("critRate_")
        useful_stats.append("critDMG_")
    elif character.crits == "always":
        useful_stats.append("critDMG_")
    if character.dmg_type == "healing":
        useful_stats.append("heal_")
    else:
        useful_stats.append(f"{character.dmg_type}_dmg_")
        useful_stats.append("dmg_")
    # Transforming stats
    for destination_stat, source_stats in character.stat_transfer.items():
        if destination_stat in useful_stats:
            for source_stat in source_stats:
                useful_stats.append(source_stat)
                if "total" in source_stat:
                    source_stat_children = source_stat[7:]
                    useful_stats.append(f"base{source_stat_children.capitalize()}")
                    useful_stats.append(f"{source_stat_children}")
                    useful_stats.append(f"{source_stat_children}_")
    for destination_stat, source_stats in artifacts.stat_transfer.items():
        if destination_stat in useful_stats:
            for source_stat in source_stats:
                useful_stats.append(source_stat)
                if "Total" in source_stat:
                    source_stat_children = source_stat[7:]
                    useful_stats.append(f"base{source_stat_children.capitalize()}")
                    useful_stats.append(f"{source_stat_children}")
                    useful_stats.append(f"{source_stat_children}_")
    return useful_stats


def _make_children(
    stars: int,
    main_stat: str,
    remaining_unlocks: int,
    remaining_increases: int,
    extra_substat_chance: float,
    seed_substats: dict[str],
    condensable_substats: list[str],
) -> pd.DataFrame:

    # Get precalculated substat distribution
    # substat_distribution = genshin_data.substat_distributions[stars][remaining_unlocks][remaining_increases]

    # Calculate initial substat count
    initial_substats = len(seed_substats["substats"])

    # Create every possible substat instance by unlocking substats
    if remaining_unlocks > 0:
        substat_instances = _add_substats(
            seed_substats=seed_substats,
            remaining_unlocks=remaining_unlocks,
            main_stat=main_stat,
            condensable_substats=condensable_substats,
        )
    else:
        substat_instances = [seed_substats]

    substat_instances_df = _calculate_substat_rolls(
        substat_instances=substat_instances,
        stars=stars,
        remaining_unlocks=remaining_unlocks,
        remaining_increases=remaining_increases,
    )
    # Add extra unlocks, this should only occur for 2-star artifacts (you bloody weirdo)
    if extra_substat_chance > 0 and (initial_substats + remaining_unlocks == 4):
        substat_instances_extra_df = _calculate_substat_rolls(
            substat_instances=substat_instances,
            stars=stars,
            remaining_unlocks=remaining_unlocks,
            remaining_increases=remaining_increases + 1,
        )
        substat_instances_df["probability"] = substat_instances_df["probability"] * (1 - extra_substat_chance)
        substat_instances_extra_df["probability"] = substat_instances_extra_df["probability"] * extra_substat_chance
        substat_instances_df = pd.concat([substat_instances_df, substat_instances_extra_df], axis=0, ignore_index=True)

    return substat_instances_df


def _add_substats(
    seed_substats: dict[str], remaining_unlocks: int, main_stat: str, condensable_substats: list[str]
) -> list[dict]:
    """Creates substat instances with every possible combination of revealed substats"""

    # Generate list of possible substats
    valid_substats = set(genshin_data.substat_rarity[main_stat].keys())
    for substat in seed_substats["substats"]:
        valid_substats.remove(substat["key"])

    # Create list of possible substats
    base_probability = sum([genshin_data.substat_rarity[main_stat][substat] for substat in valid_substats])
    possibilities = []
    for substat in valid_substats:
        possibility = {
            "key": substat,
            "probability": genshin_data.substat_rarity[main_stat][substat] / base_probability,
        }
        possibilities.append(possibility)

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([possibility["probability"] for possibility in possibilities]) - 1) < 1e-6

    # Create all possible combinations of new substats
    combinations = tuple(itertools.combinations(possibilities, remaining_unlocks))

    # Iterate across combinations
    substat_instances = []
    for combination in combinations:

        # Create new substat instance
        substat_instance = copy.deepcopy(seed_substats)

        # Assign every new substat a single roll
        for substat in combination:
            substat_instance["substats"].append({"key": substat["key"], "value": 0.0})

        # Calculate probability of substat instance
        combination_probability = 0
        permutations = tuple(itertools.permutations(combination, len(combination)))
        for permutation in permutations:
            permutation_probability = 1
            remaining_probability = 1
            for substat in permutation:
                permutation_probability *= substat["probability"] / remaining_probability
                remaining_probability -= substat["probability"]
            combination_probability += permutation_probability
        substat_instance["probability"] = combination_probability

        # Consolodate substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
        artifact_condensable_substat_indices = [
            index
            for index, substat in enumerate(substat_instance["substats"])
            if substat["key"] in condensable_substats
        ]
        for num, index in enumerate(artifact_condensable_substat_indices):
            substat_instance["substats"][index]["key"] = f"condensed_{num}"
            substat_instance["substats"][index]["value"] = np.nan
        substat_instances.append(substat_instance)

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([possibility["probability"] for possibility in substat_instances]) - 1) < 1e-6

    # Return new substat instances
    return substat_instances


def _calculate_substat_rolls(
    substat_instances: list[dict[str]], stars: int, remaining_unlocks: int, remaining_increases: int
) -> pd.DataFrame:

    # Iterate through substat instances
    substat_instance_dfs = []
    num_instances = len(substat_instances)
    for substat_instance in substat_instances:

        existing_substats = [
            substat["key"]
            for substat in substat_instance["substats"]
            if "condensed" not in substat["key"] and substat["value"] != 0
        ]
        unlocked_substats = [
            substat["key"]
            for substat in substat_instance["substats"]
            if "condensed" not in substat["key"] and substat["value"] == 0
        ]

        num_unlocked_condensed = remaining_unlocks - len(unlocked_substats)
        num_existing_condensed = 4 - len(unlocked_substats) - len(existing_substats) - num_unlocked_condensed

        # Retrieve substat distribution
        substat_distribution = genshin_data.substat_distributions[stars][remaining_unlocks][remaining_increases][
            num_existing_condensed
        ][num_unlocked_condensed]

        # Create list of columns from substat names
        columns = existing_substats + unlocked_substats

        # Multiply distribution columns by maximum value substat roll can take
        max_roll_value = [genshin_data.substat_roll_values[column][stars][-1] for column in columns]
        stats = np.multiply(max_roll_value, substat_distribution["substats"])

        # Add substat initial values
        substat_values = [
            [substat["value"] for substat in substat_instance["substats"] if substat["key"] == substat_name][0]
            for substat_name in columns
        ]
        stats += substat_values

        # Create dataframe
        substat_instance_df = pd.DataFrame(stats, columns=columns)
        substat_instance_df["probability"] = substat_distribution["probability"] / num_instances

        # Append to list
        substat_instance_dfs.append(substat_instance_df)

    # Create composite dataframe
    substat_instances_dfs = pd.concat(substat_instance_dfs, axis=0, ignore_index=True).fillna(0)

    # TODO Find a faster way to do this

    # non_probability_columns = [column for column in substat_instances_dfs.columns if column != "probability"]

    # duplicates = substat_instances_dfs.duplicated(non_probability_columns)
    # unique_substat_instance_df: pd.DataFrame = substat_instances_dfs[~duplicates]

    # Iterate through duplicated rows, summing probability
    # for index, row in unique_substat_instance_df.iterrows():
    #     print(index)
    #     matches = (substat_instances_dfs[non_probability_columns] == row[non_probability_columns]).all(axis=1)
    #     unique_substat_instance_df.loc[index, "probability"] = substat_instances_dfs[matches]["probability"].sum()
    #     substat_instances_dfs.drop(substat_instances_dfs.index[matches])

    # Add remaining columns
    remaining_columns = [
        header for header in genshin_data.pandas_headers if header not in substat_instances_dfs.columns
    ]
    substat_instances_dfs[remaining_columns] = 0

    # Save as spare
    # substat_instances_dfs = substat_instances_dfs.astype(pd.SparseDtype("float", 0))

    return substat_instances_dfs
