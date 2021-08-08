import copy
import itertools
import logging
import math

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

import pandas as pd

import artifact as art
import artifacts as arts
import character as char
import evaluate as eval
import weapon as weap

_stat_names = ['Base HP', 'Base ATK', 'Base DEF', 'HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%',
                   'Elemental DMG%', 'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%', 'probability']

_valid_main_stats = ['HP', 'ATK', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%', 'Elemental DMG%',
                    'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%']

_unrelated_substat_rarity = pd.Series({
    'HP':                0.1364,
    'ATK':               0.1364,
    'DEF':               0.1364,
    'HP%':               0.0909,
    'ATK%':              0.0909,
    'DEF%':              0.0909,
    'Energy Recharge%':  0.0909,
    'Elemental Mastery': 0.0909,
    'Crit Rate%':        0.0682,
    'Crit DMG%':         0.0682
})

_substat_rarity = {
    'HP': pd.Series({
        'ATK':               0.1579,
        'DEF':               0.1579,
        'HP%':               0.1053,
        'ATK%':              0.1053,
        'DEF%':              0.1053,
        'Energy Recharge%':  0.1053,
        'Elemental Mastery': 0.1053,
        'Crit Rate%':        0.0789,
        'Crit DMG%':         0.0789
        }),
    'ATK': pd.Series({
        'HP':                0.1579,
        'DEF':               0.1579,
        'HP%':               0.1053,
        'ATK%':              0.1053,
        'DEF%':              0.1053,
        'Energy Recharge%':  0.1053,
        'Elemental Mastery': 0.1053,
        'Crit Rate%':        0.0789,
        'Crit DMG%':         0.0789
        }),
    'HP%': pd.Series({
        'HP':                0.15,
        'ATK':               0.15,
        'DEF':               0.15,
        'ATK%':              0.1,
        'DEF%':              0.1,
        'Energy Recharge%':  0.1,
        'Elemental Mastery': 0.1,
        'Crit Rate%':        0.075,
        'Crit DMG%':         0.075
        }),
    'ATK%': pd.Series({
        'HP':                0.15,
        'ATK':               0.15,
        'DEF':               0.15,
        'HP%':               0.1,
        'DEF%':              0.1,
        'Energy Recharge%':  0.1,
        'Elemental Mastery': 0.1,
        'Crit Rate%':        0.075,
        'Crit DMG%':         0.075
        }),
    'DEF%': pd.Series({
        'HP':                0.15,
        'ATK':               0.15,
        'DEF':               0.15,
        'HP%':               0.1,
        'ATK%':              0.1,
        'Energy Recharge%':  0.1,
        'Elemental Mastery': 0.1,
        'Crit Rate%':        0.075,
        'Crit DMG%':         0.075
        }),
    'Physical DMG%': _unrelated_substat_rarity,
    'Elemental DMG%': _unrelated_substat_rarity,
    'Elemental Mastery': pd.Series({
        'HP':                0.15,
        'ATK':               0.15,
        'DEF':               0.15,
        'HP%':               0.1,
        'ATK%':              0.1,
        'DEF%':              0.1,
        'Energy Recharge%':  0.1,
        'Crit Rate%':        0.075,
        'Crit DMG%':         0.075
        }),
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
}

_substat_roll_values = {
        'HP': {
            1: [23.90, 29.88],
            2: [50.19, 60.95, 71.70],
            3: [100.38, 114.72, 129.06, 143.40],
            4: [167.30, 191.20, 215.10, 239.00],
            5: [209.13, 239.00, 269.88, 299.75]
        },
        'ATK': {
            1: [1.56, 1.95],
            2: [3.27, 3.97, 4.67],
            3: [6.54, 7.47, 8.40, 9.34],
            4: [10.89, 12.45, 14.00, 15.56],
            5: [13.62, 15.56, 17.51, 19.45]
        },
        'DEF': {
            1: [1.85, 2.31],
            2: [3.89, 4.72, 5.56],
            3: [7.78, 8.89, 10.00, 11.11],
            4: [12.96, 14.82, 16.67, 18.52],
            5: [16.20, 18.52, 20.83, 23.15]
        },
        'HP%': {
            1: [1.17, 1.46],
            2: [1.63, 1.98, 2.33],
            3: [2.45, 2.80, 3.15, 3.50],
            4: [3.26, 3.73, 4.20, 4.66],
            5: [4.08, 4.66, 5.25, 5.83]
        },
        'ATK%': {
            1: [1.17, 1.46],
            2: [1.63, 1.98, 2.33],
            3: [2.45, 2.80, 3.15, 3.50],
            4: [3.26, 3.73, 4.20, 4.66],
            5: [4.08, 4.66, 5.25, 5.83]
        },
        'DEF%': {
            1: [1.46, 1.82],
            2: [2.04, 2.48, 2.91],
            3: [3.06, 3.50, 3.93, 4.37],
            4: [4.08, 4.66, 5.25, 5.83],
            5: [5.10, 5.83, 6.56, 7.29]
        },
        'Elemental Mastery': {
            1: [4.66, 5.83],
            2: [6.53, 7.93, 9.33],
            3: [9.79, 11.19, 12.59, 13.99],
            4: [13.06, 14.92, 16.79, 18.56],
            5: [16.32, 18.65, 20.98, 23.31]
        },
        'Energy Recharge%': {
            1: [1.30, 1.62],
            2: [1.81, 2.20, 2.59, ],
            3: [2.72, 3.11, 3.50, 3.89],
            4: [3.63, 4.14, 4.66, 5.18],
            5: [4.53, 5.18, 5.83, 6.48]
        },
        'Crit Rate%': {
            1: [0.78, 0.97],
            2: [1.09, 1.32, 1.55],
            3: [1.63, 1.86, 2.10, 2.33],
            4: [2.18, 2.49, 2.80, 3.11],
            5: [2.72, 3.11, 3.50, 3.89]
        },
        'Crit DMG%':  {
            1: [1.55, 1.94],
            2: [2.18, 2.64, 3.11],
            3: [3.26, 3.73, 4.20, 4.66],
            4: [4.35, 4.97, 5.60, 6.22],
            5: [5.44, 6.22, 6.99, 7.77]
        }
    }
    
_main_stat_scaling = {
        1: {
            'HP':                [129, 	178, 	227, 	275, 	324],
            'ATK':               [8, 	12, 	15, 	18, 	21],
            'HP%':               [3.1, 	4.3, 	5.5, 	6.7, 	7.9],
            'ATK%':              [3.1, 	4.3, 	5.5, 	6.7, 	7.9],
            'DEF%':              [3.9, 	5.4, 	6.9, 	8.4, 	9.9],
            'Physical DMG%':     [3.9, 	5.4, 	6.9, 	8.4, 	9.9],
            'Elemental DMG%':    [3.1, 	4.3, 	5.5, 	6.7, 	7.9],
            'Elemental Mastery': [13, 	17, 	22, 	27, 	32],
            'Energy Recharge%':  [3.5, 	4.8, 	6.1, 	7.5, 	8.8],
            'Crit Rate%':        [2.1, 	2.9, 	3.7, 	4.5, 	5.3],
            'Crit DMG%':         [4.2, 	5.8, 	7.4, 	9.0, 	10.5],
            'Healing Bonus%':    [2.4, 	3.3, 	4.3, 	5.2, 	6.1],
        },
        2: {
            'HP':                [258, 	331, 	404, 	478, 	551],
            'ATK':               [17, 	22, 	26, 	31, 	36],
            'HP%':               [4.2, 	5.4, 	6.6, 	7.8, 	9],
            'ATK%':              [4.2, 	5.4, 	6.6, 	7.8, 	9],
            'DEF%':              [5.2, 	6.7, 	8.2, 	9.7, 	11.2],
            'Physical DMG%':     [5.2, 	6.7, 	8.2, 	9.7, 	11.2],
            'Elemental DMG%':    [4.2, 	5.4, 	6.6, 	7.8, 	9],
            'Elemental Mastery': [17, 	22, 	26, 	31, 	36],
            'Energy Recharge%':  [4.7, 	6.0, 	7.3, 	8.6, 	9.9],
            'Crit Rate%':        [2.8, 	3.6, 	4.4, 	5.2, 	6],
            'Crit DMG%':         [5.6, 	7.2, 	8.8, 	10.4, 	11.9],
            'Healing Bonus%':    [3.2, 	4.1, 	5.1, 	6.0, 	6.9],
        },
        3: {
            'HP':                [430, 	552, 	674, 	796, 	918, 	1040, 	1162, 	1283, 	1405, 	1527, 	1649, 	1771, 	1893],
            'ATK':               [28, 	36, 	44, 	52, 	60, 	68, 	76, 	84, 	91, 	99, 	107, 	115, 	123],
            'HP%':               [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
            'ATK%':              [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
            'DEF%':              [6.6, 	8.4, 	10.3, 	12.1, 	14.0, 	15.8, 	17.7, 	19.6, 	21.4, 	23.3, 	25.1, 	27.0, 	28.8],
            'Physical DMG%':     [6.6, 	8.4, 	10.3, 	12.1, 	14.0, 	15.8, 	17.7, 	19.6, 	21.4, 	23.3, 	25.1, 	27.0, 	28.8],
            'Elemental DMG%':    [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
            'Elemental Mastery': [21, 	27, 	33, 	39, 	45, 	51, 	57, 	63, 	69, 	75, 	80, 	86, 	92],
            'Energy Recharge%':  [5.8, 	7.5, 	9.1, 	10.8, 	12.4, 	14.1, 	15.7, 	17.4, 	19.0, 	20.7, 	22.3, 	24.0, 	25.6],
            'Crit Rate%':        [3.5, 	4.5, 	5.5, 	6.5, 	7.5, 	8.4, 	9.4, 	10.4, 	11.4, 	12.4, 	13.4, 	14.4, 	15.4],
            'Crit DMG%':         [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8],
            'Healing Bonus%':    [4.0, 	5.2, 	6.3, 	7.5, 	8.6, 	9.8, 	10.9, 	12.0, 	13.2, 	14.3, 	15.5, 	16.6, 	17.8],
        },
        4: {
            'HP':                [645, 	828, 	1011, 	1194, 	1377, 	1559, 	1742, 	1925, 	2108, 	2291, 	2474, 	2657, 	2839, 	3022, 	3205, 	3388, 	3571],
            'ATK':               [42, 	54, 	66, 	78, 	90, 	102, 	113, 	125, 	137, 	149, 	161, 	173, 	185, 	197, 	209, 	221, 	232],
            'HP%':               [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
            'ATK%':              [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
            'DEF%':              [7.9, 	10.1, 	12.3, 	14.6, 	16.8, 	19.0, 	21.2, 	23.5, 	25.7, 	27.9, 	30.2, 	32.4, 	34.6, 	36.8, 	39.1, 	41.3, 	43.5],
            'Physical DMG%':     [7.9, 	10.1, 	12.3, 	14.6, 	16.8, 	19.0, 	21.2, 	23.5, 	25.7, 	27.9, 	30.2, 	32.4, 	34.6, 	36.8, 	39.1, 	41.3, 	43.5],
            'Elemental DMG%':    [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
            'Elemental Mastery': [25, 	32, 	39, 	47, 	54, 	61, 	68, 	75, 	82, 	89, 	97, 	104, 	111, 	118, 	125, 	132, 	139],
            'Energy Recharge%':  [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7],
            'Crit Rate%':        [4.2, 	5.4, 	6.6, 	7.8, 	9.0, 	10.1, 	11.3, 	12.5, 	13.7, 	14.9, 	16.1, 	17.3, 	18.5, 	19.7, 	20.8, 	22.0, 	23.2],
            'Crit DMG%':         [8.4, 	10.8, 	13.1, 	15.5, 	17.9, 	20.3, 	22.7, 	25.0, 	27.4, 	29.8, 	32.2, 	34.5, 	36.9, 	39.3, 	41.7, 	44.1, 	46.4],
            'Healing Bonus%':    [4.8, 	6.2, 	7.6, 	9.0, 	10.3, 	11.7, 	13.1, 	14.4, 	15.8, 	17.2, 	18.6, 	19.9, 	21.3, 	22.7, 	24.0, 	25.4, 	26.8],
        },
        5: {
            'HP':                [717, 	920, 	1123, 	1326, 	1530, 	1733, 	1936, 	2139, 	2342, 	2545, 	2749, 	2952, 	3155, 	3358, 	3561, 	3764, 	3967, 	4171, 	4374, 	4577, 	4780],
            'ATK':               [47, 	60, 	73, 	86, 	100, 	113, 	126, 	139, 	152, 	166, 	179, 	192, 	205, 	219, 	232, 	245, 	258, 	272, 	285, 	298, 	311],
            'HP%':               [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
            'ATK%':              [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
            'DEF%':              [8.7, 	11.2, 	13.7, 	16.2, 	18.6, 	21.1, 	23.6, 	26.1, 	28.6, 	31, 	33.5, 	36, 	38.5, 	40.9, 	43.4, 	45.9, 	48.4, 	50.8, 	53.3, 	55.8, 	58.3],
            'Physical DMG%':     [8.7, 	11.2, 	13.7, 	16.2, 	16.2, 	21.1, 	23.6, 	26.1, 	28.6, 	31, 	33.5, 	36, 	38.5, 	40.9, 	43.4, 	45.9, 	48.4, 	50.8, 	53.3, 	55.8, 	58.3],
            'Elemental DMG%':    [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
            'Elemental Mastery': [28, 	36, 	44, 	52, 	60, 	68, 	76, 	84, 	91, 	99, 	107, 	115, 	123, 	131, 	139, 	147, 	155, 	163, 	171, 	179, 	187],
            'Energy Recharge%':  [7.8, 	10.0, 	12.2, 	14.4, 	16.6, 	18.8, 	21.0, 	23.2, 	25.4, 	27.6, 	29.8, 	32.0, 	34.2, 	36.4, 	38.6, 	40.8, 	43.0, 	45.2, 	47.4, 	49.6, 	51.8],
            'Crit Rate%':        [4.7, 	6.0, 	7.4, 	8.7, 	10.0, 	11.4, 	12.7, 	14.0, 	15.4, 	16.7, 	18.0, 	19.3, 	20.7, 	22.0, 	23.3, 	24.7, 	26.0, 	27.3, 	28.7, 	30.0, 	31.1],
            'Crit DMG%':         [9.3, 	11.9, 	14.6, 	17.2, 	19.9, 	22.5, 	25.2, 	27.8, 	30.5, 	33.1, 	35.8, 	38.4, 	41.1, 	43.7, 	46.3, 	49.0, 	51.6, 	54.3, 	56.9, 	59.6, 	62.2],
            'Healing Bonus%':    [5.4, 	6.9, 	8.4, 	10.0, 	11.5, 	13.0, 	14.5, 	16.1, 	17.6, 	19.1, 	20.6, 	22.2, 	23.7, 	25.2, 	26.7, 	28.3, 	29.8, 	31.3, 	32.8, 	34.4, 	35.9],
        },
    }

# Source: https://genshin-impact.fandom.com/wiki/Loot_System/Artifact_Drop_Distribution
_number_substats_probability = {
    'domain': {
        'less': [np.nan, np.nan, 0.8, 0.8, 0.8, 0.8],
        'more': [np.nan, np.nan, 0.2, 0.2, 0.2, 0.2]
        },
    'world boss': {
        'less': [np.nan, np.nan, 2/3, 2/3, 2/3, 2/3],
        'more': [np.nan, np.nan, 1/3, 1/3, 1/3, 1/3]
        },
    'weekly boss': {
        'less': [np.nan, np.nan, 2/3, 2/3, 2/3, 2/3],
        'more': [np.nan, np.nan, 1/3, 1/3, 1/3, 1/3]
        },
    'elite enemies': { # Inaccurate for l
        'less': [np.nan, np.nan, 0.9, 0.9, 0.97, 0.97],
        'more': [np.nan, np.nan, 0.1, 0.1, 0.03, 0.03]
        }
    }

_max_level_by_stars = [np.nan, 4, 4, 12, 16, 20]

log = logging.getLogger(__name__)

def slot_potential(character: char.Character, weapon: weap.Weapon, artifacts: arts.Artifacts, slot: type, set: str, stars: int, main_stat: str, target_level: int, source: str = 'domain', verbose: bool = False) -> list[dict]:

    # Validate inputs
    if target_level < 0:
        raise ValueError('Target level cannot be less than 0.')
    if source not in _number_substats_probability:
        raise ValueError('Invalid artifact source.')

    # Logging
    if verbose:
        log.info('-' * 90)
        log.info('Evaluating slot potential...')
        log.info('Artifact:')
        log.info((
            f'{slot._slot.capitalize():>7s} '
            f'{stars:>d}* '
            f'{set.capitalize():>14} '
            f'{target_level:>2d}/{_max_level_by_stars[stars]:>2d} '
            f'{main_stat:>17s}: {_main_stat_scaling[stars][main_stat][target_level]:>4}'
        ))
        log.info(f'Character: {character}')
        log.info(f'Weapon: {weapon}')
        log.info(f'Other Artifacts:                                          HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%')
        for artifact in artifacts:
            if type(artifact) is not slot:
                log.info(f'{artifact.to_string_table()}')

    # Identify roll combinations
    total_rolls_low = max(0, stars - 2) + math.floor(target_level / 4)
    total_rolls_high_chance = _number_substats_probability[source]['more'][stars]
    if verbose:
        log.info(f'Making potential artifacts...')
    potential_artifacts_df = _make_children(character=character, stars=stars, main_stat=main_stat, total_rolls=total_rolls_low, total_rolls_high_chance=total_rolls_high_chance, verbose=verbose)

    # Format output
    for stat in _stat_names:
        if stat not in potential_artifacts_df:
            potential_artifacts_df[stat] = 0
    potential_artifacts_df = potential_artifacts_df.fillna(0)

    # Assign to artifact
    artifact = slot(set=set, main_stat=main_stat, stars=stars, level=target_level, substats=potential_artifacts_df)

    # Create artifact list, replacing previous artifact
    other_artifacts_list = [other_artifact for other_artifact in artifacts if type(other_artifact) != slot]
    other_artifacts_list.append(artifact)
    other_artifacts = arts.Artifacts(other_artifacts_list)

    if verbose:
        log.info('Calculating power distribution...')
    power = eval.evaluate_power(character=character,  weapon=weapon, artifacts=other_artifacts)
    if verbose:
        log.info(f'Min Power:  {power.min():,.0f}')
        log.info(f'Avg Power:  {power.dot(potential_artifacts_df["probability"]):,.0f}, +{100 * (power.dot(potential_artifacts_df["probability"])/power.min() - 1):.1f}%')
        log.info(f'Max Power:  {power.max():,.0f}, +{100 * (power.max()/power.min() - 1):.1f}%')

    # Return results
    slot_potentials_df = pd.DataFrame({'power': power, 'probability': potential_artifacts_df['probability']})
    return slot_potentials_df

def artifact_potential(character: char.Character, weapon: weap.Weapon, artifacts: arts.Artifacts, artifact: art.Artifact, target_level: int, verbose: bool) -> list[dict]:

    # Validate inputs
    if target_level < artifact.level:
        raise ValueError('Target level cannot be less than artifact level')

    # Logging
    if verbose:
        log.info('-' * 90)
        log.info('Evaluating artifact potential...')
        log.info(f'Artifacts:                                                HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%')
        log.info(f'{artifact.to_string_table()}')
        log.info(f'Character: {character}')
        log.info(f'Weapon: {weapon}')
        log.info(f'Other Artifacts:                                          HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%')
        for other_artifact in artifacts:
            if type(other_artifact) is not type(artifact):
                log.info(f'{other_artifact.to_string_table()}')

    # Identify possible roll combinations
    total_rolls = max(0, artifact.stars - 2) + math.floor(target_level / 4)
    potential_artifacts_df = _make_children(artifact=artifact, character=character, stars=artifact.stars, main_stat=artifact.main_stat, total_rolls=total_rolls, total_rolls_high_chance=0, verbose=verbose)
    
    # Format output
    for stat in _stat_names:
        if stat not in potential_artifacts_df:
            potential_artifacts_df[stat] = 0
    potential_artifacts_df = potential_artifacts_df.fillna(0)

    # Assign to artifact
    new_artifact = copy.deepcopy(artifact)
    new_artifact.substats = potential_artifacts_df
    new_artifact.level = target_level

    # Create artifact list, replacing previous artifact
    other_artifacts_list = [other_artifact for other_artifact in artifacts if type(other_artifact) != type(new_artifact)]
    other_artifacts_list.append(new_artifact)
    other_artifacts = arts.Artifacts(other_artifacts_list)

    if verbose:
        log.info('Calculating power distribution...')
    power = eval.evaluate_power(character=character,  weapon=weapon, artifacts=other_artifacts)
    if verbose:
        log.info(f'Min Power:  {power.min():,.0f}')
        log.info(f'Avg Power:  {power.dot(potential_artifacts_df["probability"]):,.0f}, +{100 * (power.dot(potential_artifacts_df["probability"])/power.min() - 1):.1f}%')
        log.info(f'Max Power:  {power.max():,.0f}, +{100 * (power.max()/power.min() - 1):.1f}%')

    # Return results
    slot_potentials_df = pd.DataFrame({'power': power, 'probability': potential_artifacts_df['probability']})
    return slot_potentials_df

def _make_children(character: char.Character, stars: int, main_stat: str, total_rolls: int, total_rolls_high_chance: float, verbose: bool, artifact: art.Artifact = None) -> pd.DataFrame:
# def _make_children(character: char.Character, stars: int, main_stat: str, remaining_unlocks: int, remaining_increases: int, artifact: art.Artifact = None) -> pd.DataFrame:
    '''Creates dataframe containing every possible end result of artifact along with probability'''
    
    # Creates initial pseudo-artifact
    pseudo_artifacts = [{'substats': {}, 'probability':1.0}]
    if artifact is not None:
        for substat in artifact.substats:
            pseudo_artifacts[0]['substats'][substat] = 0

    # Create every possible pseudo artifact by unlocking substats
    starting_substats = len(pseudo_artifacts[0]['substats'])
    remaining_unlocks = min(4, total_rolls) - starting_substats
    if remaining_unlocks > 0:
        pseudo_artifacts = _add_substats(pseudo_artifacts=pseudo_artifacts, remaining_unlocks=remaining_unlocks, character=character, main_stat=main_stat)
    # Add extra unlocks (this should only occur for low stars or low target level)
    extra_unlock_chance = int((total_rolls_high_chance > 0) and (total_rolls < 4)) * total_rolls_high_chance
    if extra_unlock_chance > 0:
        remaining_unlocks_extra = remaining_unlocks + 1
        pseudo_artifacts_extra = _add_substats(pseudo_artifacts=pseudo_artifacts, remaining_unlocks=remaining_unlocks_extra, character=character, main_stat=main_stat)
        # Fix original probabilities
        for pseudo_artifact in pseudo_artifacts:
            pseudo_artifact['probability'] *= 1 - extra_unlock_chance
        for pseudo_artifact_extra in pseudo_artifacts_extra:
            pseudo_artifact_extra['probability'] *= extra_unlock_chance
            pseudo_artifacts.append(pseudo_artifact_extra)
    if verbose:
        log.info(f'{len(pseudo_artifacts):,} different ways to unlock condensed substats.')

    # Create every possible pseudo artifact by assigning substat rolls
    remaining_increases = total_rolls - remaining_unlocks - starting_substats
    if remaining_increases > 0:
        extra_increase_chance = int((total_rolls_high_chance > 0) and (total_rolls >= 4)) * total_rolls_high_chance
        pseudo_artifacts = _add_substat_rolls(pseudo_artifacts=pseudo_artifacts, remaining_increases=remaining_increases, extra_increase_chance=extra_increase_chance, character=character)
    if verbose:
        log.info(f'{len(pseudo_artifacts):,} different ways to assign rolls to condensed substats.')

    # Convert pseudo artifacts by calculating roll values
    substat_values_df = _calculate_substats(pseudo_artifacts=pseudo_artifacts, character=character, stars=stars)
    if verbose:
        log.info(f'{len(substat_values_df.index):,} different ways to roll condensed substats.')

    return substat_values_df

def _add_substats(pseudo_artifacts: list[dict], remaining_unlocks: int, character: char.Character, main_stat: str) -> list[dict]:
    '''Creates pseudo artifacts with every possible combination of revealed substats'''

    # Generate list of possible substats
    valid_substats = set(_substat_rarity[main_stat].keys())
    for substat in pseudo_artifacts[0]['substats']:
        valid_substats.remove(substat)

    # Consolodate similar substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
    condensable_substats = _condensable_substats(character=character)
    base_probability = sum([_substat_rarity[main_stat][substat] for substat in valid_substats])

    # Create list of possible substats
    possibilities = []
    for substat in valid_substats:
        possibility = {
            'substat': substat,
            'probability': _substat_rarity[main_stat][substat] / base_probability
        }
        possibilities.append(possibility)

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([possibility['probability'] for possibility in possibilities]) - 1) < 1e-6

    # Create all possible combinations of new substats
    combinations = tuple(itertools.combinations(possibilities, remaining_unlocks))

    # Iterate across combinations
    new_pseudo_artifacts = {}
    for combination in combinations:

        # Create new pseudo artifact
        pseudo_artifact = copy.deepcopy(pseudo_artifacts[0])

        # Assign every new substat a single roll
        for substat in combination:
            pseudo_artifact['substats'][substat['substat']] = 1

        # Calculate probability of pseudo artifact
        combination_probability = 0
        permutations = tuple(itertools.permutations(combination, len(combination)))
        for permutation in permutations:
            permutation_probability = 1
            remaining_probability = 1
            for substat in permutation:
                permutation_probability *= substat['probability'] / remaining_probability
                remaining_probability -= substat['probability']
            combination_probability += permutation_probability
        pseudo_artifact['probability'] = combination_probability

        # Consolodate substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
        artifact_condensable_substats = [substat for substat in pseudo_artifact['substats'] if substat in condensable_substats] #condensable_substats.intersection(pseudo_artifact['substats'])
        for (ind, artifact_condensable_substat) in enumerate(artifact_condensable_substats):
            condensed_substat = condensable_substats[ind]
            pseudo_artifact['substats'][condensed_substat] = 0
        for artifact_condensable_substat in artifact_condensable_substats:
            if artifact_condensable_substat not in condensable_substats[:len(artifact_condensable_substats)]:
                del pseudo_artifact['substats'][artifact_condensable_substat]
        assert len(pseudo_artifact['substats']) == 4

        # Add pseudo artifact to dict
        pseudo_artifact['substats'] = dict(sorted(pseudo_artifact['substats'].items())) # sort keys
        key = str(pseudo_artifact['substats'])
        if key not in new_pseudo_artifacts:
            new_pseudo_artifacts[key] = pseudo_artifact
        else:
            new_pseudo_artifacts[key]['probability'] += pseudo_artifact['probability']
        
    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([possibility['probability'] for possibility in pseudo_artifacts]) - 1) < 1e-6
    
    # Return new pseudo artifacts
    pseudo_artifacts = [pseudo_artifact for pseudo_artifact in new_pseudo_artifacts.values()]
    return pseudo_artifacts

def _add_substat_rolls(pseudo_artifacts: list[dict], remaining_increases: int, extra_increase_chance: float, character: char.Character) -> list[dict]:
    '''Creates pseudo artifacts with every possible combination of number of rolls for each substat'''

    # Get condensable substats
    condensable_substats = _condensable_substats(character=character)

    # If extra increase chance, run iteration a second time.
    if extra_increase_chance > 0:
        remaining_increases += 1

    # Repeat for each increase required
    for ind in range(remaining_increases):

        # Create new pseudo artifact dict
        new_pseudo_artifacts = {}

        # Iterate over existing pseudo artifacts
        for pseudo_artifact in pseudo_artifacts:

            # Consolodate similar substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
            valid_substats = set(pseudo_artifact['substats'].keys())
            condensable_substats_on_artifact = [condensable_substat for condensable_substat in condensable_substats if condensable_substat in valid_substats]

            # Create list of possible substats
            possibilities = []
            for substat in valid_substats:
                if substat in condensable_substats:
                    if substat is condensable_substats[0]:
                        substat_possibility = len(condensable_substats_on_artifact) / 4
                    else:
                        continue
                else:
                    substat_possibility = 0.25
                possibility = {
                    'substat': substat,
                    'probability': substat_possibility
                }
                possibilities.append(possibility)

            # Verify probability math (sum of probabilities is almost 1)
            assert abs(sum([possibility['probability'] for possibility in possibilities]) - 1) < 1e-6

            # Create new pseudo artifacts for each possibility
            for possibility in possibilities:
                new_pseudo_artifact = copy.deepcopy(pseudo_artifact)
                if possibility['substat'] not in condensable_substats:
                    new_pseudo_artifact['substats'][possibility['substat']] += 1
                new_pseudo_artifact['probability'] *= possibility['probability']
                # Add pseudo artifact to dict
                key = str(new_pseudo_artifact['substats'])
                if key not in new_pseudo_artifacts:
                    new_pseudo_artifacts[key] = new_pseudo_artifact
                else:
                    new_pseudo_artifacts[key]['probability'] += new_pseudo_artifact['probability']
    
        # If extra increase, merge with previous list
        if ind == 0 and extra_increase_chance > 0:
            # Update probability of new artifacts
            for new_pseudo_artifact in new_pseudo_artifacts.values():
                new_pseudo_artifact['probability'] *= extra_increase_chance
            # Update probability of old artifacts and add to dict
            for old_pseudo_artifact in pseudo_artifacts:
                old_pseudo_artifact['probability'] *= (1 - extra_increase_chance)
                key = str(old_pseudo_artifact['substats'])
                if key not in new_pseudo_artifacts:
                    new_pseudo_artifacts[key] = old_pseudo_artifact
                else:
                    new_pseudo_artifacts[key]['probability'] += old_pseudo_artifact['probability']

        # Verify probability math (sum of probabilities is almost 1)
        assert abs(sum([new_pseudo_artifact['probability'] for new_pseudo_artifact in new_pseudo_artifacts.values()]) - 1) < 1e-6

        # Return overwrite pseudo_artifacts
        pseudo_artifacts = [pseudo_artifact for pseudo_artifact in new_pseudo_artifacts.values()]

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([pseudo_artifact['probability'] for pseudo_artifact in pseudo_artifacts]) - 1) < 1e-6

    return pseudo_artifacts

def _calculate_substats(pseudo_artifacts: list[dict], character: char.Character, stars: int) -> pd.DataFrame:
    '''Creates every possible artifact from the given number of substat rolls'''

    ## NOTE: This function is where the vast majority of the computational time is spent

    # Calculate probability of possible expanded substats
    substat_rolls_probabillities = _substat_rolls_probabillities()
    
    # Creates empty list of pseudo artifacts
    pseudo_artifacts_list = []

    # Iterate over existing pseudo artifacts
    for pseudo_artifact in pseudo_artifacts:

        # Consolodate substats
        valid_substats = set(pseudo_artifact['substats'].keys())

        # Create list of possible roll combinations for each substat
        substat_products = []
        for substat in valid_substats:
            substat_products.append(substat_rolls_probabillities[pseudo_artifact['substats'][substat]])

        # Create list of all possible roll combinations across each substat
        pseudo_artifact_list = list(itertools.product(*substat_products))
        pseudo_artifact_df = pd.DataFrame(pseudo_artifact_list, columns=valid_substats)

        # Calculate probabillity of each case
        pseudo_artifact_df['probability'] = pseudo_artifact['probability']
        for column in pseudo_artifact_df:
            column_df = pd.DataFrame(pseudo_artifact_df[column].tolist())
            if len(column_df.columns) == 2:
                pseudo_artifact_df['probability'] *= column_df[column_df.columns[1]]
                pseudo_artifact_df[column] =column_df[column_df.columns[0]]

        # Verify probability math (sum of probabilities is almost the initial pseudo artifact probabillity)
        assert abs(pseudo_artifact_df['probability'].sum() - pseudo_artifact['probability']) < 1e-6 * pseudo_artifact['probability']

        # Append to list
        pseudo_artifacts_list.append(pseudo_artifact_df)
    
    # Append dataframes
    pseudo_artifacts_df = pd.concat(pseudo_artifacts_list)

    # Split each substat
    substats_values = {}
    for substat in pseudo_artifacts_df:
        if pseudo_artifacts_df[substat].dtype is np.dtype(object):
            column_names = [f'{substat}_{roll}' for roll in range(4)]
            substat_list = pseudo_artifacts_df[substat].tolist()
            if substat_list[0] is np.nan:
                substat_list[0] = (0, 0, 0, 0)
            rolls_split = pd.DataFrame(substat_list, columns=column_names)
            substat_value = rolls_split.dot(_substat_roll_values[substat][stars])
            substats_values[substat] = substat_value
        else:
            substats_values[substat] = pd.Series(pseudo_artifacts_df[substat].tolist())
        
    substat_values_df = pd.DataFrame(substats_values)

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(substat_values_df['probability'].sum() - 1) < 1e-6

    return substat_values_df

def _condensable_substats(character: char.Character):

    # Create list of condensable stats
    if character.scaling_stat == 'ATK':
        condensable_substats = ['DEF', 'DEF%', 'HP', 'HP%', 'Energy Recharge%']
    elif character.scaling_stat == 'DEF':
        condensable_substats = ['ATK', 'ATK%', 'HP', 'HP%', 'Energy Recharge%']
    elif character.scaling_stat == 'HP':
        condensable_substats = ['ATK', 'ATK%', 'DEF', 'DEF%', 'Energy Recharge%']
    if character.amplifying_reaction is None:
        condensable_substats.append('Elemental Mastery')
    if character.crits == 'always':
        condensable_substats.append('Crit Rate%')
    elif character.crits == 'never':
        condensable_substats.append('Crit Rate%')
        condensable_substats.append('Crit DMG%')

    return condensable_substats

def graph_potentials(artifact_potentials_dfs: list[pd.DataFrame], legend_labels: list[str], base_power: float = None, title: str = None, nbins: int = None, smooth: bool = False):

    # Calculate number of bins
    if nbins is None:
        biggest_df = max([artifact_potentials_df.size for artifact_potentials_df in artifact_potentials_dfs])
        nbins = min(250, biggest_df / 100)

    # Prepare histogram
    min_power = min([artifact_potentials_df['power'].min() for artifact_potentials_df in artifact_potentials_dfs])
    max_power = max([artifact_potentials_df['power'].max() for artifact_potentials_df in artifact_potentials_dfs])
    bin_size = (max_power - min_power) / nbins
    bins = pd.DataFrame([(
            min_power + bin*bin_size,
            min_power + (bin+1)*bin_size,
            min_power + (bin+0.5)*bin_size
            ) for bin in range(nbins)], columns=['bin bottom', 'bin top', 'bin mid'])

    # Fill histogram
    for (input_ind, artifact_potentials_df) in enumerate(artifact_potentials_dfs):
        bins[f'pop_{input_ind}'] = np.nan
        for bin_ind, bin in bins.iterrows():
            bins[f'pop_{input_ind}'][bin_ind] = artifact_potentials_df[(artifact_potentials_df['power'] >= bin['bin bottom']) & (artifact_potentials_df['power'] < bin['bin top'])]['probability'].sum()
        # Calculate percentiles
        bins[f'per_{input_ind}'] = bins[f'pop_{input_ind}'].cumsum()
        # Apply smoothing after percentiles
        if smooth:
            smoothing_period = math.floor(nbins / 50)
            bins[f'pop_{input_ind}'] = bins[f'pop_{input_ind}'].rolling(window=smoothing_period, min_periods=1).sum()/smoothing_period

    # Create axes
    fig, ax1 = plt.subplots()
    ax1.set_title(title)
    ax2 = ax1.twinx()
    ax3 = ax1.twiny()

    # plot_colors = [(127/255, 201/255, 127/255), (190/255, 174/255, 212/255), (253/255, 192/255, 134/255), (255/255, 255/255, 153/255), (56/255, 108/255, 176/255)]
    plot_colors = [(179/255, 205/255, 227/255), (204/255, 235/255, 197/255), (254/255, 217/255, 166/255), (222/255, 203/255, 228/255), (251/255, 180/255, 174/255)] # Source: https://colorbrewer2.org/#type=qualitative&scheme=Pastel1&n=5
    plot_color_iter = itertools.cycle(plot_colors)

    fills = []
    for ind in range(len(artifact_potentials_dfs)):
        # Select plot color
        plot_color = next(plot_color_iter)
        plot_color_dark = _adjust_lightness(plot_color, 0.5)
        # Plot histogram
        # ax1.bar(x=bins['bin bottom'], height=bins[f'pop_{ind}'], width=bin_size, color=plot_color_w_alpha)
        # Plot fill with thick border
        ax1.plot(bins['bin mid'], bins[f'pop_{ind}'], color=plot_color)
        fill = ax1.fill(bins['bin mid'].tolist() + [bins['bin mid'].loc[0]], bins[f'pop_{ind}'].to_list() + [0], color=plot_color, alpha=0.3)
        fills.append(fill)
        # Plot percentile line
        ax2.plot(bins['bin mid'], bins[f'per_{ind}'], color=plot_color_dark)

    # Draw base power comparisons
    if base_power is not None:
        ax2.plot([base_power, base_power], [0, 1], 'r-')
        percentiles = [(artifact_potentials_df[artifact_potentials_df['power'] < base_power]['probability'].sum(), ind) for (artifact_potentials_df, ind) in zip(artifact_potentials_dfs, list(range(len(artifact_potentials_dfs))))]
        percentiles = sorted(percentiles, key=lambda x: x[0], reverse=True)
        ax2.scatter([base_power] * len(percentiles), [percentile for (percentile, _) in percentiles], c='k')
        # Determine positions of labels. If far enough fro right hand side, alternate between left and right.
        if (base_power - min_power) / (max_power - min_power) < 0.85:
            x_location = itertools.cycle([base_power - (max_power - min_power) * 0.02, base_power + (max_power - min_power) * 0.02])
            horizontal_allignment = itertools.cycle(['right', 'left'])
        else:
            x_location = itertools.cycle([base_power - (max_power - min_power) * 0.02])
            horizontal_allignment = itertools.cycle(['left'])
        max_height = 1
        for (percentile, ind) in percentiles:
            label = legend_labels[ind]
            delta_power = base_power/artifact_potentials_dfs[ind]['power'].min() - 1
            if percentile < 0.15:
                y_location =  percentile + 0.05
                max_height = y_location
            else:
                y_location = min(max_height - 0.0375, percentile - 0.05)
                max_height = y_location
            # Plot labels
            ax2.annotate(
                    f' {label}: ({100*percentile:.1f}% / +{100*delta_power:.1f}%)',
                    (next(x_location), y_location), horizontalalignment=next(horizontal_allignment),
                    bbox=dict(facecolor='white', alpha=0.5))

    # Legend
    fills = [fill[0] for fill in fills]
    ax3.legend(handles=fills, labels=legend_labels, loc='lower right', framealpha=0.9)

    ax1.set_xlabel('Power')
    ax1.set_ylabel('Probability')
    ax1.set_xlim(min_power, max_power)
    # Ignore first bin in setting ymax. If things are smoothed, this is generally ignored but that's OK.
    y_max = max([bins[f'pop_{ind}'].loc[1:].max() for ind in range(len(artifact_potentials_dfs))])
    ax1.set_ylim(0, y_max)

    ax2.set_ylabel('Power Percentile')
    ax2.set_ylim(0, 1)
    ax2.set_yticks(np.arange(0, 1.1, 0.1))
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter(1.0)) 
    ax2.grid(axis='both')

    num_x_ticks = math.floor((max_power - min_power) / min_power / 0.05) + 1
    x_tick_locations = min_power + 0.05 * min_power * np.array(list(range(num_x_ticks)))
    ax3.set_xlabel('ΔPower')
    ax3.set_xlim(ax1.get_xlim())
    ax3.set_xticks(x_tick_locations)
    ax3.set_xticklabels([f'{5*num}%' for num in range(num_x_ticks)])

    plt.subplots_adjust(top=0.85)
    plt.subplots_adjust(right=0.85)

    plt.draw()
    plt.pause(0.001)

def _substat_rolls_probabillities():
    '''Creates reference of probabillity of rolls being distibuted in a given manner'''

    # Create list of possible expanded substats
    possible_substat_rolls = {
        0: tuple(_sums(4, 0)),
        1: tuple(_sums(4, 1)),
        2: tuple(_sums(4, 2)),
        3: tuple(_sums(4, 3)),
        4: tuple(_sums(4, 4)),
        5: tuple(_sums(4, 5)),
        6: tuple(_sums(4, 6)),
    }

    # Calculates probabillity of each case
    substat_rolls_probabillities = {}
    for num_rolls in possible_substat_rolls:
        substat_rolls_probabillities[num_rolls] = []
        for roll_tuple in possible_substat_rolls[num_rolls]:
            arrangements = 1
            remaining_rolls = sum(roll_tuple)
            for num_substat_rolls in roll_tuple:
                arrangements *= math.comb(remaining_rolls, num_substat_rolls)
                remaining_rolls -= num_substat_rolls
            substat_rolls_probabillities[num_rolls].append((
                roll_tuple,
                arrangements / len(roll_tuple)**sum(roll_tuple)
            ))

    return substat_rolls_probabillities

def _sums(length, total_sum):
    '''Generates '''
    if length == 1:
        yield (total_sum,)
    else:
        for value in range(total_sum + 1):
            for permutation in _sums(length - 1, total_sum - value):
                yield (value,) + permutation

def _adjust_lightness(color, amount=0.5):
    import matplotlib.colors as mc
    import colorsys
    try:
        c = mc.cnames[color]
    except:
        c = color
    c = colorsys.rgb_to_hls(*mc.to_rgb(c))
    return colorsys.hls_to_rgb(c[0], max(0, min(1, amount * c[1])), c[2])