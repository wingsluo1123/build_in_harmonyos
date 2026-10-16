#!/usr/bin/env python3
"""Build reproducible tsdecrypt path-B A/B/C variants with Conan."""

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile


PACKAGE_REF = "tsdecrypt/10.0"
FINAL_PATCH = "patches/0009-tsdecrypt.c.patch"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def remove_final_patch(conandata):
    lines = conandata.read_text(encoding="utf-8").splitlines(keepends=True)
    output = []
    index = 0
    while index < len(lines):
        if f'patch_file: "{FINAL_PATCH}"' in lines[index]:
            index += 3
            continue
        output.append(lines[index])
        index += 1
    conandata.write_text("".join(output), encoding="utf-8")


def newest_package_path(conan):
    listing = subprocess.run(
        [conan, "list", f"{PACKAGE_REF}:*", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(listing.stdout)["Local Cache"][PACKAGE_REF]["revisions"]
    _, revision_data = max(data.items(), key=lambda item: item[1].get("timestamp", 0))
    packages = revision_data.get("packages", {})
    if not packages:
        raise RuntimeError(f"no package ID found for {PACKAGE_REF}")
    package_id = next(iter(packages))
    revision = max(data.items(), key=lambda item: item[1].get("timestamp", 0))[0]
    reference = f"{PACKAGE_REF}#{revision}:{package_id}"
    result = subprocess.run(
        [conan, "cache", "path", reference],
        capture_output=True,
        text=True,
        check=True,
    )
    return pathlib.Path(result.stdout.strip())


def build_arm(conan, recipe, profile, output, arm, arm_b_patch):
    with tempfile.TemporaryDirectory(prefix=f"tsdecrypt-path-b-{arm}-") as name:
        overlay = pathlib.Path(name) / "recipe"
        shutil.copytree(recipe, overlay)
        if arm == "a":
            remove_final_patch(overlay / "conandata.yml")
        elif arm == "b":
            shutil.copyfile(arm_b_patch, overlay / FINAL_PATCH)

        command = [
            conan,
            "create",
            str(overlay),
            f"-pr:h={profile}",
            f"-pr:b={profile}",
            "--build=tsdecrypt/*",
            "--test-folder=",
        ]
        subprocess.run(command, check=True)
        packaged = newest_package_path(conan) / "bin" / "tsdecrypt"
        target = output / f"tsdecrypt-arm-{arm}"
        shutil.copy2(packaged, target)
        target.chmod(0o755)
        print(f"ARM_{arm.upper()}_ELF {sha256(target)} {target}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", required=True, type=pathlib.Path)
    parser.add_argument("--profile", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--conan", default="conan")
    args = parser.parse_args()

    recipe = args.recipe.resolve()
    profile = args.profile.resolve()
    output = args.output.resolve()
    arm_b_patch = pathlib.Path(__file__).with_name("arm-b-cc-only.patch")
    for required in (
        recipe / "conanfile.py",
        recipe / "conandata.yml",
        recipe / FINAL_PATCH,
        profile,
        arm_b_patch,
    ):
        if not required.is_file():
            raise SystemExit(f"missing required input: {required}")
    output.mkdir(parents=True, exist_ok=True)
    for arm in ("a", "b", "c"):
        build_arm(args.conan, recipe, profile, output, arm, arm_b_patch)


if __name__ == "__main__":
    main()
