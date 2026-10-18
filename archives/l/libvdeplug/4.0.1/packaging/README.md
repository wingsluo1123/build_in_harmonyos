# libvdeplug 4.0.1 packaging

- 产物: libvdeplug-4.0.1-ohos-aarch64.tar.gz
- 来源: 探索性构建 staging（make install DESTDIR），与 conan create 包内容一致
- 内容: bin/(vde_plug, dpipe)、include/(libvdeplug.h, libvdeplug_mod.h)、
  lib/(libvdeplug.so.2 + .a, libvdeplug_mod.so.2, vdeplug/ 下 13 个插件模块)、share/man
- 平台: OpenHarmony PC aarch64 (musl libc), clang 15.0.4
- SONAME: libvdeplug.so.2；RUNPATH: $ORIGIN:$ORIGIN/../lib（E1013 修复后）
- 运行时依赖: 无（libexecs 静态嵌入 libvdeplug_cmd.so 插件）
