import copy
import itertools
import math
from typing import Union

import numpy as np
import pandas as pd

import genshindata as gd


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

        # Resolve the trivial case
        if len(self.substats) == 0:
            return

        # Create list of lists of possible ways to generate value each individual roll
        possible_substat_rolls = []
        for substat_name, substat_value in self.substats.items():
            # Find the closest substat value
            value_array = np.asarray(list(gd.value2rolls[substat_name][self.stars].keys()))
            closest_value_index = (np.abs(value_array - substat_value)).argmin()
            closest_value = value_array[closest_value_index]
            possible_substat_rolls.append(gd.value2rolls[substat_name][self.stars][closest_value])

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

    # @substats.setter
    # def substats(self, substats: Union[dict[str], pd.DataFrame]):
    #     if type(substats) is dict:
    #         if len(substats) > 4:
    #             raise ValueError("Invalid number of substats: cannot have more than 4 substats")
    #         elif len(substats) > self.stars + math.floor(self.level / 4) - 1:
    #             raise ValueError(
    #                 "Invalid number of substats: cannot have more substats than limited by stars and level"
    #             )
    #         self._substats = copy.deepcopy(substats)

    #     elif type(substats) is pd.DataFrame:
    #         self._substats = copy.deepcopy(substats)
    #     else:
    #         raise TypeError("Invalid substat type.")

    # def add_substat(self, stat: str, value: float):
    #     if type(self.substats) is pd.DataFrame:
    #         raise ValueError("Changing substats of Dataframes not yet implemented.")  # TODO
    #     if stat not in gd.substat_roll_values:
    #         raise ValueError("Invalid stat name.")
    #     elif stat in self.substats:
    #         raise ValueError("Cannot add substat that already exists on artifact.")
    #     elif len(self.substats) >= 4:
    #         raise ValueError("Cannot have more than 4 substats.")
    #     self._substats[stat] = value

    # def increase_substat(self, stat: str, value: int):
    #     if type(self.substats) is pd.DataFrame:
    #         raise ValueError("Changing substats of Dataframes not yet implemented.")  # TODO
    #     if stat not in gd.substat_roll_values:
    #         raise ValueError("Invalid substat name.")
    #     elif stat not in self.substats:
    #         raise ValueError("Substat does not exist on artifact.")
    #     self._substats[stat] += value

    # def roll_substat(self, stat: str, roll: int):
    #     if type(self.substats) is pd.DataFrame:
    #         raise ValueError("Changing substats of Dataframes not yet implemented.")  # TODO
    #     if stat not in gd.substat_roll_values:
    #         raise ValueError("Invalid substat name.")
    #     elif stat not in self.substats.keys():
    #         raise ValueError("Substat does not exist on artifact.")
    #     self._substats[stat] += gd.substat_roll_values[stat][self.stars][roll]

    @property
    def stats(self):
        # Substats
        if type(self.substats) is pd.DataFrame:
            self._stats = copy.copy(self.substats)
        elif type(self.substats) is dict:
            self._stats = pd.Series(0.0, index=gd.stat_names)
            for substat, value in self.substats.items():
                self._stats[substat] += value
        # Main stat
        self._stats[self._main_stat] += gd.main_stat_scaling[self._stars][self._main_stat][self._level]
        return self._stats

    @property
    def slot(self):
        return self._slot

    def to_string_table(self):
        return_str = (
            f"{self.slot.capitalize():>7s} "
            f"{self.stars:>d}* "
            f"{self.set.capitalize():>14} "
            f"{self.level:>2d}/{gd.max_level_by_stars[self.stars]:>2d} "
            f"{self.main_stat:>17s}: {gd.main_stat_scaling[self._stars][self._main_stat][self._level]:>4}"
        )
        for possible_substat in gd.substat_roll_values:
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
    _slot = "flower"


class Plume(Artifact):

    _main_stats = ["ATK"]
    _slot = "plume"


class Sands(Artifact):

    _main_stats = ["HP%", "ATK%", "DEF%", "Elemental Mastery", "Energy Recharge%"]
    _slot = "sands"


class Goblet(Artifact):

    _main_stats = ["HP%", "ATK%", "DEF%", "Elemental Mastery", "Elemental DMG%", "Physical DMG%"]
    _slot = "goblet"


class Circlet(Artifact):

    _main_stats = ["HP%", "ATK%", "DEF%", "Elemental Mastery", "Crit Rate%", "Crit DMG%", "Healing Bonus%"]
    _slot = "circlet"


str2type = {"flower": Flower, "plume": Plume, "sands": Sands, "goblet": Goblet, "circlet": Circlet}

type2str = {Flower: "flower", Plume: "plume", Sands: "sands", Goblet: "goblet", Circlet: "circlet"}
