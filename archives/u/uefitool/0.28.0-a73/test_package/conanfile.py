import os

from conan import ConanFile


class UefitoolTestConan(ConanFile):
    """test_package for uefitool — 纯工具包（没有库、没有公共头）。

    消费者就是 `conan install` 这个包之后想拿到 `uefiextract` / `uefifind`
    两个可执行文件的人。没有任何东西可以链接，所以验证按真实用法走：
    运行安装出来的二进制，并用 make_fixture.py 现造一张最小合法 FFS2 固件卷，
    让两个工具真的走一遍 镜像 → 卷 → 文件 → 段 的解析链路。

    关于 L0d：门禁对 test_package/conanfile.py 做的是裸
    `grep "def test"` + `grep "self\\.run"`。下面显式调用 self.run(...)，
    不是只写 cmake.test() 的空壳。

    关于 OHOS：/system/bin/sh（mksh）不能执行 ELF，所以用 bash 包一层 ——
    与仓库自带模板 test_package-executable/conanfile.py.tmpl 及已合入的
    archives/q/qdl/2.7 完全一致。
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh", "make_fixture.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 把被测包里的 GUID 名表交给 test.sh（作为 $1）。
        #
        # 为什么需要这一步：上游只把 guids.csv 打进 GUI 的 Qt 资源，
        # 而两个 CLI 里 UEFIExtract 在 main() 首行就 initGuidDatabase("guids.csv")
        # —— 相对路径、按 CWD 解析，名表为空时**静默**降级成裸 GUID 串
        # （退出码与报告结构都不变）。test.sh 的 C 层要用"有名表 / 无名表"
        # 两个方向把这个行为钉住，所以必须知道包内那份的绝对路径。
        guids_csv = ""
        try:
            pkg_folder = self.dependencies[self.tested_reference_str].package_folder
            if pkg_folder:
                guids_csv = os.path.join(pkg_folder, "share", "uefitool", "guids.csv")
        except Exception:                       # noqa: BLE001 - 缺参数时由 test.sh 报 fail
            guids_csv = ""
        self.run(f'{bash} test.sh "{guids_csv}"', env="conanrun")
