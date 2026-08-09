#!/usr/bin/env python3
"""Conan recipe for libaccounts-qt 1.13 — qmake build system.

libaccounts-qt is a Qt library for managing online account configurations
and authentication tokens. It wraps libaccounts-glib with a Qt API.

Build system: qmake (.pro files)
Dependencies: qt5-qtbase/5.15.2 (conan), libaccounts-glib (system pkg-config)

Note: The qt5-qtbase conan package was built with -no-feature-xml, so
Qt5Xml is not included. This recipe builds Qt5Xml from the Qt5 source
as part of the build process.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LibaccountsQtConan(ConanFile):
    name = "libaccounts-qt"
    version = "1.13"
    description = "Qt library for managing online account configurations and authentication"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/ubports/libaccounts-qt"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libaccounts-qt only supports Linux and OHOS, got {self.settings.os}"
            )
        self.requires("qt5-qtbase/5.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cxx(self):
        """Get C++ compiler from Conan profile (R33)."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("cxx")
        if not cxx:
            raise ConanInvalidConfiguration(
                "libaccounts-qt requires cpp compiler from Conan profile"
            )
        return cxx

    def _build_qt5xml(self, qt5_prefix, cxx):
        """Build Qt5Xml module from Qt5 source (qt5-qtbase was built with -no-feature-xml)."""
        # Check if Qt5Xml already exists
        qt5xml_lib = os.path.join(qt5_prefix, "lib", "libQt5Xml.so")
        if os.path.exists(qt5xml_lib):
            self.output.info("Qt5Xml already available, skipping build")
            return

        # Get Qt5 source URL from conandata
        qt5_src_data = self.conan_data.get("qt5_source", {})
        qt5_src_url = qt5_src_data.get("url", "")
        qt5_src_sha256 = qt5_src_data.get("sha256", "")

        if not qt5_src_url:
            raise ConanInvalidConfiguration("Qt5 source URL not found in conandata.yml")

        # Download Qt5 source
        qt5_src_dir = os.path.join(self.build_folder, "qt5-src")
        get(self, qt5_src_url, sha256=qt5_src_sha256,
            destination=qt5_src_dir, strip_root=True)
        qt5_src = qt5_src_dir

        # Run syncqt.pl to generate QtXml headers
        syncqt = os.path.join(qt5_src, "bin", "syncqt.pl")
        self.run(f'perl "{syncqt}" -version 5.15.2 -module QtCore -module QtXml '
                 f'-outdir "{qt5_src}/include" "{qt5_src}"',
                 env=["conanbuild", "libaccounts_qt_env"])

        # Create qtxml-config.h
        qtxml_inc_dir = os.path.join(qt5_src, "include", "QtXml")
        os.makedirs(qtxml_inc_dir, exist_ok=True)
        with open(os.path.join(qtxml_inc_dir, "qtxml-config.h"), "w") as f:
            f.write("#ifndef QTXML_CONFIG_H\n#define QTXML_CONFIG_H\n#endif\n")

        # Create private header symlinks
        priv_dir = os.path.join(qt5_src, "src", "xml", "private")
        os.makedirs(priv_dir, exist_ok=True)
        for name, target in [("qdom_p.h", "../dom/qdom_p.h"),
                              ("qdomhelpers_p.h", "../dom/qdomhelpers_p.h"),
                              ("qxml_p.h", "../sax/qxml_p.h"),
                              ("qxmlutils_p.h", "../../corelib/serialization/qxmlutils_p.h")]:
            link = os.path.join(priv_dir, name)
            if not os.path.exists(link):
                os.symlink(target, link)

        # Compile flags
        cxxflags = "-fPIC -O2 -std=c++11 -DQT_NO_USING_NAMESPACE -DQT_NO_FOREACH "
        cxxflags += "-DQT_BUILDING_QT -DQT_XML_LIB -DQT_CORE_LIB -DQT_SHARED "
        cxxflags += "-fvisibility=hidden -fno-exceptions"

        # Include paths
        includes = f'-I{qt5_prefix}/include -I{qt5_prefix}/include/QtCore '
        includes += f'-I{qt5_prefix}/include/QtCore/5.15.2 '
        includes += f'-I{qt5_prefix}/include/QtCore/5.15.2/QtCore '
        includes += f'-I{qt5_src}/include -I{qt5_src}/include/QtCore '
        includes += f'-I{qt5_src}/include/QtCore/5.15.2 '
        includes += f'-I{qt5_src}/include/QtCore/5.15.2/QtCore '
        includes += f'-I{qt5_src}/include/QtXml -I{qt5_src}/include/QtXml/5.15.2/QtXml '
        includes += f'-I{qt5_src}/src/xml -I{qt5_src}/src/xml/private '
        includes += f'-I{qt5_prefix}/mkspecs/linux-clang -I{qt5_prefix}/mkspecs/common/posix '
        includes += f'-I{qt5_src}/src/corelib -I{qt5_src}/src/corelib/serialization'

        xml_src = os.path.join(qt5_src, "src", "xml")
        objs = []
        for src in ["dom/qdom.cpp", "dom/qdomhelpers.cpp", "sax/qxml.cpp"]:
            obj = os.path.join(xml_src, os.path.basename(src).replace(".cpp", ".o"))
            self.run(f'"{cxx}" {cxxflags} {includes} -c "{os.path.join(xml_src, src)}" -o "{obj}"',
                     env=["conanbuild", "libaccounts_qt_env"])
            objs.append(obj)

        # Link
        lib_out = os.path.join(xml_src, "libQt5Xml.so.5.15.2")
        self.run(f'"{cxx}" -shared -Wl,-soname,libQt5Xml.so.5 -o "{lib_out}" '
                 f'{" ".join(objs)} -L{qt5_prefix}/lib -lQt5Core -lpthread -ldl',
                 env=["conanbuild", "libaccounts_qt_env"])

        # Install to Qt5 package
        qt5_lib = os.path.join(qt5_prefix, "lib")
        shutil.copy(lib_out, qt5_lib)
        for link, target in [("libQt5Xml.so.5", "libQt5Xml.so.5.15.2"),
                              ("libQt5Xml.so", "libQt5Xml.so.5.15.2")]:
            link_path = os.path.join(qt5_lib, link)
            if os.path.exists(link_path):
                os.remove(link_path)
            os.symlink(target, link_path)

        # Install headers
        qtxml_dest = os.path.join(qt5_prefix, "include", "QtXml")
        if not os.path.exists(qtxml_dest):
            shutil.copytree(os.path.join(qt5_src, "include", "QtXml"), qtxml_dest)

        # Install 5.15.2 private headers
        priv_dest = os.path.join(qt5_prefix, "include", "QtXml", "5.15.2", "QtXml", "private")
        os.makedirs(priv_dest, exist_ok=True)
        for name in ["qdom_p.h", "qdomhelpers_p.h", "qxml_p.h"]:
            src_file = os.path.join(qt5_src, "src", "xml",
                                    "dom" if "dom" in name else "sax", name)
            if os.path.exists(src_file):
                shutil.copy(src_file, priv_dest)

        # Create qt_lib_xml.pri
        pri_content = """QT.xml.VERSION = 5.15.2
QT.xml.name = QtXml
QT.xml.module = Qt5Xml
QT.xml.libs = $$QT_MODULE_LIB_BASE
QT.xml.includes = $$QT_MODULE_INCLUDE_BASE $$QT_MODULE_INCLUDE_BASE/QtXml
QT.xml.frameworks =
QT.xml.depends = core
QT.xml.uses =
QT.xml.module_config = v2
QT.xml.CONFIG = moc
QT.xml.DEFINES = QT_XML_LIB
QT_MODULES += xml
"""
        for d in ["modules-inst", "modules"]:
            pri_path = os.path.join(qt5_prefix, "mkspecs", d, "qt_lib_xml.pri")
            os.makedirs(os.path.dirname(pri_path), exist_ok=True)
            with open(pri_path, "w") as f:
                f.write(pri_content)

        # Create Qt5Xml.pc
        pc_content = f"""prefix={qt5_prefix}
exec_prefix=${{prefix}}
libdir=${{exec_prefix}}/lib
includedir=${{prefix}}/include

Name: Qt5Xml
Description: Qt XML module
Version: 5.15.2
Libs: -L${{libdir}} -lQt5Xml
Cflags: -I${{includedir}} -I${{includedir}}/QtXml
Requires: Qt5Core
"""
        with open(os.path.join(qt5_lib, "Qt5Xml.pc"), "w") as f:
            f.write(pc_content)

        # Fix qt.conf with absolute paths
        qt_conf = os.path.join(qt5_prefix, "bin", "qt.conf")
        with open(qt_conf, "w") as f:
            f.write(f"""[EffectivePaths]
Prefix={qt5_prefix}
[DevicePaths]
Prefix={qt5_prefix}
[Paths]
Prefix={qt5_prefix}
HostPrefix={qt5_prefix}
Sysroot=
SysrootifyPrefix=false
TargetSpec=linux-clang
HostSpec=linux-clang
""")

        # Create build dir symlinks (qmake has hardcoded build paths in binary)
        # This is necessary because qmake looks for mkspecs in the build directory
        # even when qt.conf is set. The symlinks redirect to the package directory.
        conan_b_dir = os.path.join(os.path.expanduser("~"), ".conan2", "p", "b")
        if os.path.isdir(conan_b_dir):
            for d in os.listdir(conan_b_dir):
                if d.startswith("qt5-"):
                    build_path = os.path.join(conan_b_dir, d, "b")
                    if os.path.isdir(build_path):
                        for sub in ["mkspecs", "include", "lib", "bin", "src",
                                     "plugins", "libexec"]:
                            link = os.path.join(build_path, sub)
                            if not os.path.exists(link):
                                try:
                                    os.symlink(os.path.join(qt5_prefix, sub), link)
                                except OSError:
                                    pass  # Symlink creation may fail, non-critical
                    break

    def generate(self):
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_prefix = qt5.package_folder

        env = Environment()
        # Add Qt5 pkgconfig path and system pkgconfig for libaccounts-glib
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(qt5_prefix, "lib"))
        # Prepend to LD_LIBRARY_PATH for lld linker and runtime
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qt5_prefix, "lib"))
        # Use environment paths for system libraries (libaccounts-glib, etc.)
        sys_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if sys_ld:
            env.prepend_path("LD_LIBRARY_PATH", sys_ld)
        sys_pkg = os.environ.get("PKG_CONFIG_PATH", "")
        if sys_pkg:
            env.prepend_path("PKG_CONFIG_PATH", sys_pkg)
        env.define("TMPDIR", os.environ.get("TMPDIR", os.path.expanduser("~/tmp")))
        envvars = env.vars(self)
        envvars.save_script("libaccounts_qt_env")

    def build(self):
        apply_conandata_patches(self)

        qt5 = self.dependencies["qt5-qtbase"]
        qt5_prefix = qt5.package_folder

        # Get compiler from Conan profile (R33)
        cxx = self._get_cxx()

        # Build Qt5Xml module (qt5-qtbase was built without XML support)
        self._build_qt5xml(qt5_prefix, cxx)

        # Remove doc generation (doxygen not available on OHOS)
        # Done in build() before qmake generates Makefile
        pro_path = os.path.join(self.source_folder, "accounts-qt.pro")
        with open(pro_path, "r") as f:
            pro_content = f.read()
        pro_content = pro_content.replace("include( doc/doc.pri )", "")
        with open(pro_path, "w") as f:
            f.write(pro_content)

        qmake = os.path.join(qt5_prefix, "bin", "qmake")
        install_prefix = "/usr/local"
        source_dir = self.source_folder
        pro_file = os.path.join(source_dir, "accounts-qt.pro")

        # Run qmake with the project file
        self.run(
            f'cd "{source_dir}" && "{qmake}" "{pro_file}" PREFIX={install_prefix} LIBDIR={install_prefix}/lib',
            env=["conanbuild", "libaccounts_qt_env"],
        )

        # Build from source directory
        self.run(f'cd "{source_dir}" && make -j1', env=["conanbuild", "libaccounts_qt_env"])

    def package(self):
        source_dir = self.source_folder
        # Install using make install with INSTALL_ROOT
        # Use -o docs to skip the doxygen dependency (not available on OHOS)
        self.run(
            f'cd "{source_dir}" && make -o docs install INSTALL_ROOT={self.package_folder}',
            env=["conanbuild"],
        )

    def package_info(self):
        # The library is named accounts-qt5 for Qt5 builds
        self.cpp_info.libs = ["accounts-qt5"]

        # Set up include paths (so #include <Accounts/Manager> works)
        self.cpp_info.includedirs = ["usr/local/include/accounts-qt5"]

        # Set up libdirs
        self.cpp_info.libdirs = ["usr/local/lib"]

        # Add pkg-config info
        self.cpp_info.set_property("pkg_config_name", "accounts-qt5")
