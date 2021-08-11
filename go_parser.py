import json
import logging
from pathlib import Path
from typing import Union

import numpy as np

import artifact as art
import artifacts as arts
import character as char

# fmt: off
go_set_map = {
    'Adventurer':             'adventurer',
    'ArchaicPetra':           'petra',
    'Berserker':              'berserker',
    'BlizzardStrayer':        'blizard',
    'BloodstainedChivalry':   'chivalry',
    'BraveHeart':             'brave',
    'CrimsonWitchOfFlames':   'witch',
    'DefendersWill':          'defenders',
    'EmblemOfSeveredFate':    'emblem',
    'Gambler':                'gambler',
    'GladiatorsFinale':       'gladiators',
    'HeartOfDepth':           'depth',
    'Instructor':             'instructor',
    'Lavawalker':             'lavawalker',
    'LuckyDog':               'lucky',
    'MaidenBeloved':          'maiden',
    'MartialArtist':          'martial',
    'NoblesseOblige':         'noblesse',
    'PaleFlame':              'pale',
    'PrayersForDestiny':      'destiny',
    'PrayersForIllumination': 'illumination',
    'PrayersForWisdom':       'wisdom',
    'PrayersToSpringtime':    'springtime',
    'ResolutionOfSojourner':  'sonjourner',
    'RetracingBolide':        'bolide',
    'Scholar':                'scholar',
    'ShimenawasReminiscence': 'reminiscence',
    'TenacityOfTheMillelith': 'millelith',
    'TheExile':               'exile',
    'ThunderingFury':         'thundering',
    'Thundersoother':         'thundersoother',
    'TinyMiracle':            'miracle',
    'TravelingDoctor':        'doctor',
    'ViridescentVenerer':     'viridescent',
    'WanderersTroupe':        'wanderers'
}

go_stat_map = {
    'hp':            'HP',
    'atk':           'ATK',
    'def':           'DEF',
    'hp_':           'HP%',
    'atk_':          'ATK%',
    'def_':          'DEF%',
    'physical_dmg_': 'Physical DMG%',
    'pyro_dmg_':     'Elemental DMG%',
    'hydro_dmg_':    'Elemental DMG%',
    'cryo_dmg_':     'Elemental DMG%',
    'electro_dmg_':  'Elemental DMG%',
    'geo_dmg_':      'Elemental DMG%',
    'anemo_dmg_':    'Elemental DMG%',
    'eleMas':        'Elemental Mastery',
    'enerRech_':     'Energy Recharge%',
    'critRate_':     'Crit Rate%',
    'critDMG_':      'Crit DMG%',
    'heal_':         'Healing Bonus%'
}
# fmt: on

log = logging.getLogger(__name__)


class GenshinOptimizerData:
    def __init__(self, file_path: Union[str, Path]):

        # Read file path and save data
        with open(file_path) as f:
            self.data = json.load(f)

        if self.data["version"] != 6:
            log.warning(f"GO Database is Version {self.data['Version']}. This tool was designed for Version 6.")
            log.warning("Unintended interactions may occur.")

        # Import characters
        self._import_characters()

        # Import artifacts
        self._import_artifacts()

    @property
    def data(self) -> dict:
        return self._data

    @data.setter
    def data(self, data: dict):
        self._data = data

    @property
    def characters(self) -> list[char.Character]:
        return self._characters

    def get_character(self, character_name: str) -> char.Character:
        character_name = character_name.lower()
        if character_name not in self.characters:
            raise ValueError(f"Character {character_name} not found in import.")
        return self.characters[character_name]

    def get_characters_artifacts(self, character_name: str) -> arts.Artifacts:
        character_name = character_name.lower()
        if character_name not in self.characters:
            raise ValueError(f"Character {character_name} not found in import.")
        return self._artifacts_on_characters[character_name]

    def get_artifacts(
        self,
        sets: list[str] = None,
        stars: list[int] = None,
        min_level: int = None,
        max_level: int = None,
        slot: list[type] = None,
        main_stat: list[str] = None,
        min_substats: dict[str] = None,
        equipped: bool = None,
        location: list[str] = None,
        locked: bool = None,
    ):

        # Turn erroneous singleton inputs into lists
        if type(sets) is str:
            sets = [sets]
        if type(stars) is int:
            stars = [stars]
        if type(slot) is type:
            slot = [slot]
        if type(main_stat) is str:
            main_stat = [main_stat]
        if type(location) is str:
            location = [location]

        # Iterate through artifacts
        output_artifacts = {}
        for artifact_name, artifact in self._artifacts.items():

            # Perform filters
            go_artifact = self.data["artifactDatabase"][artifact_name]
            # Check sets
            if sets is not None:
                if artifact.set not in sets:
                    continue
            # Check stars
            if stars is not None:
                if artifact.stars not in stars:
                    continue
            # Check minimum level
            if min_level is not None:
                if artifact.level < min_level:
                    continue
            # Check maximum level
            if max_level is not None:
                if artifact.level > max_level:
                    continue
            # Check slot
            if slot is not None:
                if type(artifact) not in slot:
                    continue
            # Check main slot
            if main_stat is not None:
                if artifact.main_stat not in main_stat:
                    continue
            # Check substats
            if min_substats is not None:
                for substat, value in min_substats.items():
                    if artifact.substats.get(substat, -1) < value:
                        continue
            # Check eqiupped
            if equipped is not None:
                if bool(go_artifact["location"] != "") != equipped:
                    continue
            # Check location
            if location is not None:
                if go_artifact["location"] not in location:
                    continue
            # Check locked
            if locked is not None:
                if go_artifact["locked"] != locked:
                    continue

            # Passed filters
            output_artifacts[artifact_name] = artifact

        return output_artifacts

    def _import_characters(self):

        # Iterate across characters
        self._characters = {}
        for character_name, character_data in self.data["characterDatabase"].items():
            # Read data
            data = {
                "name": character_name,
                "level": character_data["level"],
                "ascension": character_data["ascension"],
                "passive": {},  # TODO fix this assumption
                "dmg_type": "Elemental",  # TODO fix this assumption
                "scaling_stat": "ATK",  # TODO fix this assumption
                "crits": character_data["hitMode"],
                "amplifying_reaction": character_data["reactionMode"],
                "reaction_percentage": 1 if character_data["reactionMode"] is not None else 0,
            }
            # Create character
            character = char.Character(**data)
            self._characters[character_name] = character

    def _import_artifacts(self):

        # Prepare character artifacts objects
        self._artifacts_on_characters = {}
        for character_name in self.characters:
            artifacts = arts.Artifacts([])
            self._artifacts_on_characters[character_name] = artifacts

        # Iterate across artifacts
        self._artifacts = {}
        for artifact_name, artifact_data in self.data["artifactDatabase"].items():
            # Read data
            slot = art.str2type[artifact_data["slotKey"]]
            data = {
                "set_str": go_set_map[artifact_data["setKey"]],
                "main_stat": go_stat_map[artifact_data["mainStatKey"]],
                "stars": artifact_data["numStars"],
                "level": artifact_data["level"],
                "substats": {
                    go_stat_map[substat["key"]]: substat["value"]
                    for substat in artifact_data["substats"]
                    if substat["key"] != ""
                },
            }

            # Create artifact
            artifact = slot(**data)
            self._artifacts[artifact_name] = artifact

            # Add to character artifacts
            if artifact_data["location"] is not "":
                self._artifacts_on_characters[artifact_data["location"]].set_artifact(artifact)

    # def get_character_weapon(self, character_name: str):

    #     character_data = self._get_character_data(character_name)

    #     weapon_data = character_data.get('weapon', {})
    #     if len(character_data) == 0:
    #         raise ValueError(f'Character {character_name} does not have a weapon equipped.')

    # def get_character_artifacts(self, character_name: str):

    #     character_data = self.data['characterDatabase'][character_name]

    # def _get_character_data(self, character_name: str):
    #     character_data = self.data['characterDatabase'].get(character_name, {})
    #     if len(character_data) == 0:
    #         raise ValueError(f'Character {character_name} not found in database.')
    #     return character_data


if __name__ == "__main__":
    data = GenshinOptimizerData("data.json")
