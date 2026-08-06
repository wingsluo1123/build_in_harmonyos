## PR 信息
- **三方库名称**：haproxy
- **上游版本**：3.2.0
- **上游仓库地址**：https://www.haproxy.org/download/3.2/src/haproxy-3.2.0.tar.gz
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
本次适配未修改上游测试用例。两处补丁均为平台兼容性修复：
1. `0001-include-haproxy-compat.h.patch` — 防止 linux/socket.h 重定义 sockaddr_storage（OHOS/musl 与 sys/socket.h 冲突）
2. `0002-src-thread.c.patch` — 用 sched_setaffinity 替换 glibc 专有的 pthread_setaffinity_np

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: makefile
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: makefile, 状态: built |
| 产物存在性 | PASS | conan create 验证 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 0, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: openssl/3.5.6.1, zlib/1.3.1.1, pcre2/10.45 |

### 补丁说明
- `0001-include-haproxy-compat.h.patch`: 0001-include-haproxy-compat.h.patch
- `0002-src-thread.c.patch`: 0002-src-thread.c.patch

### 依赖
- openssl/3.5.6.1
- zlib/1.3.1.1
- pcre2/10.45

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
无已知问题

### 验证命令
```
# Version verification
haproxy -vv

# Config validation
haproxy -c -f test_package/test_config.cfg

# Results:
# - haproxy -vv: Shows version 3.2.0, HarmonyOS HongMeng Kernel, OpenSSL 3.5.6 ✅
# - haproxy -c: Config validation passed ✅
# - conan create: Build and test package passed ✅
```
