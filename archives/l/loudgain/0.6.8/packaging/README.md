Conan 配方包（conanfile.py），打包产物由 `conan create` 生成并上传至 CNB 制品仓。
本目录为归档占位，实际交付物为 conan 包：loudgain/0.6.8@ohpcd/stable。

tarball 内容（loudgain-0.6.8-ohos-aarch64.tar.gz，取自 conan create 最终包目录）：
- bin/loudgain   — ReplayGain 2.0 CLI 主程序（动态链接 ffmpeg/taglib/libebur128 conan 包）
- bin/rgbpm      — 上游附带的批量 ReplayGain/BPM 辅助 shell 脚本
- licenses/      — BSD-2-Clause 许可文本
- share/man/man1 — loudgain(1) 手册页
