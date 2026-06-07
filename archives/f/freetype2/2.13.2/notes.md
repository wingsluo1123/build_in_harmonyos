# freetype2 2.13.2 编译笔记

## 编译日期
2026-05-26

## 版本信息
- 源码版本: 2.13.2 (FREETYPE_MAJOR=2, FREETYPE_MINOR=13, FREETYPE_PATCH=2)
- pkg-config 版本: 26.1.20 (libtool 格式)
- 官方版本号映射: libtool 版本号 26.1.20 对应实际版本 2.13.2

## 编译状态
built (编译成功，未发布)

## 安装路径
- 库文件: ~/usr/local/lib/libfreetype.a (939KB)
- pkg-config: ~/usr/local/lib/pkgconfig/freetype2.pc
- 头文件: ~/usr/local/include/freetype2/

## 构建系统
CMake (autotools 在 HMDFS 上有临时文件权限问题)

## 编译流程

### 1. 下载源码
```bash
cd ~/tmp
curl -L -o freetype-2.13.2.tar.xz "https://sourceforge.net/projects/freetype/files/freetype2/2.13.2/freetype-2.13.2.tar.xz/download"
tar -xJf freetype-2.13.2.tar.xz
```

### 2. 配置阶段遇到的问题

#### 问题 1: E007 - config.guess 无法识别 HarmonyOS
**症状**:
```
checking build system type... ./config.guess[1729]: can't create /storage/Users/currentUser/tmp/cgagfKkg/dummy.c: Permission denied
config.guess: unable to guess system type
```

**解决方案**:
使用 SKILL 提供的补丁脚本:
```bash
perl ${SKILL_ROOT}/scripts/patch-autotools-ohos.pl builds/unix/config.guess builds/unix/config.sub
```

补丁后还需要手动修复 config.sub 的内核-OS 组合验证:
```bash
sed -i 's/| linux-uclibc\* | linux-mlibc\* )/| linux-uclibc* | linux-mlibc* | linux-ohos* )/' builds/unix/config.sub
```

#### 问题 2: HMDFS 临时文件权限问题
**症状**:
```
./config.status[1027]: can't create ./confPLIeKI/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根因**: HMDFS 文件系统不支持在源码目录下创建临时目录

**解决方案**: 切换到 CMake 构建系统
```bash
mkdir -p ~/tmp/freetype-build
cd ~/tmp/freetype-build
cmake -DCMAKE_INSTALL_PREFIX=~/usr/local -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ~/tmp/freetype-2.13.2
```

### 3. 编译和安装
```bash
cd ~/tmp/freetype-build
make -j4
make install
```

## 依赖情况
- **zlib**: ✅ 已安装 (1.3.1)
- **harfbuzz**: ❌ 未安装 (可选)
- **libpng**: ❌ 未安装 (可选)
- **bzip2**: ❌ 未安装 (可选)
- **brotli**: ❌ 未安装 (可选)

## pkg-config 验证
```bash
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --modversion freetype2
# 输出: 26.1.20 (libtool 格式，对应 2.13.2)
pkg-config --cflags freetype2
# 输出: -I${includedir}/freetype2
pkg-config --libs freetype2
# 输出: -L${libdir} -lfreetype
```

## 关键发现

### 1. freetype2 的构建系统选择
freetype2 支持三种构建系统:
- autotools (./configure)
- CMake (推荐)
- Meson

在 HMDFS 文件系统上，autotools 有临时文件权限问题，CMake 更稳定。

### 2. pkg-config 版本号格式
freetype2 的 pkg-config 版本号使用 libtool 格式:
- 标准: 2.13.2
- libtool: 26.1.20

这是 freetype 的历史遗留设计，不影响实际使用。

### 3. E007 补丁脚本
SKILL 的 `patch-autotools-ohos.pl` 脚本需要额外手动修复:
- 脚本添加了 `linux-ohos` 到 OS 列表
- 但缺少 `linux-ohos*` 到内核-OS 组合验证列表
- 需要手动 sed 补充

建议改进补丁脚本以包含内核-OS 组合验证修复。

## 后续建议

1. **发布预编译包**: 需要制作 tar.gz 预编译包并签名
2. **安装可选依赖**: 如需 PNG/BZip2/Brotli 支持，需先编译这些依赖
3. **改进补丁脚本**: 建议更新 patch-autotools-ohos.pl 以包含内核-OS 组合验证修复

---
*编译笔记结束*
---

**编译结束**: 2026-05-26 13:51
**最终状态**: built
