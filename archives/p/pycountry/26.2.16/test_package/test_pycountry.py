#!/usr/bin/env python3
"""Consumer-side assertions for the pycountry package.

Runs inside test_package with env="conanrun", so PYTHONPATH points at the
packaged site-packages. The upstream xkeyboard-config suite imports pycountry
from tests/test_rules_xml.py to cross-check the generated rules XML against the
ISO registries, so the assertions cover both halves of that contract: the tree
that gets imported is the packaged one (provenance, not merely "an import
succeeded"), and the ISO databases really answer.
"""
import os
import sys

assertions = 0


def check(condition, message):
    global assertions
    if not condition:
        raise AssertionError(message)
    assertions += 1


def main():
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    package_folder = os.path.realpath(sys.argv[1])
    expected_site = os.path.join(
        package_folder,
        "lib",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        "site-packages",
    )

    import pycountry
    import pycountry.db

    pkg_root = os.path.realpath(os.path.dirname(pycountry.__file__))

    # 0) Provenance: the imported tree must be the packaged one.
    check(
        os.path.isfile(os.path.join(expected_site, "pycountry", "__init__.py")),
        f"packaged module missing: {expected_site}/pycountry/__init__.py",
    )
    check(
        pkg_root.startswith(expected_site + os.sep),
        f"imported pycountry is not the packaged tree: {pkg_root}",
    )
    check(
        os.path.isfile(os.path.join(pkg_root, "databases", "iso3166-1.json")),
        "packaged ISO 3166-1 database missing",
    )

    # 1) The ISO API the upstream rules-XML suite relies on.
    check(len(pycountry.countries) == 249, f"country count: {len(pycountry.countries)}")
    gb = pycountry.countries.get(alpha_2="GB")
    check(gb is not None and gb.alpha_3 == "GBR", "countries.get(alpha_2='GB')")
    check(
        pycountry.countries.get(alpha_3="USA").name == "United States",
        "countries.get(alpha_3='USA')",
    )
    check(
        isinstance(list(pycountry.countries)[0], pycountry.db.Data),
        "records are pycountry.db.Data instances",
    )
    check(
        len(pycountry.subdivisions) == 5046,
        f"subdivision count: {len(pycountry.subdivisions)}",
    )
    check(
        pycountry.subdivisions.get(code="US-CA").name == "California",
        "subdivisions.get(code='US-CA')",
    )
    check(
        pycountry.languages.get(alpha_2="de").alpha_3 == "deu",
        "languages.get(alpha_2='de')",
    )
    check(
        pycountry.currencies.get(alpha_3="USD").numeric == "840",
        "currencies.get(alpha_3='USD')",
    )
    check(
        pycountry.scripts.get(alpha_4="Latn").name == "Latin",
        "scripts.get(alpha_4='Latn')",
    )
    check(
        pycountry.countries.search_fuzzy("England")[0].alpha_2 == "GB",
        "countries.search_fuzzy('England')",
    )
    check(
        pycountry.countries.get(alpha_2="DE").name == "Germany",
        "countries.get(alpha_2='DE')",
    )
    check(pycountry.countries.get(alpha_2="XX") is None, "absent code yields None")

    # 2) Distribution metadata must travel with the package: upstream's suite
    #    reads importlib.metadata and a consumer may ask for the version too.
    from importlib import metadata

    check(
        metadata.version("pycountry") == "26.2.16",
        f"distribution metadata version: {metadata.version('pycountry')}",
    )

    # 3) The gettext catalogues ship with the tree (translations, not only data).
    locale_root = os.path.join(pkg_root, "locales")
    check(
        os.path.isfile(os.path.join(locale_root, "de", "LC_MESSAGES", "iso3166-1.mo")),
        "packaged gettext catalogue missing: locales/de/LC_MESSAGES/iso3166-1.mo",
    )
    check(
        len(os.listdir(locale_root)) >= 100,
        f"packaged locale directories: {len(os.listdir(locale_root))}",
    )

    print(f"PYCOUNTRY_CONSUMER=PASS assertions={assertions}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
