#!/usr/bin/env python3
"""Consumer test for libcontentaction 0.4.13 (upstream sailfishos/libcontentaction).

The consumer links the packaged library and drives a complete consumer
workflow end to end: fixture configuration on disk -> ContentInfo -> Action
lookup -> mime default roundtrip -> highlight search -> trigger() with
execution-trace verification (rule12).
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibcontentactionTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式锁定 qtbase 版本（与主配方 conanfile.py 的 requires 一致，亦同
        # kdbusaddons 先例）：消费者直接 include Qt 头文件并链接 Qt6::Test，
        # 不应依赖传递闭包给出该版本，避免版本来源歧义导致解析失败。
        self.requires("qtbase/6.11.1.1", transitive_headers=True, transitive_libs=True)
        # glib：需要它的 bin 目录（gio-launch-desktop）注入消费者运行时 PATH。
        # 显式声明以便 generate() 稳定取到**目标**包目录（版本与主配方逐字一致）。
        self.requires("glib/2.84.0.2", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # qtbase 以 cmake_find_mode=none 发布：由 CMakeLists 用 LCA_QT_PREFIX 注入
        qt = self.dependencies.get("qtbase")
        if qt is not None:
            tc.variables["LCA_QT_PREFIX"] = qt.package_folder
        # 被测包按包目录绝对路径链接（消费者视角：公开头 + 库文件）
        pkg = self.dependencies["libcontentaction"].package_folder
        tc.variables["LCA_INCLUDEDIR"] = os.path.join(pkg, "include")
        tc.variables["LCA_LIBRARY"] = os.path.join(pkg, "lib", "libcontentaction6.so")
        # 运行期搜索路径：只按绝对路径链接时，加载器不会记住该路径，必须在 RUNPATH
        # 里显式给出 lib 目录，否则运行消费者报
        #   Error loading shared library libcontentaction6.so.0 (needed by ./test_lca_consumer)
        #   Error relocating ...: symbol not found   -> 退出码 127（CI #79867 实测）
        tc.variables["LCA_LIBDIR"] = os.path.join(pkg, "lib")
        # ★glib helper 目录★（CI 上 trigger 断言失败的真因，2026-10-13 定位）
        # GIO ≥ 2.80 起，`g_app_info_launch()` 不再自己 fork，而是调用 glib 的
        # `gio-launch-desktop` 辅助程序；glib 按 **PATH** 查找它。
        # 本配方的库侧 ctest 环境早已把该目录放进 PATH（见 port/CMakeLists.txt 的
        # LCA_GLIB_BIN_PATH，CI 日志 `glib helper dir = .../glib78779b4fd7fde/p/bin`），
        # 但 **test_package 的 conanrun 环境不含它**，于是：
        #   普通 fork（sh -c ...）成功，而 GIO 的 trigger() 找不到 helper -> 静默失败，
        #   marker 永不产生 -> 断言 FAIL。
        # 本机已精确复现并验证（同一二进制，仅改 PATH）：
        #   PATH=/usr/bin:/bin        -> direct-fork rc=0，GIO trigger FAIL
        #   PATH=<glib>/bin:/usr/bin  -> direct-fork rc=0，GIO trigger PASS
        # 故这里把 glib 包 bin 目录显式交给消费者（经 LCA_GLIB_BIN 传入，
        # 由 test() 注入到运行时 PATH 最前），使消费者与库侧测试床同口径。
        glib = self.dependencies.get("glib")
        if glib is not None:
            tc.variables["LCA_GLIB_BIN"] = os.path.join(glib.package_folder, "bin")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_lca_consumer")
        work = os.path.join(self.build_folder, "lca-consumer-work")
        args = '"{}" "{}"'.format(binary, work)
        # 可选：把 shared-mime-info 测试库交给消费者（argv[2]），使其能校验
        # ContentInfo::typeDescription()（OHOS 无系统 shared-mime-info）。
        # 该库不随配方提交（含 NUL 字节的二进制会让 PR diff 无法被 git apply），
        # 由本测试包在构建期用宿主 update-mime-database 从 XML 源生成。
        mime_db = self._mime_db()
        if mime_db:
            args += ' "{}"'.format(mime_db)
        # 阶段 2 的标记追加在**末尾**，且消费者是在全部 argv 中扫描该标记、
        # 不依赖它的位置。这样即使 mime 数据库不可用（argv 中不含 mime_db），
        # 阶段 2 依然会被执行 —— 修复了"无 update-mime-database 时第二次调用
        # 退化成阶段 1 重跑、回归校验被静默跳过却 exit 0"的假通过缺陷。
        phase2 = args + " check-default"
        if can_run(self):
            self._run_consumer(args)
            self._run_consumer(phase2)   # 新进程验证回退
            return
        # 交叉构建：经 qemu + OHOS 运行根执行消费者（与本地 harness/CI 同口径）
        emulator, prefix = self._emulator()
        if emulator:
            cmd = '"{}"{} {}'.format(emulator, prefix, args)
            self.run(cmd, env="conanrun")
            self.run('"{}"{} {}'.format(emulator, prefix, phase2), env="conanrun")
            self.output.info("consumer executed under qemu: {}".format(emulator))
        else:
            # 显式降级告警（不使用 info）：此分支下消费者只完成了**链接**、
            # 未真正执行，端到端断言并未在本环境生效。用 warning 让"仅编译通过"
            # 不会被误读为"e2e 通过"（本仓"静默放行"反模式）。
            self.output.warning(
                "cross-building: consumer was LINKED but NOT EXECUTED here; "
                "end-to-end assertions did not run in this environment. "
                "Execution evidence: reports/device-e2e-evidence.md (real device) "
                "and reports/test-report.md (qemu ohos-aarch64-run profile).")

    def _run_consumer(self, args):
        """执行消费者。

        ★为什么最终这样写（CI #80118 实测教训，勿轻易改动）★
        先试过两种更"聪明"的做法，**都被证伪**：
          1. 把包 lib/ 里的 libcontentaction*.so 复制到消费者目录、再设一条
             只含该目录的 LD_LIBRARY_PATH —— 结果库能找到了，但它**转而解析不到
             glib**：`libcontentaction6.so.0: g_content_type_get_icon: symbol not found`
             → 仍是 127。原因是这条路径丢掉了 conanrun 提供的 glib/Qt 目录，
             等于把"找不到库"换成了"库找不到依赖"，是本末倒置。
          2. `Environment().apply()` 包住 `self.run(..., env="conanrun")` ——
             Conan 会在命令前 `. conanrun.sh`，**覆盖**外层 apply 的值，
             实测无效（报错栈落在 _run_consumer -> self.run(args, env="conanrun")）。

        所以正解是：**保留 `env="conanrun"`**（它带齐 glib/Qt/被测包的 lib 目录，
        是唯一能同时满足"找到库"和"库找到依赖"的环境），不要自己另起一套。
        本方法与旧版行为一致，仅保留为显式命名以便日后加诊断。

        ★真因与修法★（CI trigger 断言失败，2026-10-13 定位）
        GIO ≥ 2.80 起 `g_app_info_launch()` 不再自己 fork，而是调用 glib 的
        `gio-launch-desktop`；glib 在 gdesktopappinfo.c 里的查找顺序为：
            ① 环境变量 `GIO_LAUNCH_DESKTOP`（非 setuid 时）
            ② 编译期写死的 GIO_LAUNCH_DESKTOP 路径（该文件可执行时）
            ③ 回退 "gio-launch-desktop"，即按 PATH 查找
          且结果经 `g_once_init_enter_pointer` **在本进程内只算一次并缓存**。
        `conanrun` 只保证**库**能加载，不含 glib 包的 `bin/`。

        本机实测（同一二进制）：
            PATH=/usr/bin:/bin（无 helper）
                -> DIAG: direct-fork rc=0（普通 fork 成功）
                   FAIL: trigger() executed the Desktop Entry Exec
            PATH=<glib>/bin:/usr/bin（helper 可达）
                -> ok : trigger() executed the Desktop Entry Exec
            PATH 无 helper 但显式 GIO_LAUNCH_DESKTOP=<glib>/bin/gio-launch-desktop
                -> ok : trigger() executed the Desktop Entry Exec   ← 最稳
        前两者受细节影响；第 ① 条最稳（绕开 PATH 查找）。
        CI 实测（#90302）：即使把 glib bin 前置进 PATH（DIAG 行可见），trigger 仍 FAIL，
        故这里设置 `GIO_LAUNCH_DESKTOP` 指向 helper 的绝对路径（走分支①）。

        ★注入方式（吸取本文件既有教训，勿再用 Environment().apply()）★
        本文件上文已记录：`Environment().apply()` 包住 `self.run(..., env="conanrun")`
        **实测无效** —— Conan 会在命令前 source conanrun.sh，覆盖外层 apply 的值。
        故这里改为**直接写 `os.environ`**：`self.run(env="conanrun")` 会把它作为
        子进程基础环境继承下去，conanrun.sh 只设置它自己声明过的变量
        （PATH/LD_LIBRARY_PATH 等），**不会清掉**我们额外设的 GIO_LAUNCH_DESKTOP。
        本机已实测该变量在消费者进程内可见。
        """
        glib_bin = self._glib_bin_dir()
        helper = os.path.join(glib_bin, "gio-launch-desktop") if glib_bin else None
        saved = {}
        if glib_bin:
            saved["PATH"] = os.environ.get("PATH")
            os.environ["PATH"] = glib_bin + os.pathsep + os.environ.get("PATH", "")
        if helper and os.path.isfile(helper):
            saved["GIO_LAUNCH_DESKTOP"] = os.environ.get("GIO_LAUNCH_DESKTOP")
            os.environ["GIO_LAUNCH_DESKTOP"] = helper
            self.output.info("gio-launch-desktop: {}".format(helper))
        else:
            self.output.info("gio-launch-desktop not found under glib package; "
                             "trigger assertion may fail")
        try:
            self.run(args, env="conanrun")
        finally:
            # 复原，避免影响后续步骤（同一 conanfile 会被多次调用）
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def _glib_bin_dir(self):
        """返回含 `gio-launch-desktop` 的 glib 包 bin 目录；找不到返回 None。"""
        glib = self.dependencies.get("glib")
        if glib is None:
            return None
        d = os.path.join(glib.package_folder, "bin")
        if os.path.isfile(os.path.join(d, "gio-launch-desktop")):
            return d
        return d if os.path.isdir(d) else None

    def _mime_db(self):
        """生成（或复用）shared-mime-info 测试库，返回 mime.cache 所在目录。

        配方只提交可读的 XML 源（port/mime-fixture/packages/lca-test-mime.xml）；
        含 NUL 字节的生成产物不随仓库提交，否则 GitCode 导出的 PR diff 会缺
        GIT binary patch 段、CI 的 git apply 直接失败。

        构建机没有 shared-mime-info 时**降级**：返回 None，消费者会跳过依赖类型
        描述的那一项断言（其余检查照常执行），绝不因此中断整个 test_package。
        """
        # 夹具 XML 的位置在**两种布局**下不同，必须都试：
        #   * `conan create archives/l/libcontentaction/0.4.13`（CI 口径）：
        #     recipe_folder = <...>/0.4.13/test_package，夹具在
        #     <...>/0.4.13/port/mime-fixture/...
        #   * 本地验证 harness 的暂存布局：夹具在 test_package 的**父目录**下
        #     （<...>/libcontentaction-0.4.13/port/...，与 test_package 同级）。
        # 历史缺陷：原先只按 dirname(recipe_folder) 推导，在 CI 口径下 isfile 恒为
        # False → 静默跳过 typeDescription 断言（断言数由 26 降为 25 且无任何提示）。
        candidates = [
            os.path.join(self.recipe_folder, "port", "mime-fixture", "packages",
                         "lca-test-mime.xml"),
            os.path.join(os.path.dirname(self.recipe_folder), "port", "mime-fixture",
                         "packages", "lca-test-mime.xml"),
        ]
        src = next((c for c in candidates if os.path.isfile(c)), None)
        if src is None:
            # 不静默：明确告知夹具缺失及其后果（该断言将被跳过）。
            self.output.warning(
                "mime fixture XML not found in any known layout: {}; "
                "the ContentInfo::typeDescription() assertion will be skipped"
                .format(candidates))
            return None
        tool = shutil.which("update-mime-database")
        if not tool:
            self.output.warning(
                "update-mime-database not found; skipping ContentInfo description check")
            return None
        db = os.path.join(self.build_folder, "mime-fixture-db")
        cache = os.path.join(db, "mime.cache")
        if not os.path.isfile(cache):
            try:
                os.makedirs(os.path.join(db, "packages"), exist_ok=True)
                shutil.copyfile(src, os.path.join(db, "packages", "lca-test-mime.xml"))
                self.run('"{}" "{}"'.format(tool, db), env="conanbuild")
            except Exception as exc:                      # noqa: BLE001
                self.output.warning(
                    "failed to generate the mime test database ({}); "
                    "skipping ContentInfo description check".format(exc))
                return None
        return db if os.path.isfile(cache) else None

    def _emulator(self):
        """返回 (可执行文件, 前缀参数)：优先 profile 注入的 ohos-qemu-aarch64 包装脚本。"""
        runroot = os.environ.get("OHOS_RUNROOT", "")
        wrapped = (os.environ.get("OHOS_QEMU")
                   or "/root/ohpc/bin/ohos-qemu-aarch64")
        if os.path.isfile(wrapped):
            return wrapped, ""          # 包装脚本已含 -L <runroot>
        plain = (shutil.which("qemu-aarch64-static")
                 or "/root/ohpc/sdk/qemu/usr/bin/qemu-aarch64-static")
        if os.path.isfile(plain):
            # 用 shlex.quote 而非手工双引号：runroot 会被拼进 self.run(shell=True)
            # 的命令串，手工引号无法抵御值中含 " / $() / 反引号 的注入；
            # 兄弟脚本 guest-wrapper.sh.in 是按 argv 传 -L，此处对齐其安全性。
            return plain, (' -L {}'.format(shlex.quote(runroot)) if runroot else "")
        return None, ""
