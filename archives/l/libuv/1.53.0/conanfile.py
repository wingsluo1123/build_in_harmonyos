#!/usr/bin/env python3
"""Conan recipe — libuv 1.53.0 (cmake)

OHOS 适配要点：
- CMakeLists.txt 的 HarmonyOS 平台映射在 build() 内以代码方式完成
  （替代易失配的 0001 patch，见 _fix_cmake_for_ohos）
- OHOS 缺少 Linux CPU 亲和性 API (sched_getaffinity/cpu_set_t) 与
  Linux mmsg API (sendmmsg/recvmmsg/struct mmsghdr)，相关 __linux__
  分支在 build() 内以代码方式排除（见 _fix_unix_ohos_guards，
  替代易截断失配的 0002/0003/0004 patch：真机曾报 0002
  `source file is different - src/unix/core.c` 终止 build()，
  根因是 patch hunk 声明 21 行上下文但文件被截断且行号漂移
  2044->2065/545->556/191->204）
- OHOS 应用 UID 不在 /etc/passwd，getpwuid_r 失败时回退 OH_OsAccount_GetName
  （见 _fix_ohos_account_fallback，替代易失配的 0005 patch：真机曾报
  `source file is different - src/unix/core.c` 且 `actual: b'    if (buf == NULL)'`，
  根因是 1.53.0 重构了 uv__getpwuid_r 的 buf 循环，patch 上下文不再对齐）
- 上游测试在 build() 末尾真机执行 uv_run_tests_a（TAP 输出），解析后持久化
  build_folder/upstream_test_result.json，package() 复制进包内 res/，
  test_package 每轮复发同一标记（包缓存命中时 build() 不重跑，仅 test 必跑）。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class LibuvConan(ConanFile):
    name = "libuv"
    version = "1.53.0"
    description = "Cross-platform asynchronous I/O library"
    license = "MIT"
    homepage = "https://libuv.org/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=3, retry_wait=10)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def _fix_cmake_for_ohos(self):
        """HarmonyOS 平台映射（替代已删除的 0001 patch）。

        真机证据：0001-CMakeLists.txt.patch 在 1.53.0 上以
        `source file is different - CMakeLists.txt` 失败并终止 build()。
        上游 1.53.0 的 CMakeLists.txt 在 GNU/Hurd、QNX 等块之间插入了
        新的条件分支，patch 的统一上下文（含大量相同的 `endif()` 行）
        无法再对齐；逐行打补丁是脆弱路线。

        本方法改用确定性字符串替换（幂等）：三处 Linux 条件各恰好出现
        一次，找不到或出现多次时抛 ConanException 显式失败，不猜测。
        """
        import os
        from conan.errors import ConanException
        cmake = os.path.join(self.source_folder, "CMakeLists.txt")
        if not os.path.isfile(cmake):
            raise ConanException(
                "[libuv] CMakeLists.txt not found: %s" % cmake)
        with open(cmake, encoding="utf-8") as f:
            content = f.read()
        pairs = [
            ('if(APPLE OR CMAKE_SYSTEM_NAME MATCHES "Android|Linux")',
             'if(APPLE OR CMAKE_SYSTEM_NAME MATCHES "Android|Linux|HarmonyOS|OHOS")'),
            ('if(CMAKE_SYSTEM_NAME STREQUAL "Linux")',
             'if(CMAKE_SYSTEM_NAME MATCHES "Linux|HarmonyOS|OHOS")'),
            ('if(APPLE OR CMAKE_SYSTEM_NAME MATCHES "DragonFly|FreeBSD|Linux|NetBSD|OpenBSD")',
             'if(APPLE OR CMAKE_SYSTEM_NAME MATCHES "DragonFly|FreeBSD|Linux|HarmonyOS|OHOS|NetBSD|OpenBSD")'),
        ]
        for old, new in pairs:
            if new in content:
                continue
            n = content.count(old)
            if n != 1:
                raise ConanException(
                    "[libuv] CMake OHOS mapping failed: pattern %r found %d "
                    "times (expected 1); refusing to guess" % (old, n))
            content = content.replace(old, new)
        with open(cmake, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info("[libuv] CMakeLists.txt OHOS platform mapping applied")

    def _fix_unix_ohos_guards(self):
        """排除 OHOS 缺失的 Linux 专有 API（替代已删除的 0002/0003/0004 patch）。

        真机证据：0002 在 1.53.0 上以
        `source file is different - src/unix/core.c` 失败并终止 build()。
        解包 1.53.0 实测（sha256 cb0d6dd2...c53e64，1391596 字节）：
        core.c 的 uv_available_parallelism 实际在 2065 行（patch 标 2044），
        internal.h 守卫实际在 556 行（patch 标 545），
        udp.c 首个守卫实际在 204 行（patch 标 191），
        且三个 patch 的 hunk 头声明 21 行上下文但文件在约 15 行处被截断，
        patch 工具以 `actual: b''` 拒绝匹配。逐行打补丁是脆弱路线。

        本方法改用确定性字符串替换（幂等）：每个守卫在 1.53.0 有固定出现
        次数（core.c 1 次、internal.h 1 次、udp.c 3 次含 sendmmsg 延续行），
        已修复时跳过，未修复时要求计数精确匹配，否则抛 ConanException
        显式失败，不猜测。udp.c 三处（含 uv_udp_using_recvmmsg）一并排除，
        避免旧 patch 漏改第二处导致语义不一致。
        """
        import os
        from conan.errors import ConanException

        def _replace(path, old, new, expected):
            if new in open(path, encoding="utf-8").read():
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                if old in content:
                    raise ConanException(
                        "[libuv] partial OHOS guard in %s; refusing to guess" % path)
                return False
            with open(path, encoding="utf-8") as f:
                content = f.read()
            n = content.count(old)
            if n != expected:
                raise ConanException(
                    "[libuv] OHOS guard failed in %s: pattern %r found %d "
                    "times (expected %d); refusing to guess" % (path, old, n, expected))
            content = content.replace(old, new)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            return True

        core = os.path.join(self.source_folder, "src", "unix", "core.c")
        inh = os.path.join(self.source_folder, "src", "unix", "internal.h")
        udp = os.path.join(self.source_folder, "src", "unix", "udp.c")
        for p in (core, inh, udp):
            if not os.path.isfile(p):
                raise ConanException("[libuv] missing source file: %s" % p)
        changed = []
        if _replace(core,
                    "#ifdef __linux__\n  cpu_set_t set;",
                    "#if defined(__linux__) && !defined(__OHOS__)\n  cpu_set_t set;",
                    1):
            changed.append("core.c cpu_affinity")
        if _replace(inh,
                    "#if defined(__linux__) || (defined(__FreeBSD__) && __FreeBSD_version >= 1301000)",
                    "#if (defined(__linux__) && !defined(__OHOS__)) || (defined(__FreeBSD__) && __FreeBSD_version >= 1301000)",
                    1):
            changed.append("internal.h cpu_affinity")
        if _replace(udp,
                    "#if defined(__linux__) || defined(__FreeBSD__) || defined(__APPLE__)",
                    "#if (defined(__linux__) && !defined(__OHOS__)) || defined(__FreeBSD__) || defined(__APPLE__)",
                    3):
            changed.append("udp.c mmsg")
        self.output.info("[libuv] unix OHOS guards applied: %s" % (
            ", ".join(changed) if changed else "already applied"))

    def _fix_ohos_account_fallback(self):
        """OHOS 账户回退（替代已删除的 0005 patch）。

        真机证据：0005 在 1.53.0 上以
        `source file is different - src/unix/core.c`（`actual: b'    if (buf == NULL)'`）
        失败。解包 1.53.0 实测：uv__getpwuid_r 被重构为 bufsize 循环
        （`if (buf == NULL)` / `uv__free(buf)` / `ERANGE` 重试），patch 的
        1349/1385 行上下文不再对齐；上一轮保留 0005 补丁的路线已失效。
        本轮改走与 _fix_unix_ohos_guards 同一路线：幂等字符串插入，
        锚点经 1.53.0 实测各恰好 1 处（netinet/in.h 头、uv__getpwuid_r 定义、
        `result == NULL` + username 注释联合块；后者可与 getgrgid 组函数区分），
        不符时抛 ConanException 显式失败。逻辑与原 patch 等价：
        应用 UID 不在 /etc/passwd 时 dlopen 账户 NDK 回退账户名。
        """
        import os
        from conan.errors import ConanException
        core = os.path.join(self.source_folder, "src", "unix", "core.c")
        if not os.path.isfile(core):
            raise ConanException("[libuv] missing source file: %s" % core)
        with open(core, encoding="utf-8") as f:
            content = f.read()
        if "uv__get_ohos_account_name" in content:
            if "#include <dlfcn.h>" not in content:
                raise ConanException(
                    "[libuv] partial OHOS account fallback in core.c; refusing to guess")
            return
        old_inc = "#include <netinet/in.h>"
        new_inc = ("#include <netinet/in.h>\n"
                   "#ifdef __OHOS__\n"
                   "#include <dlfcn.h>\n"
                   "#endif")
        if content.count(old_inc) != 1:
            raise ConanException(
                "[libuv] OHOS account include anchor found %d times (expected 1)"
                % content.count(old_inc))
        content = content.replace(old_inc, new_inc)
        helper = (
            "#ifdef __OHOS__\n"
            "/* On HarmonyOS, application UIDs (e.g. 200xxxxx) are not in /etc/passwd.\n"
            " * Fall back to the OHOS OsAccount NDK API to retrieve the account name.\n"
            " * Note: dlclose() is intentionally NOT called - the system library registers\n"
            " * atexit handlers that cause SIGSEGV if the library is unloaded before exit. */\n"
            "static int uv__get_ohos_account_name(char* buffer, size_t buflen) {\n"
            "  typedef int (*getname_t)(char*, size_t);\n"
            "  void* handle;\n"
            "  getname_t fn;\n"
            "  int r;\n"
            "\n"
            "  handle = dlopen(\"/system/lib64/ndk/libos_account_ndk.so\",\n"
            "                  RTLD_NOW | RTLD_LOCAL);\n"
            "  if (handle == NULL)\n"
            "    return UV_ENOENT;\n"
            "\n"
            "  fn = (getname_t)dlsym(handle, \"OH_OsAccount_GetName\");\n"
            "  if (fn == NULL)\n"
            "    return UV_ENOENT;\n"
            "\n"
            "  r = fn(buffer, buflen);\n"
            "\n"
            "  if (r != 0)\n"
            "    return UV_ENOENT;\n"
            "\n"
            "  return 0;\n"
            "}\n"
            "#endif /* __OHOS__ */\n"
            "\n"
            "static int uv__getpwuid_r(uv_passwd_t *pwd, uid_t uid) {"
        )
        old_def = "static int uv__getpwuid_r(uv_passwd_t *pwd, uid_t uid) {"
        if content.count(old_def) != 1:
            raise ConanException(
                "[libuv] OHOS account def anchor found %d times (expected 1)"
                % content.count(old_def))
        content = content.replace(old_def, helper)
        old_tail = ("  if (result == NULL)\n"
                    "    return UV_ENOENT;\n"
                    "\n"
                    "  /* Allocate memory for the username, shell, and home directory */")
        new_tail = ("  if (result == NULL) {\n"
                    "#ifdef __OHOS__\n"
                    "    char ohos_name[256];\n"
                    "    const char* home;\n"
                    "    const char* shell;\n"
                    "\n"
                    "    if (uv__get_ohos_account_name(ohos_name, sizeof(ohos_name)) == 0) {\n"
                    "      home = getenv(\"HOME\");\n"
                    "      if (home == NULL)\n"
                    "        home = \"\";\n"
                    "      shell = \"/bin/sh\";\n"
                    "\n"
                    "      name_size = strlen(ohos_name) + 1;\n"
                    "      homedir_size = strlen(home) + 1;\n"
                    "      shell_size = strlen(shell) + 1;\n"
                    "      pwd->username = uv__malloc(name_size + homedir_size + shell_size);\n"
                    "      if (pwd->username == NULL)\n"
                    "        return UV_ENOMEM;\n"
                    "\n"
                    "      memcpy(pwd->username, ohos_name, name_size);\n"
                    "      pwd->homedir = pwd->username + name_size;\n"
                    "      memcpy(pwd->homedir, home, homedir_size);\n"
                    "      pwd->shell = pwd->homedir + homedir_size;\n"
                    "      memcpy(pwd->shell, shell, shell_size);\n"
                    "      pwd->uid = uid;\n"
                    "      pwd->gid = getegid();\n"
                    "\n"
                    "      return 0;\n"
                    "    }\n"
                    "#endif /* __OHOS__ */\n"
                    "    return UV_ENOENT;\n"
                    "  }\n"
                    "\n"
                    "  /* Allocate memory for the username, shell, and home directory */")
        if content.count(old_tail) != 1:
            raise ConanException(
                "[libuv] OHOS account tail anchor found %d times (expected 1)"
                % content.count(old_tail))
        content = content.replace(old_tail, new_tail)
        with open(core, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info("[libuv] OHOS account fallback applied")

    def _ohos_toolchain(self):
        # 自发现 ohos.toolchain.cmake（① profile [conf] user_toolchain
        # ② OHOS_NDK_HOME 及同类 OHOS/SDK/NDK 环境变量 ③ 编译器同级 SDK
        # ④ 多组已知 glob ⑤ /data/service/hnp 有界 walk）。
        # 背景：上一周期把 0002-0005 脆弱补丁改走 build() 内幂等字符串
        # 注入后，build() 首次越过补丁阶段到达本函数，随即报
        # `Invalid configuration: 找不到 ohos.toolchain.cmake`。
        # 旧实现只查单一 glob
        # `/data/service/hnp/ohos-sdk.org/*/ohos/native/...`，
        # 等同断言 SDK 版本目录布局与写配方时逐字一致；一旦 SDK
        # 版本号滚动、OHOS_NDK_HOME 指向层级不同（native/ohos/sdk-root
        # 三种惯例并存）或预检镜像路径漂移即全缺。本轮改走宽搜寻 +
        # 诊断输出路线，不再硬编码单一布局。
        import os
        import glob
        searched = []
        try:
            ut = self.conf.get(
                "tools.cmake.cmaketoolchain:user_toolchain",
                default=[], check_type=list) or []
        except Exception:
            ut = []
        if isinstance(ut, str):
            ut = [ut]
        cands = []
        cands.extend([c for c in list(ut) if isinstance(c, str) and c])
        for key in ("OHOS_NDK_HOME", "OHOS_SDK_HOME", "OHOS_SDK_NATIVE",
                    "OHOS_SDK_ROOT", "OHOS_NATIVE_HOME", "HMBS_OHOS_NDK",
                    "HMBS_OHOS_SDK"):
            v = os.environ.get(key, "")
            if not isinstance(v, str):
                continue
            v = v.strip()
            if not v:
                continue
            searched.append("%s=%s" % (key, v))
            # NDK 变量三种常见指向：native 本体 / ohos 目录 / SDK 根，
            # 三种拼接都试，不猜测只枚举。
            cands.append(os.path.join(v, "build/cmake/ohos.toolchain.cmake"))
            cands.append(os.path.join(v, "native/build/cmake/ohos.toolchain.cmake"))
            cands.append(os.path.join(v, "ohos/native/build/cmake/ohos.toolchain.cmake"))
        # 兜底：任何含 OHOS/NDK 的环境变量若指向已存在目录都试一次。
        for k, v in os.environ.items():
            try:
                uk = k.upper()
            except Exception:
                continue
            if ("OHOS" not in uk and "NDK" not in uk) or not isinstance(v, str):
                continue
            p = v.strip()
            if not p or not os.path.isdir(p):
                continue
            q = os.path.join(p, "build/cmake/ohos.toolchain.cmake")
            if q not in cands:
                cands.append(q)
        for cand in cands:
            if cand and os.path.isfile(cand):
                self.output.info("[libuv] OHOS toolchain: %s" % cand)
                return cand
            if cand:
                searched.append(cand)
        # 编译器同级派生：/data/service/hnp/bin/clang -> /data/service/hnp
        try:
            comp = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
            bases = set()
            for cc in comp.values():
                if not isinstance(cc, str) or not cc.strip():
                    continue
                bindir = os.path.dirname(cc.strip())
                if bindir and os.path.isdir(bindir):
                    bases.add(os.path.dirname(bindir))
                    bases.add(bindir)
            for base in sorted(bases):
                for pat in (os.path.join(base, "ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"),
                            os.path.join(base, "*/ohos/native/build/cmake/ohos.toolchain.cmake"),
                            os.path.join(base, "ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake")):
                    searched.append(pat)
                    for g in sorted(glob.glob(pat)):
                        if os.path.isfile(g):
                            self.output.info("[libuv] OHOS toolchain via compiler sibling: %s" % g)
                            return g
        except Exception as e:
            searched.append("compiler sibling probe failed: %r" % (e,))
        patterns = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/ohos-sdk.org/*/*/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/opt/ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/opt/*/ohos/native/build/cmake/ohos.toolchain.cmake",
        ]
        home = os.path.expanduser("~")
        if home and home != "~":
            patterns.append(os.path.join(home, "ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake"))
            patterns.append(os.path.join(home, "*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        for pat in patterns:
            searched.append(pat)
            for g in sorted(glob.glob(pat)):
                if os.path.isfile(g):
                    self.output.info("[libuv] OHOS toolchain via glob %s -> %s" % (pat, g))
                    return g
        # 有界 walk（深度 <=6，跳过 llvm/.git 提速）应对版本号滚动后的新布局。
        for root in ("/data/service/hnp",):
            if not os.path.isdir(root):
                searched.append(root + " (missing)")
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(root):
                    depth = dirpath.replace(root, "").count(os.sep)
                    if depth > 6:
                        dirnames[:] = []
                        continue
                    dirnames[:] = [d for d in dirnames if d not in ("llvm", ".git")]
                    if "ohos.toolchain.cmake" in filenames:
                        cand = os.path.join(dirpath, "ohos.toolchain.cmake")
                        if "build/cmake" in cand.replace("\\", "/"):
                            self.output.info("[libuv] OHOS toolchain via walk -> %s" % cand)
                            return cand
            except Exception as e:
                searched.append("walk %s failed: %r" % (root, e))
        self.output.info("[libuv] OHOS toolchain not found, fallback to conan toolchain")
        return None

    def _ohos_ar_ranlib_defs(self):
        import os
        defs = []
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"
        if os.path.isfile(ar):
            defs.append('-DCMAKE_AR="%s"' % ar)
        if os.path.isfile(ranlib):
            defs.append('-DCMAKE_RANLIB="%s"' % ranlib)
        return defs

    def _diagnose_sdk(self):
        import glob
        import os
        import shutil
        import subprocess
        def show(d, depth=0):
            try:
                names = sorted(os.listdir(d))[:40]
            except Exception as e:
                self.output.info('[libuv] ls %s failed: %r' % (d, e))
                return
            self.output.info('[libuv] ls %s: %s' % (d, ', '.join(names)))
            if depth <= 0:
                for n in names:
                    q = os.path.join(d, n)
                    if os.path.isdir(q) and not os.path.islink(q):
                        if n in ('llvm', '.git'):
                            continue
                        show(q, depth + 1)
        for base in ('/data/service/hnp', '/opt', '/usr/local'):
            if os.path.isdir(base):
                show(base, 1 if base == '/data/service/hnp' else 0)
        for key in sorted(os.environ):
            if 'OHOS' in key.upper() or 'NDK' in key.upper():
                self.output.info('[libuv] env %s=%s' % (key, os.environ[key]))
        for tool in ('clang', 'cmake', 'ninja'):
            self.output.info('[libuv] which %s=%s' % (tool, shutil.which(tool)))
        for pat in ('/data/service/hnp/*/ohos/native/sysroot', '/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot'):
            hits = sorted(glob.glob(pat))
            self.output.info('[libuv] sysroot glob %s -> %d' % (pat, len(hits)))
            for h in hits[:5]:
                self.output.info('[libuv] sysroot hit: %s' % h)
        try:
            cc = shutil.which('clang') or '/data/service/hnp/bin/clang'
            r = subprocess.run([cc, '--version'], capture_output=True, text=True, timeout=20)
            self.output.info('[libuv] clang --version: %s' % ((r.stdout or '') + (r.stderr or ''))[:500])
        except Exception as e:
            self.output.info('[libuv] clang --version failed: %r' % (e,))

    def _resolve_usable_compilers(self):
        """profile 编译器绝对路径缺失时回退 PATH 解析（经验1适配）。

        真机证据：profile 写死 tools.build:compiler_executables=
        /data/service/hnp/bin/clang，而预检机 ls /data/service/hnp 报
        PermissionError(13)，which clang 实际为
        ~/.harmonybrew/bin/clang；conan_toolchain.cmake 照抄 profile
        路径导致 CMAKE_C_COMPILER 指向不可用文件，cmake configure 报
        编译器错误。旧 _patch 只改系统名不修编译器，等同断言 profile
        路径永远可用，与真机文件系统矛盾。
        本方法以 or {} 容错读字典并规范化取值，os.path.isfile +
        os.access(X_OK) 校验存在性，缺失时按 basename/clang/cc 顺序
        shutil.which 回退并 warning+info 留痕，再供工具链补丁使用。
        """
        import os
        import shutil
        try:
            comp = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            comp = {}
        if not isinstance(comp, dict):
            comp = {}
        raw_c = comp.get("c", "")
        raw_cpp = comp.get("cpp", "")
        if not isinstance(raw_c, str):
            raw_c = ""
        if not isinstance(raw_cpp, str):
            raw_cpp = ""
        raw_c = raw_c.strip()
        raw_cpp = raw_cpp.strip()

        def _usable(path):
            return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)

        def _fallback(raw, names):
            if _usable(raw):
                return raw
            if raw:
                base = os.path.basename(raw)
                for nm in ([base] if base else []) + list(names):
                    if not nm:
                        continue
                    w = shutil.which(nm)
                    if w and _usable(w):
                        self.output.warning(
                            "[libuv] compiler fallback %s -> %s (profile path unusable)" % (raw, w))
                        self.output.info(
                            "[libuv] compiler fallback %s -> %s" % (raw, w))
                        return w
                self.output.warning(
                    "[libuv] profile compiler unusable and no PATH fallback for %s" % raw)
            for nm in names:
                w = shutil.which(nm)
                if w and _usable(w):
                    self.output.info("[libuv] compiler from PATH: %s -> %s" % (nm, w))
                    return w
            # HMBS/环境显式编译器变量兜底
            for k in ("CC", "CXX", "HMBS_CC", "HMBS_CXX"):
                v = os.environ.get(k, "").strip()
                if v and _usable(v):
                    self.output.info("[libuv] compiler from env %s=%s" % (k, v))
                    return v
            return raw

        c = _fallback(raw_c, ["clang", "cc", "gcc"])
        cxx = _fallback(raw_cpp, ["clang++", "c++", "g++"])
        self.output.info("[libuv] usable compilers: c=%s cpp=%s (profile c=%s cpp=%s)" % (
            c, cxx, raw_c, raw_cpp))
        return c, cxx

    def _fix_conan_toolchain_for_preflight(self):
        """修复 conan_toolchain.cmake 的系统名与编译器路径（稳健版）。

        替代旧 _patch_conan_toolchain_system：旧实现只做 glob +
        HarmonyOS->Linux 全局替换，不修编译器，且 glob 在
        cmake_layout 多配置目录下可能漏检（build/Release/generators
        与 build/build-*/ 双层并存），导致“System is unknown”与
        “CMAKE_C_COMPILER 不可用”同时残留。
        本方法改走 os.walk 全量定位 + 编译器回退 + 系统名兼容三合一：
        系统名仍回退为 cmake 可识别值并透传 -D__OHOS__（测试口径不变），
        编译器用 _resolve_usable_compilers 的可用路径替换缺失项，
        AR/RANLIB 缺失时回退 PATH 或注释掉缺失行，避免链接器卡点。
        """
        import os
        import re
        import shutil
        hits = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" in files:
                hits.append(os.path.join(root, "conan_toolchain.cmake"))
        hits = sorted(set(hits))
        self.output.info("[libuv] conan_toolchain candidates: %d under %s" % (
            len(hits), self.build_folder))
        for h in hits:
            self.output.info("[libuv] conan_toolchain hit: %s" % h)
        if not hits:
            self.output.warning("[libuv] no conan_toolchain.cmake found; cannot patch system/compiler")
            return
        usable_c, usable_cpp = self._resolve_usable_compilers()

        def _usable(path):
            return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)

        for f in hits:
            try:
                s = open(f, encoding="utf-8").read()
            except Exception as e:
                self.output.info("[libuv] read toolchain %s failed: %r" % (f, e))
                continue
            orig = s
            n_sys = s.count("HarmonyOS")
            if n_sys:
                s = s.replace("HarmonyOS", "Linux")
                self.output.info("[libuv] patched %s system HarmonyOS->Linux (%d)" % (f, n_sys))
            # 编译器：只替换指向缺失文件的条目，不动已可用项
            for var, usable, fallbacks in (
                    ("CMAKE_C_COMPILER", usable_c, ["clang", "cc"]),
                    ("CMAKE_CXX_COMPILER", usable_cpp, ["clang++", "c++"])):
                q = chr(34)
                pat = "set\\(" + var + "\\s+" + q + "?([^" + q + "\\s)]+)" + q + "?"
                m = re.search(pat, s)
                cur = m.group(1).strip() if m else ""
                if cur and _usable(cur):
                    self.output.info("[libuv] %s kept usable: %s (%s)" % (var, cur, f))
                    continue
                target = usable
                if not _usable(target):
                    for nm in fallbacks:
                        w = shutil.which(nm)
                        if w and _usable(w):
                            target = w
                            break
                if _usable(target):
                    if m:
                        s = re.sub(pat,
                                   "set(" + var + ' "%s"' % target, s, count=1)
                    else:
                        s += '\nset(' + var + ' "%s")\n' % target
                    self.output.warning(
                        "[libuv] patched %s %s '%s' -> '%s'" % (f, var, cur, target))
                else:
                    self.output.warning(
                        "[libuv] no usable %s (current='%s'); kept for cmake to diagnose" % (var, cur))
            # AR/RANLIB：缺失路径会让归档步骤直接失败；回退 PATH 或删行让 cmake 自寻
            for var, names in (("CMAKE_AR", ["llvm-ar", "ar"]),
                               ("CMAKE_RANLIB", ["llvm-ranlib", "ranlib"])):
                q2 = chr(34)
                pat2 = "set\\(" + var + "\\s+" + q2 + "?([^" + q2 + "\\s)]+)" + q2 + "?"
                m = re.search(pat2, s)
                if not m:
                    continue
                cur = m.group(1).strip()
                if _usable(cur) or shutil.which(os.path.basename(cur) if cur else ""):
                    continue
                repl = ""
                for nm in names:
                    w = shutil.which(nm)
                    if w:
                        repl = w
                        break
                if repl:
                    s = re.sub(pat2,
                               "set(" + var + ' "%s"' % repl, s, count=1)
                    self.output.warning("[libuv] patched %s %s '%s' -> '%s'" % (f, var, cur, repl))
                else:
                    self.output.warning("[libuv] %s '%s' missing, no fallback; kept" % (var, cur))
            if s != orig:
                open(f, "w", encoding="utf-8", newline="\n").write(s)
                self.output.info("[libuv] updated conan_toolchain: %s" % f)
            else:
                self.output.info("[libuv] conan_toolchain kept (no change): %s" % f)

    def _fix_runner_tmpfile(self):
        """Avoid SIGSEGV in upstream test harness when C tmpfile() fails (CI #96121).

        CI evidence: runner signed ok, TMPDIR writable for Python tempfile
        (probe ok), --list 527 ok, but bulk run printed only "1..527"
        (7 bytes) then exit=-11, and per-test isolation over 527 names
        yielded 527x "exit=-11 no-TAP <empty>". Root cause in
        test/runner-unix.c process_start(): it calls fileno(stdout_file)
        BEFORE checking stdout_file for NULL. When C tmpfile() fails
        (OHOS sandbox /tmp not writable or O_TMPFILE unsupported on the
        worker filesystem; note test_package build even logged
        "mkfifo ... Operation not permitted" in the same TMP area),
        fileno(NULL) dereferences NULL -> SIGSEGV for every test,
        including pure-CPU tests like utf8_decode1. --list works because
        it never calls process_start().
        Fix: reorder NULL check before fileno() and add TMPDIR/TMP/TEMP
        mkstemp fallback (unlink + fdopen) so the harness uses the HMBS
        writable TMPDIR that already passed the Python probe. Idempotent:
        skipped when "uvtestXXXXXX" already present; otherwise requires
        exactly one anchor occurrence.
        """
        import os
        from conan.errors import ConanException
        ru = os.path.join(self.source_folder, "test", "runner-unix.c")
        if not os.path.isfile(ru):
            raise ConanException("[libuv] missing runner file: %s" % ru)
        with open(ru, encoding="utf-8") as f:
            content = f.read()
        if "uvtestXXXXXX" in content:
            return
        old = ("  stdout_file = tmpfile();\n"
               "  stdout_fd = fileno(stdout_file);\n"
               "  if (!stdout_file) {\n"
               '    perror("tmpfile");\n'
               "    return -1;\n"
               "  }")
        if content.count(old) != 1:
            raise ConanException(
                "[libuv] runner tmpfile anchor found %d times (expected 1)"
                % content.count(old))
        new = ("  stdout_file = tmpfile();\n"
               "  if (stdout_file == NULL) {\n"
               '    const char* tdir = getenv("TMPDIR");\n'
               "    if (tdir == NULL || *tdir == '\\0') tdir = getenv(\"TMP\");\n"
               "    if (tdir == NULL || *tdir == '\\0') tdir = getenv(\"TEMP\");\n"
               "    if (tdir != NULL && *tdir != '\\0') {\n"
               "      char tmpl[4096];\n"
               "      int tfd;\n"
               '      snprintf(tmpl, sizeof(tmpl), "%s/uvtestXXXXXX", tdir);\n'
               "      tfd = mkstemp(tmpl);\n"
               "      if (tfd >= 0) {\n"
               "        unlink(tmpl);\n"
               '        stdout_file = fdopen(tfd, "w+");\n'
               "      }\n"
               "    }\n"
               "  }\n"
               "  if (!stdout_file) {\n"
               '    perror("tmpfile");\n'
               "    return -1;\n"
               "  }\n"
               "  stdout_fd = fileno(stdout_file);")
        content = content.replace(old, new)
        with open(ru, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info("[libuv] runner tmpfile fallback applied")

    def build(self):
        import os
        apply_conandata_patches(self)
        self._fix_cmake_for_ohos()
        self._fix_unix_ohos_guards()
        self._fix_ohos_account_fallback()
        self._fix_runner_tmpfile()
        shared_flag = "ON" if self.options.shared else "OFF"
        toolchain = self._ohos_toolchain()
        if toolchain:
            bdir = os.path.join(self.build_folder, "build-ohos")
            parts = [
                '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
                "-DOHOS_ARCH=arm64-v8a",
                "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
                "-DCMAKE_INSTALL_LIBDIR=lib",
                "-DBUILD_SHARED_LIBS=%s" % shared_flag,
                "-DLIBUV_BUILD_SHARED=%s" % shared_flag,
                "-DLIBUV_BUILD_TESTS=ON",
            ]
            parts.extend(self._ohos_ar_ranlib_defs())
            self.run('cmake -B "%s" -S "%s" %s' % (bdir, self.source_folder, " ".join(parts)))
            self.run('cmake --build "%s"' % bdir)
            self._run_upstream_tests(bdir)
        else:
            self.output.info("[libuv] building with conan toolchain (ohos.toolchain.cmake absent)")
            self._diagnose_sdk()
            self._fix_conan_toolchain_for_preflight()
            c = CMake(self)
            c.configure(variables={
                "CMAKE_INSTALL_LIBDIR": "lib",
                "BUILD_SHARED_LIBS": shared_flag,
                "LIBUV_BUILD_SHARED": shared_flag,
                "LIBUV_BUILD_TESTS": True,
                "CMAKE_C_FLAGS": "-D__OHOS__",
                "CMAKE_CXX_FLAGS": "-D__OHOS__",
            })
            c.build()
            cand = os.path.join(self.build_folder, "build-ohos")
            real = cand if os.path.isdir(cand) else self.build_folder
            found = None
            for root, _, files in os.walk(real):
                if "uv_run_tests_a" in files or "uv_run_tests" in files:
                    found = root
                    break
            self._run_upstream_tests(found or self.build_folder)

    def _sign_file_for_exec(self, path):
        """HarmonyOS PC codesign for a single executable (runner)."""
        import os
        import shutil as _sh
        if not os.path.isfile(path):
            return False
        try:
            os.chmod(path, 0o755)
        except Exception:
            pass
        objcopy = "/data/service/hnp/bin/llvm-objcopy" if os.path.isfile("/data/service/hnp/bin/llvm-objcopy") else (_sh.which("llvm-objcopy") or "")
        signer = "/data/service/hnp/bin/binary-sign-tool" if os.path.isfile("/data/service/hnp/bin/binary-sign-tool") else (_sh.which("binary-sign-tool") or "")
        if not objcopy or not signer:
            self.output.info("[libuv] sign tools absent, skip runner codesign")
            return False
        try:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=path))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=path))
            self.output.info("[libuv] signed runner: %s" % path)
            return True
        except Exception as e:
            self.output.warning("[libuv] runner codesign failed %s: %r" % (path, e))
            return False

    def _run_upstream_tests(self, bdir):
        """Execute upstream uv_run_tests_a (TAP), parse and emit HMBS marker.

        Deterministic log source: runner TAP lines (1..N / ok N / not ok N
        / # SKIP). One verdict line == one executed test. No substring
        counting, no arithmetic repair. Identities:
        passed + failed == executed, executed + skipped <= discovered.
        First round does not raise on upstream failure (status only); missing
        binary or missing TAP header still raises (environment, no fake pass).
        When status is failed, a gaps array explains every non-passing item
        and a reason is given when executed == 0.
        """
        import json
        import os
        import re
        import shutil
        import subprocess
        from conan.errors import ConanException

        cands = [
            os.path.join(bdir, "uv_run_tests_a"),
            os.path.join(bdir, "uv_run_tests"),
        ]
        runner = next((c for c in cands if os.path.isfile(c) and os.access(c, os.X_OK)), None)
        if runner is None:
            # fallback: file exists but not yet executable bit (chmod=0 env)
            for c in cands:
                if os.path.isfile(c):
                    try:
                        os.chmod(c, 0o755)
                    except Exception:
                        pass
                    if os.path.isfile(c):
                        runner = c
                        break
        if runner is None:
            raise ConanException("[libuv] upstream test runner not found in %s" % bdir)
        # Experience 1: sign executable before running on HarmonyOS PC,
        # otherwise fork/exec children fail and no verdict lines appear.
        try:
            self._sign_file_for_exec(runner)
        except Exception as e:
            self.output.warning("[libuv] sign hook error: %r" % (e,))
        # Ensure tmpfile() has a writable directory (runner-unix uses tmpfile
        # for child output capture). HMBS injects TMPDIR; ensure it exists.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k, "")
            if _v and not os.path.isdir(_v):
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
        if not os.path.isdir(os.environ.get("TMPDIR", "")):
            _fb = os.path.join(self.build_folder, "tmp")
            try:
                os.makedirs(_fb, exist_ok=True)
            except Exception:
                pass
            os.environ["TMPDIR"] = _fb
            os.environ["TMP"] = _fb
            os.environ["TEMP"] = _fb
        self.output.info("[libuv] runner TMPDIR=%s" % os.environ.get("TMPDIR", ""))
        # Allow running as root inside containers (upstream refuses by
        # default); harmless on OHOS normal user.
        env = dict(os.environ)
        env.setdefault("UV_RUN_AS_ROOT", "1")
        # Enumeration source for discovered: --list (one line per test) plus
        # TAP header cross-check. Both are deterministic; TAP header wins.
        listed = None
        listed_names = []
        try:
            _lp = subprocess.Popen([runner, "--list"], cwd=self.source_folder,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, errors="replace", env=env)
            _lout, _ = _lp.communicate(timeout=60)
            _names = [l.strip() for l in _lout.splitlines() if l.strip()]
            # --list prints one test per line, helpers shown as "name (helpers: ...)"
            # Count only non-empty lines; helpers are part of same line, not extra.
            # Keep bare task names (first token) for per-test isolation fallback.
            listed = len(_names)
            for _ln in _names:
                _tok = _ln.split()
                if _tok:
                    listed_names.append(_tok[0])
            self.output.info("[libuv] --list enumeration: %d" % listed)
        except Exception as e:
            self.output.warning("[libuv] --list enumeration failed: %r" % (e,))
        # Fixture guard (toybox lesson): harness silently passes on empty
        # fixtures; verify deterministically before running.
        try:
            _fx = os.path.join(self.source_folder, "test", "fixtures")
            if os.path.isdir(_fx):
                _fns = sorted(os.listdir(_fx))[:8]
                _empty = [n for n in _fns
                          if os.path.isfile(os.path.join(_fx, n))
                          and os.path.getsize(os.path.join(_fx, n)) == 0]
                self.output.info("[libuv] fixtures: dir=%s files=%d sample=%s empty=%s" % (
                    _fx, len(_fns), ",".join(_fns[:5]), ",".join(_empty[:5])))
            else:
                self.output.warning("[libuv] fixtures dir missing: %s" % _fx)
        except Exception as e:
            self.output.warning("[libuv] fixtures probe failed: %r" % (e,))
        # tmpfile() writability probe: runner-unix captures child output via
        # tmpfile(), which honours TMPDIR. A non-writable TMPDIR segfaults
        # the parent right after the TAP header (CI #95928: 1..527 then -11).
        try:
            import tempfile
            _tf = tempfile.TemporaryFile()
            _tf.write(b"hmbs-probe")
            _tf.close()
            self.output.info("[libuv] tmpfile probe ok (TMPDIR=%s)" % os.environ.get("TMPDIR", ""))
        except Exception as e:
            self.output.warning("[libuv] tmpfile probe failed (TMPDIR=%s): %r" % (
                os.environ.get("TMPDIR", ""), e))
        proc = subprocess.Popen(
            [runner], cwd=self.source_folder,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", env=env, bufsize=1)
        lines = []
        for line in proc.stdout:
            lines.append(line)
            print(line, end="", flush=True)
        proc.wait()
        out = "".join(lines)
        ansi = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
        clean_lines = []
        for _l in out.splitlines():
            _l2 = ansi.sub("", _l)
            # strip BOM and surrounding whitespace for verdict detection only
            _l2 = _l2.lstrip("\ufeff").strip()
            clean_lines.append(_l2)
        m = None
        for _l in clean_lines:
            _mh = re.match(r"^1\.\.(\d+)\s*$", _l)
            if _mh:
                m = _mh
                break
        if not m:
            _tail = "\n".join(clean_lines[-20:]) if clean_lines else "<empty>"
            raise ConanException(
                "[libuv] TAP header '1..N' not found (exit=%d, bytes=%d, lines=%d, listed=%s); tail: %s"
                % (proc.returncode, len(out), len(clean_lines), listed, _tail[:2000]))
        discovered = int(m.group(1))
        passed = 0
        skipped = 0
        failed = 0
        failed_names = []
        skipped_names = []
        for _l in clean_lines:
            if re.match(r"^not ok\s+\d+", _l):
                failed += 1
                failed_names.append(_l[:220])
            elif re.match(r"^ok\s+\d+", _l):
                if "# SKIP" in _l:
                    skipped += 1
                    skipped_names.append(_l[:220])
                else:
                    passed += 1
        executed = passed + failed
        if not (passed + failed == executed
                and executed + skipped <= discovered
                and executed <= discovered
                and all(v >= 0 for v in (discovered, executed, passed, failed, skipped))):
            raise ConanException(
                "[libuv] TAP count invariant violated: discovered=%d executed=%d "
                "passed=%d failed=%d skipped=%d listed=%s exit=%d" % (
                    discovered, executed, passed, failed, skipped, listed, proc.returncode))
        if listed is not None and listed != discovered:
            self.output.warning(
                "[libuv] discovered mismatch: TAP header %d vs --list %d; using TAP header" % (discovered, listed))
        # CI #95928: bulk run printed only "1..527" then exit -11 (zero
        # verdicts). Previous sign+TMPDIR route did not prevent the crash.
        # Different route: isolate per test (runner supports `runner <name>`
        # returning TEST_OK=0 / TEST_SKIP=7 with one TAP verdict line), so a
        # single crashing test cannot wipe out all 527 verdicts.
        used_isolation = False
        bulk_exit = proc.returncode
        bulk_bytes = len(out)
        if executed == 0 and listed_names and len(listed_names) == discovered:
            self.output.warning(
                "[libuv] bulk run yielded zero verdicts (exit=%d, bytes=%d); "
                "falling back to per-test isolation over %d names" % (
                    bulk_exit, bulk_bytes, len(listed_names)))
            _ipass = 0
            _iskip = 0
            _ifail = 0
            _ifail_names = []
            _iskip_names = []
            for _idx, _tname in enumerate(listed_names, start=1):
                try:
                    _sp = subprocess.Popen(
                        [runner, _tname], cwd=self.source_folder,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, errors="replace", env=env)
                    try:
                        _sout, _ = _sp.communicate(timeout=30)
                    except subprocess.TimeoutExpired:
                        try:
                            _sp.kill()
                        except Exception:
                            pass
                        _sout, _ = _sp.communicate(timeout=10)
                        _sout = (_sout or "") + "\n# TIMEOUT after 30s\n"
                    _slines = [ansi.sub("", _l).lstrip("\ufeff").strip()
                               for _l in (_sout or "").splitlines()]
                    _verdict = None
                    for _sl in _slines:
                        if re.match(r"^not ok\s+1\b", _sl):
                            _verdict = "fail"
                            _vline = _sl
                            break
                        if re.match(r"^ok\s+1\b", _sl):
                            _verdict = "skip" if "# SKIP" in _sl else "pass"
                            _vline = _sl
                            break
                    if _verdict == "pass":
                        _ipass += 1
                    elif _verdict == "skip":
                        _iskip += 1
                        _iskip_names.append((_tname + " :: " + _vline)[:220])
                    elif _verdict == "fail":
                        _ifail += 1
                        _ifail_names.append((_tname + " :: " + _vline)[:220])
                    else:
                        # No TAP verdict line: deterministic returncode map
                        # (0->pass is NOT assumed; unknown output = fail).
                        if _sp.returncode == 7:
                            _iskip += 1
                            _iskip_names.append((_tname + " :: exit=7 no-TAP")[:220])
                        elif _sp.returncode == 0 and _sout.strip():
                            _ipass += 1
                        else:
                            _ifail += 1
                            _tail1 = " | ".join(_slines[-3:]) if _slines else "<empty>"
                            _ifail_names.append((_tname + " :: exit=%s no-TAP %s" % (
                                _sp.returncode, _tail1))[:220])
                    # Keep build-log evidence bounded: one line per test.
                    print("isolated %d/%d %s: %s (exit=%s)" % (
                        _idx, len(listed_names), _tname,
                        _verdict or ("rc=%s" % _sp.returncode), _sp.returncode),
                        flush=True)
                except Exception as e:
                    _ifail += 1
                    _ifail_names.append((_tname + " :: harness error %r" % (e,))[:220])
            _iexec = _ipass + _ifail
            if not (_iexec + _iskip == discovered and _iexec <= discovered):
                raise ConanException(
                    "[libuv] isolation invariant violated: discovered=%d executed=%d "
                    "passed=%d failed=%d skipped=%d" % (
                        discovered, _iexec, _ipass, _ifail, _iskip))
            passed, failed, skipped = _ipass, _ifail, _iskip
            failed_names, skipped_names = list(_ifail_names), list(_iskip_names)
            executed = _iexec
            used_isolation = True
            self.output.info(
                "[libuv] isolation result: discovered=%d executed=%d passed=%d "
                "failed=%d skipped=%d" % (discovered, executed, passed, failed, skipped))
        status = "passed" if (failed == 0 and executed == discovered
                               and executed > 0) else "failed"
        if executed == 0:
            status = "failed"
        _cmd = "uv_run_tests_a --per-test-isolation" if used_isolation else "uv_run_tests_a"
        result = {
            "status": status,
            "framework": "ctest",
            "command": _cmd,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        # gaps: every non-passing item must be explained; count must equal
        # discovered - passed. Categories only: environment / ohos_feature / test_failure.
        gaps = []
        if status != "passed":
            if failed:
                gaps.append({
                    "count": failed,
                    "category": "test_failure",
                    "detail": "uv_run_tests_a reported %d not-ok verdicts on HarmonyOS aarch64; first: %s" % (failed, failed_names[0] if failed_names else "n/a"),
                    "evidence": "; ".join(failed_names[:5]) if failed_names else "TAP not-ok lines in build log (exit=%d)" % proc.returncode,
                })
            if skipped:
                gaps.append({
                    "count": skipped,
                    "category": "ohos_feature",
                    "detail": "uv_run_tests_a reported %d SKIP verdicts (platform-dependent tests); first: %s" % (skipped, skipped_names[0] if skipped_names else "n/a"),
                    "evidence": "; ".join(skipped_names[:5]) if skipped_names else "TAP '# SKIP' lines in build log",
                })
            _unexec = discovered - executed - skipped
            if _unexec > 0:
                _tail = "\n".join(clean_lines[-8:]) if clean_lines else "<empty>"
                gaps.append({
                    "count": _unexec,
                    "category": "environment" if executed == 0 else "ohos_feature",
                    "detail": ("runner exited after TAP header with zero verdict lines (exit=%d, bytes=%d, listed=%s; likely fork/tmpfile/signing sandbox); unexecuted=%d" % (proc.returncode, len(out), listed, _unexec)) if executed == 0 else ("no verdict for %d tests (killed/timeout/crash after header; exit=%d)" % (_unexec, proc.returncode)),
                    "evidence": "tail: %s" % _tail[:1500],
                })
            # self-check: gaps sum must equal discovered - passed
            _gsum = sum(g.get("count", 0) for g in gaps)
            if _gsum != discovered - passed:
                raise ConanException(
                    "[libuv] gaps sum %d != discovered-passed %d; refusing to fake evidence" % (_gsum, discovered - passed))
            result["gaps"] = gaps
            if used_isolation:
                result["reason"] = ("bulk run crashed after TAP header 1..%d "
                    "(exit=%s, bytes=%s); per-test isolation over %d names "
                    "yielded executed=%d passed=%d failed=%d skipped=%d" % (
                        discovered, bulk_exit, bulk_bytes,
                        len(listed_names), executed, passed, failed, skipped))
                if listed is not None and listed != discovered:
                    result["reason"] += "; TAP header %d vs --list %d mismatch" % (
                        discovered, listed)
            elif executed == 0:
                result["reason"] = "zero TAP verdict lines after header 1..%d (exit=%d, bytes=%d, listed=%s); see gaps[0].evidence" % (discovered, proc.returncode, len(out), listed)
            elif listed is not None and listed != discovered:
                result["reason"] = "TAP header %d vs --list %d mismatch; used TAP header" % (discovered, listed)
        jf = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(jf, "w", encoding="utf-8") as f:
            json.dump(result, f)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result), flush=True)

    def package(self):
        import os
        import shutil
        bdir = os.path.join(self.build_folder, "build-ohos")
        if os.path.isdir(bdir):
            self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        else:
            c = CMake(self)
            c.install()
        jf = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(jf):
            res = os.path.join(self.package_folder, "res")
            os.makedirs(res, exist_ok=True)
            shutil.copy2(jf, os.path.join(res, "upstream_test_result.json"))
        if self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        import glob
        import os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        import shutil as _sh
        objcopy = "/data/service/hnp/bin/llvm-objcopy" if os.path.isfile("/data/service/hnp/bin/llvm-objcopy") else (_sh.which("llvm-objcopy") or "")
        signer = "/data/service/hnp/bin/binary-sign-tool" if os.path.isfile("/data/service/hnp/bin/binary-sign-tool") else (_sh.which("binary-sign-tool") or "")
        if not objcopy or not signer:
            self.output.info("[libuv] sign tools absent, skip codesign")
            return
        for so in sos:
            if os.path.islink(so):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["uv"]
        self.cpp_info.set_property("cmake_file_name", "libuv")
        self.cpp_info.set_property("cmake_target_name", "libuv::libuv")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "rt", "m"]
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
