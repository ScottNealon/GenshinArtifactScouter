from __future__ import annotations

import numpy as np
import pandas as pd

from src import artifacts, character, genshin_data, potential


def evaluate_power(
    character: character.Character, artifacts: artifacts.Artifacts, stats: pd.DataFrame = None, leveled: bool = False
):
    """Evaluates the power of character with artifacts"""

    # Get stats
    if stats is None:
        stats = evaluate_stats(character=character, artifacts=artifacts, leveled=leveled)

    # ATK, DEF, or HP scaling
    scaling_stat_total = stats[f"total{character.scaling_stat.capitalize()}"]

    # Crit scaling
    if character.crits == "hit":
        crit_stat_value = 1
    elif character.crits == "critHit":
        crit_stat_value = 1 + stats["critDMG_"] / 100
    elif character.crits == "avgHit":
        stats[stats["critRate_"] > 100] = 100
        crit_stat_value = 1 + stats["critRate_"] / 100 * stats["critDMG_"] / 100

    # Damage or healing scaling
    if character.dmg_type in ["physical", "pyro", "hydro", "cryo", "electro", "anemo", "geo"]:
        dmg_stat_value = 1 + stats[f"{character.dmg_type}_dmg_"] / 100 + stats["dmg_"] / 100
    elif character.dmg_type == "healing":
        dmg_stat_value = 1 + stats["heal_"] / 100

    # Elemental mastery scaling
    if "eleMas" in stats:
        em_scaling_factor = 2.78 * stats["eleMas"] / (stats["eleMas"] + 1400)
        em_stat_value = (character.reaction_percentage / 100) * character.amplification_factor * (
            1 + em_scaling_factor
        ) + (1 - (character.reaction_percentage / 100))
    else:
        em_stat_value = 1

    # Power
    power = scaling_stat_total * crit_stat_value * dmg_stat_value * em_stat_value

    return power


def evaluate_stats(
    character: character.Character,
    artifacts: artifacts.Artifacts,
    leveled: bool = False,
    bonus_stats: dict[str, float] = None,
):
    # Agregate stats
    useful_stats = potential.find_useful_stats(character, artifacts)
    stats = pd.Series(0.0, index=useful_stats)
    stats = stats + character.get_stats(useful_stats)
    stats = stats + artifacts.get_stats(leveled, useful_stats)
    if bonus_stats is not None:
        for key, value in bonus_stats.items():
            if key in useful_stats:
                stats[key] = stats[key] + value
    # Calculate total stats
    for scaling_stat in ["hp", "atk", "def"]:
        if scaling_stat in useful_stats:
            stats[f"total{scaling_stat.capitalize()}"] = (
                stats[f"base{scaling_stat.capitalize()}"] * (1 + stats[f"{scaling_stat}_"] / 100) + stats[scaling_stat]
            )
    # Apply stat transformation
    old_stats = stats.copy()
    for source in [character, artifacts]:
        for destination_stat, source_stats in source.stat_transfer.items():
            if destination_stat in useful_stats:
                for source_stat, value in source_stats.items():
                    stats[destination_stat] = stats[destination_stat] + old_stats[source_stat] * value / 100
    return stats
