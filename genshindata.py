import itertools
import json
import logging
import math
import os

import numpy as np
import pandas as pd
import requests
from requests.api import request

log = logging.getLogger(__name__)
log.info("Importing and calculating data...")

# Copied from Genshin Optimizer pipeline/index.ts
# If you find this is out of date, feel free to copy and submit a pull request to update.
characterIdMap = {
    # 10000000: Kate
    # 10000001: Kate
    10000002: "kamisatoayaka",
    10000003: "jean",
    # 10000005: "traveler_geo",# travler_male
    10000006: "lisa",
    10000007: "traveler",  # traveler_female
    10000014: "barbara",
    10000015: "kaeya",
    10000016: "diluc",
    10000020: "razor",
    10000021: "amber",
    10000022: "venti",
    10000023: "xiangling",
    10000024: "beidou",
    10000025: "xingqiu",
    10000026: "xiao",
    10000027: "ningguang",
    10000029: "klee",
    10000030: "zhongli",
    10000031: "fischl",
    10000032: "bennett",
    10000033: "tartaglia",
    10000034: "noelle",
    10000035: "qiqi",
    10000036: "chongyun",
    10000037: "ganyu",
    10000038: "albedo",
    10000039: "diona",
    10000041: "mona",
    10000042: "keqing",
    10000043: "sucrose",
    10000044: "xinyan",
    10000045: "rosaria",
    10000046: "hutao",
    10000047: "kaedeharakazuha",
    10000048: "yanfei",
    10000049: "yoimiya",
    # 10000050: "TEMPLATE",
    10000051: "eula",
    # 10000052: "TEMPLATE",
    10000053: "sayu",
    # 10000054: "TEMPLATE",
    # 11000008: "TEMPLATE",
    # 11000009: "TEMPLATE",
    # 11000010: "TEMPLATE",
    # 11000011: "TEMPLATE",
    # 11000025: "TEMPLATE", Akuliya
    # 11000026: "TEMPLATE", Yaoyao
    # 11000028: "TEMPLATE", Shiro Maiden
    # 11000030: "TEMPLATE", Greatsword Maiden
    # 11000035: "TEMPLATE", Lance Warrioress
}


def _get_character_stats():
    """
    Contains the base stats and scaling reference for each character
    Sourced and modified from https://github.com/Dimbreath/GenshinData
    ExcelBinOutput\AvatarExcelConfigData.json
    """

    # Define file path
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "Data\AvatarExcelConfigData.json")

    # If file doesn't exist, download it
    if not os.path.isfile(file_path):
        log.info("Downloading character stats... (this is normal for first run)")
        url = "https://raw.githubusercontent.com/Dimbreath/GenshinData/master/ExcelBinOutput/AvatarExcelConfigData.json"
        request = requests.get(url, allow_redirects=True)
        with open(file_path, "wb") as file_handle:
            file_handle.write(request.content)
        log.info("Character stats downloaded.")

    # Read file
    with open(file_path, "r") as file_handle:
        character_stats_raw = json.load(file_handle)

    # Convert data form
    character_stats = {}
    for character_stat in character_stats_raw:
        if character_stat["FeatureTagGroupID"] in characterIdMap:
            character_name = characterIdMap[character_stat["FeatureTagGroupID"]]
            character_stats[character_name] = character_stat
            # Modify from list to dict
            character_stats[character_name]["PropGrowCurves"] = {
                x["Type"]: x["GrowCurve"] for x in character_stats[character_name]["PropGrowCurves"]
            }

    # # Read file
    # dir_path = os.path.dirname(os.path.realpath(__file__))
    # file_path = os.path.join(dir_path, "Data\character.json")
    # with open(file_path) as file_handle:
    #     character_stats = json.load(file_handle)

    return character_stats


character_stats = _get_character_stats()


def _get_stat_curves():
    """
    Contains the scaling multiplier for each level
    stat_curves[curve_name][level]
    curve_name: GROW_CURVE_{HP}{ATTACK}_S{4}{5}
    level: integer between 1 and 90 inclusive
    """

    # Define file path
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "Data\AvatarCurveExcelConfigData.json")

    # If file doesn't exist, download it
    if not os.path.isfile(file_path):
        log.info("Downloading character scaling curves... (this is normal for first run)")
        url = "https://raw.githubusercontent.com/Dimbreath/GenshinData/master/ExcelBinOutput/AvatarCurveExcelConfigData.json"
        request = requests.get(url, allow_redirects=True)
        with open(file_path, "wb") as file_handle:
            file_handle.write(request.content)
        log.info("Character scaling curves downloaded.")

    # Read file
    with open(file_path, "r") as file_handle:
        stat_curves_data = json.load(file_handle)

    # Convert to dict of numpy arrays
    stat_curves = {}
    for curve in range(4):
        curve_name = stat_curves_data[0]["CurveInfos"][curve]["Type"]
        stat_curves[curve_name] = np.array(
            [np.NaN] + [level["CurveInfos"][curve]["Value"] for level in stat_curves_data]
        )

    return stat_curves


stat_curves = _get_stat_curves()


def _get_promote_stats():
    """
    Contains the base stat increases for ascending characters
    promote_stats[promote_id][property_type][promote_level]
    promote_id: Integer representing character, found in __________
    property_type: FIGHT_PROP_BASE_{HP}/{DEFENSE}/{ATTACK}
    promote_level: Number of times ascended
    """

    # Define file path
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "Data\AvatarPromoteExcelConfigData.json")

    # If file doesn't exist, download it
    if not os.path.isfile(file_path):
        log.info("Downloading character promotion stats... (this is normal for first run)")
        url = "https://raw.githubusercontent.com/Dimbreath/GenshinData/master/ExcelBinOutput/AvatarPromoteExcelConfigData.json"
        request = requests.get(url, allow_redirects=True)
        with open(file_path, "wb") as file_handle:
            file_handle.write(request.content)
        log.info("Character promotion stats downloaded.")

    # Read file
    with open(file_path, "r") as file_handle:
        promote_data = json.load(file_handle)

    # Convert data
    promote_stats = {}
    for data in promote_data:
        promote_id = data["AvatarPromoteId"]

        if "PromoteLevel" not in data:
            promote_level = 0
        else:
            promote_level = data["PromoteLevel"]

        for property in data["AddProps"]:
            property_type = property["PropType"]
            value = property.get("Value", 0)
            promote_stats.setdefault(promote_id, {}).setdefault(property_type, {})[promote_level] = value

    return promote_stats


promote_stats = _get_promote_stats()

# fmt: off
promote_stats_map = {
    'FIGHT_PROP_HP_PERCENT': 'HP%',
    'FIGHT_PROP_ATTACK_PERCENT': 'ATK%',
    'FIGHT_PROP_DEFENSE_PERCENT': 'DEF%',
    'FIGHT_PROP_PHYSICAL_ADD_HURT': 'Physical DMG%',
    'FIGHT_PROP_FIRE_ADD_HURT': 'Elemental DMG%',
    'FIGHT_PROP_WATER_ADD_HURT': 'Elemental DMG%',
    'FIGHT_PROP_ICE_ADD_HURT': 'Elemental DMG%',
    'FIGHT_PROP_ELEC_ADD_HURT': 'Elemental DMG%',
    'FIGHT_PROP_WIND_ADD_HURT': 'Elemental DMG%',
    'FIGHT_PROP_ROCK_ADD_HURT': 'Elemental DMG%',
    'FIGHT_PROP_CHARGE_EFFICIENCY': 'Energy Recharge%',
    'FIGHT_PROP_ELEMENT_MASTERY': 'Elemental Mastery',
    'FIGHT_PROP_CRITICAL': 'Crit Rate%',
    'FIGHT_PROP_CRITICAL_HURT': 'Crit DMG%',
    'FIGHT_PROP_HEAL_ADD': 'Healing Bonus%'
}

stat_names = [
    'Base HP', 'Base ATK', 'Base DEF', 'HP', 'ATK', 'DEF', 'HP%', 'ATK%', 'DEF%', 'Physical DMG%', 'Elemental DMG%',
    'DMG%', 'Elemental Mastery', 'Energy Recharge%', 'Crit Rate%', 'Crit DMG%', 'Healing Bonus%', 'probability'
]

main_stat_scaling = {
    1: {
        'HP':                [129, 	178, 	227, 	275, 	324],
        'ATK':               [8, 	12, 	15, 	18, 	21],
        'HP%':               [3.1, 	4.3, 	5.5, 	6.7, 	7.9],
        'ATK%':              [3.1, 	4.3, 	5.5, 	6.7, 	7.9],
        'DEF%':              [3.9, 	5.4, 	6.9, 	8.4, 	9.9],
        'Physical DMG%':     [3.9, 	5.4, 	6.9, 	8.4, 	9.9],
        'Elemental DMG%':    [3.1, 	4.3, 	5.5, 	6.7, 	7.9],
        'Elemental Mastery': [13, 	17, 	22, 	27, 	32],
        'Energy Recharge%':  [3.5, 	4.8, 	6.1, 	7.5, 	8.8],
        'Crit Rate%':        [2.1, 	2.9, 	3.7, 	4.5, 	5.3],
        'Crit DMG%':         [4.2, 	5.8, 	7.4, 	9.0, 	10.5],
        'Healing Bonus%':    [2.4, 	3.3, 	4.3, 	5.2, 	6.1],
    },
    2: {
        'HP':                [258, 	331, 	404, 	478, 	551],
        'ATK':               [17, 	22, 	26, 	31, 	36],
        'HP%':               [4.2, 	5.4, 	6.6, 	7.8, 	9],
        'ATK%':              [4.2, 	5.4, 	6.6, 	7.8, 	9],
        'DEF%':              [5.2, 	6.7, 	8.2, 	9.7, 	11.2],
        'Physical DMG%':     [5.2, 	6.7, 	8.2, 	9.7, 	11.2],
        'Elemental DMG%':    [4.2, 	5.4, 	6.6, 	7.8, 	9],
        'Elemental Mastery': [17, 	22, 	26, 	31, 	36],
        'Energy Recharge%':  [4.7, 	6.0, 	7.3, 	8.6, 	9.9],
        'Crit Rate%':        [2.8, 	3.6, 	4.4, 	5.2, 	6],
        'Crit DMG%':         [5.6, 	7.2, 	8.8, 	10.4, 	11.9],
        'Healing Bonus%':    [3.2, 	4.1, 	5.1, 	6.0, 	6.9],
    },
    3: {
        'HP':                [430, 	552, 	674, 	796, 	918, 	1040, 	1162, 	1283, 	1405, 	1527, 	1649, 	1771, 	1893],
        'ATK':               [28, 	36, 	44, 	52, 	60, 	68, 	76, 	84, 	91, 	99, 	107, 	115, 	123],
        'HP%':               [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        'ATK%':              [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        'DEF%':              [6.6, 	8.4, 	10.3, 	12.1, 	14.0, 	15.8, 	17.7, 	19.6, 	21.4, 	23.3, 	25.1, 	27.0, 	28.8],
        'Physical DMG%':     [6.6, 	8.4, 	10.3, 	12.1, 	14.0, 	15.8, 	17.7, 	19.6, 	21.4, 	23.3, 	25.1, 	27.0, 	28.8],
        'Elemental DMG%':    [5.2, 	6.7, 	8.2, 	9.7, 	11.2, 	12.7, 	14.2, 	15.6, 	17.1, 	18.6, 	20.1, 	21.6, 	23.1],
        'Elemental Mastery': [21, 	27, 	33, 	39, 	45, 	51, 	57, 	63, 	69, 	75, 	80, 	86, 	92],
        'Energy Recharge%':  [5.8, 	7.5, 	9.1, 	10.8, 	12.4, 	14.1, 	15.7, 	17.4, 	19.0, 	20.7, 	22.3, 	24.0, 	25.6],
        'Crit Rate%':        [3.5, 	4.5, 	5.5, 	6.5, 	7.5, 	8.4, 	9.4, 	10.4, 	11.4, 	12.4, 	13.4, 	14.4, 	15.4],
        'Crit DMG%':         [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8],
        'Healing Bonus%':    [4.0, 	5.2, 	6.3, 	7.5, 	8.6, 	9.8, 	10.9, 	12.0, 	13.2, 	14.3, 	15.5, 	16.6, 	17.8],
    },
    4: {
        'HP':                [645, 	828, 	1011, 	1194, 	1377, 	1559, 	1742, 	1925, 	2108, 	2291, 	2474, 	2657, 	2839, 	3022, 	3205, 	3388, 	3571],
        'ATK':               [42, 	54, 	66, 	78, 	90, 	102, 	113, 	125, 	137, 	149, 	161, 	173, 	185, 	197, 	209, 	221, 	232],
        'HP%':               [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        'ATK%':              [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        'DEF%':              [7.9, 	10.1, 	12.3, 	14.6, 	16.8, 	19.0, 	21.2, 	23.5, 	25.7, 	27.9, 	30.2, 	32.4, 	34.6, 	36.8, 	39.1, 	41.3, 	43.5],
        'Physical DMG%':     [7.9, 	10.1, 	12.3, 	14.6, 	16.8, 	19.0, 	21.2, 	23.5, 	25.7, 	27.9, 	30.2, 	32.4, 	34.6, 	36.8, 	39.1, 	41.3, 	43.5],
        'Elemental DMG%':    [6.3, 	8.1, 	9.9, 	11.6, 	13.4, 	15.2, 	17.0, 	18.8, 	20.6, 	22.3, 	24.1, 	25.9, 	27.7, 	29.5, 	31.3, 	33.0, 	34.8],
        'Elemental Mastery': [25, 	32, 	39, 	47, 	54, 	61, 	68, 	75, 	82, 	89, 	97, 	104, 	111, 	118, 	125, 	132, 	139],
        'Energy Recharge%':  [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7],
        'Crit Rate%':        [4.2, 	5.4, 	6.6, 	7.8, 	9.0, 	10.1, 	11.3, 	12.5, 	13.7, 	14.9, 	16.1, 	17.3, 	18.5, 	19.7, 	20.8, 	22.0, 	23.2],
        'Crit DMG%':         [8.4, 	10.8, 	13.1, 	15.5, 	17.9, 	20.3, 	22.7, 	25.0, 	27.4, 	29.8, 	32.2, 	34.5, 	36.9, 	39.3, 	41.7, 	44.1, 	46.4],
        'Healing Bonus%':    [4.8, 	6.2, 	7.6, 	9.0, 	10.3, 	11.7, 	13.1, 	14.4, 	15.8, 	17.2, 	18.6, 	19.9, 	21.3, 	22.7, 	24.0, 	25.4, 	26.8],
    },
    5: {
        'HP':                [717, 	920, 	1123, 	1326, 	1530, 	1733, 	1936, 	2139, 	2342, 	2545, 	2749, 	2952, 	3155, 	3358, 	3561, 	3764, 	3967, 	4171, 	4374, 	4577, 	4780],
        'ATK':               [47, 	60, 	73, 	86, 	100, 	113, 	126, 	139, 	152, 	166, 	179, 	192, 	205, 	219, 	232, 	245, 	258, 	272, 	285, 	298, 	311],
        'HP%':               [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        'ATK%':              [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        'DEF%':              [8.7, 	11.2, 	13.7, 	16.2, 	18.6, 	21.1, 	23.6, 	26.1, 	28.6, 	31, 	33.5, 	36, 	38.5, 	40.9, 	43.4, 	45.9, 	48.4, 	50.8, 	53.3, 	55.8, 	58.3],
        'Physical DMG%':     [8.7, 	11.2, 	13.7, 	16.2, 	16.2, 	21.1, 	23.6, 	26.1, 	28.6, 	31, 	33.5, 	36, 	38.5, 	40.9, 	43.4, 	45.9, 	48.4, 	50.8, 	53.3, 	55.8, 	58.3],
        'Elemental DMG%':    [7.0, 	9.0, 	11.0, 	12.9, 	14.9, 	16.9, 	18.9, 	20.9, 	22.8, 	24.8, 	26.8, 	28.8, 	30.8, 	32.8, 	34.7, 	36.7, 	38.7, 	40.7, 	42.7, 	44.6, 	46.6],
        'Elemental Mastery': [28, 	36, 	44, 	52, 	60, 	68, 	76, 	84, 	91, 	99, 	107, 	115, 	123, 	131, 	139, 	147, 	155, 	163, 	171, 	179, 	187],
        'Energy Recharge%':  [7.8, 	10.0, 	12.2, 	14.4, 	16.6, 	18.8, 	21.0, 	23.2, 	25.4, 	27.6, 	29.8, 	32.0, 	34.2, 	36.4, 	38.6, 	40.8, 	43.0, 	45.2, 	47.4, 	49.6, 	51.8],
        'Crit Rate%':        [4.7, 	6.0, 	7.4, 	8.7, 	10.0, 	11.4, 	12.7, 	14.0, 	15.4, 	16.7, 	18.0, 	19.3, 	20.7, 	22.0, 	23.3, 	24.7, 	26.0, 	27.3, 	28.7, 	30.0, 	31.1],
        'Crit DMG%':         [9.3, 	11.9, 	14.6, 	17.2, 	19.9, 	22.5, 	25.2, 	27.8, 	30.5, 	33.1, 	35.8, 	38.4, 	41.1, 	43.7, 	46.3, 	49.0, 	51.6, 	54.3, 	56.9, 	59.6, 	62.2],
        'Healing Bonus%':    [5.4, 	6.9, 	8.4, 	10.0, 	11.5, 	13.0, 	14.5, 	16.1, 	17.6, 	19.1, 	20.6, 	22.2, 	23.7, 	25.2, 	26.7, 	28.3, 	29.8, 	31.3, 	32.8, 	34.4, 	35.9],
    },
}

substat_roll_values = {
    'HP': {
        1: [23.90, 29.88],
        2: [50.19, 60.95, 71.70],
        3: [100.38, 114.72, 129.06, 143.40],
        4: [167.30, 191.20, 215.10, 239.00],
        5: [209.13, 239.00, 269.88, 299.75]
    },
    'ATK': {
        1: [1.56, 1.95],
        2: [3.27, 3.97, 4.67],
        3: [6.54, 7.47, 8.40, 9.34],
        4: [10.89, 12.45, 14.00, 15.56],
        5: [13.62, 15.56, 17.51, 19.45]
    },
    'DEF': {
        1: [1.85, 2.31],
        2: [3.89, 4.72, 5.56],
        3: [7.78, 8.89, 10.00, 11.11],
        4: [12.96, 14.82, 16.67, 18.52],
        5: [16.20, 18.52, 20.83, 23.15]
    },
    'HP%': {
        1: [1.17, 1.46],
        2: [1.63, 1.98, 2.33],
        3: [2.45, 2.80, 3.15, 3.50],
        4: [3.26, 3.73, 4.20, 4.66],
        5: [4.08, 4.66, 5.25, 5.83]
    },
    'ATK%': {
        1: [1.17, 1.46],
        2: [1.63, 1.98, 2.33],
        3: [2.45, 2.80, 3.15, 3.50],
        4: [3.26, 3.73, 4.20, 4.66],
        5: [4.08, 4.66, 5.25, 5.83]
    },
    'DEF%': {
        1: [1.46, 1.82],
        2: [2.04, 2.48, 2.91],
        3: [3.06, 3.50, 3.93, 4.37],
        4: [4.08, 4.66, 5.25, 5.83],
        5: [5.10, 5.83, 6.56, 7.29]
    },
    'Elemental Mastery': {
        1: [4.66, 5.83],
        2: [6.53, 7.93, 9.33],
        3: [9.79, 11.19, 12.59, 13.99],
        4: [13.06, 14.92, 16.79, 18.56],
        5: [16.32, 18.65, 20.98, 23.31]
    },
    'Energy Recharge%': {
        1: [1.30, 1.62],
        2: [1.81, 2.20, 2.59, ],
        3: [2.72, 3.11, 3.50, 3.89],
        4: [3.63, 4.14, 4.66, 5.18],
        5: [4.53, 5.18, 5.83, 6.48]
    },
    'Crit Rate%': {
        1: [0.78, 0.97],
        2: [1.09, 1.32, 1.55],
        3: [1.63, 1.86, 2.10, 2.33],
        4: [2.18, 2.49, 2.80, 3.11],
        5: [2.72, 3.11, 3.50, 3.89]
    },
    'Crit DMG%':  {
        1: [1.55, 1.94],
        2: [2.18, 2.64, 3.11],
        3: [3.26, 3.73, 4.20, 4.66],
        4: [4.35, 4.97, 5.60, 6.22],
        5: [5.44, 6.22, 6.99, 7.77]
    }
}

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
    '''Implement 5 and above, give it a shove rounding'''
    if value * 10**precision % 1 == 0.5:
        return math.ceil(value * 10**precision) / 10**precision
    else:
        return round(value, precision)

value2rolls = _get_value_to_rolls_map()

_unrelated_substat_rarity = pd.Series({
    'HP':                0.1364,
    'ATK':               0.1364,
    'DEF':               0.1364,
    'HP%':               0.0909,
    'ATK%':              0.0909,
    'DEF%':              0.0909,
    'Energy Recharge%':  0.0909,
    'Elemental Mastery': 0.0909,
    'Crit Rate%':        0.0682,
    'Crit DMG%':         0.0682
})

substat_rarity = {
    'HP': pd.Series({
        'ATK':               0.1579,
        'DEF':               0.1579,
        'HP%':               0.1053,
        'ATK%':              0.1053,
        'DEF%':              0.1053,
        'Energy Recharge%':  0.1053,
        'Elemental Mastery': 0.1053,
        'Crit Rate%':        0.0789,
        'Crit DMG%':         0.0789
    }),
    'ATK': pd.Series({
        'HP':                0.1579,
        'DEF':               0.1579,
        'HP%':               0.1053,
        'ATK%':              0.1053,
        'DEF%':              0.1053,
        'Energy Recharge%':  0.1053,
        'Elemental Mastery': 0.1053,
        'Crit Rate%':        0.0789,
        'Crit DMG%':         0.0789
    }),
    'HP%': pd.Series({
        'HP':                0.15,
        'ATK':               0.15,
        'DEF':               0.15,
        'ATK%':              0.1,
        'DEF%':              0.1,
        'Energy Recharge%':  0.1,
        'Elemental Mastery': 0.1,
        'Crit Rate%':        0.075,
        'Crit DMG%':         0.075
    }),
    'ATK%': pd.Series({
        'HP':                0.15,
        'ATK':               0.15,
        'DEF':               0.15,
        'HP%':               0.1,
        'DEF%':              0.1,
        'Energy Recharge%':  0.1,
        'Elemental Mastery': 0.1,
        'Crit Rate%':        0.075,
        'Crit DMG%':         0.075
    }),
    'DEF%': pd.Series({
        'HP':                0.15,
        'ATK':               0.15,
        'DEF':               0.15,
        'HP%':               0.1,
        'ATK%':              0.1,
        'Energy Recharge%':  0.1,
        'Elemental Mastery': 0.1,
        'Crit Rate%':        0.075,
        'Crit DMG%':         0.075
    }),
    'Physical DMG%': _unrelated_substat_rarity,
    'Elemental DMG%': _unrelated_substat_rarity,
    'Elemental Mastery': pd.Series({
        'HP':                0.15,
        'ATK':               0.15,
        'DEF':               0.15,
        'HP%':               0.1,
        'ATK%':              0.1,
        'DEF%':              0.1,
        'Energy Recharge%':  0.1,
        'Crit Rate%':        0.075,
        'Crit DMG%':         0.075
    }),
    'Energy Recharge%': pd.Series({
        'HP':                0.15,
        'ATK':               0.15,
        'DEF':               0.15,
        'HP%':               0.1,
        'ATK%':              0.1,
        'DEF%':              0.1,
        'Elemental Mastery': 0.1,
        'Crit Rate%':        0.075,
        'Crit DMG%':         0.075
    }),
    'Crit Rate%': pd.Series({
        'HP':                0.1463,
        'ATK':               0.1463,
        'DEF':               0.1463,
        'HP%':               0.0976,
        'ATK%':              0.0976,
        'DEF%':              0.0976,
        'Energy Recharge%':  0.0976,
        'Elemental Mastery': 0.0976,
        'Crit DMG%':         0.0732
    }),
    'Crit DMG%':  pd.Series({
        'HP':                0.1463,
        'ATK':               0.1463,
        'DEF':               0.1463,
        'HP%':               0.0976,
        'ATK%':              0.0976,
        'DEF%':              0.0976,
        'Energy Recharge%':  0.0976,
        'Elemental Mastery': 0.0976,
        'Crit Rate%':        0.0732
    }),
    'Healing Bonus%': _unrelated_substat_rarity,
}

    
# Source: https://genshin-impact.fandom.com/wiki/Loot_System/Artifact_Drop_Distribution
extra_substat_probability = {
    'domain':        [np.nan, 0.0, 0.2, 0.2, 0.2, 0.2],
    'world boss':    [np.nan, 0.0, 1/3, 1/3, 1/3, 1/3],
    'weekly boss':   [np.nan, 0/3, 1/3, 1/3, 1/3, 1/3],
    'elite enemies': [np.nan, 0.0, 0.1, 0.1, 0.03, 0.03],
    'never':         [np.nan, 0.0, 0.0, 0.0, 0.0, 0.0],
    'always':        [np.nan, 1.0, 1.0, 1.0, 1.0, 1.0]
}

max_level_by_stars = [np.nan, 4, 4, 12, 16, 20]

valid_sets = [
    'initiate', 'adventurer', 'lucky', 'doctor', 'resolution', 'miracle', 'berserker', 'instructor', 'exile',
    'defenders', 'brave', 'martial', 'gambler', 'scholar', 'illumination', 'destiny', 'wisdom', 'springtime',
    'gladiators', 'wanderers', 'thundersoother', 'thundering', 'maiden', 'viridescent', 'witch', 'lavawalker',
    'noblesse', 'chivalry', 'petra', 'bolide', 'blizard', 'depth', 'millelith', 'pale', 'emblem', 'reminiscence'
]

set_stats = {
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

default_artifact_source = {
    'initiate':       'domain', # Initiate set does not drop naturally. 
    'adventurer':     'elite enemies',
    'lucky':          'elite enemies',
    'doctor':         'elite enemies',
    'resolution':     'domain',
    'miracle':        'domain',
    'berserker':      'domain',
    'instructor':     'domain',
    'exile':          'domain',
    'defenders':      'domain',
    'brave':          'domain',
    'martial':        'domain',
    'gambler':        'domain',
    'scholar':        'domain',
    'illumination':   'world boss',
    'destiny':        'world boss',
    'wisdom':         'world boss',
    'springtime':     'world boss',
    'gladiators':     'world boss',
    'wanderers':      'world boss',
    'thundersoother': 'domain',
    'thundering':     'domain',
    'maiden':         'domain',
    'viridescent':    'domain',
    'witch':          'domain',
    'lavawalker':     'domain',
    'noblesse':       'domain',
    'chivalry':       'domain',
    'petra':          'domain',
    'bolide':         'domain',
    'blizard':        'domain',
    'depth':          'domain',
    'millelith':      'domain',
    'pale':           'domain',
    'emblem':         'domain',
    'reminiscence':   'domain'
}
# fmt: on

log.info("Data imported and calcualted.")
