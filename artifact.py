import copy
import math

import numpy as np
import pandas as pd


class Artifact:

    _stat_names = ['Base HP', 'Base ATK', 'Base DEF', 'HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%',
                   'Elemental DMG%', 'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%']
    _max_level_by_stars = [np.nan, 4, 4, 12, 16, 20]
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
    _valid_sets = ['initiate', 'adventurer', 'lucky', 'doctor', 'resolution', 'miracle', 'berserker', 'instructor', 'exile', 'defenders', 'brave', 'martial', 'gambler', 'scholar', 'illumination', 'destiny', 'wisdom', 'springtime',
                   'gladiators', 'wanderers', 'thundersoother', 'thundering', 'maiden', 'viridescent', 'witch', 'lavawalker', 'noblesse', 'chivalry', 'petra', 'bolide', 'blizard', 'depth', 'millelith', 'pale', 'fate', 'reminiscnece']

    # To be overwritten by inherited types
    _main_stats = []
    _slot = ''

    def __init__(self, set: str, main_stat: str, stars: int, level: int, substats: dict[str]):

        # Validated inputs
        self.set = set
        self.stars = stars
        self.main_stat = main_stat
        self.level = level
        self.substats = substats

    @property
    def set(self):
        return self._set

    @set.setter
    def set(self, set: str):
        if set not in self._valid_sets:
            raise ValueError('Invalid set.')
        self._set = set

    @property
    def stars(self):
        return self._stars

    @stars.setter
    def stars(self, stars: int):
        if stars < 1 or stars > 5:
            raise ValueError('Invalid artifact number of stars.')
        if hasattr(self, 'stars'):
            if self.stars is not None:
                raise ValueError(
                    'TODO: I do not curerntly have implemented a method for updating substats/level nicely if you update stars.')
        self._stars = stars

    @property
    def main_stat(self):
        return self._main_stat

    @main_stat.setter
    def main_stat(self, main_stat):
        if main_stat not in self._main_stats:
            raise ValueError('Invalid main stat.')
        self._main_stat = main_stat

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level: int):
        if level < 0:
            raise ValueError('Invalid artifact level: Must be positive.')
        elif level > self._max_level_by_stars[self.stars]:
            raise ValueError(
                f'Invalid artifact level: {self.stars}-star artifacts must be less than or equal to level {level}.')
        elif hasattr(self, 'substats'):
            if self.stars + math.floor(level / 4) - 1 < len(self.substats):
                raise ValueError(
                    f'Cannot lower level below {self.stars + math.floor(level / 4) - 1} while there are {len(self.substats)} substats.')
        self._level = level

    @property
    def substats(self):
        return self._substats

    @substats.setter
    def substats(self, substats: dict[str]):
        if len(substats) > 4:
            raise ValueError(
                'Invalid number of substats: cannot have more than 4 substats')
        elif len(substats) > self.stars + math.floor(self.level / 4) - 1:
            raise ValueError(
                'Invalid number of substats: cannot have more substats than limited by stars and level')
        self._substats = copy.deepcopy(substats)

    def add_substat(self, stat: str, value: float):
        if stat not in self._substat_roll_values:
            raise ValueError('Invalid stat name.')
        elif stat in self.substats:
            raise ValueError(
                'Cannot add substat that already exists on artifact.')
        elif len(self.substats) >= 4:
            raise ValueError('Cannot have more than 4 substats.')
        self._substats[stat] = value

    def increase_substat(self, stat: str, value: int):
        if stat not in self._substat_roll_values:
            raise ValueError('Invalid substat name.')
        elif stat not in self.substats:
            raise ValueError('Substat does not exist on artifact.')
        self._substats[stat] += value

    def roll_substat(self, stat: str, roll: int):
        if stat not in self._substat_roll_values:
            raise ValueError('Invalid substat name.')
        elif stat not in self.substats.keys():
            raise ValueError('Substat does not exist on artifact.')
        self._substats[stat] += self._substat_roll_values[stat][self.stars][roll]

    # TODO: Have this return the set of rolls that were used to generate self.value.
    # @property
    # def rolls(self):
    #     return None

    @property
    def stats(self):

        self._stats = pd.Series(0.0, index=self._stat_names)
        # Main stat
        self._stats[self._main_stat] += self._main_stat_scaling[self._stars][self._main_stat][self._level]
        # Substats
        for substat, value in self.substats.items():
            self._stats[substat] += value
        return self._stats

    @property
    def slot(self):
        return self._slot

    def to_string_table(self):
        return_str = (
            f'{self.slot.capitalize():>7s} '
            f'{self.stars:>d}* '
            f'{self.level:>2d}/{self._max_level_by_stars[self.stars]:>2d} '
            f'{self.main_stat:>17s}: {self._main_stat_scaling[self._stars][self._main_stat][self._level]:>4}'
        )
        for possible_substat in self._substat_roll_values:
            if possible_substat in self.substats:
                return_str += f' {self.substats[possible_substat]:>4}'
            else:
                return_str += '     '

        return return_str

class Flower(Artifact):

    _main_stats = ['HP']
    _slot = 'flower'


class Plume(Artifact):

    _main_stats = ['ATK']
    _slot = 'plume'


class Sands(Artifact):

    _main_stats = ['HP%', 'ATK%', 'DEF%',
                   'Elemental Master', 'Energy Rechage%']
    _slot = 'sands'


class Goblet(Artifact):

    _main_stats = ['HP%', 'ATK%', 'DEF%', 'Elemental Mastery',
                   'Elemental DMG%', 'Physical DMG%']
    _slot = 'goblet'


class Circlet(Artifact):

    _main_stats = ['HP%', 'ATK%', 'DEF%',
                   'ELemental Mastery', 'Crit Rate%', 'Crit DMG%']
    _slot = 'circlet'
