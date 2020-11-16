"""
Representation/access to the parsed rating files.
"""
import pathlib
import attr
from registered import parser, merge


@attr.s(eq=False)
class Rating:  # pylint: disable=too-few-public-methods
    """
    Wrapper around all the files exported/merged from HASTUS.

    To use, pass in a path to the files, then access this as a dictionary.

    >>> rat = Rating(<path>)
    >>> rat["ppat"]
    [<items parsed from the .ppat files>]
    """

    path = attr.ib(converter=pathlib.Path)

    def __attrs_post_init__(self):
        # pylint: disable=attribute-defined-outside-init
        self._cache = {}

    def __getitem__(self, extension):
        if extension not in self._cache:
            filename_glob = merge.insensitive_glob(extension)
            parsed = []
            for path in self.path.glob(filename_glob):
                with open(path) as to_be_parsed:
                    parsed.extend(parser.parse_lines(to_be_parsed))
            self._cache[extension] = parsed

        return self._cache[extension]