"""One installed-package flow; assertions are not additional test cases."""
from pathlib import Path
import sys

import twodict
from twodict import TwoWayOrderedDict


def main():
    expected_module = Path(sys.argv[1]).resolve() / "twodict.py"
    assert Path(twodict.__file__).resolve() == expected_module
    mapping = TwoWayOrderedDict([("a", 1), ("b", 2)])
    assert (mapping["a"], mapping[1]) == (1, "a")
    assert list(mapping.items()) == [("a", 1), ("b", 2)]
    assert dict(dict.items(mapping)) == {"a": 1, 1: "a", "b": 2, 2: "b"}
    parent_copy = super(TwoWayOrderedDict, mapping).copy()
    print("oracle observation:", {"public_items": list(mapping.items()),
                                  "parent_copy": parent_copy,
                                  "raw_items": list(dict.items(mapping))})
    mapping["a"] = 3
    assert (mapping["a"], mapping[3]) == (3, "a")
    assert 1 not in mapping
    del mapping[2]
    assert "b" not in mapping and 2 not in mapping
    assert list(mapping.items()) == [("a", 3)]
    assert dict(dict.items(mapping)) == {"a": 3, 3: "a"}
    print("twodict installed consumer: 1 flow / 9 assertions PASS")


if __name__ == "__main__":
    main()
