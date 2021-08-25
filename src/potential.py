from __future__ import annotations

import copy
import decimal
import itertools
import logging
import math
import re

import numpy as np
import pandas as pd
from pandas.core.frame import DataFrame

from . import genshin_data, graphing, power_calculator
from .artifact import Artifact, Circlet, Flower, Goblet, Plume, Sands
from .artifacts import Artifacts
from .character import Character
from .go_parser import GenshinOptimizerData

log = logging.getLogger(__name__)


def evaluate_character(
    genshin_optimizer_data: GenshinOptimizerData,
    character_name: str,
    character_dmg_type: str,
    character_scaling_stat: str = "ATK",
    character_passive: dict[str, float] = {},
    character_stat_transfer: dict[str, dict[str, float]] = {},
    weapon_passive: dict[str, float] = {},
    amplifying_reaction: str = None,
    reaction_percentage: float = None,
    verbose: bool = True,
    plot: bool = True,
    smooth_plot: bool = True,
):

    # Log
    log.info("-" * 110)
    log.info(f"EVALUATING ARTIFACT POTENTIALS")
    log.info("")

    # Retrieve character from GO database
    character = genshin_optimizer_data.get_character(character_name=character_name)
    # Set character and weapon characteristics
    character.dmg_type = character_dmg_type
    character.scaling_stat = character_scaling_stat
    character.passive = character_passive
    character.stat_transfer = character_stat_transfer
    character.weapon.passive = weapon_passive
    character.amplifying_reaction = amplifying_reaction
    character.reaction_percentage = reaction_percentage

    # Retrieve equipped and potential artifacts from GO database
    equipped_artifacts = genshin_optimizer_data.get_characters_artifacts(character_name=character_name)
    alternative_artifacts = genshin_optimizer_data.get_alternative_artifacts(equipped_artifacts=equipped_artifacts)

    # Calculate current power
    current_power = power_calculator.evaluate_power(character=character, artifacts=equipped_artifacts)

    # Log character settings
    # fmt: off
    log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
    log.info(f"WEAPON: {character.weapon.name_formated.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
    if character.amplifying_reaction is not None:
        log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)")
    log.info(f"EQUIPPED ARTIFACTS:                                 MAIN STAT   HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%")
    for artifact in equipped_artifacts:
        log.info(artifact.to_string_table())
    log.info(f"CURRENT POWER: {current_power:,.0f}")
    log.info("")
    # fmt: on

    # TODO LOG CHARACTER STATS

    # Log number of artifacts
    log.info("Number of alternative artifacts:")
    for slot, artifacts in alternative_artifacts.items():
        log.info(f"{slot.__name__}: {len(artifacts)}")
    log.info("")

    # Iterate through slots
    slot_potentials: dict[type, pd.DataFrame] = {}
    artifact_potentials: dict[type, dict[Artifact, pd.DataFrame]] = {
        Flower: {},
        Plume: {},
        Sands: {},
        Goblet: {},
        Circlet: {},
    }
    artifact_scores: dict[type, dict[Artifact, float]] = {
        Flower: {},
        Plume: {},
        Sands: {},
        Goblet: {},
        Circlet: {},
    }
    for slot in [Flower, Plume, Sands, Goblet, Circlet]:

        log.info("-" * 25)
        log.info(f"EVALUATING {slot.__name__.upper()} SLOT POTENTIAL...")

        # Get equipped artifact
        equipped_artifact = equipped_artifacts.get_artifact(slot=slot)
        if equipped_artifact is None:
            log.info(f"No {slot.__name__} equipped on {character_name}.")
            log.info("")
            continue
        log.info(f"    Stars: {equipped_artifact.stars:>d}*")
        set_str_long = re.sub(r"(\w)([A-Z])", r"\1 \2", equipped_artifact.set)  # Add spaces between capitals
        log.info(f"      Set: {set_str_long}")
        log.info(f"Main Stat: {equipped_artifact.main_stat}")

        # Evaluate slot potential
        if equipped_artifact.set in genshin_data.dropped_from_world_boss:
            source = "world boss"
        else:
            source = "domain"
        slot_potential_df = _individual_potential(
            character=character,
            equipped_artifacts=equipped_artifacts,
            slot=slot,
            set_str=equipped_artifact.set,
            stars=equipped_artifact.stars,
            main_stat=equipped_artifact.main_stat,
            target_level=equipped_artifact.max_level,
            source=source,
        )
        slot_potentials[slot] = slot_potential_df

        log_slot_power(slot_potential_df=slot_potential_df, current_power=current_power)
        log.info("")
        log.info(f"EVALUATING ALTERNATIVE {slot.__name__.upper()} SLOT POTENTIAL...")

        # Evaluate artifact potential
        # Start with the equipped artifact and then iterate through other artifacts, sorted numerically
        log.info("!!! CURRENTLY EQUIPPED ARTIFACT !!!")
        equipped_artifact = equipped_artifacts.get_artifact(slot)
        other_artifacts = [artifact for artifact in alternative_artifacts[slot] if artifact is not equipped_artifact]
        other_artifacts.sort(key=lambda artifact: int(artifact.name))
        alternative_artifacts_slot = [equipped_artifact] + other_artifacts
        equipped_power = None
        for alternative_artifact in alternative_artifacts_slot:
            # Log artifact
            log.info(
                f"                                                    MAIN STAT   HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
            )
            log.info(alternative_artifact.to_string_table())
            # Calculate potential
            artifact_potential_df = _individual_potential(
                character=character,
                equipped_artifacts=equipped_artifacts,
                slot=type(alternative_artifact),
                set_str=alternative_artifact.set,
                stars=alternative_artifact.stars,
                main_stat=alternative_artifact.main_stat,
                target_level=alternative_artifact.max_level,
                substat_rolls=alternative_artifact.substat_rolls,
                source=source,
            )
            artifact_potentials[slot][alternative_artifact] = artifact_potential_df
            # Save equipped power
            if equipped_power is None:
                equipped_potential_df_sorted = artifact_potential_df.sort_values("power")
                cumsum = equipped_potential_df_sorted["probability"].cumsum()
                equipped_power = equipped_potential_df_sorted.iloc[(cumsum >= 0.5).idxmax()]["power"]
            # Log results (and calculate score)
            score, beat_equipped_chance = log_artifact_power(
                slot_potential_df=slot_potential_df,
                artifact_potential_df=artifact_potential_df,
                equipped_power=equipped_power,
                artifact=alternative_artifact,
            )
            artifact_scores[slot][alternative_artifact] = (score, beat_equipped_chance)

            log.info("")

        # Summarize slot
        # Sort scores decending
        artifact_scores_sorted = dict(sorted(artifact_scores[slot].items(), key=lambda item: item[1], reverse=True))
        set_str_long = re.sub(r"(\w)([A-Z])", r"\1 \2", equipped_artifact.set)
        log.info(f"{equipped_artifact.stars}* {set_str_long} {equipped_artifact.main_stat} {slot.__name__} Scoreboard")
        header_str = (
            f"                    HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%    Score  Chance of Beating Equipped"
        )
        ind = 1
        for artifact, (score, beat_equipped_chance) in artifact_scores_sorted.items():
            if ind % 10 == 1:
                log.info(header_str)
            log_str = f"{ind:>3.0f}) " + artifact.to_short_string_table() + f" {score:>8,.0f}  "
            if artifact is equipped_artifact:
                # Mark as equipped
                log_str += "EQUIPPED"
            else:
                # Add decimal with fixed period
                if beat_equipped_chance > 1e-8:
                    decimal.getcontext().prec = 2
                    decimal_str = str(decimal.getcontext().create_decimal(beat_equipped_chance)) + "%"
                else:
                    decimal_str = "0.0%"
                if beat_equipped_chance < 100:
                    decimal_str = " " + decimal_str
                if beat_equipped_chance < 10:
                    decimal_str = " " + decimal_str
                log_str += decimal_str
            log.info(log_str)
            ind += 1
        log.info("")

    a = 1


def log_slot_power(slot_potential_df: pd.DataFrame, current_power: float):
    """Logs slot potential to console"""
    # Minimum Power
    min_power = slot_potential_df["power"].min()
    # Maximum Power
    max_power = slot_potential_df["power"].max()
    max_power_increase = 100 * (max_power / min_power - 1)
    # Median Power
    slot_potential_df_sorted = slot_potential_df.sort_values("power")
    cumsum = slot_potential_df_sorted["probability"].cumsum()
    median_power = slot_potential_df_sorted.iloc[(cumsum >= 0.5).idxmax()]["power"]
    median_power_increase = 100 * (median_power / min_power - 1)
    # Base Power
    if current_power is not None:
        current_power_increase = 100 * (current_power / min_power - 1)
        current_power_percentile = (
            100 * slot_potential_df["probability"][slot_potential_df["power"] < current_power].sum()
        )
    # Log to console
    # fmt: off
    if current_power is not None:
        if current_power < min_power:
            log.info(f"Current Power:       {current_power:>7,.0f} | {current_power_increase:>+5.1f}% | {current_power_percentile:>5.1f}{_suffix(current_power_percentile)} Slot Percentile")
    log.info(f"Slot Min Power:      {min_power:>7,.0f} |  +0.0%")
    if current_power is not None:
        if min_power <= current_power < median_power:
            log.info(f"Current Power:       {current_power:>7,.0f} | {current_power_increase:>+5.1f}% | {current_power_percentile:>5.1f}{_suffix(current_power_percentile)} Slot Percentile")
    log.info(f"Slot Expected Power: {median_power:>7,.0f} | {median_power_increase:>+5.1f}%")
    if current_power is not None:
        if current_power >= median_power: 
            log.info(f"Current Power:       {current_power:>7,.0f} | {current_power_increase:>+5.1f}% | {current_power_percentile:>5.1f}{_suffix(current_power_percentile)} Slot Percentile")
    log.info(f"Slot Max Power:      {max_power:>7,.0f} | {max_power_increase:>+5.1f}%")
    # fmt: on


def log_artifact_power(
    slot_potential_df: pd.DataFrame, artifact_potential_df: pd.DataFrame, equipped_power: float, artifact: Artifact
):
    """Logs artifact potential to console"""

    # Slot Power
    slot_min_power = slot_potential_df["power"].min()
    # Minimum Artifact Power
    artifact_min_power = artifact_potential_df["power"].min()
    min_power_increase = 100 * (artifact_min_power / slot_min_power - 1)
    min_power_slot_percentile = (
        100 * slot_potential_df["probability"][slot_potential_df["power"] < artifact_min_power].sum()
    )
    # Median Artifact Power
    artifact_potential_df_sorted = artifact_potential_df.sort_values("power")
    cumsum = artifact_potential_df_sorted["probability"].cumsum()
    artifact_median_power = artifact_potential_df_sorted.iloc[(cumsum >= 0.5).idxmax()]["power"]
    median_power_increase = 100 * (artifact_median_power / slot_min_power - 1)
    median_power_slot_percentile = (
        100 * slot_potential_df["probability"][slot_potential_df["power"] < artifact_median_power].sum()
    )
    # Maximum Artifact Power
    artifact_max_power = artifact_potential_df["power"].max()
    max_power_increase = 100 * (artifact_max_power / slot_min_power - 1)
    max_power_slot_percentile = (
        100 * slot_potential_df["probability"][slot_potential_df["power"] < artifact_max_power].sum()
    )
    # Current Power
    equipped_power_artifact_percentile = (
        100 * artifact_potential_df["probability"][artifact_potential_df["power"] < equipped_power].sum()
    )
    equipped_power_increase = 100 * (equipped_power / slot_min_power - 1)
    equipped_power_slot_percentile = (
        100 * slot_potential_df["probability"][slot_potential_df["power"] < equipped_power].sum()
    )

    # Log to console
    if equipped_power is not None:
        if equipped_power < artifact_min_power:
            log.info(
                f"Equipped Power:          {equipped_power:>7,.0f} | {equipped_power_increase:>+5.1f}% | {equipped_power_slot_percentile:>5.1f}{_suffix(equipped_power_slot_percentile)} Slot Percentile | {equipped_power_artifact_percentile:>5.1f}{_suffix(equipped_power_artifact_percentile)} Artifact Percentile"
            )
    num_child_artifacts = artifact_potential_df.shape[0]
    if num_child_artifacts > 1:
        log.info(
            f"Artifact Min Power:      {artifact_min_power:>7,.0f} | {min_power_increase:>+5.1f}% | {min_power_slot_percentile:>5.1f}{_suffix(min_power_slot_percentile)} Slot Percentile"
        )
    if equipped_power is not None:
        if artifact_min_power <= equipped_power < artifact_median_power:
            log.info(
                f"Equipped Power:          {equipped_power:>7,.0f} | {equipped_power_increase:>+5.1f}% | {equipped_power_slot_percentile:>5.1f}{_suffix(equipped_power_slot_percentile)} Slot Percentile | {equipped_power_artifact_percentile:>5.1f}{_suffix(equipped_power_artifact_percentile)} Artifact Percentile"
            )
    log.info(
        f"Artifact Expected Power: {artifact_median_power:>7,.0f} | {median_power_increase:>+5.1f}% | {median_power_slot_percentile:>5.1f}{_suffix(median_power_slot_percentile)} Slot Percentile"
    )
    if equipped_power is not None:
        if (
            artifact_median_power < equipped_power < artifact_max_power
        ):  # Not <= because I don't want it printing if this IS the equipped artifact
            log.info(
                f"Equipped Power:          {equipped_power:>7,.0f} | {equipped_power_increase:>+5.1f}% | {equipped_power_slot_percentile:>5.1f}{_suffix(equipped_power_slot_percentile)} Slot Percentile | {equipped_power_artifact_percentile:>5.1f}{_suffix(equipped_power_artifact_percentile)} Artifact Percentile"
            )
    if num_child_artifacts > 1:
        log.info(
            f"Artifact Max Power:      {artifact_max_power:>7,.0f} | {max_power_increase:>+5.1f}% | {max_power_slot_percentile:>5.1f}{_suffix(max_power_slot_percentile)} Slot Percentile"
        )
    if equipped_power is not None:
        if equipped_power >= artifact_max_power and equipped_power > artifact_median_power:
            log.info(
                f"Equipped Power:          {equipped_power:>7,.0f} | {equipped_power_increase:>+5.1f}% | {equipped_power_slot_percentile:>5.1f}{_suffix(equipped_power_slot_percentile)} Slot Percentile |  {equipped_power_artifact_percentile:>5.1f}{_suffix(equipped_power_artifact_percentile)} Artifact Percentile"
            )

    # Calculate artifact score
    # Cost to run domain once
    if artifact.set in genshin_data.dropped_from_world_boss:
        run_cost = 40
    else:
        run_cost = 20
    # Chance to drop artifact with same set, slot, and main_stat
    drop_chance = 0.5 * 0.2 * genshin_data.main_stat_drop_rate[type(artifact).__name__][artifact.main_stat] / 100
    # Chance of dropping better artifact
    better_chance = (100 - median_power_slot_percentile) / 100
    # Score
    score = run_cost / (drop_chance * better_chance)
    log_str = f"Artifact Score: {score:>6,.0f} Resin"
    # Better than equipped chance
    if equipped_power != artifact_median_power:
        beat_equipped_chance = 100 - equipped_power_artifact_percentile
        decimal.getcontext().prec = 2
        beat_equipped_chance_str = str(decimal.getcontext().create_decimal(beat_equipped_chance)) + "%"
        log_str += f"         Chance of Beating Equipped: {beat_equipped_chance_str}"
    else:
        beat_equipped_chance = None
    log.info(log_str)

    return score, beat_equipped_chance


def _suffix(value: float) -> str:
    suffix = ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"]
    mod_value = round(10 * value) % 10
    return suffix[mod_value]


# ### CLASSES GENERATED THROUGH PUBLIC METHODS ###


# class SlotPotential:
#     """Contains the potentials of a slot and the settings used to generate them"""

#     def __init__(
#         self,
#         character: Character,
#         equipped_artifacts: Artifacts,
#         slot: type,
#         set_str: str,
#         stars: int,
#         main_stat: str,
#         target_level: int,
#         source: str,
#         potential_df: pd.DataFrame,
#     ):
#         """Initialize slot potentials, called in other functions in file"""
#         # Save inputs
#         self._character = character
#         self._equipped_artifacts = equipped_artifacts
#         self._slot = slot
#         self._target_level = target_level
#         self._set = set_str
#         self._stars = stars
#         self._main_stat = main_stat
#         self._source = source
#         self._potential_df = potential_df

#     @property
#     def character(self) -> Character:
#         return self._character

#     @property
#     def equipped_artifacts(self) -> Artifacts:
#         return self._equipped_artifacts

#     @property
#     def slot(self) -> type:
#         return self._slot

#     @property
#     def target_level(self) -> int:
#         return self._target_level

#     @property
#     def set(self) -> str:
#         return self._set

#     @property
#     def stars(self) -> int:
#         return self._stars

#     @property
#     def main_stat(self) -> str:
#         return self._main_stat

#     @property
#     def source(self) -> str:
#         return self._source

#     @property
#     def potential_df(self) -> pd.DataFrame:
#         return self._potential_df

#     def log_report(self, base_power: float, log: logging.Logger):
#         """Logs slot potential to console"""

#         # Extract series
#         slot_power = self.potential_df["power"]
#         slot_percentile = self.potential_df["probability"]
#         # Minimum Power
#         min_power = slot_power.min()
#         # Maximum Power
#         max_power = slot_power.max()
#         max_power_increase = 100 * (max_power / min_power - 1)
#         # Average Power
#         avg_power = slot_power.dot(slot_percentile)
#         avg_power_increase = 100 * (avg_power / min_power - 1)
#         avg_power_percentile = 100 * slot_percentile[slot_power < avg_power].sum()
#         # Base Power
#         if base_power is not None:
#             base_power_increase = 100 * (base_power / min_power - 1)
#             base_power_percentile = 100 * slot_percentile[slot_power < base_power].sum()
#         # Log to console
#         # fmt: off
#         log.info(f"{len(self.potential_df.index):,} different ways to roll condensed substats.")
#         log.info(f"Slot Min Power: {min_power:>7,.0f} |  +0.0% |   0.0th Slot Percentile")
#         if base_power is not None:
#             if base_power < avg_power:
#                 log.info(f"Base Power:     {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_percentile:>5.1f}{_suffix(base_power_percentile)} Slot Percentile")
#         log.info(f"Slot Avg Power: {avg_power:>7,.0f} | {avg_power_increase:>+5.1f}% | {avg_power_percentile:>5.1f}{_suffix(avg_power_percentile)} Slot Percentile")
#         if base_power is not None:
#             if base_power >= avg_power:
#                 log.info(f"Base Power:     {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_percentile:>5.1f}{_suffix(base_power_percentile)} Slot Percentile")
#         log.info(f"Slot Max Power: {max_power:>7,.0f} | {max_power_increase:>+5.1f}% | 100.0th Slot Percentile")
#         # fmt: on

#     def match(self, other_potential: SlotPotential):
#         return (
#             self.character == other_potential.character
#             and self.equipped_artifacts == other_potential.equipped_artifacts
#             and self.slot == other_potential.slot
#             and self.set == other_potential.set
#             and self.stars == other_potential.stars
#             and self.main_stat == other_potential.main_stat
#             and self.target_level == other_potential.target_level
#             and self.source == other_potential.source
#         )


# class ArtifactPotential(SlotPotential):
#     """Contains the potentials of an artifact and the settings used to generate them"""

#     def __init__(self, name: str, substat_rolls: dict[str, int], slot_potential: SlotPotential = None, **kwargs):
#         super(ArtifactPotential, self).__init__(**kwargs)
#         self._substat_rolls = substat_rolls
#         if slot_potential is not None:
#             if not self.match(slot_potential):
#                 raise ValueError("Slot Potential and Artifact Potential do not match")
#         self._name = name
#         self._slot_potential = slot_potential

#     @property
#     def name(self) -> str:
#         return self._name

#     @property
#     def substat_rolls(self) -> dict[str, int]:
#         return self._substat_rolls

#     @property
#     def slot_potential(self) -> SlotPotential:
#         return self._slot_potential

#     def find_matching_slot_potential(self, slot_potentials: list[SlotPotential]):
#         """Finds first slot potential in list to match properties"""
#         for slot_potential in slot_potentials:
#             if slot_potential.match(self):
#                 self._slot_potential = slot_potential
#                 return

#     def log_report(self, base_power: float, log: logging.Logger):
#         """Logs artifact potential to console"""

#         # Number of artifacts
#         num_artifacts = len(self.potential_df.index)
#         log.info(f"{num_artifacts:,} different ways to roll condensed substats.")

#         # Extract series
#         artifact_power = self.potential_df["power"]
#         artifact_percentile = self.potential_df["probability"]
#         # Minimum Artifact Power
#         artifact_min_power = artifact_power.min()
#         # Average Artifact Power
#         artifact_avg_power = artifact_power.dot(artifact_percentile)
#         if num_artifacts > 1:
#             avg_power_artifact_percentile = 100 * artifact_percentile[artifact_power < artifact_avg_power].sum()
#         else:
#             avg_power_artifact_percentile = 50.0
#         # Maximum Artifact Power
#         artifact_max_power = artifact_power.max()
#         # Base Power
#         if base_power is not None:
#             base_power_artifact_percentile = 100 * artifact_percentile[artifact_power < base_power].sum()

#         # Get slot
#         if self.slot_potential is not None:
#             slot_power = self.slot_potential.potential_df["power"]
#             slot_percentile = self.slot_potential.potential_df["probability"]
#             slot_min_power = slot_power.min()
#             slot_max_power = slot_power.max()
#             slot_max_power_increase = 100 * (slot_max_power / slot_min_power - 1)
#             # Minimum Artifact Power
#             min_power_increase = 100 * (artifact_min_power / slot_min_power - 1)
#             min_power_slot_percentile = 100 * slot_percentile[slot_power < artifact_min_power].sum()
#             # Average Artifact Power
#             avg_power_increase = 100 * (artifact_avg_power / slot_min_power - 1)
#             avg_power_slot_percentile = 100 * slot_percentile[slot_power < artifact_avg_power].sum()
#             # Maximum Artifact Power
#             max_power_increase = 100 * (artifact_max_power / slot_min_power - 1)
#             max_power_slot_percentile = 100 * slot_percentile[slot_power < artifact_max_power].sum()
#             # Base Power
#             if base_power is not None:
#                 base_power_increase = 100 * (base_power / slot_min_power - 1)
#                 base_power_slot_percentile = 100 * slot_percentile[slot_power < base_power].sum()
#             # Log to console
#             # fmt: off
#             if base_power is not None:
#                 if base_power < artifact_min_power:
#                     log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile")
#             if num_artifacts > 1:
#                 log.info(f"Artifact Min Power: {artifact_min_power:>7,.0f} | {min_power_increase:>+5.1f}% |   0.0th Artifact Percentile | {min_power_slot_percentile:>5.1f}{_suffix(min_power_slot_percentile)} Slot Percentile")
#             if base_power is not None:
#                 if artifact_min_power <= base_power < artifact_avg_power:
#                     log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile")
#             log.info(f"Artifact Avg Power: {artifact_avg_power:>7,.0f} | {avg_power_increase:>+5.1f}% | {avg_power_artifact_percentile:>5.1f}{_suffix(avg_power_artifact_percentile)} Artifact Percentile | {avg_power_slot_percentile:>5.1f}{_suffix(avg_power_slot_percentile)} Slot Percentile")
#             if base_power is not None:
#                 if artifact_avg_power <= base_power < artifact_max_power:
#                     log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile")
#             if num_artifacts > 1:
#                 log.info(f"Artifact Max Power: {artifact_max_power:>7,.0f} | {max_power_increase:>+5.1f}% | 100.0th Artifact Percentile | {max_power_slot_percentile:>5.1f}{_suffix(max_power_slot_percentile)} Slot Percentile")
#             if base_power is not None:
#                 if base_power >= artifact_max_power:
#                     log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile")
#             log.info(f"Slot Max Power:     {slot_max_power:>7,.0f} | {slot_max_power_increase:>+5.1f}% | 100.0th Artifact Percentile | 100.0th Slot Percentile")
#             # fmt: on
#         else:
#             log.info(
#                 "(No slot potential found. Run slot_potential() or all_slots_potentials() with matching parameters.)"
#             )
#             if (
#                 self.set != self.equipped_artifacts.get_artifact(self.slot).set
#             ) and self.equipped_artifacts.use_set_bonus:
#                 log.info(
#                     "(Equipped artifact has different set than evaluating artifact. Base power may be naturally higher. Consider using equipped_artifacts.use_set_bonus = False)"
#                 )
#             avg_power_increase = 100 * (artifact_avg_power / artifact_min_power - 1)
#             max_power_increase = 100 * (artifact_max_power / artifact_min_power - 1)
#             # Base Power
#             if base_power is not None:
#                 base_power_increase = 100 * (base_power / artifact_min_power - 1)
#             # Log to console
#             # fmt: off
#             if base_power is not None:
#                 if base_power < artifact_min_power:
#                     log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile")
#             if num_artifacts > 0:
#                 log.info(f"Artifact Min Power: {artifact_min_power:>7,.0f} |  +0.0% |   0.0th Artifact Percentile")
#             if base_power is not None:
#                 if artifact_min_power <= base_power < artifact_avg_power:
#                     log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile")
#             log.info(f"Artifact Avg Power: {artifact_avg_power:>7,.0f} | {avg_power_increase:>+5.1f}% | {avg_power_artifact_percentile:>5.1f}{_suffix(avg_power_artifact_percentile)} Artifact Percentile")
#             if base_power is not None:
#                 if artifact_avg_power <= base_power < artifact_max_power:
#                     log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile")
#             if num_artifacts > 0:
#                 log.info(f"Artifact Max Power: {artifact_max_power:>7,.0f} | {max_power_increase:>+5.1f}% | 100.0th Artifact Percentile")
#             if base_power is not None:
#                 if  base_power >= artifact_max_power:
#                     log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile")
#             # fmt: on


### PUBLIC METHODS TO CREATE SLOT POTENTIAL OBJECTS ###


# def all_slots_potentials(
#     character: Character,
#     equipped_artifacts: Artifacts,
#     target_level: int = None,
#     source: str = None,
#     verbose: bool = True,
#     plot: bool = False,
#     smooth_plot: bool = True,
# ) -> list[SlotPotential]:
#     """Calculates the slot potential for all slots

#     Parameters
#     ----------
#     character : Character
#         Character to evaluate artifacts on
#     equipped_artifacts : Artifacts
#         Source of set, stars, and main stat for evaluating slots. Will be equipped on character when evaluating other
#         slots
#     target_level : int, default=None,
#         Artifact level to evaluate to. If not supplied, defaults to max level.
#     source : str, default=None,
#         Source of artifacts. Different sources have different low vs high substat drop rates. Default defined by set in
#         genshin_data.py.
#     verbose : bool, default=True
#         Booleon whether to output updates to console
#     TODO
#     plot : bool, default=False

#     Returns
#     ----------
#     list[SlotPotential]
#         List containing the slot potentials for each possible slot based on provided evaluation criteria
#     """

#     # Set verbosity
#     log = logging.getLogger(__name__)
#     if verbose:
#         log.setLevel("INFO")
#     else:
#         log.setLevel("WARNING")

#     # Validate inputs
#     # Source must be a valid source
#     if source is not None and source not in genshin_data.extra_substat_probability:
#         raise ValueError("Invalid domain name.")
#     # Target level must be a valid target level
#     if target_level is not None:
#         if target_level < 0:
#             raise ValueError("Target level cannot be less than 0.")
#         elif target_level > 20:
#             raise ValueError("Target level cannot be greater than 20.")

#     # Calculate base power
#     base_power = power_calculator.evaluate_power(character=character, artifacts=equipped_artifacts)

#     # Log intro
#     # fmt: off
#     log.info("-" * 110)
#     log.info("Evaluating potential of all slots...")
#     log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
#     log.info(f"WEAPON: {character.weapon.name_formated.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
#     if character.amplifying_reaction is not None:
#         log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)")
#     log.info(f"EQUIPPED ARTIFACTS:                                       HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%")
#     for artifact in equipped_artifacts:
#         log.info(f"{artifact.to_string_table()}")
#     if not equipped_artifacts.use_set_bonus:
#         log.info("Set Bonuses Off")
#     log.info(f"BASE POWER: {base_power:,.0f}")
#     # fmt: on

#     # Iterate through artifacts
#     slot_potentials = list[SlotPotential]()
#     for slot in [Flower, Plume, Sands, Goblet, Circlet]:
#         base_artifact = equipped_artifacts.get_artifact(slot)
#         if base_artifact is None:
#             log.warning(f"Artifacts does not contain a {slot.__name__}")
#         else:
#             # Default target_level
#             iter_target_level = (
#                 genshin_data.max_level_by_stars[base_artifact.stars] if target_level is None else target_level
#             )
#             # Default source
#             iter_source = genshin_data.default_artifact_source[base_artifact.set] if source is None else source
#             # Log artifact
#             log.info("-" * 10)
#             log.info(f"Evaluating {slot.__name__} slot potential...")
#             log.info("ARTIFACT:")
#             log.info(
#                 (
#                     f"{slot.__name__.title():>7s} "
#                     f"{base_artifact.stars:>d}* "
#                     f"{base_artifact.set.title():>14} "
#                     f"{iter_target_level:>2d}/{genshin_data.max_level_by_stars[base_artifact.stars]:>2d} "
#                     f"{base_artifact.main_stat:>17s}: {genshin_data.main_stat_scaling[base_artifact.stars][base_artifact.main_stat][iter_target_level]:>4}"
#                 )
#             )
#             # Calculate potential
#             potential_df = _individual_potential(
#                 character=character,
#                 equipped_artifacts=equipped_artifacts,
#                 slot=slot,
#                 set_str=base_artifact.set,
#                 stars=base_artifact.stars,
#                 main_stat=base_artifact.main_stat,
#                 target_level=iter_target_level,
#                 source=iter_source,
#             )
#             slot_potential = SlotPotential(
#                 character=character,
#                 equipped_artifacts=equipped_artifacts,
#                 slot=slot,
#                 set_str=base_artifact.set,
#                 stars=base_artifact.stars,
#                 main_stat=base_artifact.main_stat,
#                 target_level=iter_target_level,
#                 source=iter_source,
#                 potential_df=potential_df,
#             )
#             # Report on potential
#             slot_potential.log_report(base_power=base_power, log=log)
#             # Append to return
#             slot_potentials.append(slot_potential)
#     if plot:
#         log.info("-" * 10)
#         log.info("Plotting slots...")
#         legend_label = ["Flower", "Plume", "Sands", "Goblet", "Circlet"]
#         title = f"Slot Potentials on {character.name.title()}"
#         graphing.graph_slot_potentials(
#             slot_potentials=slot_potentials,
#             legend_labels=legend_label,
#             base_power=base_power,
#             title=title,
#             smooth_plot=smooth_plot,
#         )
#         log.info("Slots plotted.")
#     return slot_potentials


# def slot_potential(
#     character: Character,
#     equipped_artifacts: Artifacts,
#     slot: type,
#     set_str: str = None,
#     stars: int = None,
#     main_stat: str = None,
#     target_level: int = None,
#     source: str = None,
#     verbose: bool = True,
#     plot: bool = False,
#     smooth_plot: bool = True,
# ) -> list[SlotPotential]:
#     """Calculates the probabillity and power of all possible substats for a single slots

#     Parameters
#     ----------
#     character : Character
#         Character to evaluate artifacts on
#     equipped_artifacts : Artifacts
#         Artifacts to equip character with if not in slot
#     slot : type
#         Base artifact slot.
#     set_str : str, default=None
#         Base artifact set. If not supplied, defaults to set of artifact in slot in equipped_artifacts.
#     stars : int, default=None
#         Base artifact number of stars. If not supplied, defaults to stars of artifact in slot in equipped_artifacts.
#     main_stat : str, default=None,
#         Base artifact main stat. If not supplied, defaults to main stat of artifact in slot in equipped_artifacts.
#     target_level : int, default=None,
#         Artifact level to evaluate to. If not supplied, defaults to maximum give artifact stars.
#     source : str, default=None,
#         Source of artifacts. Different sources have different low vs high substat drop rates. Default defined by set in
#         genshin_data.py.
#     verbose : bool, default=True
#         Booleon whether to output updates to console
#     TODO
#     plot : bool, default=False

#     Returns
#     ----------
#     list[SlotPotential]
#         List containing the singular slot potential for slot based on provided evaluation criteria
#     """

#     # Set verbosity
#     log = logging.getLogger(__name__)
#     if verbose:
#         log.setLevel("INFO")
#     else:
#         log.setLevel("WARNING")

#     # Default inputs to artifact in slot
#     base_artifact = equipped_artifacts.get_artifact(slot)
#     if (set_str is None) or (stars is None) or (main_stat is None):
#         if base_artifact is None:
#             raise ValueError(
#                 f"Either artifacts must contain a {slot.__name__} or {slot.__name__} parameters are provided to evaluate slot."
#             )
#     set_str = base_artifact.set if set_str is None else set_str
#     stars = base_artifact.stars if stars is None else stars
#     main_stat = base_artifact.main_stat if main_stat is None else main_stat

#     # Validate inputs
#     # Source must be a valid source
#     if source is not None and source not in genshin_data.extra_substat_probability:
#         raise ValueError("Invalid domain name.")
#     # Target level must be a valid target level
#     if target_level is not None:
#         if target_level < 0:
#             raise ValueError("Target level cannot be less than 0.")
#         elif target_level > 20:
#             raise ValueError("Target level cannot be greater than 20.")
#     else:
#         # Default target level to maximum
#         target_level = genshin_data.max_level_by_stars[stars]
#     # Default source
#     if source is None:
#         source = genshin_data.default_artifact_source[set_str]

#     # Calculate base power
#     base_power = power_calculator.evaluate_power(character=character, artifacts=equipped_artifacts)

#     # Log intro
#     # fmt: off
#     log.info("-" * 110)
#     log.info(f"Evaluating potential of {slot.__name__} slot...")
#     log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
#     log.info(f"WEAPON: {character.weapon.name_formated.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
#     if character.amplifying_reaction is not None:
#         log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)")
#     log.info("ARTIFACT:")
#     log.info((
#             f"{slot.__name__.title():>7s} "
#             f"{stars:>d}* "
#             f"{set_str.title():>14} "
#             f"{target_level:>2d}/{genshin_data.max_level_by_stars[stars]:>2d} "
#             f"{main_stat:>17s}: {genshin_data.main_stat_scaling[stars][main_stat][target_level]:>4}"
#     ))
#     log.info(f"EQUIPPED ARTIFACTS:                                       HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%")
#     for equipped_artifact in equipped_artifacts:
#         if type(equipped_artifact) is not slot:
#             log.info(f"{equipped_artifact.to_string_table()}")
#     if not equipped_artifacts.use_set_bonus:
#         log.info("Set Bonuses Off")
#     log.info(f"BASE POWER: {base_power:,.0f}")
#     # fmt: on

#     # Evaluate single slot
#     potential_df = _individual_potential(
#         character=character,
#         equipped_artifacts=equipped_artifacts,
#         slot=slot,
#         set_str=set_str,
#         stars=stars,
#         main_stat=main_stat,
#         target_level=target_level,
#         source=source,
#     )
#     slot_potentials = [
#         SlotPotential(
#             character=character,
#             equipped_artifacts=equipped_artifacts,
#             slot=slot,
#             set_str=set_str,
#             stars=stars,
#             main_stat=main_stat,
#             target_level=target_level,
#             source=source,
#             potential_df=potential_df,
#         )
#     ]
#     # Report potential
#     slot_potentials[0].log_report(base_power=base_power, log=log)
#     if plot:
#         log.info("-" * 10)
#         log.info("Plotting slot...")
#         legend_label = [slot.__name__]
#         title = f"{stars}* {set_str.title()} {main_stat} {slot.__name__} Slot Potential on {character.name.title()}"
#         graphing.graph_slot_potentials(
#             slot_potentials=slot_potentials,
#             legend_labels=legend_label,
#             base_power=base_power,
#             title=title,
#             smooth_plot=smooth_plot,
#         )
#         log.info("Slot plotted.")
#     # Return results
#     return slot_potentials


# ### PUBLIC METHODS TO CREATE ARTIFACT POTENTIAL OBJECTS ###


# def artifacts_potentials(
#     character: Character,
#     equipped_artifacts: Artifacts,
#     evaluating_artifacts: dict[str],
#     target_level: int = None,
#     source: str = None,
#     slot_potentials: list[SlotPotential] = None,
#     verbose: bool = True,
#     plot: bool = False,
#     smooth_plot: bool = True,
# ) -> list[ArtifactPotential]:
#     """Calculates the probabillity and power of all possible substats for the artifacts

#     Parameters
#     ----------
#     character : Character
#         Character to evaluate artifacts on
#     equipped_artifacts : Artifacts
#         Artifacts to equip character with if not in slot
#     evaluating_artifacts : dict[str]
#         Dictionary of artifacts to evaluate substats for, keyed to "name" of artifact
#     target_level : int, default=None,
#         Artifact level to evaluate to. If not supplied, defaults to maximum give artifact stars.
#     source : str, default=None,
#         Source of artifacts. Different sources have different low vs high substat drop rates. Default defined by set in
#         genshin_data.py.
#     slot_potentials : list[SlotPotential], default=None
#         List of slot potentials that MAY contain a match for current parameters
#     verbose : bool, default=True
#         Booleon whether to output updates to console

#     Returns
#     ----------
#     list[ArtifactPotential]
#        List containing the artifact potentials for each provided artifact based on provided evaluation criteria
#     """

#     # Set verbosity
#     log = logging.getLogger(__name__)
#     if verbose:
#         log.setLevel("INFO")
#     else:
#         log.setLevel("WARNING")

#     # Validate inputs
#     # Source must be a valid source
#     if source is not None and source not in genshin_data.extra_substat_probability:
#         raise ValueError("Invalid domain name.")
#     # Target level must be a valid target level
#     if target_level is not None:
#         if target_level < 0:
#             raise ValueError("Target level cannot be less than 0.")
#         elif target_level > 20:
#             raise ValueError("Target level cannot be greater than 20.")

#     # Calculate base power
#     base_power = power_calculator.evaluate_power(character=character, artifacts=equipped_artifacts)

#     # Log intro
#     # fmt: off
#     log.info("-" * 110)
#     log.info("Evaluating potential of artifacts...")
#     log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
#     log.info(f"WEAPON: {character.weapon.name.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
#     if character.amplifying_reaction is not None:
#         log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)")
#     log.info(f"EQUIPPED ARTIFACTS:                                       HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%")
#     for artifact in equipped_artifacts:
#         log.info(f"{artifact.to_string_table()}")
#     if not equipped_artifacts.use_set_bonus:
#         log.info("Set Bonuses Off")
#     log.info(f"BASE POWER: {base_power:,.0f}")
#     # fmt: on

#     # Iterate through artifacts
#     artifact_potentials = []
#     for artifact_name, base_artifact in evaluating_artifacts.items():
#         # Default target_level
#         iter_target_level = (
#             genshin_data.max_level_by_stars[base_artifact.stars] if target_level is None else target_level
#         )
#         # Default source
#         iter_source = genshin_data.default_artifact_source[base_artifact.set] if source is None else source
#         # Log artifact
#         log.info("-" * 10)
#         log.info(f"Evaluating {artifact_name} potential...")
#         log.info(
#             f"ARTIFACT:                                                 HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
#         )
#         log.info(f"{base_artifact.to_string_table()}")
#         # Calculate potential
#         potential_df = _individual_potential(
#             character=character,
#             equipped_artifacts=equipped_artifacts,
#             slot=type(base_artifact),
#             set_str=base_artifact.set,
#             stars=base_artifact.stars,
#             main_stat=base_artifact.main_stat,
#             starting_level=base_artifact.level,
#             target_level=iter_target_level,
#             substat_rolls=base_artifact.substat_rolls,
#             source=iter_source,
#         )
#         # Create and report artifact potential
#         artifact_potential = ArtifactPotential(
#             name=artifact_name,
#             character=character,
#             equipped_artifacts=equipped_artifacts,
#             slot=type(base_artifact),
#             set_str=base_artifact.set,
#             stars=base_artifact.stars,
#             main_stat=base_artifact.main_stat,
#             target_level=iter_target_level,
#             substat_rolls=base_artifact.substat_rolls,
#             source=iter_source,
#             potential_df=potential_df,
#         )
#         artifact_potential.find_matching_slot_potential(slot_potentials=slot_potentials)
#         artifact_potential.log_report(base_power=base_power, log=log)
#         # Append to return
#         artifact_potentials.append(artifact_potential)

#     if plot:
#         log.info("-" * 10)
#         log.info("Plotting artifacts...")
#         graphing.graph_artifact_potentials(
#             artifact_potentials=artifact_potentials,
#             base_power=base_power,
#             smooth_plot=smooth_plot,
#         )
#         log.info("Slot plotted.")
#     return artifact_potentials


# def artifact_potential(
#     character: Character,
#     equipped_artifacts: Artifacts,
#     evaluating_artifact: Artifact,
#     target_level: int = None,
#     source: str = None,
#     slot_potentials: list[SlotPotential] = None,
#     verbose: bool = True,
#     plot: bool = False,
#     artifact_name: str = None,
#     smooth_plot: bool = True,
# ) -> list[ArtifactPotential]:
#     """Calculates the probabillity and power of all possible substats rolls for a given artifact

#     Parameters
#     ----------
#     character : Character
#         Character to evaluate artifacts on
#     equipped_artifacts : Artifacts
#         Artifacts to equip character with if not in slot
#     evaluating_artifact : Artifact
#        Artifacts to evaluate substats for
#     target_level : int, default=None,
#         Artifact level to evaluate to. If not supplied, defaults to maximum give artifact stars.
#     source : str, default=None,
#         Source of artifacts. Different sources have different low vs high substat drop rates. Default defined by set in
#         genshin_data.py.
#     slot_potentials : list[SlotPotential], default=None
#         List of slot potentials that MAY contain a match for current parameters
#     verbose : bool, default=True
#         Booleon whether to output updates to console

#     Returns
#     ----------
#     list[ArtifactPotential]
#        List containing singular artifact potentials for artifact based on provided evaluation criteria
#     """

#     # Set verbosity
#     log = logging.getLogger(__name__)
#     if verbose:
#         log.setLevel("INFO")
#     else:
#         log.setLevel("WARNING")

#     # Validate inputs
#     # Source must be a valid source
#     if source is not None and source not in genshin_data.extra_substat_probability:
#         raise ValueError("Invalid domain name.")
#     # Target level must be a valid target level
#     if target_level is not None:
#         if target_level < 0:
#             raise ValueError("Target level cannot be less than 0.")
#         elif target_level > 20:
#             raise ValueError("Target level cannot be greater than 20.")
#     else:
#         # Default target level to maximum
#         target_level = genshin_data.max_level_by_stars[evaluating_artifact.stars]
#     # Default source
#     if source is None:
#         source = genshin_data.default_artifact_source[evaluating_artifact.set]

#     # Calculate base power
#     base_power = power_calculator.evaluate_power(character=character, artifacts=equipped_artifacts)

#     # Log intro
#     # fmt: off
#     log.info("-" * 110)
#     log.info(f"Evaluating potential of single artifact...")
#     log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
#     log.info(f"WEAPON: {character.weapon.name_formated.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
#     if character.amplifying_reaction is not None:
#         log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)")
#     log.info(f"ARTIFACT:                                                 HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%")
#     log.info(f"{evaluating_artifact.to_string_table()}")
#     log.info(f"EQUIPPED ARTIFACTS:")
#     for equipped_artifact in equipped_artifacts:
#         if type(equipped_artifact) is not type(evaluating_artifact):
#             log.info(f"{equipped_artifact.to_string_table()}")
#     if not equipped_artifacts.use_set_bonus:
#         log.info("Set Bonuses Off")
#     log.info(f"BASE POWER: {base_power:,.0f}")
#     # fmt:on

#     # Evaluate single artifact
#     potential_df = _individual_potential(
#         character=character,
#         equipped_artifacts=equipped_artifacts,
#         slot=type(evaluating_artifact),
#         set_str=evaluating_artifact.set,
#         stars=evaluating_artifact.stars,
#         main_stat=evaluating_artifact.main_stat,
#         target_level=target_level,
#         substat_rolls=evaluating_artifact.substat_rolls,
#         source=source,
#     )
#     # Create and report artifact potential
#     artifact_potentials = [
#         ArtifactPotential(
#             name=artifact_name,
#             character=character,
#             equipped_artifacts=equipped_artifacts,
#             slot=type(evaluating_artifact),
#             set_str=evaluating_artifact.set,
#             stars=evaluating_artifact.stars,
#             main_stat=evaluating_artifact.main_stat,
#             starting_level=evaluating_artifact.level,
#             target_level=target_level,
#             substat_rolls=evaluating_artifact.substat_rolls,
#             source=source,
#             potential_df=potential_df,
#         )
#     ]
#     artifact_potentials[0].find_matching_slot_potential(slot_potentials=slot_potentials)
#     artifact_potentials[0].log_report(base_power=base_power, log=log)
#     if plot:
#         log.info("-" * 10)
#         log.info("Plotting artifact...")
#         graphing.graph_artifact_potentials(
#             artifact_potentials=artifact_potentials,
#             base_power=base_power,
#             smooth_plot=smooth_plot,
#         )
#         log.info("Slot plotted.")
#     return artifact_potentials


### PRIVATE METHODS CALLED BY METHODS ABOVE ###


def _individual_potential(
    character: Character,
    equipped_artifacts: Artifacts,
    slot: type,
    set_str: str,
    stars: int,
    main_stat: str,
    target_level: int,
    source: str,
    starting_level: int = None,
    substat_rolls: dict[str] = None,
) -> pd.DataFrame:
    """Calculates the probabillity and power of all possible substats rolls for given parameters

    Parameters
    ----------
    character : Character
        Character to evaluate artifacts on
    equipped_artifacts : Artifacts
        Artifacts to equip character with if not in slot
    slot : type
        Base artifact slot
    set_str : str
        Base artifact set
    stars : int
        Base artifact number of stars
    main_stat : str
        Base artifact main stat
    target_level : int
        Artifact level to evaluate to
    source : str
        Source of artifacts. Different sources have different low vs high substat drop rates.
    starting_level : int, default = None
        Starting level of artifact is substat_rolls is suppied. Used to identify number of rolls.
    substats_rolls : dict[str], default=None
        Dictionary of rolls of substats to start with. If not provided, will evaluate all possible starting substats.

    Returns
    ----------
    pd.Dataframe
       Slot potentials including substats, power, and probability
    """

    # Default substats
    seed_pseudo_artifact = {"substats": {}, "probability": 1.0}
    seed_pseudo_artifact_rolls = {"substats": {}, "probability": 1.0}
    if substat_rolls is not None:
        for substat, rolls in substat_rolls.items():
            seed_pseudo_artifact["substats"][substat] = 0
            seed_pseudo_artifact_rolls["substats"][substat] = [0, 0, 0, 0]
            for roll in rolls:
                roll_level = genshin_data.substat_roll_values[substat][stars].index(roll)
                seed_pseudo_artifact_rolls["substats"][substat][roll_level] += 1

    # Calculate number of unlocks and increases
    existing_unlocks = len(seed_pseudo_artifact["substats"])
    if substat_rolls is not None:
        remaining_unlocks = min(4, max(0, stars - 2) + math.floor(target_level / 4)) - existing_unlocks
        if starting_level is not None:
            remaining_increases = math.floor(target_level / 4) - math.floor(starting_level / 4) - remaining_unlocks
        else:
            existing_increases = sum([len(rolls) for substat, rolls in substat_rolls.items()]) - existing_unlocks
            remaining_increases = (
                max(0, stars - 2)
                + math.floor(target_level / 4)
                - existing_unlocks
                - remaining_unlocks
                - existing_increases
            )
    else:
        remaining_unlocks = min(4, max(0, stars - 2) + math.floor(target_level / 4)) - existing_unlocks
        remaining_increases = max(0, stars - 2) + math.floor(target_level / 4) - existing_unlocks - remaining_unlocks

    total_rolls_high_chance = genshin_data.extra_substat_probability[source][stars]

    # Identify roll combinations
    substat_values_df, slot_potential_df = _make_children(
        character=character,
        stars=stars,
        main_stat=main_stat,
        remaining_unlocks=remaining_unlocks,
        remaining_increases=remaining_increases,
        total_rolls_high_chance=total_rolls_high_chance,
        seed_pseudo_artifact=seed_pseudo_artifact,
        seed_pseudo_artifact_rolls=seed_pseudo_artifact_rolls,
    )

    # Format output
    for stat in genshin_data.stat_names:
        if stat not in substat_values_df:
            substat_values_df[stat] = 0
    substat_values_df = substat_values_df.fillna(0)

    # Assign to artifact
    artifact = slot(
        name="pseudo", set_str=set_str, main_stat=main_stat, stars=stars, level=target_level, substats=substat_values_df
    )

    # Create artifact list, replacing previous artifact
    other_artifacts_list = [other_artifact for other_artifact in equipped_artifacts if type(other_artifact) != slot]
    other_artifacts_list.append(artifact)
    other_artifacts = Artifacts(other_artifacts_list)

    # Calculate stats and power
    stats = power_calculator.evaluate_stats(character=character, artifacts=other_artifacts)
    power = power_calculator.evaluate_power(
        character=character, stats=stats, probability=slot_potential_df["probability"]
    )

    # Return results
    slot_potential_df["power"] = power
    return slot_potential_df


def _make_children(
    character: Character,
    stars: int,
    main_stat: str,
    remaining_unlocks: int,
    remaining_increases: int,
    total_rolls_high_chance: float,
    seed_pseudo_artifact: dict[str],
    seed_pseudo_artifact_rolls: dict[str],
) -> pd.DataFrame:
    """Calculate probabillity of every possible substat roll

    Parameters
    ----------
    character : Character
        Character to evaluate artifacts on
    stars : int
        Base artifact number of stars
    main_stat : str
        Base artifact main stat
    remaining_unlocks : int
        Number of times to unlock substats
    remaining_increases : int
        Number of times to increase existing substats
    total_rolls_high_chance : float
        Probabillity that an artifact will be rolled with an increased number of initial stats
    seed_pseudo_artifact : dict[str]
        Pseudo-artifact dictionary to iterate off of
    seed_pseudo_artifact_rolls : dict[str]
        Pseudo-artifact dictionary recording existing rolls

    Returns
    ----------
    pd.Dataframe
       Slot potentials including substats, power, and probability
    """

    # Calculate initial substat count
    initial_substats = len(seed_pseudo_artifact["substats"])

    # Create pseudo artifact list
    pseudo_artifacts = [seed_pseudo_artifact]

    # Create every possible pseudo artifact by unlocking substats
    if remaining_unlocks > 0:
        pseudo_artifacts = _add_substats(
            pseudo_artifacts=pseudo_artifacts,
            remaining_unlocks=remaining_unlocks,
            character=character,
            main_stat=main_stat,
        )
    # Add extra unlocks (this should only occur for low stars or low target level)
    extra_unlock_chance = total_rolls_high_chance * int(
        (total_rolls_high_chance > 0) and (initial_substats + remaining_unlocks < 4)
    )
    if extra_unlock_chance > 0:
        remaining_unlocks_extra = remaining_unlocks + 1
        pseudo_artifacts_extra = _add_substats(
            pseudo_artifacts=pseudo_artifacts,
            remaining_unlocks=remaining_unlocks_extra,
            character=character,
            main_stat=main_stat,
        )
        # Fix original probabilities
        for pseudo_artifact in pseudo_artifacts:
            pseudo_artifact["probability"] *= 1 - extra_unlock_chance
        for pseudo_artifact_extra in pseudo_artifacts_extra:
            pseudo_artifact_extra["probability"] *= extra_unlock_chance
            pseudo_artifacts.append(pseudo_artifact_extra)
    if len(pseudo_artifacts) > 1:
        log.info(f"{len(pseudo_artifacts):,.0f} possible ways to roll initial substats...")

    # Create every possible pseudo artifact by assigning substat rolls
    if remaining_increases > 0:
        extra_increase_chance = total_rolls_high_chance * int(
            (total_rolls_high_chance > 0) and (initial_substats + remaining_unlocks >= 4)
        )
        pseudo_artifacts = _add_substat_rolls(
            pseudo_artifacts=pseudo_artifacts,
            remaining_increases=remaining_increases,
            extra_increase_chance=extra_increase_chance,
            character=character,
        )
    if len(pseudo_artifacts) > 1:
        log.info(f"{len(pseudo_artifacts):,.0f} possible ways to assign substat increases...")

    # Convert pseudo artifacts by calculating roll values
    substat_values_df, pseudo_artifacts_df = _calculate_substats(
        pseudo_artifacts=pseudo_artifacts,
        character=character,
        stars=stars,
        seed_pseudo_artifact_rolls=seed_pseudo_artifact_rolls,
    )
    if substat_values_df.shape[0] > 1:
        log.info(f"{substat_values_df.shape[0]:,.0f} different ways to roll substat increases...")

    return substat_values_df, pseudo_artifacts_df


def _add_substats(
    pseudo_artifacts: list[dict], remaining_unlocks: int, character: Character, main_stat: str
) -> list[dict]:
    """Creates pseudo artifacts with every possible combination of revealed substats"""

    # Generate list of possible substats
    valid_substats = set(genshin_data.substat_rarity[main_stat].keys())
    for substat in pseudo_artifacts[0]["substats"]:
        valid_substats.remove(substat)

    # Consolodate similar substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
    condensable_substats = character.condensable_substats
    base_probability = sum([genshin_data.substat_rarity[main_stat][substat] for substat in valid_substats])

    # Create list of possible substats
    possibilities = []
    for substat in valid_substats:
        possibility = {
            "substat": substat,
            "probability": genshin_data.substat_rarity[main_stat][substat] / base_probability,
        }
        possibilities.append(possibility)

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([possibility["probability"] for possibility in possibilities]) - 1) < 1e-6

    # Create all possible combinations of new substats
    combinations = tuple(itertools.combinations(possibilities, remaining_unlocks))

    # Iterate across combinations
    new_pseudo_artifacts = {}
    for combination in combinations:

        # Create new pseudo artifact
        pseudo_artifact = copy.deepcopy(pseudo_artifacts[0])

        # Assign every new substat a single roll
        for substat in combination:
            pseudo_artifact["substats"][substat["substat"]] = 1

        # Calculate probability of pseudo artifact
        combination_probability = 0
        permutations = tuple(itertools.permutations(combination, len(combination)))
        for permutation in permutations:
            permutation_probability = 1
            remaining_probability = 1
            for substat in permutation:
                permutation_probability *= substat["probability"] / remaining_probability
                remaining_probability -= substat["probability"]
            combination_probability += permutation_probability
        pseudo_artifact["probability"] = combination_probability

        # Consolodate substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
        artifact_condensable_substats = [
            substat for substat in pseudo_artifact["substats"] if substat in condensable_substats
        ]
        for (ind, artifact_condensable_substat) in enumerate(artifact_condensable_substats):
            condensed_substat = condensable_substats[ind]
            pseudo_artifact["substats"][condensed_substat] = 0
        for artifact_condensable_substat in artifact_condensable_substats:
            if artifact_condensable_substat not in condensable_substats[: len(artifact_condensable_substats)]:
                del pseudo_artifact["substats"][artifact_condensable_substat]
        assert len(pseudo_artifact["substats"]) == 4

        # Add pseudo artifact to dict
        pseudo_artifact["substats"] = dict(sorted(pseudo_artifact["substats"].items()))  # sort keys
        key = str(pseudo_artifact["substats"])
        if key not in new_pseudo_artifacts:
            new_pseudo_artifacts[key] = pseudo_artifact
        else:
            new_pseudo_artifacts[key]["probability"] += pseudo_artifact["probability"]

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([possibility["probability"] for possibility in pseudo_artifacts]) - 1) < 1e-6

    # Return new pseudo artifacts
    pseudo_artifacts = [pseudo_artifact for pseudo_artifact in new_pseudo_artifacts.values()]
    return pseudo_artifacts


def _add_substat_rolls(
    pseudo_artifacts: list[dict], remaining_increases: int, extra_increase_chance: float, character: Character
) -> list[dict]:
    """Creates pseudo artifacts with every possible combination of number of rolls for each substat"""

    # Get condensable substats
    condensable_substats = character.condensable_substats

    # If extra increase chance, run iteration a second time.
    if extra_increase_chance > 0:
        remaining_increases += 1

    # Repeat for each increase required
    for ind in range(remaining_increases):

        # Create new pseudo artifact dict
        new_pseudo_artifacts = {}

        # Iterate over existing pseudo artifacts
        for pseudo_artifact in pseudo_artifacts:

            # Consolodate similar substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
            valid_substats = set(pseudo_artifact["substats"].keys())
            condensable_substats_on_artifact = [
                condensable_substat
                for condensable_substat in condensable_substats
                if condensable_substat in valid_substats
            ]

            # Create list of possible substats
            possibilities = []
            for substat in valid_substats:
                if substat in condensable_substats:
                    if substat == condensable_substats_on_artifact[0]:
                        substat_possibility = len(condensable_substats_on_artifact) / 4
                    else:
                        continue
                else:
                    substat_possibility = 0.25
                possibility = {"substat": substat, "probability": substat_possibility}
                possibilities.append(possibility)

            # Verify probability math (sum of probabilities is almost 1)
            assert abs(sum([possibility["probability"] for possibility in possibilities]) - 1) < 1e-6

            # Create new pseudo artifacts for each possibility
            for possibility in possibilities:
                new_pseudo_artifact = copy.deepcopy(pseudo_artifact)
                if possibility["substat"] not in condensable_substats:
                    new_pseudo_artifact["substats"][possibility["substat"]] += 1
                new_pseudo_artifact["probability"] *= possibility["probability"]
                # Add pseudo artifact to dict
                key = str(new_pseudo_artifact["substats"])
                if key not in new_pseudo_artifacts:
                    new_pseudo_artifacts[key] = new_pseudo_artifact
                else:
                    new_pseudo_artifacts[key]["probability"] += new_pseudo_artifact["probability"]

        # If extra increase, merge with previous list
        if ind == 0 and extra_increase_chance > 0:
            # Update probability of new artifacts
            for new_pseudo_artifact in new_pseudo_artifacts.values():
                new_pseudo_artifact["probability"] *= extra_increase_chance
            # Update probability of old artifacts and add to dict
            for old_pseudo_artifact in pseudo_artifacts:
                old_pseudo_artifact["probability"] *= 1 - extra_increase_chance
                key = str(old_pseudo_artifact["substats"])
                if key not in new_pseudo_artifacts:
                    new_pseudo_artifacts[key] = old_pseudo_artifact
                else:
                    new_pseudo_artifacts[key]["probability"] += old_pseudo_artifact["probability"]

        # Verify probability math (sum of probabilities is almost 1)
        assert (
            abs(sum([new_pseudo_artifact["probability"] for new_pseudo_artifact in new_pseudo_artifacts.values()]) - 1)
            < 1e-6
        )

        # Return overwrite pseudo_artifacts
        pseudo_artifacts = [pseudo_artifact for pseudo_artifact in new_pseudo_artifacts.values()]

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(sum([pseudo_artifact["probability"] for pseudo_artifact in pseudo_artifacts]) - 1) < 1e-6

    return pseudo_artifacts


def _calculate_substats(
    pseudo_artifacts: list[dict], character: Character, stars: int, seed_pseudo_artifact_rolls: dict[str]
) -> pd.DataFrame:
    """Creates every possible artifact from the given number of substat rolls"""

    ## NOTE: This function is where the vast majority of the computational time is spent

    # Calculate probability of possible expanded substats
    substat_rolls_probabillities_map = _substat_rolls_probabillities(seed_pseudo_artifact_rolls)

    # Creates empty list of pseudo artifacts
    pseudo_artifacts_list = []

    # Iterate over existing pseudo artifacts
    for pseudo_artifact in pseudo_artifacts:

        # Consolodate substats
        valid_substats = set(pseudo_artifact["substats"].keys())

        # Create list of possible roll combinations for each substat
        substat_products = []
        for substat in valid_substats:
            substat_products.append(substat_rolls_probabillities_map[substat][pseudo_artifact["substats"][substat]])

        # Create list of all possible roll combinations across each substat
        pseudo_artifact_list = list(itertools.product(*substat_products))
        pseudo_artifact_df = pd.DataFrame(pseudo_artifact_list, columns=valid_substats)

        # Calculate probabillity of each case
        pseudo_artifact_df["probability"] = pseudo_artifact["probability"]
        for column in pseudo_artifact_df:
            column_df = pd.DataFrame(pseudo_artifact_df[column].tolist())
            if len(column_df.columns) == 2:
                pseudo_artifact_df["probability"] *= column_df[column_df.columns[1]]
                pseudo_artifact_df[column] = column_df[column_df.columns[0]]

        # Verify probability math (sum of probabilities is almost the initial pseudo artifact probabillity)
        assert (
            abs(pseudo_artifact_df["probability"].sum() - pseudo_artifact["probability"])
            < 1e-6 * pseudo_artifact["probability"]
        )

        # Append to list
        pseudo_artifacts_list.append(pseudo_artifact_df)

    # Append dataframes
    pseudo_artifacts_df = pd.concat(pseudo_artifacts_list)

    # Split each substat
    substats_values = {}
    for substat in pseudo_artifacts_df:
        if pseudo_artifacts_df[substat].dtype is np.dtype(object):
            column_names = [f"{substat}_{roll}" for roll in range(4)]
            substat_list = pseudo_artifacts_df[substat].tolist()
            if substat_list[0] is np.nan:
                substat_list[0] = (0, 0, 0, 0)
            rolls_split = pd.DataFrame(substat_list, columns=column_names)
            substat_value = rolls_split.dot(genshin_data.substat_roll_values[substat][stars])
            substats_values[substat] = substat_value
        else:
            substats_values[substat] = pd.Series(pseudo_artifacts_df[substat].tolist())

    substat_values_df = pd.DataFrame(substats_values)

    # Verify probability math (sum of probabilities is almost 1)
    assert abs(substat_values_df["probability"].sum() - 1) < 1e-6

    # Reset pseudo_artifacts index
    pseudo_artifacts_df.index = substat_values_df.index

    return substat_values_df, pseudo_artifacts_df


def _substat_rolls_probabillities(seed_pseudo_artifact_rolls: dict[str]) -> dict[int]:
    """Creates reference of probabillity of rolls being distibuted in a given manner"""

    # Create list of possible expanded substats
    possible_substat_rolls = {
        0: tuple(_sums(4, 0)),
        1: tuple(_sums(4, 1)),
        2: tuple(_sums(4, 2)),
        3: tuple(_sums(4, 3)),
        4: tuple(_sums(4, 4)),
        5: tuple(_sums(4, 5)),
        6: tuple(_sums(4, 6)),
    }

    # Calculates probabillity of each case
    substat_rolls_probabillities = {}
    for num_rolls in possible_substat_rolls:
        substat_rolls_probabillities[num_rolls] = []
        for roll_tuple in possible_substat_rolls[num_rolls]:
            arrangements = 1
            remaining_rolls = sum(roll_tuple)
            for num_substat_rolls in roll_tuple:
                arrangements *= math.comb(remaining_rolls, num_substat_rolls)
                remaining_rolls -= num_substat_rolls
            substat_rolls_probabillities[num_rolls].append(
                (roll_tuple, arrangements / len(roll_tuple) ** sum(roll_tuple))
            )

    # Complicated method for adding in pre-existing substat rolls from the seed artifact
    substat_rolls_probabillities_map = {}
    for substat in genshin_data.substat_roll_values:
        substat_rolls_probabillities_map[substat] = copy.deepcopy(substat_rolls_probabillities)
        if substat in seed_pseudo_artifact_rolls["substats"]:
            for num_rolls in substat_rolls_probabillities_map[substat]:
                new_combinations = []
                for combination in substat_rolls_probabillities_map[substat][num_rolls]:
                    # if combination[0] != (0,):
                    new_combination_rolls = np.array(combination[0]) + np.array(
                        seed_pseudo_artifact_rolls["substats"][substat]
                    )
                    new_combinations.append(
                        (
                            tuple(new_combination_rolls),
                            combination[1],
                        )
                    )
                substat_rolls_probabillities_map[substat][num_rolls] = new_combinations

    return substat_rolls_probabillities_map


# Source: https://stackoverflow.com/questions/7748442/generate-all-possible-lists-of-length-n-that-sum-to-s-in-python
def _sums(length, total_sum) -> tuple:
    if length == 1:
        yield (total_sum,)
    else:
        for value in range(total_sum + 1):
            for permutation in _sums(length - 1, total_sum - value):
                yield (value,) + permutation
