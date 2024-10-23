"""
Helpers for friendly environment access.
"""


class FriendlyEnviron:
    """
    Wrapper around os.environ which raises a more helpful error on missing keys.
    """

    def __init__(self, *parents):
        self._parents = parents

    def __getitem__(self, key):
        """
        Item access for environment variables.
        """
        self._validate_key_type(key)
        for parent in self._parents:
            if key in parent:
                return parent[key]
        raise KeyError(
            f"{repr(key)}: In order to add this to your environment, add it to the .env file."
        ) from None

    def get(self, key, missing_val=None):
        """
        Optional access for environment variables.
        """
        self._validate_key_type(key)
        for parent in self._parents:
            if key in parent:
                return parent[key]
        return missing_val

    @staticmethod
    def _validate_key_type(key):
        if not isinstance(key, str):
            raise TypeError(f"str expected, not {type(key)}")
