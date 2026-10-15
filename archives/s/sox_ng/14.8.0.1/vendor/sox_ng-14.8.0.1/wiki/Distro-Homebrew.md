# Distro homebrew

Homebrew carries 14.4.2 with two patches

## Links

* [Homebrew formula](https://github.com/Homebrew/homebrew-core/blob/3f8e8c8f8cf7671ad134464f6eee2f82cb8f22b2/Formula/s/sox.rb)

## Patches

| Patch | Issue |
| :---- | :---: |
| [fix device name length in MacOS](https://80x24.org/sox.git/patch?id=bf2afa54a7dec) | #167 |
| [Fix -flat_namespace being used on Big Sur and later](https://raw.githubusercontent.com/Homebrew/formula-patches/03cf8088210822aa2c1ab544ed58ea04c897d9c4/libtool/configure-pre-0.4.2.418-big_sur.diff) | - |

The second patch modifies `configure`, which is auto-generated.
