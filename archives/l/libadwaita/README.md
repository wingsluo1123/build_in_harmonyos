# libadwaita

libadwaita provides building blocks for modern GNOME applications using GTK4.

## Available Version
- 1.2.0 (2026-08-09): Built for OHOS with GTK4 Broadway backend

## Description
libadwaita is the GNOME application widget library built on top of GTK4. It provides adaptive widgets, styles, and utilities for modern GNOME applications.

## Dependencies
- gtk4 (4.22.4)
- glib (2.84.0.1)

## Features (1.2.0)
- Introspection disabled
- Tests, examples, vapi, and gtk_doc disabled

## Usage
```bash
# Conan recipe
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
