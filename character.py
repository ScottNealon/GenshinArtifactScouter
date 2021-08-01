import pandas as pd

import artifact as art
import artifacts as arts
import weapon as weap


class Character:

    _stat_names = ['Base HP', 'Base ATK', 'Base DEF', 'HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%',
                   'Elemental DMG%', 'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%']

    def __init__(self, name: str, level: int, baseHP: int, baseATK: int, baseDEF: int, ascension_stat: str, ascension_stat_value: float, passive: dict[str],
                 dmg_type: str, scaling_stat: str = None, crits: str = None, amplifying_reaction: str = None, reaction_percentage: float = None):

        # Undefaulted inputs
        self.name = name
        self.level = level
        self.baseHP = baseHP
        self.baseATK = baseATK
        self.baseDEF = baseDEF
        self.ascension_stat = ascension_stat
        self.ascension_stat_value = ascension_stat_value
        self.passive = passive
        # self.weapon = weapon
        self.dmg_type = dmg_type

        # Defaulted inputs
        if scaling_stat is None:
            self.scaling_stat = 'ATK'
        else:
            self.scaling_stat = scaling_stat

        if crits is None:
            self.crits = 'average'
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

    @name.setter
    def name(self, name: str):
        self._name = name
        self._update_stats = True

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level: int):
        if level < 1 or level > 90:
            raise ValueError('Invalid character level')
        self._level = level
        self._update_stats = True

    @property
    def baseHP(self):
        return self._baseHP

    @baseHP.setter
    def baseHP(self, baseHP: int):
        self._baseHP = baseHP

    @property
    def baseATK(self):
        return self._baseATK

    @baseATK.setter
    def baseATK(self, baseATK: int):
        self._baseATK = baseATK

    @property
    def baseDEF(self):
        return self._baseDEF

    @baseDEF.setter
    def baseDEF(self, baseDEF: int):
        self._baseDEF = baseDEF

    @property
    def ascension_stat(self):
        return self._ascension_stat

    @ascension_stat.setter
    def ascension_stat(self, ascension_stat: str):
        if ascension_stat not in self._stat_names:
            raise ValueError('Invalid ascension stat.')
        self._ascension_stat = ascension_stat
        self._update_stats = True

    @property
    def ascension_stat_value(self):
        return self._ascension_stat_value

    @ascension_stat_value.setter
    def ascension_stat_value(self, ascension_stat_value: float):
        if ascension_stat_value < 0:
            raise ValueError('Invalid ascension stat value.')
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
        self._passive = passive
        self._update_stats = True

    @property
    def base_stats(self):
        if self._update_stats:
            self.update_stats()
        return self._baseStats

    def update_stats(self):
        self._baseStats = pd.Series(0.0, index=self._stat_names)
        self._baseStats['Base HP'] += self.baseHP
        self._baseStats['Base ATK'] += self.baseATK
        self._baseStats['Base DEF'] += self.baseDEF
        self._baseStats['Crit Rate%'] += 5
        self._baseStats['Crit DMG%'] += 50
        self._baseStats[self.ascension_stat] += self.ascension_stat_value
        for stat, value in self.passive.items():
            self._baseStats[stat] += value
        self._update_stats = False

    @property
    def crits(self):
        return self._crits

    @crits.setter
    def crits(self, crits: str):
        if crits not in ['average', 'always', 'never']:
            raise ValueError('Invalid crit type.')
        self._crits = crits

    @property
    def scaling_stat(self):
        return self._scaling_stat

    @scaling_stat.setter
    def scaling_stat(self, scaling_stat: str):
        if scaling_stat not in ['ATK', 'DEF', 'HP']:
            raise ValueError('Invalid scaling stat.')
        self._scaling_stat = scaling_stat

    @property
    def dmg_type(self):
        return self._dmg_type

    @dmg_type.setter
    def dmg_type(self, dmg_type: str):
        if dmg_type not in ['Physical', 'Elemental', 'Healing']:
            raise ValueError('Invalid damage type.')
        self._dmg_type = dmg_type

    @property
    def amplifying_reaction(self):
        return self._amplifying_reaction

    @amplifying_reaction.setter
    def amplifying_reaction(self, amplifying_reaction):
        if amplifying_reaction is None:
            self._amplifying_reaction = amplifying_reaction
            self._amplification_factor = 0
        if amplifying_reaction not in ['Vaporize', 'Reverse Vaporize', 'Melt', 'Reverse Melt']:
            raise ValueError('Invalid amplification reaction')
        self._amplifying_reaction = amplifying_reaction
        if 'Reverse' not in amplifying_reaction:
            self._amplification_factor = 2
        else:
            self._amplification_factor = 1.5

    @property
    def amplification_factor(self):
        return self._amplification_factor

    @property
    def reaction_percentage(self):
        return self._reaction_percentage

    @reaction_percentage.setter
    def reaction_percentage(self, reaction_percentage):
        if reaction_percentage < 0 or reaction_percentage > 1:
            raise ValueError('Invalid reaction percentage.')
        self._reaction_percentage = reaction_percentage

    def __str__(self):
        return self._name
