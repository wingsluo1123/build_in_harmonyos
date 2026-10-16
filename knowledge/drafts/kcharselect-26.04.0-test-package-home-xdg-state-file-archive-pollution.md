# kcharselect 26.04.0 — test_package 里 HOME 指向归档目录导致 Qt 状态文件污染归档树

## 现象

首次 `conan create` 成功后，归档目录里出现：

```
archives/k/kcharselect/26.04.0/test_package/.local/state/kcharselectstaterc
```

`git add archives/k/kcharselect/` 会把它列进暂存区（`git check-ignore` 不匹配），
于是无意义的运行时状态会随 PR 提交，并可能触发 junk/JC 类门禁。

## 根因

1. conan 对 `test_type = "explicit"` 且未定义 `layout()` 的 test_package，把
   **test_package 源码目录本身**当作构建目录：
   `Test package build folder: .../archives/k/kcharselect/26.04.0/test_package`。
   它在此生成 `conanrun.sh` / `bin/` / `metadata/`（这些已被 .gitignore 覆盖），
   但 `.local/` 不在白名单里。
2. 原配方为给无头 GUI 应用一个干净 HOME 写了
   `env.define("HOME", self.build_folder)`（kblocks/kjumpingcube/kteatime 一族写法），
   于是 HOME 就是归档的 `test_package/`。
3. kcharselect 的 `main()` 在 `QApplication` 之前调用
   `KIconTheme::initTheme()` + `KStyleManager::initStyle()`，二者经 QSettings
   写 `<HOME>/.local/state/kcharselectstaterc` → 正好落进归档树。

## 修复

```python
runtime_home = os.path.join(
    os.environ.get("TMPDIR", tempfile.gettempdir()),
    "kcharselect-test-runtime",
)
os.makedirs(runtime_home, exist_ok=True)
env.define("HOME", runtime_home)
env.define("XDG_RUNTIME_DIR", runtime_home)
env.define("XDG_STATE_HOME", os.path.join(runtime_home, "state"))
env.define("XDG_CONFIG_HOME", os.path.join(runtime_home, "config"))
env.define("XDG_DATA_HOME", os.path.join(runtime_home, "data"))
env.define("XDG_CACHE_HOME", os.path.join(runtime_home, "cache"))
```

并删除已产生的 `.local/`。

## 验证

修复后重跑 `conan create`（含 `conan-verify` 的 G2 干净构建）：
归档 `test_package/` 下不再出现 `.local/`，4 用例 / 5 断言仍全通过。

## 适用范围

任何在 test_package 中真实启动 Qt/KF GUI 程序的配方——尤其是把 HOME/XDG_* 指到
`self.build_folder` 的写法。判定口径：`git check-ignore -v <归档内新出现的文件>`，
未被 ignore 的一律不能留在归档树里。
