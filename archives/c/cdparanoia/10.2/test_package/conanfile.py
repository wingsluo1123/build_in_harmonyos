import os
from conan import ConanFile

class CdparanoiaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the static libraries exist
        dep = self.dependencies["cdparanoia"]
        for lib in ["libcdda_interface.a", "libcdda_paranoia.a"]:
            libpath = os.path.join(dep.cpp_info.libdirs[0], lib)
            if not os.path.exists(libpath):
                raise Exception(f"Library not found: {libpath}")
        # Verify headers exist
        for hdr in ["cdda_interface.h", "cdda_paranoia.h"]:
            hdrpath = os.path.join(dep.cpp_info.includedirs[0], hdr)
            if not os.path.exists(hdrpath):
                raise Exception(f"Header not found: {hdrpath}")
        print("cdparanoia test: libraries and headers verified")
