import copy
import itertools
import math
from typing import Union

import numpy as np
import pandas as pd

import genshindata


class Artifact:

    # To be overwritten by inherited types
    _main_stats = []
    _slot = ""

    def __init__(
        self,
        set_str: str,
        main_stat: str,
        stars: int,
        level: int,
        substats: dict[str] = None,
        substat_rolls: dict[str] = None,
    ):

        # Mutually exclusive inputs
        if (substats is not None) and (substat_rolls is not None):
            raise ValueError("substats and substat_rolls are mutually exclusive. Only one can be provided.")

        # Validated inputs
        self._set = set_str
        self._stars = stars
        self._main_stat = main_stat
        self._level = level

        if substats is not None:
            self._substats = substats
            self.calculate_substat_rolls()
        else:
            self._substat_rolls = substat_rolls
            self.calculate_substats()

    @property
    def set(self):
        return self._set

    @property
    def stars(self):
        return self._stars

    @property
    def main_stat(self):
        return self._main_stat

    @property
    def level(self):
        return self._level

    @property
    def substats(self):
        return self._substats

    @property
    def substat_rolls(self):
        return self._substat_rolls

    def calculate_substat_rolls(self):

        # Create empty dictionary
        self._substat_rolls = {}

        # Ignore if dataframe
        if type(self.substats) is pd.DataFrame:
            return

        # Resolve the trivial case
        if len(self.substats) == 0:
            return

        # Create list of lists of possible ways to generate value each individual roll
        possible_substat_rolls = []
        for substat_name, substat_value in self.substats.items():
            # Find the closest substat value
            value_array = np.asarray(list(genshindata.value2rolls[substat_name][self.stars].keys()))
            closest_value_index = (np.abs(value_array - substat_value)).argmin()
            closest_value = value_array[closest_value_index]
            possible_substat_rolls.append(genshindata.value2rolls[substat_name][self.stars][closest_value])

        # Iterate through combinations until some combination is valid ( = total_possible_rolls or +1)
        total_possible_rolls = max(0, self.stars - 2) + math.floor(self.level / 4)
        roll_combinations = list(itertools.product(*possible_substat_rolls))
        for roll_combination in roll_combinations:
            total_rolls = sum([len(rolls) for rolls in roll_combination])
            if total_rolls == total_possible_rolls or total_rolls == total_possible_rolls + 1:
                for substat_name, rolls in zip(self.substats, roll_combination):
                    self._substat_rolls[substat_name] = rolls
                return

        raise ValueError("Count not find a valid set of rolls to generate substat combination.")

    def calculate_substats(self):

        self._substats = {}
        for substat_name, substat_rolls in self.substat_rolls.items():
            self._substats[substat_name] = sum(substat_rolls)

    @property
    def stats(self):
        # Substats
        if type(self.substats) is pd.DataFrame:
            self._stats = copy.copy(self.substats)
        elif type(self.substats) is dict:
            self._stats = pd.Series(0.0, index=genshindata.stat_names)
            for substat, value in self.substats.items():
                self._stats[substat] += value
        # Main stat
        self._stats[self._main_stat] += genshindata.main_stat_scaling[self._stars][self._main_stat][self._level]
        return self._stats

    def to_string_table(self):
        return_str = (
            f"{type(self).__name__:>7s} "
            f"{self.stars:>d}* "
            f"{self.set.capitalize():>14} "
            f"{self.level:>2d}/{genshindata.max_level_by_stars[self.stars]:>2d} "
            f"{self.main_stat:>17s}: {genshindata.main_stat_scaling[self._stars][self._main_stat][self._level]:>4}"
        )
        for possible_substat in genshindata.substat_roll_values:
            if possible_substat in self.substats:
                if "%" in possible_substat:
                    return_str += f" {self.substats[possible_substat]:>4.1f}"
                else:
                    return_str += f" {self.substats[possible_substat]:>4}"
            else:
                return_str += "     "

        return return_str


class Flower(Artifact):

    _main_stats = ["HP"]


class Plume(Artifact):

    _main_stats = ["ATK"]


class Sands(Artifact):

    _main_stats = ["HP%", "ATK%", "DEF%", "Elemental Mastery", "Energy Recharge%"]


class Goblet(Artifact):

    _main_stats = ["HP%", "ATK%", "DEF%", "Elemental Mastery", "Elemental DMG%", "Physical DMG%"]


class Circlet(Artifact):

    _main_stats = ["HP%", "ATK%", "DEF%", "Elemental Mastery", "Crit Rate%", "Crit DMG%", "Healing Bonus%"]
