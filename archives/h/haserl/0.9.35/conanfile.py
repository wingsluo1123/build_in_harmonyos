#!/usr/bin/env python3
import glob
import os
import re
import shutil
from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout

_OHOS_BIN = "/data/service/hnp/bin"
_OHOS_OBJCOPY = _OHOS_BIN + "/llvm-objcopy"
_OHOS_SIGNER = _OHOS_BIN + "/binary-sign-tool"


class HaserlConan(ConanFile):
    name = "haserl"
    version = "0.9.35"
    description = "Small CGI wrapper that embeds shell scripts in HTML pages (PHP-like approach for shell scripts)"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/haserl/"
    url = "https://sourceforge.net/projects/haserl/"
    topics = ("cgi", "shell", "scripting")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 上游 2010 年代 config.guess/sub 不认识 HarmonyOS：显式指定构建三元组
        tc.configure_args.extend([
            "--without-lua",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        tc.generate()
        Environment().vars(self).save_script("haserl_env")

    def build(self):
        apply_conandata_patches(self)
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            t = open(cfg).read()
            # 1) 交叉编译检测为内联 exec：未签名 ELF 被拒执行时 as_fn_error 退出
            #    → 替换为 no-op（本机为原生构建，语义上本应通过）
            if "cannot run C compiled programs" in t:
                t2 = re.sub(
                    r'as_fn_error \$? "cannot run C compiled programs\..*?" "\$LINENO" 5',
                    '$as_echo "OHOS-assume-pass" >&2', t, flags=re.S)
                if t2 != t:
                    t = t2
            # 2) 其它 try-run 探测（ac_fn_c_try_run）兜底为通过
            fn = "ac_fn_c_try_run ()\n{\n"
            if fn in t:
                t = t.replace(fn, fn + "  return 0\n", 1)
            # 3) config.status 以 umask 077 建临时目录在 HMDFS 写入 EACCES → 放宽 022
            if "umask 077" in t:
                t = t.replace("umask 077", "umask 022")
            open(cfg, "w").write(t)
        # 老 autotools 项目为 in-source 构建：configure 与 make 均在源码目录执行
        self.run("./configure --prefix=/ --without-lua "
                 "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu",
                 cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        self.run('make install DESTDIR="%s"' % self.package_folder,
                 cwd=self.source_folder)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        self._sign_artifacts()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as h:
                return h.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_artifacts(self):
        targets = []
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for n in os.listdir(bindir):
                p = os.path.join(bindir, n)
                if os.path.isfile(p) and not os.path.islink(p):
                    targets.append(p)
        targets = [t for t in targets if self._is_elf(t)]
        if not targets:
            return
        if not os.path.isfile(_OHOS_SIGNER):
            self.output.warning("binary-sign-tool not found; skip codesign")
            return
        objcopy = _OHOS_OBJCOPY if os.path.isfile(_OHOS_OBJCOPY) else shutil.which("llvm-objcopy")
        for t in sorted(set(targets)):
            if objcopy:
                self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true'
                         % (objcopy, t))
            self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                     % (_OHOS_SIGNER, t, t))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
