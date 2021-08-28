from __future__ import annotations

import logging
import logging.config

import pandas as pd

from . import genshin_data
from .artifacts import Artifacts
from .character import Character


def evaluate_power(character: Character, artifacts: Artifacts):
    """Evaluates the current power of character with artifacts"""
    stats = evaluate_stats(character=character, artifacts=artifacts)
    power = _evaluate_power(character=character, stats=stats)
    return power


def evaluate_leveled_power(character: Character, artifacts: Artifacts):
    """Evalautes the future power of character with artifacts"""
    stats = evaluate_leveled_stats(character=character, artifacts=artifacts)
    power = _evaluate_power(character=character, stats=stats)
    return power


def evaluate_stats(character: Character, artifacts: Artifacts):
    # Agregate stats
    stats = pd.Series(0.0, index=genshin_data.pandas_headers)
    stats = stats + character.stats
    stats = stats + artifacts.stats
    # Calculate total stats
    for stat in ["HP", "ATK", "DEF"]:
        stats[f"Total {stat}"] = stats[f"Base {stat}"] * (1 + stats[f"{stat}%"] / 100) + stats[stat]
    # Apply stat transformation
    old_stats = stats.copy()
    for destination_stat, source_stats in character.stat_transfer.items():
        for source_stat, value in source_stats.items():
            stats[destination_stat] += old_stats[source_stat] * value / 100
    for destination_stat, source_stats in artifacts.stat_transfer.items():
        for source_stat, value in source_stats.items():
            stats[destination_stat] += old_stats[source_stat] * value / 100
    return stats


def evaluate_leveled_stats(character: Character, artifacts: Artifacts):
    # Agregate stats
    stats = pd.Series(0.0, index=genshin_data.pandas_headers)
    stats = stats + character.stats
    stats = stats + artifacts.leveled_stats
    # Calculate total stats
    for stat in ["HP", "ATK", "DEF"]:
        stats[f"Total {stat}"] = stats[f"Base {stat}"] * (1 + stats[f"{stat}%"] / 100) + stats[stat]
    # Apply stat transformation
    for destination_stat, source_stats in character.stat_transfer.items():
        for source_stat, value in source_stats.items():
            stats[destination_stat] += stats[source_stat] * value / 100
    return stats


def _evaluate_power(character: Character, stats: pd.Series) -> float:

    # ATK, DEF, or HP scaling
    scaling_stat_total = stats[f"Total {character.scaling_stat}"]

    # Crit scaling
    if character.crits == "hit":
        crit_stat_value = 1
    elif character.crits == "critHit":
        crit_stat_value = 1 + stats["Crit DMG%"] / 100
    elif character.crits == "avgHit":
        stats[stats["Crit Rate%"] > 100] = 100
        crit_stat_value = 1 + stats["Crit Rate%"] / 100 * stats["Crit DMG%"] / 100

    # Damage or healing scaling
    if character.dmg_type in ["physical", "pyro", "hydro", "cryo", "electro", "anemo", "geo"]:
        dmg_stat_value = 1 + stats[f"{character.dmg_type.capitalize()} DMG%"] / 100 + stats["DMG%"] / 100
    elif character.dmg_type == "healing":
        dmg_stat_value = 1 + stats["Healing Bonus%"] / 100

    # Elemental Mastery scaling
    em_scaling_factor = 2.78 * stats["Elemental Mastery"] / (stats["Elemental Mastery"] + 1400)
    em_stat_value = (character.reaction_percentage / 100) * character.amplification_factor * (1 + em_scaling_factor) + (
        1 - (character.reaction_percentage / 100)
    )

    # Power
    power = scaling_stat_total * crit_stat_value * dmg_stat_value * em_stat_value

    return power
