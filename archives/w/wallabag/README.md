# wallabag

wallabag 是一个自托管的稍后阅读（read-it-later）Web 应用（PHP/Symfony），
可收藏网页并转为干净的阅读视图，支持标签、全文搜索、RSS 导出与 REST API。

## 功能概述

- 网页收藏与正文提取（graby）、阅读时间估算
- 标签（含按规则自动打标签）、全文搜索、导出（EPUB/PDF/CSV/TXT）
- REST API 与 Fever/订阅源兼容接口
- 多语言界面、多数据库后端（MySQL/PostgreSQL/SQLite）

## OHOS 适配

- 适配方式：官方生产包原样分发到 `share/wallabag`，无编译、无补丁、无 conan 依赖
- 验证策略：纯 python 结构完整性校验（精确计数 + 关键文件非空与版本锚点）；
  构建机有系统 php 时追加 php -l 全量校验、autoloader 装载验证与 php 消费者套件
  （conan 远端无 php 配方，故不声明 tool_requires，改探测系统解释器）
- 上游 phpunit 套件（571 方法）需 DB 与外部服务且生产包无运行器，
  在真机/CI 均不可执行，如实计 environment gaps；build() 内以
  结构完整性校验替代（有 php 时加 lint 全量 10,545 文件校验 + 装载验证）
- 对外运行（httpd/php-fpm、数据库）由部署环境提供，不在配方范围内

## 依赖关系

- 无 conan 依赖（bundle 内 vendor/ 自带全部 PHP 第三方库；composer.json 要求
  php >= 7.4 及 ext-curl/gd/intl/tidy 等，ohpcd php 系 --disable-all 构建，
  即使补齐运行器也缺扩展——进一步佐证 gaps 归类）

## 参考资料

- 官网: https://www.wallabag.org
- 源码: https://github.com/wallabag/wallabag
- 本版发布: https://github.com/wallabag/wallabag/releases/tag/2.6.14
