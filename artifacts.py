import pandas as pd

import artifact as art


class Artifacts:

    _stat_names = ['Base HP', 'Base ATK', 'Base DEF', 'HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%',
                   'Elemental DMG%', 'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%']
    _set_stats = {
        'initiate':       [{}, {}],
        'adventurer':     [{'HP': 1000}, {}],
        'lucky':          [{'DEF': 100}, {}],
        'doctor':         [{'Healing Bonus%': 20.0}, {}],
        'resolution':     [{'ATK%': 18.0}, {'Crit Rate%': 30.0}],
        'miracle':        [{}, {}],
        'berserker':      [{'Crit Rate%': 12.0}, {}],
        'instructor':     [{'Elemental Mastery': 80}, {'Elemental Mastery': 120}],
        'exile':          [{'Energy Recharge%': 20.0}, {}],
        'defenders':      [{'DEF%': 30.0}, {}],
        'brave':          [{'ATK%': 18.0}, {'DMG%': 15.0}],
        'martial':        [{'DMG%': 15.0}, {'DMG%': 25.0}],
        'gambler':        [{'DMG%': 20.0}, {}],
        'scholar':        [{'Energy Recharge%': 20.0}, {}],
        'illumination':   [{}, {}],
        'destiny':        [{}, {}],
        'wisdom':         [{}, {}],
        'springtime':     [{}, {}],
        'gladiators':     [{'ATK%': 18.0}, {'DMG%': 35.0}],
        'wanderers':      [{'Elemental Mastery': 80}, {'DMG%': 35.0}],
        'thundersoother': [{}, {'DMG%': 35.0}],
        'thundering':     [{'Elemental DMG%': 15.0}, {}],
        'maiden':         [{'Healing Bonus%': 15.0}, {'Healing Bonus%': 20.0}],
        'viridescent':    [{'Elemental DMG%': 15.0}, {}],
        'witch':          [{'Elemental DMG%': 15.0}, {'DMG%': 15.0}],
        'lavawalker':     [{}, {'DMG%': 35.0}],
        'noblesse':       [{'DMG%': 20.0}, {}],
        'chivalry':       [{'Physical DMG%': 25.0}, {'DMG%': 50.0}],
        'petra':          [{'Elemental DMG%': 15.0}, {}],
        'bolide':         [{}, {'DMG%': 40.0}],
        'blizard':        [{'Elemental DMG%': 15.0}, {'Crit Rate%': 40.0}],
        'depth':          [{'Elemental DMG%': 15.0}, {'DMG%': 30.0}],
        'millelith':      [{'HP%': 20.0}, {'ATK%': 20.0}],
        'pale':           [{'Physical DMG%': 25.0}, {'ATK%': 18.0, 'Physical DMG%': 15.0}],
        'fate':           [{'Energy Recharge%': 20.0}, {}],
        'reminiscnece':   [{'ATK%': 18.0}, {'DMG%': 50.0}]
    }

    def __init__(self, flower: art.Flower, plume: art.Plume, sands: art.Sands, goblet: art.Goblet, circlet: art.Circlet):

        # Validated inputs
        self.flower = flower
        self.plume = plume
        self.sands = sands
        self.goblet = goblet
        self.circlet = circlet

        self._update_stats = True

    @property
    def flower(self):
        return self._flower

    @flower.setter
    def flower(self, flower: art.Flower):
        self._flower = flower
        self._update_stats = True

    @property
    def plume(self):
        return self._plume

    @plume.setter
    def plume(self, plume: art.Plume):
        self._plume = plume
        self._update_stats = True

    @property
    def sands(self):
        return self._sands

    @sands.setter
    def sands(self, sands: art.Sands):
        self._sands = sands
        self._update_stats = True

    @property
    def goblet(self):
        return self._goblet

    @goblet.setter
    def goblet(self, goblet: art.Goblet):
        self._goblet = goblet
        self._update_stats = True

    @property
    def circlet(self):
        return self._circlet

    @circlet.setter
    def circlet(self, circlet: art.Circlet):
        self._circlet = circlet
        self._update_stats = True

    @property
    def artifact_list(self):
        return [self.flower, self.plume, self.sands, self.goblet, self.circlet]

    def get_artifact(self, slot_type: type = None, slot_str: str = None):
        if slot_type is art.Flower or slot_str == 'flower':
            return self.flower
        elif slot_type is art.Plume or slot_str == 'plume':
            return self.plume
        elif slot_type is art.Sands or slot_str == 'sands':
            return self.sands
        elif slot_type is art.Goblet or slot_str == 'goblet':
            return self.goblet
        elif slot_type is art.Circlet or slot_str == 'circlet':
            return self.circlet

    def set_artifact(self, artifact: art.Artifact):
        if type(artifact) is art.Flower:
            self.flower = artifact
        elif type(artifact) is art.Plume:
            self.plume = artifact
        elif type(artifact) is art.Sands:
            self.sands = artifact
        elif type(artifact) is art.Goblet:
            self.goblet = artifact
        elif type(artifact) is art.Circlet:
            self.circlet = artifact
        else:
            raise ValueError('Invalid slot type')

    @property
    def stats(self):
        if self._update_stats:
            self._stats = pd.Series(0.0, index=self._stat_names)
            sets = {}
            # Artifact stats
            for artifact in self.artifact_list:
                if artifact is not None:
                    self._stats += artifact.stats
                    sets[artifact.set] = sets.get(artifact.set, 0) + 1
            # Set stats
            for set, count in sets.items():
                if count >= 2:
                    for stat, value in self._set_stats[set][0].items():
                        self._stats[stat] += value
                if count >= 4:
                    for stat, value in self._set_stats[set][1].items():
                        self._stas[stat] += value
            self._update_stats = False

        return self._stats
