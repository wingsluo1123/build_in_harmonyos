#!/usr/bin/env python3
"""Conan recipe for PDAL 2.10.2 — CMake build system.
Point Data Abstraction Library for point cloud processing.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PdalConan(ConanFile):
    name = "pdal"
    version = "2.10.2"
    description = "PDAL (Point Data Abstraction Library) - C++ library for point cloud data processing"
    license = "MIT"
    homepage = "https://pdal.io"
    url = "https://github.com/PDAL/PDAL"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    # Dependencies are installed as system packages via cmd-pkgs (pre-compiled)
    # When conan recipes for these dependencies are published to ohpcd remote,
    # uncomment the following to declare them as conan requirements:
    # def requirements(self):
    #     self.requires("gdal/3.9.2")
    #     self.requires("proj/9.3.1")
    #     self.requires("nlohmann-json/3.11.2")
    #     self.requires("curl/8.19.0")
    #     self.requires("zlib/1.3.1")
    #     self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Write gen_dimension.py (HarmonyOS SELinux workaround for dimbuilder)
        scripts_dir = os.path.join(self.source_folder, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        save(self, os.path.join(scripts_dir, "gen_dimension.py"), self._gen_dimension_script())

    def _gen_dimension_script(self):
        """Return Python script content for gen_dimension.py (HarmonyOS workaround)."""
        return r'''#!/usr/bin/env python3
import json, sys
TYPE_MAP = {"double":"Double","float":"Float","uint8":"Unsigned8","int8":"Signed8",
    "uint16":"Unsigned16","int16":"Signed16","uint32":"Unsigned32","int32":"Signed32",
    "uint64":"Unsigned64","int64":"Signed64"}
def word_wrap(t,w=63):
    lines=[];c=""
    for word in t.split():
        if len(c)+len(word)+1>w:
            if c:lines.append(c)
            c=word
        else:c=(c+" "+word).strip()
    if c:lines.append(c)
    return lines or [""]
with open(sys.argv[1]) as f: data=json.load(f)
dims=data.get("dimensions",[])
specs=[]
for d in dims:
    alt=d.get("alt_names",[])
    if isinstance(alt,str):alt=[s.strip()for s in alt.split(",")]
    specs.append({"name":d["name"],"desc":d["description"],"type":TYPE_MAP.get(d["type"],"None"),
        "alt":alt,"dep":d.get("deprecated",False)})
o=[]
o.append("// This file was programatically generated from 'pdal/Dimension.json'.")
o.append("// Do not edit directly.");o.append("");o.append("#pragma once");o.append("")
o.append("#include <string>");o.append("#include <vector>");o.append("")
o.append("#include <pdal/DimUtil.hpp>");o.append("#include <pdal/pdal_types.hpp>")
o.append("#include <pdal/util/Utils.hpp>");o.append("");o.append("namespace pdal")
o.append("{");o.append("namespace Dimension");o.append("{");o.append("")
o.append("enum class Id");o.append("{");o.append("    Unknown,")
for i,d in enumerate(specs):
    c=","if i<len(specs)-1else""
    o.append(f"    {d['name']}{c} ///< \\brief {d['desc']}")
    o.append(f"    {'':<{len(d['name'])+5}}///< \\default {d['type']}")
o.append("};");o.append("typedef std::vector<Id> IdList;");o.append("")
o.append("/// Get a description of a predefined dimension.");o.append("/// \\param[in] id  Dimension ID.")
o.append("/// \\return  Dimension description.");o.append("inline std::string description(Id id)")
o.append("{");o.append("    switch (id)");o.append("    {")
for d in specs:
    o.append(f"    case Id::{d['name']}:")
    o.append(f'        return "{d["desc"]}";')
o.append("    case Id::Unknown:");o.append('        return "";');o.append("    }")
o.append('    return "";');o.append("}");o.append("")
o.append('/// Get a predefined dimension ID given a dimension name.')
o.append('/// \\param[in] s  Name of dimension.');o.append('/// \\return  Dimension ID.')
o.append("inline Id id(std::string s)");o.append("{");o.append("    s = Utils::toupper(s);");o.append("")
for d in specs:
    for nm in[d["name"]]+d["alt"]:
        o.append(f'    if (s == "{nm.upper()}")')
        o.append(f'        return Id::{d["name"]};')
o.append("    return Id::Unknown;");o.append("}");o.append("")
o.append("/// Get the name of a predefined dimension.");o.append("/// \\param[in] id  Dimension ID")
o.append("/// \\return  Dimension name.");o.append("inline std::string name(Id id)")
o.append("{");o.append("    switch (id)");o.append("    {")
for d in specs:
    o.append(f"    case Id::{d['name']}:");o.append(f'        return "{d["name"]}";')
o.append("    case Id::Unknown:");o.append('        return "";');o.append("    }")
o.append('    return "";');o.append("}");o.append("")
o.append("/// Get the default storage type of a predefined dimension.")
o.append("/// \\param id  ID of the predefined dimension.")
o.append("/// \\return  The dimension's default storage type.")
o.append("inline Type defaultType(Id id)");o.append("{");o.append("    switch (id)");o.append("    {")
for d in specs:
    o.append(f"    case Id::{d['name']}:");o.append(f"        return Type::{d['type']};")
o.append('    case Id::Unknown:')
o.append('        throw pdal_error("No type found for undefined dimension.");')
o.append("    }")
o.append('    throw pdal_error("No type found for undefined dimension.");')
o.append("}");o.append("")
o.append("/// Check whether a predefined dimension is deprecated.")
o.append("/// \\param[in] id  Dimension ID.");o.append("/// \\return  True if deprecated, otherwise false.")
o.append("inline bool isDeprecated(Id id)");o.append("{");o.append("    switch (id)");o.append("    {")
for d in specs:
    if d["dep"]:o.append(f"    case Id::{d['name']}:")
o.append("        return true;");o.append("    default:");o.append("        return false;")
o.append("    }");o.append("}");o.append("");o.append("} // namespace Dimension")
o.append("} // namespace pdal");o.append("")
with open(sys.argv[2],"w") as f:f.write("\n".join(o))
'''

    def generate(self):
        tc = CMakeToolchain(self)
        # Point to system-installed dependencies (via cmd-pkgs)
        tc.cache_variables["CMAKE_PREFIX_PATH"] = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
        # Disable features not needed for HarmonyOS
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["WITH_TESTS"] = False
        tc.cache_variables["WITH_BACKTRACE"] = False
        tc.cache_variables["WITH_GCS"] = False
        tc.cache_variables["WITH_COMPLETION"] = False
        tc.cache_variables["BUILD_TOOLS_LASDUMP"] = False
        # Disable all optional plugins
        for plugin in ["CPD", "DRACO", "ICEBRIDGE", "HDF", "MATLAB", "NITF",
                       "OPENSCENEGRAPH", "PGPOINTCLOUD", "RIVLIB", "RDBLIB",
                       "MBIO", "FBX", "TEASER", "TILEDB", "TRAJECTORY",
                       "E57", "ARROW", "SPZ"]:
            tc.cache_variables[f"BUILD_PLUGIN_{plugin}"] = False
        # Allow unresolved symbols in shared libs (GDAL transitive deps)
        # Use bfd linker (lld can't handle --allow-shlib-undefined on HarmonyOS)
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-fuse-ld=bfd -Wl,--allow-shlib-undefined"
        tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = "-fuse-ld=bfd -Wl,--allow-shlib-undefined"
        # Use Python script instead of dimbuilder binary (HarmonyOS SELinux workaround)
        # CMAKE_CROSSCOMPILING=ON prevents make from building/running dimbuilder target
        dimbuilder_path = os.path.join(self.source_folder, "scripts", "gen_dimension.py")
        tc.cache_variables["DIMBUILDER_EXECUTABLE"] = f"python3 {dimbuilder_path}"
        tc.cache_variables["CMAKE_CROSSCOMPILING"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["pdalcpp"]
        self.cpp_info.set_property("cmake_file_name", "PDAL")
        self.cpp_info.set_property("cmake_target_name", "PDAL::PDAL")
        self.cpp_info.set_property("pkg_config_name", "pdal")

        # PDAL has a command-line tool
        self.cpp_info.bindirs = ["bin"]
