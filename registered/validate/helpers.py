"""
Helper functions for validating a rating.
"""

import difflib


def same_list_order(first, second):
    """
    Return whether the items in the second list appear in the same order as the first list.
    """
    matcher = difflib.SequenceMatcher(a=first, b=second)

    for opcode, _, _, _, _ in matcher.get_opcodes():
        if opcode in {"insert", "replace"}:
            return False

    return True


def timepoints_by_route_direction(rating):
    """
    Return a dictionary mapping (route ID, direction name) -> list of timepoints
    """
    return {
        (
            timepoint_pattern.route_id,
            timepoint_pattern.direction_name,
        ): timepoint_pattern.timepoints
        for timepoint_pattern in rating["ppat"]
    }
