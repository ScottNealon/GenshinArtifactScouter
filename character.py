import numpy as np
import pandas as pd

import substat as sub
import artifact as art
import artifacts as arts
import weapon as weap


class Character:

    _stat_names = ['Base HP', 'Base ATK', 'Base DEF', 'HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%',
                   'Elemental DMG%', 'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%']

    def __init__(self, name: str, level: int, baseHP: int, baseATK: int, baseDEF: int, ascension_stat: str, ascension_stat_value: float, passive: dict[str],
                 dmg_type: str, weapon: weap.Weapon, artifacts: arts.Artifacts = None, scaling_stat: str = None, crits: str = None, amplifying_reaction: str = None,
                 reaction_percentage: float = None):

        # Undefaulted inputs
        self.name = name
        self.level = level
        self.ascension_stat = ascension_stat
        self.ascension_stat_value = ascension_stat_value
        self.passive = passive
        self.weapon = weapon
        self.dmg_type = dmg_type

        # Defaulted inputs
        if crits is None:
            self.crits = 'average'
        else:
            self.crits = crits

        if scaling_stat is None:
            self.scaling_stat = 'ATK'
        else:
            self.scaling_stat = scaling_stat

        if artifacts is None:
            self.artifacts = arts.Artifacts(
                flower=None, plume=None, sands=None, goblet=None, circlet=None)
        else:
            self.artifacts = artifacts

        self.amplifying_reaction = amplifying_reaction

        if reaction_percentage is None:
            if self.amplifying_reaction is None:
                self.reaction_percentage = 0
            else:
                self.reaction_percentage = 1
        else:
            self.reaction_percentage = reaction_percentage

        self._baseStats = pd.Series(0.0, index=self._stat_names)
        self._baseStats['Base HP'] += baseHP
        self._baseStats['Base ATK'] += baseATK
        self._baseStats['Base DEF'] += baseDEF
        self._baseStats['Crit Rate%'] += 5
        self._baseStats['Crit DMG%'] += 50
        self._baseStats[ascension_stat] += ascension_stat_value
        for stat, value in self.passive.items():
            self._baseStats[stat] += value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name

    @property
    def weapon(self):
        return self._weapon

    @weapon.setter
    def weapon(self, weapon: weap.Weapon):
        self._weapon = weapon
        self._update_stats = True

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level: int):
        if level < 1 or level > 90:
            raise ValueError('Invalid character level')
        else:
            self._level = level

    @property
    def ascension_stat(self):
        return self._ascension_stat

    @ascension_stat.setter
    def ascension_stat(self, ascension_stat: str):
        if ascension_stat not in self._stat_names:
            raise ValueError('Invalid ascension stat.')
        else:
            self._ascension_stat = ascension_stat
            self._update_stats = True

    @property
    def ascension_stat_value(self):
        return self._ascension_stat_value

    @ascension_stat_value.setter
    def ascension_stat_value(self, ascension_stat_value: float):
        if ascension_stat_value < 0:
            raise ValueError('Invalid ascension stat value.')
        else:
            self._ascension_stat_value = ascension_stat_value
            self._update_stats = True

    @property
    def passive(self):
        return self._passive

    @passive.setter
    def passive(self, passive: dict[str]):
        for key, value in passive.items():
            if key not in self._stat_names:
                raise ValueError('Invalid passive.')
            # if value < 0:
                # raise ValueError('Invalid passive value.')
        self._passive = passive
        self._update_stats = True

    @property
    def crits(self):
        return self._crits

    @crits.setter
    def crits(self, crits: str):
        if crits not in ['average', 'always', 'never']:
            raise ValueError('Invalid crit type.')
        else:
            self._crits = crits
            self._update_power = True

    @property
    def scaling_stat(self):
        return self._scaling_stat

    @scaling_stat.setter
    def scaling_stat(self, scaling_stat: str):
        if scaling_stat not in ['ATK', 'DEF', 'HP']:
            raise ValueError('Invalid scaling stat.')
        else:
            self._scaling_stat = scaling_stat
            self._update_power = True

    @property
    def dmg_type(self):
        return self._dmg_type

    @dmg_type.setter
    def dmg_type(self, dmg_type: str):
        if dmg_type not in ['Physical', 'Elemental', 'Healing']:
            raise ValueError('Invalid damage type.')
        else:
            self._dmg_type = dmg_type
            self._update_power = True

    @property
    def amplifying_reaction(self):
        return self._amplifying_reaction

    @amplifying_reaction.setter
    def amplifying_reaction(self, amplifying_reaction):
        if amplifying_reaction is None:
            self._amplifying_reaction = amplifying_reaction
            self._amplification_factor = 0
            self._update_power = True
        elif amplifying_reaction not in ['Vaporize', 'Reverse Vaporize', 'Melt', 'Reverse Melt']:
            raise ValueError('Invalid amplification reaction')
        else:
            self._amplifying_reaction = amplifying_reaction
            if 'Reverse' not in amplifying_reaction:
                self._amplification_factor = 2
            else:
                self._amplification_factor = 1.5
            self._update_power = True

    @property
    def reaction_percentage(self):
        return self._reaction_percentage

    @reaction_percentage.setter
    def reaction_percentage(self, reaction_percentage):
        if reaction_percentage < 0 or reaction_percentage > 1:
            raise ValueError('Invalid reaction percentage.')
        else:
            self._reaction_percentage = reaction_percentage
            self._update_power = True

    @property
    def artifacts(self):
        return self._artifacts

    @artifacts.setter
    def artifacts(self, artifacts: arts.Artifacts):
        self._artifacts = artifacts
        self._update_stats = True

    @property
    def artifact(self, slot):
        return self._artifacts[slot]

    @artifact.setter
    def artifact(self,  artifacts: art.Artifact):
        self._artifacts.set_artifact(artifacts)
        self._update_stats = True

    @property
    def stats(self):
        if self._update_stats:
            self._stats = pd.Series(0.0, index=self._stat_names)
            self._stats += self._baseStats
            self._stats += self.weapon.stats
            self._stats += self.artifacts.stats
            self._update_stats = False
            self._update_power = True

        return self._stats

    @property
    def power(self):
        if self._update_power:
            # ATK, DEF, or HP scaling
            scaling_stat_value = self.stats['Base ' + self.scaling_stat] * (
                1 + self.stats[self.scaling_stat + '%']/100) + self.stats[self.scaling_stat]

            # Crit scaling
            if self.crits == 'never':
                crit_stat_value = 1
            elif self.crits == 'always':
                crit_stat_value = 1 + self.stats['Crit DMG%']/100
            elif self.crits == 'average':
                crit_stat_value = 1 + \
                    min(1, self.stats['Crit Rate%']/100) * \
                    self.stats['Crit DMG%']/100

            # Damage or healing scaling
            if self.dmg_type == 'Physical':
                dmg_stat_value = 1 + \
                    self.stats['Physical DMG%']/100 + self.stats['DMG%']/100
            elif self.dmg_type == 'Elemental':
                dmg_stat_value = 1 + \
                    self.stats['Elemental DMG%']/100 + self.stats['DMG%']/100
            elif self.dmg_type == 'Healing':
                dmg_stat_value = 1 + self.stats['Healing Bonus%']/100

            # Elemental Master scaling
            em_stat_value = 1 + self.reaction_percentage * (self._amplification_factor * (
                1 + 2.78 * self.stats['Elemental Mastery'] / (self.stats['Elemental Mastery'] + 1400)) - 1)

            # Power
            self._power = scaling_stat_value * crit_stat_value * dmg_stat_value * em_stat_value
            self._update_power = False

        return self._power

    def __str__(self):
        return self._name
