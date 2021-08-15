import logging
import re

import numpy as np
import pandas as pd

import genshindata

log = logging.getLogger(__name__)


class Weapon:
    def __init__(
        # self, name: str, level: int, baseATK: int, ascension_stat: str, ascension_stat_value: float, passive: dict[str]
        self,
        name: str,
        level: int,
        ascension: int,
        passive: dict[str],
    ):

        # Validated inputs
        # Capitalize words, leave existing capitals, then remove spaces
        name = " ".join(s[:1].upper() + s[1:] for s in name.split(" ")).replace(" ", "")
        if name not in genshindata.weapon_stats:
            raise ValueError("Invalid weapon name.")
        self._name = name

        self.level = level
        self.ascension = ascension

        self.passive = passive

        self._get_stat_arrays()

    @property
    def name(self):
        return self._name

    @property
    def name_formated(self):
        return re.sub(r"(\w)([A-Z])", r"\1 \2", self._name)

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level: int):
        if level < 1 or level > 90:
            raise ValueError("Invalid weapon level")
        self._level = level
        # If weapon has already been instantiated, default ascension to highest valid
        if hasattr(self, "_ascension"):
            intended_ascension = sum(level >= np.array([20, 40, 50, 60, 70, 80]))
            if self.ascension != intended_ascension:
                self.ascension = intended_ascension
                if level in [20, 40, 50, 60, 70, 80]:
                    log.warning(
                        f"Weapon {self.name.title()} set to level {level}. Ascension defaulted to {intended_ascension}."
                    )
        self._update_stats = True

    @property
    def ascension(self):
        return self._ascension

    @ascension.setter
    def ascension(self, ascension: int):
        if ascension < 0 or ascension > 6:
            raise ValueError("Invalid ascension")
        self._ascension = ascension
        # If weapon has alredy been instantiated, default level to middle of valid if not in range
        min_level = [0, 20, 40, 50, 60, 70, 80][ascension]
        max_level = [20, 40, 50, 60, 70, 80, 90][ascension]
        if not min_level <= self.level <= max_level:
            self.level = int((min_level + max_level) / 2)
            log.warning(f"Weapon {self.name.title()} set to Ascension {ascension}. Level defaulted to {self.level}.")
        self._update_stats = True

    def _get_stat_arrays(self):

        # Retrieve all stats from database
        self._base_stats = genshindata.weapon_stats[self.name]

        # Retrieve base stat arrays
        self._base_ATK_scaling = genshindata.weapon_stat_curves[
            self._base_stats["WeaponProp"]["FIGHT_PROP_BASE_ATTACK"]["Type"]
        ]

        # Retrieve base stat increases due to ascension
        self._promote_stats = genshindata.weapon_promote_stats[self._base_stats["WeaponPromoteId"]]

        # Retireve ascension stat increases
        if len(self._base_stats["WeaponProp"]) > 1:
            self._ascension_stat_str = list(self._base_stats["WeaponProp"])[1]
            self._ascension_stat = genshindata.promote_stats_map[self._ascension_stat_str]
            self._ascension_stat_dict = self._base_stats["WeaponProp"][self._ascension_stat_str]
            self._ascension_stat_initial_value = self._ascension_stat_dict["InitValue"]

            ascension_stat_scaling_str = self._ascension_stat_dict["Type"]
            self._ascension_stat_scaling = genshindata.weapon_stat_curves[ascension_stat_scaling_str]
        else:
            self._ascension_stat = "ATK"
            self._ascension_stat_initial_value = 0
            self._ascension_stat_scaling = np.zeros([1, 91])

    @property
    def base_ATK(self):
        base_ATK = self._base_stats["WeaponProp"]["FIGHT_PROP_BASE_ATTACK"]["InitValue"]
        ascension_ATK = self._promote_stats["FIGHT_PROP_BASE_ATTACK"][self.ascension]
        scaling_ATK = self._base_ATK_scaling[self.level]
        return base_ATK * scaling_ATK + ascension_ATK

    @property
    def ascension_stat(self):
        return self._ascension_stat

    @property
    def ascension_stat_value(self):
        ascension_value = self._ascension_stat_initial_value * self._ascension_stat_scaling[self.level]
        if "%" in self.ascension_stat:
            ascension_value *= 100
        return ascension_value

    @property
    def passive(self):
        return self._passive

    @passive.setter
    def passive(self, passive: dict[str]):
        for key, value in passive.items():
            if key not in genshindata.stat_names:
                raise ValueError("Invalid passive stat.")
            elif value < 0:
                raise ValueError("Invalid passive stat value.")
        self._passive = passive

    @property
    def stats(self):
        self._stats = pd.Series(0.0, index=genshindata.stat_names)
        self._stats["Base ATK"] += self.base_ATK
        self._stats[self.ascension_stat] += self.ascension_stat_value
        for key, value in self.passive.items():
            self._stats[key] += value
        return self._stats

    def __str__(self):
        return f"{self.name}, Level: {self.level}"
