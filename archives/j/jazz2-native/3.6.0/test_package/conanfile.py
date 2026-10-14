#!/usr/bin/env python3
"""Conan test_package for jazz2-native 3.6.0 (application).

jazz2-native 是 SDL2/OpenGL ES 2 图形游戏，常规启动需要显示设备。上游 main()
原生支持 `--version` 早退路径（Sources/Main.cpp:2243，先于任何 SDL/GL 初始化），
因此无需打补丁即可在 headless CI 上验证：

  - 二进制存在且可加载（共享依赖 OpenAL/curl 可解析，SDL2/zlib 由配方静态链接）；
  - ELF 已自签（未签名在 OHOS 上运行报 Operation not permitted）；
  - 版本字符串与配方版本一致。

具体断言逻辑在 test_jazz2_native.sh（L0c 门禁要求 test_package 下有测试源文件）。
"""
import os
import tempfile

from conan import ConanFile


class Jazz2NativeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # jazz2-native 是 application 包：其运行时依赖在消费者/测试图中被标为
        # "Skipped binaries"（cpp_info 只剩相对 libdirs、package_folder 为空），
        # VirtualRunEnv 因此漏掉 OpenAL。OpenAL 是本二进制唯一需动态解析的第三方共享库
        # （SDL2/zlib 由配方静态链接），显式声明使测试图解析出真实包目录。
        self.requires("openal-soft/1.25.2")

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return

        pkg = self.dependencies["jazz2-native"].package_folder
        exe = os.path.join(pkg, "bin", "jazz2")
        assert os.path.isfile(exe), f"jazz2 not found at {exe}"

        # 运行库路径：制品包只装 bin/ 与 share/，动态依赖（OpenAL/curl/vorbis/ogg）由消费者
        # 提供。从依赖图取各包 libdirs（部分包在消费者侧只有相对目录 "lib"，按 package_folder
        # 解析），并把 LD_LIBRARY_PATH 内联进命令行 —— 实测 conan run env 列表在本环境不生效
        # （同仓库 acsccid 先例：env= 传入的 LD_LIBRARY_PATH 被忽略，二进制报 127）。
        lib_paths = []
        dep_names = []
        for dep in self.dependencies.values():
            dep_names.append(str(dep.ref))
            ci = dep.cpp_info
            raw_dirs = list(ci.libdirs)
            try:
                raw_dirs += list(ci.aggregated_components().libdirs)
            except Exception:
                pass
            for libdir in raw_dirs:
                if not libdir:
                    continue
                if os.path.isabs(libdir):
                    path = libdir
                elif dep.package_folder:
                    path = os.path.join(dep.package_folder, libdir)
                else:
                    continue
                if os.path.isdir(path) and path not in lib_paths:
                    lib_paths.append(path)
        self.output.info("运行时依赖: %s" % ", ".join(dep_names))
        self.output.info("运行时库路径: %s" % ":".join(lib_paths))

        # 输出写临时目录，避免污染 repo 的 test_package/
        test_script = os.path.join(self.source_folder, "test_jazz2_native.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        ld_prefix = 'LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"' % ":".join(lib_paths)
        with tempfile.TemporaryDirectory() as out_dir:
            self.run('%s %s "%s" "%s" "%s"' % (ld_prefix, bash, test_script, exe, out_dir))
