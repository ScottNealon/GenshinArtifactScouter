import pandas as pd

import artifact as art
import artifacts as arts
import character as char
import weapon as weap

# TODO Move all these constants to a constant module
_stat_names = ['Base HP', 'Base ATK', 'Base DEF', 'HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%',
                   'Elemental DMG%', 'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%']

# TODO Use dimentionality to do all calculations simultaneously
def evaluate_stats(character: char.Character, weapon: weap.Weapon, artifacts: arts.Artifacts):
        stats = pd.Series(0.0, index=_stat_names)
        stats += character._baseStats
        stats += weapon.stats
        stats += artifacts.stats
        return stats

def evaluate_power(character: char.Character, weapon: weap.Weapon, artifacts: arts.Artifacts):

    # Calculate overall stats
    stats = evaluate_stats(character=character, weapon=weapon, artifacts=artifacts)

    # ATK, DEF, or HP scaling
    scaling_stat_base = stats['Base ' + character.scaling_stat]
    scaling_stat_flat = stats[character.scaling_stat]
    scaling_stat_percent = stats[character.scaling_stat + '%']/100
    scaling_stat_value = scaling_stat_base * (1 + scaling_stat_percent) + scaling_stat_flat

    # Crit scaling
    if character.crits == 'never':
        crit_stat_value = 1
    elif character.crits == 'always':
        crit_stat_value = 1 + stats['Crit DMG%']/100
    elif character.crits == 'average':
        crit_stat_value = 1 + min(1, stats['Crit Rate%']/100) * stats['Crit DMG%']/100

    # Damage or healing scaling
    if character.dmg_type == 'Physical':
        dmg_stat_value = 1 + stats['Physical DMG%']/100 + stats['DMG%']/100
    elif character.dmg_type == 'Elemental':
        dmg_stat_value = 1 + stats['Elemental DMG%']/100 + stats['DMG%']/100
    elif character.dmg_type == 'Healing':
        dmg_stat_value = 1 + stats['Healing Bonus%']/100

    # Elemental Master scaling
    em_stat_value = (1 - character.reaction_percentage) + \
        character.reaction_percentage * character.amplification_factor * (1 + 2.78 * stats['Elemental Mastery'] / (stats['Elemental Mastery'] + 1400))

    # Power
    power = scaling_stat_value * crit_stat_value * dmg_stat_value * em_stat_value
    return power