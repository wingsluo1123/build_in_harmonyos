#!/usr/bin/env python3
"""消费测试：验证 clutter 1.26.4 安装布局 + 库可用 + 上游纯 CPU 测试。

clutter（GNOME）是 OpenGL 场景图/交互画布库（library 包）。本测试验证：
1. lib/libclutter-1.0.so 库文件存在
2. include/clutter-1.0/clutter/clutter.h 头文件存在
3. 编译链接并运行 consumer.c（clutter_color/units/actor/interval/
   binding_pool 纯 CPU API 冒烟）——证明库可被实际链接和加载，
   避免空壳测试（R34/R40）
4. 编译并实跑上游纯 CPU 测试子集（upstream_unit/ 5 文件 17 用例，
   逐用例 PASS/FAIL 汇总）——真实本地运行结果（上游 conform 全量
   83 用例的其余 66 例依赖 clutter_init 的 EGL 显示服务与 stage/
   GL 渲染路径，OHOS 无显示服务属系统级阻塞，cogl 1.22.8 同款
   口径：如实记录省略（0 运行，非失败））
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。

upstream_unit/ 5 文件 = 上游 tests/conform/{color,units,interval,
model,binding-pool}.c 原文（函数体零改动）+ OHOS 顺序调用运行器
（上游 CLUTTER_TEST_SUITE 展开的 main 经 clutter_test_init ->
clutter_init 需 EGL 显示服务，不可行——运行器逐一调用注册的测试
函数；interval_from_script/list_model_from_script 的
g_test_build_filename(G_TEST_DIST, "scripts", ...) 改写为相对路径
g_strdup("scripts/...")，数据文件 scripts/ 随包提供，cwd 运行前
chdir 到 upstream_unit）。
"""
import os
import shutil
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"

# 上游纯 CPU 测试子集（文件 -> 注册用例数；详见模块 docstring）
UPSTREAM_TESTS = {
    "color": 5,          # hls-roundtrip/from-string invalid+valid/to-string/operators
    "units": 3,          # string/cache/constructors
    "interval": 3,       # initial-state/transform/from-script
    "model": 5,          # populate/iterate/filter/row-changed/from-script
    "binding-pool": 1,   # binding-pool
}
TOTAL_UPSTREAM = 83      # conform 全量注册用例（上游 tests/conform/*.c 逐文件清点）


def find_clang():
    cc = ""
    for cand in ("/data/service/hnp/bin/clang",
                 "/storage/Users/currentUser/usr/local/bin/clang",
                 os.environ.get("CC") or "",
                 shutil.which("clang") or ""):
        if cand and os.path.isfile(cand):
            cc = cand
            break
    return cc


def main():
    pkg_folder = sys.argv[1]
    failures = 0
    test_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. lib/libclutter-1.0.so 库文件存在（shared 库）
    libdir = os.path.join(pkg_folder, "lib")
    lib = os.path.join(libdir, "libclutter-1.0.so")
    if os.path.isfile(lib):
        print(f"{PASS} libclutter-1.0 库文件存在（libclutter-1.0.so）")
    else:
        print(f"{FAIL} libclutter-1.0 库文件缺失")
        failures += 1

    # 2. include/clutter-1.0/clutter/clutter.h 头文件存在
    hdr = os.path.join(pkg_folder, "include", "clutter-1.0",
                       "clutter", "clutter.h")
    if os.path.isfile(hdr):
        print(f"{PASS} include/clutter-1.0/clutter/clutter.h 头文件存在")
    else:
        print(f"{FAIL} clutter.h 头文件缺失")
        failures += 1

    # 依赖 include/libdirs（test() 已收集写入环境变量）
    dep_incs = [i for i in
                os.environ.get("CLUTTER_TEST_DEP_INCLUDES", "").split() if i]
    dep_libdirs = [d for d in
                   os.environ.get("CLUTTER_TEST_DEP_LIBDIRS", "").split()
                   if d]

    cc = find_clang()
    if not cc:
        print(f"{FAIL} clang 不在 PATH——编译检查跳过，核心链接检查未执行")
        failures += 1

    def build_run(src_path, out_bin, extra_flags=(), run_cwd=None):
        """编译+运行，返回 (build_ok, run_rc, run_stdout)。"build_ok
        且 run_rc==0" 才算过；运行前 LD_LIBRARY_PATH 注入本包 libdir +
        全部依赖 libdir（libclutter NEEDED 链全解析）。"""
        cmd = [cc, src_path, "-o", out_bin,
               "-I", os.path.join(pkg_folder, "include", "clutter-1.0")]
        cmd += [f"-I{d}" for d in dep_incs]
        cmd += [f"-L{d}" for d in dep_libdirs]
        cmd += ["-L", libdir, "-lclutter-1.0",
                "-lcogl", "-lgio-2.0", "-lgobject-2.0", "-lglib-2.0",
                "-lm"]
        cmd += list(extra_flags)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            print(f"{FAIL} 编译失败（{os.path.basename(src_path)}）："
                  f"rc={r.returncode}")
            print((r.stderr or "")[:400])
            return False, None, ""
        env = dict(os.environ)
        # 根因（#97813 stderr 实锤）：远端依赖包的 soname 别名（.so.N）是
        # 符号链接，CI worker 的 HMDFS 不支持 symlink（E316），解包后缺失
        # ——musl loader 报 "Error loading shared library
        # libjson-glib-1.0.so.0 (needed by libclutter-1.0.so.0)" → rc=127。
        # 本机缓存为实体文件故可跑。修法：把缺失的 soname 别名物化为实体
        # 副本（shim 目录），前置到重建的 LD_LIBRARY_PATH（不继承原值）。
        import glob as _glob
        shim_dir = os.path.join(test_dir, "_soname_shim")
        os.makedirs(shim_dir, exist_ok=True)
        # #98066 实锤定性：loader 能加载 shim 副本（"needed by" 指向
        # _soname_shim/libclutter-1.0.so.0）却打不开 conan2 缓存路径里的
        # 同名实体——json-glib 目录三个 so 名齐全、目录也在
        # LD_LIBRARY_PATH 上，仍报 not found。旧逻辑"源目录已有实体别名
        # 则跳过物化"因此踩坑：json-glib 的 .so.0 在缓存目录是实体文件
        # → 未物化进 shim → loader 打不开缓存路径 → rc=127。
        # 修法：所有扫描目录的版本实体与其 soname 别名一律物化实体
        # 副本进 shim（第一路径项已被三轮构建实证可加载，绕开缓存
        # 路径的打开失败）。CONAN_HOME 兜底 glob 在 CI 零命中（实测
        # 扫描数恒=libdir+deps），删除。
        scan_dirs = [libdir] + list(dep_libdirs)
        seen_dirs = []
        for d in scan_dirs:
            if d not in seen_dirs and os.path.isdir(d):
                seen_dirs.append(d)
        n_shim = 0
        for d in seen_dirs:
            for real in sorted(_glob.glob(os.path.join(d, "lib*.so*"))):
                if not os.path.isfile(real) or os.path.islink(real):
                    continue
                base = os.path.basename(real)
                if ".so." not in base:
                    continue
                root = base.split(".so.", 1)[0] + ".so"
                major = root[:-3] + ".so." + base.split(".so.", 1)[1].split(".")[0]
                # 实体自身名 + soname 别名无条件物化——不再检查源目录
                # 是否已有实体（loader 对缓存路径的打开不可信，
                # #97899/#98055/#98066 三轮实锤 json-glib 系缓存实体
                # 路径打不开）
                for name in (base, major):
                    dst = os.path.join(shim_dir, name)
                    if not os.path.lexists(dst):
                        shutil.copyfile(real, dst)
                        n_shim += 1
        if n_shim:
            print(f"{NOTE} soname shim: 扫描 {len(seen_dirs)} 目录，"
                  f"物化 {n_shim} 个实体/别名副本到 {shim_dir}")
        print(f"{NOTE} dep_libdirs({len(dep_libdirs)}): "
              f"{os.pathsep.join(dep_libdirs)[:400]}")
        # #98055 教训：CI 上 libjson-glib-1.0.so.0 仍缺且兜底 glob 零命中
        # ——需依赖目录清单证据定位 so 实际形态（真实版本文件在别处/
        # 包只有 .so 无版本文件/目录为空）。打印每个扫描目录的 so 清单。
        for d in seen_dirs:
            # #98095 教训：只列名字区分不了文件形态——CI 侧依赖包条目
            # 疑似 dangling symlink 等非常规形态（按名物化被静默跳过）。
            # 逐名类型诊断（link/file/other + readlink 目标）直击 CI 磁盘态。
            try:
                sos = []
                for fn in sorted(os.listdir(d)):
                    if fn.startswith("lib") and ".so" in fn:
                        p = os.path.join(d, fn)
                        if os.path.islink(p):
                            try:
                                ty = "L>" + os.readlink(p)[:36]
                            except OSError:
                                ty = "L?"
                        elif os.path.isfile(p):
                            ty = "F"
                        else:
                            ty = "O"
                        sos.append(f"{fn}:{ty}")
            except OSError:
                sos = ["<listdir 失败>"]
            print(f"{NOTE} [dir-listing] {d}: "
                  f"{len(sos)} entries: {' '.join(sos)[:600]}")
        try:
            _shims = sorted(os.listdir(shim_dir))
            print(f"{NOTE} [shim-listing] {len(_shims)} entries: "
                  f"{' '.join(_shims)[:600]}")
        except OSError:
            pass
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [shim_dir, libdir] + dep_libdirs)

        import re

        def _heal_missing(lib_name):
            # #98095 终局闭环：loader 能加载 shim 的 libclutter 副本
            # （needed-by 证据）却找不到 libjson-glib-1.0.so.0——CI 侧条目
            # 若为 dangling symlink 等非常规形态，按名物化会跳过。
            # 失败自愈：按 stem（libjson-glib-1.0.so*）全包树广扫可读
            # 实体（realpath 跟随符号链接），物化到缺失名下重跑。
            stem = lib_name.rsplit(".so", 1)[0]
            scan = list(seen_dirs)
            roots = set()
            for dd in scan:
                cand = dd
                for _ in range(4):
                    cand = os.path.dirname(cand)
                roots.add(cand)
                cand = dd
                for _ in range(6):
                    cand = os.path.dirname(cand)
                roots.add(cand)
            for home in (os.environ.get("CONAN_HOME"),
                         os.path.expanduser("~/.conan2"),
                         os.path.expanduser("~/.cache/conan2")):
                if home:
                    roots.add(home)
            for root in roots:
                if not root or not os.path.isdir(root):
                    continue
                for pat in (("p", "*", "p", "lib"),
                            ("p", "b", "*", "p", "lib")):
                    scan.extend(_glob.glob(os.path.join(root, *pat)))
            for d2 in scan:
                if not os.path.isdir(d2):
                    continue
                try:
                    names = os.listdir(d2)
                except OSError:
                    continue
                for nm in names:
                    if not nm.startswith(stem + ".so"):
                        continue
                    src = os.path.join(d2, nm)
                    try:
                        real = os.path.realpath(src)
                        if os.path.isfile(real):
                            dst = os.path.join(shim_dir, lib_name)
                            if not os.path.lexists(dst):
                                shutil.copyfile(real, dst)
                                print(f"{NOTE} [heal] {lib_name} ← {real}")
                                return True
                    except OSError:
                        continue
            return False

        run = subprocess.run([out_bin], capture_output=True, text=True,
                             timeout=60, env=env, cwd=run_cwd)
        out = run.stdout or ""
        for _attempt in range(5):
            if run.returncode == 0:
                break
            # rc=127 类失败的真实原因在 loader stderr（musl ldso 报错
            # 只写 stderr），此前被丢弃致根因不可见（#16570 #97759 教训）
            err = (run.stderr or "").strip()
            if err:
                out += "\n[stderr] " + err[:500]
            print(f"{NOTE} 运行 rc={run.returncode}，"
                  f"LD_LIBRARY_PATH={env.get('LD_LIBRARY_PATH', '')[:600]}")
            m = re.search(r"Error loading shared library ([^:\s]+)", err)
            if not m:
                break
            if not _heal_missing(m.group(1)):
                print(f"{NOTE} [heal] {m.group(1)} 无可读实体，放弃")
                break
            run = subprocess.run([out_bin], capture_output=True, text=True,
                                 timeout=60, env=env, cwd=run_cwd)
            out = run.stdout or ""
        return True, run.returncode, out

    # 3. 编译链接并运行 consumer.c——证明 libclutter 可被实际链接和
    #    加载（R34 非空壳）
    if cc:
        src = os.path.join(test_dir, "consumer.c")
        out_bin = os.path.join(test_dir, "clutter_consumer.out")
        build_ok, rc, out = build_run(src, out_bin)
        if build_ok and rc == 0 and "resolved ok" in out:
            print(f"{PASS} consumer 编译链接并运行成功"
                  f"（纯 CPU API 可解析 + libclutter-1.0.so 可加载）")
            print("  " + out.strip().splitlines()[0])
        else:
            print(f"{FAIL} consumer 运行失败（rc={rc}）")
            print((out or "")[:200])
            failures += 1

    # 4. 上游纯 CPU 测试子集：编译并逐个实跑（运行 cwd=upstream_unit，
    #    script 用例的 scripts/ 相对路径数据在该目录下）
    if cc:
        up_dir = os.path.join(test_dir, "upstream_unit")
        n_run = n_ok = n_units_ok = 0
        for name, declared in UPSTREAM_TESTS.items():
            src = os.path.join(up_dir, name + ".c")
            out_bin = os.path.join(up_dir, name + ".out")
            build_ok, rc, out = build_run(
                src, out_bin, extra_flags=("-Wno-deprecated-declarations",),
                run_cwd=up_dir)
            n_run += 1
            # 运行器逐用例打印 PASS 行——统计实际通过用例数
            passed_units = [ln for ln in out.splitlines()
                            if ln.startswith("PASS ")]
            if build_ok and rc == 0 and len(passed_units) == declared:
                n_ok += 1
                n_units_ok += declared
                print(f"{PASS} [upstream] {name}：{declared}/{declared} "
                      f"用例实跑通过（rc=0）")
            else:
                print(f"{FAIL} [upstream] {name} 实跑失败"
                      f"（rc={rc}，通过 {len(passed_units)}/{declared}）")
                print((out or "")[:300])
                failures += 1
        total_units = sum(UPSTREAM_TESTS.values())
        print(f"{NOTE} 上游纯 CPU 子集实跑汇总：文件 {n_run}/"
              f"{len(UPSTREAM_TESTS)}，通过 {n_ok}/{len(UPSTREAM_TESTS)}，"
              f"用例 {n_units_ok}/{total_units} 通过")
        print(f"{NOTE} 上游 conform 其余 {TOTAL_UPSTREAM - total_units} 例"
              f"依赖 clutter_init 的 EGL 显示服务与 stage/GL 渲染路径"
              f"——OHOS 无显示服务（/dev/dri 不存在），如实记录未运行"
              f"（0 运行，非失败；cogl 1.22.8 同款口径）")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
