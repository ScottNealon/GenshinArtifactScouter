import logging
import logging.config
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import artifact as art
import artifacts as arts
import character as char
import evaluate as eval
import go_parser as gop
import potential as pot
import weapon as weap

if __name__ == "__main__":

    # Setup Logging
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(dir_path, "logging.conf")
    logging.config.fileConfig(config_path)
    logging.info("Logging initialized.")

    # Import data from Genshin Optimizer
    go_data = gop.GenshinOptimizerData("go_data.json")

    # Import Klee from Genshin Optimizer
    klee = go_data.get_character(character_name="klee")
    klee.amplifying_reaction = "pyro_vaporize"
    klee.reaction_percentage = 0.5
    klee_artifacts = go_data.get_characters_artifacts(character_name="klee")

    # TODO Import weapon from GO and reattribute to characters
    dodoco_tales = weap.Weapon(
        name="Dodoco Tales",
        level=90,
        baseATK=454,
        ascension_stat="ATK%",
        ascension_stat_value=55.1,
        passive={"DMG%": 32.0, "ATK%": 16.0},
    )

    # Evaluate character current power
    base_power = eval.evaluate_power(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, verbose=True)

    # Evaluate the potential of every slot
    slots_substat_potentials = pot.all_slots_substats_potentials(
        character=klee, weapon=dodoco_tales, equipped_artifacts=klee_artifacts, base_power=base_power, verbose=True
    )

    # Evalute the potential of a single slot using properties in equipped_artifacts
    slot_substat_potentials = pot.slot_substat_potentials(
        character=klee,
        weapon=dodoco_tales,
        equipped_artifacts=klee_artifacts,
        slot=art.Sands,
        base_power=base_power,
        verbose=True,
    )

    # Evaluate the potential of a single slot using explicit properties
    slot_substat_potentials_explicit = pot.slot_substat_potentials(
        character=klee,
        weapon=dodoco_tales,
        equipped_artifacts=klee_artifacts,
        slot=art.Sands,
        set_str="gladiators",
        stars=5,
        main_stat="ATK%",
        base_power=base_power,
        verbose=True,
    )

    # Collect all gladiators ATK% sands from Genshin Optimizer
    sands = go_data.get_artifacts(sets="gladiators", slot=[art.Sands], main_stat="ATK%")

    # Evaluate the potential of all gladiators ATK% sands I own
    artifacts_substat_potentials = pot.artifacts_substat_potentials(
        character=klee,
        weapon=dodoco_tales,
        equipped_artifacts=klee_artifacts,
        evaluating_artifacts=sands,
        slot_substat_potentials=slot_substat_potentials,
        verbose=True,
    )

    # Evaluate the potential of a single gladiators ATK% sands I own
    sands_singular = sands[list(sands.keys())[0]]
    artifact_substat_potentials = pot.artifact_substat_potential(
        character=klee,
        weapon=dodoco_tales,
        equipped_artifacts=klee_artifacts,
        evaluating_artifact=sands_singular,
        slot_substat_potentials=slot_substat_potentials,
        verbose=True,
    )

    # Compare potentials
    # artifact_potentials = [flower_potentials_df, plume_potentials_df, sands_potentials_df, goblet_potentials_df, circlet_potentials_df]
    # legend_labels = ['Flower', 'Plume', 'Sands', 'Goblet', 'Circlet']
    # pot.graph_potentials(artifact_potentials, base_power=base_power, title='Potential of Artifacts on Klee', legend_labels=legend_labels, smooth=True)

    plt.show()
