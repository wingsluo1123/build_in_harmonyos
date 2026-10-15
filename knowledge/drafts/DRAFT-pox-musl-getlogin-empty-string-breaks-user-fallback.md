# pox：musl 上 `os.getlogin()` 返回空串，破坏用户名回退

> 配套结构化条目：`DRAFT-pox-musl-getlogin-empty-string-breaks-user-fallback.kv`

## 现象

`pox/0.3.7`（uqfoundation 的纯 Python 工具库）上游 pytest 套件在设备上失败：

```
assert homedir().rstrip(sep()).endswith(username())     # test_shutils
IndexError: list index out of range                      # walk(...)[0]
```

## 根因 1：`os.getlogin()` 在 musl 上返回 `''` 而不抛异常

pox 的 `shutils.username()`：

```python
try:
    return os.getlogin()
except:
    uname = os.path.expandvars('$USER')
    if '$' in uname: uname = env('USERNAME', all=False)
    return uname
```

在 glibc 上 `getlogin()` 失败会**抛异常**，回退生效。在 **musl/OHOS 上它返回空串**，
`except` 永不触发 → `username()` 返回 `''` → 所有依赖它的断言落空。

修法：把「空值」也纳入回退条件（补丁 0002）：

```python
try:
    uname = os.getlogin()
except Exception:
    uname = None
# musl/OHOS: getlogin() returns an empty string instead of raising
if not uname:
    uname = os.path.expandvars('$USER')
    if '$' in uname or not uname:
        uname = env('USERNAME', all=False)
return uname
```

## 根因 2：`rootdir()` 不可列举

```python
folders = walk(rootdir(), '*', recurse=False, folders=True, files=False)
assert len(folders) > 0
```

本平台 `rootdir()` = `/`，而沙箱**拒绝列举根目录**：

```
ls /            → Permission denied
os.listdir('/') → [Errno 13] Permission denied
```

断言不可能成立。补丁 0001 改为 `walk(os.getcwd())`（可列），
**断言语义与 `walk(folders=True)` 的验证点不变**。

## 根因 3：用受控 HOME 运行上游套件

此外还有两个环境因素：

- 真实 HOME 是 `/storage/Users/currentUser`，而父目录 `/storage/Users`
  **不可列举**（`Operation not permitted`），`walk(homedir()+'/..', username())`
  取不到用户项；
- 设备 `$USER` 是纯数字 uid（`100`），与 HOME 的 basename 不一致；
- `findpackage()` 会递归整个真实 HOME，**导致测试挂起**。

解法：在 `build()` 里用一个**受控可写 HOME**，其 basename 即用户名：

```python
user = "ohos"
home = os.path.join(self.build_folder, "test-home", user)
env = Environment()
env.define("HOME", home); env.define("USER", user)
env.define("LOGNAME", user); env.define("TMPDIR", tmp)
with env.vars(self).apply():
    self.run(python3 + " -m pytest pox/tests -q", cwd=self.source_folder)
```

实测结果：`2 passed in 0.98s`。

## 消费者验证（test_package）

在 `env="conanrun"` 下（PYTHONPATH 指向包产物）：

| # | 断言 | 证明 |
|---|---|---|
| 1 | `POX_PACKAGE_ROOT` 在 `pox.__file__` 父链上 + 版本 0.3.7 | 导入来自本包 |
| 2 | `expandvars("$POX_CONSUMER_PROBE") == "harmony"`、`env(NAME, all=False)` | 环境读取真实生效 |
| 3 | `mkdir` 建目录、`walk(folders=True)` 回查、`find` 命中临时文件 | 文件系统真实工作 |
| 4 | `pattern` / `minpath` 文档化行为 | 纯逻辑正确 |

输出 `POX-CONSUMER-OK`。

## 易混淆提示

存在**两个不同的 pox**：本包是 PyPI 上 uqfoundation 的 `pox`
（filesystem/automation utilities）；Noxrepo/pox 是 Python SDN/OpenFlow
控制器。版本号与依赖完全不同，勿混用。
