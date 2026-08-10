# packaging

本目录用于存放构建产物（release/debug tar.gz）。

aiven-client 4.16.0 为纯 Python 包，构建产物为 `lib/python3.12/site-packages/aiven/`，
由 Conan package() 阶段打包到 Conan cache，不在此目录单独归档。
