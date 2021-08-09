import logging
import logging.config
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import artifact as art
import artifacts as arts
import weapon as weap
import character as char
import potential as pot
import evaluate as eval
import go_parser as gop
    
if __name__ == '__main__':

    # Setup Logging
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(dir_path, 'logging.conf')
    logging.config.fileConfig(config_path)
    logging.info('Logging initialized.')

    # Import data from Genshin Optimizer
    go_data = gop.GenshinOptimizerData('go_data.json')

    # Import Klee from Genshin Optimizer
    klee = go_data.get_character(character_name='klee')
    klee.amplifying_reaction = 'pyro_vaporize'
    klee.reaction_percentage = 0.5
    klee_artifacts = go_data.get_characters_artifacts(character_name='klee')

    # TODO Import weapon from GO and reattribute to characters
    dodoco_tales = weap.Weapon(
        name='Dodoco Tales',
        level=90,
        baseATK=454,
        ascension_stat='ATK%',
        ascension_stat_value=55.1,
        passive= {
            'DMG%': 32.0,
            'ATK%': 16.0
        }
    )

    # Evaluate character current power
    base_power = eval.evaluate_power(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, verbose=True)

    # Evaluate the potential of an entire slot
    # flower_potentials_df   = pot.slot_potential(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, artifact_like=klee_artifacts.flower,  source='domain', verbose=True)
    # plume_potentials_df    = pot.slot_potential(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, artifact_like=klee_artifacts.plume,   source='domain', verbose=True)
    # sands_potentials_df    = pot.slot_potential(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, artifact_like=klee_artifacts.sands,   source='domain', verbose=True)
    goblet_potentials_df   = pot.slot_potential(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, artifact_like=klee_artifacts.goblet,  source='domain', verbose=True)
    circlet_potentials_df  = pot.slot_potential(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, artifact_like=klee_artifacts.circlet, source='domain', verbose=True)

    # Evaluate potential of every nonleveled flower of same set
    #flower = go_data.get_artifacts(sets=[klee_artifacts.flower.set], slot=[art.Flower], max_level=19)
    # flower_potentials_df = pot.multiple_artifact_potential(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, artifact_list=flower.values(), target_level=20, verbose=True, slot_potential_df=flower_potentials_df, base_power=base_power)

    # Evaluate potential of every nonleveled plume of same set
    #plumes = go_data.get_artifacts(sets=[klee_artifacts.plume.set], slot=[art.Plume],  max_level=19)
    #plumes_potentials_df = pot.multiple_artifact_potential(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, artifact_list=plumes.values(), target_level=20, verbose=True, slot_potential_df=plume_potentials_df, base_power=base_power)
    
    # Evaluate potential of every nonleveled sands of same set
    # sands = go_data.get_artifacts(sets=[klee_artifacts.sands.set], slot=[art.Sands], main_stat=['ATK%'], max_level=19)
    # sands_potentials_df = pot.multiple_artifact_potential(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, artifact_list=sands.values(), target_level=20, verbose=True, slot_potential_df=sands_potentials_df, base_power=base_power)
    
    # Evaluate potential of every nonleveled goblet of same set
    goblets = go_data.get_artifacts(sets=[klee_artifacts.goblet.set], slot=[art.Goblet], main_stat=['ATK%', 'Elemental DMG%'], max_level=19)
    goblets_potentials_df = pot.multiple_artifact_potential(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, artifact_list=goblets.values(), target_level=20, verbose=True, slot_potential_df=goblet_potentials_df, base_power=base_power)
    
    # Evaluate potential of every nonleveled circlet of same set
    circlets = go_data.get_artifacts(sets=[klee_artifacts.circlet.set], slot=[art.Circlet], main_stat=['ATK%', 'Crit Rate%', 'Crit DMG%'], max_level=19)
    circlets_potentials_df = pot.multiple_artifact_potential(character=klee, weapon=dodoco_tales, artifacts=klee_artifacts, artifact_list=circlets.values(), target_level=20, verbose=True, slot_potential_df=circlet_potentials_df, base_power=base_power)

    # Compare potentials
    # artifact_potentials = [flower_potentials_df, plume_potentials_df, sands_potentials_df, goblet_potentials_df, circlet_potentials_df]
    # legend_labels = ['Flower', 'Plume', 'Sands', 'Goblet', 'Circlet']
    # pot.graph_potentials(artifact_potentials, base_power=base_power, title='Potential of Artifacts on Klee', legend_labels=legend_labels, smooth=True)

    plt.show()