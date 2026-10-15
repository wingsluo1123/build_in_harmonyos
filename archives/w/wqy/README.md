# WenQuanYi Zen Hei

文泉驿正黑是一套包含简体中文、繁体中文及多种语言字形的开源 TrueType 字体集合。

## 功能

- 分发上游原版 `wqy-zenhei.ttc`，包含 Zen Hei、Zen Hei Mono 和 Zen Hei Sharp 三个字体面。
- 供 HarmonyOS 应用将字体资源随 HAP 打包，并在应用内按需加载。
- 保留上游 `COPYING`、`README` 和 `AUTHORS`，包括字体嵌入例外及字形署名说明。

## HarmonyOS 适配

此 Conan 包只分发字体资源，不修改设备字体目录、不安装系统服务，也不进行全局字体注册。需要通过文件路径加载字体的应用，应将 TTC 纳入 HAP，复制至自身私有目录，再使用 HarmonyOS Drawing API 加载。设备预装字体的匹配行为不由本包改变。

## 依赖

Conan 包没有构建或运行时依赖。HarmonyOS 应用使用系统提供的 OH_Drawing API。

## 参考

- [WenQuanYi 项目主页](https://sourceforge.net/projects/wqy/)
- [WenQuanYi Zen Hei 0.9.45 上游归档](https://sourceforge.net/projects/wqy/files/wqy-zenhei/0.9.45%20%28Fighting-state%20RC1%29/wqy-zenhei-0.9.45.tar.gz/download)
