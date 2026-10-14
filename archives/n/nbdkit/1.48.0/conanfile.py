#!/usr/bin/env python3
"""Conan recipe — nbdkit 1.48.0 (Autotools)

nbdkit 是 NBD 网络块设备服务器，产物为：
  - sbin/nbdkit（服务器主进程，应用型二进制）
  - lib/nbdkit/plugins/*.so（动态插件）
  - lib/nbdkit/filters/*.so（过滤器）
  - include/nbdkit-*.h（公开插件 ABI 头文件）
  - lib/pkgconfig/nbdkit.pc

OHOS 适配要点：
  - config.guess/config.sub 已按 E007/E072 打补丁识别 HarmonyOS（补丁在 patches/）
  - config.status 临时目录：HMDFS 不保留 POSIX 0700 权限位，configure 内
    umask 077 已按 E129 改为 022（补丁在 patches/）
  - 可选依赖（gnutls/curl/libssh/libnfs/libvirt/bzip2/zlib/libnbd/liblzma/
    libzstd/libguestfs/ext2fs 等）本环境缺失，configure 自动 disable 对应
    插件/过滤器，构建核心服务器 + 无依赖插件
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NbdkitConan(ConanFile):
    name = "nbdkit"
    version = "1.48.0"
    description = "NBD server with stable plugin ABI and permissive license"
    license = "BSD-2-Clause"
    homepage = "https://libguestfs.org/nbdkit/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 注意：nbdkit 的 plugins/filters 是 libtool -module -shared 构建的
        # 动态插件，即使服务器静态编译也必须保留共享模块（--disable-shared
        # 会使 libtool 拒绝构建插件："cannot build a shared library"）。
        # 因此此处不设置 --disable-shared；可选依赖层面全部禁用即可。
        # 保持与已验证的本地构建一致：禁用缺失可选依赖，聚焦核心服务器
        tc.configure_args.append("--without-gnutls")
        tc.configure_args.append("--without-curl")
        tc.configure_args.append("--without-ssh")
        tc.configure_args.append("--without-nfs")
        tc.configure_args.append("--without-libvirt")
        tc.configure_args.append("--without-bzip2")
        tc.configure_args.append("--without-zlib")
        tc.configure_args.append("--without-libnbd")
        tc.configure_args.append("--without-liblzma")
        tc.configure_args.append("--without-libzstd")
        tc.configure_args.append("--without-libguestfs")
        tc.configure_args.append("--without-ext2")
        tc.configure_args.append("--without-libtorrent")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # OHOS HMDFS 权限位归一化：HMDFS 强制 group=rwx、清空 other 位，
        # 且 chmod 加 other 位不生效（实测 755→770、644→660）。CI worker
        # 用户若不属于文件 owner/group，dlopen 插件 .so 会报 Permission denied。
        # 此处将 bin/.so/.a 统一加 owner/group 可执行位，并尽可能补 other 位，
        # 从打包源头上规避插件的运行时加载权限问题。
        import os
        for root, dirs, files in os.walk(self.package_folder):
            for f in files:
                p = os.path.join(root, f)
                try:
                    if f.endswith(".so") or f.endswith(".a") or "/bin/" in p:
                        os.chmod(p, 0o775)
                    else:
                        os.chmod(p, 0o664)
                except OSError:
                    pass

    def package_info(self):
        # 应用型：conan Autotools.install 将主程序放入 bin/（本地 autotools
        # 默认 sbin/），插件/过滤器在 lib/nbdkit/ 下
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]