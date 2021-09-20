"""Backend Genshin Data required to run GAS"""

from __future__ import annotations

import itertools
import json
import logging
import math
import os

import numpy as np
import pandas as pd
import requests

log = logging.getLogger(__name__)
log.info("-" * 140)
log.info(f"IMPORTING AND CALCULATING GAME DATA...")

_data_dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../data")


def get_character_stats(character_name: str):
    """Contains the base stats and scaling reference for each character"""

    # Define file path
    file_path = os.path.join(_data_dir_path, "characters", f"{character_name}.json")

    if not os.path.isfile(file_path):
        raise ValueError("Character {character_name} not found in database.")

    # Read file
    with open(file_path, "r") as file_handle:
        character_stats = json.load(file_handle)

    return character_stats


def get_weapon_stats(weapon_name: str):

    # Define file path
    file_path = os.path.join(_data_dir_path, "weapons", f"{weapon_name}.json")

    # Read file
    with open(file_path, "r") as file_handle:
        weapon_stats = json.load(file_handle)

    return weapon_stats


def _get_character_stat_curves():
    """
    Contains the scaling multiplier for each character level
    stat_curves[curve_name][level]
    curve_name: GROW_CURVE_{HP}{ATTACK}_S{4}{5}
    level: integer between 1 and 90 inclusive
    """

    # Define file path
    file_path = os.path.join(_data_dir_path, "AvatarCurveExcelConfigData.json")

    # If file doesn't exist, download it
    if not os.path.isfile(file_path):
        log.info("Downloading character scaling curves...")
        url = "https://raw.githubusercontent.com/Dimbreath/GenshinData/master/ExcelBinOutput/AvatarCurveExcelConfigData.json"
        request = requests.get(url, allow_redirects=True)
        with open(file_path, "wb") as file_handle:
            file_handle.write(request.content)
        log.info("Character scaling curves downloaded.")

    # Read file
    with open(file_path, "r") as file_handle:
        character_stat_curves_data = json.load(file_handle)

    # Convert to dict of numpy arrays
    character_stat_curves = {}
    for curve in range(4):
        curve_name = character_stat_curves_data[0]["CurveInfos"][curve]["Type"]
        character_stat_curves[curve_name] = np.array(
            [np.NaN] + [level["CurveInfos"][curve]["Value"] for level in character_stat_curves_data]
        )

    return character_stat_curves


def _get_weapon_stat_curves():
    """
    Contains the scaling multiplier for each weapon level
    stat_curves[curve_name][level]
    curve_name: GROW_CURVE_{HP}{ATTACK}_S{4}{5}
    level: integer between 1 and 90 inclusive
    """

    # Define file path
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "..\data\WeaponCurveExcelConfigData.json")

    # If file doesn't exist, download it
    if not os.path.isfile(file_path):
        log.info("Downloading weapon scaling curves...")
        url = "https://raw.githubusercontent.com/Dimbreath/GenshinData/master/ExcelBinOutput/WeaponCurveExcelConfigData.json"
        request = requests.get(url, allow_redirects=True)
        with open(file_path, "wb") as file_handle:
            file_handle.write(request.content)
        log.info("Weapon scaling curves downloaded.")

    # Read file
    with open(file_path, "r") as file_handle:
        weapon_stat_curves_data = json.load(file_handle)

    # Convert to dict of numpy arrays
    weapon_stat_curves = {}
    for curve in range(18):
        curve_name = weapon_stat_curves_data[0]["CurveInfos"][curve]["Type"]
        weapon_stat_curves[curve_name] = np.array(
            [np.NaN] + [level["CurveInfos"][curve]["Value"] for level in weapon_stat_curves_data]
        )

    return weapon_stat_curves


def _get_substat_distribution_json():
    def toFloatIfFloat(string: str):
        """Converts string to float if string is int, else leaves as string"""
        if string.replace(".", "").isnumeric():
            return float(string)
        else:
            return string

    def toNumpyIfNumpy(val):
        """Converts value to numpy array if list else leaves as is"""
        if type(val) is list:
            return np.array(val)
        else:
            return val

    # Define file path
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "..\data\precalculated_substat_distributions.json")

    # Read file
    with open(file_path, "r") as file_handle:
        substat_distributions = json.load(
            file_handle, object_hook=lambda x: {toFloatIfFloat(k): toNumpyIfNumpy(v) for k, v in x.items()}
        )
    return substat_distributions


def _get_value_to_rolls_map():
    """Creates mapping between the end substat value and the possible substat rolls resulting in it"""

    value2rolls = {}
    # Iterate through substat-stars pairing
    for substat in substat_roll_values:
        value2rolls[substat] = {}
        for stars, roll_values in substat_roll_values[substat].items():
            # Calculate all possible results
            value2rolls[substat][stars] = {}
            for num_rolls in range(1, 6 + 1):
                possible_rolls = itertools.combinations_with_replacement(roll_values, num_rolls)
                for possible_roll in possible_rolls:
                    # Rounds total (complicated to explain why)
                    total = round(sum(possible_roll), 1)
                    if total in value2rolls[substat][stars]:
                        value2rolls[substat][stars][total].append(possible_roll)
                    else:
                        value2rolls[substat][stars][total] = [possible_roll]
            # Determine if any total can result from different number of rolls
            num_rolls = {}
            for total, rolls in value2rolls[substat][stars].items():
                num_rolls = []
                for roll in rolls:
                    if len(roll) not in num_rolls:
                        num_rolls.append(len(roll))
                # For each number of rolls, only save first instance
                shortened_rolls = []
                for num_roll in num_rolls:
                    for roll in rolls:
                        if len(roll) == num_roll:
                            shortened_rolls.append(roll)
                            break
                value2rolls[substat][stars][total] = shortened_rolls

    return value2rolls


def round_normal(value, precision):
    """Implement 5 and above, give it a shove rounding"""
    if value * 10 ** precision % 1 == 0.5:
        return math.ceil(value * 10 ** precision) / 10 ** precision
    else:
        return round(value, precision)


promote_stats_map = {
    "FIGHT_PROP_HP_PERCENT": "hp_",
    "FIGHT_PROP_ATTACK_PERCENT": "atk_",
    "FIGHT_PROP_DEFENSE_PERCENT": "def_",
    "FIGHT_PROP_PHYSICAL_ADD_HURT": "physical_dmg_",
    "FIGHT_PROP_FIRE_ADD_HURT": "pyro_dmg_",
    "FIGHT_PROP_WATER_ADD_HURT": "hydro_dmg_",
    "FIGHT_PROP_ICE_ADD_HURT": "cryo_dmg_",
    "FIGHT_PROP_ELEC_ADD_HURT": "electro_dmg_",
    "FIGHT_PROP_WIND_ADD_HURT": "anemo_dmg_",
    "FIGHT_PROP_ROCK_ADD_HURT": "geo_dmg_",
    "FIGHT_PROP_CHARGE_EFFICIENCY": "enerRech_",
    "FIGHT_PROP_ELEMENT_MASTERY": "eleMas",
    "FIGHT_PROP_CRITICAL": "critRate_",
    "FIGHT_PROP_CRITICAL_HURT": "critDMG_",
    "FIGHT_PROP_HEAL_ADD": "heal_",
}

stat_names = [
    "baseHp",
    "baseAtk",
    "baseDef",
    "hp",
    "atk",
    "def",
    "hp_",
    "atk_",
    "def_",
    "physical_dmg_",
    "pyro_dmg_",
    "hydro_dmg_",
    "cryo_dmg_",
    "electro_dmg_",
    "anemo_dmg_",
    "geo_dmg_",
    "dmg_",
    "eleMas",
    "enerRech_",
    "critRate_",
    "critDMG_",
    "heal_",
]
pandas_headers = stat_names + ["probability"]

# fmt: off
stat2output_map = {
    "hp":            "HP",
    "atk":           "ATK",
    "def":           "DEF",
    "hp_":           "HP %",
    "atk_":          "ATK %",
    "def_":          "DEF %",
    "physical_dmg_": "Physical DMG %",
    "pyro_dmg_":     "Pyro DMG %",
    "hydro_dmg_":    "Hydro DMG %",
    "cryo_dmg_":     "Cryo DMG %",
    "electro_dmg_":  "Electro DMG %",
    "geo_dmg_":      "Geo DMG %",
    "anemo_dmg_":    "Anemo DMG %",
    "eleMas":        "eleMas",
    "enerRech_":     "Energy Recharge %",
    "critRate_":     "Crit Rate %",
    "critDMG_":      "Crit DMG %",
    "heal_":         "Healing Bonus %",
    "dmg_":          "DMG %",
    "baseAtk":       "Base ATK",
    "baseHp":        "Base HP",
    "baseDef":       "Base DEF",
    "totalAtk":      "Total ATK",
    "toalHp":        "Total HP",
    "totalDef":      "Total DEF"
}

main_stat_scaling = {
    3: {
        "hp":            [430, 	552, 	674, 	796, 	918, 	1040, 	1162, 	1283, 	1405, 	1527, 	1649, 	1771, 	1893],
        "atk":           [28, 	36, 	44, 	52, 	60, 	68, 	76, 	84, 	91, 	99, 	107, 	115, 	123],
        "hp_":           [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        "atk_":          [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        "def_":          [6.6, 	8.4, 	10.3, 	12.1, 	14.0, 	15.8, 	17.7, 	19.6, 	21.4, 	23.3, 	25.1, 	27.0, 	28.8],
        "physical_dmg_": [6.6, 	8.4, 	10.3, 	12.1, 	14.0, 	15.8, 	17.7, 	19.6, 	21.4, 	23.3, 	25.1, 	27.0, 	28.8],
        "pyro_dmg_":     [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        "hydro_dmg_":    [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        "cryo_dmg_":     [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        "electro_dmg_":  [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        "anemo_dmg_":    [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        "geo_dmg_":      [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        "eleMas":        [21, 	27, 	33, 	39, 	45, 	51, 	57, 	63, 	69, 	75, 	80, 	86, 	92],
        "enerRech_":     [5.8, 	7.5, 	9.1, 	10.8, 	12.4, 	14.1, 	15.7, 	17.4, 	19.0, 	20.7, 	22.3, 	24.0, 	25.6],
        "critRate_":     [3.5, 	4.5, 	5.5, 	6.5, 	7.5, 	8.4, 	9.4, 	10.4, 	11.4, 	12.4, 	13.4, 	14.4, 	15.4],
        "critDMG_":      [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8],
        "heal_":         [4.0, 	5.2, 	6.3, 	7.5, 	8.6, 	9.8, 	10.9, 	12.0, 	13.2, 	14.3, 	15.5, 	16.6, 	17.8],
    },
    4: {
        "hp":            [645, 	828, 	1011, 	1194, 	1377, 	1559, 	1742, 	1925, 	2108, 	2291, 	2474, 	2657, 	2839, 	3022, 	3205, 	3388, 	3571],
        "atk":           [42, 	54, 	66, 	78, 	90, 	102, 	113, 	125, 	137, 	149, 	161, 	173, 	185, 	197, 	209, 	221, 	232],
        "hp_":           [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        "atk_":          [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        "def_":          [7.9, 	10.1, 	12.3, 	14.6, 	16.8, 	19.0, 	21.2, 	23.5, 	25.7, 	27.9, 	30.2, 	32.4, 	34.6, 	36.8, 	39.1, 	41.3, 	43.5],
        "physical_dmg_": [7.9, 	10.1, 	12.3, 	14.6, 	16.8, 	19.0, 	21.2, 	23.5, 	25.7, 	27.9, 	30.2, 	32.4, 	34.6, 	36.8, 	39.1, 	41.3, 	43.5],
        "pyro_dmg_":     [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        "hydro_dmg_":    [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        "cryo_dmg_":     [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        "electro_dmg_":  [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        "anemo_dmg_":    [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        "geo_dmg_":      [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        "eleMas":        [25, 	32, 	39, 	47, 	54, 	61, 	68, 	75, 	82, 	89, 	97, 	104, 	111, 	118, 	125, 	132, 	139],
        "enerRech_":     [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7],
        "critRate_":     [4.2, 	5.4, 	6.6, 	7.8, 	9.0, 	10.1, 	11.3, 	12.5, 	13.7, 	14.9, 	16.1, 	17.3, 	18.5, 	19.7, 	20.8, 	22.0, 	23.2],
        "critDMG_":      [8.4, 	10.8, 	13.1, 	15.5, 	17.9, 	20.3, 	22.7, 	25.0, 	27.4, 	29.8, 	32.2, 	34.5, 	36.9, 	39.3, 	41.7, 	44.1, 	46.4],
        "heal_":         [4.8, 	6.2, 	7.6, 	9.0, 	10.3, 	11.7, 	13.1, 	14.4, 	15.8, 	17.2, 	18.6, 	19.9, 	21.3, 	22.7, 	24.0, 	25.4, 	26.8],
    },
    5: {
        "hp":            [717, 	920, 	1123, 	1326, 	1530, 	1733, 	1936, 	2139, 	2342, 	2545, 	2749, 	2952, 	3155, 	3358, 	3561, 	3764, 	3967, 	4171, 	4374, 	4577, 	4780],
        "atk":           [47, 	60, 	73, 	86, 	100, 	113, 	126, 	139, 	152, 	166, 	179, 	192, 	205, 	219, 	232, 	245, 	258, 	272, 	285, 	298, 	311],
        "hp_":           [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        "atk_":          [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        "def_":          [8.7, 	11.2, 	13.7, 	16.2, 	18.6, 	21.1, 	23.6, 	26.1, 	28.6, 	31, 	33.5, 	36, 	38.5, 	40.9, 	43.4, 	45.9, 	48.4, 	50.8, 	53.3, 	55.8, 	58.3],
        "physical_dmg_": [8.7, 	11.2, 	13.7, 	16.2, 	16.2, 	21.1, 	23.6, 	26.1, 	28.6, 	31, 	33.5, 	36, 	38.5, 	40.9, 	43.4, 	45.9, 	48.4, 	50.8, 	53.3, 	55.8, 	58.3],
        "pyro_dmg_":     [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        "hydro_dmg_":    [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        "cryo_dmg_":     [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        "electro_dmg_":  [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        "anemo_dmg_":    [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        "geo_dmg_":      [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        "eleMas":        [28, 	36, 	44, 	52, 	60, 	68, 	76, 	84, 	91, 	99, 	107, 	115, 	123, 	131, 	139, 	147, 	155, 	163, 	171, 	179, 	187],
        "enerRech_":     [7.8, 	10.0, 	12.2, 	14.4, 	16.6, 	18.8, 	21.0, 	23.2, 	25.4, 	27.6, 	29.8, 	32.0, 	34.2, 	36.4, 	38.6, 	40.8, 	43.0, 	45.2, 	47.4, 	49.6, 	51.8],
        "critRate_":     [4.7, 	6.0, 	7.4, 	8.7, 	10.0, 	11.4, 	12.7, 	14.0, 	15.4, 	16.7, 	18.0, 	19.3, 	20.7, 	22.0, 	23.3, 	24.7, 	26.0, 	27.3, 	28.7, 	30.0, 	31.1],
        "critDMG_":      [9.3, 	11.9, 	14.6, 	17.2, 	19.9, 	22.5, 	25.2, 	27.8, 	30.5, 	33.1, 	35.8, 	38.4, 	41.1, 	43.7, 	46.3, 	49.0, 	51.6, 	54.3, 	56.9, 	59.6, 	62.2],
        "heal_":         [5.4, 	6.9, 	8.4, 	10.0, 	11.5, 	13.0, 	14.5, 	16.1, 	17.6, 	19.1, 	20.6, 	22.2, 	23.7, 	25.2, 	26.7, 	28.3, 	29.8, 	31.3, 	32.8, 	34.4, 	35.9],
    },
}

substat_roll_values = {
    "hp": {
        3: [100.38, 114.72, 129.06, 143.40],
        4: [167.30, 191.20, 215.10, 239.00],
        5: [209.13, 239.00, 269.88, 299.75]
    },
    "atk": {
        3: [6.54, 7.47, 8.40, 9.34],
        4: [10.89, 12.45, 14.00, 15.56],
        5: [13.62, 15.56, 17.51, 19.45]
    },
    "def": {
        3: [7.78, 8.89, 10.00, 11.11],
        4: [12.96, 14.82, 16.67, 18.52],
        5: [16.20, 18.52, 20.83, 23.15]
    },
    "hp_": {
        3: [2.45, 2.80, 3.15, 3.50],
        4: [3.26, 3.73, 4.20, 4.66],
        5: [4.08, 4.66, 5.25, 5.83]
    },
    "atk_": {
        3: [2.45, 2.80, 3.15, 3.50],
        4: [3.26, 3.73, 4.20, 4.66],
        5: [4.08, 4.66, 5.25, 5.83]
    },
    "def_": {
        3: [3.06, 3.50, 3.93, 4.37],
        4: [4.08, 4.66, 5.25, 5.83],
        5: [5.10, 5.83, 6.56, 7.29]
    },
    "eleMas": {
        3: [9.79, 11.19, 12.59, 13.99],
        4: [13.06, 14.92, 16.79, 18.56],
        5: [16.32, 18.65, 20.98, 23.31]
    },
    "enerRech_": {
        3: [2.72, 3.11, 3.50, 3.89],
        4: [3.63, 4.14, 4.66, 5.18],
        5: [4.53, 5.18, 5.83, 6.48]
    },
    "critRate_": {
        3: [1.63, 1.86, 2.10, 2.33],
        4: [2.18, 2.49, 2.80, 3.11],
        5: [2.72, 3.11, 3.50, 3.89]
    },
    "critDMG_":  {
        3: [3.26, 3.73, 4.20, 4.66],
        4: [4.35, 4.97, 5.60, 6.22],
        5: [5.44, 6.22, 6.99, 7.77]
    }
}


# Source: 
# https://genshin-impact.fandom.com/wiki/Artifacts/Distribution
# https://github.com/Dimbreath/GenshinData/blob/master/ExcelBinOutput/ReliquaryMainPropExcelConfigData.json
main_stat_drop_rate = {
    "Flower": {
        "hp": 100.0
    },
    "Plume": {
        "atk": 100.0
    },
    "Sands": {
        "hp_": 26.68,
        "atk_": 26.66,
        "def_": 26.66,
        "enerRech_": 10.0,
        "eleMas": 10.0
    },
    "Goblet": {
        "hp_": 21.25,
        "atk_": 21.25,
        "def_": 20.0,
        "pyro_dmg_": 5.0,
        "electro_dmg_": 5.0,
        "cryo_dmg_": 5.0,
        "hydro_dmg_": 5.0,
        "anemo_dmg_": 5.0,
        "geo_dmg_": 5.0,
        "physical_dmg_": 5.0,
        "eleMas": 2.5,
    },
    "Circlet": {
        "hp_": 22.0,
        "atk_": 22.0,
        "def_": 22.0,
        "critRate_": 10.0,
        "critDMG_": 10.0,
        "heal_": 10.0,
        "eleMas": 4.0
    }
}

_unrelated_substat_rarity = pd.Series({
    "hp":        0.1364,
    "atk":       0.1364,
    "def":       0.1364,
    "hp_":       0.0909,
    "atk_":      0.0909,
    "def_":      0.0909,
    "enerRech_": 0.0909,
    "eleMas":    0.0909,
    "critRate_": 0.0682,
    "critDMG_":  0.0682
})

substat_rarity = {
    "hp": pd.Series({
        "atk":       0.1579,
        "def":       0.1579,
        "hp_":       0.1053,
        "atk_":      0.1053,
        "def_":      0.1053,
        "enerRech_": 0.1053,
        "eleMas":    0.1053,
        "critRate_": 0.0789,
        "critDMG_":  0.0789
    }),
    "atk": pd.Series({
        "hp":        0.1579,
        "def":       0.1579,
        "hp_":       0.1053,
        "atk_":      0.1053,
        "def_":      0.1053,
        "enerRech_": 0.1053,
        "eleMas":    0.1053,
        "critRate_": 0.0789,
        "critDMG_":  0.0789
    }),
    "hp_": pd.Series({
        "hp":        0.15,
        "atk":       0.15,
        "def":       0.15,
        "atk_":      0.1,
        "def_":      0.1,
        "enerRech_": 0.1,
        "eleMas":    0.1,
        "critRate_": 0.075,
        "critDMG_":  0.075
    }),
    "atk_": pd.Series({
        "hp":        0.15,
        "atk":       0.15,
        "def":       0.15,
        "hp_":       0.1,
        "def_":      0.1,
        "enerRech_": 0.1,
        "eleMas":    0.1,
        "critRate_": 0.075,
        "critDMG_":  0.075
    }),
    "def_": pd.Series({
        "hp":        0.15,
        "atk":       0.15,
        "def":       0.15,
        "hp_":       0.1,
        "atk_":      0.1,
        "enerRech_": 0.1,
        "eleMas":    0.1,
        "critRate_": 0.075,
        "critDMG_":  0.075
    }),
    "physical_dmg_": _unrelated_substat_rarity,
    "pyro_dmg_":     _unrelated_substat_rarity,
    "hydro_dmg_":    _unrelated_substat_rarity,
    "cryo_dmg_":     _unrelated_substat_rarity,
    "electro_dmg_":  _unrelated_substat_rarity,
    "anemo_dmg_":    _unrelated_substat_rarity,
    "geo_dmg_":      _unrelated_substat_rarity,
    "eleMas": pd.Series({
        "hp":        0.15,
        "atk":       0.15,
        "def":       0.15,
        "hp_":       0.1,
        "atk_":      0.1,
        "def_":      0.1,
        "enerRech_": 0.1,
        "critRate_": 0.075,
        "critDMG_":  0.075
    }),
    "enerRech_": pd.Series({
        "hp":        0.15,
        "atk":       0.15,
        "def":       0.15,
        "hp_":       0.1,
        "atk_":      0.1,
        "def_":      0.1,
        "eleMas":    0.1,
        "critRate_": 0.075,
        "critDMG_":  0.075
    }),
    "critRate_": pd.Series({
        "hp":        0.1463,
        "atk":       0.1463,
        "def":       0.1463,
        "hp_":       0.0976,
        "atk_":      0.0976,
        "def_":      0.0976,
        "enerRech_": 0.0976,
        "eleMas":    0.0976,
        "critDMG_":  0.0732
    }),
    "critDMG_":  pd.Series({
        "hp":        0.1463,
        "atk":       0.1463,
        "def":       0.1463,
        "hp_":       0.0976,
        "atk_":      0.0976,
        "def_":      0.0976,
        "enerRech_": 0.0976,
        "eleMas":    0.0976,
        "critRate_": 0.0732
    }),
    "heal_": _unrelated_substat_rarity,
}
# fmt: on

max_level_by_stars = {3: 12, 4: 16, 5: 20}

set_stats = {
    "Initiate": [{}, {}],
    "Adventuerer": [{"hp": 1000}, {}],
    "LuckyDog": [{"def": 100}, {}],
    "TravelingDoctor": [{"heal_": 20.0}, {}],
    "ResolutionOfSojouner": [{"atk_": 18.0}, {"critRate_": 30.0}],
    "TinyMiracle": [{}, {}],
    "Berserker": [{"critRate_": 12.0}, {}],
    "Instructor": [{"eleMas": 80}, {"eleMas": 120}],
    "TheExile": [{"enerRech_": 20.0}, {}],
    "DefendersWill": [{"def_": 30.0}, {}],
    "BraveHeart": [{"atk_": 18.0}, {"dmg_": 15.0}],
    "MartialArtist": [{"dmg_": 15.0}, {"dmg_": 25.0}],
    "Gambler": [{"dmg_": 20.0}, {}],
    "Scholar": [{"enerRech_": 20.0}, {}],
    "PrayersForIllumination": [{}, {}],
    "PrayersForDestiny": [{}, {}],
    "PrayersForWisdom": [{}, {}],
    "PrayersForSpringtime": [{}, {}],
    "GladiatorsFinale": [{"atk_": 18.0}, {"dmg_": 35.0}],
    "WanderersTroupe": [{"eleMas": 80}, {"dmg_": 35.0}],
    "Thundersoother": [{}, {"dmg_": 35.0}],
    "ThunderingFury": [{"electro_dmg_": 15.0}, {}],
    "MaidenBeloved": [{"heal_": 15.0}, {"heal_": 20.0}],
    "ViridescentVenerer": [{"anemo_dmg_": 15.0}, {}],
    "CrimsonWitchOfFlames": [{"pyro_dmg_": 15.0}, {"dmg_": 15.0}],
    "Lavawalker": [{}, {"dmg_": 35.0}],
    "NoblesseOblige": [{"dmg_": 20.0}, {}],
    "BloodstainedChivalry": [{"physical_dmg_": 25.0}, {"dmg_": 50.0}],
    "ArchaicPetra": [{"geo_dmg_": 15.0}, {}],
    "RetracingBolide": [{}, {"dmg_": 40.0}],
    "BlizzardStrayer": [{"cryo_dmg_": 15.0}, {"critRate_": 40.0}],
    "HeartOfDepth": [{"hydro_dmg_": 15.0}, {"dmg_": 30.0}],
    "TenacityOfTheMillelith": [{"hp_": 20.0}, {"atk_": 20.0}],
    "PaleFlame": [{"physical_dmg_": 25.0}, {"atk_": 18.0, "physical_dmg_": 15.0}],
    "EmblemOfSeveredFate": [{"enerRech_": 20.0}, {"dmg_": {"enerRech_": 20.0}}],  # Unique stat transfer
    "ShimenawasReminiscence": [{"atk_": 18.0}, {"dmg_": 50.0}],
}

# Source: https://genshin-impact.fandom.com/wiki/Loot_System/Artifact_Drop_Distribution
extra_substat_probability = {"domain": 0.2, "world": 1 / 3}

dropped_from_world_boss = [
    "PrayersForIllumination",
    "PrayersForDestiny",
    "PrayersForWisdom",
    "PrayersForSpringtime",
    "GladiatorsFinale",
    "WanderersTroupe",
]

artifact_set_shortened = {
    "Initiate": "Initiate",
    "Adventuerer": "Adventurer",
    "LuckyDog": "Lucky",
    "TravelingDoctor": "Doctor",
    "ResolutionOfSojouner": "Resolution",
    "TinyMiracle": "Miracle",
    "Berserker": "Berserker",
    "Instructor": "Instructor",
    "TheExile": "Exile",
    "DefendersWill": "Defenders",
    "BraveHeart": "Brave",
    "MartialArtist": "Martial",
    "Gambler": "Gambler",
    "Scholar": "Scholar",
    "PrayersForIllumination": "Illumination",
    "PrayersForDestiny": "Destiny",
    "PrayersForWisdom": "Wisdom",
    "PrayersForSpringtime": "Springtime",
    "GladiatorsFinale": "Gladiators",
    "WanderersTroupe": "Wanderers",
    "Thundersoother": "Thundersoother",
    "ThunderingFury": "Thundering",
    "MaidenBeloved": "Maiden",
    "ViridescentVenerer": "Viridescent",
    "CrimsonWitchOfFlames": "Witch",
    "Lavawalker": "Lavawalker",
    "NoblesseOblige": "Noblesse",
    "BloodstainedChivalry": "Chivalry",
    "ArchaicPetra": "Petra",
    "RetracingBolide": "Bolide",
    "BlizzardStrayer": "Blizzard",
    "HeartOfDepth": "Depth",
    "TenacityOfTheMillelith": "Millelith",
    "PaleFlame": "Pale",
    "EmblemOfSeveredFate": "Emblem",
    "ShimenawasReminiscence": "Reminiscence",
}


character_stat_curves = _get_character_stat_curves()
weapon_stat_curves = _get_weapon_stat_curves()
substat_distributions = _get_substat_distribution_json()
value2rolls = _get_value_to_rolls_map()

log.info("Data imported and calcualted.")
log.info("")
