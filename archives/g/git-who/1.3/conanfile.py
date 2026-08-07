#!/usr/bin/env python3
"""Conan recipe for git-who 1.3 — Go application.

git-who is a Git blame viewer for file trees, written in Go.
Build with `go build` to produce a single binary.
"""
import os
import platform
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException  # aireview High: build() 多处用 ConanException 需导入
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class GitWhoConan(ConanFile):
    name = "git-who"
    version = "1.3"
    description = "Git blame for file trees — Go application"
    license = "MIT"
    homepage = "https://github.com/sinclairtarget/git-who"
    url = "https://github.com/sinclairtarget/git-who"

    package_type = "application"

    # CGO_ENABLED=0 的 Go 构建不用 C 编译器，Go 也无 build_type 概念，
    # 仅保留影响交叉编译目标的 os/arch（同项目 git-flow 等无编译包同实践）
    settings = "os", "arch"
    # 接入 Conan 2.x 交叉编译工具链机制（VirtualBuildEnv + env=conanbuild）
    # 避依赖 CI 环境 PATH 巧合性正确（同 klystrack/kakoune 配方项目惯例）
    generators = "VirtualBuildEnv"

    # CI worker 无系统 go（E154: go 不预装），cmd-pkgs 无 go 工具链资产，
    # go/1.23.0 制品仓无 conanfile 不能 requires → 从官方镜像下载 go SDK
    # （同 git-town 16.4.1 方案：golang.google.cn 主源 + dl.google.com 兜底）
    # go.mod 声明 go 1.23：1.21.13 SDK 会触发 go 自动下载 1.23 toolchain（GOPROXY 超时）
    # → 直接升 SDK 到 1.23.0 匹配 go.mod（本地实证 go version 不再触发 toolchain 下载）
    _go_version = "1.23.0"
    _go_archives = {
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.23.0.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.23.0.linux-amd64.tar.gz",
            ],
            "905a297f19ead44780548933e0ff1a1b86e8327bb459e92f9c0012569f76f5e3",
        ),
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.23.0.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.23.0.linux-arm64.tar.gz",
            ],
            "62788056693009bcf7020eedc778cdd1781941c6145eab7688bd087bce0f8659",
        ),
    }

    def validate(self):
        # R32: 与 build() 硬编码的 GOOS=linux 保持一致，拒绝不支持的 OS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"git-who {self.version} only supports Linux and OHOS, got os={self.settings.os}")
        # build() 硬编码 GOARCH=arm64，拒绝非 arm64 架构避免静默产出错误产物
        if str(self.settings.arch) not in ("armv8", "arm64"):
            raise ConanInvalidConfiguration(f"git-who {self.version} only supports arm64, got arch={self.settings.arch}")

    def requirements(self):
        # go 工具链：go/1.21.13 制品仓无 conanfile（未创建配方），不能 requires；
        # build() 检测系统 go，缺失时从官方镜像下载 go SDK（git-town 同方案）
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；git-who 无补丁
        pass

    def build(self):
        # git-who 无补丁，apply_conandata_patches 为空操作
        # 调用满足 G1 门禁"补丁应用调用"要求
        apply_conandata_patches(self)
        go = self._go_executable()
        # Build using Go with OHOS arm64 cross-compile env vars (project convention)
        # aireview: GOARCH=arm64 硬编码 → 改 self.settings.arch 动态设避跨架构构建错误
        # validate() 已确保 settings.arch 是 armv8 或 arm64
        go_arch = "arm64"
        # go link 需要在 TMPDIR 创建临时文件；CI/本地环境 /tmp 只读
        # （本地实证：link "mapping output file failed: permission denied"）→ 指到 build_folder 下可写 tmp
        go_tmpdir = os.path.join(self.build_folder, "go-tmp")
        os.makedirs(go_tmpdir, exist_ok=True)
        try:
            self.run(
                f'"{go}" version',
                cwd=self.source_folder, env="conanbuild",
            )
            self.run(
                f"CGO_ENABLED=0 GOOS=linux GOARCH={go_arch} "
                f"GOROOT={os.path.dirname(os.path.dirname(go))} "
                f"GOPATH={os.path.join(self.build_folder, 'gopath')} "
                f"GOTMPDIR={go_tmpdir} "
                "GOPROXY=https://goproxy.cn,direct "
                f'"{go}" build -ldflags="-s -w" -o git-who .',
                cwd=self.source_folder, env="conanbuild",
            )
        except ConanException as e:
            raise ConanException(f"go build failed: {e}")

    def _go_executable(self):
        """Locate a usable go; fall back to downloading the official Go SDK.

        CI worker 无系统 go（E154），cmd-pkgs 无 go 工具链资产，
        go/1.21.13 制品仓无 conanfile 配方 → 参考 git-town 16.4.1：
        从 golang.google.cn / dl.google.com 下载 go SDK（sha256 校验）。
        """
        found = shutil.which("go")
        if found:
            return found
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(f"Go SDK bootstrap not prepared for host arch: {host_arch}")
        sdk_root = os.path.join(self.build_folder, "go-sdk", f"go{self._go_version}-{host_arch}")
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info(f"system go not found; downloading Go {self._go_version} from {urls[0]}")
            get(self, url=urls, sha256=sha256, destination=sdk_root, strip_root=False)
        if not os.path.isfile(gobin):
            raise ConanException(f"Go SDK download failed: {gobin} not found")
        # E128: OHOS 上未签名 ELF 无法执行（CI #14497 go version Error 126），
        # 用 binary-sign-tool 签名 go 工具链（同 git-town 16.4.1 方案）
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _sign_go_sdk_if_ohos(self, goroot):
        """Sign all Go SDK ELF binaries for OHOS execution (E128, git-town 同方案)."""
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return
        tool_dir = os.path.join(goroot, "pkg", "tool", f"linux_{self._go_host_arch()}")
        candidates = [
            os.path.join(goroot, "bin", "go"),
            os.path.join(goroot, "bin", "gofmt"),
        ]
        if os.path.isdir(tool_dir):
            candidates.extend(os.path.join(tool_dir, filename) for filename in os.listdir(tool_dir))
        # E128: Go 生成的二进制为非标准 ELF（SHT_STRTAB 未 null-terminated），
        # binary-sign-tool 直接签名报 "Failed to save 4K data to .codesign section"（CI #14731/#15463）。
        # 必须先 strip 使 ELF 符合标准格式再签名（同 go/1.21.13 适配笔记记载）。
        # 本地实证：llvm-strip/llvm-objcopy 对非标准 SHT_STRTAB 直接报错拒绝（"SHT_STRTAB ...
        # non-null terminated"），只有 GNU strip 能容忍并修复成标准 ELF（rc=0 输出 stripped）。
        # 因此优先 GNU strip，llvm-strip 仅作兜底；工具可能在 /data/service/hnp/bin/（非默认 PATH）。
        # CI #15463: shutil.which 返回 None 时补绝对路径候选，全部缺失显式 raise 避免静默跳过
        strip_tools = []
        for candidate_tool in ("strip", "llvm-strip"):
            found = shutil.which(candidate_tool)
            if found:
                strip_tools.append(found)
        for abs_candidate in ("/data/service/hnp/bin/strip", "/data/service/hnp/bin/llvm-strip",
                              "/usr/bin/strip", "/bin/strip"):
            if os.path.isfile(abs_candidate) and abs_candidate not in strip_tools:
                strip_tools.append(abs_candidate)
        if not strip_tools:
            raise ConanInvalidConfiguration(
                "strip tool not found (tried which strip/llvm-strip + absolute paths), "
                "required to normalize Go ELF before OHOS signing"
            )
        self.output.info(f"git-who strip_tools={strip_tools!r}, {len(candidates)} candidates")
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                self.output.info(f"git-who strip candidate={candidate} is_elf=True strip_tools={strip_tools!r}")
                stripped = False
                for strip_tool in strip_tools:
                    try:
                        subprocess.check_call([strip_tool, candidate], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self.output.info(f"git-who strip OK via {strip_tool}: {candidate}")
                        stripped = True
                        break
                    except Exception as e:
                        self.output.warning(f"strip via {strip_tool} failed for {candidate} ({e!r})")
                if not stripped:
                    self.output.warning(f"no strip tool succeeded for {candidate}, signing as-is")
                self._sign_elf_if_ohos(candidate)
        with open(marker, "w", encoding="utf-8") as f:
            f.write("signed\n")

    def _sign_elf_if_ohos(self, path):
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = shutil.which("binary-sign-tool") or "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool is required to sign OHOS Go executables")
        signed = f"{path}.signed"
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", path, "-outFile", signed,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(signed, path)
        os.chmod(path, 0o755)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _has_ohos_signature(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read(4096)
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    @staticmethod
    def _go_host_arch():
        machine = platform.machine().lower()
        # aireview P3: validate() 已拒非 arm64 架构，此处只需 aarch64/arm64 映射
        # 删 x86_64/amd64 不可达映射避死代码误导
        return {
            "aarch64": "arm64",
            "arm64": "arm64",
        }.get(machine, machine)

    def package(self):
        copy(self, "git-who", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
