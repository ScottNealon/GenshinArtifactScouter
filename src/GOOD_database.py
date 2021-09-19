from __future__ import annotations

import json
import logging
import os

from src.artifact import Artifact, Circlet, Flower, Goblet, Plume, Sands
from src.artifacts import Artifacts
from src.character import Character
from src.weapon import Weapon

slotStr2type = {"flower": Flower, "plume": Plume, "sands": Sands, "goblet": Goblet, "circlet": Circlet}


log = logging.getLogger(__name__)


class GenshinOpenObjectDescriptionDatabase:
    def __init__(self, file_path: os.PathLike):

        # Read file path and save data
        with open(file_path) as file_handle:
            self._GOOD_json = json.load(file_handle)

        # Validate database
        if self._GOOD_json["format"] != "GOOD":
            raise ValueError(
                f"Invalid database format: {self.data['format']}. This tool is only compatable with GOOD format."
            )
        if self._GOOD_json["dbVersion"] > 8:
            log.warning(f"GOOD database is Version {self.data['dbVersion']}. This tool was designed for Version 8.")
            log.warning("Unintended interactions may occur.")

        # Import characters
        self._import_characters()

        # Import artifacts
        self._import_artifacts()

    @property
    def GOOD_json(self) -> dict[str]:
        return self._GOOD_json

    @property
    def characters(self) -> list[Character]:
        return self._characters

    def get_character(self, character_key: str) -> Character:
        return next(character for character in self.characters if character.key == character_key)

    @property
    def artifacts(self) -> list[Artifacts]:
        return self._artifacts

    @property
    def equipped_artifacts(self) -> dict[Character, Artifacts]:
        return self._equipped_artifacts

    def _import_characters(self):

        # Iterate across characters
        self._characters = []
        for character_data in self._GOOD_json["characters"]:

            # Find weapon
            for weapon_data in self._GOOD_json["weapons"]:
                if weapon_data["location"] == character_data["key"]:
                    weapon = Weapon(**weapon_data)
                    break
            # If no weapon is created, raise error
            if "weapon" not in locals():
                raise ValueError(f"Character {character_data['key']} does not have an equipped weapon.")

            # Create and save character
            character = Character(weapon=weapon, **character_data)
            self._characters.append(character)

    def _import_artifacts(self):

        # Prepare equipped artifacts objects
        self._equipped_artifacts = {}
        for character in self.characters:
            artifacts = Artifacts([])
            self._equipped_artifacts[character] = artifacts

        # Iterate across artifacts
        self._artifacts = []
        for artifact_index, artifact_data in enumerate(self._GOOD_json["artifacts"]):

            # Create artifact
            slot = slotStr2type[artifact_data["slotKey"]]
            artifact = slot(index=artifact_index, **artifact_data)
            self._artifacts.append(artifact)

            # Add to character artifacts if equipped
            if artifact_data["location"] != "":
                equipped_character = self.get_character(artifact_data["location"])
                self.equipped_artifacts[equipped_character].set_artifact(artifact)

    def get_alternative_artifacts(self, equipped_artifacts: Artifacts) -> dict[type, list[Artifact]]:
        """Generate list of artifacts that could be put in equipped_artifacts without changing set bonus"""

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
        for artifact in self.artifacts:
            # Eliminate invalid artifacts
            if artifact.main_stat != main_stat_restrictions[artifact.slot]:
                continue
            if artifact.slot in set_restrictions:
                if artifact.set != set_restrictions[artifact.slot]:
                    continue
            # Ignore excluded artifacts unless they are already equipped
            if artifact.exclude:
                if artifact is not equipped_artifacts.get_artifact(artifact.slot):
                    continue
            # Add artifacts to dict
            replacement_artifacts[artifact.slot].append(artifact)

        return replacement_artifacts
