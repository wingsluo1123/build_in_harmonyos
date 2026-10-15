import os

from conan import ConanFile
from conan.tools.build import can_run


class Krb5PkinitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["krb5-pkinit"].package_folder
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_krb5pkinit.c")
        # application package_type 下 CMakeDeps 目标既不传播 include 也不传播库集
        # （CI #89870 报 'krb5.h' file not found、#90892 报 krb5_init_context
        # undefined symbol），改 clang 直接编译（-I/-L 包路径 + 11 库集 + -ldl），
        # 绕过 CMakeDeps/find_package，与 varlink/libmaus2 test_package 同型。
        self.run(
            f"{cc} -o test_krb5pkinit {src} "
            f"-I{pkg}/include -L{pkg}/lib "
            "-lkadm5srv_mit -lkadm5clnt_mit -lkdb5 -lkrad -lkrb5 "
            "-lgssapi_krb5 -lk5crypto -lgssrpc -lkrb5support -lcom_err -lverto -ldl",
            env="conanbuild",
        )

    def test(self):
        if can_run(self):
            pkg = self.dependencies["krb5-pkinit"].package_folder
            libdir = os.path.join(pkg, "lib")
            bin_path = os.path.join(self.build_folder, "test_krb5pkinit")
            # dlopen 包内 pkinit.so 插件 + 库集链接验证（显式 LD_LIBRARY_PATH）
            plugin = os.path.join(pkg, "lib", "krb5", "plugins", "preauth", "pkinit.so")
            self.run(
                f"LD_LIBRARY_PATH='{libdir}' KRB5_PKINIT_PLUGIN='{plugin}' {bin_path}",
                env="conanrun",
            )
            # 真实调用服务端工具 kdb5_util 创建/查询 KDB
            script = os.path.join(self.source_folder, "test_krb5pkinit.sh")
            self.run(f"sh {script}", env="conanrun")
