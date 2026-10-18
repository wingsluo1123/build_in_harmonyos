import glob
import os
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment

# 消费侧验证：用随 test_package 交付的上游语法样例（examples/fact/fact.g）
# 真跑一次生成器 —— 与消费方 KDevelop 的 KDEVPGQT_GENERATE 宏同一调用形态
# （`kdev-pg-qt --output=<name> <grammar.g>`），断言生成了非空输出文件。
class KDevelopPgQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _grammar_path(self):
        for folder in (self.recipe_folder, self.source_folder):
            candidate = os.path.join(folder, "fact.g")
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "fact.g fixture not found in the test_package folder"
        )

    def test(self):
        if not can_run(self):
            return

        pkg = self.dependencies[self.tested_reference_str].package_folder
        generator = os.path.join(pkg, "bin", "kdev-pg-qt")
        if not os.path.isfile(generator):
            raise ConanInvalidConfiguration(
                "kdev-pg-qt generator is missing from the package (bin/)"
            )

        # 输出写到系统临时目录：`conan create` 时 test_package 的 build_folder 就是
        # test_package 目录本身，写在那里会污染工作区（实测生成器产物会被误提交，
        # 而 CI 的 JC 杂项检查会拦构建产物）。
        out_dir = tempfile.mkdtemp(prefix="kdevpg-qt-test-")
        self.output.info("generator output dir: %s" % out_dir)

        grammar = self._grammar_path()
        # 与配方内跑 ctest 同一经验：OHOS 上这些 ELF 没有 RUNPATH，运行时只能靠
        # LD_LIBRARY_PATH（实测：只用 Environment().apply() 时子进程拿不到该变量，
        # 生成器会报 "...: symbol not found" 并以 127 退出）。故直接内联进命令。
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    lib_dirs.append(lib_dir)
        env_prefix = (
            'PATH="%s:$PATH" LD_LIBRARY_PATH="%s" QT_QPA_PLATFORM=offscreen '
            % (os.path.join(pkg, "bin"), os.pathsep.join(lib_dirs))
        )
        # smoke.sh：与下述 python 断言同一调用形态的真跑冒烟（L0c 要求测试源文件；
        # 本脚本断言生成器真跑且产出非空 factparser.cpp）。env_prefix 必须先构造好。
        smoke = os.path.join(self.recipe_folder, "smoke.sh")
        self.run(
            env_prefix +
            'sh "{smoke}" kdev-pg-qt "{grammar}"'.format(smoke=smoke, grammar=grammar)
        )
        # 必须用 sh -c 包住整条命令：写成 `VAR=... cd X && gen ...` 时内联变量
        # 只作用于 `cd`，`&&` 之后的生成器拿不到（实测退出码 127 = 命令找不到）。
        self.run(
            env_prefix +
            'sh -c \'cd "{out}" && kdev-pg-qt --output=fact "{grammar}"\''.format(
                out=out_dir, grammar=grammar
            )
        )

        produced = sorted(
            path for path in glob.glob(os.path.join(out_dir, "fact*"))
            if os.path.isfile(path) and os.path.getsize(path) > 0
        )
        if len(produced) < 3:
            raise ConanInvalidConfiguration(
                "generator produced too few non-empty files from fact.g: %r"
                % ([os.path.basename(p) for p in produced],)
            )
        # 生成器至少要产出解析器实现这个关键件（实测 --output=fact 得到
        # factparser.cpp/h、factast.h、factvisitor.cpp/h、factdefaultvisitor.*、
        # facttokentype.h、factast-fwd.h 共 9 个文件；名字不带下划线）。
        names = [os.path.basename(path) for path in produced]
        if not any(name.endswith("parser.cpp") for name in names):
            raise ConanInvalidConfiguration(
                "no *parser.cpp generated (got: %r)" % (names,)
            )
        self.output.info(
            "kdev-pg-qt generated %d files from fact.g: %s"
            % (len(produced), names)
        )
