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
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


# Qt5 source URL for building the XML module
QT5_SOURCE_URL = "https://mirrors.tuna.tsinghua.edu.cn/qt/archive/qt/5.15/5.15.2/submodules/qtbase-everywhere-src-5.15.2.tar.xz"
QT5_SOURCE_SHA256 = "909fad2591ee367993a75d7e2ea50ad4db332f05e1c38dd7a5a274e156a4e0f8"


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

    def _build_qt5xml(self, qt5_prefix):
        """Build Qt5Xml module from Qt5 source (qt5-qtbase was built with -no-feature-xml)."""
        # Check if Qt5Xml already exists
        qt5xml_lib = os.path.join(qt5_prefix, "lib", "libQt5Xml.so")
        if os.path.exists(qt5xml_lib):
            return

        # Download Qt5 source
        qt5_src_dir = os.path.join(self.build_folder, "qt5-src")
        get(self, QT5_SOURCE_URL, sha256=QT5_SOURCE_SHA256,
            destination=os.path.dirname(qt5_src_dir))
        qt5_src = qt5_src_dir

        # Run syncqt.pl to generate QtXml headers
        syncqt = os.path.join(qt5_src, "bin", "syncqt.pl")
        self.run(f'perl "{syncqt}" -version 5.15.2 -module QtCore -module QtXml '
                 f'-outdir "{qt5_src}/include" "{qt5_src}"')

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
        cxx = "clang++"
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
            self.run(f'{cxx} {cxxflags} {includes} -c "{os.path.join(xml_src, src)}" -o "{obj}"')
            objs.append(obj)

        # Link
        lib_out = os.path.join(xml_src, "libQt5Xml.so.5.15.2")
        self.run(f'{cxx} -shared -Wl,-soname,libQt5Xml.so.5 -o "{lib_out}" '
                 f'{" ".join(objs)} -L{qt5_prefix}/lib -lQt5Core -lpthread -ldl')

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
        pri_content = f"""QT.xml.VERSION = 5.15.2
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

        # Fix qt.conf
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

        # Create build dir symlinks (qmake uses hardcoded build paths)
        # The build dir hash is in the conan cache
        for d in os.listdir(os.path.expanduser("~/.conan2/p/b")):
            if d.startswith("qt5-"):
                build_path = os.path.join(os.path.expanduser("~/.conan2/p/b"), d, "b")
                for sub in ["mkspecs", "include", "lib", "bin", "src",
                             "plugins", "libexec"]:
                    link = os.path.join(build_path, sub)
                    if not os.path.exists(link):
                        try:
                            os.symlink(os.path.join(qt5_prefix, sub), link)
                        except (OSError, FileExistsError):
                            pass
                break

    def generate(self):
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_prefix = qt5.package_folder

        # Include both Qt5 pkgconfig and system pkgconfig (for libaccounts-glib)
        system_pkg = "/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig"
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(qt5_prefix, "lib"))
        env.prepend_path("PKG_CONFIG_PATH", system_pkg)
        # Prepend to LD_LIBRARY_PATH so lld can find libxml2.so.16
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qt5_prefix, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", "/storage/Users/currentUser/usr/local/lib")
        env.prepend_path("LD_LIBRARY_PATH", "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib")
        env.define("TMPDIR", os.environ.get("TMPDIR", os.path.expanduser("~/tmp")))
        envvars = env.vars(self)
        envvars.save_script("libaccounts_qt_env")

    def build(self):
        apply_conandata_patches(self)

        qt5 = self.dependencies["qt5-qtbase"]
        qt5_prefix = qt5.package_folder

        # Build Qt5Xml module (qt5-qtbase was built without XML support)
        self._build_qt5xml(qt5_prefix)

        # Remove doc generation (doxygen not available on OHOS)
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
