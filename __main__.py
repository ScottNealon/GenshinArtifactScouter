"""Main

This is a sample script showcasing the module's functionality. All
commands run in this script are duplicated in the different scripts, #TODO Actually do this
which can be run individual to gain a greater understanding of how the
commands function."""

import copy
import logging
import logging.config
import os

import matplotlib.pyplot as plt

# Setup Logging
dir_path = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join(dir_path, "logging.conf")
logging.config.fileConfig(config_path)
logging.info("Logging initialized.")

import evaluate
import go_parser as gop
import potential as pot
from artifact import Circlet, Flower, Goblet, Plume, Sands
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
    slot_potentials = pot.all_slots_potentials(character=klee, equipped_artifacts=klee_artifacts, verbose=True)

    # Evalute the potential of a single slot using properties in equipped_artifacts
    sands_potential = pot.slot_potential(
        character=klee,
        equipped_artifacts=klee_artifacts,
        slot=Sands,
        verbose=True,
    )

    ### EVALUATE ARTIFACT POTENTIALS ###
    logging.info("")
    logging.info("-" * 120)
    logging.info("EVALUATE ARTIFACT POTENTIALS")

    # Collect all noblesse ATK% sands from Genshin Optimizer
    sands = go_data.get_artifacts(sets="noblesse", slot=[Sands], main_stat="ATK%")

    # Evaluate the potential of all noblesse ATK% sands I own
    artifacts_potentials = pot.artifacts_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifacts=sands,
        slot_potentials=slot_potentials,
        verbose=True,
    )

    # Evaluate the potential of the first noblesse ATK% sands I own
    sands_singular = sands[list(sands.keys())[0]]
    artifact_potentials = pot.artifact_potential(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifact=sands_singular,
        slot_potentials=slot_potentials,
        verbose=True,
    )

    ### CALCULATING POTENTIAL WITH OFF-SETS ARTIFACTS
    logging.info("")
    logging.info("-" * 120)
    logging.info("CALCULATING POTENTIAL WITH OFF-SETS ARTIFACTS")

    # Collect all gladiator ATK% sands from Genshin Optimizer
    gladiators_sands = go_data.get_artifacts(sets="gladiators", slot=[Sands], main_stat="ATK%")

    # Evaluate the potential of all gladiator ATK% sands I own
    #   This should raise a warning due to using different slot potentials and due to different set from equippped
    #   artifacts.
    artifact_potentials = pot.artifacts_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifacts=gladiators_sands,
        slot_potentials=slot_potentials,
        verbose=True,
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
        verbose=True,
    )

    # Evaluate the potential of all gladiator ATK% sands I own without throwing a warning
    artifact_potentials = pot.artifacts_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts_no_set,
        evaluating_artifacts=gladiators_sands,
        slot_potentials=sands_potential_no_set,
        verbose=True,
    )

    # Compare potentials
    # artifact_potentials = [flower_potentials_df, plume_potentials_df, sands_potentials_df, goblet_potentials_df, circlet_potentials_df]
    # legend_labels = ['Flower', 'Plume', 'Sands', 'Goblet', 'Circlet']
    # pot.graph_potentials(artifact_potentials, base_power=base_power, title='Potential of Artifacts on Klee', legend_labels=legend_labels, smooth=True)

    plt.show()
