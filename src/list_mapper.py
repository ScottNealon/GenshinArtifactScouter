import math

import numpy as np


def map_float_lists(key_list: list[float], val_list: list[float]):
    """Map values in sorted key_list to the closest SMALLER valuer in sorted val_list, if one exists else None"""
    # Get max and mins
    key_min = key_list[0]
    key_max = key_list[-1]
    val_min = val_list[0]
    val_max = val_list[-1]
    # Special cases for non-overlaping lists
    if key_min > val_max:
        return {a: val_max for a in key_list}
    elif key_max < val_min:
        return {a: None for a in key_list}
    # Split into lists of keys above, below, and overlapping val_list
    # Lower list
    if key_min < val_min:
        key_overlap_bot_index = binary_serach_lower(key_list, val_min) + 1
        key_lower = key_list[:key_overlap_bot_index]
    else:
        key_lower = []
        key_overlap_bot_index = 0
    # Upper list
    if key_max > val_max:
        key_overlap_top_index = binary_serach_lower(key_list, val_max) + 1
        key_upper = key_list[key_overlap_top_index:]
    else:
        key_upper = []
        key_overlap_top_index = len(key_list)
    # Overlap list
    key_overlap_list = key_list[key_overlap_bot_index:key_overlap_top_index]
    # Prepare initial search range
    val_bot_index = 0
    val_top_index = 1
    val_list_len = len(val_list)
    val_top_val = val_list[val_top_index] if val_list_len > 1 else np.Inf
    # Make map
    map = {}
    # Include lower keys
    for key in key_lower:
        map[key] = None
    # Include overlapping keys
    for key in key_overlap_list:
        # Expand search range until surrounding target
        while key > val_top_val:
            val_top_index = min(2 * val_top_index - val_bot_index, val_list_len - 1)
            val_top_val = val_list[val_top_index]
        # Perform binary search to find target
        sublist = val_list[val_bot_index : (val_top_index + 1)]
        sublist_index = binary_serach_lower(sublist, key)
        # Save solution
        val_val = val_list[val_bot_index + sublist_index]
        map[key] = val_val
        # Update range
        val_bot_index = val_bot_index + sublist_index
    # Include upper keys
    for key in key_upper:
        map[key] = val_max

    return map


def binary_serach_lower(search_list: list[float], target: float):
    """Find the index in `search_list` containing the largest value smaller than `target` using binary search"""
    # Initialize search window size
    bot_index = 0
    top_index = len(search_list) - 1
    # Loop until search window is size 1
    while top_index - bot_index > 1:
        mid_index = math.floor((bot_index + top_index) / 2)
        mid_val = search_list[mid_index]
        # Top half
        if mid_val < target:
            bot_index = mid_index
        # Bottom half
        else:
            top_index = mid_index
    return bot_index
