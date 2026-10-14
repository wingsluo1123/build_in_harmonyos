# sacc

sacc is a small terminal Gopher client. The 1.07 archive builds the upstream terminal interface with Gopher and Gophers support and installs the `sacc` executable, manual page, and ISC license.

The Conan recipe pins the original 1.07 source archive by SHA256. It uses LibreSSL for TLS and ncursesw for the terminal interface. The upstream Makefile defaults to `-lcurses`; the recipe selects `-lncursesw` to match the available OHOS package and supplies the Conan target compiler and dependency paths.

The installed-package test starts a local Gopher server and checks menu and text selectors, received output, executable installation, and missing-URL handling. These tests passed on WSL Linux x86_64. They do not cover a TLS handshake, external Gopher servers, downloads, or interactive terminal navigation. HarmonyOS armv8 build and runtime behavior remain subject to official CI.

Upstream source: https://git.codemadness.org/sacc/
