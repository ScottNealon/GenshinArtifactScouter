class Substat:

    _substat_names = ['HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%',
                      'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%']

    def __init__(self, stat: str, value: float):
        self.stat = stat
        self.value = value


    @property
    def stat(self):
        return self._stat

    @stat.setter
    def stat(self, stat: str):
        if stat not in self._substat_names:
            raise ValueError('Invalid substat type.')
        self._stat = stat


    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value: float):
        self._value = value
