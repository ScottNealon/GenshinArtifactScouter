import logging
import logging.config

import pandas as pd

import genshindata
from artifacts import Artifacts
from character import Character
from weapon import Weapon

log = logging.getLogger(__name__)


def evaluate_stats(character: Character, artifacts: Artifacts, *args):
    stats = pd.Series(0.0, index=genshindata.stat_names)
    stats = stats + character.stats
    stats = stats + artifacts.stats
    for arg in args:
        stats = stats + arg
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
    log.info("-" * 120)
    log.info("Evaluating power...")
    log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
    log.info(f"WEAPON: {character.weapon.name_formated.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
    if character.amplifying_reaction is not None:
        log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({100 * character.reaction_percentage::>.0f}%)")
    # fmt: on

    # Calculate overall stats if not provided
    if stats is None:
        stats = evaluate_stats(character=character, artifacts=artifacts)

    # ATK, DEF, or HP scaling
    scaling_stat_base = stats["Base " + character.scaling_stat]
    scaling_stat_flat = stats[character.scaling_stat]
    scaling_stat_percent = stats[character.scaling_stat + "%"] / 100
    scaling_stat_value = scaling_stat_base * (1 + scaling_stat_percent) + scaling_stat_flat

    # Crit scaling
    if character.crits == "hit":
        crit_stat_value = 1
    elif character.crits == "critHit":
        crit_stat_value = 1 + stats["Crit DMG%"] / 100
    elif character.crits == "avgHit":
        stats[stats["Crit Rate%"] > 100] = 100
        crit_stat_value = 1 + stats["Crit Rate%"] / 100 * stats["Crit DMG%"] / 100

    # Damage or healing scaling
    if character.dmg_type == "Physical":
        dmg_stat_value = 1 + stats["Physical DMG%"] / 100 + stats["DMG%"] / 100
    elif character.dmg_type == "Elemental":
        dmg_stat_value = 1 + stats["Elemental DMG%"] / 100 + stats["DMG%"] / 100
    elif character.dmg_type == "Healing":
        dmg_stat_value = 1 + stats["Healing Bonus%"] / 100

    # Elemental Mastery scaling
    em_scaling_factor = 2.78 * stats["Elemental Mastery"] / (stats["Elemental Mastery"] + 1400)
    em_stat_value = character.reaction_percentage * character.amplification_factor * (1 + em_scaling_factor) + (
        1 - character.reaction_percentage
    )

    # Power
    power = scaling_stat_value * crit_stat_value * dmg_stat_value * em_stat_value

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
