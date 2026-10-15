# DRAFT-2670 — rest-0.7 缺件：以 libsoup 2.4 重建固定 URL 表单 POST 调用簇

> 状态：草稿（来自 gnome-recipes 2.0.4 适配，task_id=2670）

## 问题

上游 `dependency('rest-0.7')` 在 OHOS 环境解析失败：

```
meson.build:90:0: ERROR: Dependency "rest-0.7" not found, tried pkgconfig and cmake
```

第一反应查制品仓会发现 **librest/0.10.2 已发布**——但它救不了场：
该包是 librest 的 **rest-1.0 API 世代**（`pkg_config_name=rest-1.0`、
libs `rest-1.0`、`include/rest-1.0`），且 `requires libsoup3/3.6.5`。
而 gnome-recipes 要的是 **rest-0.7.pc**（libsoup 2.4 世代 API）。

## 根因

两层不匹配叠在一起：

1. **世代缺件**：制品仓没有 librest 0.8/0.9（libsoup 2.4 系、保留
   rest-0.7.pc 名字）的老世代包，只有重命名后的 rest-1.0 新世代。
2. **libsoup 代际冲突**：gnome-recipes 的 GTK3 栈整个建立在
   libsoup 2.4 上；librest/0.10.2 会把 libsoup3 拖进同一进程。
   libsoup2 与 libsoup3 导出同名符号，GNOME 明确不支持同进程混链
   ——所以"就近消费 librest/0.10.2"这条捷径从根上不成立。

进一步看实际调用面：gnome-recipes 用 librest 的地方全部是
**固定 URL 的 x-www-form-urlencoded POST**（Todoist 购物清单），
`oauth2-proxy.h` 头文件虽被 include，但 OAuth 逻辑实际不存在于调用面。
这类用法就是 libsoup 的一层薄封装，移植代价可控。

## 方案

**主方案**：把调用簇直接落回 libsoup 2.4，整文件移除 rest 依赖。

gnome-recipes 2.0.4 的移植形态（5 处调用簇：3 异步 + 2 同步）：

- 静态单例 `SoupSession`（`soup_session_new`）；
- `form_post_message(url, form)`：`soup_message_new("POST", url)` +
  `soup_message_set_request(msg, "application/x-www-form-urlencoded",
  SOUP_MEMORY_TAKE, form->str, form->len)`，随后
  `g_string_free(form, FALSE)`（SOUP_MEMORY_TAKE 已接管内存）；
- 表单构造：`GString` + `g_string_append_uri_escaped` 逐键值 append；
- 同步：`soup_session_send_message` + `msg->status_code`，出口
  `g_object_unref(msg)`；
- 异步：`soup_session_queue_message(session, msg, cb, user_data)`，
  回调签名 `(SoupSession*, SoupMessage*, gpointer)`，回调内**不要**
  unref（队列持有），响应体取 `msg->response_body->data/length`；
- `sync_token` 指向 dup 出的 json 对象（原设计有意不释放以复用），
  移植保持同一生命周期语义；
- 上游 `meson.build` 只需删 `dependency('rest-0.7')` 一行。

**回退**：若调用面含真 OAuth（rest 的 oauth/oauth2 proxy 族），
单纯重建表单层不够，需自行实现 token 获取与 Authorization 头
（可经 libgoa）；或先适配一版 librest 0.8/0.9（libsoup2.4 老世代）
recipes 再消费——属于新库适配，工作量大，通常不如直接改应用。

## 验证

- gnome-recipes 2.0.4（task 2670，2026-10-14）：
  - patch_ng（conan 同款解析器）strip=0 链式应用补丁 0001 通过，应用结果与编写树逐字节一致（meson.build / exporter.c）；
  - 未移植函数与上游逐字节一致（仅 8 个函数为移植面）；
  - 真机 conan-verify 八门禁结果见主配方 notes.md。

## 适用边界

- 上游用 `dependency('rest-0.7')` / `rest_proxy_call_*`，且与
  gtk3 / libsoup2.4 栈同进程共存的应用；
- 判定捷径：制品仓有 `librest/*` 时先看 `pkg_config_name`——
  是 `rest-1.0`（soup3）就与 rest-0.7 需求无关，不可当"已有依赖"复用；
- 如果应用本身不含 libsoup2.4 依赖（全新 soup3 栈），则应直接升级到
  librest/0.10.2 + rest-1.0 API，而不是本移植路线。

## 查重差异

- 与既有"缺件即查制品仓"总则条目互补：本条目的要点恰恰是
  **"同名包存在"≠"可复用"**——世代（rest-0.7 vs rest-1.0）
  与 soup 代际（2.4 vs 3）双重判据缺一不可；
- 与 libsoup3 系条目（DRAFT-libsoup3-*）不重叠：那是 soup3 自身的
  配方形态问题。

## 关联交付

- 本草稿与 `archives/g/gnome-recipes/2.0.4/**` 同属一次交付
  （补丁 0001-shopping-list-export-via-libsoup.patch）。
- 正式 E 编号由知识库主编审核后分配。
