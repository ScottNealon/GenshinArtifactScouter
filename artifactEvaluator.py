import copy
import math
from numpy.core.numeric import roll

import pandas as pd

import artifact as art
import character as char

_valid_main_stats = ['HP', 'ATK', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%', 'Elemental DMG%',
                    'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%']

_HP_substat_rarity = pd.Series({
    'HP':                0.15,
    'ATK':               0.15,
    'DEF':               0.15,
    'ATK%':              0.1,
    'DEF%':              0.1,
    'Energy Recharge%':  0.1,
    'Elemental Mastery': 0.1,
    'Crit Rate%':        0.075,
    'Crit DMG%':         0.075
})
_ATK_substat_rarity = pd.Series({
    'HP':                0.15,
    'ATK':               0.15,
    'DEF':               0.15,
    'HP%':               0.1,
    'DEF%':              0.1,
    'Energy Recharge%':  0.1,
    'Elemental Mastery': 0.1,
    'Crit Rate%':        0.075,
    'Crit DMG%':         0.075
})
_DEF_substat_rarity = pd.Series({
    'HP':                0.15,
    'ATK':               0.15,
    'DEF':               0.15,
    'HP%':               0.1,
    'ATK%':              0.1,
    'Energy Recharge%':  0.1,
    'Elemental Mastery': 0.1,
    'Crit Rate%':        0.075,
    'Crit DMG%':         0.075
})
_EM_substat_rarity = pd.Series({
    'HP':                0.15,
    'ATK':               0.15,
    'DEF':               0.15,
    'HP%':               0.1,
    'ATK%':              0.1,
    'DEF%':              0.1,
    'Energy Recharge%':  0.1,
    'Crit Rate%':        0.075,
    'Crit DMG%':         0.075
})
_unrelated_substat_rarity = pd.Series({
    'HP':                0.1364,
    'ATK':               0.1364,
    'DEF':               0.1364,
    'HP%':               0.0909,
    'ATK%':              0.0909,
    'DEF%':              0.0909,
    'Energy Recharge%':  0.0909,
    'Crit Rate%':        0.0682,
    'Crit DMG%':         0.0682
})

_substat_rarity = {
    'flower': {
        'HP': {
            'ATK':               0.1579,
            'DEF':               0.1579,
            'HP%':               0.1053,
            'ATK%':              0.1053,
            'DEF%':              0.1053,
            'Energy Recharge%':  0.1053,
            'Elemental Mastery': 0.1053,
            'Crit Rate%':        0.0789,
            'Crit DMG%':         0.0789
        }
    },
    'plume': {
        'ATK': {
            'HP':                0.1579,
            'DEF':               0.1579,
            'HP%':               0.1053,
            'ATK%':              0.1053,
            'DEF%':              0.1053,
            'Energy Recharge%':  0.1053,
            'Elemental Mastery': 0.1053,
            'Crit Rate%':        0.0789,
            'Crit DMG%':         0.0789
        }
    },
    'sands': {
        'HP%': _HP_substat_rarity,
        'ATK%': _ATK_substat_rarity,
        'DEF%': _DEF_substat_rarity,
        'Energy Recharge%': pd.Series({
            'HP':                0.15,
            'ATK':               0.15,
            'DEF':               0.15,
            'HP%':               0.1,
            'ATK%':              0.1,
            'DEF%':              0.1,
            'Elemental Mastery': 0.1,
            'Crit Rate%':        0.075,
            'Crit DMG%':         0.075
        }),
        'Elemental Mastery': _EM_substat_rarity
    },
    'goblet': {
        'HP%': _HP_substat_rarity,
        'ATK%': _ATK_substat_rarity,
        'DEF%': _DEF_substat_rarity,
        'Elemental DMG%': _unrelated_substat_rarity,
        'Physical DMG%': _unrelated_substat_rarity,
        'Elemental Mastery': _EM_substat_rarity
    },
    'circlet': {
        'HP%': _HP_substat_rarity,
        'ATK%': _ATK_substat_rarity,
        'DEF%': _DEF_substat_rarity,
        'Crit Rate%': pd.Series({
            'HP':                0.1463,
            'ATK':               0.1463,
            'DEF':               0.1463,
            'HP%':               0.0976,
            'ATK%':              0.0976,
            'DEF%':              0.0976,
            'Energy Recharge%':  0.0976,
            'Elemental Mastery': 0.0976,
            'Crit DMG%':         0.0732
        }),
        'Crit DMG%':  pd.Series({
            'HP':                0.1463,
            'ATK':               0.1463,
            'DEF':               0.1463,
            'HP%':               0.0976,
            'ATK%':              0.0976,
            'DEF%':              0.0976,
            'Energy Recharge%':  0.0976,
            'Elemental Mastery': 0.0976,
            'Crit Rate%':        0.0732
        }),
        'Healing Bonus%': _unrelated_substat_rarity,
        'Elemental Mastery': _EM_substat_rarity
    }
}

def evaluate_artifact(character: char.Character, artifact: art.Artifact, target_level: int):

    # Validate inputs
    if target_level < artifact.level:
        raise ValueError('Target level cannot be less than artifact level')

    # Number of substats to be unlocked
    remaining_unlocks = min(4 - len(artifact.substats), math.floor(target_level / 4) - math.floor(artifact.level / 4))

    # Number of substats to be increased
    remaining_increases = math.floor(target_level / 4) - math.floor(artifact.level / 4) - remaining_unlocks

    # Identify possible roll combinations
    previous_generation = [{'substats': {}, 'probability':1.0}]
    for substat in artifact.substats:
        previous_generation[0]['substats'][substat] = []
    roll_combinations = make_children(character=character, artifact=artifact, previous_generation=previous_generation, remaining_unlocks=remaining_unlocks, remaining_increases=remaining_increases, target_level=target_level)

    # Simulate artifacts

    for roll_combination in roll_combinations:
        artifact_slot = type(artifact)
        pseduo_artifact = artifact_slot(set=artifact.set, main_stat=artifact.main_stat, stars=artifact.stars, level=target_level, substats=copy.copy(artifact.substats))
        #copy.deepcopy(artifact)
        #pseduo_artifact.level = target_level

        for substat, substat_rolls in roll_combination['substats'].items():
            if substat not in pseduo_artifact.substats.keys():
                pseduo_artifact.add_substat(substat, 0)
            for roll in substat_rolls:
                pseduo_artifact.roll_substat(substat, roll)
        character.set_artifact(pseduo_artifact)
        power = character.power
        roll_combination['power'] = power

    return roll_combinations


def make_children(character: char.Character, artifact: art.Artifact, previous_generation: list[dict], remaining_unlocks: int, remaining_increases: int, target_level: int) -> list[dict]:

    new_generation = {}
    if remaining_unlocks > 0:
        for previous_individual in previous_generation:

            # Generate list of possible substats
            valid_substats = list(_substat_rarity[artifact.slot][artifact.main_stat].keys())
            for substat in previous_individual['substats']:
                valid_substats.remove(substat)

            # Consolodate substats
            valid_substats, simplified_substat_rarity, condensed_substat = _consolodate_substats(character=character, artifact=artifact, valid_substats=valid_substats)

            # Generate all substat rolls
            for substat in valid_substats:
                if substat == condensed_substat:
                    possible_substat_rolls = 1
                else:
                    possible_substat_rolls = min(1 + artifact.stars, 4)
                for substat_roll in range(possible_substat_rolls):
                    # Create new individual
                    new_individual = copy.deepcopy(previous_individual)
                    new_individual['substats'][substat] = [substat_roll]
                    new_individual['substats'] = dict(sorted(new_individual['substats'].items()))
                    # Determine probability of artifact
                    base_probability = 1
                    for old_substat in artifact.substats:
                        base_probability -= simplified_substat_rarity[old_substat]
                    substat_roll_probability = (1/possible_substat_rolls) * simplified_substat_rarity[substat] / base_probability
                    new_individual['probability'] *= substat_roll_probability
                    # Add to generation
                    key = str(new_individual['substats'])
                    if key not in new_generation:
                        new_generation[key] = new_individual
                    else:
                        new_generation[key]['probability'] += new_individual['probability']
        
        next_generation = make_children(character=character, artifact=artifact, previous_generation=list(new_generation.values()), remaining_unlocks=remaining_unlocks - 1, remaining_increases=remaining_increases, target_level=target_level)

    elif remaining_increases > 0:
        for previous_individual in previous_generation:

            # Consolodate substats
            valid_substats = list(previous_individual['substats'].keys())
            valid_substats, simplified_substat_rarity, condensed_substat = _consolodate_substats(character=character, artifact=artifact, valid_substats=valid_substats)

            for substat in valid_substats:
                if substat == condensed_substat:
                    possible_substat_rolls = 1
                else:
                    possible_substat_rolls = min(1 + artifact.stars, 4)
                for substat_roll in range(possible_substat_rolls):
                    # Create new individual
                    new_individual = copy.deepcopy(previous_individual)
                    new_individual['substats'][substat].append(substat_roll)
                    new_individual['substats'][substat].sort()
                    # Determine probability of artifact
                    substat_roll_probability = (1/possible_substat_rolls) * 0.25
                    new_individual['probability'] *= substat_roll_probability
                    # Add to generation
                    key = str(new_individual['substats'])
                    if key not in new_generation:
                        new_generation[key] = new_individual
                    else:
                        new_generation[key]['probability'] += new_individual['probability']

        next_generation = make_children(character=character, artifact=artifact, previous_generation=list(new_generation.values()), remaining_unlocks=remaining_unlocks, remaining_increases=remaining_increases - 1, target_level=target_level)

    else:
        next_generation = previous_generation
    
    return next_generation


# def make_children(character: char.Character, artifact: art.Artifact, remaining_unlocks: int, remaining_increases: int, target_level: int, probability: float = None) -> list[dict]:

#     if probability is None:
#         probability = 1

#     children_artifacts = []

#     if remaining_unlocks > 0:

#         # Generate list of possible substats
#         valid_substats = list(_substat_rarity[artifact.slot][artifact.main_stat].keys())
#         for substat in artifact.substats:
#             valid_substats.remove(substat.stat)

#         # Consolodate substats
#         valid_substats, simplified_substat_rarity, condensed_substat = _consolodate_substats(character=character, artifact=artifact, valid_substats=valid_substats)

#         # Generate all possible children artifacts
#         for substat in valid_substats:
#             if substat == condensed_substat:
#                 possible_substat_rolls = 1
#             else:
#                 possible_substat_rolls = min(1 + artifact.stars, 4)
#             for substat_roll in range(possible_substat_rolls):
#                 # Create new artifact
#                 new_artifact = copy.copy(artifact)
#                 new_artifact.level = 4 * math.ceil(new_artifact.level / 4 + 1e-6)
#                 new_artifact.new_substat(substat, substat_roll)
#                 # Determine probability of artifact
#                 base_probability = 1
#                 for old_substat in artifact.substats:
#                     base_probability -= simplified_substat_rarity[old_substat.stat]
#                 substat_roll_probability = (1/possible_substat_rolls) * simplified_substat_rarity[substat] / base_probability
#                 new_probability = probability * substat_roll_probability
#                 # Recursion
#                 results = make_children(character=character, artifact=new_artifact, remaining_unlocks=remaining_unlocks - 1, remaining_increases=remaining_increases, target_level=target_level, probability=new_probability)
#                 children_artifacts.extend(results)

#     elif remaining_increases > 0:

#         valid_substats = []
#         for substat in artifact.substats:
#             valid_substats.append(substat.stat)

#         # Consolodate substats
#         valid_substats, simplified_substat_rarity, condensed_substat = _consolodate_substats(character=character, artifact=artifact, valid_substats=valid_substats)

#         substat_increases = {}
#         for valid_substat in valid_substats:
#             substat_increases[valid_substat] = []

#         substat_increases = _all_substat_increases(substat_increases=substat_increases, artifact=artifact, remaining_increases=remaining_increases, probability=probability, simplified_substat_rarity=simplified_substat_rarity, condensed_substat=condensed_substat)

#         for (ind, substat) in enumerate(artifact.substats):
#             if substat == condensed_substat:
#                 possible_substat_rolls = 1
#             else:
#                 possible_substat_rolls = min(1 + artifact.stars, 4)
#             for substat_roll in range(possible_substat_rolls):
#                 # Create new artifact
#                 new_artifact = copy.copy(artifact)
#                 new_artifact.level = 4 * math.ceil(new_artifact.level / 4 + 1e-6)
#                 new_artifact.increase_substat(ind=ind, roll=substat_roll)
#                 # Determine probability of artifact
#                 substat_roll_probability = (1/possible_substat_rolls) * 0.25
#                 new_probability = probability * substat_roll_probability
#                 # Recursion
#                 results = make_children(character=character, artifact=new_artifact, remaining_unlocks=remaining_unlocks, remaining_increases=remaining_increases - 1, target_level=target_level, probability=new_probability)
#                 children_artifacts.extend(results)

#     else:

#         new_artifact = copy.copy(artifact)
#         new_artifact.level = target_level

#         # Calculate power
#         character.artifact = new_artifact
#         artifact_power = character.power

#         # Return
#         children_artifacts = [{
#             'probability': probability,
#             #'artifact': new_artifact
#             'power': artifact_power
#             }]
        
#     return children_artifacts


def _consolodate_substats(character: char.Character, artifact: art.Artifact, valid_substats: list[str]):

    # Simplify list to consolidate unused stats
    simplified_substat_rarity = copy.copy(_substat_rarity[artifact.slot][artifact.main_stat])
    if character.scaling_stat == 'ATK':
        simplified_substats = ['DEF', 'DEF%', 'HP', 'HP%']
    elif character.scaling_stat == 'DEF':
        simplified_substats = ['ATK', 'ATK%', 'HP', 'HP%']
    elif character.scaling_stat == 'HP':
        simplified_substats = ['ATK', 'ATK%', 'DEF', 'DEF%']

    simplified_substats.append('Energy Recharge%')
    if character.amplifying_reaction is None:
        simplified_substats.append('Elemental Mastery')

    if character.crits == 'always':
        simplified_substats.append('Crit Rate%')
    elif character.crits == 'never':
        simplified_substats.append('Crit Rate%')
        simplified_substats.append('Crit DMG%')

    # Determine condensed substat (first valid one in list)'
    condensed_substat = None
    for simplified_substat in simplified_substats:
        if simplified_substat in valid_substats:
            condensed_substat = simplified_substat
            break

    # Remove other substats
    for simplified_substat in simplified_substats:
        if simplified_substat in valid_substats:
            if simplified_substat != condensed_substat:
                simplified_substat_rarity[condensed_substat] += simplified_substat_rarity[simplified_substat]
                del simplified_substat_rarity[simplified_substat]
                valid_substats.remove(simplified_substat)

    return valid_substats, simplified_substat_rarity, condensed_substat

# def _all_substat_increases(substat_increases: dict[str], artifact: art.Artifact, remaining_increases: int, probability: int, simplified_substat_rarity: dict[str], condensed_substat: str) -> list[dict]:

#     all_substat_increases = []

#     if remaining_increases > 0:

#         for substat in substat_increases:
#             if substat == condensed_substat:
#                 possible_substat_rolls = 1
#             else:
#                 possible_substat_rolls = min(1 + artifact.stars, 4)
#             for substat_roll in range(possible_substat_rolls):
#                 new_substat_increases = copy.copy(substat_increases)
#                 new_substat_increases[substat].append(substat_roll)
#                 new_probability = probability * simplified_substat_rarity[substat]
#                 result = _all_substat_increases(substat_increases=new_substat_increases, artifact=artifact.stars, probability=new_probability, simplified_substat_rarity=simplified_substat_rarity, condensed_substat=condensed_substat)
#                 all_substat_increases.extend(result)

#     return all_substat_increases