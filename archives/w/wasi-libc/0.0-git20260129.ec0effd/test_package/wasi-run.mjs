#!/usr/bin/env node
// wasi-run.mjs - run a wasm32-wasip1 module under Node's built-in WASI
// (preview1), emulating the wasmtime CLI surface the wasi-libc test suite is
// driven with:
//
//   --dir <HOST>::<GUEST>   preopen host directory as guest path
//   --env K=V               set environment variable
//
// followed by the .wasm path and its program arguments.  Exit status mirrors
// the wasm program's exit code.
//
// Known Node-WASI engine gaps relative to wasmtime (documented in the
// adaptation notes; all host-side, not libc defects): no "." / ".."
// synthesis in fd_readdir, fd_fdstat flags reporting, and ENOTSUP for
// path_link / fd_ioctl / posix_advise / posix_allocate style hostcalls.
import { readFileSync } from 'node:fs';
import { WASI } from 'node:wasi';

function parse(argv) {
  const preopens = {};
  const env = {};
  const args = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--dir') {
      if (i + 1 >= argv.length) {
        console.error('wasi-run.mjs: --dir requires HOST::GUEST');
        process.exit(2);
      }
      const spec = argv[++i];
      const sep = spec.indexOf('::');
      if (sep >= 0) {
        const host = spec.slice(0, sep);
        const guest = spec.slice(sep + 2);
        preopens[guest || host] = host || guest;
      } else {
        preopens[spec] = spec;
      }
    } else if (a === '--env') {
      if (i + 1 >= argv.length) {
        console.error('wasi-run.mjs: --env requires K=V');
        process.exit(2);
      }
      const kv = argv[++i];
      const eq = kv.indexOf('=');
      env[kv.slice(0, eq)] = kv.slice(eq + 1);
    } else {
      args.push(a, ...argv.slice(i + 1));
      break;
    }
  }
  return { preopens, env, args };
}

const { preopens, env, args } = parse(process.argv.slice(2));
if (args.length === 0) {
  console.error('wasi-run.mjs: no wasm module given');
  process.exit(2);
}

const wasi = new WASI({
  version: 'preview1',
  args,
  env,
  preopens,
  returnOnExit: true,
});

const bytes = readFileSync(args[0]);
const mod = await WebAssembly.compile(bytes);
const instance = await WebAssembly.instantiate(mod, wasi.getImportObject());
const code = wasi.start(instance);
process.exit(code);
