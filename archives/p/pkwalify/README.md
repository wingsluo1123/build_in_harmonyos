# pkwalify

- **上游**：https://github.com/eserte/p5-Kwalify （CPAN 发行名 **Kwalify**，作者 Slaven Rezic）
- **版本**：1.24
- **形态**：纯 Perl 模块 —— Kwalify 模式校验器（`Kwalify.pm` + `Schema/Kwalify.pm`）
  + 上游 CLI `pkwalify`
- **许可证**：perl_5（"same terms as Perl itself"）
- **依赖**：**零运行期依赖**（`Makefile.PL` 的 `PREREQ_PM` 仅 `warnings::compat`，且只在 perl < 5.006 时）

## 归档内容

```
pkwalify/
  commands.json            软件级命令声明（R38：本包产出上游 CLI pkwalify）
  1.24/
    conandata.yml          CPAN 源（4 个镜像同 sha256）与哈希
    conanfile.py           配方（source → build(Makefile.PL+make+make test) → package(.pm→lib/perl5, CLI→bin)）
    manifest.yaml          版本级 manifest（dependencies / upstream_tests / knowledge_gained）
    notes.md               适配要点（perl 绝对路径、必须走 make、CLI 可选后端限制等 6 条）
    test_package/          消费者校验（8 项，全部离线）
```

## 产物

- `lib/perl5/site_perl/<perl 版本>/Kwalify.pm`、`…/Schema/Kwalify.pm`（沿用仓库既有 Perl 配方布局）
- **`bin/pkwalify`**：上游 `Makefile.PL` 的 `EXE_FILES` 声明的命令行工具

## 上游测试

自带 TAP 套件 `t/`（`Kwalify.t` / `compat.t` / `pkwalify.t` / `required-no.t` + `t/testdata`），
官方跑法即上游 README 的 `perl Makefile.PL && make && make test` → 实测 **`Result: PASS`**
（本次 conan 构建 `Files=3, Tests=133`；解包目录直跑 `Files=4, Tests=134`——两处观测都 PASS，
计数差异如实并列）。
⚠️ 只 `prove -l t/`（跳过 `make`）会挂 1 条：`t/pkwalify.t` 检查 `blib/script/pkwalify`，
而 `blib/` 由 `make` 生成（并非测试坏了）。

## 消费者校验（8 项，全部离线）

`test_package/check_pkwalify.py`：产物齐备 / `Schema::Kwalify` 产物 / 上游 CLI 产物可执行 /
`perl -MKwalify` 且 `$Kwalify::VERSION == 1.24` / `perl -MSchema::Kwalify` /
**真实功能真跑**（`Kwalify::validate` 合法返回 1、非法 `die`）/ **上游 CLI 真跑并如实记录**
（本环境缺**可选** YAML/JSON 后端 → rc=2 且工具自报 `Unsupported module …`，**不计为通过**）/
证据。实测 `checks=8 fails=0` / `RESULT: PASS`。

> **已知限制**：CLI 的文件解析依赖可选后端（`YAML::Syck`/`YAML`/`YAML::XS`/`JSON::XS`/`JSON`，
> 上游不强制其任一）；本环境这 5 个全缺，故 CLI 无法解析文件（库的 API 与上游测试均不受影响）。
