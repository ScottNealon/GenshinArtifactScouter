import json
import os

import numpy as np

def _get_character_stats():
    '''
    Contains the base stats and scaling reference for each character
    Sourced and modified from https://github.com/Dimbreath/GenshinData
    ExcelBinOutput\AvatarExcelConfigData.json
    '''

    # Read file
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, 'Data\character.json')
    with open(file_path) as f:
        character_stats = json.load(f)

    return character_stats

character_stats = _get_character_stats()

def _get_stat_curves():
    '''
    Contains the scaling multiplier for each level
    stat_curves[curve_name][level]
    curve_name: GROW_CURVE_{HP}{ATTACK}_S{4}{5}
    level: integer between 1 and 90 inclusive
    '''

    # Read file
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, 'Data\AvatarCurveExcelConfigData.json')
    with open(file_path) as f:
        stat_curves_data = json.load(f)

    # Convert to dict of numpy arrays
    stat_curves = {}
    for curve in range(4):
        curve_name = stat_curves_data[0]['CurveInfos'][curve]['Type']
        stat_curves[curve_name] = np.array([np.NaN] + [level['CurveInfos'][curve]['Value'] for level in stat_curves_data])

    return stat_curves

stat_curves = _get_stat_curves()

def _get_promote_stats():
    '''
    Contains the base stat increases for ascending characters
    promote_stats[promote_id][property_type][promote_level]
    promote_id: Integer representing character, found in __________
    property_type: FIGHT_PROP_BASE_{HP}/{DEFENSE}/{ATTACK}
    promote_level: Number of times ascended
    '''

    # Read file
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, 'Data\AvatarPromoteExcelConfigData.json')
    with open(file_path) as f:
        promote_data = json.load(f)

    # Convert data
    promote_stats = {}
    for data in promote_data:
        promote_id = data['AvatarPromoteId']

        if 'PromoteLevel' not in data:
            promote_level = 0
        else:
            promote_level = data['PromoteLevel']

        for property in data['AddProps']:
            property_type = property['PropType']
            value = property.get('Value', 0)
            promote_stats.setdefault(promote_id, {}).setdefault(property_type, {})[promote_level] = value

    return promote_stats

promote_stats = _get_promote_stats()

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