# DRAFT — toybox patch 与 GNU patch 的行为差异：上游"参考输出 + .diff 夹具"式测试的可移植修法

**来源**：libdisplay-info 0.4.0 适配（`archives/l/libdisplay-info/0.4.0`）
**日期**：2026-10-16
**状态**：DRAFT（待复审）

## 现象

上游 `test/edid-decode-check.sh`（每个夹具都跑）：

```sh
cp "$ref" "$workdir/ref"
"$DI_EDID_DECODE" <"$edid" >"$workdir/di" || [ $? = 254 ]
if [ -f "$diff" ]; then
	patch "$workdir/ref" "$diff"      # ← GNU patch 的"目标文件位置参数"
fi
diff -u "$workdir/ref" "$workdir/di"
```

设备上 `meson test -C build` 结果：34 个 `print-*` 通过，32 个带 `.diff` 的 `decode-*`
报 `exit status 1`（另 2 个无 `.diff` 的夹具通过）。比对差集恰好是每个 `.diff` 文件的内容，
看上去像"解码输出不对"。

## 根因（两处不兼容，不是一处）

1. **调用形式**：本平台 `/usr/bin/patch` 是 toybox 实现——
   `usage: patch [-d DIR] [-i file] [-p depth] [-Rlsu] [--dry-run]`，**没有"目标文件位置参数"**。
   传 `patch <目标文件> <diff>` 时它按自己的语义解析参数，找不到 hunk 便返回 0 且不修改文件
   （不报错、无 `.rej`，`set -eu` 察觉不到）。
2. **目标名取值相反**：即使改用 `-i`，两家对"`--- old` / `+++ new` 都存在时该改哪个"的选择相反——
   toybox 打 `+++`（实测输出 `patching di`），GNU patch 打 `---`（`ref`）。
   所以只换成 `-i` 仍会让 `.diff` 套到错误文件上（实测：`ref` 未被修改）。

最小判定：

```sh
printf 'a\nb\nc\n' > t.txt
printf -- '--- t.txt\n+++ t.txt\n@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n' > t.diff
/usr/bin/patch t.txt t.diff; echo "rc=$?"; cat t.txt   # rc=0，t.txt 未变 → 位置参数形式不生效
```

## 修法（可移植、语义不变）

把 diff 头部路径改写为目标文件本身，再用两家都认的 `-p0 -i` 形式：

```sh
if [ -f "$diff" ]; then
	sed -e '1s|^--- .*|--- ref|' -e '2s|^+++ .*|+++ ref|' "$diff" >"$workdir/ref.diff"
	(cd "$workdir" && patch -p0 -i ref.diff >/dev/null)
fi
```

- 头部两个名字都写成 `ref` ⇒ 不论实现偏好 `---` 还是 `+++`，改的都是同一个文件；
- `sed` 用行号限定在 `1s`/`2s`（unified diff 的第 1/2 行就是 `---`/`+++` 头），
  避免误改正文里以 `--- `/`+++ ` 开头的行（本仓 31 个夹具实测无此情况，仍收紧）；
- `-p0 -i` 是 GNU patch 与 toybox patch 的公共子集；
- 只改"怎么套用夹具"，不改断言、夹具、参考输出与比较逻辑。

效果（libdisplay-info 0.4.0 实测）：`meson test` 从 **36/68 → 68/68**。

## 处置口径

1. **先分清"包的问题"还是"工具的问题"**：差集内容恰好等于 `.diff` 的内容 ⇒ 夹具没套上（工具）；
   否则才是真差异。可用 `patch_ng` 独立复算：
   `patch_ng.fromfile(diff).apply(root=workdir)`（conan 打补丁用的同一实现）。
2. **修工具而不是放宽断言**：优先改调用方式使其可移植；不要删夹具、不要改 `.ref`、
   不要把失败用例从 meson 清单里摘掉。
3. 这类改动属于"修改了上游测试资产"，按 R51/PR 模板必须申报：文件、原因、内容逐条写清，
   并说明断言与阈值未变。

## 参考

- 补丁：`archives/l/libdisplay-info/0.4.0/patches/0002-meson-test-harness-portable.patch`
- 证据：`archives/l/libdisplay-info/0.4.0/reports/test-report.md` 第 4 节
