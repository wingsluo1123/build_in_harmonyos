#!/usr/bin/env python3
"""Conan recipe for cline 4.0.5 — TypeScript autonomous coding agent SDK/CLI.

cline is an autonomous coding agent capable of creating/editing files, running
commands, using the browser, and more. Written in TypeScript, built with esbuild.

Build system: npm (package.json + esbuild + TypeScript)
No C/C++ compilation required — pure JavaScript/TypeScript project.

Note: The upstream project uses Bun as its package manager and build tool.
Bun is not available on OpenHarmony. This recipe uses npm + esbuild as a
replacement build system, writing an esbuild-based build script inline.

Packaging strategy: The built JS output (dist/ directories for SDK packages
and CLI) is packaged as data files. Consumers use NODE_PATH to locate modules.
"""
import os
import shutil
import json

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


# Inline esbuild build script (replaces Bun.build() calls)
BUILD_SCRIPT = r'''#!/usr/bin/env node
import { build } from 'esbuild';
import { copyFileSync, cpSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = fileURLToPath(new URL('.', import.meta.url));
const sdkDir = join(rootDir, 'sdk/packages');
const cliDir = join(rootDir, 'apps/cli');

async function buildPkg(pkgDir, name, entrypoints, external = []) {
  console.log(`\n📦 Building ${name}...`);
  for (const e of entrypoints) {
    try {
      await build({
        entryPoints: [join(pkgDir, e.src)],
        outfile: join(pkgDir, e.outDir, e.outFile || 'index.js'),
        bundle: true, platform: 'node', target: 'node22',
        format: 'esm', minify: true, sourcemap: false,
        external: [...external, ...(e.external || [])],
        define: { 'process.env.NODE_ENV': '"production"' },
        logLevel: 'warning',
      });
    } catch (err) { console.error(`❌ ${name}: ${err.message}`); throw err; }
  }
  console.log(`  ✅ ${name}`);
}

async function main() {
  // 1. shared
  await buildPkg(join(sdkDir, 'shared'), '@cline/shared', [
    { src: './src/index.ts', outDir: './dist' },
    { src: './src/automation/index.ts', outDir: './dist/automation' },
    { src: './src/db/index.ts', outDir: './dist/db' },
    { src: './src/remote-config/index.ts', outDir: './dist/remote-config' },
    { src: './src/storage/index.ts', outDir: './dist/storage' },
  ]);
  // 2. llms
  await buildPkg(join(sdkDir, 'llms'), '@cline/llms', [
    { src: './src/index.ts', outDir: './dist' },
  ], ['@cline/shared', 'nanoid']);
  // 3. agents
  await buildPkg(join(sdkDir, 'agents'), '@cline/agents', [
    { src: './src/index.ts', outDir: './dist' },
  ], ['@cline/llms', '@cline/shared', 'nanoid']);
  // 4. core
  const corePkg = JSON.parse(await import('node:fs').then(fs =>
    fs.readFileSync(join(sdkDir, 'core/package.json'), 'utf-8')));
  const coreExt = [...Object.keys(corePkg.dependencies || {}),
    ...Object.keys(corePkg.peerDependencies || {})];
  await buildPkg(join(sdkDir, 'core'), '@cline/core', [
    { src: './src/index.ts', outDir: './dist' },
    { src: './src/hub/index.ts', outDir: './dist/hub' },
    { src: './src/hub/daemon/entry.ts', outDir: './dist/hub/daemon', outFile: 'entry.js' },
    { src: './src/services/telemetry/index.ts', outDir: './dist/services/telemetry' },
    { src: './src/services/feature-flags/posthog.ts', outDir: './dist/services/feature-flags', outFile: 'posthog.js' },
    { src: './src/extensions/plugin/plugin-sandbox-bootstrap.ts', outDir: './dist/extensions', outFile: 'plugin-sandbox-bootstrap.js' },
  ], coreExt);
  // 5. sdk
  await buildPkg(join(sdkDir, 'sdk'), '@cline/sdk', [
    { src: './src/index.ts', outDir: './dist' },
  ], ['@cline/core']);
  // 6. cli
  await buildPkg(cliDir, '@cline/cli', [
    { src: './src/index.ts', outDir: './dist' },
  ], ['@opentui/core','@opentui/react','@opentui-ui/dialog','opentui-spinner',
    'react','react/jsx-runtime','react/jsx-dev-runtime','react-devtools-core']);
  // 7. Copy bootstrap
  const bs = join(sdkDir, 'core/dist/extensions/plugin-sandbox-bootstrap.js');
  const bsDest = join(cliDir, './dist/extensions/plugin-sandbox-bootstrap.js');
  if (existsSync(bs)) { mkdirSync(dirname(bsDest), { recursive: true }); copyFileSync(bs, bsDest); }
  console.log('\n✅ All packages built!');
}
main().catch(e => { console.error('❌', e); process.exit(1); });
'''


class ClineConan(ConanFile):
    name = "cline"
    version = "4.0.5"
    description = "Autonomous coding agent SDK/CLI — capable of creating/editing files, running commands, using the browser, and more"
    license = "Apache-2.0"
    homepage = "https://github.com/cline/cline"
    url = ""

    # R32: settings.os check must use in ("Linux", "OHOS")
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # JavaScript/TypeScript dependencies are installed via npm in build(),
        # not as Conan requires (R27: no @ohpcd/stable deps needed for pure JS)
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches (none currently, but required by G1 check)
        apply_conandata_patches(self)

        src_dir = self.source_folder

        # Step 1: Convert workspace:* protocol to * for npm compatibility
        self.run(
            f'cd "{src_dir}" && '
            f'find . -name "package.json" -not -path "*/node_modules/*" '
            f"-exec sed -i 's/\"workspace:\\*\"/\"\\*\"/g' {{}} \\;",
            env="conanrun",
        )

        # Step 2: Install npm dependencies (force to bypass platform checks)
        self.run(f'cd "{src_dir}" && npm install --force', env="conanrun")

        # Step 3: Write the esbuild build script (replaces Bun.build())
        build_script_path = os.path.join(src_dir, "build-with-esbuild.mjs")
        with open(build_script_path, "w") as f:
            f.write(BUILD_SCRIPT)

        # Step 4: Build all packages using esbuild
        self.run(f'cd "{src_dir}" && node build-with-esbuild.mjs', env="conanrun")

    def package(self):
        src_dir = self.source_folder
        pkg = self.package_folder

        # Install structure: lib/node_modules/cline/
        dest = os.path.join(pkg, "lib", "node_modules", "cline")
        os.makedirs(dest, exist_ok=True)

        # Copy CLI built artifacts
        cli_dist = os.path.join(src_dir, "apps", "cli", "dist")
        if os.path.exists(cli_dist):
            shutil.copytree(cli_dist, os.path.join(dest, "dist"), dirs_exist_ok=True)

        # Copy CLI package.json
        cli_pkg = os.path.join(src_dir, "apps", "cli", "package.json")
        if os.path.exists(cli_pkg):
            shutil.copy2(cli_pkg, os.path.join(dest, "package.json"))

        # Copy SDK packages' dist directories
        sdk_dir = os.path.join(src_dir, "sdk", "packages")
        if os.path.isdir(sdk_dir):
            for pkg_name in os.listdir(sdk_dir):
                pkg_path = os.path.join(sdk_dir, pkg_name)
                dist_path = os.path.join(pkg_path, "dist")
                pkg_json = os.path.join(pkg_path, "package.json")
                if os.path.isdir(dist_path):
                    sdk_dest = os.path.join(dest, "sdk", pkg_name)
                    os.makedirs(sdk_dest, exist_ok=True)
                    shutil.copytree(dist_path, os.path.join(sdk_dest, "dist"), dirs_exist_ok=True)
                    if os.path.exists(pkg_json):
                        shutil.copy2(pkg_json, os.path.join(sdk_dest, "package.json"))

        # Copy root package.json
        root_pkg = os.path.join(src_dir, "package.json")
        if os.path.exists(root_pkg):
            shutil.copy2(root_pkg, os.path.join(dest, "root-package.json"))

        # Copy essential runtime node_modules (external deps not bundled in CLI)
        node_modules = os.path.join(src_dir, "node_modules")
        if os.path.isdir(node_modules):
            nm_dest = os.path.join(dest, "node_modules")
            os.makedirs(nm_dest, exist_ok=True)
            essential_deps = [
                "@opentui", "react", "react-reconciler", "react-devtools-core",
                "commander", "marked", "pino", "zod", "nanoid", "yaml",
                "open", "fzf", "posthog-node",
            ]
            for dep in essential_deps:
                dep_path = os.path.join(node_modules, dep)
                if os.path.exists(dep_path):
                    dest_path = os.path.join(nm_dest, dep)
                    if os.path.isdir(dep_path):
                        shutil.copytree(dep_path, dest_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(dep_path, dest_path)

    def package_info(self):
        # Node.js module path for consumers
        node_modules_path = os.path.join(self.package_folder, "lib", "node_modules")
        bin_path = os.path.join(self.package_folder, "lib", "node_modules", "cline", "dist")

        # Set up environment for consumers
        self.cpp_info.bindirs = [os.path.join("lib", "node_modules", "cline", "dist")]
        self.cpp_info.libdirs = [os.path.join("lib", "node_modules")]

        # Environment variables for consumers
        self.runenv_info.define("NODE_PATH", node_modules_path)
        self.runenv_info.append("PATH", bin_path)
