# DRAFT-10718：上游测试报「插件目录不存在/配置解析失败」时，先接可选依赖再谈适配缺陷

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-14
> Source: slurm-wlm 25.11.4 HarmonyOS PC 适配（`archives/s/slurm-wlm/25.11.4`）
> 对应：`knowledge/drafts/DRAFT-10718-slurm-wlm-optional-dep-plugin-dir-upstream-tests.kv`
> 相关：DRAFT-10251（可选测试框架缺失 → 测试套件没跑，TOTAL: 0）、
> DRAFT-10718-slurm-wlm-libcheck-default-timeout-nameservice-test（同套用例的另一类失败面）

## 现象

slurm 25.11.4 的上游单元测试（`testsuite/slurm_unit`，41 条）在设备上跑，两条"与 yaml 无关"的
用例稳定失败：

```text
$ ./serializer-test        # 位于 testsuite/slurm_unit/common
serializer-test: error: PluginDir: ../../../src/plugins/serializer/yaml/.libs/: No such file or directory
serializer-test: error: Bad value "../../../src/plugins/serializer/json/.libs:../../../src/plugins/serializer/yaml/.libs/" for PluginDir
serializer-test: fatal: Unable to process configuration file
FAIL serializer-test (exit status: 1)

$ ./topology-test          # 位于 testsuite/slurm_unit/topology，配置来自同目录 slurm.conf
topo-test: error: PluginDir: ../../../src/plugins/serializer/yaml/.libs/: No such file or directory
topo-test: error: Bad value "../../../src/plugins/serializer/{select,topology,auth,...}/...:.libs/..." for PluginDir
topo-test: fatal: Unable to process configuration file
FAIL topology-test (exit status: 1)
```

报错面是 **目录不存在** 与 **配置解析致命退出**，不是断言失败、也不是链接错误。

## 根因

1. 这两条用例都要先加载一份测试配置（`slurm.conf` 片段），而 slurm 的配置解析器会**逐个 stat**
   `PluginDir` 里列出的目录，任一个不存在就 `fatal: Unable to process configuration file`；
2. 上游测试夹具里的 `PluginDir` 是"全量插件"集合，其中 `serializer/yaml/.libs` 只有在
   configure 探测到 libyaml 时才产出（`--with-yaml=PATH` → `WITH_YAML`/`HAVE_YAML`）；
3. HarmonyOS 上原本没有 libyaml → 该目录从未生成 → 这两条用例必然失败。

判据链（一条命令就能闭环）：

```sh
$ ls -d <build>/src/plugins/serializer/*/.libs
<build>/src/plugins/serializer/json/.libs
<build>/src/plugins/serializer/url-encoded/.libs      # ← 只缺 yaml

$ grep -n "checking for libyaml installation" <build>/config.log
configure:23126: checking for libyaml installation...        # 未接依赖时为空

$ grep -n "define HAVE_YAML" <build>/config.h                # → 无
```

## 处置（接上"已发布"的可选依赖）

制品仓里已有 libyaml 的 portable 发行版（`portable-libyaml/0.2.5`，提供 `include/yaml.h`
与 `lib/libyaml.a`），按 R36 的口径先确认它能被下载/安装，再在配方里补上：

```python
    def requirements(self):
        ...
        self.requires("portable-libyaml/0.2.5")   # serializer/yaml 插件

    def generate(self):
        for dep, flag in (("munge", "--with-munge"),
                          ("hwloc", "--with-hwloc"),
                          ("json-c", "--with-json"),
                          ("http-parser", "--with-http-parser"),
                          ("portable-libyaml", "--with-yaml")):
            folder = self.dependencies[dep].package_folder
            tc.configure_args.append("%s=%s" % (flag, folder))
```

重新 configure 后：

```sh
$ grep -n "checking for libyaml installation" <build>/config.log
configure: checking for libyaml installation... /…/porta9f539159acafe/p     # 已接上
$ grep -n "define HAVE_YAML" <build>/config.h
345:#define HAVE_YAML 1
$ ls -d <build>/src/plugins/serializer/yaml/.libs                          # 目录产出 → 用例可过
```

`HAVE_YAML` 在 slurm 源码里只作用于该插件（`src/plugins/serializer/yaml/Makefile.am` 里的
`if WITH_YAML`），不会牵动别的组件，属于低风险可选依赖补齐。

## 为什么不"改测试夹具"

把夹具里那个 yaml 目录删掉、或改 `slurm.conf` 片段，都能让这两条用例变绿 —— 但那等于**篡改上游用例**：

- 真实产出（插件集合）与用例期望仍然不一致，只是被掩盖了；
- R51「如实回填」要求申报的通过率与实际一致，改夹具会让申报失去依据；
- 上游之所以把全量 `PluginDir` 写进夹具，正是为了覆盖"所有列出的插件目录都必须存在"这一行为。

同理，若该依赖在制品仓**没有**发布，也不要在配方里私编一个（R36）；正确做法是在
`test_package/MANIFEST.yml` 里按 `docs/TEST_QUALITY_SPEC.md §3.3` 声明豁免，并如实计入 FAIL。

## 通用化建议

1. 上游用例失败先看**失败面**：断言失败 / 框架报错 / 目录或文件不存在 / 链接错误 —— 四类的处置完全不同。
2. 报错面是"目录/文件不存在"时，先列"实际产出了什么"（`ls` 产物的目录树），再回到上游
   `configure`/`configure.ac` 找决定该产物的 `--with-X` 开关。
3. 找到开关后**先在制品仓确认依赖是否已发布**（`conan download <ref> -r=<remote>`），已发布就直接接、
   没发布就写豁免；两条路都不要碰上游测试夹具。
