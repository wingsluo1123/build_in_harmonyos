# DRAFT-9008-flang-ohos-fortran-toolchain-gaps

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-9008-flang-ohos-fortran-toolchain-gaps.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-9008: 用 flang-ohos 编译 OHOS 上的 Fortran 组件 —— 工具链缺口的四类报错与处置

- 条目主题：HarmonyOS 无 gfortran，Fortran 上游包必须 `tool_requires("flang-ohos/20.1.0")`；
  flang 与 gfortran 的差异会依次暴露四类报错，逐条对应固定处置。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxxx）
- 关联 PR：feat/pftools-3.2.12（参照 archives/a/alfa/2.2）

## 适用场景

- 目标库含 Fortran 组件（`PROJECT(... Fortran ...)`、`*.f`/`*.f90`）；
- 本机与 ohpcd 都无 gfortran（`gcc/9.5.0` 配方为 `--enable-languages=c`）；
- 直接 cmake 会先报 `No CMAKE_Fortran_COMPILER could be found`。

## 四类报错与处置（按出现顺序）

### ① 找不到编译器 → tool_requires + 只编译不链接

```python
def build_requirements(self):
    self.tool_requires("flang-ohos/20.1.0")
def generate(self):
    flang = self.dependencies.build["flang-ohos"].package_folder
    tc.variables["CMAKE_Fortran_COMPILER"] = os.path.join(flang, "bin", "flang")
    tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
```
不设 `TRY_COMPILE_TARGET_TYPE` 时，`PROJECT(... Fortran ...)` 的 try-compile 会因缺 crt 失败。

### ② `error: Only -std=f2018 is allowed currently.`

```cmake
IF(CMAKE_Fortran_COMPILER_ID STREQUAL "LLVMFlang")
    SET(F2K_FLAGS "-fno-automatic")
ELSE()
    SET(F2K_FLAGS "-fno-automatic -std=legacy")
ENDIF()
```

### ③ `fdate is not supported.`（Signal 6）

```fortran
      FDAT=' '
      Call Date_and_time(Date=FDAT(1:8),Time=FDAT(10:15))
```

### ④ 链接期缺 crt / 运行时

把 OHOS SDK clang 的 `crtbeginS.o`/`crtendS.o`/`libclang_rt.builtins.a`/`libunwind.a`
复制到 flang 期望的 `lib/clang/20/lib/aarch64-linux-ohos/`（见 kv 内完整脚本），
CMake 侧补 `--sysroot` + `-L` + `libFortranRuntime.a`/`libFortranDecimal.a`；
C 目标若链接 Fortran 目标文件（如 `quantile(rq0.f)`），C 链接行也要带 Fortran 运行时。

## 证据（真实执行）

pftools 3.2.12：

- `conan download gcc/9.5.0 -r=ohpcd --only-recipe` → `--enable-languages=c`（无 gfortran）；
- `conan download flang-ohos/20.1.0 -r=ohpcd` → exit 0；`flang --version` → 20.1.0，Target aarch64-unknown-linux-ohos；
- 依次踩到 ①②③④，逐条处置后 `make` exit 0，12 个 Fortran 程序 + `pfcalibrateV3` 全部链接成功
  （`readelf -d` 仅依赖 libc）；上游 CTest **6/6 通过**。

## 推广价值

- 所有含 Fortran 的鸿蒙 PC 适配（arpack-ng / blas / alfa / devicexlib / kim-api / pftools …）；
- 把"OHOS 没有 Fortran 编译器"从选型否决条件变成可复用工具链方案，并给出 flang/gfortran 差异清单。

## 查重关键词

flang-ohos、LLVMFlang、No CMAKE_Fortran_COMPILER、-std=legacy、Only -std=f2018 is allowed、
fdate is not supported、libFortranRuntime、libclang_rt.builtins、crtbeginS.o、libunwind.a、
CMAKE_TRY_COMPILE_TARGET_TYPE、tool_requires Fortran
