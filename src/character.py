from __future__ import absolute_import, annotations

import json
import os
import re

import numpy as np
import pandas as pd

from src import genshin_data
from src.weapon import Weapon

# Location of directory containing character json files
_character_dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "data", "characters")


class Character:
    def __init__(
        self, key: str, level: int, constellation: int, ascension: int, talent: list[int], weapon: Weapon, **kwargs
    ):

        # Save inputs
        self._key = key
        self._level = level
        self._constellation = constellation
        self._ascension = ascension
        self._talent = talent
        self._weapon = weapon

        # Interpret potential additional data
        self._crits = kwargs.setdefault("hitMode", "avgHits")
        self._amplifying_reaction = kwargs.setdefault("reactionMode", None)
        self._reaction_percentage = 100.0 if self.amplifying_reaction is not None else 0.0

        # Retrieve and save character data
        file_path = os.path.join(_character_dir_path, f"{key}.json")
        if not os.path.isfile(file_path):
            raise ValueError(f'Statistics for character "{key}" not found in GAS database.')
        with open(file_path, "r") as file_handle:
            character_data = json.load(file_handle)
        self._element = character_data["element"]
        self._weapon_type = character_data["weapon_type"]
        self._stars = character_data["stars"]
        self._initial_HP = character_data["initial_HP"]
        self._initial_ATK = character_data["initial_ATK"]
        self._initial_DEF = character_data["initial_DEF"]
        self._HP_ascension_scaling = character_data["HP_ascension_scaling"]
        self._ATK_ascension_scaling = character_data["ATK_ascension_scaling"]
        self._DEF_ascension_scaling = character_data["DEF_ascension_scaling"]
        self._ascension_stat = character_data["ascension_stat"]
        self._ascension_stat_scaling = character_data["ascension_stat_scaling"]
        self._passive = {}  # TODO
        self._stat_transfer = {}  # TODO

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

    @property
    def weapon(self) -> Weapon:
        return self._weapon

    @property
    def dmg_type(self) -> str:
        # TODO make this dependent on attack type (auto, skill, burst)
        return self._element
        # return self._dmg_type

    # @dmg_type.setter
    # def dmg_type(self, dmg_type: str):
    #     dmg_type = dmg_type.lower()
    #     if dmg_type not in ["physical", "pyro", "hydro", "cryo", "electro", "anemo", "geo", "healing"]:
    #         raise ValueError("Invalid damage type.")
    #     self._dmg_type = dmg_type

    @property
    def passive(self) -> dict[str, float]:
        return self._passive

    @property
    def crits(self) -> str:
        return self._crits

    @property
    def scaling_stat(self) -> str:
        # TODO Make different things scale differently
        return "atk"
        # return self._scaling_stat

    @property
    def amplifying_reaction(self) -> str:
        return self._amplifying_reaction

    @property
    def amplification_factor(self) -> float:
        if self.amplifying_reaction in ["hydro_vaporize", "pyro_melt"]:
            return 2
        elif self.amplifying_reaction in ["pyro_vaporize", "cryo_melt"]:
            return 1.5
        else:
            return 0.0

    @property
    def reaction_percentage(self) -> float:
        return self._reaction_percentage

    @property
    def stat_transfer(self) -> dict[str, dict[str, float]]:
        """Dictionary of dictionaries for dealing with dual scaling characters.

        First set of string keys is the destination stat
        Second set of string keys is the source stat
        Float values represent what percent of the source stat gets transfered to the destination stat

        For example:
        Mona: {
            "hydro_dmg_": {
                "enerRech_": 20.0
            }
        }

        Noelle C6 Ult at Talent 10: {
            "Total ATK": {
                "Total DEF": 140.0
            }
        }
        """
        return self._stat_transfer

    @property
    def ascension_stat(self) -> str:
        return self._ascension_stat

    @property
    def ascension_stat_value(self) -> float:
        ascension_value = self._ascension_stat_scaling[self.ascension]
        if "%" in self.ascension_stat:
            ascension_value *= 100
        return ascension_value

    def get_stats(self, useful_stats: list[str] = None) -> pd.Series:
        # Calculate base HP
        ascension_HP = self._HP_ascension_scaling[self.ascension]
        scaling_HP = genshin_data.character_stat_curves[f"GROW_CURVE_HP_S{self._stars}"][self.level]
        base_HP = self._initial_HP * scaling_HP + ascension_HP
        # Calculate base ATK
        ascension_ATK = self._ATK_ascension_scaling[self.ascension]
        scaling_ATK = genshin_data.character_stat_curves[f"GROW_CURVE_ATTACK_S{self._stars}"][self.level]
        base_ATK = self._initial_ATK * scaling_ATK + ascension_ATK
        # Calculate base DEF
        ascension_DEF = self._DEF_ascension_scaling[self.ascension]
        scaling_DEF = genshin_data.character_stat_curves[f"GROW_CURVE_HP_S{self._stars}"][self.level]
        # Yes, character DEF follows the same curve as HP.
        base_DEF = self._initial_DEF * scaling_DEF + ascension_DEF
        # Create stats
        stats = pd.Series(0.0, index=useful_stats)
        if "baseHp" in useful_stats:
            stats["baseHp"] += base_HP
        if "baseAtk" in useful_stats:
            stats["baseAtk"] += base_ATK
        if "baseDef" in useful_stats:
            stats["baseDef"] += base_DEF
        if "critRate_" in useful_stats:
            stats["critRate_"] += 5
        if "critDMG_" in useful_stats:
            stats["critDMG_"] += 50
        if "enerRech_" in useful_stats:
            stats["enerRech_"] += 100
        if self.ascension_stat in useful_stats:
            stats[self.ascension_stat] += self.ascension_stat_value
        for stat, value in self.passive.items():
            if stat in useful_stats:
                stats[stat] += value
        if self.weapon is None:
            raise ValueError("Character does not have a weapon.")
        stats += self.weapon.get_stats(useful_stats)
        return stats

    def __str__(self) -> str:
        return f"{self.name}, Level: {self.level}"

    def __repr__(self) -> str:
        return f"<__src__.character.Character: {self.name}>"
