#!/usr/bin/env python3
"""HarmonyOS-specific consumer test for the installed tubeup package.

Verifies the OHOS target platform, the sandbox-writable download tree, the
HMDFS-safe filename option of this port, the DirError guard for a blocked
download root, the optional-yt-dlp guard and the packaged console script.
"""
import importlib.util
import os
import platform
import shutil
import sys
import tempfile


def main(argv):
    if len(argv) > 1 and argv[1]:
        for entry in argv[1].split(os.pathsep):
            if entry and entry not in sys.path:
                sys.path.insert(0, entry)
    package_folder = argv[2] if len(argv) > 2 else ""

    # --- this adaptation targets the OHOS aarch64 POSIX runtime ---
    assert os.name == "posix", os.name
    machine = platform.machine().lower()
    assert machine in {"aarch64", "arm64", "armv8", "armv8l"}, platform.machine()
    system = platform.system()
    assert system in ("HarmonyOS", "OpenHarmony"), (
        f"expected a HarmonyOS/OpenHarmony runtime, got {system!r}")

    from tubeup.TubeUp import TubeUp, DOWNLOAD_DIR_NAME
    from tubeup.utils import sanitize_identifier

    # --- sandbox HOME: tubeup must create and use its download tree there ---
    root = tempfile.mkdtemp(prefix="tubeup-ohos-consumer-",
                            dir=os.path.expanduser("~"))
    try:
        tu = TubeUp(dir_path=root)
        assert tu.dir_path["root"] == os.path.abspath(root)
        assert os.path.basename(tu.dir_path["downloads"]) == DOWNLOAD_DIR_NAME
        assert os.path.isdir(tu.dir_path["downloads"])
        probe = os.path.join(tu.dir_path["downloads"], "writable-probe.txt")
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("ohos")
        with open(probe, encoding="utf-8") as handle:
            assert handle.read() == "ohos"

        # --- HMDFS-safe filenames: restrictfilenames stays enabled ---
        opts = tu.generate_ydl_options(lambda d: None)
        assert opts["restrictfilenames"] is True
        assert sanitize_identifier("twitch:clips-1003820974") == \
            "twitch-clips-1003820974"
        assert ":" not in sanitize_identifier("twitch:vod-v181464551")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # --- a file blocking the download root must be reported, not crash ---
    blocked = os.path.join(os.path.expanduser("~"), ".tubeup-ohos-blocked-probe")
    with open(blocked, "w", encoding="utf-8") as handle:
        handle.write("x")
    try:
        try:
            TubeUp(dir_path=blocked)
        except TubeUp.DirError:
            pass
        else:
            raise AssertionError("TubeUp must raise DirError for a file dir_path")
    finally:
        os.remove(blocked)

    # --- optional yt-dlp guard: controlled error, not an import failure ---
    if importlib.util.find_spec("yt_dlp") is None:
        import tubeup.TubeUp as tubeup_module
        assert tubeup_module.YoutubeDL is None
        guard_root = tempfile.mkdtemp(prefix="tubeup-ohos-guard-",
                                      dir=os.path.expanduser("~"))
        try:
            try:
                TubeUp(dir_path=guard_root).get_resource_basenames(
                    ["https://example.invalid/watch?v=x"])
            except RuntimeError as exc:
                assert "yt-dlp" in str(exc), exc
            else:
                raise AssertionError(
                    "downloading without yt-dlp must raise RuntimeError")
        finally:
            shutil.rmtree(guard_root, ignore_errors=True)

    # --- packaged console script ---
    script = os.path.join(package_folder, "bin", "tubeup")
    assert os.path.isfile(script), f"missing console script: {script}"
    with open(script, encoding="utf-8") as handle:
        first = handle.readline().strip()
    assert first.startswith("#!") and "python3" in first, first

    print(f"OK: tubeup OHOS consumer test passed "
          f"(system={system}, machine={platform.machine()})")


if __name__ == "__main__":
    main(sys.argv)
