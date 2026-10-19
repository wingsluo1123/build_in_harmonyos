# E-DRAFT: cnb.cool 制品仓"包不存在"的判定陷阱（conan list 假阳性 + download 非标准 404）

## 错误签名

- `conan download <ref> -r=ohpcd` → `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`（缺失包，非标准 404）
- `conan list <精确ref> -r=ohpcd` → `ERROR: Recipe '<ref>' not found`，**但 exit 0**
- `conan list "<名称>*" -r=ohpcd` → `Found 0 pkg/version recipes matching`（可靠信号）

## 根因

cnb.cool remote 对不存在资源的响应不符合 conan 官方 404 语义，被 conan CLI 转成上述两种误导形态。精确 ref 的 list 即使 not found 也返回退出码 0，脚本若以 `$?` 或 `grep -q <版本>`（会命中 ERROR 回显行）判断即假阳性。

## 实证矩阵（2026-09-23，本机鸿蒙PC）

| 包 | 通配 list | download | 结论 |
|---|---|---|---|
| ocaml/4.14.1.1.4 | 命中 | 正常返回 revisions | 存在 |
| dune/3.17.0 | 命中 | 正常 | 存在 |
| gtk/3.24.43 | 命中 | 正常 + graph info 全图可解析 | 存在 |
| gtk+/3.24.38 | Found 0 | acceleration policy 错误 | 不存在（正确名是 gtk/3.24.43） |
| cairo2/0.6.5 | Found 0 | acceleration policy 错误 | 不存在 |
| camlp-streams/5.0.1 | Found 0 | acceleration policy 错误 | 不存在 |

## 处方

1. W0/R35 判定一律走 **通配符 list + download 双验证**，禁止只看退出码；
2. "acceleration policy" 错误在已知存在包可正常 download 的同一会话内 = 包不存在（非网络故障），重试 2 次即改判 missing，勿按网络抖动无限退避；
3. 脚本解析建议锚定 `Found N` 行（通配）或 `not found` 行（精确，反向匹配）。

## 关联案例

- lablgtk3 3.1.5 W0 预检：初判 gtk+ 误报"已存在"（精确 ref grep 假阳性），改通配符后纠正为 gtk/3.24.43。
