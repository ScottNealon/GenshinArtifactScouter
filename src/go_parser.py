from __future__ import annotations

import json
import logging
import os
import re

from src import artifacts

from . import genshin_data, power_calculator
from .artifact import Artifact, Circlet, Flower, Goblet, Plume, Sands
from .artifacts import Artifacts
from .character import Character
from .weapon import Weapon

# fmt: off
go_stat_map = {
    'hp':            'HP',
    'atk':           'ATK',
    'def':           'DEF',
    'hp_':           'HP%',
    'atk_':          'ATK%',
    'def_':          'DEF%',
    'physical_dmg_': 'Physical DMG%',
    'pyro_dmg_':     'Pyro DMG%',
    'hydro_dmg_':    'Hydro DMG%',
    'cryo_dmg_':     'Cryo DMG%',
    'electro_dmg_':  'Electro DMG%',
    'geo_dmg_':      'Geo DMG%',
    'anemo_dmg_':    'Anemo DMG%',
    'eleMas':        'Elemental Mastery',
    'enerRech_':     'Energy Recharge%',
    'critRate_':     'Crit Rate%',
    'critDMG_':      'Crit DMG%',
    'heal_':         'Healing Bonus%'
}

slotStr2type = {"flower": Flower, "plume": Plume, "sands": Sands, "goblet": Goblet, "circlet": Circlet}
# fmt: on

log = logging.getLogger(__name__)


class GenshinOptimizerData:
    def __init__(self, file_path: os.PathLike):
        log.info("-" * 140)
        log.info(f"READING GENSHIN OPTIMIZER DATA FROM {file_path}...")

        # Read file path and save data
        with open(file_path) as file_handle:
            self.data = json.load(file_handle)

        if self.data["version"] != 6:
            log.warning(f"GO Database is Version {self.data['Version']}. This tool was designed for Version 6.")
            log.warning("Unintended interactions may occur.")

        # Import characters
        self._import_characters()
        log.info(f"Characters imported successfully.")

        # Import artifacts
        self._import_artifacts()
        log.info(f"Artifacts imported successfully.")
        log.info("")

    @property
    def data(self) -> dict:
        return self._data

    @data.setter
    def data(self, data: dict):
        self._data = data

    @property
    def characters(self) -> list[Character]:
        return self._characters

    def get_character(self, character_name: str) -> Character:
        character_name = character_name.lower()
        if character_name not in self.characters:
            raise ValueError(f"Character {character_name} not found in import.")
        return self.characters[character_name]

    def get_characters_artifacts(self, character_name: str) -> Artifacts:
        character_name = character_name.lower()
        if character_name not in self.characters:
            raise ValueError(f"Character {character_name} not found in import.")
        return self._artifacts_on_characters[character_name]

    def get_alternative_artifacts(self, equipped_artifacts: Artifacts) -> dict[type, list[Artifact]]:

        # Determine which artifacts can be from other sets
        flex_slots = equipped_artifacts.find_flex_slots()
        main_stat_restrictions: dict[type, str] = {}
        set_restrictions: dict[type, str] = {}
        for artifact in equipped_artifacts:
            if artifact is not None:
                main_stat_restrictions[artifact.slot] = artifact.main_stat
                if artifact.slot not in flex_slots:
                    set_restrictions[artifact.slot] = artifact.set
            else:
                main_stat_restrictions[artifact.slot] = ""
                set_restrictions[artifact.slot] = ""

        # Iterate through artifacts, adding those that fit requirements
        replacement_artifacts: dict[type, list[Artifact]] = {Flower: [], Plume: [], Sands: [], Goblet: [], Circlet: []}
        for artifact in self._artifacts:
            # Eliminate invalid artifacts
            if artifact.main_stat != main_stat_restrictions[artifact.slot]:
                continue
            if artifact.slot in set_restrictions:
                if artifact.set != set_restrictions[artifact.slot]:
                    continue
            # Ignore locked artifacts unless they are already equipped
            if artifact.locked:
                if artifact is not equipped_artifacts.get_artifact(artifact.slot):
                    continue
            # Add artifacts to dict
            replacement_artifacts[artifact.slot].append(artifact)

        return replacement_artifacts

    def _import_characters(self):

        # Iterate across characters
        self._characters = {}
        for character_name, character_data in self.data["characterDatabase"].items():
            # Create weapon
            weapon_data = {
                "name": character_data["weapon"]["key"],
                "level": character_data["weapon"]["level"],
                "ascension": character_data["weapon"]["ascension"],
                "passive": {},
            }
            weapon = Weapon(**weapon_data)
            # Read data
            data = {
                "name": character_name,
                "level": character_data["level"],
                "ascension": character_data["ascension"],
                "passive": {},
                "dmg_type": "physical",
                "weapon": weapon,
                "scaling_stat": "ATK",
                "crits": character_data["hitMode"],
                "amplifying_reaction": character_data["reactionMode"],
                "reaction_percentage": 100.0 if character_data["reactionMode"] is not None else 0.0,
            }
            # Create character
            character = Character(**data)
            self._characters[character_name] = character

    def _import_artifacts(self):

        # Prepare character artifacts objects
        self._artifacts_on_characters = {}
        for character_name in self.characters:
            artifacts = Artifacts([])
            self._artifacts_on_characters[character_name] = artifacts

        # Iterate across artifacts
        self._artifacts = []
        for artifact_name, artifact_data in self.data["artifactDatabase"].items():
            # Read data
            slot = slotStr2type[artifact_data["slotKey"]]
            data = {
                "name": artifact_name.replace("artifact_", ""),
                "set_str": artifact_data["setKey"],
                "main_stat": go_stat_map[artifact_data["mainStatKey"]],
                "stars": artifact_data["numStars"],
                "level": artifact_data["level"],
                "substats": {
                    go_stat_map[substat["key"]]: substat["value"]
                    for substat in artifact_data["substats"]
                    if substat["key"] != ""
                },
                "locked": artifact_data["lock"],
            }

            # Create artifact
            artifact = slot(**data)
            self._artifacts.append(artifact)

            # Add to character artifacts
            if artifact_data["location"] != "":
                self._artifacts_on_characters[artifact_data["location"]].set_artifact(artifact)
