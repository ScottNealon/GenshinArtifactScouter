import logging
import logging.config
import os

dir_path = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join(dir_path, "config", "logging.conf")
logging.config.fileConfig(config_path)

from src import GOOD_database
from src.analysis import evaluate_character
from src.artifact import Circlet, Flower, Goblet, Plume, Sands

# Import data from Genshin Optimizer
database = GOOD_database.GenshinOpenObjectDescriptionDatabase(
    file_path=os.path.join(dir_path, "data", "sample_GOOD_data.json")
)

# Evaluate Mona
evaluate_character(
    database=database,
    character_key="Mona",
    slots=[Flower, Plume, Sands, Goblet, Circlet],
    log_to_file=True,
    plot=True,
    max_artifacts_plotted=10,
)

a = 1

# # Evaluate Barbara
# evaluate_character(
#     genshin_optimizer_data=genshin_optimizer_data,
#     character_name="Barbara",
#     character_dmg_type="Healing",
#     character_scaling_stat="HP",
#     character_passive={},
#     character_stat_transfer={},
#     weapon_passive={},  # TTODS
#     amplifying_reaction=None,
#     reaction_percentage=0.0,
#     plot=True,
#     max_artifacts_plotted=10,
# )


# Evaluate Klee
# evaluate_character(
#     genshin_optimizer_data=genshin_optimizer_data,
#     character_name="Klee",
#     character_dmg_type="Pyro",
#     character_scaling_stat="ATK",
#     character_passive={},
#     character_stat_transfer={},
#     weapon_passive={"dmg_": 32.0, "atk_": 16.0},  # Dodoco Tales R5
#     amplifying_reaction="Pyro Vaporize",
#     reaction_percentage=50.0,
#     plot=True,
# )

# # Evaluate Eula
# evaluate_character(
#     genshin_optimizer_data=genshin_optimizer_data,
#     character_name="Eula",
#     character_dmg_type="Physical",
#     character_scaling_stat="ATK",
#     character_passive={},
#     character_stat_transfer={},
#     weapon_passive={"dmg_": 50.0},  # Serpent Spine R5
# )
