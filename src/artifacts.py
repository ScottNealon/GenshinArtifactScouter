from __future__ import annotations

from typing import Iterable, Union

import pandas as pd

from src import genshin_data
from src.artifact import Artifact, Circlet, Flower, Goblet, Plume, Sands


class Artifacts:
    def __init__(self, artifacts: list[Artifact]):

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
    def flower(self, flower: Flower):
        self._flower = flower

    @property
    def plume(self):
        return self._plume

    @plume.setter
    def plume(self, plume: Plume):
        self._plume = plume

    @property
    def sands(self):
        return self._sands

    @sands.setter
    def sands(self, sands: Sands):
        self._sands = sands

    @property
    def goblet(self):
        return self._goblet

    @goblet.setter
    def goblet(self, goblet: Goblet):
        self._goblet = goblet

    @property
    def circlet(self):
        return self._circlet

    @circlet.setter
    def circlet(self, circlet: Circlet):
        self._circlet = circlet

    @property
    def artifact_list(self) -> list[Artifact]:
        return [
            artifact
            for artifact in [self.flower, self.plume, self.sands, self.goblet, self.circlet]
            if artifact is not None
        ]

    def get_artifact(self, slot: Union[Artifact, str, type]) -> Artifact:

        if type(slot) is str:
            return getattr(self, slot)  # self.flower / self.plume / ...
        elif type(slot) is type:
            return getattr(self, slot.__name__.lower())
        elif type(slot) is Artifact:
            return getattr(self, type(slot).__name__.lower())
        else:
            raise ValueError("Invalid input type.")

    def set_artifact(self, artifact: Artifact, override: bool = False):
        if artifact is None:
            return
        slot = type(artifact)
        if slot not in [Flower, Plume, Sands, Goblet, Circlet]:
            raise ValueError("Invalid artifact type.")
        if not override:
            if self.has_artifact(slot):
                raise ValueError("Artifact already exists. Override flag not provided.")
        setattr(self, slot.__name__.lower(), artifact)

    def has_artifact(self, slot: type):
        if not issubclass(slot, Artifact):
            raise ValueError("Invalid slot type.")
        if not hasattr(self, "_" + slot.__name__.lower()):
            return False
        return getattr(self, slot.__name__.lower()) is not None

    def get_stats(self, leveled: bool = False, useful_stats: list[str] = None) -> Union[pd.Series, pd.DataFrame]:
        """Returns collective stats of artifacts"""
        stats = pd.Series(0.0, index=useful_stats)
        sets = {}
        # Artifact stats
        for artifact in self.artifact_list:
            if artifact is not None:
                artifact_stats = artifact.get_stats(leveled, useful_stats)
                if (type(artifact_stats) is pd.DataFrame) and (type(stats) is pd.DataFrame):
                    raise ValueError("Cannot have two probablistic artifacts.")
                stats = stats + artifact_stats
                if artifact.set is not None:
                    sets[artifact.set] = sets.get(artifact.set, 0) + 1
        # Set stats
        stats, _ = self.add_set_bonus(stats=stats, sets=sets)
        return stats

    @property
    def stat_transfer(self) -> dict[str, dict[str, float]]:
        stats = pd.Series(0.0, index=genshin_data.pandas_headers)
        sets = {}
        # Artifact stats
        for artifact in self.artifact_list:
            if artifact is not None:
                if artifact.set is not None:
                    sets[artifact.set] = sets.get(artifact.set, 0) + 1
        # Set stats
        _, stat_transfer = self.add_set_bonus(stats, sets)
        return stat_transfer

    def add_set_bonus(
        self, stats: Union[pd.Series, pd.DataFrame], sets: dict[str, int]
    ) -> tuple[Union[pd.Series, pd.DataFrame], dict[str, dict[str, float]]]:
        stat_transfer: dict[str, dict[str, float]] = {}
        for set, count in sets.items():
            if count >= 2:
                for stat, value in genshin_data.set_stats[set][0].items():
                    if type(value) is not dict:  # Not stat transfer
                        stats[stat] += value
                    else:
                        if stat not in stat_transfer:
                            stat_transfer[stat] = {}
                        for source_stat, source_value in stats[stat]:
                            stat_transfer[stat][source_stat] = source_value
            if count >= 4:
                for stat, value in genshin_data.set_stats[set][1].items():
                    if type(value) is not dict:  # Not stat transfer
                        stats[stat] += value
                    else:
                        if stat not in stat_transfer:
                            stat_transfer[stat] = {}
                        for source_stat, source_value in value.items():
                            stat_transfer[stat][source_stat] = source_value
        return stats, stat_transfer

    def __iter__(self) -> Iterable[type]:
        return iter(self.artifact_list)

    def generate_empty_artifacts(stars: int, level: int, main_stats: list[str]) -> Artifacts:
        """Generates an Artifacs object with empty artifacts (no set, no substats)"""
        empty_flower = Flower(main_stat=main_stats[0], stars=stars, level=level)
        empty_plume = Plume(main_stat=main_stats[1], stars=stars, level=level)
        empty_sands = Sands(main_stat=main_stats[2], stars=stars, level=level)
        empty_goblet = Goblet(main_stat=main_stats[3], stars=stars, level=level)
        empty_circlet = Circlet(main_stat=main_stats[4], stars=stars, level=level)
        empty_artifacts = Artifacts([empty_flower, empty_plume, empty_sands, empty_goblet, empty_circlet])
        return empty_artifacts

    def find_flex_slots(self) -> list[type]:
        """Determine which slots could be changed without affecting set bonus"""
        # Determine number for each set
        sets = {}
        for artifact in self.artifact_list:
            if artifact is not None:
                sets[artifact.set] = sets.get(artifact.set, 0) + 1
        # Append artifact slots that aren't forming a multiple of two set
        flex_slots = []
        for artifact in self.artifact_list:
            if artifact is not None:
                if sets[artifact.set] % 2 != 0:
                    flex_slots.append(artifact.slot)
        return flex_slots
