"""Preparatory python script used to precalculate possible substat distributions. Not used in regular operations."""

import ast
import copy
import json
import logging
import os
import re

import numpy as np

log = logging.getLogger(__name__)


def generate_substat_distribution_json():
    """Precalculate substat distribution json used for evaluating potential"""

    # Possible substat rolls normalized by max roll for given artifact star level
    substat_rolls = {
        1: [0.80, 1.00],
        2: [0.70, 0.85, 1.00],
        3: [0.70, 0.80, 0.90, 1.00],
        4: [0.70, 0.80, 0.90, 1.00],
        5: [0.70, 0.80, 0.90, 1.00],
    }

    pre_output: dict[int, dict[int, dict[int, dict[str]]]] = {}
    # Iterate through number of stars
    for stars in range(3, 5 + 1):
        pre_output[stars] = {}
        possible_rolls = substat_rolls[stars]
        # Iterate through number of unlocks
        for num_unlocks in range(0, 4 + 1):
            pre_output[stars][num_unlocks] = {}
            # Iterate through number of increases (without extra drop chance)
            for num_increases in range(0, max(0, 2 * stars - 5) + 1):
                pre_output[stars][num_unlocks][num_increases] = {}

                # Number of different values a single roll on a single substat could take
                num_options = len(possible_rolls)

                # Calculate list of list of roll options for each possible unlock
                unlock_rolls_options = []
                for already_unlocked in range(4):
                    if already_unlocked < 4 - num_unlocks:
                        unlock_rolls_options.append([0])
                    else:
                        unlock_rolls_options.append(possible_rolls)

                # Calculate all possible normalized substat unlock values
                substat_unlocks = np.array(np.meshgrid(*unlock_rolls_options)).T.reshape(-1, 4)

                # Calculate all possible number of times each roll level / index combination is rolled for increases
                substat_increases = np.array(list(sums(4 * num_options, num_increases)))

                # Convert roll level / index combinations to normalized substat values
                substat_rolls_matrix = np.zeros([4 * num_options, 4])
                for substat_index in range(4):
                    substat_rolls_matrix[
                        (num_options * substat_index) : (num_options * substat_index + num_options), substat_index
                    ] = possible_rolls
                substat_values = np.matmul(substat_increases, substat_rolls_matrix)

                # Combine unlocks and increases
                substats_list = []
                for substat_unlock in substat_unlocks:
                    full_substats = substat_unlock + substat_values
                    substats_list.append(full_substats)
                substats = np.array(substats_list).reshape(-4, 4)

                # Iteratively remove columns from the left side, representing useless substats existing previously
                left_remove_substats = copy.deepcopy(substats)
                for num_existing_condensed in range(0, 4 - num_unlocks + 1):
                    pre_output[stars][num_unlocks][num_increases][num_existing_condensed] = {}
                    if num_existing_condensed > 0:
                        left_remove_substats = np.delete(left_remove_substats, 0, 1)

                    # Iteratively remove columns from the right side, representing useless substats that were just rolled
                    right_remove_substats = copy.deepcopy(left_remove_substats)
                    for num_unlocked_condensed in range(0, num_unlocks + 1):
                        if num_unlocked_condensed > 0:
                            right_remove_substats = np.delete(right_remove_substats, -1, 1)

                        log.info(
                            f"Precalculate: Stars: {stars}, Unlocks: {num_unlocks}, Increases: {num_increases}, Existing Condensed: {num_existing_condensed}, New Condensed: {num_unlocked_condensed}"
                        )

                        # Return a unique array of substat values and number of occurances
                        substats_unique, frequency = np.unique(right_remove_substats, axis=0, return_counts=True)

                        # Calculate probability
                        probability = frequency / np.sum(frequency)

                        pre_output[stars][num_unlocks][num_increases][num_existing_condensed][
                            num_unlocked_condensed
                        ] = {
                            "substats": substats_unique.tolist(),
                            "probability": probability.tolist(),
                        }

    # Go through loop again, reformating probability into a dictionary based on extra drop chance
    output: dict[int, dict[int, dict[int, dict[str]]]] = {}
    # Iterate through number of stars
    for stars in range(3, 5 + 1):
        output[stars] = {}
        possible_rolls = substat_rolls[stars]
        # Iterate through number of unlocks
        for num_unlocks in range(0, 4 + 1):
            output[stars][num_unlocks] = {}
            # Iterate through number of increases (without extra drop chance)
            for num_increases in range(0, max(0, 2 * stars - 5) + 1):
                output[stars][num_unlocks][num_increases] = {}
                for num_existing_condensed in range(0, 4 - num_unlocks + 1):
                    output[stars][num_unlocks][num_increases][num_existing_condensed] = {}
                    for num_unlocked_condensed in range(0, num_unlocks + 1):

                        log.info(
                            f"Merge: Stars: {stars}, Unlocks: {num_unlocks}, Increases: {num_increases}, Existing Condensed: {num_existing_condensed}, New Condensed: {num_unlocked_condensed}"
                        )

                        if num_increases == max(0, 2 * stars - 5):
                            roll_results = pre_output[stars][num_unlocks][num_increases][num_existing_condensed][
                                num_unlocked_condensed
                            ]
                            output[stars][num_unlocks][num_increases][num_existing_condensed][
                                num_unlocked_condensed
                            ] = {
                                "substats": roll_results["substats"],
                                "probabilities": {0.0: roll_results["probability"]},
                            }
                            continue

                        low_roll_results = pre_output[stars][num_unlocks][num_increases][num_existing_condensed][
                            num_unlocked_condensed
                        ]
                        high_roll_results = pre_output[stars][num_unlocks][num_increases + 1][num_existing_condensed][
                            num_unlocked_condensed
                        ]
                        combined_substats = low_roll_results["substats"] + high_roll_results["substats"]

                        combined_probability: dict[float, list[float]] = {}

                        for extra_drop_chance in [0.0, 0.2, 1 / 3]:
                            low_roll_probability = np.array(low_roll_results["probability"]) * (1 - extra_drop_chance)
                            high_roll_probability = np.array(high_roll_results["probability"]) * extra_drop_chance
                            combined_probability[extra_drop_chance] = (
                                low_roll_probability.tolist() + high_roll_probability.tolist()
                            )

                        unique_substats_dict: dict[str, dict[float, float]] = {}
                        for index, substat in enumerate(combined_substats):
                            substat_str = str(substat)
                            if substat_str not in unique_substats_dict:
                                unique_substats_dict[substat_str] = {key: 0.0 for key in [0.0, 0.2, 1 / 3]}
                            for extra_drop_chance in [0.0, 0.2, 1 / 3]:
                                unique_substats_dict[substat_str][extra_drop_chance] += combined_probability[
                                    extra_drop_chance
                                ][index]

                        unique_substats = [ast.literal_eval(string) for string in list(unique_substats_dict.keys())]
                        unique_probabilities = {
                            extra_drop_chance: [prob[extra_drop_chance] for prob in unique_substats_dict.values()]
                            for extra_drop_chance in [0.0, 0.2, 1 / 3]
                        }

                        output[stars][num_unlocks][num_increases][num_existing_condensed][num_unlocked_condensed] = {
                            "substats": unique_substats,
                            "probabilities": unique_probabilities,
                        }

    # Save output to string
    log.info("Writing json string...")
    output_str = json.dumps(output)

    # Remove floating point repeating digits (0.587100000001, -> 0.5871)
    log.info("Removing floating point errors to reduce file size...")
    output_str = remove_floating_point_errors(output_str)

    # Save outputs to file
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "..\..\data\precalculated_substat_distributions.json")
    with open(file_path, "w") as file_handle:
        log.info(f"Saving JSON to {file_path}...")
        file_handle.write(output_str)
        log.info(f"File saved.")


def calculate_substat_distributions(
    num_unlocks: int,
    num_increases: int,
    num_existing_condensed: int,
    num_unlocked_condensed: int,
    possible_rolls: list[float],
):
    """Calculates all possible substat distributions and frequencies for given parameters"""

    # Number of different values a single roll on a single substat could take
    num_options = len(possible_rolls)

    # Calculate list of list of roll options for each possible unlock
    unlock_rolls_options = []
    for already_unlocked in range(4):
        if already_unlocked < 4 - num_unlocks:
            unlock_rolls_options.append([0])
        else:
            unlock_rolls_options.append(possible_rolls)

    # Calculate all possible normalized substat unlock values
    substat_unlocks = np.array(np.meshgrid(*unlock_rolls_options)).T.reshape(-1, 4)

    # Calculate all possible number of times each roll level / index combination is rolled for increases
    substat_increases = np.array(list(sums(4 * num_options, num_increases)))

    # Convert roll level / index combinations to normalized substat values
    substat_rolls_matrix = np.zeros([4 * num_options, 4])
    for substat_index in range(4):
        substat_rolls_matrix[
            (num_options * substat_index) : (num_options * substat_index + num_options), substat_index
        ] = possible_rolls
    substat_values = np.matmul(substat_increases, substat_rolls_matrix)

    # Combine unlocks and increases
    substats_list = []
    for substat_unlock in substat_unlocks:
        full_substats = substat_unlock + substat_values
        substats_list.append(full_substats)
    substats = np.array(substats_list).reshape(-4, 4)

    # Remove columns for condensed substats
    for _ in range(num_existing_condensed):
        substats = np.delete(substats, 0, 1)
    for _ in range(num_unlocked_condensed):
        substats = np.delete(substats, -1, 1)

    # Return a unique array of substat values and number of occurances
    substats_unique, frequency = np.unique(substats, axis=0, return_counts=True)

    # Calculate probability
    probability = frequency / np.sum(frequency)

    return substats_unique, probability


def sums(length, total_sum):
    """
    Generates list of all possible integer vectors of length totalling sum
    Soure: https://stackoverflow.com/questions/7748442/generate-all-possible-lists-of-length-n-that-sum-to-s-in-python
    """
    if length == 1:
        yield (total_sum,)
    else:
        for value in range(total_sum + 1):
            for permutation in sums(length - 1, total_sum - value):
                yield (value,) + permutation


def remove_floating_point_errors(input_str: str) -> str:

    new_output_string = ""
    remaining_string = input_str

    # Premptive simplification
    remaining_string = remaining_string.replace(" ", "")
    completed = len(new_output_string)
    total = completed + len(remaining_string)
    percent_complete = completed / total
    compression = 1 - (total) / len(input_str)
    log.info(f"Removed spaces")
    log.info(
        f"Characters: {completed:,} / {total:,}, Percent Complete: {percent_complete:>.1%}, Compression: {compression:>.1%}"
    )
    remaining_string = remaining_string.replace("0.0,", "0,")
    remaining_string = remaining_string.replace("0.0]", "0]")
    completed = len(new_output_string)
    total = completed + len(remaining_string)
    percent_complete = completed / total
    compression = 1 - (total) / len(input_str)
    log.info(f"0.0 -> 0")
    log.info(
        f"Characters: {completed:,} / {total:,}, Percent Complete: {percent_complete:>.1%}, Compression: {compression:>.1%}"
    )
    re_string = r"(?<=\d)(\d)\1{5,}\d*(?=,|])"
    match = re.search(re_string, remaining_string)
    while match is not None:
        # Find preceding number
        preceding_number_str: str = re.split("[,\[]", remaining_string[: match.start()])[
            -1
        ]  # output_str[: match.start()].rsplit(" ", 1)[1]
        old_number_str = preceding_number_str + remaining_string[match.start() : match.end()]
        # Determine if repeated number is 0 or 9
        first_match_digit = int(remaining_string[match.start()])
        # Rounding
        if first_match_digit == 0 or first_match_digit == 9:
            increase = int(remaining_string[match.start()]) == 9
            # Create new number
            if not increase:
                new_number_str = preceding_number_str
            else:
                number_index = len(preceding_number_str) - 1
                while old_number_str[number_index] == "9" or old_number_str[number_index] == ".":
                    if number_index == 0:
                        number_index = -1
                        break
                    elif old_number_str[number_index - 1] == ".":
                        number_index -= 2
                    else:
                        number_index -= 1
                if number_index == -1:
                    new_number_str = str(10 ** len(old_number_str.split(".")[0]))
                else:
                    new_number_str = old_number_str[:number_index] + str(int(old_number_str[number_index]) + 1)
        # Dealing with repeated numbers that aren't 0 or 9. Just have 3 of them and continue
        else:
            new_number_str = preceding_number_str + str(first_match_digit) * 3

        # Replace it
        remaining_string = remaining_string.replace(old_number_str, new_number_str)
        new_output_string += remaining_string[: match.start() - len(preceding_number_str)]
        remaining_string = remaining_string[match.start() - len(preceding_number_str) :]
        # Repeat
        match = re.search(re_string, remaining_string)
        # Log
        completed = len(new_output_string)
        total = completed + len(remaining_string)
        percent_complete = completed / total
        compression = 1 - (total) / len(input_str)
        log.info(f"{old_number_str} -> {new_number_str}")
        log.info(
            f"Characters: {completed:,} / {total:,}, Percent Complete: {percent_complete:>.1%}, Compression: {compression:>.1%}"
        )

    new_output_string += remaining_string

    return new_output_string


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()])
    log = logging.getLogger(__name__)
    generate_substat_distribution_json()
