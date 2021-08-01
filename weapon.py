import pandas as pd


class Weapon:

    _stat_names = ['Base HP', 'Base ATK', 'Base DEF', 'HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%',
                   'Elemental DMG%', 'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%']
    _valid_passive_stats = ['Base ATK', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%', 'Elemental DMG%',
                            'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%']
    _valid_ascension_stats = ['HP%', 'ATK%', 'DEF%', 'Physical DMG%',
                              'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%']

    def __init__(self, name: str, level: int, baseATK: int, ascension_stat: str, ascension_stat_value: float, passive: dict[str]):

        # Unvalidated inputs
        self._name = name

        # Validated inputs
        self.level = level
        self.baseATK = baseATK
        self.ascension_stat = ascension_stat
        self.ascension_stat_value = ascension_stat_value
        self.passive = passive

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level: int):
        if level < 1 or level > 90:
            raise ValueError('Invalid character level')
        else:
            self._level = level
            self._update_stats = True

    @property
    def baseATK(self):
        return self._baseATK

    @baseATK.setter
    def baseATK(self, baseATK: int):
        if baseATK <= 0:
            raise ValueError('Invalid base attack.')
        else:
            self._baseATK = baseATK
            self._update_stats = True

    @property
    def ascension_stat(self):
        return self._ascension_stat

    @ascension_stat.setter
    def ascension_stat(self, ascension_stat: str):
        if ascension_stat not in self._valid_ascension_stats:
            raise ValueError('Invalid ascension stat.')
        else:
            self._ascension_stat = ascension_stat
            self._update_stats = True

    @property
    def ascension_stat_value(self):
        return self._ascension_stat_value

    @ascension_stat_value.setter
    def ascension_stat_value(self, ascension_stat_value: float):
        if ascension_stat_value <= 0:
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
            if key not in self._valid_passive_stats:
                raise ValueError('Invalid passive stat.')
            elif value < 0:
                raise ValueError('Invalid passive stat value.')
        self._passive = passive

    @property
    def stats(self):
        if self._update_stats:
            self._stats = pd.Series(0.0, index=self._stat_names)
            self._stats['Base ATK'] += self.baseATK
            self._stats[self.ascension_stat] += self.ascension_stat_value
            for key, value in self.passive.items():
                self._stats[key] += value
            self._update_stats = False

        return self._stats
