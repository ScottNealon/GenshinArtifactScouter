from __future__ import annotations

import copy
import itertools
import logging
import math
import re

import numpy as np
import pandas as pd

from . import evaluate, genshin_data, graphing
from .artifact import Artifact, Circlet, Flower, Goblet, Plume, Sands
from .artifacts import Artifacts
from .character import Character

### CLASSES GENERATED THROUGH PUBLIC METHODS ###


class SlotPotential:
    """Contains the potentials of a slot and the settings used to generate them"""

    def __init__(
        self,
        character: Character,
        equipped_artifacts: Artifacts,
        slot: type,
        set_str: str,
        stars: int,
        main_stat: str,
        target_level: int,
        source: str,
        potential_df: pd.DataFrame,
    ):
        """Initialize slot potentials, called in other functions in file"""
        # Save inputs
        self._character = character
        self._equipped_artifacts = equipped_artifacts
        self._slot = slot
        self._target_level = target_level
        self._set = set_str
        self._stars = stars
        self._main_stat = main_stat
        self._source = source
        self._potential_df = potential_df

    @property
    def character(self) -> Character:
        return self._character

    @property
    def equipped_artifacts(self) -> Artifacts:
        return self._equipped_artifacts

    @property
    def slot(self) -> type:
        return self._slot

    @property
    def target_level(self) -> int:
        return self._target_level

    @property
    def set(self) -> str:
        return self._set

    @property
    def stars(self) -> int:
        return self._stars

    @property
    def main_stat(self) -> str:
        return self._main_stat

    @property
    def source(self) -> str:
        return self._source

    @property
    def potential_df(self) -> pd.DataFrame:
        return self._potential_df

    def log_report(self, base_power: float, log: logging.Logger):
        """Logs slot potential to console"""

        # Extract series
        slot_power = self.potential_df["power"]
        slot_percentile = self.potential_df["probability"]
        # Minimum Power
        min_power = slot_power.min()
        # Maximum Power
        max_power = slot_power.max()
        max_power_increase = 100 * (max_power / min_power - 1)
        # Average Power
        avg_power = slot_power.dot(slot_percentile)
        avg_power_increase = 100 * (avg_power / min_power - 1)
        avg_power_percentile = 100 * slot_percentile[slot_power < avg_power].sum()
        # Base Power
        if base_power is not None:
            base_power_increase = 100 * (base_power / min_power - 1)
            base_power_percentile = 100 * slot_percentile[slot_power < base_power].sum()
        # Log to console
        # fmt: off
        log.info(f"{len(self.potential_df.index):,} different ways to roll condensed substats.")
        log.info(f"Slot Min Power: {min_power:>7,.0f} |  +0.0% |   0.0th Slot Percentile")
        if base_power is not None:
            if base_power < avg_power:
                log.info(f"Base Power:     {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_percentile:>5.1f}{_suffix(base_power_percentile)} Slot Percentile")
        log.info(f"Slot Avg Power: {avg_power:>7,.0f} | {avg_power_increase:>+5.1f}% | {avg_power_percentile:>5.1f}{_suffix(avg_power_percentile)} Slot Percentile")
        if base_power is not None:
            if base_power >= avg_power:
                log.info(f"Base Power:     {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_percentile:>5.1f}{_suffix(base_power_percentile)} Slot Percentile")
        log.info(f"Slot Max Power: {max_power:>7,.0f} | {max_power_increase:>+5.1f}% | 100.0th Slot Percentile")
        # fmt: on

    def match(self, other_potential: SlotPotential):
        return (
            self.character == other_potential.character
            and self.equipped_artifacts == other_potential.equipped_artifacts
            and self.slot == other_potential.slot
            and self.set == other_potential.set
            and self.stars == other_potential.stars
            and self.main_stat == other_potential.main_stat
            and self.target_level == other_potential.target_level
            and self.source == other_potential.source
        )


class ArtifactPotential(SlotPotential):
    """Contains the potentials of an artifact and the settings used to generate them"""

    def __init__(self, substat_rolls: dict[str, int], slot_potential: SlotPotential = None, **kwargs):
        super(ArtifactPotential, self).__init__(**kwargs)
        self._substat_rolls = substat_rolls
        if slot_potential is not None:
            if not self.match(slot_potential):
                raise ValueError("Slot Potential and Artifact Potential do not match")
        self._slot_potential = slot_potential

    @property
    def substat_rolls(self) -> dict[str, int]:
        return self._substat_rolls

    @property
    def slot_potential(self) -> SlotPotential:
        return self._slot_potential

    def find_matching_slot_potential(self, slot_potentials: list[SlotPotential]):
        """Finds first slot potential in list to match properties"""
        for slot_potential in slot_potentials:
            if slot_potential.match(self):
                self._slot_potential = slot_potential
                return

    def log_report(self, base_power: float, log: logging.Logger):
        """Logs artifact potential to console"""

        # Number of artifacts
        num_artifacts = len(self.potential_df.index)
        log.info(f"{num_artifacts:,} different ways to roll condensed substats.")

        # Extract series
        artifact_power = self.potential_df["power"]
        artifact_percentile = self.potential_df["probability"]
        # Minimum Artifact Power
        artifact_min_power = artifact_power.min()
        # Average Artifact Power
        artifact_avg_power = artifact_power.dot(artifact_percentile)
        if num_artifacts > 1:
            avg_power_artifact_percentile = 100 * artifact_percentile[artifact_power < artifact_avg_power].sum()
        else:
            avg_power_artifact_percentile = 50.0
        # Maximum Artifact Power
        artifact_max_power = artifact_power.max()
        # Base Power
        if base_power is not None:
            base_power_artifact_percentile = 100 * artifact_percentile[artifact_power < base_power].sum()

        # Get slot
        if self.slot_potential is not None:
            slot_power = self.slot_potential.potential_df["power"]
            slot_percentile = self.slot_potential.potential_df["probability"]
            slot_min_power = slot_power.min()
            slot_max_power = slot_power.max()
            slot_max_power_increase = 100 * (slot_max_power / slot_min_power - 1)
            # Minimum Artifact Power
            min_power_increase = 100 * (artifact_min_power / slot_min_power - 1)
            min_power_slot_percentile = 100 * slot_percentile[slot_power < artifact_min_power].sum()
            # Average Artifact Power
            avg_power_increase = 100 * (artifact_avg_power / slot_min_power - 1)
            avg_power_slot_percentile = 100 * slot_percentile[slot_power < artifact_avg_power].sum()
            # Maximum Artifact Power
            max_power_increase = 100 * (artifact_max_power / slot_min_power - 1)
            max_power_slot_percentile = 100 * slot_percentile[slot_power < artifact_max_power].sum()
            # Base Power
            if base_power is not None:
                base_power_increase = 100 * (base_power / slot_min_power - 1)
                base_power_slot_percentile = 100 * slot_percentile[slot_power < base_power].sum()
            # Log to console
            # fmt: off
            if num_artifacts > 1:
                log.info(f"Artifact Min Power: {artifact_min_power:>7,.0f} | {min_power_increase:>+5.1f}% |   0.0th Artifact Percentile | {min_power_slot_percentile:>5.1f}{_suffix(min_power_slot_percentile)} Slot Percentile")
            if base_power is not None:
                if base_power < artifact_avg_power:
                    log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile")
            log.info(f"Artifact Avg Power: {artifact_avg_power:>7,.0f} | {avg_power_increase:>+5.1f}% | {avg_power_artifact_percentile:>5.1f}{_suffix(avg_power_artifact_percentile)} Artifact Percentile | {avg_power_slot_percentile:>5.1f}{_suffix(avg_power_slot_percentile)} Slot Percentile")
            if base_power is not None:
                if artifact_avg_power <= base_power < artifact_max_power:
                    log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile")
            if num_artifacts > 1:
                log.info(f"Artifact Max Power: {artifact_max_power:>7,.0f} | {max_power_increase:>+5.1f}% | 100.0th Artifact Percentile | {max_power_slot_percentile:>5.1f}{_suffix(max_power_slot_percentile)} Slot Percentile")
            if base_power is not None:
                if base_power >= artifact_max_power:
                    log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile")
            log.info(f"Slot Max Power:     {slot_max_power:>7,.0f} | {slot_max_power_increase:>+5.1f}% | 100.0th Artifact Percentile | 100.0th Slot Percentile")
            # fmt: on
        else:
            log.info(
                "(No slot potential found. Run slot_potential() or all_slots_potentials() with matching parameters.)"
            )
            if (
                self.set != self.equipped_artifacts.get_artifact(self.slot).set
            ) and self.equipped_artifacts.use_set_bonus:
                log.info(
                    "(Equipped artifact has different set than evaluating artifact. Base power may be naturally higher. Consider using equipped_artifacts.use_set_bonus = False)"
                )
            avg_power_increase = 100 * (artifact_avg_power / artifact_min_power - 1)
            max_power_increase = 100 * (artifact_max_power / artifact_min_power - 1)
            # Base Power
            if base_power is not None:
                base_power_increase = 100 * (base_power / artifact_min_power - 1)
            # Log to console
            # fmt: off
            if base_power is not None:
                if base_power < artifact_min_power:
                    log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile")
            if num_artifacts > 0:
                log.info(f"Artifact Min Power: {artifact_min_power:>7,.0f} |  +0.0% |   0.0th Artifact Percentile")
            if base_power is not None:
                if artifact_min_power <= base_power < artifact_avg_power:
                    log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile")
            log.info(f"Artifact Avg Power: {artifact_avg_power:>7,.0f} | {avg_power_increase:>+5.1f}% | {avg_power_artifact_percentile:>5.1f}{_suffix(avg_power_artifact_percentile)} Artifact Percentile")
            if base_power is not None:
                if artifact_avg_power <= base_power < artifact_max_power:
                    log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile")
            if num_artifacts > 0:
                log.info(f"Artifact Max Power: {artifact_max_power:>7,.0f} | {max_power_increase:>+5.1f}% | 100.0th Artifact Percentile")
            if base_power is not None:
                if  base_power >= artifact_max_power:
                    log.info(f"Base Power:         {base_power:>7,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile")
            # fmt: on


def _suffix(value: float) -> str:
    suffix = ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"]
    mod_value = round(10 * value) % 10
    return suffix[mod_value]


### PUBLIC METHODS TO CREATE SLOT POTENTIAL OBJECTS ###


def all_slots_potentials(
    character: Character,
    equipped_artifacts: Artifacts,
    target_level: int = None,
    source: str = None,
    verbose: bool = True,
    plot: bool = False,
    smooth: bool = True,
) -> list[SlotPotential]:
    """Calculates the slot potential for all slots

    Parameters
    ----------
    character : Character
        Character to evaluate artifacts on
    equipped_artifacts : Artifacts
        Source of set, stars, and main stat for evaluating slots. Will be equipped on character when evaluating other
        slots
    target_level : int, default=None,
        Artifact level to evaluate to. If not supplied, defaults to max level.
    source : str, default=None,
        Source of artifacts. Different sources have different low vs high substat drop rates. Default defined by set in
        genshin_data.py.
    verbose : bool, default=True
        Booleon whether to output updates to console
    TODO
    plot : bool, default=False

    Returns
    ----------
    list[SlotPotential]
        List containing the slot potentials for each possible slot based on provided evaluation criteria
    """

    # Set verbosity
    log = logging.getLogger(__name__)
    if verbose:
        log.setLevel("INFO")
    else:
        log.setLevel("WARNING")

    # Validate inputs
    # Source must be a valid source
    if source is not None and source not in genshin_data.extra_substat_probability:
        raise ValueError("Invalid domain name.")
    # Target level must be a valid target level
    if target_level is not None:
        if target_level < 0:
            raise ValueError("Target level cannot be less than 0.")
        elif target_level > 20:
            raise ValueError("Target level cannot be greater than 20.")

    # Calculate base power
    base_power = evaluate.evaluate_power(character=character, artifacts=equipped_artifacts)

    # Log intro
    # fmt: off
    log.info("-" * 110)
    log.info("Evaluating potential of all artifacts...")
    log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
    log.info(f"WEAPON: {character.weapon.name_formated.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
    if character.amplifying_reaction is not None:
        log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)")
    log.info(f"EQUIPPED ARTIFACTS:                                       HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%")
    for artifact in equipped_artifacts:
        log.info(f"{artifact.to_string_table()}")
    if not equipped_artifacts.use_set_bonus:
        log.info("Set Bonuses Off")
    log.info(f"BASE POWER: {base_power:,.0f}")
    # fmt: on

    # Iterate through artifacts
    slot_potentials = list[SlotPotential]()
    for slot in [Flower, Plume, Sands, Goblet, Circlet]:
        base_artifact = equipped_artifacts.get_artifact(slot)
        if base_artifact is None:
            log.warning(f"Artifacts does not contain a {slot.__name__}")
        else:
            # Default target_level
            iter_target_level = (
                genshin_data.max_level_by_stars[base_artifact.stars] if target_level is None else target_level
            )
            # Default source
            iter_source = genshin_data.default_artifact_source[base_artifact.set] if source is None else source
            # Log artifact
            log.info("-" * 10)
            log.info(f"Evaluating {slot.__name__} slot potential...")
            log.info("ARTIFACT:")
            log.info(
                (
                    f"{slot.__name__.title():>7s} "
                    f"{base_artifact.stars:>d}* "
                    f"{base_artifact.set.title():>14} "
                    f"{iter_target_level:>2d}/{genshin_data.max_level_by_stars[base_artifact.stars]:>2d} "
                    f"{base_artifact.main_stat:>17s}: {genshin_data.main_stat_scaling[base_artifact.stars][base_artifact.main_stat][iter_target_level]:>4}"
                )
            )
            # Calculate potential
            potential_df = _individual_potential(
                character=character,
                equipped_artifacts=equipped_artifacts,
                slot=slot,
                set_str=base_artifact.set,
                stars=base_artifact.stars,
                main_stat=base_artifact.main_stat,
                target_level=iter_target_level,
                source=iter_source,
            )
            slot_potential = SlotPotential(
                character=character,
                equipped_artifacts=equipped_artifacts,
                slot=slot,
                set_str=base_artifact.set,
                stars=base_artifact.stars,
                main_stat=base_artifact.main_stat,
                target_level=iter_target_level,
                source=iter_source,
                potential_df=potential_df,
            )
            # Report on potential
            slot_potential.log_report(base_power=base_power, log=log)
            # Append to return
            slot_potentials.append(slot_potential)
    if plot:
        log.info("-" * 10)
        log.info("Plotting slots...")
        legend_label = ["Flower", "Plume", "Sands", "Goblet", "Circlet"]
        title = f"Slot Potentials on {character.name.title()}"
        graphing.graph_slot_potentials(
            slot_potentials=slot_potentials,
            legend_labels=legend_label,
            base_power=base_power,
            title=title,
            smooth=smooth,
        )
        log.info("Slots plotted.")
    return slot_potentials


def slot_potential(
    character: Character,
    equipped_artifacts: Artifacts,
    slot: type,
    set_str: str = None,
    stars: int = None,
    main_stat: str = None,
    target_level: int = None,
    source: str = None,
    verbose: bool = True,
    plot: bool = False,
    smooth: bool = True,
) -> list[SlotPotential]:
    """Calculates the probabillity and power of all possible substats for a single slots

    Parameters
    ----------
    character : Character
        Character to evaluate artifacts on
    equipped_artifacts : Artifacts
        Artifacts to equip character with if not in slot
    slot : type
        Base artifact slot.
    set_str : str, default=None
        Base artifact set. If not supplied, defaults to set of artifact in slot in equipped_artifacts.
    stars : int, default=None
        Base artifact number of stars. If not supplied, defaults to stars of artifact in slot in equipped_artifacts.
    main_stat : str, default=None,
        Base artifact main stat. If not supplied, defaults to main stat of artifact in slot in equipped_artifacts.
    target_level : int, default=None,
        Artifact level to evaluate to. If not supplied, defaults to maximum give artifact stars.
    source : str, default=None,
        Source of artifacts. Different sources have different low vs high substat drop rates. Default defined by set in
        genshin_data.py.
    verbose : bool, default=True
        Booleon whether to output updates to console
    TODO
    plot : bool, default=False

    Returns
    ----------
    list[SlotPotential]
        List containing the singular slot potential for slot based on provided evaluation criteria
    """

    # Set verbosity
    log = logging.getLogger(__name__)
    if verbose:
        log.setLevel("INFO")
    else:
        log.setLevel("WARNING")

    # Default inputs to artifact in slot
    base_artifact = equipped_artifacts.get_artifact(slot)
    if (set_str is None) or (stars is None) or (main_stat is None):
        if base_artifact is None:
            raise ValueError(
                f"Either artifacts must contain a {slot.__name__} or {slot.__name__} parameters are provided to evaluate slot."
            )
    set_str = base_artifact.set if set_str is None else set_str
    stars = base_artifact.stars if stars is None else stars
    main_stat = base_artifact.main_stat if main_stat is None else main_stat

    # Validate inputs
    # Source must be a valid source
    if source is not None and source not in genshin_data.extra_substat_probability:
        raise ValueError("Invalid domain name.")
    # Target level must be a valid target level
    if target_level is not None:
        if target_level < 0:
            raise ValueError("Target level cannot be less than 0.")
        elif target_level > 20:
            raise ValueError("Target level cannot be greater than 20.")
    else:
        # Default target level to maximum
        target_level = genshin_data.max_level_by_stars[stars]
    # Default source
    if source is None:
        source = genshin_data.default_artifact_source[set_str]

    # Calculate base power
    base_power = evaluate.evaluate_power(character=character, artifacts=equipped_artifacts)

    # Log intro
    # fmt: off
    log.info("-" * 110)
    log.info(f"Evaluating potential of {slot.__name__} slot...")
    log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
    log.info(f"WEAPON: {character.weapon.name_formated.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
    if character.amplifying_reaction is not None:
        log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)")
    log.info("ARTIFACT:")
    log.info((
            f"{slot.__name__.title():>7s} "
            f"{stars:>d}* "
            f"{set_str.title():>14} "
            f"{target_level:>2d}/{genshin_data.max_level_by_stars[stars]:>2d} "
            f"{main_stat:>17s}: {genshin_data.main_stat_scaling[stars][main_stat][target_level]:>4}"
    ))
    log.info(f"EQUIPPED ARTIFACTS:                                       HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%")
    for equipped_artifact in equipped_artifacts:
        if type(equipped_artifact) is not slot:
            log.info(f"{equipped_artifact.to_string_table()}")
    if not equipped_artifacts.use_set_bonus:
        log.info("Set Bonuses Off")
    log.info(f"BASE POWER: {base_power:,.0f}")
    # fmt: on

    # Evaluate single slot
    potential_df = _individual_potential(
        character=character,
        equipped_artifacts=equipped_artifacts,
        slot=slot,
        set_str=set_str,
        stars=stars,
        main_stat=main_stat,
        target_level=target_level,
        source=source,
    )
    slot_potentials = [
        SlotPotential(
            character=character,
            equipped_artifacts=equipped_artifacts,
            slot=slot,
            set_str=set_str,
            stars=stars,
            main_stat=main_stat,
            target_level=target_level,
            source=source,
            potential_df=potential_df,
        )
    ]
    # Report potential
    slot_potentials[0].log_report(base_power=base_power, log=log)
    if plot:
        log.info("-" * 10)
        log.info("Plotting slot...")
        legend_label = [slot.__name__]
        title = f"{stars}* {set_str.title()} {main_stat} {slot.__name__} Slot Potential on {character.name.title()}"
        graphing.graph_slot_potentials(
            slot_potentials=slot_potentials,
            legend_labels=legend_label,
            base_power=base_power,
            title=title,
            smooth=smooth,
        )
        log.info("Slot plotted.")
    # Return results
    return slot_potentials


### PUBLIC METHODS TO CREATE ARTIFACT POTENTIAL OBJECTS ###


def artifacts_potentials(
    character: Character,
    equipped_artifacts: Artifacts,
    evaluating_artifacts: dict[str],
    target_level: int = None,
    source: str = None,
    slot_potentials: list[SlotPotential] = None,
    verbose: bool = True,
    plot: bool = False,
    smooth: bool = True,
) -> list[ArtifactPotential]:
    """Calculates the probabillity and power of all possible substats for the artifacts

    Parameters
    ----------
    character : Character
        Character to evaluate artifacts on
    equipped_artifacts : Artifacts
        Artifacts to equip character with if not in slot
    evaluating_artifacts : dict[str]
        Dictionary of artifacts to evaluate substats for, keyed to "name" of artifact
    target_level : int, default=None,
        Artifact level to evaluate to. If not supplied, defaults to maximum give artifact stars.
    source : str, default=None,
        Source of artifacts. Different sources have different low vs high substat drop rates. Default defined by set in
        genshin_data.py.
    slot_potentials : list[SlotPotential], default=None
        List of slot potentials that MAY contain a match for current parameters
    verbose : bool, default=True
        Booleon whether to output updates to console

    Returns
    ----------
    list[ArtifactPotential]
       List containing the artifact potentials for each provided artifact based on provided evaluation criteria
    """

    # Set verbosity
    log = logging.getLogger(__name__)
    if verbose:
        log.setLevel("INFO")
    else:
        log.setLevel("WARNING")

    # Validate inputs
    # Source must be a valid source
    if source is not None and source not in genshin_data.extra_substat_probability:
        raise ValueError("Invalid domain name.")
    # Target level must be a valid target level
    if target_level is not None:
        if target_level < 0:
            raise ValueError("Target level cannot be less than 0.")
        elif target_level > 20:
            raise ValueError("Target level cannot be greater than 20.")

    # Calculate base power
    base_power = evaluate.evaluate_power(character=character, artifacts=equipped_artifacts)

    # Log intro
    # fmt: off
    log.info("-" * 110)
    log.info("Evaluating potential of artifacts...")
    log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
    log.info(f"WEAPON: {character.weapon.name.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
    if character.amplifying_reaction is not None:
        log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)")
    log.info(f"EQUIPPED ARTIFACTS:                                       HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%")
    for artifact in equipped_artifacts:
        log.info(f"{artifact.to_string_table()}")
    if not equipped_artifacts.use_set_bonus:
        log.info("Set Bonuses Off")
    log.info(f"BASE POWER: {base_power:,.0f}")
    # fmt: on

    # Iterate through artifacts
    artifact_potentials = []
    for artifact_name, base_artifact in evaluating_artifacts.items():
        # Default target_level
        iter_target_level = (
            genshin_data.max_level_by_stars[base_artifact.stars] if target_level is None else target_level
        )
        # Default source
        iter_source = genshin_data.default_artifact_source[base_artifact.set] if source is None else source
        # Log artifact
        log.info("-" * 10)
        log.info(f"Evaluating {artifact_name} potential...")
        log.info(
            f"ARTIFACT:                                                 HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
        )
        log.info(f"{base_artifact.to_string_table()}")
        # Calculate potential
        potential_df = _individual_potential(
            character=character,
            equipped_artifacts=equipped_artifacts,
            slot=type(base_artifact),
            set_str=base_artifact.set,
            stars=base_artifact.stars,
            main_stat=base_artifact.main_stat,
            target_level=iter_target_level,
            substat_rolls=base_artifact.substat_rolls,
            source=iter_source,
        )
        # Create and report artifact potential
        artifact_potential = ArtifactPotential(
            character=character,
            equipped_artifacts=equipped_artifacts,
            slot=type(base_artifact),
            set_str=base_artifact.set,
            stars=base_artifact.stars,
            main_stat=base_artifact.main_stat,
            target_level=iter_target_level,
            substat_rolls=base_artifact.substat_rolls,
            source=iter_source,
            potential_df=potential_df,
        )
        artifact_potential.find_matching_slot_potential(slot_potentials=slot_potentials)
        artifact_potential.log_report(base_power=base_power, log=log)
        # Append to return
        artifact_potentials.append(artifact_potential)

    if plot:
        log.info("-" * 10)
        log.info("Plotting artifacts...")
        artifact_labels = list(evaluating_artifacts.keys())
        graphing.graph_artifact_potentials(
            artifact_potentials=artifact_potentials,
            artifact_labels=artifact_labels,
            base_power=base_power,
            smooth=smooth,
        )
        log.info("Slot plotted.")
    return artifact_potentials


def artifact_potential(
    character: Character,
    equipped_artifacts: Artifacts,
    evaluating_artifact: Artifact,
    target_level: int = None,
    source: str = None,
    slot_potentials: list[SlotPotential] = None,
    verbose: bool = True,
    plot: bool = False,
    artifact_name: str = None,
    smooth: bool = True,
) -> list[ArtifactPotential]:
    """Calculates the probabillity and power of all possible substats rolls for a given artifact

    Parameters
    ----------
    character : Character
        Character to evaluate artifacts on
    equipped_artifacts : Artifacts
        Artifacts to equip character with if not in slot
    evaluating_artifact : Artifact
       Artifacts to evaluate substats for
    target_level : int, default=None,
        Artifact level to evaluate to. If not supplied, defaults to maximum give artifact stars.
    source : str, default=None,
        Source of artifacts. Different sources have different low vs high substat drop rates. Default defined by set in
        genshin_data.py.
    slot_potentials : list[SlotPotential], default=None
        List of slot potentials that MAY contain a match for current parameters
    verbose : bool, default=True
        Booleon whether to output updates to console

    Returns
    ----------
    list[ArtifactPotential]
       List containing singular artifact potentials for artifact based on provided evaluation criteria
    """

    # Set verbosity
    log = logging.getLogger(__name__)
    if verbose:
        log.setLevel("INFO")
    else:
        log.setLevel("WARNING")

    # Validate inputs
    # Source must be a valid source
    if source is not None and source not in genshin_data.extra_substat_probability:
        raise ValueError("Invalid domain name.")
    # Target level must be a valid target level
    if target_level is not None:
        if target_level < 0:
            raise ValueError("Target level cannot be less than 0.")
        elif target_level > 20:
            raise ValueError("Target level cannot be greater than 20.")
    else:
        # Default target level to maximum
        target_level = genshin_data.max_level_by_stars[evaluating_artifact.stars]
    # Default source
    if source is None:
        source = genshin_data.default_artifact_source[evaluating_artifact.set]

    # Calculate base power
    base_power = evaluate.evaluate_power(character=character, artifacts=equipped_artifacts)

    # Log intro
    # fmt: off
    log.info("-" * 110)
    log.info(f"Evaluating potential of single artifact...")
    log.info(f"CHARACTER: {character.name.title()}, {character.level}/{[20, 40, 50, 60, 70, 80, 90][character.ascension]}")
    log.info(f"WEAPON: {character.weapon.name_formated.title()}, {character.weapon.level}/{[20, 40, 50, 60, 70, 80, 90][character.weapon.ascension]}")
    if character.amplifying_reaction is not None:
        log.info(f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({character.reaction_percentage::>.0f}%)")
    log.info(f"ARTIFACT:                                                 HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%")
    log.info(f"{evaluating_artifact.to_string_table()}")
    log.info(f"EQUIPPED ARTIFACTS:")
    for equipped_artifact in equipped_artifacts:
        if type(equipped_artifact) is not type(evaluating_artifact):
            log.info(f"{equipped_artifact.to_string_table()}")
    if not equipped_artifacts.use_set_bonus:
        log.info("Set Bonuses Off")
    log.info(f"BASE POWER: {base_power:,.0f}")
    # fmt:on

    # Evaluate single artifact
    potential_df = _individual_potential(
        character=character,
        equipped_artifacts=equipped_artifacts,
        slot=type(evaluating_artifact),
        set_str=evaluating_artifact.set,
        stars=evaluating_artifact.stars,
        main_stat=evaluating_artifact.main_stat,
        target_level=target_level,
        substat_rolls=evaluating_artifact.substat_rolls,
        source=source,
    )
    # Create and report artifact potential
    artifact_potentials = [
        ArtifactPotential(
            character=character,
            equipped_artifacts=equipped_artifacts,
            slot=type(evaluating_artifact),
            set_str=evaluating_artifact.set,
            stars=evaluating_artifact.stars,
            main_stat=evaluating_artifact.main_stat,
            target_level=target_level,
            substat_rolls=evaluating_artifact.substat_rolls,
            source=source,
            potential_df=potential_df,
        )
    ]
    artifact_potentials[0].find_matching_slot_potential(slot_potentials=slot_potentials)
    artifact_potentials[0].log_report(base_power=base_power, log=log)
    if plot:
        log.info("-" * 10)
        log.info("Plotting artifact...")
        if artifact_name is not None:
            artifact_labels = [artifact_name]
        else:
            artifact_labels = [type(evaluating_artifact).__name__]
        graphing.graph_artifact_potentials(
            artifact_potentials=artifact_potentials,
            artifact_labels=artifact_labels,
            base_power=base_power,
            smooth=smooth,
        )
        log.info("Slot plotted.")
    return artifact_potentials


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
        existing_increases = sum([len(rolls) for substat, rolls in substat_rolls.items()]) - existing_unlocks
    else:
        existing_increases = 0
    remaining_unlocks = min(4, max(0, stars - 2) + math.floor(target_level / 4)) - existing_unlocks
    remaining_increases = (
        max(0, stars - 2) + math.floor(target_level / 4) - existing_unlocks - remaining_unlocks - existing_increases
    )
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
    artifact = slot(set_str=set_str, main_stat=main_stat, stars=stars, level=target_level, substats=substat_values_df)

    # Create artifact list, replacing previous artifact
    other_artifacts_list = [other_artifact for other_artifact in equipped_artifacts if type(other_artifact) != slot]
    other_artifacts_list.append(artifact)
    other_artifacts = Artifacts(other_artifacts_list, use_set_bonus=equipped_artifacts.use_set_bonus)

    # Calculate stats and power
    stats = evaluate.evaluate_stats(character=character, artifacts=other_artifacts)
    power = evaluate.evaluate_power(character=character, stats=stats, probability=slot_potential_df["probability"])

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

    # Convert pseudo artifacts by calculating roll values
    substat_values_df, pseudo_artifacts_df = _calculate_substats(
        pseudo_artifacts=pseudo_artifacts,
        character=character,
        stars=stars,
        seed_pseudo_artifact_rolls=seed_pseudo_artifact_rolls,
    )

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
    condensable_substats = _condensable_substats(character=character)
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
    condensable_substats = _condensable_substats(character=character)

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


def _condensable_substats(character: Character):

    # TODO Include this on a character by character basis

    # Create list of condensable stats
    if character.scaling_stat == "ATK":
        condensable_substats = ["DEF", "DEF%", "HP", "HP%", "Energy Recharge%"]
    elif character.scaling_stat == "DEF":
        condensable_substats = ["ATK", "ATK%", "HP", "HP%", "Energy Recharge%"]
    elif character.scaling_stat == "HP":
        condensable_substats = ["ATK", "ATK%", "DEF", "DEF%", "Energy Recharge%"]
    if character.amplifying_reaction is None:
        condensable_substats.append("Elemental Mastery")
    if character.crits == "always":
        condensable_substats.append("Crit Rate%")
    elif character.crits == "never":
        condensable_substats.append("Crit Rate%")
        condensable_substats.append("Crit DMG%")

    return condensable_substats


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
