import os

from conan import ConanFile


class OddjobTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "cpp") or "c++"
        src = os.path.join(self.source_folder, "test_oddjob.cpp")
        exe = os.path.join(self.build_folder, "test_oddjob")
        self.run(f"{cc} -std=c++17 {src} -o {exe}")

    def test(self):
        dep = self.dependencies["oddjob"]
        bindir = dep.cpp_info.bindirs[0]
        sbindir = dep.cpp_info.bindirs[1]
        # 包内二进制动态链接 dbus-1 与 libxml2：运行期需依赖包 lib 在
        # LD_LIBRARY_PATH（oddjob_request→dbus-1；oddjobd→dbus-1+xml2）
        libdirs = ":".join(
            list(self.dependencies["dbus"].cpp_info.libdirs)
            + list(self.dependencies["libxml2"].cpp_info.libdirs))
        self.run(f'ODDJOB_BINDIR="{bindir}" ODDJOB_SBINDIR="{sbindir}" '
                 f'LD_LIBRARY_PATH="{libdirs}" '
                 f'"{os.path.join(self.build_folder, "test_oddjob")}"')
