"""Main

This is a sample script showcasing the module's functionality. All
commands run in this script are duplicated in the different scripts, #TODO Actually do this
which can be run individual to gain a greater understanding of how the
commands function."""

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

    # Evaluate the potential of every slot
    slots_substat_potentials = pot.all_slots_substats_potentials(
        character=klee, equipped_artifacts=klee_artifacts, base_power=base_power, verbose=True
    )

    # Evalute the potential of a single slot using properties in equipped_artifacts
    slot_substat_potentials = pot.slot_substat_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        slot=Sands,
        base_power=base_power,
        verbose=True,
    )

    # Evaluate the potential of a single slot using explicit properties
    slot_substat_potentials_explicit = pot.slot_substat_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        slot=Sands,
        set_str="gladiators",
        stars=5,
        main_stat="ATK%",
        base_power=base_power,
        verbose=True,
    )

    # Collect all noblesse ATK% sands from Genshin Optimizer
    sands = go_data.get_artifacts(sets="noblesse", slot=[Sands], main_stat="ATK%")

    # Evaluate the potential of all noblesse ATK% sands I own
    artifacts_substat_potentials = pot.artifacts_substat_potentials(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifacts=sands,
        slot_substat_potentials=slot_substat_potentials,
        verbose=True,
    )

    # Evaluate the potential of a single noblesse ATK% sands I own
    sands_singular = sands[list(sands.keys())[0]]
    artifact_substat_potentials = pot.artifact_substat_potential(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifact=sands_singular,
        slot_substat_potentials=slot_substat_potentials,
        verbose=True,
    )

    # Collect all gladiators ATK% sands from Genshin Optimizer and evaluate potential of one.
    # This should raise a warning due to using a different slot potentials
    gladiators_sands = go_data.get_artifacts(sets="gladiators", slot=[Sands], main_stat="ATK%")
    gladiators_sand_singular = gladiators_sands[list(gladiators_sands.keys())[0]]
    artifact_substat_potentials = pot.artifact_substat_potential(
        character=klee,
        equipped_artifacts=klee_artifacts,
        evaluating_artifact=gladiators_sand_singular,
        slot_substat_potentials=slot_substat_potentials,
        verbose=True,
    )

    # Compare potentials
    # artifact_potentials = [flower_potentials_df, plume_potentials_df, sands_potentials_df, goblet_potentials_df, circlet_potentials_df]
    # legend_labels = ['Flower', 'Plume', 'Sands', 'Goblet', 'Circlet']
    # pot.graph_potentials(artifact_potentials, base_power=base_power, title='Potential of Artifacts on Klee', legend_labels=legend_labels, smooth=True)

    plt.show()
