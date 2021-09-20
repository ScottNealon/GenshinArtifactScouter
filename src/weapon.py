from __future__ import annotations

import json
import logging
import os
import re

import numpy as np
import pandas as pd

from src import genshin_data

log = logging.getLogger("root")

# Location of directory containing weapon json files
_weapon_dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "data", "weapons")


class Weapon:
    def __init__(self, key: str, level: int, ascension: int, refinement: int, location: int):

        # Save inputs
        self._key = key
        self._level = level
        self._ascension = ascension
        self._refinement = refinement
        self._location = location

        # Retrieve and save weapon data
        file_path = os.path.join(_weapon_dir_path, f"{key}.json")
        if not os.path.isfile(file_path):
            raise ValueError(f'Statistics for weapon "{key}" not found in GAS database.')
        with open(file_path, "r") as file_handle:
            weapon_data = json.load(file_handle)
        self._weapon_type = weapon_data["weapon_type"]
        self._initial_ATK = weapon_data["initial_ATK"]
        self._base_ATK_scaling = weapon_data["base_ATK_scaling"]
        self._ATK_ascension_scaling = weapon_data["ATK_ascension_scaling"]
        self._ascension_stat = weapon_data.setdefault("ascension_stat", "atk_")
        self._base_ascension_stat = weapon_data.setdefault("base_ascension_stat", 0)
        self._ascension_stat_scaling = weapon_data.setdefault("ascension_stat_scaling", [0, 0, 0, 0, 0, 0, 0])
        self._passive = {}  # TODO

    @property
    def key(self) -> str:
        return self._key

    @property
    def name(self) -> str:
        return re.sub(r"(\w)([A-Z])", r"\1 \2", self.key)

    @property
    def level(self) -> int:
        return self._level

    @property
    def ascension(self) -> int:
        return self._ascension

    # TODO: Use this
    @property
    def refinement(self) -> int:
        return self._refinement

    @property
    def ascension_stat(self) -> str:
        return self._ascension_stat

    @property
    def ascension_stat_value(self) -> float:
        ascension_value = self._base_ascension_stat * self._ascension_stat_scaling[self.level]
        if "_" in self.ascension_stat:
            ascension_value *= 100
        return ascension_value

    @property
    def passive(self) -> dict[str]:
        return self._passive

    def get_stats(self, useful_stats: list[str]) -> pd.Series:
        # Calculate base ATK
        ascension_ATK = self._ATK_ascension_scaling[self.ascension]
        scaling_ATK = genshin_data.weapon_stat_curves[self._base_ATK_scaling][self.level]
        base_ATK = self._initial_ATK * scaling_ATK + ascension_ATK
        # Calculate ascension value
        ascension_scaling = genshin_data.weapon_stat_curves[self._ascension_stat_scaling][self.level]
        ascension_value = self._base_ascension_stat * ascension_scaling
        if "_" in self.ascension_stat:
            ascension_value *= 100
        # Create stats
        stats = pd.Series(0.0, index=useful_stats)
        if "baseAtk" in useful_stats:
            stats["baseAtk"] += base_ATK
        if self.ascension_stat in useful_stats:
            stats[self.ascension_stat] += ascension_scaling
        for key, value in self.passive.items():
            if key in useful_stats:
                stats[key] += value
        return stats

    def __str__(self) -> str:
        return f"{self.name}, Level: {self.level}"

    def __repr__(self) -> str:
        return f"<__src__.weapon.Weapon: {self.name}>"
