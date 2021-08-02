import matplotlib.pyplot as plt
import numpy as np
from numpy.core.numeric import roll
import pandas as pd

import artifact as art
import artifacts as arts
import weapon as weap
import character as char
import potential as pot
import evaluate as eval
    
if __name__ == '__main__':

    flower_substats = {
        'DEF': 37,
        'Crit DMG%': 7.8,
        'Crit Rate%': 10.9,
        'ATK': 33
    }

    plume_substats_potential = {
        'ATK%': 4.1,
        'DEF%': 7.3,
        'HP%': 5.3
    }

    plume_substats = {
        'Crit DMG%': 19.4,
        'Crit Rate%': 10.1,
        'ATK%': 4.1,
        'DEF%': 10.9
    }

    sands_substats = {
        'Energy Recharge%': 5.2,
        'Crit DMG%': 28.0,
        'Elemental Mastery': 68,
        'HP%': 4.7
    }

    goblet_substats = {
        'ATK': 64,
        'Elemental Mastery': 42,
        'Crit DMG%': 6.2,
        'DEF%': 7.3
    }

    circlet_substats = {
        'HP': 269,
        'Crit DMG%': 28.8,
        'HP%': 5.3,
        'ATK': 29
    }

    flower =  art.Flower( set='witch',      main_stat='HP',              stars=5, level=20, substats=flower_substats)
    # plume =   art.Plume(  set='gladiators', main_stat='ATK',             stars=5, level= 20, substats=plume_substats)
    plume =   art.Plume(  set='gladiators', main_stat='ATK',             stars=5, level= 0, substats=plume_substats_potential)
    sands =   art.Sands(  set='noblesse',   main_stat='ATK%',            stars=5, level=20, substats=sands_substats)
    goblet =  art.Goblet( set='gladiators', main_stat='Elemental DMG%',  stars=5, level=20, substats=goblet_substats)
    circlet = art.Circlet(set='witch',      main_stat='Crit Rate%',      stars=5, level=20, substats=circlet_substats)

    artifacts = arts.Artifacts(flower, plume, sands, goblet, circlet)

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

    klee = char.Character(
        name='Klee',
        level=80,
        baseHP=9563,
        baseATK=289,
        baseDEF=572,
        ascension_stat='Elemental DMG%',
        ascension_stat_value=28.8,
        passive={},
        dmg_type='Elemental',
        amplifying_reaction='Reverse Vaporize',
        reaction_percentage=0.5,
        #weapon=weapon,
        #artifacts=artifacts
        )

    print(klee.base_stats)
    base_power = eval.evaluate_power(character=klee, weapon=dodoco_tales, artifacts=artifacts)
    print(base_power)

    roll_combinations = pot.artifact_potential(character=klee, weapon=dodoco_tales, artifacts=artifacts, artifact=plume, target_level=20)

    power = [ind['power'] for ind in roll_combinations]

    plt.hist(power, bins=50)
    plt.show()