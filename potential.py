import copy
import itertools
import logging
import math

import numpy as np
import pandas as pd

import evaluate
import genshindata
from artifact import Artifact, Circlet, Flower, Goblet, Plume, Sands
from artifacts import Artifacts
from character import Character


def all_slots_substats_potentials(
    character: Character,
    equipped_artifacts: Artifacts,
    target_level: int = None,
    source: str = None,
    base_power: float = None,
    verbose: bool = False,
) -> dict[type]:
    """Calculates the probabillity and power of all possible substats for all slots

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
        genshindata.py.
    base_power: float, default=None
        Baseline power to compare artifact potential to
    verbose : bool, default=False
        Booleon whether to output updates to console

    Returns
    ----------
    dict[type] = pd.Dataframe
        Dictionary of substat potential dataframes indexed by slot and main stat. Dataframe contains stats,
        probabillity, and power of every potential substat outcome for every slot and main stat combination provided.
    """

    # Set verbosity
    log = logging.getLogger(__name__)
    if verbose:
        log.setLevel("INFO")
    else:
        log.setLevel("WARNING")

    # Validate inputs
    # Source must be a valid source
    if source is not None and source not in genshindata.extra_substat_probability:
        raise ValueError("Invalid domain name.")
    # Target level must be a valid target level
    if target_level is not None:
        if target_level < 0:
            raise ValueError("Target level cannot be less than 0.")
        elif target_level > 20:
            raise ValueError("Target level cannot be greater than 20.")

    # Log intro
    log.info("-" * 120)
    log.info("Evaluating substat potential of all artifacts...")
    log.info(f"CHARACTER: {character.name.title()}")
    if character.amplifying_reaction is not None:
        log.info(
            f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({100 * character.reaction_percentage::>.0f}%)"
        )
    log.info(
        f"EQUIPPED ARTIFACTS:                                       HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
    )
    for artifact in equipped_artifacts:
        log.info(f"{artifact.to_string_table()}")

    # Iterate through artifacts
    substat_potentials = {}
    for slot in [Flower, Plume, Sands, Goblet, Circlet]:
        substat_potentials[slot] = {}
        base_artifact = equipped_artifacts.get_artifact(slot)
        if base_artifact is None:
            log.warning(f"Artifacts does not contain a {slot.__name__}")
        else:
            # Default target_level
            iter_target_level = (
                genshindata.max_level_by_stars[base_artifact.stars] if target_level is None else target_level
            )
            # Default source
            iter_source = genshindata.default_artifact_source[base_artifact.set] if source is None else source
            # Log artifact
            log.info("-" * 10)
            log.info(f"Evaluating {slot.__name__} slot potential...")
            log.info("ARTIFACT:")
            log.info(
                (
                    f"{slot._slot.capitalize():>7s} "
                    f"{base_artifact.stars:>d}* "
                    f"{base_artifact.set.capitalize():>14} "
                    f"{iter_target_level:>2d}/{genshindata.max_level_by_stars[base_artifact.stars]:>2d} "
                    f"{base_artifact.main_stat:>17s}: {genshindata.main_stat_scaling[base_artifact.stars][base_artifact.main_stat][iter_target_level]:>4}"
                )
            )
            # Calculate potential
            substat_potential_df = _individual_slot_potential(
                character=character,
                equipped_artifacts=equipped_artifacts,
                slot=slot,
                set_str=base_artifact.set,
                stars=base_artifact.stars,
                main_stat=base_artifact.main_stat,
                target_level=iter_target_level,
                source=iter_source,
            )
            log.info(f"{len(substat_potential_df.index):,} different ways to roll condensed substats.")
            # TODO Report on potential
            substat_potentials[type(base_artifact)][base_artifact.main_stat] = substat_potential_df

    return substat_potentials


def slot_substat_potentials(
    character: Character,
    equipped_artifacts: Artifacts,
    slot: type,
    set_str: str = None,
    stars: int = None,
    main_stat: str = None,
    target_level: int = None,
    source: str = None,
    base_power: float = None,
    verbose: bool = False,
) -> pd.DataFrame:
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
        genshindata.py.
    base_power: float, default=None
        Baseline power to compare artifact potential to
    verbose : bool, default=False
        Booleon whether to output updates to console

    Returns
    ----------
    pd.Dataframe
        Dataframe containing stats, probabillity, and power of every potential substat outcome for the given slot
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
        else:
            set_str = base_artifact.set if set_str is None else set_str
            stars = base_artifact.stars if stars is None else stars
            main_stat = base_artifact.main_stat if main_stat is None else main_stat

    # Validate inputs
    # Source must be a valid source
    if source is not None and source not in genshindata.extra_substat_probability:
        raise ValueError("Invalid domain name.")
    # Target level must be a valid target level
    if target_level is not None:
        if target_level < 0:
            raise ValueError("Target level cannot be less than 0.")
        elif target_level > 20:
            raise ValueError("Target level cannot be greater than 20.")
    else:
        # Default target level to maximum
        target_level = genshindata.max_level_by_stars[stars]
    # Default source
    if source is None:
        source = genshindata.default_artifact_source[set_str]

    # Log intro
    log.info("-" * 120)
    log.info(f"Evaluating substat potential of {slot.__name__} slot...")
    log.info(f"CHARACTER: {character.name.title()}")
    if character.amplifying_reaction is not None:
        log.info(
            f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({100 * character.reaction_percentage::>.0f}%)"
        )
    log.info("ARTIFACT:")
    log.info(
        (
            f"{slot._slot.capitalize():>7s} "
            f"{base_artifact.stars:>d}* "
            f"{base_artifact.set.capitalize():>14} "
            f"{target_level:>2d}/{genshindata.max_level_by_stars[base_artifact.stars]:>2d} "
            f"{base_artifact.main_stat:>17s}: {genshindata.main_stat_scaling[base_artifact.stars][base_artifact.main_stat][target_level]:>4}"
        )
    )
    log.info(
        f"EQUIPPED ARTIFACTS:                                       HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
    )
    for equipped_artifact in equipped_artifacts:
        if type(equipped_artifact) is not slot:
            log.info(f"{equipped_artifact.to_string_table()}")

    # Evaluate single slot
    substat_potential_df = _individual_slot_potential(
        character=character,
        equipped_artifacts=equipped_artifacts,
        slot=slot,
        set_str=set_str,
        stars=stars,
        main_stat=main_stat,
        target_level=target_level,
        source=source,
    )
    log.info(f"{len(substat_potential_df.index):,} different ways to roll condensed substats.")

    # TODO Report on potential

    return substat_potential_df


def artifacts_substat_potentials(
    character: Character,
    equipped_artifacts: Artifacts,
    evaluating_artifacts: dict[str],
    target_level: int = None,
    source: str = None,
    slot_substat_potentials: dict[type] = None,
    base_power: float = None,
    verbose: bool = False,
):
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
        genshindata.py.
    slot_substat_potentials : dict[type], default=None
        Dictionary of substat potential dataframes indexed by slot and main stat. Dataframe contains stats,
        probabillity, and power of every potential substat outcome for every slot and main stat combination provided.
        Used as a baseline for comparing the potential of the artifact.
    base_power: float, default=None
        Baseline power to compare artifact potential to
    verbose : bool, default=False
        Booleon whether to output updates to console

    Returns
    ----------
    dict[str] = pd.Dataframe
        Dictionary of dataframe containing stats, probabillity, and power of every potential substat outcome for the
        artifacts, keyed to the names of
    """

    # Set verbosity
    log = logging.getLogger(__name__)
    if verbose:
        log.setLevel("INFO")
    else:
        log.setLevel("WARNING")

    # Validate inputs
    # Source must be a valid source
    if source is not None and source not in genshindata.extra_substat_probability:
        raise ValueError("Invalid domain name.")
    # Target level must be a valid target level
    if target_level is not None:
        if target_level < 0:
            raise ValueError("Target level cannot be less than 0.")
        elif target_level > 20:
            raise ValueError("Target level cannot be greater than 20.")

    # Log intro
    log.info("-" * 120)
    log.info("Evaluating substat potential of artifacts...")
    log.info(f"CHARACTER: {character.name.title()}")
    if character.amplifying_reaction is not None:
        log.info(
            f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({100 * character.reaction_percentage::>.0f}%)"
        )
    log.info(
        f"EQUIPPED ARTIFACTS:                                       HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
    )
    for artifact in equipped_artifacts:
        log.info(f"{artifact.to_string_table()}")

    # Iterate through artifacts
    substat_potentials = {}
    for artifact_name, base_artifact in evaluating_artifacts.items():
        # Default target_level
        iter_target_level = (
            genshindata.max_level_by_stars[base_artifact.stars] if target_level is None else target_level
        )
        # Default source
        iter_source = genshindata.default_artifact_source[base_artifact.set] if source is None else source
        # Log artifact
        log.info("-" * 10)
        log.info(f"Evaluating {artifact_name} potential...")
        log.info(
            f"ARTIFACT:                                                 HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
        )
        log.info(f"{artifact.to_string_table()}")
        # Calculate potential
        substat_potential_df = _individual_slot_potential(
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
        log.info(f"{len(substat_potential_df.index):,} different ways to roll condensed substats.")
        # TODO Report on potential
        equipped_artifact_set = equipped_artifacts.get_artifact(type(base_artifact)).set
        if (base_artifact.set != equipped_artifact_set) and equipped_artifacts.use_set_bonus:
            log.warn(
                f"Evaluating artifact set ({base_artifact.set}) is different from equipped artifact set ({equipped_artifact_set})."
            )
            log.warn(
                f"This may interfere with comparing artifact potentials. Consider evaluating slot with correct set or turn artifacts.use_set_bonus = False"
            )
        substat_potentials[artifact_name] = substat_potential_df

    return substat_potentials


def artifact_substat_potential(
    character: Character,
    equipped_artifacts: Artifacts,
    evaluating_artifact: Artifact,
    target_level: int = None,
    source: str = None,
    slot_substat_potentials: dict[type] = None,
    base_power: float = None,
    verbose: bool = False,
) -> pd.DataFrame:
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
        genshindata.py.
    slot_substat_potentials : pd.Dataframe, default=None
        Dataframe containing stats, probabillity, and power of every potential substat outcome for the slot of artifact.
        Used as a baseline for comparing the potential of the artifact.
    base_power: float, default=None
        Baseline power to compare artifact potential to
    verbose : bool, default=False
        Booleon whether to output updates to console

    Returns
    ----------
    pd.Dataframe
        Dataframe containing stats, probabillity, and power of every potential substat outcome for the given slot
    """

    # Set verbosity
    log = logging.getLogger(__name__)
    if verbose:
        log.setLevel("INFO")
    else:
        log.setLevel("WARNING")

    # Validate inputs
    # Source must be a valid source
    if source is not None and source not in genshindata.extra_substat_probability:
        raise ValueError("Invalid domain name.")
    # Target level must be a valid target level
    if target_level is not None:
        if target_level < 0:
            raise ValueError("Target level cannot be less than 0.")
        elif target_level > 20:
            raise ValueError("Target level cannot be greater than 20.")
    else:
        # Default target level to maximum
        target_level = genshindata.max_level_by_stars[evaluating_artifact.stars]
    # Default source
    if source is None:
        source = genshindata.default_artifact_source[evaluating_artifact.set]

    # Log intro
    log.info("-" * 120)
    log.info(f"Evaluating substat potential of single artifact...")
    log.info(f"CHARACTER: {character.name.title()}")
    if character.amplifying_reaction is not None:
        log.info(
            f"TRANSFORMATIVE REACTION: {character.amplifying_reaction.replace('_', ' ').title()} ({100 * character.reaction_percentage::>.0f}%)"
        )
    log.info(
        f"ARTIFACT:                                                 HP  ATK  DEF  HP% ATK% DEF%   EM  ER%  CR%  CD%"
    )
    log.info(f"{evaluating_artifact.to_string_table()}")
    log.info(f"EQUIPPED ARTIFACTS:")
    for equipped_artifact in equipped_artifacts:
        if type(equipped_artifact) is not type(evaluating_artifact):
            log.info(f"{equipped_artifact.to_string_table()}")

    # Evaluate single slot
    substat_potential_df = _individual_slot_potential(
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
    log.info(f"{len(substat_potential_df.index):,} different ways to roll condensed substats.")

    # TODO Report on potential
    equipped_artifact_set = equipped_artifacts.get_artifact(type(evaluating_artifact)).set
    if evaluating_artifact.set != equipped_artifact_set and equipped_artifacts.use_set_bonus:
        log.warn(
            f"Evaluating artifact set ({evaluating_artifact.set}) is different from equipped artifact set ({equipped_artifact_set})."
        )
        log.warn(
            f"This may interfere with comparing artifact potentials. Consider evaluating slot with correct set or turn artifacts.use_set_bonus = False"
        )

    return substat_potential_df


def _individual_slot_potential(
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
                roll_level = genshindata.substat_roll_values[substat][stars].index(roll)
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
    total_rolls_high_chance = genshindata.extra_substat_probability[source][stars]

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
    for stat in genshindata.stat_names:
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
    valid_substats = set(genshindata.substat_rarity[main_stat].keys())
    for substat in pseudo_artifacts[0]["substats"]:
        valid_substats.remove(substat)

    # Consolodate similar substats (don't need DEF vs DEF% or low roll DEF vs high roll DEF on an ATK scaling character)
    condensable_substats = _condensable_substats(character=character)
    base_probability = sum([genshindata.substat_rarity[main_stat][substat] for substat in valid_substats])

    # Create list of possible substats
    possibilities = []
    for substat in valid_substats:
        possibility = {
            "substat": substat,
            "probability": genshindata.substat_rarity[main_stat][substat] / base_probability,
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
            substat_value = rolls_split.dot(genshindata.substat_roll_values[substat][stars])
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


def _artifact_potential_summary(
    artifact_potential_df: pd.DataFrame, slot_potential: pd.DataFrame, base_power: float = None
):

    slot_power = slot_potential["power"]
    artifact_power = artifact_potential_df["power"]

    slot_min_power = slot_power.min()

    artifact_min_power = artifact_power.min()
    artifact_min_increase = 100 * (artifact_min_power / slot_min_power - 1)
    artifact_min_percentile = 100 * slot_potential[slot_power < artifact_min_power]["probability"].sum()

    artifact_avg_power = artifact_power.dot(artifact_potential_df["probability"])
    artifact_avg_increase = 100 * (artifact_avg_power / slot_min_power - 1)
    artifact_avg_percentile = 100 * slot_potential[slot_power < artifact_avg_power]["probability"].sum()

    artifact_max_power = artifact_power.max()
    artifact_max_increase = 100 * (artifact_max_power / slot_min_power - 1)
    artifact_max_percentile = 100 * slot_potential[slot_power < artifact_max_power]["probability"].sum()

    if base_power is not None:
        base_power_increase = 100 * (base_power / slot_min_power - 1)
        base_power_slot_percentile = 100 * slot_potential[slot_power < base_power]["probability"].sum()
        base_power_artifact_percentile = 100 * artifact_potential_df[artifact_power < base_power]["probability"].sum()

    # Output artifact min, avg, max and base power, sorted.
    # fmt: off
    if base_power is not None:
        if base_power < artifact_min_power:
            log.info(f'Base Power:         {base_power:>6,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile')
    log.info(f'Artifact Min Power: {artifact_min_power:>6,.0f} | {artifact_min_increase:>+5.1f}% |   0.0th Artifact Percentile | {artifact_min_percentile:>5.1f}{_suffix(artifact_min_percentile)} Slot Percentile')
    if base_power is not None:
        if artifact_min_power <= base_power < artifact_avg_power:
            log.info(f'Base Power:         {base_power:>6,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile')
    log.info(f'Artifact Avg Power: {artifact_avg_power:>6,.0f} | {artifact_avg_increase:>+5.1f}% |  50.0th Artifact Percentile | {artifact_avg_percentile:>5.1f}{_suffix(artifact_avg_percentile)} Slot Percentile')
    if base_power is not None:
        if artifact_avg_power <= base_power < artifact_max_power:
            log.info(f'Base Power:         {base_power:>6,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile')
    log.info(f'Artifact Max Power: {artifact_max_power:>6,.0f} | {artifact_max_increase:>+5.1f}% | 100.0th Artifact Percentile | {artifact_max_percentile:>5.1f}{_suffix(artifact_max_percentile)} Slot Percentile')
    if base_power is not None:
        if artifact_max_power <= base_power:
            log.info(f'Base Power:         {base_power:>6,.0f} | {base_power_increase:>+5.1f}% | {base_power_artifact_percentile:>5.1f}{_suffix(base_power_artifact_percentile)} Artifact Percentile | {base_power_slot_percentile:>5.1f}{_suffix(base_power_slot_percentile)} Slot Percentile')
        log.info(f'Artifact has a {max(0, 100 - base_power_artifact_percentile):>.1f}% chance of outperforming the baseline.')
        if artifact_min_power == artifact_avg_power == artifact_max_power == base_power:
            log.info(f'Artifact is very likely the baseline.')
    # fmt: on


def _suffix(value: float) -> str:
    suffix = ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"]
    mod_value = math.floor(10 * value) % 10
    return suffix[mod_value]


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
    for substat in genshindata.substat_roll_values:
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
