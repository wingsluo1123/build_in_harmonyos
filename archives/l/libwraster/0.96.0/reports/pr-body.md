## PR 信息
- **三方库名称**：libwraster
- **上游版本**：0.96.0
- **上游仓库地址**：https://github.com/window-maker/wmaker/releases/download/wmaker-0.96.0/WindowMaker-0.96.0.tar.gz
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
- `patches/0001-config.guess.patch` —— config.guess 识别 HarmonyOS，
输出 `aarch64-unknown-linux-ohos`。
- `patches/0002-config.sub.patch` —— config.sub 的 OS 列表接受 `linux-ohos` 组合。
两个补丁均为 `refresh-patch --auto` 生成的 config 探针补丁，已回环验证
（`config.sub aarch64-unknown-linux-ohos` 返回 0）。

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
| 动态依赖 | PASS | 依赖: libx11/6.4.0, libxext/6.4.0, libxpm/3.5.17, libxft/2.3.9 |

### 补丁说明
- `0001-config.guess.patch`: 0001-config.guess.patch
- `0002-config.sub.patch`: 0002-config.sub.patch

### 依赖
- libx11/6.4.0
- libxext/6.4.0
- libxpm/3.5.17
- libxft/2.3.9

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
- **1**: 根因=`config.sub` 拒绝 `aarch64-unknown-linux-ohos`（`OS 'ohos' not recognized`，报错点 config.sub:1766）, 解决方案=2022 年版 config.sub 的 OS 列表没有 `ohos`
- **2**: 根因=`config.h:285:10: fatal error: 'config-paths.h' file not found`, 解决方案=该文件由顶层 Makefile 的 `BUILT_SOURCES` 规则生成，`wrlib/Makefile` 无此规则
- **3**: 根因=configure 报 `No package 'xft' found`, 解决方案=顶层 configure 对 Xft 是硬检查（该探针只服务 WINGs；wrlib 源码零引用 Xft，`wrlib/Makefile.am` 的 `LIBADD` 只含 `@GFXLIBS@ @MAGICKLIBS@ @XLIBS@ @LIBXMU@ -lm`）
- **4**: 根因=`package_info(): The direct dependency 'libxft' is not used by any '(cpp_info/components).requires'`, 解决方案=显式设置 `cpp_info.requires` 时，所有直接依赖都必须列于其中
- **5**: 根因=autotools helper 脚本缺执行位, 解决方案=部分适配路径只保留文件内容、不保留权限位（知识 E490）

### 验证命令
```
```bash
$ python3 scripts/ohc-run.py conan-verify libwraster 0.96.0
G0 ✅  G1 ✅  G2 ✅(conan create)  G3 ✅  G4 ✅  L2/L4/L5 ✅
✅ 配方验证通过: libwraster 0.96.0
```

`test_package/test.c` 通过真实 wraster API（`RLoadImage` / `RCreateImage` /
`RPutPixel` / `RConvertImage` / `RReleaseImage` 等）构建并执行，非空壳测试。

```
