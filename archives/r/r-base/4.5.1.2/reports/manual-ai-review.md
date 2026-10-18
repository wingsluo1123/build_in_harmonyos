# PR #15348 人工 AI 检视核验记录（rule6）

> 检视背景：atomgit AI 检视因单文件过大无法完成自动检视，按 rule6 由人工对 PR 全部改动文件
> 逐文件执行 P0/P1 级别核验。本记录与 R52 审计证据一致性口径对齐：结论附被检文件 sha256。

- 分支：feat/r-base-4.5.1.2（HEAD 41bd30dbe8）
- 与 main 分叉基点：6425af5145
- 改动文件数：28（单包 archives/r/r-base/4.5.1.2 + 软件级 manifest/commands.json + build_timeouts.txt + 知识草稿 E547）
- 检视日期：2026-10-15

## 检查项与结论

| # | 检查项 | 结论 | 说明 |
|---|--------|------|------|
| 1 | 平台宏注入（PF5/R8） | PASS | patches 新增行仅 0001 含 `#if defined(__OHOS__)`（config.guess libc 探针），与已合入的 4.5.1/4.5.1.1 补丁逐字节一致（cmp 验证 IDENTICAL），存量豁免；0002-0009 无平台宏；conanfile.py 无 -D__OHOS__/replace 注入 |
| 2 | 共享前缀注入（PF6/R49） | PASS | 无 environ 读 SYS_PREFIX、无共享 /usr/local 注入；conanfile.py:514 的 "/storage/Users/currentUser/usr/local/include" 为 _reject_build_paths 的 openssl 构建信息串白名单匹配串（既有评审结论），非编译注入 |
| 3 | 源 URL 官方性（PF7/R39） | PASS | conandata.yml 仅两个 URL：cran.r-project.org（R 4.5.1 官方）与 curl.se（curl 8.15.0 官方），均为 https 官方源，无镜像黑名单域/明文 http/file:// |
| 4 | 裸 shell 环境变量（R33） | PASS | conanfile.py 无裸 ${CC}/${CFLAGS}/${CXXFLAGS}/${LDFLAGS} 依赖，编译器/标志全部来自 Conan toolchain |
| 5 | 配方内 curl/wget 下载（R39） | PASS | grep 命中均为私有 curl 构建路径/探针源文件名（curl_https_probe.c），源码获取全部经 conandata.yml 由 Conan 完成 |
| 6 | test_package 实质依赖（PF3/R34） | PASS | test_package/conanfile.py test() 含 self.run（run_test.sh 真实执行移动副本）；test_r.R + test_consumer_e2e.R 消费被测包 R/Rscript 可执行文件并调用其统计引擎/文件 IO |
| 7 | 单包原子性（PF1/W2/JC6） | PASS | archives 变更仅 archives/r/r-base/ 单包目录（4.5.1.2 + 软件级 manifest/commands.json），无第二包捎带 |
| 8 | 版本号规范（PF8/R37） | PASS | 目录 4.5.1.2 = 上游 4.5.1 + 修复后缀；recipe version 与目录一致；commands.json versions.ref 含三版本对齐 |
| 9 | 分支/路径规范（PF9/L0n） | PASS | 分支 feat/r-base-4.5.1.2 符合 pkg-version 口径；archives 变更全落单一 包/版本 目录 |
| 10 | 垃圾文件（PF2/JC） | PASS | 无压缩包/二进制/临时产物/.bak 残留入库 |
| 11 | 知识草稿完整性（W5/KC） | PASS | knowledge/drafts/E547-draft-1835.kv 与 .md 一一对应，error_signature/root_cause/rec_approach 非空 |
| 12 | MANIFEST/结构完整性（L0a-L0e） | PASS | test_package/ 存在且含 MANIFEST.yml、conanfile.py、测试源（test_r.R + test_consumer_e2e.R）、run_test.sh；包目录 manifest.yaml/notes.md/reports 齐备 |
| 13 | 测试用例规则（R51/rule12） | PASS | 上游 68 项清点如实申报（62 执行/1 OOM/5 技术原因）；鸿蒙特有测试 10 项中含端到端消费者用例 test_consumer_e2e.R（CSV→独立 Rscript lm 消费者→RDS 往返→父进程校验，跨两真实 R 进程含文件 IO），非纯断言 |

## 结论

**P0 = 0，P1 = 0**（PASS 13/13）。P2/P3 层面无新增发现（既有 P2/P3 已在 2026-10-14 评审修复提交 73db56562d 处理）。

## 被检文件 sha256（证据锚定，HEAD 41bd30dbe8 终态）

```
a3d7df7e93bf284d151fb2470bea26f6bcc37c111cb1e89c7d165fd4723bae4f  archives/r/r-base/4.5.1.2/conandata.yml
9f7499f7c5754c9c2634f12ab5fdda4e14c6792a82cf6d70adecbcf365aec770  archives/r/r-base/4.5.1.2/conanfile.py
f5fa8fdc5cf8812962091a07410359a7620d00a9109fe26c3fc4cff0d9b8f4da  archives/r/r-base/4.5.1.2/curl_https_probe.c
a714926f2b0170153aee59b65419e2ee2197ff3b0593ff2c0e69d4b9b392daca  archives/r/r-base/4.5.1.2/manifest.yaml
d0788eb3a7eb33289b23f63db6692df1932cdb23898fa682df7b1269ac359b4f  archives/r/r-base/4.5.1.2/notes.md
2c9fd0d40cb654aa9178d65a4c15387ee9602bbee0b8da602ea6b7b8cce2c615  archives/r/r-base/4.5.1.2/patches/0001-recognize-harmonyos.patch
ee564bb838c8ea677f790c78e9e3f825fa7b61c7ab1bd4b6bd91544fd93089da  archives/r/r-base/4.5.1.2/patches/0002-clang-c23-alignof.patch
e588b2dd48b2052298bce4bcf0b8d676103418d4e235dede8abf2cf99df66aa4  archives/r/r-base/4.5.1.2/patches/0003-authoritative-timezone-param.patch
718ac2fed5a0003bfcedd52d4e84a156c59a291a9e6f0e2dd50288b81562abf3  archives/r/r-base/4.5.1.2/patches/0004-readable-pipe-target.patch
1126482a8f2245d583a205d2a75c0fe6c02f50fd328b975ed20978ad37de728d  archives/r/r-base/4.5.1.2/patches/0005-portable-subnormal-pretty-oracle.patch
380a77120a58f6b8faeca826df7125893eb6b96eef4e4b046f61348904ae9b0c  archives/r/r-base/4.5.1.2/patches/0006-relocatable-r-launcher.patch
9e918ff855f39978d2732b104ab1b48686d9ba8d643ce510f518a1b2317ce863  archives/r/r-base/4.5.1.2/patches/0007-relocatable-runtime-environment.patch
2323ed597df2ead082d06f147b00065d2eaa0f972e3f9d20737d23abdec62c5e  archives/r/r-base/4.5.1.2/patches/0008-rprof-memory-profiling-cpu-fallback.patch
2050e061c30afe5b72162510a4aefe2ff78df3e8cecc3cecd98dcc50a97a6a55  archives/r/r-base/4.5.1.2/patches/0009-sed-range-relocatable-resource-dirs.patch
e4a36b1ba9831da97fc30f9cb326ee3f46d3a96c026d47c7a08c8e80944de325  archives/r/r-base/4.5.1.2/reports/conan-verify-report.md
7b2c2f093630acd58ebb3ee4f916e04f4a185281285c7b34892705fe1225afdd  archives/r/r-base/4.5.1.2/reports/test-report.md
e68e4dbc4b7d050b93b5cf0982401c46e44321c7dc1e152a103a6327e2d6020c  archives/r/r-base/4.5.1.2/reports/w3-local-ci.log
9ded8b09455681b4daef84e6d618aa56bcbf288a26b33d7eb89b8b4f29d38c8e  archives/r/r-base/4.5.1.2/res/cacert.pem
0e173fe1568d784600393e6f5aeed9def38408b538e45e52b4a76104fc666484  archives/r/r-base/4.5.1.2/test_package/MANIFEST.yml
b3fb8647f14f5ec43d6b2a9850720f12754f4f92bba9e3f60691fb351b3799ad  archives/r/r-base/4.5.1.2/test_package/conanfile.py
e0616eb8adbd76d8d51fcfeda0b5a5f27cf593fe3eea4f67236f11c40f3bcbb3  archives/r/r-base/4.5.1.2/test_package/run_test.sh
81a778e8dda6a4e21789e1f35335cf4d467ac7759c5be9bc145933b5a4dc0b71  archives/r/r-base/4.5.1.2/test_package/test_consumer_e2e.R
be34dd1975e7683b543ab8b0037b61673ff2611d9fc3f9d91f9b6ce2e5f6b3fc  archives/r/r-base/4.5.1.2/test_package/test_r.R
ba2beb601b40d25d6249bbc4bf5f0bb7c97b76a9e603c7423b438360e21d5280  archives/r/r-base/commands.json
a0a1e7cbc255868e9e759107bc76f6a12c0b3417c3aa718f5a52b4ed2e5890f8  archives/r/r-base/manifest.yaml
0391de946cea4c3dae23e2280498b4f3c07b07341f936963f45f16ef91ccff6d  ci/config/build_timeouts.txt
6cbadc3a8b631476d3f35af168cf7b7e9959ae4428732f1149a10e47cf5f9526  knowledge/drafts/E547-draft-1835.kv
c2e649af4519c8b11bbaba2764a7dea31010f542104d2a58d7bf01ea190704a4  knowledge/drafts/E547-draft-1835.md
```
