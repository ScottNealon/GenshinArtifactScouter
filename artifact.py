import copy
import math
from typing import Union

import numpy as np
import pandas as pd

import genshindata as gd


class Artifact:

    # To be overwritten by inherited types
    _main_stats = []
    _slot = ""

    def __init__(self, set_str: str, main_stat: str, stars: int, level: int, substats: dict[str]):

        # Validated inputs
        self.set = set_str
        self.stars = stars
        self.main_stat = main_stat
        self.level = level
        self.substats = substats

    @property
    def set(self):
        return self._set

    @set.setter
    def set(self, set_str: str):
        if set_str not in gd.valid_sets:
            raise ValueError("Invalid set.")
        self._set = set_str

    @property
    def stars(self):
        return self._stars

    @stars.setter
    def stars(self, stars: int):
        if stars < 1 or stars > 5:
            raise ValueError("Invalid artifact number of stars.")
        if hasattr(self, "stars"):
            if self.stars is not None:
                raise ValueError(
                    "TODO: I do not curerntly have implemented a method for updating substats/level nicely if you update stars."
                )
        self._stars = stars

    @property
    def main_stat(self):
        return self._main_stat

    @main_stat.setter
    def main_stat(self, main_stat):
        if main_stat not in self._main_stats:
            raise ValueError("Invalid main stat.")
        self._main_stat = main_stat

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level: int):
        if level < 0:
            raise ValueError("Invalid artifact level: Must be positive.")
        elif level > gd.max_level_by_stars[self.stars]:
            raise ValueError(
                f"Invalid artifact level: {self.stars}-star artifacts must be less than or equal to level {gd.max_level_by_stars[self.stars]}."
            )
        # elif hasattr(self, 'substats'):
        #     if self.stars + math.floor(level / 4) - 1 < len(self.substats):
        #         raise ValueError(
        #             f'Cannot lower level below {self.stars + math.floor(level / 4) - 1} while there are {len(self.substats)} substats.')
        self._level = level

    @property
    def substats(self):
        return self._substats

    @substats.setter
    def substats(self, substats: Union[dict[str], pd.DataFrame]):
        if type(substats) is dict:
            if len(substats) > 4:
                raise ValueError("Invalid number of substats: cannot have more than 4 substats")
            elif len(substats) > self.stars + math.floor(self.level / 4) - 1:
                raise ValueError(
                    "Invalid number of substats: cannot have more substats than limited by stars and level"
                )
            self._substats = copy.deepcopy(substats)

        elif type(substats) is pd.DataFrame:
            self._substats = copy.deepcopy(substats)
        else:
            raise TypeError("Invalid substat type.")

    def add_substat(self, stat: str, value: float):
        if type(self.substats) is pd.DataFrame:
            raise ValueError("Changing substats of Dataframes not yet implemented.")  # TODO
        if stat not in gd.substat_roll_values:
            raise ValueError("Invalid stat name.")
        elif stat in self.substats:
            raise ValueError("Cannot add substat that already exists on artifact.")
        elif len(self.substats) >= 4:
            raise ValueError("Cannot have more than 4 substats.")
        self._substats[stat] = value

    def increase_substat(self, stat: str, value: int):
        if type(self.substats) is pd.DataFrame:
            raise ValueError("Changing substats of Dataframes not yet implemented.")  # TODO
        if stat not in gd.substat_roll_values:
            raise ValueError("Invalid substat name.")
        elif stat not in self.substats:
            raise ValueError("Substat does not exist on artifact.")
        self._substats[stat] += value

    def roll_substat(self, stat: str, roll: int):
        if type(self.substats) is pd.DataFrame:
            raise ValueError("Changing substats of Dataframes not yet implemented.")  # TODO
        if stat not in gd.substat_roll_values:
            raise ValueError("Invalid substat name.")
        elif stat not in self.substats.keys():
            raise ValueError("Substat does not exist on artifact.")
        self._substats[stat] += gd.substat_roll_values[stat][self.stars][roll]

    # TODO: Have this return the set of rolls that were used to generate self.value.
    # @property
    # def rolls(self):
    #     return None

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
