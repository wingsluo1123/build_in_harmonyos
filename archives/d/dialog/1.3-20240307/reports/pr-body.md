## PR 信息
- **三方库名称**：dialog
- **上游版本**：1.3-20240307
- **上游仓库地址**：https://invisible-mirror.net/archives/dialog/dialog-1.3-20240307.tgz
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
未修改上游测试用例。仅修改了构建系统配置文件 `config.sub`，添加 OHOS 平台识别（`ohos*` OS 验证 + `linux-ohos*-` kernel 验证）。上游 `make check` 测试（create-rc）在适配后仍正常运行，全部通过。

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: autotools
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: autotools, 状态: built |
| 产物存在性 | PASS | conan create 验证 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 0, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: ncurses (system-installed via cmd-pkgs, static + bundled headers) |

### 补丁说明
- `0001-config.sub.patch`: 添加 OHOS 平台识别到 config.sub（ohos* OS 验证 + linux-ohos*- kernel 验证）

### 依赖
- ncurses (system-installed via cmd-pkgs, static + bundled headers)

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
无已知问题

### 验证命令
```
# 1. 编译验证
./configure --prefix=$TEST_PREFIX --build=aarch64-linux-ohos --host=aarch64-linux-ohos --with-ncurses
make -j1
make install DESTDIR=$TEST_PREFIX
# 结果: 编译成功，生成 dialog 二进制和 libdialog.a 静态库

# 2. 上游测试
make check
# 结果: PASS (create-rc test with 5 sample RC files: debian, slackware, sourcemage, suse, whiptail)

# 3. 运行时验证
./dialog --version
# 结果: Version: 1.3-20240307

# 4. Conan 配方验证 (conan create + test_package)
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 结果: G2 PASS, test_package PASS (dialog --version)
```
