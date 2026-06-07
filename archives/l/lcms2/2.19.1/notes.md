# lcms2 2.19.1 适配笔记

## 编译环境

| 项目 | 值 |
|------|-----|
| 软件 | lcms2 |
| 版本 | 2.19.1 |
| 状态 | ✅ success |
| 构建系统 | cmake (切换自 autotools) |
| 源码路径 | /storage/Users/currentUser/tmp/builds/lcms2-2.19.1.work |
| 安装路径 | /storage/Users/currentUser/usr/local |

## 问题记录

### 问题 1: config.guess 无法识别 HarmonyOS

**现象**:
- config.guess (2018-02-24 版本) 无法识别 HarmonyOS 系统
- uname -s 返回 "HarmonyOS"
- 已应用 patch-autotools-ohos.pl 补丁，但仍无法识别

**尝试方案**:
1. ✅ 应用 patch-autotools-ohos.pl 补丁 → 失败，仍然无法识别
2. ✅ 切换到 cmake 构建 → 成功

**决策**: 使用 cmake 构建，避免 autotools 平台识别问题

## 编译步骤

### Step 1: init-build (已完成)
- ✅ 源码下载成功（从 GitHub tarball）
- ✅ 解压到工作目录
- ✅ 档架创建完成

### Step 2: cmake 构建流程 (已完成)
- ✅ cmake configure（设置 CMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX）
- ✅ make 编译成功
- ✅ make install DESTDIR=$TEST_PREFIX（staging 验证）
- ✅ 测试运行成功（testcms）
- ✅ make install 到本地系统

### Step 3: 验证 (已完成)
- ✅ pkg-config --modversion lcms2 = 2.19
- ✅ transicc 工具可执行
- ✅ liblcms2.so 和 liblcms2.a 已安装

## 知识沉淀

- **构建系统选择**: lcms2 同时支持 autotools 和 cmake，在 HarmonyOS 上推荐使用 cmake
- **依赖库**: 自动检测到 JPEG、TIFF、ZLIB 库
- **编译产物**: 共享库 liblcms2.so、静态库 liblcms2.a、工具程序（transicc、linkicc、psicc、jpgicc、tificc、tifdiff）

**编译结束**: 2026-05-26 15:05
**最终状态**: success
---

**编译结束**: 2026-05-26 15:06
**最终状态**: built
