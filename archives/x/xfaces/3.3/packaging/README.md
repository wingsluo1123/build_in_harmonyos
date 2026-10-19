# Packaging

xfaces 以 Conan 配方交付：`conan create` 产出单个 GUI 可执行文件
`bin/xfaces`（OHOS ELF 签名）与应用资源文件 `share/xfaces/XFaces.ad`；
X11 依赖（libxaw/libxext/compface 及传递库）均来自制品仓已发布的 conan
包，运行期由 conanrun 环境解析，不随包提交归档。
