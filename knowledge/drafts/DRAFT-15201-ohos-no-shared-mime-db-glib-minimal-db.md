# DRAFT-15201: OHOS 无 shared-mime-info MIME 数据库（glib vendored libxdgmime 最小库构建）

> 状态: **草稿**（待审核 promote） | severity: `P1` | category: `platform` | 更新: 2026-10-16
> 对应 kv: `knowledge/drafts/DRAFT-15201-ohos-no-shared-mime-db-glib-minimal-db.kv`

---

**匹配关键词**: shared-mime-info, g_content_type_guess, application/octet-stream, XDG_DATA_HOME, MIME-Magic, globs, libxdgmime, subclasses

## 错误特征 (error_signature)

```text
g_content_type_guess.*octet-stream
_get_mime_type.*returned 'application/octet-stream'
MIME type.*not found
```

## 错误摘录 (error_excerpt)

```text
# _get_mime_type_for_name for 'file:///.../tmp/.C2VQX3' returned 'application/octet-stream'
# _get_mime_type_with_data for 'file:///.../tmp/.C2VQX3' returned NULL, ignoring
```

## 根因 (root_cause)

OHOS 无 `/usr/share/mime`（shared-mime-info）数据库。glib 2.84 的 vendored libxdgmime
（`gio/xdgmime/`，源码随 glib tarball 分发）只读 MIME 目录下 4 种文件格式：

| 文件 | 格式 | 作用 |
|------|------|------|
| `globs` | v1 文本，每行 `mimetype:glob [glob ...]`，`#` 注释 | 扩展名 → MIME（`g_content_type_guess(name)`） |
| `magic` | **v1 二进制**：12 字节文件头 `MIME-Magic\0\n` + 节头 `[priority:mime]` + 行 `>offset=<2字节大端长度><原始字节值>[&掩码][~字长][+扫描范围]` | 内容嗅探（`g_content_type_guess(data)`） |
| `subclasses` | v1 文本，每行 `派生类型 父类型` | `g_content_type_is_a` / 子类层级判定 |
| `aliases` | v1 文本，每行 `别名 规范名` | MIME 别名解析 |

无库时：扩展名探测 0 命中、内容嗅探 UNKNOWN → 退化 `application/octet-stream`
（文本内容则 `text/plain`）。依赖 content-type 路由的库（totem-plparser 的
m3u/xspf/rss/SMIL/php-dual 分派等）全部失败。

**magic 文件两个易错点**（实测踩坑）：
1. **缺 12 字节文件头 `MIME-Magic\x00\n` → 整文件被静默拒绝**。
   `_xdg_mime_magic_read_from_file`（xdgmimemagic.c:800）先 `fread(header,1,12)` 比对
   `memcmp("MIME-Magic\0\n", ...)`，不匹配直接 return，match_list 为空
   （`_xdg_mime_magic_get_buffer_extents()` 返回 0 可验证）。
2. **每行必须带 `+N`（N≥1）扫描范围**。`compare_to_data` 的循环是
   `for (i = offset; i < offset + range_length; i++)`——range_length=0 时循环体一次
   都不执行，恒不匹配。

## 建议方案 (rec_approach)

1. 构建最小 MIME 库目录（按被测库实际用到的类型裁剪），例如 totem-plparser：
   ```
   $XDG_DATA_HOME/mime/globs        # m3u/m3u8/xspf/smi/smIL/pls/wpl/xml/... 共 50 行
   $XDG_DATA_HOME/mime/magic        # MIME-Magic\0\n + [100:application/xspf+xml] + >0=\x00\x11<playlist version+600
   $XDG_DATA_HOME/mime/subclasses   # application/x-php text/plain
   ```
2. 注入方式二选一：
   - **XDG_DATA_HOME 环境变量**（推荐，公开接口）：`xdg_init_dirs` 自动读
     `$XDG_DATA_HOME/mime/`；
   - `g_content_type_set_mime_dirs()`（gio 私有 API）：库初始化前调用，
     目录须含 globs。
3. magic 规则覆盖被测库的**内容嗅探盲区**：totem 的 `is_xml_feed` 只识别
   rss/atom/opml；XSPF 必须靠 magic 命中。注意 totem 自有 XSPF 保存器写的根元素是
   `<playlist version="1" xmlns="http://xspf.org/ns/0/">`（非标准 `<xspf>`），
   规则须按实际内容写（`<playlist version` + 扫描范围）。
4. `subclasses` 为 dual-type 的 IGNORED 判定提供层级（totem
   `totem_pl_parser.c:2190`：dual 类型 + with_data 后仍是 `is_a(text/plain)` 且非
   `is_a(application/xml)` → 返回 IGNORED，如 audio.php 用例）。

## 实测证据 (source)

- totem-pl 3.26.7（glib 2.84.0.2 / ohpcd 制品仓包），OHOS 真机 aarch64，2026-10-16
- 无库基线：72 用例 13 失败（全部 MIME 路由相关）
- 最小库（globs+magic+subclasses）+ XDG_DATA_HOME：上述 9 个 MIME 相关用例全部转绿
  （xspf_title / not_really_php / not_really_php_but_html_instead / smi_starttime /
  videosite / no_url_podcast / rss_id / rss_link / youtube_starttime）
- magic 文件头缺失 → vendored 解析器实测 max_extent=0、lookup=NULL（magictest 复现）
- 补文件头后 lookup 命中 `application/xspf+xml (prio=100)`
- 配方实现见 `archives/t/totem-pl/3.26.7/`（消费者用例内嵌最小 globs + set_mime_dirs）
