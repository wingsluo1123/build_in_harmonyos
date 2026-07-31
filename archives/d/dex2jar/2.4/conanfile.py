from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy
import os


class Dex2JarConan(ConanFile):
    name = "dex2jar"
    version = "2.4"
    license = "Apache-2.0"
    url = "https://github.com/pxb1988/dex2jar"
    description = "Tools to convert Android .dex files to .class files (JAR)"
    package_type = "application"
    settings = "os", "arch"

    exports_sources = "conandata.yml"

    def layout(self):
        self.folders.build = "build"
        self.folders.source = "."

    def source(self):
        src_data = self.conan_data["sources"][self.version]
        get(self, src_data["url"], strip_root=True)

    def build(self):
        # Use the Gradle wrapper if available, otherwise system gradle
        gradle_cmd = "gradlew" if os.path.exists("gradlew") else "gradle"
        if gradle_cmd == "gradlew" and os.name == "nt":
            gradle_cmd = "gradlew.bat"

        self.run(f"{gradle_cmd} clean distZip", cwd=self.source_folder)

    def package(self):
        # distZip produces build/distributions/dex2jar-<version>.zip
        dist_name = f"dex2jar-{self.version}"
        zip_path = os.path.join(self.source_folder, "build", "distributions", f"{dist_name}.zip")

        if not os.path.exists(zip_path):
            raise ConanException(f"Expected distribution zip not found: {zip_path}")

        # Extract the zip into the source folder
        self.run(f"cd {self.source_folder} && unzip -o {zip_path}")
        extract_dir = os.path.join(self.source_folder, dist_name)

        # Copy bin/ and lib/ into the package folder
        copy(self, "*", src=os.path.join(extract_dir, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.jar", src=os.path.join(extract_dir, "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.buildenv_info.define("DEX2JAR_HOME", self.package_folder)
