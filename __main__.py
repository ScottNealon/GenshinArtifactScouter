"""Main

This is a sample script showcasing the module's functionality. All
commands run in this script are duplicated in the different scripts, #TODO Actually do this
which can be run individual to gain a greater understanding of how the
commands function."""

import copy
import logging
import logging.config
import os

# Setup Logging
dir_path = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join(dir_path, "logging.conf")
logging.config.fileConfig(config_path)
logging.info("Logging initialized.")

import matplotlib.pyplot as plt

import evaluate
import go_parser as gop
import potential as pot
from artifact import Circlet, Flower, Goblet, Plume, Sands
from artifacts import Artifacts, generate_empty_artifacts
from character import Character

if __name__ == "__main__":

    ### IMPORT CHARACTER FROM GENSHIN OPTIMIZER AND PROVIDE EXTRA DATA ###
    logging.info("")
    logging.info("-" * 120)
    logging.info("IMPORT CHARACTER FROM GENSHIN OPTIMIZER AND PROVIDE EXTRA DATA")

    # Import data from Genshin Optimizer
    go_data = gop.GenshinOptimizerData("Data/go_data.json")

    # Import Klee from Genshin Optimizer
    klee = go_data.get_character(character_name="klee")
    klee_artifacts = go_data.get_characters_artifacts(character_name="klee")
    klee.passive = {}
    klee.weapon.passive = {"DMG%": 32.0, "ATK%": 16.0}
    klee.amplifying_reaction = "Pyro Vaporize"
    klee.reaction_percentage = 0.5

    # Evaluate Klee's power
    base_power = evaluate.evaluate_power(character=klee, artifacts=klee_artifacts, verbose=True)

    ### EVALUATE SLOT POTENTIALS ###
    logging.info("")
    logging.info("-" * 120)
    logging.info("EVALUATE SLOT POTENTIALS")

    # Evaluate the potential of every slot
    slot_potentials = pot.all_slots_potentials(character=klee, equipped_artifacts=klee_artifacts, plot=True)

    # Evalute the potential of a single slot using properties in equipped_artifacts
    sands_potential = pot.slot_potential(character=klee, equipped_artifacts=klee_artifacts, slot=Sands, plot=True)

    ### EVALUATE ARTIFACT POTENTIALS ###
    logging.info("")
    logging.info("-" * 120)
    logging.info("EVALUATE ARTIFACT POTENTIALS")

    # Collect all matching slot/main stat artifacts from Genshin Optimizer
    flowers = go_data.get_artifacts_like(klee_artifacts.get_artifact(Flower))
    plumes = go_data.get_artifacts_like(klee_artifacts.get_artifact(Plume))
    sands = go_data.get_artifacts_like(klee_artifacts.get_artifact(Sands))
    goblets = go_data.get_artifacts_like(klee_artifacts.get_artifact(Goblet))
    circlets = go_data.get_artifacts_like(klee_artifacts.get_artifact(Circlet))

    # Evaluate the potential of matching artifacts I own
    artifacts_potentials = pot.artifacts_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifacts=flowers,
        slot_potentials=slot_potentials,
        plot=True,
    )
    artifacts_potentials = pot.artifacts_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifacts=plumes,
        slot_potentials=slot_potentials,
        plot=True,
    )
    artifacts_potentials = pot.artifacts_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifacts=sands,
        slot_potentials=slot_potentials,
        plot=True,
    )
    artifacts_potentials = pot.artifacts_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifacts=goblets,
        slot_potentials=slot_potentials,
        plot=True,
    )
    artifacts_potentials = pot.artifacts_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifacts=circlets,
        slot_potentials=slot_potentials,
        plot=True,
    )

    # Evaluate the potential of the first noblesse ATK% sands I own
    artifact_name = list(sands.keys())[0]
    sands_singular = sands[artifact_name]
    artifact_potentials = pot.artifact_potential(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifact=sands_singular,
        slot_potentials=slot_potentials,
        plot=True,
        artifact_name=artifact_name,
    )

    ### CALCULATING POTENTIAL WITH OFF-SETS ARTIFACTS
    logging.info("")
    logging.info("-" * 120)
    logging.info("CALCULATING POTENTIAL WITH OFF-SETS ARTIFACTS")

    # Collect all gladiator ATK% sands from Genshin Optimizer
    gladiators_sands = go_data.get_artifacts(sets="gladiators", slot=[Sands], main_stat="ATK%")

    # Evaluate the potential of all gladiator ATK% sands I own
    #   This should raise a warning due to using different slot potentials and due to different set from equippped
    #   artifacts. It should also fail to plot.
    artifact_potentials = pot.artifacts_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifacts=gladiators_sands,
        slot_potentials=slot_potentials,
        plot=True,
    )

    ### CALCULATING POTENTIAL WITH USE_SET_BONUS = FALSE
    logging.info("")
    logging.info("-" * 120)
    logging.info("CALCULATING POTENTIAL WITH USE_SET_BONUS = FALSE")

    # Create a copy of klee artifacts to evaluate without sets
    klee_artifacts_no_set = copy.deepcopy(klee_artifacts)
    klee_artifacts_no_set.use_set_bonus = False

    # Evaluate the potential of a single slot using explicit properties
    sands_potential_no_set = pot.slot_potential(
        character=klee,
        equipped_artifacts=klee_artifacts_no_set,
        slot=Sands,
        set_str="gladiators",
        stars=5,
        main_stat="ATK%",
        plot=True,
    )

    # Evaluate the potential of all gladiator ATK% sands I own without throwing a warning
    artifact_potentials = pot.artifacts_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts_no_set,
        evaluating_artifacts=gladiators_sands,
        slot_potentials=sands_potential_no_set,
        plot=True,
    )

    ### CALCULATING POTENTIAL WITH NO ARTIFACTS EQUIPPED
    logging.info("")
    logging.info("-" * 120)
    logging.info("CALCULATING POTENTIAL WITH NO ARTIFACTS EQUIPPED")

    # Get new Klee and have no reactions
    klee_no_reaction = copy.deepcopy(klee)
    klee_no_reaction.amplifying_reaction = None
    klee_no_reaction.reaction_percentage = 0

    # Create artifacts with no artifacts
    no_artifacts = generate_empty_artifacts(
        stars=5, level=20, main_stats=["HP", "ATK", "ATK%", "Elemental DMG%", "Crit Rate%"]
    )

    # Calculate slot potential
    slot_potentials_no_artifacts = pot.all_slots_potentials(
        character=klee_no_reaction, equipped_artifacts=no_artifacts, plot=True
    )

    # Calculate artifact potential
    sands_singular = Sands(
        main_stat="ATK%",
        stars=5,
        level=0,
        set_str="",
        substats={},
    )
    artifact_potentials = pot.artifact_potential(
        character=klee_no_reaction,
        equipped_artifacts=no_artifacts,
        evaluating_artifact=sands_singular,
        slot_potentials=slot_potentials_no_artifacts,
        plot=True,
    )

    plt.show()
