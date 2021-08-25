from __future__ import annotations

import logging
import logging.config

import pandas as pd

from . import genshin_data
from .artifacts import Artifacts
from .character import Character
from .weapon import Weapon

log = logging.getLogger(__name__)


def evaluate_stats(character: Character, artifacts: Artifacts, *args):
    # Agregate stats
    stats = pd.Series(0.0, index=genshin_data.stat_names)
    stats = stats + character.stats
    stats = stats + artifacts.stats
    for arg in args:
        stats = stats + arg
    # Calculate total stats
    for stat in ["HP", "ATK", "DEF"]:
        stats[f"Total {stat}"] = stats[f"Base {stat}"] * (1 + stats[f"{stat}%"] / 100) + stats[stat]
    return stats


def evaluate_power(
    character: Character,
    stats: pd.DataFrame = None,
    artifacts: Artifacts = None,
    probability: pd.Series = None,
    verbose: bool = False,
):

    # Set verbosity
    if verbose:
        log.setLevel("INFO")
    else:
        log.setLevel("WARNING")

    # Log intro
    # fmt: off
    log.info("-" * 110)
    log.info("Evaluating power...")
    log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
    log.info(f"WEAPON: {character.weapon.name_formated.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
    if character.amplifying_reaction is not None:
        log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)")
    # fmt: on

    # Calculate overall stats if not provided
    if stats is None:
        stats = evaluate_stats(character=character, artifacts=artifacts)

    # Apply stat transformation
    for destination_stat, source_stats in character.stat_transfer.items():
        for source_stat, value in source_stats.items():
            stats[destination_stat] += stats[source_stat] * value / 100

    # ATK, DEF, or HP scaling
    scalling_stat_total = stats[f"Total {character.scaling_stat}"]

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
    power = scalling_stat_total * crit_stat_value * dmg_stat_value * em_stat_value

    # Log
    if type(power) is pd.Series:
        if probability is not None:
            log.info(f"MIN POWER: {power.min():,.0f}")
            log.info(f"AVG POWER: {power.dot(probability):,.0f}")
            log.info(f"MAX POWER: {power.max():,.0f}")
    else:
        log.info(f"POWER: {power:,.0f}")

    return power


# Example
if __name__ == "__main__":

    # Example setup
    character = Character(name="klee", level=90, ascension=6, passive={}, dmg_type="Elemental")
    weapon = Weapon(
        name="Dodoco Tales",
        level=90,
        ascension=6,
        passive={"DMG%": 32.0, "ATK%": 16.0},
    )
    artifacts = Artifacts([None, None, None, None, None])

    # Evaluate stats
    stats = evaluate_stats(character=character, weapon=weapon, artifacts=artifacts)

    # Evaluate power with example setup
    power_from_exampe = evaluate_power(character=character, weapon=weapon, artifacts=artifacts)

    # Evaluate power with stats
    power_from_stats = evaluate_power(character=character, stats=stats)

    assert power_from_exampe == power_from_stats
