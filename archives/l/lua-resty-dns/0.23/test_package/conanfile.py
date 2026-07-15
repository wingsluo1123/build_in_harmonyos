import os

from conan import ConanFile


class LuaRestyDnsTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["lua-resty-dns"]
        lua_file = os.path.join(
            pkg.package_folder, "lib", "resty", "dns", "resolver.lua"
        )
        test_script = os.path.join(self.source_folder, "test_package.py")
        self.run(f'python3 "{test_script}" "{lua_file}"')
