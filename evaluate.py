import logging
import logging.config
import os

import pandas as pd

import artifacts as arts
import character as char
import genshindata as gd
import weapon as weap

log = logging.getLogger(__name__)


def evaluate_stats(character: char.Character, weapon: weap.Weapon, artifacts: arts.Artifacts, *args):
    stats = pd.Series(0.0, index=gd.stat_names)
    stats = stats + character.base_stats
    stats = stats + weapon.stats
    stats = stats + artifacts.stats
    for arg in args:
        stats = stats + arg
    return stats


def evaluate_power(
    character: char.Character,
    stats: pd.DataFrame = None,
    weapon: weap.Weapon = None,
    artifacts: arts.Artifacts = None,
    probability: pd.Series = None,
    verbose: bool = False,
):

    # Set verbosity
    if verbose:
        log.setLevel("INFO")
    else:
        log.setLevel("WARNING")

    log.info("-" * 120)
    log.info("Evaluating power...")
    log.info(f"CHARACTER: {character.name.title()}")
    if weapon is not None:
        log.info(f"WEAPON: {weapon.name.title()}")
    if character.amplifying_reaction is not None:
        log.info(
            f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({100 * character.reaction_percentage::>.0f}%)"
        )

    # Calculate overall stats if not provided
    if stats is None:
        stats = evaluate_stats(character=character, weapon=weapon, artifacts=artifacts)

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
            log.info(f"MIN POWER: {power.min():,.2f}")
            log.info(f"AVG POWER: {power.dot(probability):,.2f}")
            log.info(f"MAX POWER: {power.max():,.2f}")
    else:
        log.info(f"POWER: {power:,.2f}")

    return power


# Example
if __name__ == "__main__":

    # Example setup
    character = char.Character(name="klee", level=90, ascension=6, passive={}, dmg_type="Elemental")
    weapon = weap.Weapon(
        name="Dodoco Tales",
        level=90,
        baseATK=454,
        ascension_stat="ATK%",
        ascension_stat_value=55.1,
        passive={"DMG%": 32.0, "ATK%": 16.0},
    )
    artifacts = arts.Artifacts([None, None, None, None, None])

    # Evaluate stats
    stats = evaluate_stats(character=character, weapon=weapon, artifacts=artifacts)

    # Evaluate power with example setup
    power_from_exampe = evaluate_power(character=character, weapon=weapon, artifacts=artifacts)

    # Evaluate power with stats
    power_from_stats = evaluate_power(character=character, stats=stats)

    assert power_from_exampe == power_from_stats
