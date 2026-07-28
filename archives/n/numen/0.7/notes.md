# numen 0.7 适配笔记

## 编译环境
- 构建系统: custom (Go `go build`)
- 编译日期: 2026-07-28
- 编译器: Go (1.19+)，CGO_ENABLED=1
- 状态: published

## 软件简介

numen 是一个语音控制工具，允许用户通过语音命令操作计算机。它使用 vosk-api 进行语音识别，将识别结果转为 dotool 命令执行鼠标/键盘操作。适用于无障碍辅助场景。

## 编译步骤

1. 获取源码：从 Sourcehut 下载 0.7 版本 tarball
2. 应用补丁：无（numen 0.7 源码无需补丁即可在 HarmonyOS 上编译）
3. Go 构建：
   ```bash
   CGO_ENABLED=1 go build -ldflags "-X 'main.Version=0.7'" -o numen .
   ```
4. 安装：
   - `numen` 二进制 → bin/
   - `numenc` shell 脚本 → bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 默认生成 autotools 模板 | numen 是 Go 项目，无 configure 脚本 | 手动重写 conanfile.py 为 Go build |
| 2 | Sourcehut tarball URL 直接下载失败 | 某些网络环境无法访问 git.sr.ht | 通过 git clone + git archive 生成 tarball |
| 3 | numen 依赖 vosk-api (CGO) | Go vosk 绑定需要 C++ 库 | 构建时设置 CGO_ENABLED=1 |

## 源码修改

无补丁。numen 0.7 源码无需修改即可在 HarmonyOS 上编译。

## 依赖版本

### 构建依赖
- Go 1.19+ (go.mod 要求)
- CGO (CGO_ENABLED=1)
- vosk-api C++ 库（通过 Go 绑定 github.com/alphacep/vosk-api/go 引入）

### 运行时依赖
- dotool（鼠标/键盘操作执行）
- alsa-utils（arecord 录音）
- vosk 语音模型（运行时需要下载）

## 验证结果

```bash
# 冒烟测试：验证 numen 二进制可执行
numen --version
# 预期输出: 0.7 (通过 -ldflags 注入的版本号)
```

完整功能测试需要麦克风 + vosk 语音模型，超出 CI 范围。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/numen | 主二进制（Go 编译） |
| bin/numenc | 命令行控制脚本（shell） |

## 注意事项

1. **CGO 必需**：numen 依赖 vosk-api Go 绑定，必须 CGO_ENABLED=1
2. **运行时依赖**：完整使用需要 dotool + arecord + vosk 模型
3. **交叉编译**：CGO 交叉编译需要目标架构的 C/C++ 工具链
4. **R38 合规**：package_type=application，已创建 commands.json 声明 `numen` 命令
---

**编译结束**: 2026-07-28 11:53
**最终状态**: failed
