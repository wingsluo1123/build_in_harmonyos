#!/usr/bin/env python3
"""Build the uMurmur path-B A/B/C variants with Conan on HarmonyOS PC."""

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import tempfile


PACKAGE_REF = "umurmur/0.3.1"
DEFERRED_PATCH = "patches/0003-flush-first-frame-after-tls-handshake.patch"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def remove_deferred_patch(conandata):
    lines = conandata.read_text(encoding="utf-8").splitlines(keepends=True)
    output = []
    index = 0
    while index < len(lines):
        if f'patch_file: "{DEFERRED_PATCH}"' in lines[index]:
            index += 3
            continue
        output.append(lines[index])
        index += 1
    conandata.write_text("".join(output), encoding="utf-8")


def use_standard_patch_application(recipe):
    path = recipe / "conanfile.py"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"    def _apply_patches\(self\):.*?(?=\n    def package\(self\):)",
        re.DOTALL,
    )
    replacement = (
        "    def _apply_patches(self):\n"
        "        apply_conandata_patches(self)\n"
    )
    text, count = pattern.subn(replacement, text)
    if count != 1:
        raise RuntimeError("could not isolate _apply_patches() in recipe overlay")
    path.write_text(text, encoding="utf-8")


def newest_package_path(conan):
    listing = subprocess.run(
        [conan, "list", f"{PACKAGE_REF}:*", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(listing.stdout)["Local Cache"][PACKAGE_REF]["revisions"]
    revision, revision_data = max(
        data.items(), key=lambda item: item[1].get("timestamp", 0)
    )
    packages = revision_data.get("packages", {})
    if not packages:
        raise RuntimeError(f"no package ID found for {PACKAGE_REF}#{revision}")
    package_id = next(iter(packages))
    reference = f"{PACKAGE_REF}#{revision}:{package_id}"
    result = subprocess.run(
        [conan, "cache", "path", reference],
        capture_output=True,
        text=True,
        check=True,
    )
    return pathlib.Path(result.stdout.strip())


def build_arm(conan, source_recipe, profile, output, arm, arm_b_patch):
    with tempfile.TemporaryDirectory(prefix=f"umurmur-path-b-{arm}-") as name:
        overlay = pathlib.Path(name) / "recipe"
        shutil.copytree(source_recipe, overlay)
        if arm == "a":
            remove_deferred_patch(overlay / "conandata.yml")
            use_standard_patch_application(overlay)
        elif arm == "b":
            shutil.copyfile(arm_b_patch, overlay / DEFERRED_PATCH)

        command = [
            conan,
            "create",
            str(overlay),
            f"-pr:h={profile}",
            f"-pr:b={profile}",
            "--build=umurmur/*",
            "--test-folder=",
            "--format=json",
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            detail = "\n".join(result.stderr.splitlines()[-120:])
            raise RuntimeError(f"Arm {arm.upper()} build failed:\n{detail}")
        json.loads(result.stdout)
        packaged = newest_package_path(conan) / "sbin" / "umurmurd"
        target = output / f"umurmurd-arm-{arm}"
        shutil.copy2(packaged, target)
        target.chmod(0o755)
        print(f"ARM_{arm.upper()}_ELF {sha256(target)} {target}")
        if arm == "c":
            installed_config = packaged.parents[1] / "etc" / "umurmur" / "umurmur.conf"
            shutil.copy2(installed_config, output / "umurmur.conf")


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
    arm_b_patch = pathlib.Path(__file__).with_name("arm-b-always-pollout.patch")
    for required in (
        recipe / "conanfile.py",
        recipe / "conandata.yml",
        recipe / DEFERRED_PATCH,
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
