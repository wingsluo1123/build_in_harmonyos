"""One installed-package consumer: ranges, socket allocation and port store."""
import argparse
import json
from pathlib import Path
import socket
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-folder", required=True)
    args = parser.parse_args()
    package = Path(args.package_folder).resolve()
    modules = package / "lib/python"
    sys.path.insert(0, str(modules))
    import port_for

    assert Path(port_for.__file__).resolve().is_relative_to(modules)
    assert port_for.__version__ == "1.0.0"
    checks = 0
    ranges = port_for.good_port_ranges(set(range(1000, 1040)), 20, 3)
    assert ranges == [(1003, 1036)], ranges
    checks += 1
    eligible = set(range(1003, 1037))
    assert port_for.utils.ranges_to_set(ranges) == eligible
    checks += 1
    selected = port_for.get_port(eligible)
    assert selected in eligible
    checks += 1
    assert not port_for.port_is_used(selected)
    checks += 1
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", selected))
        listener.listen(1)
        assert port_for.port_is_used(selected)
        checks += 1
    assert not port_for.port_is_used(selected)
    checks += 1
    with tempfile.TemporaryDirectory(prefix="port-for-consumer-") as temporary:
        filename = Path(temporary) / "associations.ini"
        store = port_for.PortStore(str(filename))
        assert store.bound_ports() == []
        checks += 1
        assert store.bind_port("consumer", selected) == selected
        checks += 1
        assert port_for.PortStore(str(filename)).bound_ports() == [("consumer", selected)]
        checks += 1
        try:
            store.bind_port("other", selected)
        except port_for.PortForException:
            checks += 1
        else:
            raise AssertionError("Duplicate stored port accepted")
        store.unbind_port("consumer")
        assert store.bound_ports() == []
        checks += 1
    assert checks == 11
    print(json.dumps({"consumer_programs": 1, "functional_checks": checks,
                      "identity_assertions": 2, "module": port_for.__file__,
                      "python": sys.version, "ranges": ranges, "selected": selected}))


if __name__ == "__main__":
    main()
