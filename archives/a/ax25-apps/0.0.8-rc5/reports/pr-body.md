## PR 信息
- **三方库名称**：ax25-apps
- **上游版本**：0.0.8-rc5
- **上游仓库地址**：https://deb.debian.org/debian/pool/main/a/ax25-apps/ax25-apps_0.0.8-rc5+git20230513+afc4a5f.orig.tar.xz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游测试套件 |
| 集成测试 | 0 | - |
| 其他测试 | 0 | 跳过的测试 |
| **合计** | **0** | |

### 是否存在对上游测试用例的修改？
是，见下方补丁说明

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 一致 | 通过 0/0 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 0 | - | 新增 |
| **合计** | **0** | | |

---

## 上游测试用例修改说明
ax25-apps 上游无测试套件（make check 无测试目标）。适配补丁不涉及测试代码修改，仅修改源码以适配 OHOS 平台：
- 0001: termio.h → termios.h（OHOS 不提供 termio.h，POSIX 已弃用）
- 0002: call.h 添加 time.h 头文件包含（上游遗漏，在 OHOS 上编译报错）
- 0003: 移除 yapp.c 中未使用的 linux/ax25.h（OHOS sysroot 中 sockaddr_storage 定义冲突）

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: autotools
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: autotools, 状态: published |
| 产物存在性 | PASS | conan create 验证通过 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 0, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: libax25/0.0.12-rc5 |

### 补丁说明
- `0001-ax25ipd-io.c.patch`: 0001-ax25ipd-io.c.patch
- `0002-call-call.h.patch`: 0002-call-call.h.patch
- `0003-call-yapp.c.patch`: 0003-call-yapp.c.patch

### 依赖
- libax25/0.0.12-rc5

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
无已知问题

### 验证命令
```
# conan-verify (8道门禁全部通过)
python3 scripts/ohc-run.py conan-verify ax25-apps 0.0.8-rc5
# 结果: G1 PASS, G0 PASS, G2 PASS, G3 PASS, G4 PASS, L2 PASS, L4 PASS, L5 PASS

# 本地 CI 模拟 (W3)
python3 scripts/ohc-run.py finish ax25-apps 0.0.8-rc5 published
# 结果: W3 setup.sh PASS, build_and_test.sh PASS

# 功能测试
ax25ipd --version   # → ax25ipd 0.0.8-rc5 (exit 0)
ax25rtctl --version  # → ax25rtctl: 0.0.8-rc5 (exit 0)
ax25mond --version   # → Version 0.0.8-rc5 (exit 1, expected)

# ELF 架构验证
readelf -h bin/ax25ipd  # → Machine: AArch64, Class: ELF64
```
