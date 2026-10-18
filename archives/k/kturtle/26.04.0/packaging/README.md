# kturtle 26.04.0 packaging notes

交付形态：conan 包（conan create / CI upload 流水线），无独立离线安装包。

- 包内容：`bin/kturtle`（ELF aarch64，OHOS 签名由 CI sign.sh 处理）+
  `share/applications/org.kde.kturtle.desktop`、`share/knsrcfiles/kturtle.knsrc`、
  `share/metainfo/org.kde.kturtle.appdata.xml`、icons。
- 命令行声明：软件级 `commands.json`（R38，tool 类型）。
- 依赖闭包：conan 图管理（qtbase/6.11.1 + KF6 系），运行时库不打包进制品。
- 本目录仅存打包说明；打包产物归 conan 制品仓，不进源码仓（JC3）。
