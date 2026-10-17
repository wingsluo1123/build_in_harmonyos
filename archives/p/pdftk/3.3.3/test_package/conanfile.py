from conan import ConanFile
import os


class PdftkTest(ConanFile):
    # L0p: settings match the main recipe (only enter package_id)
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["pdftk"].package_folder
        self.output.info(f"Testing package in: {pkg_folder}")

        # Resolve JAVA_HOME: env first, then common JDK locations
        # (HNP bundled java may fail to start in some environments,
        # so prefer ~/bishengjdk17 installed via cmd-pkgs)
        java_home = os.environ.get("JAVA_HOME")
        if not (java_home and os.path.isfile(os.path.join(java_home, "bin", "java"))):
            for candidate in (
                os.path.expanduser("~/bishengjdk17"),
                os.path.expanduser("~/usr/local/bishengjdk17"),
                "/storage/Users/currentUser/bishengjdk17",
                "/usr/lib/jvm/bishengjdk-17",
                "/usr/lib/jvm/java-17-openjdk",
                "/usr/lib/jvm/java-17-openjdk-arm64",
            ):
                if os.path.isfile(os.path.join(candidate, "bin", "java")):
                    java_home = candidate
                    break
        if not (java_home and os.path.isfile(os.path.join(java_home, "bin", "java"))):
            raise Exception(
                "JAVA_HOME not set and no JDK found in common locations. "
                "Set JAVA_HOME to a JDK 17+ installation path."
            )
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (
            f"{java_home}/bin:{os.environ.get('PATH', '/usr/bin:/bin')}"
        )

        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{script}" "{pkg_folder}"', env="conanrun")
