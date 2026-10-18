# DRAFT-HMDFS-SIGNED-ELF-BYTE-REWRITE

HMDFS 已签名 ELF 内容改写 → 加载期 Permission denied（R1 实证）

## 一句话

HMDFS 在装载时校验 ELF `.codesign` 签名：对 conan 制品仓发布件（全部带 CI
签名）做**任何内容改写**（patchelf/python 字节替换/tar 重打包）都会使签名
失效，`dlopen` 报 `Permission denied`；**逐字节原样复制**（rm+cp、conan
remove+download、tar 解包）则完全正常。创建方式与 mode 位都不是判据
（早期假说已被对照实验证伪）。

## 决定性实验（kturtle 26.04.0 适配期，本机 HMDFS）

| 实验 | 操作 | 结果 |
|---|---|---|
| T1 | 新鲜签名件逐字节复制（os.open 创建，mode 770） | 加载推进到「缺 libQt6Core.so.6」——非拒载，签名完好 |
| T2 | 同一文件仅翻转 0x200 一个字节 | `Error loading shared library ...: Permission denied` |
| S1-S3 | 无签名自编译 .so 以 tar(770)/python 写+chmod/cp 三种方式落盘 | 三行全 PASS——证伪「创建方式/mode 位」假说 |
| R3 | 无签名件原地覆盖 `cp f f` | EPERM（HMDFS 禁原地覆盖，写侧规律独立成立） |

## 与相邻知识的边界

- `knowledge/drafts/signed-elf-overwrite-eperm.kv`：写侧（open(wb) 截断
  已签文件被拒 EPERM）。本条：读侧/装载侧（写成功了但签名坏了，dlopen 才炸）。
- `harmonyos-specifics.md §chmod`：chmod 三规律（other 恒 0/group 恒 6/
  owner 保底 rw）——「事后 chmod 补 x 位」救不了任何场景，是早期假说的成因之一。
- E046：chmod 不生效的既有正式条目。

## 处置（唯一出路 = 恢复原始字节）

```sh
conan remove "<pkg>/<ver>" -c && conan download "<pkg>/<ver>" -r=<remote>
```

需要 NEEDED 级修复时用**不改字节**的方案：
- 相对 NEEDED（`../../bin/libX.so`，按 CWD 解析）→ test_package cwdroot
  模式（参考 archives/k/kturtle/26.04.0/test_package/conanfile.py）；
- 绝对 NEEDED 断链（发布件烙死构建 worker 布局路径）→ 从可信源 rm+cp
  逐字节填充（见同目录 repair-hmdfs-cache.sh fill）。

配套工具（知识库拓展四件套）：
`archives/k/kturtle/26.04.0/knowledge-extension/`
（detect-hmdfs-exec-integrity.sh / repair-hmdfs-cache.sh / README.md /
reproduce.sh——reproduce 阶段 2 即本条 T1/T2 的可复现版本）。
