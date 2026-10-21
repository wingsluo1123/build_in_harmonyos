# 未执行的上游测试项清单

本清单列出被配方命令排除的 Meson failing suite 中的上游测试项。这些项目未执行，也不计为 SKIP。计数按 GTest 注册用例、Python unittest 方法、每条 shell/pkg-config 检查，以及每个无 GTest 子项的 Meson 可执行命令逐项统计。

共 **1,106 个未执行测试项**：单元测试 526 项、集成测试 467 项、脚本与独立检查 113 项。

| 单个测试项 | 分类 | 未运行原因 |
|---|---|---|
| **collate: /unicode/collate/0** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **collate: /unicode/collate/1** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **collate: /unicode/collate/2** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **collate: /unicode/collate-key/0** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **collate: /unicode/collate-key/1** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **collate: /unicode/collate-key/2** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **collate: /unicode/collate-filename/0** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **collate: /unicode/collate-filename/1** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **collate: /unicode/collate-filename/2** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **convert: /conversion/no-conv** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/iconv-state** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/illegal-sequence** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/byte-order** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/unicode** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/filename-utf8** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/filename-display** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/convert-embedded-nul** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/locale-to-utf8/embedded-nul** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/locale-from-utf8/embedded-nul** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/filename-to-utf8/embedded-nul** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/filename-from-utf8/embedded-nul** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/filename-from-uri/query-is-ignored** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **convert: /conversion/filename-from-uri/fragment-is-ignored** | GLib/GObject/GModule 单元测试 | 上游标注的 musl 转换问题：/conversion/illegal-sequence（GLib #3182）；Meson 按目标标记 can_fail，因此同一 convert 二进制中的 14 个注册用例整组未运行 |
| **date: /date/basic** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/empty** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/dmy** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/julian** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/compare** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/dates** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/strftime** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/two-digit-years** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/parse** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/parse_locale_change** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/month_substring** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/month_names** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/clamp** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/order** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/copy** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/valid-dmy** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/parse/invalid** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/3** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/4** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/5** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/6** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/7** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/8** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/9** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/10** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/11** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/12** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/13** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/14** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/98** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/99** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/100** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/101** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/102** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/103** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/397** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/398** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/399** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/400** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/401** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/402** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/403** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/404** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/405** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/406** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1598** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1599** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1600** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1601** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1602** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1650** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1651** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1897** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1898** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1899** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1900** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1901** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1902** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1903** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1961** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1962** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1963** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1964** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1965** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1967** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1968** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1969** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1970** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1971** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1972** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1973** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1974** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1975** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1976** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1977** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1978** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1979** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1980** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1981** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1982** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1983** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1984** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1985** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1986** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1987** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1988** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1989** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1990** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1991** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1992** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1993** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1994** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1995** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1996** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1997** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1998** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/1999** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2000** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2001** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2002** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2003** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2004** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2005** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2006** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2007** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2008** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2009** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2010** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2011** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/2012** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/3000** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/3001** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/3002** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/3998** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/3999** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/4000** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/4001** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/4002** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **date: /date/year/4003** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **environment: /environ/listenv** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **environment: /environ/getenv** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **environment: /environ/setenv** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **environment: /environ/array** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **environment: /environ/null** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **environment: /environ/case** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gdatetime: /GDateTime/invalid** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/add_days** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/add_full** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/add_hours** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/add_minutes** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/add_months** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/add_seconds** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/add_weeks** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/add_years** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/compare** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/diff** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/equal** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/get_day_of_week** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/get_day_of_month** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/get_day_of_year** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/get_hour** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/get_microsecond** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/get_minute** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/get_month** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/get_second** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/get_utc_offset** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/get_year** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/hash** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/new_from_unix** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/new_from_unix_utc** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/new_from_timeval** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/new_from_timeval_utc** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/new_from_iso8601** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/new_full** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/now** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/test-6-days-until-end-of-the-month** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/printf** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/non_utf8_printf** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/format_unrepresentable** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/format_iso8601** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/strftime** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/modifiers** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/month_names** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/to_local** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/to_unix** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/to_timeval** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/to_utc** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/now_utc** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/dst** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/test_z** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/test-all-dates** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/unix_usec** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/new_from_unix/overflow** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/new_from_timeval/overflow** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/new_from_iso8601/2** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/format_mixed/utf8_time_non_utf8_messages** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/format_mixed/utf8_time_utf8_messages** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/format_mixed/non_utf8_time_non_utf8_messages** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/format_mixed/non_utf8_time_utf8_messages** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/strftime/error_handling** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/eras/japan** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/eras/thailand** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GDateTime/eras/parsing** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GTimeZone/find-interval** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GTimeZone/adjust-time** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GTimeZone/no-header** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GTimeZone/no-header-identifier** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GTimeZone/posix-parse** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GTimeZone/floating-point** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GTimeZone/identifier** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GTimeZone/new-offset** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GTimeZone/parse-rfc8536** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **gdatetime: /GTimeZone/caching** | GLib/GObject/GModule 单元测试 | 设备未安装上游测试要求的 locale，或 collation 行为不同 |
| **mutex: /thread/mutex1** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex2** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex3** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex4** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex5** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/errno** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/uncontended** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/contended/1** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/contended/2** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/contended/3** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/contended/4** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/contended/5** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/contended/6** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/contended/7** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/contended/8** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/contended/9** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **mutex: /thread/mutex/perf/contended/10** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **option-context: /option/basic** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/translate** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/strict-posix** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/help/options** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/help/no-options** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/help/no-help-options** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/group/captions** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/group/main** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/group/error-hook** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/group/parse** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/restoration/int** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/restoration/string** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/restoration/boolean** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/reverse-string** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/optional-int** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/repetition/int** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/repetition/string** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/repetition/filename** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/repetition/double** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/repetition/locale** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/repetition/int64** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/array/string** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/callback/string** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/callback/count** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/callback/optional1** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/callback/optional2** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/callback/optional3** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/callback/optional4** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/callback/optional5** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/callback/optional6** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/callback/optional7** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/callback/optional8** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/remaining/callback** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/remaining/callback-false** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/remaining/non-option** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/remaining/separator** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/remaining/array** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/ignore/long** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/ignore/short** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/ignore/arg** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/rest/non-option** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/rest/separator1** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/rest/separator2** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/rest/separator3** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/rest/separator4** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/arg/rest/separator5** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/context/add** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/context/empty2** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/context/empty3** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/bug/unknown-short** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/bug/lonely-dash** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/bug/triple-dash** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/bug/missing-arg** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/bug/dash-arg** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/bug/short-remaining** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/bug/double-free** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **option-context: /option/bug/double-zero** | GLib/GObject/GModule 单元测试 | 上游注明 musl 下 /option/arg/repetition/locale 应跳过但当前实现没有跳过；该项依赖 de_DE.UTF-8 的小数逗号解析，Meson 按目标标记 can_fail，因此同一二进制的 57 个注册用例整组未运行 |
| **rwlock: /thread/rwlock1** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **rwlock: /thread/rwlock2** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **rwlock: /thread/rwlock3** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **rwlock: /thread/rwlock4** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **rwlock: /thread/rwlock5** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **rwlock: /thread/rwlock6** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **rwlock: /thread/rwlock7** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **rwlock: /thread/rwlock8** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **spawn-singlethread: /gthread/spawn-single-sync** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **spawn-singlethread: /gthread/spawn-stderr-socket** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **spawn-singlethread: /gthread/spawn-single-async** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **spawn-singlethread: /gthread/spawn-single-async-with-fds** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **spawn-singlethread: /gthread/spawn-async-with-invalid-fds** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **spawn-singlethread: /gthread/spawn-script** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **spawn-singlethread: /gthread/spawn-posix-spawn** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **spawn-singlethread: /gthread/spawn/nonexistent** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **spawn-singlethread: /gthread/spawn/fd-assignment-clash** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **spawn-test: /spawn/basics** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **spawn-test: /spawn/stdio-overwrite** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/language-names** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/locale-variants** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/version** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/appname** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/prgname-thread-safety** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/tmpdir** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/basic_bits** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/bits** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/swap** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/find-program** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/find-program-for-path** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/debug** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/codeset** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/codeset2** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/console-charset** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/gettext** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/username** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/realname** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/hostname** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/xdgdirs** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/specialdir** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/os-info** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/clear-pointer** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/clear-pointer-cast** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/take-pointer** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/clear-source** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/misc-mem** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/aligned-mem** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/free-sized** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/nullify** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/atexit** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/check-setuid** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/int-limits** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/clear-list** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/clear-slist** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/specialdir/desktop** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/clear-pointer/side-effects** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/aligned-mem/alignment** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/aligned-mem/zeroed** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils: /utils/aligned-mem/free-sized** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils-isolated: /utils-isolated/tmp-dir** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils-isolated: /utils-isolated/home-dir** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils-isolated: /utils-isolated/user-cache-dir** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils-isolated: /utils-isolated/system-config-dirs** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils-isolated: /utils-isolated/user-config-dir** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils-isolated: /utils-isolated/system-data-dirs** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils-isolated: /utils-isolated/user-data-dir** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils-isolated: /utils-isolated/user-state-dir** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **utils-isolated: /utils-isolated/user-runtime-dir** | GLib/GObject/GModule 单元测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **1bit-mutex: /glib/1bit-mutex/int** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **1bit-mutex: /glib/1bit-mutex/pointer** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/language-names** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/locale-variants** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/version** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/appname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/prgname-thread-safety** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/tmpdir** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/basic_bits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/bits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/swap** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/find-program** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/find-program-for-path** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/debug** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/codeset** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/codeset2** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/console-charset** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/gettext** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/username** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/realname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/hostname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/xdgdirs** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/specialdir** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/os-info** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/clear-pointer** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/clear-pointer-cast** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/take-pointer** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/clear-source** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/misc-mem** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/aligned-mem** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/free-sized** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/nullify** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/atexit** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/check-setuid** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/int-limits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/clear-list** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/clear-slist** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/specialdir/desktop** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/clear-pointer/side-effects** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/aligned-mem/alignment** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/aligned-mem/zeroed** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-11: /utils/aligned-mem/free-sized** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/language-names** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/locale-variants** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/version** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/appname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/prgname-thread-safety** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/tmpdir** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/basic_bits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/bits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/swap** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/find-program** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/find-program-for-path** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/debug** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/codeset** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/codeset2** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/console-charset** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/gettext** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/username** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/realname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/hostname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/xdgdirs** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/specialdir** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/os-info** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/clear-pointer** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/clear-pointer-cast** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/take-pointer** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/clear-source** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/misc-mem** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/aligned-mem** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/free-sized** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/nullify** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/atexit** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/check-setuid** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/int-limits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/clear-list** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/clear-slist** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/specialdir/desktop** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/clear-pointer/side-effects** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/aligned-mem/alignment** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/aligned-mem/zeroed** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-17: /utils/aligned-mem/free-sized** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/language-names** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/locale-variants** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/version** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/appname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/prgname-thread-safety** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/tmpdir** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/basic_bits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/bits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/swap** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/find-program** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/find-program-for-path** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/debug** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/codeset** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/codeset2** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/console-charset** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/gettext** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/username** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/realname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/hostname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/xdgdirs** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/specialdir** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/os-info** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/clear-pointer** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/clear-pointer-cast** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/take-pointer** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/clear-source** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/misc-mem** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/aligned-mem** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/free-sized** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/nullify** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/atexit** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/check-setuid** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/int-limits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/clear-list** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/clear-slist** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/specialdir/desktop** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/clear-pointer/side-effects** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/aligned-mem/alignment** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/aligned-mem/zeroed** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-90: /utils/aligned-mem/free-sized** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/language-names** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/locale-variants** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/version** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/appname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/prgname-thread-safety** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/tmpdir** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/basic_bits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/bits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/swap** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/find-program** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/find-program-for-path** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/debug** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/codeset** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/codeset2** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/console-charset** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/gettext** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/username** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/realname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/hostname** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/xdgdirs** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/specialdir** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/os-info** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/clear-pointer** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/clear-pointer-cast** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/take-pointer** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/clear-source** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/misc-mem** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/aligned-mem** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/free-sized** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/nullify** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/atexit** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/check-setuid** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/int-limits** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/clear-list** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/clear-slist** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/specialdir/desktop** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/clear-pointer/side-effects** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/aligned-mem/alignment** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/aligned-mem/zeroed** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **utils-c-99: /utils/aligned-mem/free-sized** | GLib/GObject/GModule 单元测试 | 线程调度、affinity 接口或线程资源条件未满足 |
| **module-test-library: /module/basics** | GLib/GObject/GModule 单元测试 | 当前静态 HarmonyOS 构建不满足动态 GModule/plugin 测试条件 |
| **module-test-library: /module/invalid-libtool-archive** | GLib/GObject/GModule 单元测试 | 当前静态 HarmonyOS 构建不满足动态 GModule/plugin 测试条件 |
| **module-test-plugin: /module/basics** | GLib/GObject/GModule 单元测试 | 当前静态 HarmonyOS 构建不满足动态 GModule/plugin 测试条件 |
| **module-test-plugin: /module/invalid-libtool-archive** | GLib/GObject/GModule 单元测试 | 当前静态 HarmonyOS 构建不满足动态 GModule/plugin 测试条件 |
| **contenttype: /contenttype/guess** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/guess_svg_from_data** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/mime_from_content** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/unknown** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/subtype** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/list** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/executable** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/description** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/icon** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/symbolic-icon** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/tree** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/tree_invalid_encoding** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **contenttype: /contenttype/test_type_is_a_special_case** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **converter-stream: /converter/basics** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-input-stream/expander** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-input-stream/compressor** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-input-stream/truncation/zlib** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-input-stream/truncation/gzip** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-input-stream/truncation/raw** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-input-stream/charset/utf8->latin1** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-input-stream/charset/latin1->utf8** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-input-stream/charset/fallbacks** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-output-stream/roundtrip/zlib-0** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-output-stream/roundtrip/zlib-9** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-output-stream/roundtrip/gzip-0** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-output-stream/roundtrip/gzip-9** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-output-stream/roundtrip/raw-0** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-output-stream/roundtrip/raw-9** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-stream/pollable** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **converter-stream: /converter-stream/leftover** | GIO/设备集成测试 | 上游注明 musl 缺少 LC_COLLATE 非简单码点排序支持，charset 流转换用例可能失败；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行 |
| **gsubprocess: /gsubprocess/noop** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/noop-all-to-null** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/noop-no-wait** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/noop-stdin-inherit** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/search-path** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/search-path-from-envp** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/signal** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/exit1** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/echo1** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/echo-merged** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/cat-utf8** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/cat-eof** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/multi1** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/terminate** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/env** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/cwd** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/launcher-close** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/stdout-file** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/stdout-fd** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/child-setup** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/launcher-environment** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/exit1/cancel** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/exit1/cancel_in_cb** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/cancelled** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/no-pipes** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/separate-stderr** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/stdout-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/stderr-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/stdout-silence** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/nothing** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/cancelled** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/no-pipes** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/separate-stderr** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/stdout-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/stderr-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/stdout-silence** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/cancelled/no-pipes** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/cancelled/separate-stderr** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/cancelled/stdout-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/cancelled/stderr-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/async/cancelled/stdout-silence** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/cancelled** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/no-pipes** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/separate-stderr** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/stdout-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/stderr-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/stdout-silence** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/invalid** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/cancelled** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/no-pipes** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/separate-stderr** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/stdout-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/stderr-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/stdout-silence** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/invalid** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/cancelled/no-pipes** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/cancelled/separate-stderr** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/cancelled/stdout-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/cancelled/stderr-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/async/cancelled/stdout-silence** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/cancelled/no-pipes** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/cancelled/separate-stderr** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/cancelled/stdout-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/cancelled/stderr-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/utf8/cancelled/stdout-silence** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/cancelled/no-pipes** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/cancelled/separate-stderr** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/cancelled/stdout-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/cancelled/stderr-only** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/communicate/cancelled/stdout-silence** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/env/inherit** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/pass-fd/basic** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/pass-fd/empty-child-setup** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/pass-fd/inherit-fds** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/fd-conflation/basic** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/fd-conflation/empty-child-setup** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/fd-conflation/inherit-fds** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/fd-conflation/child-err-report-fd** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gsubprocess: /gsubprocess/exit-status/trapped** | GIO/设备集成测试 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **g-file-info: /g-file-info/test_g_file_info** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **g-file-info: /g-file-info/xattrs** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **g-file-info: /g-file-info/set-modified-date-time-precision** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **g-file-info: /g-file-info/test_g_file_info/modification-time** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **g-file-info: /g-file-info/test_g_file_info/access-time** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **g-file-info: /g-file-info/test_g_file_info/creation-time** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **gdbus-peer: /gdbus/peer-to-peer** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/delayed-message-processing** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/nonce-tcp** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/tcp-anonymous** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/credentials** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/codegen-peer-to-peer** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/peer-to-peer/signals** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/peer-to-peer/invalid/server** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/peer-to-peer/invalid/conn/stream/async** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/peer-to-peer/invalid/conn/stream/sync** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/peer-to-peer/invalid/conn/addr/async** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer: /gdbus/peer-to-peer/invalid/conn/addr/sync** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/ipv4_sync** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/ipv4_async** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/ipv6_sync** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/ipv6_async** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/ipv6_v4mapped** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/close_graceful** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/timed_wait** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/fd_reuse** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/address** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/unix-from-fd** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/unix-connection** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/unix-connection-ancillary-data** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/source-postmortem** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/read_write** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/read_writev** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/receive_bytes** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/receive_bytes_from** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/ipv4_sync/datagram** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/ipv4_sync/datagram/timeouts** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/ipv6_sync/datagram** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/ipv6_sync/datagram/timeouts** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/reuse/tcp** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/reuse/udp** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/get_available/datagram** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/get_available/stream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/credentials/tcp_client** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/credentials/tcp_server** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **socket: /socket/credentials/unix_socketpair** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **testfilemonitor: /monitor/atomic-replace** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **testfilemonitor: /monitor/file-changes** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **testfilemonitor: /monitor/dir-monitor** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **testfilemonitor: /monitor/dir-not-existent** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **testfilemonitor: /monitor/cross-dir-moves** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **testfilemonitor: /monitor/finalize-in-callback** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **testfilemonitor: /monitor/root** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **testfilemonitor: /monitor/file/hard-links** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **gdbus-address-get-session: /gdbus/x11-autolaunch** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-address-get-session: /gdbus/xdg-runtime** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-server-auth: /gdbus/server-auth** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-server-auth: /gdbus/server-auth/abstract** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-server-auth: /gdbus/server-auth/tcp** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-server-auth: /gdbus/server-auth/anonymous** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-server-auth: /gdbus/server-auth/external** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-server-auth: /gdbus/server-auth/sha1** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-server-auth: /gdbus/server-auth/anonymous/tcp** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-server-auth: /gdbus/server-auth/external/require-same-user** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-server-auth: /gdbus/server-auth/sha1/tcp** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **debugcontroller: /debug-controller/dbus/basic** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **debugcontroller: /debug-controller/dbus/duplicate** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **debugcontroller: /debug-controller/dbus/properties** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **file: /file/basic** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/build-filename** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/build-filenamev** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/parent** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/child** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/empty-path** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/type** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/parse-name** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/replace-load** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/replace-cancel** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/replace-symlink** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/async-new-tmp** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/async-new-tmp-dir** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/async-delete** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/async-make-symlink** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/copy-preserve-mode** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/measure** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/measure-async** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/load-bytes** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/load-bytes-async** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/build-attribute-list-for-copy** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/move_async** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/query-zero-length-content-type** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/query-default-handler-file** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/query-default-handler-file-async** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/query-default-handler-uri** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/query-default-handler-uri-async** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/enumerator-cancellation** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/async-create-delete/0** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/async-create-delete/1** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/async-create-delete/10** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/async-create-delete/25** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/async-create-delete/4096** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/replace-symlink/using-etag** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/replace/write-only** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/replace/read-write** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/copy/progress** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev/no-bytes-written** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev/no-vectors** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev/empty-vectors** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev/too-big-vectors** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev/async** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev/async_all** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev/async_all-empty-vectors** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev/async_all-no-vectors** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev/async_all-to-big-vectors** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/writev/async_all-cancellation** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/from-uri/ignores-query-string** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **file: /file/from-uri/ignores-fragment** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **gdbus-peer-object-manager: /gdbus/peer-object-manager/normal** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-peer-object-manager: /gdbus/peer-object-manager/root** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-sasl: /gdbus/sasl/server** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **live-g-file: /live-g-file/prep_clean_structure** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/create_structure** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/test_initial_structure** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/test_traverse_structure** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/test_enumerate** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/test_open** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/test_create** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/test_copy_move** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/test_delete** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/test_make_directory_with_parents** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/final_clean** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/test_unix_is_mountpoint/sysroot** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **live-g-file: /live-g-file/test_unix_is_mountpoint/proc** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **portal-support-flatpak-none: /portal-support/flatpak/none** | GIO/设备集成测试 | 该项检查 Flatpak portal 支持：在 g_get_user_runtime_dir() 写入 .flatpak-info 后读取 sandbox 网络与 dconf policy；HarmonyOS shell 不提供 Flatpak/XDG portal 会话，故将这 1 项列入 failing suite |
| **stream-rw_all: /stream/read_all_async/memory** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **stream-rw_all: /stream/write_all_async/memory** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **stream-rw_all: /stream/read_write_all_async/pipe** | GIO/设备集成测试 | 系统路径只读，或设备沙箱的文件系统/挂载行为不同 |
| **appinfo: /appinfo/basic** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/text** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/launch** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/show-in** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/commandline** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/launch-context** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/launch-context-signals** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/tryexec** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/associations** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/environment** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/startup-wm-class** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/supported-types** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/from-keyfile** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **appinfo: /appinfo/launch/no-appid** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **mimeapps: /appinfo/all** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **mimeapps: /appinfo/mime/api** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **mimeapps: /appinfo/mime/default** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **mimeapps: /appinfo/mime/file** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **mimeapps: /appinfo/mime/scheme-handler** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **mimeapps: /appinfo/mime/default-last-used** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **mimeapps: /appinfo/mime/ignore-nonexisting** | GIO/设备集成测试 | HarmonyOS shell 未提供上游测试依赖的系统 MIME 数据库 |
| **actions: /actions/basic** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/name** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/simplegroup** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/stateful** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/default-activate** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/entries** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/parse-detailed** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/property** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/no-properties** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/dbus/export** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/dbus/threaded** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **actions: /actions/dbus/bug679509** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **fdo-notification-backend: /fdo-notification-backend/construction** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **fdo-notification-backend: /fdo-notification-backend/dbus/activate-action** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-auth: /gdbus/auth/client/EXTERNAL** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-auth: /gdbus/auth/client/DBUS_COOKIE_SHA1** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-auth: /gdbus/auth/server/ANONYMOUS** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-auth: /gdbus/auth/server/EXTERNAL** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-auth: /gdbus/auth/server/DBUS_COOKIE_SHA1** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-bz627724: /gdbus/bz627724** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-close-pending: /gdbus/close-pending** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-close-pending: /gdbus/unref-pending** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-error: /gdbus/registered-errors** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-error: /gdbus/unregistered-errors** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-error: /gdbus/transparent-gerror** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-error: /gdbus/register-error** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-exit-on-close: /gdbus/exit-on-close/default** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-exit-on-close: /gdbus/exit-on-close/true** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-exit-on-close: /gdbus/exit-on-close/false** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-exit-on-close: /gdbus/exit-on-close/we-close** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-proxy-threads: /gdbus/proxy/vs-threads** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gnotification: /gnotification/basic** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gnotification: /gnotification/properties** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-connection-flush: /gdbus/connection/flush/busy** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-connection-flush: /gdbus/connection/flush/idle** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-non-socket: /gdbus/non-socket** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **resources: /resource/file** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/file-path** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/data** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/data_unaligned** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/data-corrupt** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/data-empty** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/registered** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/manual** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/manual2** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/automatic** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/module** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/binary-linked** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/64k** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/overlay** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/digits** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/uri/query-info** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **resources: /resource/uri/file** | GIO/设备集成测试 | 上游对 musl 的 GResource 测试保留 FIXME（GLib #3160）；Meson 按目标标记 can_fail，因此该二进制的 17 个注册用例整组未运行，具体缺陷以该上游 issue 为准 |
| **gdbus-export: /gdbus/object-registration** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-export: /gdbus/object-registration-with-closures** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-export: /gdbus/registered-interfaces** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-export: /gdbus/async-properties** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-export: /gdbus/threaded-unregistration/object** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-export: /gdbus/threaded-unregistration/subtree** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-method-invocation: /gdbus/method-invocation/return** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen: /gdbus/codegen/annotations** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen: /gdbus/codegen/interface_stability** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen: /gdbus/codegen/object-manager** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen: /gdbus/codegen/property-naming** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen: /gdbus/codegen/autocleanups** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen: /gdbus/codegen/deprecations** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen: /gdbus/codegen/standalone-interface-info** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen: /gdbus/codegen/unix-fd-list** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-old: /gdbus/codegen/annotations** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-old: /gdbus/codegen/interface_stability** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-old: /gdbus/codegen/object-manager** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-old: /gdbus/codegen/property-naming** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-old: /gdbus/codegen/autocleanups** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-old: /gdbus/codegen/deprecations** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-old: /gdbus/codegen/standalone-interface-info** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-old: /gdbus/codegen/unix-fd-list** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-min-required-2-64: /gdbus/codegen/annotations** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-min-required-2-64: /gdbus/codegen/interface_stability** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-min-required-2-64: /gdbus/codegen/object-manager** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-min-required-2-64: /gdbus/codegen/property-naming** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-min-required-2-64: /gdbus/codegen/autocleanups** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-min-required-2-64: /gdbus/codegen/deprecations** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-min-required-2-64: /gdbus/codegen/standalone-interface-info** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-test-codegen-min-required-2-64: /gdbus/codegen/unix-fd-list** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/equality** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/random** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/dbus/roundtrip** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/dbus/subscriptions** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/dbus/threaded** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/dbus/peer/roundtrip** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/dbus/peer/subscriptions** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/attributes** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/attributes/iterate** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/links** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/mutable** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/convenience** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/menuitem** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gmenumodel: /gmenu/input-validation** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GAppInfoMonitor** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GAppLaunchContext** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GApplicationCommandLine** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GApplication** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GBinding** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GBindingGroup** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GBufferedInputStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GBufferedOutputStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GBytesIcon** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GCancellable** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GCharsetConverter** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GConverterInputStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GConverterOutputStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GCredentials** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDataInputStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDataOutputStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusActionGroup** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusAuthObserver** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusConnection** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusMenuModel** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusMessage** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusMethodInvocation** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusObjectManagerClient** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusObjectManagerServer** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusObjectProxy** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusObjectSkeleton** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusProxy** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GDBusServer** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GEmblem** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GEmblemedIcon** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GFileEnumerator** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GFileInfo** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GFileInputStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GFileIOStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GFileOutputStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GFilenameCompleter** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GInetAddress** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GInetAddressMask** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GInetSocketAddress** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GInitiallyUnowned** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GIOModule** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GListStore** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GMemoryInputStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GMemoryOutputStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GMenu** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GMenuItem** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GMountOperation** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GNativeSocketAddress** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GNetworkAddress** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GNetworkService** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GNotification** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GObject** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GPropertyAction** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GProxyAddressEnumerator** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GProxyAddress** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSettings** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSignalGroup** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSimpleAction** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSimpleActionGroup** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSimpleAsyncResult** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSimpleIOStream** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSimplePermission** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSimpleProxyResolver** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSocketClient** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSocketConnection** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSocket** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSocketListener** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSocketService** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSubprocess** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GSubprocessLauncher** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GTask** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GTcpConnection** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GTcpWrapperConnection** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GTestDBus** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GThemedIcon** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GThreadedSocketService** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GTlsInteraction** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GTlsPassword** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GUnixConnection** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GUnixFDList** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GVfs** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GVolumeMonitor** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GZlibCompressor** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **defaultvalue: /Default Values/GZlibDecompressor** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **assert-msg-test.py: TestAssertMessage.test_gassert** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **assert-msg-test.py: TestAssertMessage.test_gdb_gassert** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **genmarshal.py: TestGenmarshal.test_help** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **genmarshal.py: TestGenmarshal.test_no_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **genmarshal.py: TestGenmarshal.test_empty_list** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **genmarshal.py: TestGenmarshal.test_void_boolean** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **genmarshal.py: TestGenmarshal.test_void_boolean_int64** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **genmarshal.py: TestGenmarshal.test_void_variant_nostdinc_valist_marshaller** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **genmarshal.py: TestGenmarshal.test_void_string_nostdinc** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **genmarshal.py: TestGenmarshal.test_void_param_nostdinc** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_help** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_no_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_empty_template** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_no_headers** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_empty_header** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_enum_name** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_non_utf8_encoding** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_reproducible** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_no_nick** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_with_double_quotes** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_filename_basename_in_fhead_ftail** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_since** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_enum_private_public** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_available_in** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_deprecated_in** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_deprecated_in_for** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_enum_symbolic_expression** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestMkenums.test_comma_in_enum_value** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_help (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_no_args (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_empty_template (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_no_headers (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_empty_header (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_enum_name (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_non_utf8_encoding (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_reproducible (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_no_nick (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_with_double_quotes (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_filename_basename_in_fhead_ftail (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_since (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_enum_private_public (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_available_in (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_deprecated_in (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_deprecated_in_for (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_enum_symbolic_expression (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **mkenums.py: TestRspMkenums.test_comma_in_enum_value (inherited)** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_help** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_no_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_empty_interface_header** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_empty_interface_info_header** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_empty_interface_body** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_empty_interface_info_body** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_reproducible** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_docbook** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_md** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_rst** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_rst_method** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_rst_signal** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_rst_property** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_glib_min_required_invalid** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_glib_min_required_too_low** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_glib_min_required_major_only** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_glib_min_required_with_micro** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_glib_max_allowed_too_low** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_glib_max_allowed_major_only** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_glib_max_allowed_with_micro** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_glib_max_allowed_unstable** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_glib_max_allowed_less_than_min_required** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_dbus_types** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_unix_fd_types_and_annotations** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_call_flags_and_timeout_method_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_signal_id_simple_signal** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_signal_id_multiple_signals_types** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_signal_id_multiple_signal_args_types** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_signals_marshaller_simple_signal** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_signals_marshaller_single_typed_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_signals_marshallers_multiple_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_methods_marshaller_simple_method** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_methods_marshaller_single_typed_in_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_methods_marshaller_single_typed_out_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_methods_marshallers_multiple_in_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_methods_marshallers_multiple_out_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_methods_marshallers_with_unix_fds** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_generate_valid_docbook** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **codegen.py: TestCodegen.test_indentation_preservation_in_comments** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-tool.py: TestGioTool.test_help** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-tool.py: TestGioTool.test_no_args** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-tool.py: TestGioTool.test_info_non_default_attributes** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gtester-xmllint-check: xmllint --noout tmpsample.xml** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **glib-2.0-pkg-config: pkg-config --validate glib-2.0** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **glib-2.0-pkg-config: test "$(pkg-config --modversion glib-2.0)" = "2.80.0"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **glib-2.0-pkg-config: test "$(pkg-config --variable=prefix glib-2.0)" = "/"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **glib-2.0-pkg-config: test "$(pkg-config --variable=datadir glib-2.0)" = "/share"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **glib-2.0-pkg-config: test "$(pkg-config --variable=gobject_query glib-2.0)" = "/bin/gobject-query"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **glib-2.0-pkg-config: test "$(pkg-config --variable=glib_mkenums glib-2.0)" = "/bin/glib-mkenums"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **glib-2.0-pkg-config: test "$(pkg-config --variable=glib_valgrind_suppressions glib-2.0)" = "/share/glib-2.0/valgrind/glib.supp"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: pkg-config --validate gio-2.0** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --modversion gio-2.0)" = "2.80.0"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=prefix gio-2.0)" = "/"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=datadir gio-2.0)" = "/share"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=schemasdir gio-2.0)" = "/share/glib-2.0/schemas"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=giomoduledir gio-2.0)" = "/lib/gio/modules"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=gio gio-2.0)" = "/bin/gio"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=glib_compile_resources gio-2.0)" = "/bin/glib-compile-resources"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=gdbus gio-2.0)" = "/bin/gdbus"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=gdbus_codegen gio-2.0)" = "/bin/gdbus-codegen"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=gresource gio-2.0)" = "/bin/gresource"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=gsettings gio-2.0)" = "/bin/gsettings"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=gio_querymodules gio-2.0)" = "/bin/gio-querymodules"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-2.0-pkg-config: test "$(pkg-config --variable=glib_compile_schemas gio-2.0)" = "/bin/glib-compile-schemas"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-unix-2.0-pkg-config: pkg-config --validate gio-unix-2.0** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-unix-2.0-pkg-config: test "$(pkg-config --modversion gio-unix-2.0)" = "2.80.0"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **gio-unix-2.0-pkg-config: test "$(pkg-config --variable=prefix gio-unix-2.0)" = "/"** | 脚本与独立检查 | POSIX 账户、shell 环境、工具安装或设备路径与上游假设不同 |
| **desktop-app-info: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-connection: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-connection-loss: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-connection-slow: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-introspection: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-names: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-proxy: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-proxy-unique-name: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-proxy-well-known-name: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gdbus-threading: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gapplication: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **dbus-appinfo: standalone Meson command check** | GIO/设备集成测试 | session D-Bus 服务不可用，或 AF_UNIX/套接字受设备沙箱限制 |
| **gsettings: standalone Meson command check** | GIO/设备集成测试 | 上游 gio/tests/meson.build 将该 GSettings 集成目标标为 can_fail（关联 GLib #3148）；目标需要编译 schema 并加载 gettext 测试目录，HarmonyOS shell 的会话与运行时环境不同，因此这 1 项按目标排除 |
