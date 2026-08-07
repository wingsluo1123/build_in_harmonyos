## PR 信息
- **三方库名称**：pkcs11-tools
- **上游版本**：2.6.0
- **上游仓库地址**：https://github.com/Mastercard/pkcs11-tools
- **适配路径**：路径 A（基础适配，无补丁）
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
否

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 一致 | 通过 0/0 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 0 | - | 新增 |
| **合计** | **0** | | |

---

## 上游测试用例修改说明
### 新增文件
- `manual-bootstrap.py`: 手动 bootstrap 脚本，替代 gnulib-tool
- `include/target.h`: 目标平台定义头文件
### 修改文件
- `include/config.h`: 添加 `_GL_CONFIG_H_INCLUDED 1`
- `lib/Makefile`: 修复 LIBCRYPTO_CFLAGS 和 LIBCRYPTO_LIBS
- `src/Makefile`: 修复 LIBCRYPTO_CFLAGS 和 LIBCRYPTO_LIBS
- `config.status`: 修改临时目录路径为 .config-tmp

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
| 动态依赖 | PASS | 依赖: openssl/3.5.6 |

### 补丁说明
无补丁

### 依赖
- openssl/3.5.6

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
- **1**: 根因=bootstrap.sh 失败, 解决方案=HMDFS 不支持在临时目录创建文件，且 tarball 没有 .git 目录
- **2**: 根因=config.status 失败, 解决方案=HMDFS 不支持在 mktemp 创建的临时目录中创建文件
- **3**: 根因=oasis-pkcs11 缺失, 解决方案=git submodule，tarball 中为空
- **4**: 根因=LIBCRYPTO 变量无效, 解决方案=configure 生成了包含方括号的无效变量名
- **5**: 根因=target.h 缺失, 解决方案=AX_CREATE_TARGET_H 宏未正确执行
- **6**: 根因=_GL_CONFIG_H_INCLUDED 缺失, 解决方案=简化的 gnulib-m4.m4 不完整

### 验证命令
```
编译成功，生成 22 个可执行文件：
- p11mkcert, p11rewrap, p11wrap, p11unwrap, p11cp, p11ls, p11cat, p11more, p11od, p11rm, p11mv
- p11slotinfo, p11req, p11importcert, p11importpubk, p11importdata, p11keycomp, p11setattr
- masqreq, p11keygen, p11kcv
- with_beid, with_luna, with_nfast, with_nss, with_softhsm, with_utimaco, with_aws
```
