# gnutls 3.8.4 adaptation notes

## Recipe scope

- Source: official GnuTLS 3.8.4 tarball with a fixed SHA-256 digest.
- Dependencies: `nettle/3.10.2` and `gmp/6.3.0`.
- Bundled component: libtasn1 is selected with `--with-included-libtasn1`.
- Platform patches: `config.guess` and `config.sub` triplet recognition only.
- Shell handling: bash is resolved from the worker `PATH`; `CONFIG_SHELL` and
  `SHELL` are scoped to configure and make through Conan `Environment`.

## Consumer check

The Conan test package executes `gnutls-cli --version` through the generated
run environment. The package also installs `gnutls-cli` and `gnutls-serv`,
which are declared in the software-level `commands.json`.

## Validation state

Historical target work produced GnuTLS binaries, but its notes mixed a manual
workaround with a failed `cat -` run and therefore cannot establish current
recipe reproducibility. The current recipe has passed Python/YAML parsing and
repository diff checks. Official CI remains pending until `nettle/3.10.2` is
merged and published; no current CI success is claimed here.
