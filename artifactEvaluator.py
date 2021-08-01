import numpy as np
import pandas as pd

import substat as sub
import artifact as art
import artifacts as arts
import weapon as weap
import character as char
    
if __name__ == '__main__':

    flower_substat_1 = sub.Substat('DEF', 37)
    flower_substat_2 = sub.Substat('Crit DMG%', 7.8)
    flower_substat_3 = sub.Substat('Crit Rate%', 10.9)
    flower_substat_4 = sub.Substat('ATK', 33) 

    plume_substat_1 = sub.Substat('Crit DMG%', 19.4)
    plume_substat_2 = sub.Substat('Crit Rate%', 10.1)
    plume_substat_3 = sub.Substat('ATK%', 4.1)
    plume_substat_4 = sub.Substat('DEF%', 10.9)

    sands_substat_1 = sub.Substat('Energy Recharge%', 5.2)
    sands_substat_2 = sub.Substat('Crit DMG%', 28.0)
    sands_substat_3 = sub.Substat('Elemental Mastery', 68)
    sands_substat_4 = sub.Substat('HP%', 4.7)
    
    goblet_substat_1 = sub.Substat('ATK', 64)
    goblet_substat_2 = sub.Substat('Elemental Mastery', 42)
    goblet_substat_3 = sub.Substat('Crit DMG%', 6.2)
    goblet_substat_4 = sub.Substat('DEF%', 7.3)
    
    circlet_substat_1 = sub.Substat('HP', 269)
    circlet_substat_2 = sub.Substat('Crit DMG%', 28.8)
    circlet_substat_3 = sub.Substat('HP%', 5.3)
    circlet_substat_4 = sub.Substat('ATK', 29)

    flower =  art.Flower( set='witch',      main_stat='HP',              stars=5, level=20, substats=[flower_substat_1, flower_substat_2, flower_substat_3, flower_substat_4])
    plume =   art.Plume(  set='gladiators', main_stat='ATK',             stars=5, level=20, substats=[plume_substat_1, plume_substat_2, plume_substat_3, plume_substat_4])
    sands =   art.Sands(  set='noblesse',   main_stat='ATK%',            stars=5, level=20, substats=[sands_substat_1, sands_substat_2, sands_substat_3, sands_substat_4])
    goblet =  art.Goblet( set='gladiators', main_stat='Elemental DMG%',  stars=5, level=20, substats=[goblet_substat_1, goblet_substat_2, goblet_substat_3, goblet_substat_4])
    circlet = art.Circlet(set='witch',      main_stat='Crit Rate%',      stars=5, level=20, substats=[circlet_substat_1, circlet_substat_2, circlet_substat_3, circlet_substat_4])

    artifacts = arts.Artifacts(flower, plume, sands, goblet, circlet)

    weapon = weap.Weapon(
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
        weapon=weapon,
        artifacts=artifacts)

    print(klee.stats)
    print(klee.power)