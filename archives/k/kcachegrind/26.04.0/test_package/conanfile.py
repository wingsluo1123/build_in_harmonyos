#!/usr/bin/env python3
"""Conan test_package for kcachegrind 26.04.0 (HarmonyOS PC).

上游 kcachegrind 26.04.0 无任何测试目标（无 tests/ 目录，全部 CMakeLists.txt
中 add_test/enable_testing/BUILD_TESTING 出现 0 次），MANIFEST.yml 如实申报 0。
按 R51「上游测试三步法」的第三步，消费者视角验证由本 test_package 承担：
真实运行安装后的 `bin/kcachegrind`，并校验交付物布局与 OHOS ELF 属性。

- `QT_QPA_PLATFORM=offscreen`：OHOS 无显示服务器，qtbase 自带 offscreen 平台插件
  （ktimer/kteatime 26.04.0 同款）。
- `kcachegrind --version` 走 KAboutData::processCommandLine，输出
  `kcachegrind 26.04.0 …` 并退出 0；运行期依赖（Qt6Core/Gui/Widgets/DBus、
  KF6CoreAddons/XmlGui/ConfigCore/ConfigGui/KIOCore/KIOWidgets/DBusAddons、
  kjobwidgets、karchive、openssl、libxml2）须经 conanrun env + 二进制 DT_RPATH
  完整解析。
- 交付物布局断言：bin/kcachegrind + 5 个 callgrind 转换脚本（上游把
  converters/ 安装到 KDE_INSTALL_BINDIR）。
- OHOS ELF 断言：PIE、GNU_STACK、存在 DT_RPATH、关键 KF6/Qt6 依赖链接
  （绝对路径 DT_NEEDED 属 E537 族已知生态现象，记录为 INFO 不判失败）。

⚠️ KF6 依赖库的「烤死的坏 DT_NEEDED」重构（kteatime/ktimer 26.04.0 先例）：
KF6 生态里同时存在两类不可解析的 `DT_NEEDED`：
  1. **相对路径** `../../bin/libKF6ConfigCore.so` / `../../bin/libKF6IconThemes.so`
     —— 含 `/` 的名字被加载器当成**相对 CWD 的路径**直接打开，绕过
     DT_RPATH/LD_LIBRARY_PATH ⇒ 只有把 CWD 放在 `<conan_cache>/recon/<x>` 并把
     这些 .so 复制到 `<conan_cache>/bin` 才能解析。CI 实测（构建 #92573）：
     `Error loading shared library ../../bin/libKF6ConfigCore.so (needed by
     …/libKF6ConfigGui.so)`。该相对形式在 CI worker 的**缓存副本**上观测到
     —— 同一 package_id 的字节在不同机器上可能不同（Conan 只按 package_id
     索引、不校验字节），worker 上由上游配方本地重建的副本会记录相对链接行；
  2. **绝对路径**指向构建方/发布方的 conan home（本机 readelf 可见
     `~/.cache/conan2/p/…` 形式）—— 用 `<home>/.conan2 → cache_home` 软链兜底。
本包 CI 首轮失败（26/31）即第 1 类；本地不暴露是因为开发机 `~/.cache/conan2`
恰好存在且副本为发布方构建（绝对路径可直接命中）。两类都属 E537 族。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment


class KcachegrindTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _reconstruct_kf6_rpaths(self):
        """KF6 依赖库坏 DT_NEEDED 重构（kteatime/ktimer 26.04.0 先例）。

        返回受控 CWD（`<cache_home>/recon/kcg`，使 `../../bin/<lib>.so`
        指向 `<cache_home>/bin`）；定位失败返回 None。
        """
        cache_home = None
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf and os.path.isdir(os.path.join(pf, "lib")):
                cache_home = os.path.dirname(
                    os.path.dirname(os.path.dirname(pf)))
                break
        if not cache_home:
            self.output.warning("[recon] 无法定位 conan 缓存 home，跳过重构")
            return None

        # 2) 绝对路径兜底：<home>/.conan2 指向真实缓存 home
        conan2_link = os.path.join(
            os.path.dirname(os.path.dirname(cache_home)), ".conan2")
        try:
            if os.path.islink(conan2_link):
                if os.path.realpath(conan2_link) != cache_home:
                    os.unlink(conan2_link)
                    os.symlink(cache_home, conan2_link)
            elif not os.path.exists(conan2_link):
                os.symlink(cache_home, conan2_link)
        except OSError as e:
            self.output.warning(f"[recon] .conan2 软链失败: {e}")

        # 1) 相对路径兜底：把依赖的所有 .so 实体复制到 <cache_home>/bin
        bin_dir = os.path.join(cache_home, "bin")
        try:
            os.makedirs(bin_dir, exist_ok=True)
        except OSError as e:
            self.output.warning(f"[recon] 创建 {bin_dir} 失败: {e}")
            return None
        copied = 0
        for dep in self.dependencies.values():
            lib_dir = (os.path.join(dep.package_folder, "lib")
                       if dep.package_folder else None)
            if not (lib_dir and os.path.isdir(lib_dir)):
                continue
            for name in sorted(os.listdir(lib_dir)):
                if ".so" not in name:
                    continue
                src = os.path.join(lib_dir, name)
                if not os.path.isfile(src):
                    continue
                # 原地实体化符号链接（HMDFS 上加载器对 symlink .so 不稳定）。
                # 用「临时文件 + os.replace」原子替换，避免中途被打断后留下
                # 半截文件污染共享缓存里的依赖包。
                if os.path.islink(src):
                    try:
                        real = os.path.realpath(src)
                        tmp = src + ".recon-tmp"
                        shutil.copy2(real, tmp)
                        os.chmod(tmp, 0o755)
                        os.replace(tmp, src)
                    except OSError as e:
                        self.output.warning(
                            f"[recon] 原地真实化 {name} 失败: {e}")
                dst = os.path.join(bin_dir, name)
                try:
                    # 覆盖式复制（不用 first-wins）：<cache_home>/bin 可能残留
                    # 上一次任务/其他 package_id 的同名 .so，必须让本次依赖集
                    # 的副本胜出，否则测试可能对着错误的库通过。
                    shutil.copy2(src, dst)
                    os.chmod(dst, 0o755)
                    copied += 1
                except OSError as e:
                    self.output.warning(
                        f"[recon] 复制 {name} 到 bin 失败: {e}")
        recon_cwd = os.path.join(cache_home, "recon", "kcg")
        try:
            os.makedirs(recon_cwd, exist_ok=True)
        except OSError as e:
            self.output.warning(f"[recon] 创建 {recon_cwd} 失败: {e}")
            return None
        self.output.info(
            f"[recon] cache_home={cache_home} bin_copied={copied} "
            f"CWD={recon_cwd}（../../bin -> {bin_dir}）")
        return recon_cwd

    def test(self):
        pkg = self.dependencies["kcachegrind"]
        env = Environment()
        # OHOS 无显示服务器：必须用 offscreen QPA 插件。
        env.define("QT_QPA_PLATFORM", "offscreen")
        # 无会话总线时 KDBusService 只告警不阻塞（上游 main.cpp 先构造它再解析
        # 命令行）；显式指向一个不存在的总线地址，避免触发自动启动尝试。
        env.define("DBUS_SESSION_BUS_ADDRESS", "unix:path=/nonexistent-ohos-bus")
        if pkg.package_folder:
            env.define(
                "KCACHEGRIND_BIN",
                os.path.join(pkg.package_folder, "bin", "kcachegrind"),
            )
            env.define("KCACHEGRIND_PKG", pkg.package_folder)
        with env.vars(self).apply():
            script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "test_kcachegrind.py",
            )
            # 受控 CWD：让依赖库里 `../../bin/<lib>.so` 形式的相对 DT_NEEDED
            # 解析到 <cache_home>/bin（见模块 docstring）。
            recon_cwd = self._reconstruct_kf6_rpaths()
            self.run(f"python3 {script}", env="conanrun", cwd=recon_cwd)
