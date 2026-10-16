#!/usr/bin/env python3
"""Conan recipe — ublock 1.70.0 (uBlock Origin)

uBlock Origin（uBO）是一款高效、低资源占用的广谱内容拦截器。上游交付物是
浏览器扩展（Chromium / Opera / Firefox / Safari / Thunderbird）以及可复用的
静态网络过滤引擎 npm 库 @gorhill/ubo-core。

仓库内 **零 C/C++ 源文件**（纯 JavaScript + 已提交的 WebAssembly 制品，见
notes.md「语言核验」），因此本配方按仓库既有「JS / npm 包」范式适配
（参照 archives/u/uglify、archives/r/roblox-ts、archives/l/leaflet-markercluster）：
真实执行上游 `make` 构建目标，把产物作为 Conan 资产包分发。

构建（build）：
  真实执行上游构建脚本（显式 bash，避免 shebang 执行失败）：
  tools/make-chromium.sh → dist/build/uBlock0.chromium  （浏览器扩展，uBO 主交付物）
  tools/make-npm.sh      → dist/build/uBlock0.npm(.tgz)（@gorhill/ubo-core 静态过滤引擎库）
  随后真实执行上游测试入口 platform/npm/test.js（mocha：tests/wasm.js + tests/snfe.js）
  以及未被 test.js 收录的 tests/leaks.js。

打包（package）：
  res/ublock/ubo-core/   静态过滤引擎 Node 库（index.js + js/ + lib/ + build/）
  res/ublock/chromium/   浏览器扩展
  licenses/LICENSE.txt   GPLv3 全文

OHOS 平台适配（鸿蒙相关改动，均有 [OHOS] 测试用例覆盖）：
 1. settings.os 判定为 in ("Linux", "OHOS")（R32）；OHOS settings.yml 为 OHOS 定义了
    无默认值的 os.version 子设置，configure() 用 rm_safe 移除（否则 package_id 校验
    报 "Invalid: 'settings.os.version' value not defined"）。
 2. **Node.js 必须启用 JIT（WebAssembly 可用）**：uBO 引擎核心依赖 WebAssembly 制品
    （hntrie / biditrie / publicsuffixlist / lz4）；实测 `--jitless` 会让 V8 关闭
    可执行内存，导致 `WebAssembly is not defined`（上游 tests/wasm.js 正是验证此点，
    conan create 首个失败即由此暴露）。故本配方**不使用** `NODE_OPTIONS=--jitless`
    （与 archives/u/uglify 的做法相反），构建期与 test_package 均以「plain node +
    WebAssembly 可用」为可用性判据。
 3. **不依赖 shell 环境变量与 shebang（R33）**：bash/node/npm/python3 由 shutil.which
    显式解析绝对路径后注入子进程 PATH；上游 `tools/make-*.sh` **不经 make 直接 exec**
    （其 shebang 为 `#!/usr/bin/env bash`，在 OHOS/CI 沙箱下 exec 失败：
    `make: tools/make-chromium.sh: Resource temporarily unavailable` → Error 127，
    知识库 E165），改以显式 `bash <script>` 调用；`tools/make-npm.sh` 内部两处
    `./tools/*.sh` 调用由 patches/0001-tools-explicit-bash.patch 同样改为显式 bash。
 4. **npm 入口必须用真实 npm-cli.js**：hnp `node.org/<ver>/bin/npm` 是**残缺 stub**
    （`require('../lib/cli.js')(process)`，而 `lib/cli.js` 不存在），CI 上报
    `Error: Cannot find module '../lib/cli.js'`（知识库 E431）。配方探测并解析可用的
    (node, npm-cli.js) 组合（要求 node 支持 WebAssembly），并在 build 目录生成 `npm`
    shim 指向真实 npm-cli.js，使上游 `npm run build` / `npm pack` 可用。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class UblockConan(ConanFile):
    name = "ublock"
    version = "1.70.0"
    description = ("uBlock Origin — efficient wide-spectrum content blocker "
                   "for Chromium-based and Firefox browsers, plus the reusable "
                   "@gorhill/ubo-core static network filtering engine")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/gorhill/uBlock"
    url = ""  # CI fills this

    package_type = "application"

    # CI L0p 门禁要求四项齐备（OHOS profile 兼容性）
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # OHOS settings.yml 为 OHOS 定义 version 子设置且无默认值，配方未声明
        # os.version 时 package_id 计算会报
        # "Invalid: 'settings.os.version' value not defined"；有该子设置才 rm_safe。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "scripts/run_upstream_tests.sh",
            src=self.recipe_folder,
            dst=self.export_sources_folder,
        )

    def layout(self):
        basic_layout(self)

    # ── 工具链解析（R33：不裸用 shell 变量；OHOS 上路径与常规 Linux 不同） ──
    def _tool(self, names, fallbacks=()):
        for name in list(names) + list(fallbacks):
            found = shutil.which(name) if os.sep not in name else name
            if found and os.path.isfile(found) and os.access(found, os.X_OK):
                return os.path.realpath(found)
        raise ConanInvalidConfiguration(
            f"required tool not found: {' / '.join(names)}")

    @staticmethod
    def _probe(argv):
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=180)
            return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
        except Exception:
            return 1, ""

    @staticmethod
    def _node_candidates():
        # 顺序优先 PATH 上的 node（本地=cmd-pkgs、CI=hnp node.org，均为该环境可用者）；
        # 其余为回退。勿把本机不可用的 node 放前面（E400：本机 node.org v24.13.0 在
        # conan 构建环境下会 SIGTRAP）。
        cands = []
        which = shutil.which("node")
        if which:
            cands.append(which)
        cands.append(os.path.expanduser("~/.harmonybrew/bin/node"))
        cands += sorted(glob.glob("/data/service/hnp/node.org/*/bin/node"), reverse=True)
        cands.append("/data/service/hnp/bin/node")
        return cands

    @staticmethod
    def _npm_candidates(node):
        base = os.path.dirname(node)
        cands = []
        for rel in (os.path.join("..", "lib", "node_modules", "npm", "bin", "npm-cli.js"),
                    os.path.join("lib", "node_modules", "npm", "bin", "npm-cli.js")):
            cands.append(os.path.normpath(os.path.join(base, rel)))
        for extra in (os.path.join(base, "npm"), "/data/service/hnp/bin/npm",
                      os.path.expanduser("~/.harmonybrew/bin/npm"), shutil.which("npm")):
            if extra:
                cands.append(extra)
        return cands

    def _resolve_node_npm(self):
        """解析（node 可执行文件, npm 入口 JS），要求 node 支持 WebAssembly（uBO 引擎
        强依赖 wasm）且 npm 入口可真实运行。

        踩坑：hnp `node.org/<ver>/bin/npm` 是**残缺 stub**
        （`require('../lib/cli.js')(process)`，而 `lib/cli.js` 不存在 → MODULE_NOT_FOUND，
        CI 实测），故不能用 PATH 上的 `npm`，须用
        `<node>/lib/node_modules/npm/bin/npm-cli.js`。候选顺序参照
        archives/r/roblox-ts（harmonybrew 优先）。
        """
        for cand in self._node_candidates():
            node = os.path.realpath(cand)
            if not (os.path.isfile(node) and os.access(node, os.X_OK)):
                continue
            rc, out = self._probe([node, "-e", "process.stdout.write(typeof WebAssembly)"])
            if rc != 0 or out != "object":
                continue
            for npm in self._npm_candidates(node):
                if not os.path.isfile(npm):
                    continue
                rc, out = self._probe([node, npm, "--version"])
                if rc == 0 and out:
                    return node, npm
        raise ConanInvalidConfiguration(
            "no WebAssembly-capable Node.js with a working npm entry found")

    def _tools(self):
        """解析 bash / node / npm / python3 的绝对路径。"""
        node, npm_cli = self._resolve_node_npm()
        bash = self._tool(["bash"], ("/data/service/hnp/bin/bash",))
        python = self._tool(["python3", "python"], ("/data/service/hnp/bin/python3",))
        return {"node": node, "npm_cli": npm_cli, "bash": bash, "python": python}

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # uAssets（官方快照，钉死 commit）→ dist/build/uAssets/{main,prod}
        uassets = os.path.join(self.source_folder, "dist", "build", "uAssets")
        for name in ("main", "prod"):
            get(self, **self.conan_data["assets"][name],
                destination=os.path.join(uassets, name), strip_root=True)
        # 上游全量电池测试所需外部 dev 依赖（scaling-palm-tree）→ test-assets/
        for name, entry in self.conan_data.get("test_assets", {}).items():
            get(self, **entry,
                destination=os.path.join(self.source_folder, "test-assets", name),
                strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        tools = self._tools()
        for key in ("node", "bash", "python"):
            self.output.info(f"  tool.{key}: {tools[key]}")

        # 干净、绝对化的构建环境：JS 工具链与 C/C++ 工具链无关，不套 conanbuild
        # env 文件。注意：**不注入 NODE_OPTIONS=--jitless**（会禁用 WebAssembly，
        # 使 uBO 引擎不可用）——见模块 docstring 第 2 点。
        node = tools["node"]
        bash = tools["bash"]

        # `npm` shim：hnp `node.org/<ver>/bin/npm` 是残缺 stub（MODULE_NOT_FOUND），
        # 把 PATH 上的 `npm` 指向真实 npm-cli.js，使上游 tools/make-npm.sh 内的
        # `npm run build` / `npm pack` / `npm install` 可用（node 在 PATH 上，shim 的
        # `#!/usr/bin/env node` 才能解析）。
        shim_dir = os.path.join(self.build_folder, "toolbin")
        os.makedirs(shim_dir, exist_ok=True)
        npm_shim = os.path.join(shim_dir, "npm")
        if os.path.lexists(npm_shim):
            os.remove(npm_shim)
        os.symlink(tools["npm_cli"], npm_shim)

        path_dirs = [shim_dir]
        for key in ("node", "bash", "python"):
            d = os.path.dirname(tools[key])
            if d not in path_dirs:
                path_dirs.append(d)
        for d in ("/data/service/hnp/bin", "/usr/bin", "/bin"):
            if d not in path_dirs:
                path_dirs.append(d)
        env_prefix = f'PATH="{"".join(d + ":" for d in path_dirs)}/usr/bin:/bin"'

        # 可用性校验：node 必须启用 JIT（WebAssembly 可用），否则 uBO wasm 引擎
        # 不可用（--jitless 场景）。快速失败并给出明确根因。
        wasm_check = os.path.join(self.build_folder, "node-wasm-check.log")
        js_probe = ('if (typeof WebAssembly !== "object") { '
                    'console.error("WebAssembly unavailable (jitless node?)"); '
                    'process.exit(1); } console.log("WebAssembly ok");')
        self.run(
            f'{env_prefix} "{node}" -e \'{js_probe}\''
            f' < /dev/null > "{wasm_check}" 2>&1 || {{ rc=$?; cat "{wasm_check}"; exit $rc; }}',
            cwd=self.source_folder, env=None,
        )

        # ── 上游构建（真实执行上游 tools/make-*.sh，非等价替代） ──
        # 不用 `make <target>`：make 会直接 exec 脚本，而脚本 shebang 为
        # `#!/usr/bin/env bash`，在 OHOS/CI 沙箱下 exec 失败
        # （`make: tools/make-chromium.sh: Resource temporarily unavailable` → Error 127；
        # 知识库 E165：OHOS 无传统 /bin，shebang 解释器不可直接执行）。
        # 改为显式 `bash <script>`（仓库既有约定，见 archives/u/uglify）：bash 自读
        # 脚本、不依赖 shebang；tools/make-npm.sh 内部两处 `./tools/*.sh` 调用由
        # patches/0001-tools-explicit-bash.patch 同样改为显式 bash。
        for target, script in (("chromium", "tools/make-chromium.sh"),
                               ("npm", "tools/make-npm.sh")):
            log = os.path.join(self.build_folder, f"make-{target}.log")
            self.run(
                f'{env_prefix} "{bash}" "{script}"'
                f' < /dev/null > "{log}" 2>&1 || {{ rc=$?; cat "{log}"; exit $rc; }}',
                cwd=self.source_folder, env=None,
            )
            with open(log) as fh:
                self.output.info(f"  {script}: {fh.read().strip().splitlines()[-1]}")

        for rel in (os.path.join("dist", "build", "uBlock0.chromium", "manifest.json"),
                    os.path.join("dist", "build", "uBlock0.npm", "index.js")):
            p = os.path.join(self.source_folder, rel)
            if not os.path.isfile(p) or os.path.getsize(p) == 0:
                raise ConanInvalidConfiguration(
                    f"upstream build output incomplete: missing/empty {rel}")

        # ── 上游测试（真实执行；默认电池 + leaks，逐项计数） ──
        runner = os.path.join(self.export_sources_folder, "scripts", "run_upstream_tests.sh")
        test_env = (f'{env_prefix} '
                    f'UBO_NODE="{tools["node"]}" '
                    f'UBO_NPM_CLI="{tools.get("npm_cli") or ""}" '
                    f'UBO_SFT_SRC="{os.path.join(self.source_folder, "test-assets", "scaling_palm_tree")}"')
        self.run(f'{test_env} "{bash}" "{runner}" "{self.source_folder}"',
                 cwd=os.path.join(self.source_folder, "dist", "build", "uBlock0.npm"),
                 env=None)

    def package(self):
        res = os.path.join(self.package_folder, "res", "ublock")

        # 1) @gorhill/ubo-core 静态过滤引擎 Node 库
        core_src = os.path.join(self.source_folder, "dist", "build", "uBlock0.npm")
        core_dst = os.path.join(res, "ubo-core")
        os.makedirs(core_dst, exist_ok=True)
        for d in ("js", "lib", "build"):
            shutil.copytree(os.path.join(core_src, d), os.path.join(core_dst, d),
                            symlinks=True)
        for f in ("index.js", "package.json", "README.md", "LICENSE.txt"):
            copy(self, f, src=core_src, dst=core_dst, keep_path=False)
        # demo.js 便于消费方快速上手（上游 README 指向它）
        copy(self, "demo.js", src=core_src, dst=core_dst, keep_path=False)

        # 2) 浏览器扩展（uBO 主交付物，含 uAssets 默认过滤列表）
        shutil.copytree(os.path.join(self.source_folder, "dist", "build",
                                     "uBlock0.chromium"),
                        os.path.join(res, "chromium"), symlinks=True)

        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["res/ublock"]
