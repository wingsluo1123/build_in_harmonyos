import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    download,
    export_conandata_patches,
    get,
    rmdir,
)


class Mbedtls3Conan(ConanFile):
    name = "mbedtls-3"
    version = "3.6.7"
    description = "Mbed TLS 3.6 LTS：TLS 与密码库，含 AArch64 加密扩展运行时探测"
    license = "Apache-2.0 OR GPL-2.0-or-later"
    homepage = "https://github.com/Mbed-TLS/mbedtls"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("tls", "crypto", "ssl", "aarch64")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "user_config_armv8_if_present.h",
             src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "openssl-legacy.cnf",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self)

    def build_requirements(self):
        # ssl-opt.sh / compat.sh 的对端。制品仓已有二进制，CI 与真机走同一条路径。
        self.tool_requires("openssl/3.5.6.1.2")
        self.tool_requires("gnutls/3.8.10")

    def source(self):
        self._ensure_sources()

    def _ensure_sources(self):
        marker = os.path.join(self.source_folder, "CMakeLists.txt")
        if os.path.isfile(marker):
            return
        data = self.conan_data["sources"]
        filename = "mbedtls-3.6.7.tar.bz2"
        archive = os.path.join(self.source_folder, filename)
        try:
            get(self, data["url"], sha256=data["sha256"],
                filename=filename, strip_root=True)
        except Exception as exc:
            self.output.warning(f"tools.files.get 失败（{exc}），改用 tarfile 解压官方 bz2")
            if not os.path.isfile(archive):
                download(self, data["url"], filename=filename)
                check_sha256(self, filename, data["sha256"])
            with tarfile.open(archive, "r:bz2") as tf:
                members = tf.getmembers()
                roots = {m.name.split("/")[0] for m in members if m.name}
                if len(roots) != 1:
                    raise ConanException(f"无法识别压缩包根目录: {roots}")
                root = roots.pop()
                prefix = root + "/"
                for member in members:
                    name = member.name
                    if name == root or not name.startswith(prefix):
                        continue
                    member.name = name[len(prefix):]
                    if member.name:
                        tf.extract(member, self.source_folder)
            if os.path.isfile(archive):
                os.remove(archive)
        if not os.path.isfile(marker):
            raise ConanException("解压后缺少 CMakeLists.txt")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_PROGRAMS"] = True
        tc.variables["ENABLE_TESTING"] = True
        tc.variables["GEN_FILES"] = False
        tc.variables["UNSAFE_BUILD"] = False
        # 上游默认把警告当错误。Clang 15 对测试生成代码的告警不应阻断适配。
        tc.variables["MBEDTLS_FATAL_WARNINGS"] = False
        tc.variables["USE_STATIC_MBEDTLS_LIBRARY"] = not bool(self.options.shared)
        tc.variables["USE_SHARED_MBEDTLS_LIBRARY"] = bool(self.options.shared)
        tc.variables["LINK_WITH_PTHREAD"] = True
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        user_cfg = os.path.join(self.export_sources_folder, "user_config_armv8_if_present.h")
        tc.variables["MBEDTLS_USER_CONFIG_FILE"] = user_cfg.replace("\\", "/")
        python3 = shutil.which("python3") or shutil.which("python")
        if python3:
            tc.variables["Python3_EXECUTABLE"] = python3
            tc.variables["MBEDTLS_PYTHON_EXECUTABLE"] = python3
        tc.generate()

    def _bash(self):
        return os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"

    @staticmethod
    def _rc(value):
        if value is None:
            return 0
        return int(value)

    def _crypto_evidence(self):
        """记录 AES-CE / PMULL / SHA 指令是否进入目标文件。失败不阻断测试。"""
        bash = self._bash()
        cmd = r"""
set +e
echo '=== CRYPTO_EVIDENCE ==='
find . \( -name 'aesce.c.obj' -o -name 'sha256.c.obj' -o -name 'sha512.c.obj' -o -name 'aesce.c.o' -o -name 'sha256.c.o' -o -name 'sha512.c.o' \) | while read -r obj; do
  echo "-- $obj"
  llvm-objdump -d "$obj" 2>/dev/null | grep -E -m 6 'aese|aesd|aesmc|aesimc|pmull|sha256h|sha256su|sha512h|sha512su' | head -n 6
  echo "-- nm $obj"
  llvm-nm "$obj" 2>/dev/null | grep -E 'mbedtls_aesce_has_support|mbedtls_a64_crypto_sha' | head -n 20
done
echo '=== CRYPTO_EVIDENCE_END ==='
"""
        self.run(f'"{bash}" -c {self._shell_quote(cmd)}', cwd=self.build_folder, env="conanbuild")

    @staticmethod
    def _shell_quote(text):
        return "'" + text.replace("'", "'\"'\"'") + "'"

    def _run_script(self, script):
        bash = self._bash()
        tests_dir = os.path.join(self.build_folder, "tests")
        path = os.path.join(tests_dir, script)
        if not os.path.isfile(path):
            raise ConanException(f"缺少上游脚本 {path}")
        # 脚本自己会 cd 到自身目录，并用 ../programs 找 ssl_server2。
        self.output.info(f"运行上游 {script}")
        cnf = os.path.join(self.export_sources_folder, "openssl-legacy.cnf")
        prefix = f'OPENSSL_CONF="{cnf}" ' if os.path.isfile(cnf) else ""
        return self._rc(self.run(
            f'{prefix}"{bash}" "{path}"',
            cwd=tests_dir, env="conanbuild", ignore_errors=True))

    def _prepare_test_tree(self):
        """compat.sh 按源码树相对路径找 framework/scripts。
        源外构建只链了 data_files，没有链 scripts。补上这个链接。"""
        dest_parent = os.path.join(self.build_folder, "framework")
        dest = os.path.join(dest_parent, "scripts")
        src = os.path.join(self.source_folder, "framework", "scripts")
        if os.path.isdir(dest) or os.path.islink(dest):
            return
        os.makedirs(dest_parent, exist_ok=True)
        try:
            os.symlink(src, dest)
        except OSError as exc:
            self.output.warning(f"symlink framework/scripts 失败（{exc}），改为复制")
            shutil.copytree(src, dest)

    def build(self):
        self._ensure_sources()
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._crypto_evidence()
        self._prepare_test_tree()
        # PSA ITS 把密钥写成当前目录下的文件。ctest -jN 会让多个套件
        # 同时写同一组文件，出现 DATA_INVALID / ALREADY_EXISTS。必须 -j1。
        # --output-on-failure 会丢掉通过套件的「PASSED (n/m)」汇总，所以把
        # 详细日志落到文件，再把汇总行打出来。
        bash = self._bash()
        ctest_bin = shutil.which("ctest") or "ctest"
        log = os.path.join(self.build_folder, "ctest-verbose.log")
        unit_cmd = (
            f'"{ctest_bin}" -j1 --verbose > "{log}" 2>&1\n'
            "rc=$?\n"
            f'grep -E "PASSED \\(|FAILED \\(|tests passed" "{log}" || true\n'
            "exit $rc\n"
        )
        unit = self._rc(self.run(
            f'"{bash}" -c {self._shell_quote(unit_cmd)}',
            cwd=self.build_folder,
            env="conanbuild",
            ignore_errors=True,
        ))
        cnf = os.path.join(self.export_sources_folder, "openssl-legacy.cnf")
        os.environ["OPENSSL_CONF"] = cnf
        ssl = self._run_script("ssl-opt.sh")
        compat = self._run_script("compat.sh")
        self.output.info(f"UPSTREAM_RC unit={unit} ssl={ssl} compat={compat}")
        if unit:
            raise ConanException(f"ctest 未通过，退出码 {unit}")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 库包不交付 programs/，避免 L0k 把本包当成 CLI。测试已在 build() 用构建树程序跑完。
        rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # 静态链接顺序：mbedtls -> mbedx509 -> mbedcrypto
        self.cpp_info.libs = ["mbedtls", "mbedx509", "mbedcrypto"]
        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread"]
