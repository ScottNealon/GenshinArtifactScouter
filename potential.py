import copy
import itertools
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import artifact as art
import artifacts as arts
import character as char
import evaluate as eval
import weapon as weap

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

def artifact_potential(character: char.Character, weapon: weap.Weapon, artifacts: arts.Artifacts, artifact: art.Artifact, target_level: int) -> list[dict]:

    # Validate inputs
    if target_level < artifact.level:
        raise ValueError('Target level cannot be less than artifact level')

    # Identify possible roll combinations
    artifact_potentials = make_children(character=character, artifact=artifact, target_level=target_level)

    # List of other artifacts that are not of the same type as primary artifact
    other_artifacts_list = [other_artifact for other_artifact in artifacts.get_artifacts() if type(other_artifact) != type(artifact)]

    # Simulate artifacts
    for artifact_potential in artifact_potentials:
        # Create new artifact
        artifact_slot = type(artifact)
        substats = copy.deepcopy(artifact.substats)
        test_artifact = artifact_slot(set=artifact.set, main_stat=artifact.main_stat, stars=artifact.stars, level=target_level, substats=substats)
        # Update substats
        for substat, substat_rolls in artifact_potential['substats'].items():
            if substat not in test_artifact.substats.keys():
                test_artifact.add_substat(substat, 0)
            for roll in substat_rolls:
                test_artifact.roll_substat(substat, roll)
        # Create new artifact collection
        test_artifacts = arts.Artifacts(test_artifact, *other_artifacts_list)
        # Calculate power
        power = eval.evaluate_power(character=character, weapon=weapon, artifacts=test_artifacts)
        artifact_potential['power'] = power

    return artifact_potentials

def make_children(character: char.Character, artifact: art.Artifact, target_level: int):
    
    # Creates initial pseudo-artifact
    pseudo_artifacts = [{'substats': {}, 'probability':1.0}]
    for substat in artifact.substats:
        pseudo_artifacts[0]['substats'][substat] = []

    # Number of substats to be unlocked
    remaining_unlocks = min(4 - len(artifact.substats), math.floor(target_level / 4) - math.floor(artifact.level / 4))
    if remaining_unlocks > 0:

        # Create new pseudo artifact dict
        new_pseudo_artifacts = {}

        # Generate list of possible substats
        valid_substats = list(_substat_rarity[artifact.slot][artifact.main_stat].keys())
        for substat in pseudo_artifacts[0]['substats']:
            valid_substats.remove(substat)

        # Consolodate similar substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
        valid_substats, simplified_substat_rarity, condensed_substat = _consolodate_substats(character=character, artifact=artifact, valid_substats=valid_substats)
        base_probability = sum([simplified_substat_rarity[substat] for substat in valid_substats])

        # Create list of possibilities
        possibilities = []
        for substat in valid_substats:
            if substat == condensed_substat:
                possible_substat_rolls = 1
            else:
                possible_substat_rolls = min(1 + artifact.stars, 4)
            for substat_roll in range(possible_substat_rolls):
                possibility = {
                    'substat': substat,
                    'substat_roll': substat_roll,
                    'probability': (1/possible_substat_rolls) * simplified_substat_rarity[substat] / base_probability,
                    'possible_substat_rolls': possible_substat_rolls
                }
                possibilities.append(possibility)

        # Verify probability math (sum of probabilities is almost 1)
        assert abs(sum([possibility['probability'] for possibility in possibilities]) - 1) < 1e-6

        # Iterate acorss possibilities
        permutations = list(itertools.permutations(possibilities, remaining_unlocks))
        for permutation in permutations:

            # Check if permutation has duplicate substats. If so, skip.
            substats = [possibility['substat'] for possibility in permutation]
            if len(substats) > len(set(substats)):
                continue

            # Create new pseudo artifact
            pseudo_artifact = copy.deepcopy(pseudo_artifacts[0])
            # Calculate probability of pseudo artifact
            base_probability_reduction = 1
            for possibility in permutation:
                pseudo_artifact['substats'][possibility['substat']] = [possibility['substat_roll']]
                pseudo_artifact['probability'] *= possibility['probability'] / base_probability_reduction
                base_probability_reduction -= possibility['probability'] * possibility['possible_substat_rolls']
            # Add pseudo artifact to dict
            pseudo_artifact['substats'] = dict(sorted(pseudo_artifact['substats'].items())) # sort keys
            key = str(pseudo_artifact['substats'])
            if key not in new_pseudo_artifacts:
                new_pseudo_artifacts[key] = pseudo_artifact
            else:
                new_pseudo_artifacts[key]['probability'] += pseudo_artifact['probability']
            
        # Return overwrite pseudo_artifacts
        pseudo_artifacts = [pseudo_artifact for pseudo_artifact in new_pseudo_artifacts.values()]

        # Verify probability math (sum of probabilities is almost 1)
        assert abs(sum([possibility['probability'] for possibility in pseudo_artifacts]) - 1) < 1e-6

    # Number of substats to be increased
    remaining_increases = math.floor(target_level / 4) - math.floor(artifact.level / 4) - remaining_unlocks
    if remaining_increases > 0:

        # Create new pseudo artifact dict
        new_pseudo_artifacts = {}

        # Iterate over existing pseudo artifacts
        for pseudo_artifact in pseudo_artifacts:

            # Consolodate substats
            valid_substats = list(pseudo_artifact['substats'].keys())
            valid_substats, _, condensed_substat = _consolodate_substats(character=character, artifact=artifact, valid_substats=valid_substats)

            # Create list of possibilities
            possibilities = []
            for substat in valid_substats:
                if substat == condensed_substat:
                    possible_substat_rolls = 1
                    substat_possibility = (5 - len(valid_substats)) / 4
                else:
                    possible_substat_rolls = min(1 + artifact.stars, 4)
                    substat_possibility = 0.25
                for substat_roll in range(possible_substat_rolls):
                    possibility = {
                        'substat': substat,
                        'substat_roll': substat_roll,
                        'probability': (1/possible_substat_rolls) * substat_possibility
                    }
                    possibilities.append(possibility)

            # Verify probability math (sum of probabilities is almost 1)
            assert abs(sum([possibility['probability'] for possibility in possibilities]) - 1) < 1e-6

            # Iterate acorss possibilities, creating new pseudo artifacts
            products = itertools.product(possibilities, repeat=remaining_increases)
            for product in products:

                # Create new pseudo artifact
                new_pseudo_artifact = copy.deepcopy(pseudo_artifact)
                # Calculate probability of pseudo artifact
                for possibility in product:
                    new_pseudo_artifact['substats'][possibility['substat']].append(possibility['substat_roll'])
                    new_pseudo_artifact['substats'][possibility['substat']].sort() # sort rolls within substat
                    new_pseudo_artifact['probability'] *= possibility['probability']
                # Add pseudo artifact to dict
                new_pseudo_artifact['substats'] = dict(sorted(new_pseudo_artifact['substats'].items())) # sort keys
                key = str(new_pseudo_artifact['substats'])
                if key not in new_pseudo_artifacts:
                    new_pseudo_artifacts[key] = new_pseudo_artifact
                else:
                    new_pseudo_artifacts[key]['probability'] += new_pseudo_artifact['probability']
    
        # Return overwrite pseudo_artifacts
        pseudo_artifacts = [pseudo_artifact for pseudo_artifact in new_pseudo_artifacts.values()]

        # Verify probability math (sum of probabilities is almost 1)
        assert abs(sum([possibility['probability'] for possibility in possibilities]) - 1) < 1e-6

    # Sort artifacts
    # Commented out because it isn't needed but I want to keep the code
    # pseudo_artifacts = sorted(pseudo_artifacts, key=lambda pseudo_artifact: pseudo_artifact['probability'], reverse=True)

    return pseudo_artifacts

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

def graph_artifact_potential(artifact_potentials: list[dict], nbins: int = 100):

    artifact_potentials_df = pd.DataFrame(artifact_potentials)

    min_power = artifact_potentials_df['power'].min()
    max_power = artifact_potentials_df['power'].max()
    bin_size = (max_power - min_power) / nbins

    bins = pd.DataFrame([(
        min_power + bin*bin_size,
        min_power + (bin+1)*bin_size,
        min_power + (bin+0.5)*bin_size,
        np.nan
        ) for bin in range(nbins)], columns=['bin bottom', 'bin top', 'bin mid', 'population'])

    for ind, bin in bins.iterrows():
        bins['population'][ind] = artifact_potentials_df[(artifact_potentials_df['power'] >= bin['bin bottom']) & (artifact_potentials_df['power'] < bin['bin top'])]['probability'].sum()

    # Plot
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    ax1.bar(x=bins['bin bottom'], height=bins['population'], width=bin_size)
    ax1.set_xlabel('Power')
    ax1.set_ylabel('Probability')

    ax2.plot(bins['bin mid'], bins['population'].cumsum(), color='r')
    ax2.set_ylabel('Power Percentile')
    ax2.set_ylim(0, 1)
    ax2.set_yticks(np.arange(0, 1.1, 0.1))
    ax2.grid(axis='both')

    plt.show()
    
    a = 1