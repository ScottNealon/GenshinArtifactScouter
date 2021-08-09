import logging

import pandas as pd

import artifacts as arts
import character as char
import weapon as weap

# TODO Move all these constants to a constant module
_stat_names = ['Base HP', 'Base ATK', 'Base DEF', 'HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%',
                   'Elemental DMG%', 'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%', 'probability']

log = logging.getLogger(__name__)

def evaluate_stats(character: char.Character, weapon: weap.Weapon, artifacts: arts.Artifacts, *args):
        stats = pd.Series(0.0, index=_stat_names)
        stats = stats + character.base_stats
        stats = stats + weapon.stats
        stats = stats + artifacts.stats
        for arg in args:
            stats = stats + arg
        return stats

def evaluate_power(character: char.Character, stats: pd.DataFrame = None, weapon: weap.Weapon = None, artifacts: arts.Artifacts = None, verbose: bool = False):

    if verbose:
        log.info('-' * 90)
        log.info('Evaluating power...')
        log.info(f'Character: {character}')
        log.info(f'Weapon: {weapon}')

    # Calculate overall stats if not provided
    if stats is None:
        stats = evaluate_stats(character=character, weapon=weapon, artifacts=artifacts)

    # ATK, DEF, or HP scaling
    scaling_stat_base = stats['Base ' + character.scaling_stat]
    scaling_stat_flat = stats[character.scaling_stat]
    scaling_stat_percent = stats[character.scaling_stat + '%']/100
    scaling_stat_value = scaling_stat_base * (1 + scaling_stat_percent) + scaling_stat_flat

    # Crit scaling
    if character.crits == 'hit':
        crit_stat_value = 1
    elif character.crits == 'critHit':
        crit_stat_value = 1 + stats['Crit DMG%']/100
    elif character.crits == 'avgHit':
        stats[stats['Crit Rate%'] > 100] = 100
        crit_stat_value = 1 + stats['Crit Rate%']/100 * stats['Crit DMG%']/100

    # Damage or healing scaling
    if character.dmg_type == 'Physical':
        dmg_stat_value = 1 + stats['Physical DMG%']/100 + stats['DMG%']/100
    elif character.dmg_type == 'Elemental':
        dmg_stat_value = 1 + stats['Elemental DMG%']/100 + stats['DMG%']/100
    elif character.dmg_type == 'Healing':
        dmg_stat_value = 1 + stats['Healing Bonus%']/100

    # Elemental Mastery scaling
    em_stat_value = (1 - character.reaction_percentage) + \
        character.reaction_percentage * character.amplification_factor * (1 + 2.78 * stats['Elemental Mastery'] / (stats['Elemental Mastery'] + 1400))

    # Power
    power = scaling_stat_value * crit_stat_value * dmg_stat_value * em_stat_value

    # Log
    if verbose:
        log.info(f'Power: {power:,.2f}')

    return power