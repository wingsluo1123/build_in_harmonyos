# ocamlbuild

OCamlbuild is a generic build tool with built-in rules for building OCaml
libraries and programs.

## Homepage

https://github.com/ocaml/ocamlbuild

## License

LGPL-2.0-or-later WITH OCaml-LGPL-linking-exception

## Versions

| Version | Status |
|---------|--------|
| 0.16.1 | built |

## Build notes

Built with the registry OCaml toolchain (`ocaml/4.14.1.1.4`) and findlib
(`findlib/1.9.8`). The recipe installs a private OHOS toolchain shim
(`as`/`ocamlc`/`ocamlopt`/`ocamlmklib` wrappers, findlib conf/topfind,
ELF re-signing) to work around registry-package baked CI paths and OHOS
`.codesign` enforcement. See `0.16.1/notes.md` for details.
