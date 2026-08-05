import os

from conan import ConanFile


class BlenderTestConan(ConanFile):
    """test_package for blender - verifies the headless build works.

    R40 note: Blender is a graphics/rendering library. A complete adaptation
    validation requires human confirmation of full rendering pipeline behavior
    (cycles engine, OpenGL/OSMesa fallback, image I/O, etc.). This test only
    covers minimal binary execution and command-line smoke checks, which is
    insufficient to prove the rendering pipeline is fully functional on OHOS.
    Mark this package as `requires_manual_verification: true` in the registry.
    """
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 1. Version check - basic binary execution
        self.run("blender --version", env="conanrun")

        # 2. Help introspection - validates CLI argument parsing
        #    and module initialization without requiring GUI/X server
        self.run("blender --help", env="conanrun")

        # 3. Background factory startup - validates that Blender can
        #    initialize without GUI and load core modules. Exits with
        #    a non-zero status (factory startup requires arguments);
        #    we only check that it does NOT crash with missing-library
        #    errors (which would indicate broken dynamic linking).
        result = self.run(
            "blender -b --factory-startup",
            env="conanrun",
            ignore_errors=True,
        )
        # A clean non-zero exit (missing required arguments) is expected.
        # Treat signal exits (>=128, i.e. SIGSEGV/SIGABRT) and missing
        # shared libraries (127) as test failures so broken dynamic
        # linking is not silently swallowed.
        if result >= 128 or result == 127:
            raise ConanException(
                f"blender -b --factory-startup crashed (exit code {result}): "
                "possible missing dynamic library or initialization failure"
            )
        self.output.info(
            f"blender -b --factory-startup exited with code {result} "
            "(non-zero expected; binary loaded and initialized without crash)"
        )

        # NOTE: Full rendering pipeline validation (e.g. rendering an
        # actual .blend file to PNG) requires a richer runtime environment
        # (image libraries, OpenEXR, etc.) than a minimal test_package can
        # reliably provide. Per R40, treat this test as smoke-level only
        # and require human confirmation of full adaptation completeness.
