# graphene

Graphene is a thin layer of graphic data types for 2D/3D graphics (vectors, matrices, quaternions, etc.), used by GTK4 and the GNOME desktop.

## Available Version
- 1.10.8 (2026-08-09): SIMD-tuned for OHOS aarch64 (ARM NEON)

## Description
Graphene provides efficient SIMD-accelerated 2D/3D data types: vectors, matrices, quaternions, points, rects, and more. It is a dependency of GTK4.

## Dependencies
- glib (2.84.0.1)

## Features (1.10.8)
- ARM NEON SIMD enabled, SSE2/GCC vector disabled (aarch64)
- GObject types enabled
- Introspection disabled

## Usage
```bash
# Conan recipe
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
