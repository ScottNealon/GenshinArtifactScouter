import logging
import math

import numpy as np
import pandas as pd

import genshindata
from weapon import Weapon

log = logging.getLogger(__name__)


class Character:
    def __init__(
        self,
        name: str,
        level: int,
        ascension: int,
        passive: dict[str],
        dmg_type: str,
        weapon: Weapon,
        scaling_stat: str = None,
        crits: str = None,
        amplifying_reaction: str = None,
        reaction_percentage: float = None,
    ):

        if name.lower() not in genshindata.character_stats:
            raise ValueError("Invalid character name.")
        self._name = name.lower()

        self.level = level
        self.ascension = ascension

        self._get_stat_arrays()

        self.passive = passive
        self.dmg_type = dmg_type
        self.weapon = weapon

        # Defaulted inputs
        if scaling_stat is None:
            self.scaling_stat = "ATK"
        else:
            self.scaling_stat = scaling_stat

        if crits is None:
            self.crits = "avgHit"
        else:
            self.crits = crits

        self.amplifying_reaction = amplifying_reaction

        if reaction_percentage is None:
            if self.amplifying_reaction is None:
                self.reaction_percentage = 0
            else:
                self.reaction_percentage = 1
        else:
            self.reaction_percentage = reaction_percentage

        # Updated
        self._update_stats = True

    @property
    def name(self):
        return self._name

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level: int):
        if level < 1 or level > 90:
            raise ValueError("Invalid character level")
        self._level = level
        # If character has already been instantiated, default ascension to highest valid
        if hasattr(self, "_ascension"):
            intended_ascension = sum(level >= np.array([20, 40, 50, 60, 70, 80]))
            if self.ascension != intended_ascension:
                self.ascension = intended_ascension
                if level in [20, 40, 50, 60, 70, 80]:
                    log.warning(
                        f"Character {self.name.title()} set to level {level}. Ascension defaulted to {intended_ascension}."
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
        # If character has alredy been instantiated, default level to middle of valid if not in range
        min_level = [0, 20, 40, 50, 60, 70, 80][ascension]
        max_level = [20, 40, 50, 60, 70, 80, 90][ascension]
        if not min_level <= self.level <= max_level:
            self.level = int((min_level + max_level) / 2)
            log.warning(f"Character {self.name.title()} set to Ascension {ascension}. Level defaulted to {self.level}.")
        self._update_stats = True

    def _get_stat_arrays(self):

        # Retrieve all stats from database
        self._stats = genshindata.character_stats[self.name]

        # Retrieve base stat arrays
        self._base_HP_scaling = genshindata.character_stat_curves[self._stats["PropGrowCurves"]["FIGHT_PROP_BASE_HP"]]
        self._base_ATK_scaling = genshindata.character_stat_curves[
            self._stats["PropGrowCurves"]["FIGHT_PROP_BASE_ATTACK"]
        ]
        self._base_DEF_scaling = genshindata.character_stat_curves[
            self._stats["PropGrowCurves"]["FIGHT_PROP_BASE_DEFENSE"]
        ]

        # Retrieve base stat increases due to ascension
        self._promote_stats = genshindata.character_promote_stats[self._stats["AvatarPromoteId"]]

        # Retireve ascension stat increases
        self._ascension_stat_str = list(self._promote_stats.keys())[3]
        self._ascenion_stat_scaling = self._promote_stats[self._ascension_stat_str]
        self._ascension_stat = genshindata.promote_stats_map[self._ascension_stat_str]

    @property
    def base_HP(self):
        base_HP = self._stats["HpBase"]
        ascension_HP = self._promote_stats["FIGHT_PROP_BASE_HP"][self.ascension]
        scaling_HP = self._base_HP_scaling[self.level]
        return base_HP * scaling_HP + ascension_HP

    @property
    def base_ATK(self):
        base_ATK = self._stats["AttackBase"]
        ascension_ATK = self._promote_stats["FIGHT_PROP_BASE_ATTACK"][self.ascension]
        scaling_ATK = self._base_ATK_scaling[self.level]
        return base_ATK * scaling_ATK + ascension_ATK

    @property
    def base_DEF(self):
        base_DEF = self._stats["DefenseBase"]
        ascension_DEF = self._promote_stats["FIGHT_PROP_BASE_DEFENSE"][self.ascension]
        scaling_DEF = self._base_DEF_scaling[self.level]
        return base_DEF * scaling_DEF + ascension_DEF

    @property
    def ascension_stat(self):
        return self._ascension_stat

    @property
    def ascension_stat_value(self):
        ascension_value = self._ascenion_stat_scaling[self.ascension]
        if "%" in self.ascension_stat:
            ascension_value *= 100
        return ascension_value

    # @ascension_stat_value.setter
    # def ascension_stat_value(self, ascension_stat_value: float):
    #     if ascension_stat_value < 0:
    #         raise ValueError("Invalid ascension stat value.")
    #     self._ascension_stat_value = ascension_stat_value
    #     self._update_stats = True

    @property
    def passive(self):
        return self._passive

    @passive.setter
    def passive(self, passive: dict[str]):
        for key in passive:
            if key not in genshindata.stat_names:
                raise ValueError("Invalid passive.")
        self._passive = passive
        self._update_stats = True

    @property
    def weapon(self):
        return self._weapon

    @weapon.setter
    def weapon(self, weapon: Weapon):
        if type(weapon) != Weapon:
            raise ValueError("Weapon must be a weapon.")
        self._weapon = weapon
        self._update_stats = True

    @property
    def stats(self):
        if self._update_stats:
            self.update_stats()
        return self._baseStats

    def update_stats(self):
        self._baseStats = pd.Series(0.0, index=genshindata.stat_names)
        self._baseStats["Base HP"] += self.base_HP
        self._baseStats["Base ATK"] += self.base_ATK
        self._baseStats["Base DEF"] += self.base_DEF
        self._baseStats["Crit Rate%"] += 5
        self._baseStats["Crit DMG%"] += 50
        self._baseStats[self.ascension_stat] += self.ascension_stat_value
        for stat, value in self.passive.items():
            self._baseStats[stat] += value
        self._baseStats += self.weapon.stats
        self._update_stats = False

    @property
    def crits(self):
        return self._crits

    @crits.setter
    def crits(self, crits: str):
        if crits not in ["avgHit", "hit", "critHit"]:
            raise ValueError("Invalid crit type.")
        self._crits = crits

    @property
    def scaling_stat(self):
        return self._scaling_stat

    @scaling_stat.setter
    def scaling_stat(self, scaling_stat: str):
        if scaling_stat not in ["ATK", "DEF", "HP"]:
            raise ValueError("Invalid scaling stat.")
        self._scaling_stat = scaling_stat

    @property
    def dmg_type(self):
        return self._dmg_type

    @dmg_type.setter
    def dmg_type(self, dmg_type: str):
        if dmg_type not in ["Physical", "Elemental", "Healing"]:
            raise ValueError("Invalid damage type.")
        self._dmg_type = dmg_type

    @property
    def amplifying_reaction(self):
        return self._amplifying_reaction

    @amplifying_reaction.setter
    def amplifying_reaction(self, amplifying_reaction: str):
        if amplifying_reaction is None:
            self._amplifying_reaction = amplifying_reaction
            self._amplification_factor = 0
        elif type(amplifying_reaction) != str:
            raise ValueError("Amplifying reaction must be provided as a string.")
        else:
            # Convert to proper format if supplied normally
            amplifying_reaction = amplifying_reaction.lower().replace(" ", "_")
            # Convert "reverse" inputs
            if "reverse" in amplifying_reaction:
                if "vaporize" in amplifying_reaction:
                    amplifying_reaction = "pyro_vaporize"
                elif "melt" in amplifying_reaction:
                    amplifying_reaction = "cryo_melt"
            # Validate inputs
            if amplifying_reaction not in ["hydro_vaporize", "pyro_vaporize", "pyro_melt", "cryo_melt", "None"]:
                raise ValueError("Invalid amplification reaction")
            # Save results
            self._amplifying_reaction = amplifying_reaction
            self._amplification_factor = 2 if amplifying_reaction in ["hydro_vaporize", "pyro_melt"] else 1.5

    @property
    def amplification_factor(self):
        return self._amplification_factor

    @property
    def reaction_percentage(self):
        return self._reaction_percentage

    @reaction_percentage.setter
    def reaction_percentage(self, reaction_percentage):
        if reaction_percentage < 0 or reaction_percentage > 1:
            raise ValueError("Invalid reaction percentage.")
        self._reaction_percentage = reaction_percentage

    def __str__(self):
        return f"{self.name}, Level: {self.level}"
