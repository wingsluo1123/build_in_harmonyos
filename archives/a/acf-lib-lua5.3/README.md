# acf-lib-lua5.3

Lua 5.3 modules from the Alpine Configuration Framework standard library.

The package installs the eight upstream modules below
`share/lua/5.3/acf/`, preserves the upstream top-level compatibility module
names below `share/lua/5.3/`, and exports the search path through `LUA_PATH`.

A portability patch replaces Lua 5.1-era APIs in `format.lua`
(`getfenv`, `string.gfind`) with their Lua 5.2+ equivalents so the
modules load cleanly under Lua 5.3.

The modules `acf.format`, `acf.html`, and `acf.validator` use only Lua's
standard library. Other modules expose optional system-facing features that
require POSIX, subprocess, or database-driver modules at runtime.
