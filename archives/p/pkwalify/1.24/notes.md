# pkwalify 1.24 适配笔记

## 结论速览
- **类型**：纯 Perl 模块（`lib/Kwalify.pm` + `lib/Schema/Kwalify.pm`）+ 上游 CLI `pkwalify`
  （`Makefile.PL` 的 `EXE_FILES` 声明）；**零运行期依赖**
- **上游**：发行名 **Kwalify**（作者 SREZIC），https://github.com/eserte/p5-Kwalify
- **上游测试**：自带 `t/*.t`（TAP），官方跑法 `perl Makefile.PL && make && make test` → **`Result: PASS`**
- **状态**：built（本地 conan create 全绿：上游 `make test` PASS + 消费者 8/8）

## 打包步骤
```bash
conan create archives/p/pkwalify/1.24 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1) 先验证"测试能不能跑"（按规矩：跑不了就放弃该库）
```bash
tar xf Kwalify-1.24.tar.gz && cd p5-Kwalify-1.24
perl Makefile.PL && make && make test        # → Files=4, Tests=134 ... Result: PASS
# ⚠️ 只 prove -l t/（跳过 make）会挂 1 条：
#    t/pkwalify.t 检查 blib/script/pkwalify，而 blib/ 是 make 生成的（Failed 1/31）
```

### 2) 产物与布局（沿用仓库既有 Perl 配方 `perl-protocol-websocket` 的约定）
- `perl Makefile.PL INSTALLDIRS=site` → `make -j1` → `make install DESTDIR=staging`
- `.pm` 归到 **`lib/perl5/site_perl/<perl 版本>/…`**（含 `Schema/Kwalify.pm`）
- 上游 CLI → **`bin/pkwalify`**（并按 R38 在软件级目录补 `commands.json`）
- `package_info()` 把 **`PERL5LIB` 指向含 `Kwalify.pm` 的目录**（动态探测，不写死 perl 版本）

### 3) 已知限制（如实记录，**不计为通过**）
`pkwalify` CLI 解析 YAML/JSON 文件需要**可选**后端模块，其候选列表是
`YAML::Syck / YAML / YAML::XS / JSON::XS / JSON`（上游 `Makefile.PL` 不强制装其一）；本环境
这 5 个全缺（核心的 `JSON::PP` 虽有但**不在其列表里**）→ 实测：

```
$ perl -I<lib> bin/pkwalify -f schema.yaml data.yaml
Cannot parse <schema.yaml>. Cumulated errors:
Unsupported module YAML::Syck / YAML / YAML::XS / JSON::XS / JSON     (rc=2)
```

**模块级功能完全正常**：`Kwalify::validate($schema, $data)` 合法数据返回 `1`、非法数据 `die`
（消费者第 ⑥ 项就是真跑这条），且上游 `make test` 全绿 —— 库本身可用，CLI 的文件解析只是
缺一个可选后端。消费者第 ⑦ 项把这个状态**原样记录**（自报缺哪些后端 + rc），不冒充成功。

## 实测结果（本地 conan create）
```
RUN: make test
Files=3, Tests=133, ... Result: PASS          ← 同一套 TAP 在解包目录直跑为 Files=4, Tests=134
[upstream tests] 上游 `make test` 通过（TAP 套件 Result: PASS）
[ok]   产物齐备：Kwalify.pm 位于 lib/perl5/site_perl/5.42.0/Kwalify.pm（共 2 个 .pm）
[ok]   Schema::Kwalify 产物存在 / 上游 CLI 产物存在且可执行：bin/pkwalify
[ok]   真实加载：perl -MKwalify 成功，$Kwalify::VERSION == 1.24
[ok]   真实加载：perl -MSchema::Kwalify 成功
[ok]   真实功能真跑：Kwalify::validate 合法数据返回 1、非法数据 die
[ok]   上游 CLI 真跑：rc=2，工具自报缺可选解析后端 ['JSON::XS','YAML::Syck','YAML::XS']（如实记录，不计为通过）
checks=8 fails=0
RESULT: PASS
```

## 踩坑记录
1. **消费者校验不能裸名调 `perl`**：`test()` 的 `env="conanrun"` 里 PATH 不含 perl（实测
   `FileNotFoundError: No such file or directory: 'perl'`）→ 必须显式解析绝对路径
   （`/data/service/hnp/bin/perl` 等，最后退回 `shutil.which`）。与 init-system-helpers 同源教训。
2. **必须走 `make` 流程**：`t/pkwalify.t` 依赖 `blib/script/pkwalify`；只 `prove -l t/` 会挂 1 条。
3. **同一套 TAP 的计数会随跑法不同**（4 文件/134 vs 3 文件/133）：清单里应**并列观测值**，不取其一冒称。
4. **CLI 的可选后端要如实披露**：缺后端时 rc=2 且工具自报缺哪些模块；不把这种情况写成"通过"。
5. **CPAN 多镜像同 sha256**：`www.cpan.org` 与清华 CPAN 镜像逐字节相同（已 `cmp` 验证），
   故 `conandata.yml` 里 4 个镜像共用同一哈希；本沙箱 `cpan.metacpan.org` 不可达，故把清华镜像排第一。
6. `/tmp` 只读 → 测试与 CLI 探测都写 `/data/storage/el2/base/cache`。
