from __future__ import annotations

import copy
import itertools
import math

import numpy as np
import pandas as pd

from src import genshin_data


class Artifact:

    # To be overwritten by inherited types
    _main_stats = []

    def __init__(
        self,
        setKey: str,
        level: int,
        rarity: int,
        mainStatKey: str,
        substats: list[dict[str, float]],
        index: int = np.nan,
        **kwargs,  # Ignore slotKey, location, and lock
    ):
        # Argument nameing scheme aligns with GOOD standardizatoin

        # Save inputs
        self._index = index
        self._stars = rarity
        self._main_stat = mainStatKey
        self._level = level
        self._set = setKey
        self._substats = substats

        # Interpret potential additional data
        self._exclude = kwargs.setdefault("exclude", False)

        # Calculate substat rolls from values
        # self.calculate_substat_rolls()

    @property
    def index(self) -> int:
        return self._index

    @property
    def stars(self) -> int:
        return self._stars

    @property
    def max_level(self) -> int:
        return [np.nan, 4, 4, 12, 16, 20][self.stars]

    @property
    def main_stat(self) -> str:
        return self._main_stat

    @property
    def level(self) -> int:
        return self._level

    @property
    def set(self) -> str:
        return self._set

    @property
    def slot(self) -> type:
        return type(self)

    @property
    def substats(self) -> list[dict[str, float]]:
        return self._substats

    @property
    def substat_names(self) -> list[str]:
        return [value["key"] for value in self.substats]

    @property
    def exclude(self) -> bool:
        return self._exclude

    # TODO Reimplement

    # @property
    # def substat_rolls(self) -> list[dict[str, list[int]]]:
    #     return self._substat_rolls

    # def calculate_substat_rolls(self):

    #     # Create empty dictionary
    #     self._substat_rolls = {}

    #     # Ignore if dataframe
    #     if type(self.substats) is pd.DataFrame:
    #         return

    #     # Resolve the trivial case
    #     if len(self.substats) == 0:
    #         return

    #     # Create list of lists of possible ways to generate value each individual roll
    #     possible_substat_rolls = []
    #     for substat_name, substat_value in self.substats.items():
    #         # Find the closest substat value
    #         value_array = np.asarray(list(genshin_data.value2rolls[substat_name][self.stars].keys()))
    #         closest_value_index = (np.abs(value_array - substat_value)).argmin()
    #         closest_value = value_array[closest_value_index]
    #         possible_substat_rolls.append(genshin_data.value2rolls[substat_name][self.stars][closest_value])

    #     # Iterate through combinations until some combination is valid ( = total_possible_rolls or +1)
    #     total_possible_rolls = max(0, self.stars - 2) + math.floor(self.level / 4)
    #     roll_combinations = list(itertools.product(*possible_substat_rolls))
    #     for roll_combination in roll_combinations:
    #         total_rolls = sum([len(rolls) for rolls in roll_combination])
    #         if total_rolls == total_possible_rolls or total_rolls == total_possible_rolls + 1:
    #             for substat_name, rolls in zip(self.substats, roll_combination):
    #                 self._substat_rolls[substat_name] = rolls
    #             return

    #     raise ValueError("Count not find a valid set of rolls to generate substat combination.")

    def get_stats(self, leveled: bool = False):
        # Substats
        if type(self.substats) is pd.DataFrame:
            self._stats = copy.copy(self.substats)
        else:
            self._stats = pd.Series(0.0, index=genshin_data.pandas_headers)
            for substat in self.substats:
                self._stats[substat["key"]] += substat["value"]
        # Main stat
        if leveled:
            self._stats[self.main_stat] += genshin_data.main_stat_scaling[self.stars][self.main_stat][self.max_level]
        else:
            self._stats[self.main_stat] += genshin_data.main_stat_scaling[self.stars][self.main_stat][self.level]
        return self._stats

    def to_string_table(self) -> str:
        short_set_name = genshin_data.artifact_set_shortened[self.set]
        return_str = (
            f"#{self.index:>4} "
            f"{type(self).__name__:>7s} "
            f"{self.stars:>d}* "
            f"{short_set_name:>14} "
            f"{self.level:>2d}/{genshin_data.max_level_by_stars[self.stars]:>2d} "
            f"{genshin_data.stat2output_map[self.main_stat]:>17s}: "
            f"{genshin_data.main_stat_scaling[self._stars][self._main_stat][self._level]:>4}"
        )
        for possible_substat in genshin_data.substat_roll_values:
            if possible_substat in self.substat_names:
                substat_value = next(
                    substat["value"] for substat in self.substats if substat["key"] == possible_substat
                )
                if "_" in possible_substat:  # Percentage
                    return_str += f" {substat_value:>4.1f}"
                else:
                    return_str += f" {substat_value:>4}"
            else:
                return_str += "     "

        return return_str

    def to_short_string_table(self) -> str:
        return_str = f"{f'#{self.name}':>5} " f"{self.level:>2d}/{genshin_data.max_level_by_stars[self.stars]:>2d} "
        for possible_substat in genshin_data.substat_roll_values:
            if possible_substat in self.substat_names:
                if "_" in possible_substat:
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

    _main_stats = ["hp_", "atk_", "def_", "eleMas", "enerRech_"]


class Goblet(Artifact):

    _main_stats = [
        "hp_",
        "atk_",
        "def_",
        "eleMas",
        "physical_dmg_",
        "pyro_dmg_",
        "hydro_dmg_",
        "cryo_dmg_",
        "electro_dmg_",
        "anemo_dmg_",
        "geo_dmg_",
    ]


class Circlet(Artifact):

    _main_stats = ["hp_", "atk_", "def_", "eleMas", "critRate_", "critDMG_", "heal_"]
