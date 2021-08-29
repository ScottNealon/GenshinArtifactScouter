import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler(filename="output.log", mode="w", encoding="utf8"),
        logging.StreamHandler(),
    ],
)

from src import *

# Import data from Genshin Optimizer
genshin_optimizer_data = go_parser.GenshinOptimizerData(file_path="Data/sample_go_data.json")

# Evaluate Mona
evaluate_character(
    genshin_optimizer_data=genshin_optimizer_data,
    character_name="Mona",
    character_dmg_type="Hydro",
    character_scaling_stat="ATK",
    character_passive={},
    character_stat_transfer={"Hydro DMG%": {"Energy Recharge%": 20.0}},
    weapon_passive={},  # TTODS
    amplifying_reaction=None,
    reaction_percentage=0.0,
    # slots=[Sands],
    plot=True,
    max_artifacts_plotted=10,
)

a = 1

# Evaluate Klee
# potential.evaluate_character(
#     genshin_optimizer_data=genshin_optimizer_data,
#     character_name="Klee",
#     character_dmg_type="Pyro",
#     character_scaling_stat="ATK",
#     character_passive={},
#     character_stat_transfer={},
#     weapon_passive={"DMG%": 32.0, "ATK%": 16.0}, # Dodoco Tales R5
#     amplifying_reaction="Pyro Vaporize",
#     reaction_percentage=50.0,
#     plot=True,
#     smooth_plot=True,
# )

# # Evaluate Eula
# potential.evaluate_character(
#     genshin_optimizer_data=genshin_optimizer_data,
#     character_name="Eula",
#     character_dmg_type="Physical",
#     character_scaling_stat="ATK",
#     character_passive={},
#     character_stat_transfer={},
#     weapon_passive={"DMG%": 50.0},  # Serpent Spine R5
#     amplifying_reaction=None,
#     reaction_percentage=0.0,
#     plot=True,
#     smooth_plot=True,
# )
