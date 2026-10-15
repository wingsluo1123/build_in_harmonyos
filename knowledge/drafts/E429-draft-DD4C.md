# E429 — Perl 模块适配：test() 环境无 perl 需绝对路径；上游测试必须走 make（blib 依赖），CLI 可选后端要如实披露

## 错误特征
1. 消费者校验（conan `test()`）里起 perl 进程：
   ```
   FileNotFoundError: [Errno 2] No such file or directory: 'perl'
   ERROR: pkwalify/1.24 (test package): Error in test() method
   ```
2. 用 `prove -l t/` 直接跑 TAP 会挂 1 条：
   ```
   Failed test '.../blib/script/pkwalify compiles OK'
   t/pkwalify.t ... Failed 1/31 subtests
   ```
3. CLI 解析文件时报：
   ```
   Cannot parse <schema.yaml>. Cumulated errors:
   Unsupported module YAML::Syck / YAML / YAML::XS / JSON::XS / JSON      (rc=2)
   ```

## 触发条件
- 构建系统: Perl（ExtUtils::MakeMaker / `Makefile.PL`）
- 阶段: testing（`build()` 内 `make test` 与 `test()` 内的消费者校验）

## 根因分析
1. **`test()` 的 `conanrun` 环境 PATH 不含 perl**：conan 的 `test()` 用聚合环境（`env="conanrun"`），
   其中没有 HNP 的 perl 目录。`subprocess.run(["perl", ...])` 走 PATH 解析 → 找不到。
2. **Perl 的 `make test` 依赖 `blib/`**：`blib/` 由 `make` 生成（把 `lib/` 的 .pm 与 `EXE_FILES`
   的脚本拷进去）。上游测试常直接检验 `blib/script/<tool>` 能否运行 → 跳过 `make` 只 `prove -l`
   时该条必挂，但这是**跑法不对**，不是测试失败。
3. **CLI 的可选解析后端**：模块把 YAML/JSON 解析做成可插拔候选（`JSON::XS`/`JSON`/`YAML::Syck`/
   `YAML`/`YAML::XS`），`Makefile.PL` 不强制其一。环境若一个都没有（注意：核心模块 `JSON::PP`
   **不在候选列表**），CLI 就无法解析任何文件——而**库的 API 与 `make test` 完全正常**。

## 解决方案

### 推荐方案
1. **消费者校验里显式解析 perl 绝对路径**（不要裸名）：
   ```python
   for cand in ("/data/service/hnp/bin/perl", "/usr/bin/perl", "/bin/perl",
                "/usr/local/bin/perl"):
       if os.path.exists(cand):
           return cand
   return shutil.which("perl") or "perl"
   ```
2. **上游测试按上游 README/构建系统跑**：`perl Makefile.PL INSTALLDIRS=site && make -j1 && make test`
   （`make test` 非零即让 build 硬失败）；**不要**用 `prove -l t/` 替代。
3. **产物与布局**：`make install DESTDIR=staging` → `.pm` 归 `lib/perl5/…`；`EXE_FILES` 的脚本
   落到 `bin/<tool>`，并按 R38 在软件级目录补 `commands.json`；`PERL5LIB` 动态指向含主模块的目录。
4. **CLI 缺可选后端如实披露**：消费者校验里真跑一次并**分类记录**（有后端 → rc=0；仅缺后端 →
   rc≠0 且给出缺失模块名），**不计为通过**、也不写成失败；同时用模块级真跑（
   `Kwalify::validate` 合法返回 1 / 非法 die）证明**库本身可用**。
5. 同一套 TAP 在“解包目录直跑”与“构建内跑”的计数可能不同（实测 4 文件/134 vs 3 文件/133，均 PASS）
   → 清单里**并列观测值**，不取其一冒称。

### 禁止做法
- ❌ 消费者校验里裸名 `perl`（必然 `FileNotFoundError`）
- ❌ 用 `prove -l t/` 替代 `make test` 后把挂的 1 条当成"上游测试有缺陷"
- ❌ 把 CLI 因缺可选后端而 rc≠0 写成"通过"，或反过来把库判定为不可用

## 验证
```bash
# test() 环境里有没有 perl
which perl || echo "PATH 无 perl（需绝对路径）"
# 官方流程
perl Makefile.PL && make && make test          # → Result: PASS
# 模块级真跑（不依赖任何 YAML/JSON 后端）
perl -I<lib> -MKwalify -e 'my $r = eval { Kwalify::validate({type=>"int"}, 1) }; print $r'
# CLI（缺可选后端时如实记录）
perl -I<lib> <prefix>/bin/pkwalify -f schema.yaml data.yaml; echo rc=$?
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它适配条目：sdist 缺测试数据与依赖实证判定 / conan 依赖遮蔽 /
  test_requires 的 test 上下文 / console_scripts 入口落地 / src 布局与插件型 addopts）
