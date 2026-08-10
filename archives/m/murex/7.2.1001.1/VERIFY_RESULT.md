# VERIFY_RESULT — murex 7.2.1001

## 1. 编译状态

**成功** ✅

`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing -nr` 退出码 0，产出 15MB 静态 stripped ELF arm64 murex 二进制。

---

## 2. 本地编译证据

完整日志：`/storage/Users/currentUser/Desktop/build_in_harmonyos/.murex-verify.log`（394 行）

### 2.1 Building from source（日志第 91 行）

```
murex/7.2.1001.1: Building from source
murex/7.2.1001.1: Building your package in /storage/Users/currentUser/.conan2/p/b/murex61652286e3057/b
```

### 2.2 上游 go test ./...（日志第 102-228 行）

109 个测试包全 `ok`，0 个 `FAIL`（43 个无测试文件的包跳过）。示例：

```
ok  	github.com/lmorg/murex	1.326s
ok  	github.com/lmorg/murex/app	0.444s
ok  	github.com/lmorg/murex/builtins/core/arraytools	0.700s
ok  	github.com/lmorg/murex/builtins/core/autocomplete	0.695s
ok  	github.com/lmorg/murex/builtins/core/config	0.673s
ok  	github.com/lmorg/murex/builtins/core/io	4.079s
ok  	github.com/lmorg/murex/builtins/core/pipe	7.683s
ok  	github.com/lmorg/murex/builtins/core/processes	7.652s
```

### 2.3 go build 产出 murex 二进制

15MB ELF 64-bit arm64 static stripped，缓存于 `~/.conan2/p/b/murex61652286e3057/p/bin/murex`。

### 2.4 无远程下载确认

日志中 `Download (ohpcd)` / `Retrieving package ... from remote` 出现次数：**0**。`-nr` 标志确保完全本地构建，源码从本地下载缓存取，Go 工具链从 Aliyun 镜像 sha256 校验下载，Go 模块通过 goproxy.cn 下载。

---

## 3. conan create 结果

| 项目 | 值 |
|------|-----|
| 命令 | `conan create . -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64 --build=missing -nr` |
| exit code | 0 |
| Recipe revision | `73b8bb2e05cecfabfcc14d8e8d03d02e` |
| Package ID | `6b129b068851896169fae42d399fa922d239ce8a` |
| conan 缓存 | `conan list "murex/*"` → Local Cache 中有 `murex/7.2.1001.1` |

---

## 4. test_package 执行结果

### 4.1 test_murex.py 3 断言（日志第 295 + 369 行）

```
murex package checks passed: 3/3
```

- 断言1：`murex -c "echo ohpcd"` 输出 `ohpcd` ✅
- 断言2：`murex -version` 含 `7.2.1001` ✅
- 断言3：可执行文件存在性 ✅

### 4.2 测试通过率

| 指标 | 值 |
|------|------|
| 上游 go test ./... | 109 ok / 0 FAIL / 43 no-test-files = **100%** |
| test_package | 3/3 断言通过 = **100%** |

---

## 5. 失败分析

**无失败**。编译、上游测试、test_package 全通过。

---

## 6. 是否需要打回重做

**否**。编译成功 ✅，本地编译（非远程下载）✅，上游测试 100% 通过 ✅，test_package 100% 通过 ✅，缓存已建立 ✅。

---

## 7. 配方修改说明

修改了 `conanfile.py` 的 `_chmod_read_exec()` 方法，添加 `PermissionError` 容错：

```python
try:
    os.chmod(path, mode | read_exec)
except PermissionError:
    # HMDFS: chmod on non-owned files fails even when we only add bits.
    # If the file is already executable (or readable for non-exec), skip.
    if not (executable or is_dir):
        raise
    if os.access(path, os.X_OK):
        return
    raise
```

**修改原因**：OHOS/HMDFS 文件系统上，对非所有者文件执行 `os.chmod()` 会抛 `PermissionError`，即使只是添加读/执行位。fallback Go 工具链解压后的文件归属可能导致 chmod 失败，中断构建。容错逻辑：若文件已可执行（`os.access(path, os.X_OK)`）则跳过，否则仍 raise。

同时将 `manifest.yaml` 的 `status` 从 `pending` 更改为 `built`，反映本地验证已通过。

---

## 8. 验证流程摘要

| 步骤 | 命令 | 结果 |
|------|------|------|
| 1. 本地构建 | `conan create ... --build=missing -nr` | exit 0，15MB ELF arm64 二进制 |
| 2. 上游测试 | `go test ./...`（build() 内） | 109 ok / 0 FAIL |
| 3. test_package | `conan test test_package ...` | 3/3 断言通过 |
| 4. 缓存确认 | `conan list "murex/*"` | murex/7.2.1001.1 in Local Cache |

完整日志路径：`/storage/Users/currentUser/Desktop/build_in_harmonyos/.murex-verify.log`
