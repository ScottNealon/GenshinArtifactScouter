"""
Preparatory python script used to generate character and weapon json files. Not used in regular operations.
To use, run `python -m src.setup_scripts.generate_data_jsons` from GenshinArtifactScouter directory.
"""

import json
import os

import numpy as np
import requests
from src import GOOD_database, genshin_data

# Copied from Genshin Optimizer pipeline/index.ts
# If you find this is out of date, feel free to copy and submit a pull request to update.
character_id_map = {
    10000002: "KamisatoAyaka",
    10000003: "Jean",
    10000006: "Lisa",
    10000007: "Traveler",
    10000014: "Barbara",
    10000015: "Kaeya",
    10000016: "Diluc",
    10000020: "Razor",
    10000021: "Amber",
    10000022: "Venti",
    10000023: "Xiangling",
    10000024: "Beidou",
    10000025: "Xingqiu",
    10000026: "Xiao",
    10000027: "Ningguang",
    10000029: "Klee",
    10000030: "Zhongli",
    10000031: "Fischl",
    10000032: "Bennett",
    10000033: "Tartaglia",
    10000034: "Noelle",
    10000035: "Qiqi",
    10000036: "Chongyun",
    10000037: "Ganyu",
    10000038: "Albedo",
    10000039: "Diona",
    10000041: "Mona",
    10000042: "Keqing",
    10000043: "Sucrose",
    10000044: "Xinyan",
    10000045: "Rosaria",
    10000046: "HuTao",
    10000047: "KaedeharaKazuha",
    10000048: "Yanfei",
    10000049: "Yoimiya",
    10000051: "Eula",
    10000052: "RaidenShogun",
    10000053: "Sayu",
    10000056: "KujouSara",
    10000062: "Aloy",
}
weapon_id_map = weaponIdMap = {
    # swords
    11101: "DullBlade",
    11201: "SilverSword",
    11301: "CoolSteel",
    11302: "HarbingerOfDawn",
    11303: "TravelersHandySword",
    11304: "DarkIronSword",
    11305: "FilletBlade",
    11306: "SkyriderSword",
    11401: "FavoniusSword",
    11402: "TheFlute",
    11403: "SacrificialSword",
    11404: "RoyalLongsword",
    11405: "LionsRoar",
    11406: "PrototypeRancour",
    11407: "IronSting",
    11408: "BlackcliffLongsword",
    11409: "TheBlackSword",
    11410: "TheAlleyFlash",
    # 11411: "",
    11412: "SwordOfDescension",
    11413: "FesteringDesire",
    11414: "AmenomaKageuchi",
    11501: "AquilaFavonia",
    11502: "SkywardBlade",
    11503: "FreedomSworn",
    11504: "SummitShaper",
    11505: "PrimordialJadeCutter",
    # 11506: "PrimordialJadeCutter",
    # 11507: "One Side",#new weapon?
    # 11508: "",
    11509: "MistsplitterReforged",
    # claymore
    12101: "WasterGreatsword",
    12201: "OldMercsPal",
    12301: "FerrousShadow",
    12302: "BloodtaintedGreatsword",
    12303: "WhiteIronGreatsword",
    12304: "Quartz",
    12305: "DebateClub",
    12306: "SkyriderGreatsword",
    12401: "FavoniusGreatsword",
    12402: "TheBell",
    12403: "SacrificialGreatsword",
    12404: "RoyalGreatsword",
    12405: "Rainslasher",
    12406: "PrototypeArchaic",
    12407: "Whiteblind",
    12408: "BlackcliffSlasher",
    12409: "SerpentSpine",
    12410: "LithicBlade",
    12411: "SnowTombedStarsilver",
    12412: "LuxuriousSeaLord",
    12414: "KatsuragikiriNagamasa",
    12501: "SkywardPride",
    12502: "WolfsGravestone",
    12503: "SongOfBrokenPines",
    12504: "TheUnforged",
    # 12505: "Primordial Jade Greatsword",
    # 12506: "The Other Side",
    # 12508: "",
    # polearm
    13101: "BeginnersProtector",
    13201: "IronPoint",
    13301: "WhiteTassel",
    13302: "Halberd",
    13303: "BlackTassel",
    # 13304: "The Flagstaff",
    13401: "DragonsBane",
    13402: "PrototypeStarglitter",
    13403: "CrescentPike",
    13404: "BlackcliffPole",
    13405: "Deathmatch",
    13406: "LithicSpear",
    13407: "FavoniusLance",
    13408: "RoyalSpear",
    13409: "DragonspineSpear",
    13414: "KitainCrossSpear",
    13415: "TheCatch",
    13501: "StaffOfHoma",
    13502: "SkywardSpine",
    # 13503: "",
    13504: "VortexVanquisher",
    13505: "PrimordialJadeWingedSpear",
    # 13506: "Deicide",
    # 13507: "",
    13509: "EngulfingLightning",
    # catalyst
    14101: "ApprenticesNotes",
    14201: "PocketGrimoire",
    14301: "MagicGuide",
    14302: "ThrillingTalesOfDragonSlayers",
    14303: "OtherworldlyStory",
    14304: "EmeraldOrb",
    14305: "TwinNephrite",
    # 14306: "Amber Bead",
    14401: "FavoniusCodex",
    14402: "TheWidsith",
    14403: "SacrificialFragments",
    14404: "RoyalGrimoire",
    14405: "SolarPearl",
    14406: "PrototypeAmber",
    14407: "MappaMare",
    14408: "BlackcliffAgate",
    14409: "EyeOfPerception",
    14410: "WineAndSong",
    # 14411: "",
    14412: "Frostbearer",
    14413: "DodocoTales",
    14414: "HakushinRing",
    14501: "SkywardAtlas",
    14502: "LostPrayerToTheSacredWinds",
    # 14503: "Lost Ballade",
    14504: "MemoryOfDust",
    14506: "EverlastingMoonglow",
    # 14505: "Primordial Jade Regalia",
    # 14506: "Diamond Visage",
    # 14508: "",
    # bow
    15101: "HuntersBow",
    15201: "SeasonedHuntersBow",
    15301: "RavenBow",
    15302: "SharpshootersOath",
    15303: "RecurveBow",
    15304: "Slingshot",
    15305: "Messenger",
    15306: "EbonyBow",
    15401: "FavoniusWarbow",
    15402: "TheStringless",
    15403: "SacrificialBow",
    15404: "RoyalBow",
    15405: "Rust",
    15406: "PrototypeCrescent",
    15407: "CompoundBow",
    15408: "BlackcliffWarbow",
    15409: "TheViridescentHunt",
    15410: "AlleyHunter",
    15412: "MitternachtsWaltz",
    15413: "WindblumeOde",
    15414: "Hamayumi",
    15415: "Predator",
    15501: "SkywardHarp",
    15502: "AmosBow",
    15503: "ElegyForTheEnd",
    15509: "ThunderingPulse",
}

weapon_type_map = {
    "WEAPON_SWORD_ONE_HAND": "sword",
    "WEAPON_CLAYMORE": "claymore",
    "WEAPON_POLE": "polearm",
    "WEAPON_CATALYST": "catalyst",
    "WEAPON_BOW": "bow",
}

# Get Character stats
url = "https://raw.githubusercontent.com/Dimbreath/GenshinData/master/ExcelBinOutput/AvatarExcelConfigData.json"
request = requests.get(url, allow_redirects=True)
character_stats_raw = request.json()
# Convert data form
character_stats = {}
for character_stat in character_stats_raw:
    if character_stat["FeatureTagGroupID"] in character_id_map:
        character_name = character_id_map[character_stat["FeatureTagGroupID"]]
        character_stats[character_name] = character_stat
        # Modify from list to dict
        character_stats[character_name]["PropGrowCurves"] = {
            x["Type"]: x["GrowCurve"] for x in character_stats[character_name]["PropGrowCurves"]
        }

# Get character stat curves
character_stat_curves = genshin_data.character_stat_curves

# Get character promote curves
url = "https://raw.githubusercontent.com/Dimbreath/GenshinData/master/ExcelBinOutput/AvatarPromoteExcelConfigData.json"
request = requests.get(url, allow_redirects=True)
promote_data = request.json()
# Convert data
character_promote_stats = {}
for data in promote_data:
    promote_id = data["AvatarPromoteId"]
    if "PromoteLevel" not in data:
        promote_level = 0
    else:
        promote_level = data["PromoteLevel"]
    for property in data["AddProps"]:
        property_type = property["PropType"]
        value = property.get("Value", 0)
        character_promote_stats.setdefault(promote_id, {}).setdefault(property_type, {})[promote_level] = value

# Get weapon stats
url = "https://raw.githubusercontent.com/Dimbreath/GenshinData/master/ExcelBinOutput/WeaponExcelConfigData.json"
request = requests.get(url, allow_redirects=True)
weapon_stats_raw = request.json()
# Convert data form
weapon_stats = {}
for weapon_stat in weapon_stats_raw:
    if weapon_stat["Id"] in weapon_id_map:
        weapon_name = weapon_id_map[weapon_stat["Id"]]
        weapon_stats[weapon_name] = weapon_stat
        props = {}
        for prop in weapon_stats[weapon_name]["WeaponProp"]:
            if "InitValue" in prop:
                props[prop["PropType"]] = {"InitValue": prop["InitValue"], "Type": prop["Type"]}
        weapon_stats[weapon_name]["WeaponProp"] = props

# Get weapon stat curves
weapon_stat_curves = genshin_data.weapon_stat_curves

# Get weapon promote curves
url = "https://raw.githubusercontent.com/Dimbreath/GenshinData/master/ExcelBinOutput/WeaponPromoteExcelConfigData.json"
request = requests.get(url, allow_redirects=True)
promote_data = request.json()
# Convert data
weapon_promote_stats = {}
for data in promote_data:
    promote_id = data["WeaponPromoteId"]
    if "PromoteLevel" not in data:
        promote_level = 0
    else:
        promote_level = data["PromoteLevel"]
    for property in data["AddProps"]:
        property_type = property["PropType"]
        value = property.get("Value", 0)
        weapon_promote_stats.setdefault(promote_id, {}).setdefault(property_type, {})[promote_level] = value

# Find data directory
_data_dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../data")

# Write to character directory
for character_name, values in character_stats.items():
    character_data = {}
    character_data["element"] = "FILL"
    character_data["weapon_type"] = "FILL"
    character_data["stars"] = int(values["PropGrowCurves"]["FIGHT_PROP_BASE_HP"][-1])
    character_data["initial_HP"] = values["HpBase"]
    character_data["initial_ATK"] = values["AttackBase"]
    character_data["initial_DEF"] = values["DefenseBase"]
    promote_id = values["AvatarPromoteId"]
    character_data["HP_ascension_scaling"] = list(character_promote_stats[promote_id]["FIGHT_PROP_BASE_HP"].values())
    character_data["ATK_ascension_scaling"] = list(
        character_promote_stats[promote_id]["FIGHT_PROP_BASE_ATTACK"].values()
    )
    character_data["DEF_ascension_scaling"] = list(
        character_promote_stats[promote_id]["FIGHT_PROP_BASE_DEFENSE"].values()
    )
    ascension_stat = list(character_promote_stats[promote_id].keys())[3]
    character_data["ascension_stat"] = genshin_data.promote_stats_map[ascension_stat]
    character_data["ascension_stat_scaling"] = list(character_promote_stats[promote_id][ascension_stat].values())

    file_path = os.path.join(_data_dir_path, "characters", f"{character_name}.json")
    with open(file_path, "w") as file_handle:
        json.dump(character_data, file_handle, indent=4)

# Write to weapon directory
for weapon_name, values in weapon_stats.items():
    weapon = {}
    weapon["weapon_type"] = weapon_type_map[values["WeaponType"]]
    weapon["initial_ATK"] = values["WeaponProp"]["FIGHT_PROP_BASE_ATTACK"]["InitValue"]
    weapon["base_ATK_scaling"] = values["WeaponProp"]["FIGHT_PROP_BASE_ATTACK"]["Type"]
    promote_id = values["WeaponPromoteId"]
    weapon["ATK_ascension_scaling"] = list(weapon_promote_stats[promote_id]["FIGHT_PROP_BASE_ATTACK"].values())
    if len(values["WeaponProp"]) > 1:
        ascension_stat = list(values["WeaponProp"].keys())[1]
        weapon["ascension_stat"] = genshin_data.promote_stats_map[ascension_stat]
        weapon["base_ascension_stat"] = values["WeaponProp"][ascension_stat]["InitValue"]
        weapon["ascension_stat_scaling"] = values["WeaponProp"][ascension_stat]["Type"]

    file_path = os.path.join(_data_dir_path, "weapons", f"{weapon_name}.json")
    with open(file_path, "w") as file_handle:
        json.dump(weapon, file_handle, indent=4)
