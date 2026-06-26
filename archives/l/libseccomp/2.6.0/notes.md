# libseccomp 2.6.0 — 适配笔记

## 平台
- 目标: OpenHarmony (aarch64)
- 构建系统: autotools

## 适配步骤

### 1. 平台检测
config.guess 不识别 HarmonyOS，使用 `patch-autotools-ohos.pl` 打补丁:
```
perl ${SKILL_ROOT}/scripts/patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub
```

### 2. 源码修改
- `src/arch-gperf-generate`: 添加 OHOS 平台分支
- `src/arch-syscall-check`: 调整 syscall 检测逻辑适配 OHOS
- `src/arch-syscall-validate`: 修正 syscall 验证

### 3. 编译命令
```
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

### 4. 产物
- libseccomp.so.2.6.0
- libseccomp.a
- scmp_sys_resolver (工具)
- 头文件: seccomp.h, seccomp-syscalls.h
- pkg-config: libseccomp.pc
---

**编译结束**: 2026-06-26 11:46
**最终状态**: built
