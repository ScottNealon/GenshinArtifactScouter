"""Main

This is a sample script showcasing the module's functionality. All
commands run in this script are duplicated in the different scripts, #TODO Actually do this
which can be run individual to gain a greater understanding of how the
commands function."""

import logging
import logging.config
import os

# Setup Logging
config_path = os.path.join(os.path.abspath(""), "config/logging.conf")
logging.config.fileConfig(config_path)
logging.info("Logging initialized.")

from src import *

if __name__ == "__main__":

    # Import data from Genshin Optimizer
    genshin_optimizer_data = go_parser.GenshinOptimizerData("Data/sample_go_data.json")

    # Evaluate Mona
    potential.evaluate_character(
        genshin_optimizer_data=genshin_optimizer_data,
        character_name="Mona",
        character_dmg_type="Hydro",
        character_scaling_stat="ATK",
        character_passive={},
        character_stat_transfer={"Hydro DMG%": {"Energy Recharge%": 20.0}},
        weapon_passive={},
        amplifying_reaction=None,
        reaction_percentage=0.0,
        verbose=True,
        plot=True,
        smooth_plot=True,
    )

    # # Import Mona from Genshin Optimizer
    # mona = go_data.get_character(character_name="Mona")
    # mona.stat_transfer = {"Elemental DMG%": {"Energy Recharge%": 20.0}}
    # mona_artifacts = Artifacts(
    #     [
    #         Flower(stars=5, level=20, set_str="emblem", main_stat="HP"),
    #         Plume(stars=5, level=20, set_str="emblem", main_stat="ATK"),
    #         Sands(stars=5, level=20, set_str="emblem", main_stat="ATK%"),
    #         Goblet(stars=5, level=20, set_str="emblem", main_stat="Elemental DMG%"),
    #         Circlet(stars=5, level=20, set_str="emblem", main_stat="ATK%"),
    #     ]
    # )

    # # Evaluate Mona's power
    # base_power = power_calculator.evaluate_power(character=mona, artifacts=mona_artifacts, verbose=True)

    # # Evaluate slot potentials
    # slot_potentials = potential.all_slots_potentials(character=mona, equipped_artifacts=mona_artifacts, plot=True)

    # flower = go_data.get_artifacts(names=["artifact_614"])
    # artifacts_potentials = potential.artifacts_potentials(
    #     character=mona,
    #     equipped_artifacts=mona_artifacts,
    #     evaluating_artifacts=flower,
    #     slot_potentials=slot_potentials,
    #     plot=True,
    # )

    # # Get Emblem Artifacts
    # # flowers = go_data.get_artifacts(sets="emblem", slots=Flower)
    # # plumes = go_data.get_artifacts(sets="emblem", slots=Plume)
    # # sands = go_data.get_artifacts(sets="emblem", slots=Sands, main_stat=["ATK%", "Energy Recharge %"])
    # # goblets = go_data.get_artifacts(sets="emblem", slots=Goblet, main_stat=["ATK%", "Elemental DMG%"])
    # # circlets = go_data.get_artifacts(sets="emblem", slots=Circlet, main_stat=["ATK%", "Crit Rate%", "Crit DMG%"])

    # # # Evaluate the potential of matching artifacts I own
    # # artifacts_potentials = potential.artifacts_potentials(
    # #     character=mona,
    # #     equipped_artifacts=mona_artifacts,
    # #     evaluating_artifacts=flowers,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )
    # # artifacts_potentials = potential.artifacts_potentials(
    # #     character=mona,
    # #     equipped_artifacts=mona_artifacts,
    # #     evaluating_artifacts=plumes,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )
    # # artifacts_potentials = potential.artifacts_potentials(
    # #     character=mona,
    # #     equipped_artifacts=mona_artifacts,
    # #     evaluating_artifacts=sands,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )
    # # artifacts_potentials = potential.artifacts_potentials(
    # #     character=mona,
    # #     equipped_artifacts=mona_artifacts,
    # #     evaluating_artifacts=goblets,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )
    # # artifacts_potentials = potential.artifacts_potentials(
    # #     character=mona,
    # #     equipped_artifacts=mona_artifacts,
    # #     evaluating_artifacts=circlets,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )

    # # # Import Klee from Genshin Optimizer
    # # klee = go_data.get_character(character_name="klee")
    # # klee_artifacts = go_data.get_characters_artifacts(character_name="klee")
    # # klee.passive = {}
    # # klee.weapon.passive = {"DMG%": 32.0, "ATK%": 16.0}
    # # klee.amplifying_reaction = "Pyro Vaporize"
    # # klee.reaction_percentage = 50.0

    # # # Evaluate Klee's power
    # # base_power = power_calculator.evaluate_power(character=klee, artifacts=klee_artifacts, verbose=True)

    # # ### EVALUATE SLOT POTENTIALS ###
    # # logging.info("")
    # # logging.info("-" * 110)
    # # logging.info("EVALUATE SLOT POTENTIALS")

    # # # Evaluate the potential of every slot
    # # slot_potentials = potential.all_slots_potentials(character=klee, equipped_artifacts=klee_artifacts, plot=True)

    # # # Evalute the potential of a single slot using properties in equipped_artifacts
    # # sands_potential = potential.slot_potential(character=klee, equipped_artifacts=klee_artifacts, slot=Sands, plot=True)

    # # ### EVALUATE ARTIFACT POTENTIALS ###
    # # logging.info("")
    # # logging.info("-" * 110)
    # # logging.info("EVALUATE ARTIFACT POTENTIALS")

    # # # Collect all matching slot/main stat artifacts from Genshin Optimizer
    # # flowers = go_data.get_artifacts_like(klee_artifacts.get_artifact(Flower))
    # # plumes = go_data.get_artifacts_like(klee_artifacts.get_artifact(Plume))
    # # sands = go_data.get_artifacts_like(klee_artifacts.get_artifact(Sands))
    # # goblets = go_data.get_artifacts_like(klee_artifacts.get_artifact(Goblet))
    # # circlets = go_data.get_artifacts_like(klee_artifacts.get_artifact(Circlet))

    # # # Evaluate the potential of matching artifacts I own
    # # artifacts_potentials = potential.artifacts_potentials(
    # #     character=klee,
    # #     equipped_artifacts=klee_artifacts,
    # #     evaluating_artifacts=flowers,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )
    # # artifacts_potentials = potential.artifacts_potentials(
    # #     character=klee,
    # #     equipped_artifacts=klee_artifacts,
    # #     evaluating_artifacts=plumes,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )
    # # artifacts_potentials = potential.artifacts_potentials(
    # #     character=klee,
    # #     equipped_artifacts=klee_artifacts,
    # #     evaluating_artifacts=sands,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )
    # # artifacts_potentials = potential.artifacts_potentials(
    # #     character=klee,
    # #     equipped_artifacts=klee_artifacts,
    # #     evaluating_artifacts=goblets,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )
    # # artifacts_potentials = potential.artifacts_potentials(
    # #     character=klee,
    # #     equipped_artifacts=klee_artifacts,
    # #     evaluating_artifacts=circlets,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )

    # # # Evaluate the potential of the first noblesse ATK% sands I own
    # # artifact_name = list(sands.keys())[0]
    # # sands_singular = sands[artifact_name]
    # # artifact_potentials = potential.artifact_potential(
    # #     character=klee,
    # #     equipped_artifacts=klee_artifacts,
    # #     evaluating_artifact=sands_singular,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # #     artifact_name=artifact_name,
    # # )

    # # ### CALCULATING POTENTIAL WITH OFF-SETS ARTIFACTS
    # # logging.info("")
    # # logging.info("-" * 110)
    # # logging.info("CALCULATING POTENTIAL WITH OFF-SETS ARTIFACTS")

    # # # Collect all gladiator ATK% sands from Genshin Optimizer
    # # gladiators_sands = go_data.get_artifacts(sets="gladiators", slot=[Sands], main_stat="ATK%")

    # # # Evaluate the potential of all gladiator ATK% sands I own
    # # #   This should raise a warning due to using different slot potentials and due to different set from equippped
    # # #   artifacts. It should also fail to plot.
    # # artifact_potentials = potential.artifacts_potentials(
    # #     character=klee,
    # #     equipped_artifacts=klee_artifacts,
    # #     evaluating_artifacts=gladiators_sands,
    # #     slot_potentials=slot_potentials,
    # #     plot=True,
    # # )

    # # ### CALCULATING POTENTIAL WITH USE_SET_BONUS = FALSE
    # # logging.info("")
    # # logging.info("-" * 110)
    # # logging.info("CALCULATING POTENTIAL WITH USE_SET_BONUS = FALSE")

    # # # Create a copy of klee artifacts to evaluate without sets
    # # klee_artifacts_no_set = copy.deepcopy(klee_artifacts)
    # # klee_artifacts_no_set.use_set_bonus = False

    # # # Evaluate the potential of a single slot using explicit properties
    # # sands_potential_no_set = potential.slot_potential(
    # #     character=klee,
    # #     equipped_artifacts=klee_artifacts_no_set,
    # #     slot=Sands,
    # #     set_str="gladiators",
    # #     stars=5,
    # #     main_stat="ATK%",
    # #     plot=True,
    # # )

    # # # Evaluate the potential of all gladiator ATK% sands I own without throwing a warning
    # # artifact_potentials = potential.artifacts_potentials(
    # #     character=klee,
    # #     equipped_artifacts=klee_artifacts_no_set,
    # #     evaluating_artifacts=gladiators_sands,
    # #     slot_potentials=sands_potential_no_set,
    # #     plot=True,
    # # )

    # # ### CALCULATING POTENTIAL WITH NO ARTIFACTS EQUIPPED
    # # logging.info("")
    # # logging.info("-" * 110)
    # # logging.info("CALCULATING POTENTIAL WITH NO ARTIFACTS EQUIPPED")

    # # # Get new Klee and have no reactions
    # # klee_no_reaction = copy.deepcopy(klee)
    # # klee_no_reaction.amplifying_reaction = None
    # # klee_no_reaction.reaction_percentage = 0

    # # # Create artifacts with no artifacts
    # # no_artifacts = Artifacts.generate_empty_artifacts(
    # #     stars=5, level=20, main_stats=["HP", "ATK", "ATK%", "Elemental DMG%", "Crit Rate%"]
    # # )

    # # # Calculate slot potential
    # # slot_potentials_no_artifacts = potential.all_slots_potentials(
    # #     character=klee_no_reaction, equipped_artifacts=no_artifacts, plot=True
    # # )

    # # # Calculate artifact potential
    # # sands_singular = Sands(
    # #     main_stat="ATK%",
    # #     stars=5,
    # #     level=0,
    # #     set_str="",
    # #     substats={},
    # # )
    # # artifact_potentials = potential.artifact_potential(
    # #     character=klee_no_reaction,
    # #     equipped_artifacts=no_artifacts,
    # #     evaluating_artifact=sands_singular,
    # #     slot_potentials=slot_potentials_no_artifacts,
    # #     plot=True,
    # # )

    # plt.show()
