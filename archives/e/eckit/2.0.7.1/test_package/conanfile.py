import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["eckit"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        cc = os.environ.get("CXX", "clang++")
        # 库本体按 profile 的 cppstd 编，测试标准必须跟上，
        # 否则库头里的 C++17 设施（std::void_t / is_arithmetic_v 等）全报找不到。
        _std = self.settings.get_safe("compiler.cppstd")
        std_flag = ("-std=c++%s" % str(_std).replace("gnu", "")) if _std else ""
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs]
                        + ["-Wl,-rpath," + p for p in libdirs])
        self.run(f"{cc} {std_flag} test.cpp -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 同 package() 的签名器一类缺陷：写死 /data/service/hnp/bin/bash 在新机不存在（rc=127，
        # create-eckit-2.log:1976 实证），会把 test_package 全部断言吞掉。运行时定位，最后回落 /bin/sh。
        home = os.path.expanduser("~")
        bash = next((c for c in [
            os.environ.get("CONFIG_SHELL") or "",
            "/data/service/hnp/bin/bash",
            os.path.join(home, "usr/local/bin/bash"),
            os.path.join(home, ".harmonybrew/bin/bash"),
            "/bin/bash", "/bin/sh",
        ] if c and os.path.isfile(c)), "/bin/sh")
        self.output.info("test_package shell: %s" % bash)
        self.run(f"{bash} -c './test_probe'", env="conanrun")
