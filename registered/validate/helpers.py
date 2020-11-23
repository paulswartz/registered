"""
Helper functions for validating a rating.
"""


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
