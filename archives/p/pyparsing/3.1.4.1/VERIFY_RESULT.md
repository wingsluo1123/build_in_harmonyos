# pyparsing 3.1.4.1 本地 Conan 编译+测试验证结果

## 编译状态

**成功** ✅

`conan create` 从源码本地构建成功，`conan test` 全部测试通过，测试通过率 **100%**。

---

## 本地编译证据

日志文件: `/storage/Users/currentUser/Desktop/build_in_harmonyos/.pyparsing-verify.log`

### 1. pip install 本地安装过程

| 行号 | 原文 |
|------|------|
| 74 | `pyparsing/3.1.4: RUN: /storage/Users/currentUser/usr/local/bin/python3 -m pip install . --prefix=/storage/Users/currentUser/.conan2/p/b/pypar7594e45e95df5/b/build/package --no-deps` |
| 83 | `Building wheels for collected packages: pyparsing` |
| 84 | `  Building wheel for pyparsing (pyproject.toml): started` |
| 85 | `  Building wheel for pyparsing (pyproject.toml): finished with status 'done'` |
| 86 | `  Created wheel for pyparsing: filename=pyparsing-3.1.4-py3-none-any.whl size=104141 sha256=93a33b6a2dfe72bfce6489d53e771f25308edecb729c90dfac55e89eeebeeb4c` |
| 90 | `Successfully installed pyparsing-3.1.4` |

**判定**: 构建方式为 `pip install . --prefix=... --no-deps`，从本地源码树构建 wheel 并安装，符合"从源码本地 pip 安装"要求。

### 2. pyparsing 模块文件产出

| 行号 | 原文 |
|------|------|
| 109 | `pyparsing/3.1.4: pyparsing installed: lib/python3.12/site-packages/pyparsing/` |
| 125 | `pyparsing/3.1.4: pyparsing installed: lib/python3.12/site-packages/pyparsing/` |
| 210 | `pyparsing/3.1.4: pyparsing installed: lib/python3.12/site-packages/pyparsing/` |

package() 阶段产出了 11 个 .py 文件、1 个 py.typed、11 个 .pyc、1 个 direct_url.json（日志行 95-101）。

### 3. 无远程预编译包下载

- `grep 'Download (ohpcd)'` → 无匹配（grep exit=1）
- `grep 'Retrieving package'` → 无匹配（grep exit=1）

**判定**: 日志中未出现任何从制品仓下载预编译包的记录，构建完全本地完成。源码 tar.gz 从 GitHub 下载（`get()` 步骤），属于源码获取而非预编译包下载，符合 `-nr`（不使用远程仓库）+ `--build=missing`（从源码构建缺失包）的预期行为。

---

## conan create 结果

- **状态**: 成功（EXIT_CODE=0）
- **recipe revision**: `be4d9ccec90e8c7b6bc7c9ccd0aa4b49`
- **package ID**: `199b501a334fc7fce69568b5806901bfdcee316a`
- **package revision**: `b2665da3f9dac0b19bc392d6f0ba45e4`
- **完整 ref**: `pyparsing/3.1.4#be4d9ccec90e8c7b6bc7c9ccd0aa4b49:199b501a334fc7fce69568b5806901bfdcee316a#b2665da3f9dac0b19bc392d6f0ba45e4`
- **构建 settings**: os=OHOS, os.version=6.0, arch=armv8
- **构建 options**: shared=False

### conan 缓存中的 ref

```
Local Cache
  pyparsing
    pyparsing/3.1.4
      revisions
        be4d9ccec90e8c7b6bc7c9ccd0aa4b49 (2026-08-10 04:25:39 UTC)
          packages
            199b501a334fc7fce69568b5806901bfdcee316a
              info
                settings
                  arch: armv8
                  os: OHOS
                  os.version: 6.0
                options
                  shared: False
```

---

## test_package 执行结果

### conan create 内嵌 test_package（第 1 次执行）

| 用例 | 行号 | 结果 |
|------|------|------|
| Test 1: Module import | 141-142 | ✅ PASS（`pyparsing version: 3.1.4`） |
| Test 2: Basic word parsing | 143-144 | ✅ PASS（`Word parsing: PASS (result: ['hello'])`） |
| Test 3: ParseException on invalid input | 145-148 | ✅ PASS（`ParseException correctly raised`） |
| Test 4: DOT-style node parsing | 147-149 | ✅ PASS（`DOT node parsing: PASS` + `delimited_list parsing: PASS`） |
| Test 5: Attribute parsing | 150-151 | ✅ PASS（`Attribute parsing: PASS (key=label, value=center)`） |

汇总行 153: `=== All tests PASSED ===`

### conan test 独立执行（第 2 次执行）

| 用例 | 行号 | 结果 |
|------|------|------|
| Test 1: Module import | 226-227 | ✅ PASS |
| Test 2: Basic word parsing | 228-229 | ✅ PASS |
| Test 3: ParseException on invalid input | 230-231 | ✅ PASS |
| Test 4: DOT-style node parsing | 232-234 | ✅ PASS |
| Test 5: Attribute parsing | 235-236 | ✅ PASS |

汇总行 238: `=== All tests PASSED ===`

### 统计

- **通过用例数**: 5 / 5
- **通过率**: **100%**
- **两轮执行均全部通过**

---

## 失败情况

无失败。编译、测试均 100% 通过，无需崩溃点分析。

---

## 完整日志路径

`/storage/Users/currentUser/Desktop/build_in_harmonyos/.pyparsing-verify.log`（262 行，含 conan create + conan test + conan list 完整输出）

---

## 结论

| 检查项 | 结果 |
|--------|------|
| conan create 成功 | ✅ |
| 本地源码编译（非远程下载预编译包） | ✅ pip install . 本地构建 wheel |
| site-packages/pyparsing/ 产出 | ✅ |
| 无 Download (ohpcd) / Retrieving package | ✅ |
| conan test 通过率 100% | ✅ 5/5 |
| conan 缓存已建立 | ✅ pyparsing/3.1.4 in local cache |
| 是否需要打回重做 | **否** |
