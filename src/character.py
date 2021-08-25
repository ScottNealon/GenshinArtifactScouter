from __future__ import absolute_import, annotations

import logging
import math
import random

import numpy as np
import pandas as pd

from . import genshin_data
from .weapon import Weapon

log = logging.getLogger(__name__)


class Character:
    def __init__(
        self,
        name: str,
        level: int,
        ascension: int,
        weapon: Weapon,
        dmg_type: str,
        passive: dict[str],
        scaling_stat: str = "ATK",
        crits: str = "avgHit",
        amplifying_reaction: str = None,
        reaction_percentage: float = 0.0,
        stat_transfer: dict[str, dict[str, float]] = {},
    ):

        # Validate inputs
        name = name.lower()
        if name not in genshin_data.character_stats:
            raise ValueError("Invalid character name.")

        # Save inputs
        self._name = name
        self.level = level
        self.ascension = ascension
        self.weapon = weapon
        self.dmg_type = dmg_type
        self.passive = passive
        self.scaling_stat = scaling_stat
        self.crits = crits
        self.amplifying_reaction = amplifying_reaction
        self.reaction_percentage = reaction_percentage
        self.stat_transfer = stat_transfer

        # Get stats
        self._get_stat_arrays()
        self._update_stats = True

    @property
    def name(self) -> str:
        """Return name of character. Name does not have a setter as this should not change after initialization."""
        return self._name

    @property
    def level(self) -> int:
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
    def ascension(self) -> int:
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

    @property
    def weapon(self) -> Weapon:
        return self._weapon

    @weapon.setter
    def weapon(self, weapon: Weapon):
        if weapon is not None:
            if type(weapon) != Weapon:
                raise ValueError("Weapon must be a weapon.")
        self._weapon = weapon
        self._update_stats = True

    @property
    def dmg_type(self) -> str:
        return self._dmg_type

    @dmg_type.setter
    def dmg_type(self, dmg_type: str):
        dmg_type = dmg_type.lower()
        if dmg_type not in ["physical", "pyro", "hydro", "cryo", "electro", "anemo", "geo", "healing"]:
            raise ValueError("Invalid damage type.")
        self._dmg_type = dmg_type

    @property
    def passive(self) -> dict[str, float]:
        return self._passive

    @passive.setter
    def passive(self, passive: dict[str]):
        for key in passive:
            if key not in genshin_data.stat_names:
                raise ValueError("Invalid passive.")
        self._passive = passive
        self._update_stats = True

    @property
    def crits(self) -> str:
        return self._crits

    @crits.setter
    def crits(self, crits: str):
        if crits not in ["avgHit", "hit", "critHit"]:
            raise ValueError("Invalid crit type.")
        self._crits = crits

    @property
    def scaling_stat(self) -> str:
        return self._scaling_stat

    @scaling_stat.setter
    def scaling_stat(self, scaling_stat: str):
        if scaling_stat not in ["ATK", "DEF", "HP"]:
            raise ValueError("Invalid scaling stat.")
        self._scaling_stat = scaling_stat

    @property
    def amplifying_reaction(self) -> str:
        return self._amplifying_reaction

    @amplifying_reaction.setter
    def amplifying_reaction(self, amplifying_reaction: str):
        if amplifying_reaction is None:
            self._amplifying_reaction = None
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
            if amplifying_reaction not in ["hydro_vaporize", "pyro_vaporize", "pyro_melt", "cryo_melt"]:
                raise ValueError("Invalid amplification reaction")
            # Save results
            self._amplifying_reaction = amplifying_reaction

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

    @reaction_percentage.setter
    def reaction_percentage(self, reaction_percentage):
        if reaction_percentage < 0.0 or reaction_percentage > 100.0:
            raise ValueError("Invalid reaction percentage.")
        self._reaction_percentage = reaction_percentage

    @property
    def stat_transfer(self) -> dict[str, dict[str, float]]:
        """Dictionary of dictionaries for dealing with dual scaling characters.

        First set of string keys is the destination stat
        Second set of string keys is the source stat
        Float values represent what percent of the source stat gets transfered to the destination stat

        For example:
        Mona: {
            "Hydro DMG%": {
                "Energy Recharge%": 20.0
            }
        }

        TODO: Actually make this work
        Noelle C6 Ult at Talent 10: {
            "Total ATK": {
                "Total DEF": 140.0
            }
        }
        """
        return self._stat_transfer

    @stat_transfer.setter
    def stat_transfer(self, stat_transfer: dict[str, dict[str, float]]):
        # Validate input
        for destination_stat, source_stats in stat_transfer.items():
            if destination_stat not in genshin_data.stat_names:
                raise ValueError("Invalid stat name")
            for source_stat in source_stats:
                if source_stat not in genshin_data.stat_names:
                    raise ValueError("Invalid stat name")
        # Save data
        self._stat_transfer = stat_transfer

    def _get_stat_arrays(self):

        # Retrieve all stats from database
        self._stats = genshin_data.character_stats[self.name]

        # Retrieve base stat arrays
        self._base_HP_scaling = genshin_data.character_stat_curves[self._stats["PropGrowCurves"]["FIGHT_PROP_BASE_HP"]]
        self._base_ATK_scaling = genshin_data.character_stat_curves[
            self._stats["PropGrowCurves"]["FIGHT_PROP_BASE_ATTACK"]
        ]
        self._base_DEF_scaling = genshin_data.character_stat_curves[
            self._stats["PropGrowCurves"]["FIGHT_PROP_BASE_DEFENSE"]
        ]

        # Retrieve base stat increases due to ascension
        self._promote_stats = genshin_data.character_promote_stats[self._stats["AvatarPromoteId"]]

        # Retireve ascension stat increases
        self._ascension_stat_str = list(self._promote_stats.keys())[3]
        self._ascenion_stat_scaling = self._promote_stats[self._ascension_stat_str]
        self._ascension_stat = genshin_data.promote_stats_map[self._ascension_stat_str]

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

    @property
    def stats(self):
        if self._update_stats:
            self.update_stats()
        return self._baseStats

    def update_stats(self):
        self._baseStats = pd.Series(0.0, index=genshin_data.stat_names)
        self._baseStats["Base HP"] += self.base_HP
        self._baseStats["Base ATK"] += self.base_ATK
        self._baseStats["Base DEF"] += self.base_DEF
        self._baseStats["Crit Rate%"] += 5
        self._baseStats["Crit DMG%"] += 50
        self._baseStats["Energy Recharge%"] += 100
        self._baseStats[self.ascension_stat] += self.ascension_stat_value
        for stat, value in self.passive.items():
            self._baseStats[stat] += value
        if self.weapon is None:
            raise ValueError("Character does not have a weapon.")
        self._baseStats += self.weapon.stats
        self._update_stats = False

    @property
    def condensable_substats(self) -> list[str]:
        """Return a list of substats that can be 'condensed' when evaluating potential"""

        # Scaling stat
        if self.scaling_stat == "ATK":
            condensable_substats = ["DEF", "DEF%", "HP", "HP%", "Energy Recharge%"]
        elif self.scaling_stat == "DEF":
            condensable_substats = ["ATK", "ATK%", "HP", "HP%", "Energy Recharge%"]
        elif self.scaling_stat == "HP":
            condensable_substats = ["ATK", "ATK%", "DEF", "DEF%", "Energy Recharge%"]
        # Elemental Mastery
        if self.amplifying_reaction is None:
            condensable_substats.append("Elemental Mastery")
        # Crits
        if self.crits == "always":
            condensable_substats.append("Crit Rate%")
        elif self.crits == "never":
            condensable_substats.append("Crit Rate%")
            condensable_substats.append("Crit DMG%")
        # Transforming stats
        for destination_stat, source_stats in self.stat_transfer.items():
            for source_stat in source_stats:
                if source_stat in condensable_substats:
                    condensable_substats.remove(source_stat)

        return condensable_substats

    def __str__(self):
        return f"{self.name}, Level: {self.level}"
