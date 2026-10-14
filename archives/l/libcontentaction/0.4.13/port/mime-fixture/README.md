# 测试用 shared-mime-info 数据库（夹具）

上游 `tests/test-info.cpp` / `tests/test-action.cpp` 依赖系统的 shared-mime-info：
`ContentInfo::typeDescription()` 期望 "Plain text document" / "PNG image"，
`ContentInfo::forFile()/forData()` 期望按内容探测出 `image/png`。

OHOS 与 Conan 运行环境都没有 shared-mime-info，因此随测试床提供最小数据库。

## 组成

| 路径 | 说明 |
|------|------|
| `packages/lca-test-mime.xml` | **唯一随仓库提交的文件**：XML 源（可读、可评审）。只含上游用例需要的 4 个类型（text/plain、image/png、audio/mpeg、application/pdf），comment 文案与上游期望一致，glob/magic 取自 freedesktop.org.xml 同名条目 |

## 为什么生成产物不提交

GLib 的 GIO（实测 2.84）只读取 `update-mime-database` **生成后**的数据库
（`mime.cache`、`mime/magic`、`mime/globs2` …），裸 `mime/packages/*.xml` 不生效
（实测：只有 XML 时 `ContentInfo::forFile()` 返回 `application/octet-stream`，
描述退化为 `"text/plain type"`；且缺少 `<media>/<subtype>.xml` 时描述同样退化）。

但这些生成产物**本质是二进制**（含 NUL 字节，实测 `mime.cache` 584 字节，
其中 NUL 占 390 字节；`magic`、`treemagic` 同）：

- GitCode 导出的 PR diff 会把它渲染成**缺少 `GIT binary patch` 段**的
  `binary patch`，于是 CI 的 `checkout-pr` 步骤 `git apply` 直接失败：
  `error: missing binary patch data for '.../mime.cache'`；
- 因此**不随仓库提交任何二进制文件**，改为构建期用宿主
  `update-mime-database` 从 XML 源生成。

## 落点

- 配方测试床：`port/CMakeLists.txt` 的 `lca-mime-fixture` 目标在构建期调用
  `update-mime-database`，生成到 `<build>/testbed/home/tests-home/mime/`，
  即上游 `lca-cita-test` 设置的 `XDG_DATA_HOME=${HOME}/tests-home/` 之下 ——
  优先级高于 `XDG_DATA_DIRS` 中的系统数据库，保证用例结果不随构建机是否安装
  shared-mime-info 而变。
- 消费者测试包：`test_package/conanfile.py` 的 `_mime_db()` 在 `test()` 前用同样方式
  生成，并把该目录作为 `argv[2]` 传给消费者。

两处都依赖构建机上的 `update-mime-database`（shared-mime-info 包）。

## 手工生成（复现用）

```sh
mkdir -p /tmp/lca-mime/packages
cp port/mime-fixture/packages/lca-test-mime.xml /tmp/lca-mime/packages/
update-mime-database /tmp/lca-mime
# 生成结果用于本地排查，不要提交
```
