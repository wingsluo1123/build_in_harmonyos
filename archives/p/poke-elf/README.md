# poke-elf

**GNU poke pickle for editing ELF object files, executables, shared libraries and core dumps**

`poke-elf` is a full-fledged Poke pickle (`.pk` files) plus the `prelinkr`
example utility. It supports many architectures and extensions, including
AArch64, and is used through the GNU poke editor (`poke`).

## Usage

```bash
# Load the ELF pickle inside poke (pickles live in share/poke/pickles).
# Out-of-prefix pickles are exposed via POKE_LOAD_PATH (prepended to
# poke's load_path at startup); `-L FILE` is a script-file option, not
# a load-path directory option.
export POKE_LOAD_PATH=<poke-elf pickles>
poke --color=no -c 'load elf;'

# Inspect constants (Poke language)
poke --color=no -c 'load elf; printf "%u32d\n", ELF_ET_DYN;'

# Example utility (installed to bin/)
prelinkr --help
```

Poke language notes: `load elf;` finds `elf.pk` via `POKE_LOAD_PATH`;
`poke -c` propagates assertion failures, `poke -s` needs exact-output matching.

## OHOS arm64 adaptation points

- `poke/5.0` is required at build time (upstream `make check`) and at runtime
- `configure` umask relaxed for HMDFS; prebuilt `poke-elf.info` pinned with `MAKEINFO=true`
- Runtime needs both the poke stdlib datadir (`POKEDATADIR`) and the elf pickles
  (`POKE_LOAD_PATH=<pkg>/share/poke/pickles` + `load elf;`)

See version directory [1.0/notes.md](1.0/notes.md).
