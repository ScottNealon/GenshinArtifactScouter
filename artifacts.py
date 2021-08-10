from typing import Union

import pandas as pd

import artifact as art


class Artifacts:

    _stat_names = ['Base HP', 'Base ATK', 'Base DEF', 'HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%',
                   'Elemental DMG%', 'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%', 'probability']
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
        'emblem':         [{'Energy Recharge%': 20.0}, {}],
        'reminiscence':   [{'ATK%': 18.0}, {'DMG%': 50.0}]
    }

    def __init__(self, artifacts: list[art.Artifact]):

        self.flower = None
        self.plume = None
        self.sands = None
        self.goblet = None
        self.circlet = None
        for artifact in artifacts:
            self.set_artifact(artifact, override=False)

    @property
    def flower(self):
        return self._flower

    @flower.setter
    def flower(self, flower: art.Flower):
        self._flower = flower

    @property
    def plume(self):
        return self._plume

    @plume.setter
    def plume(self, plume: art.Plume):
        self._plume = plume

    @property
    def sands(self):
        return self._sands

    @sands.setter
    def sands(self, sands: art.Sands):
        self._sands = sands

    @property
    def goblet(self):
        return self._goblet

    @goblet.setter
    def goblet(self, goblet: art.Goblet):
        self._goblet = goblet

    @property
    def circlet(self):
        return self._circlet

    @circlet.setter
    def circlet(self, circlet: art.Circlet):
        self._circlet = circlet

    @property
    def artifact_list(self):
        return [self.flower, self.plume, self.sands, self.goblet, self.circlet]

    def get_artifact(self, slot: Union[art.Artifact, str, type]):

        if type(slot) is str:
            return getattr(self, slot) # self.flower / self.plume / ...

        if slot is art.Flower or slot == 'flower':
            return self.flower
        elif slot is art.Plume or slot == 'plume':
            return self.plume
        elif slot is art.Sands or slot == 'sands':
            return self.sands
        elif slot is art.Goblet or slot == 'goblet':
            return self.goblet
        elif slot is art.Circlet or slot == 'circlet':
            return self.circlet

    def set_artifact(self, artifact: art.Artifact, override: bool = False):
        slot = type(artifact)
        if not override:
            if self.has_artifact(slot):
                raise ValueError('Artifact already exists. Override flag not provided.')
        if slot is art.Flower:
            self.flower = artifact
        elif slot is art.Plume:
            self.plume = artifact
        elif slot is art.Sands:
            self.sands = artifact
        elif slot is art.Goblet:
            self.goblet = artifact
        elif slot is art.Circlet:
            self.circlet = artifact
        else:
            raise ValueError('Invalid slot type')

    def has_artifact(self, slot: type):
        if not issubclass(slot, art.Artifact):
            raise ValueError('Invalid slot type.')
        if slot is art.Flower:
            if not hasattr(self, '_flower'):
                return False
            return self.flower is not None
        elif slot is art.Plume:
            if not hasattr(self, '_plume'):
                return False
            return self.plume is not None
        elif slot is art.Sands:
            if not hasattr(self, '_sands'):
                return False
            return self.sands is not None
        elif slot is art.Goblet:
            if not hasattr(self, '_goblet'):
                return False
            return self.goblet is not None
        elif slot is art.Circlet:
            if not hasattr(self, '_circlet'):
                return False
            return self.circlet is not None
        else:
            raise ValueError('Invalid slot type')

    @property
    def stats(self):
        self._stats = pd.Series(0.0, index=self._stat_names)
        sets = {}
        # Artifact stats
        for artifact in self.artifact_list:
            if artifact is not None:
                if (type(artifact.stats) is pd.DataFrame) and (type(self._stats) is pd.DataFrame):
                    raise ValueError('Cannot have two probablistic artifacts.') # TODO
                self._stats = self._stats + artifact.stats
                sets[artifact.set] = sets.get(artifact.set, 0) + 1
        # Set stats
        for set, count in sets.items():
            if count >= 2:
                for stat, value in self._set_stats[set][0].items():
                    self._stats[stat] += value
            if count >= 4:
                for stat, value in self._set_stats[set][1].items():
                    self._stas[stat] += value

        return self._stats

    def __iter__(self):
        return iter(self.artifact_list)
