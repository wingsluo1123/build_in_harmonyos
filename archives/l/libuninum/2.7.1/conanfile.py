"""libuninum upstream 2.7, adaptation repair 1: preserve UTF32 ABI on LP64."""
import glob
import hashlib
import io
import os
import re
import shlex
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run, load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get,
                              replace_in_file, save, unzip)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain


class LibuninumConan(ConanFile):
    name = 'libuninum'
    version = '2.7.1'
    description = 'Unicode numeral conversion; LP64 adaptation repair of upstream 2.7'
    license = 'LGPL-2.1'
    homepage = 'https://www.billposer.org/Software/libuninum.html'
    url = 'https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos'
    package_type = 'library'
    settings = 'os', 'compiler', 'build_type', 'arch'
    options = {'shared':[True,False], 'fPIC':[True,False]}
    default_options = {'shared':False, 'fPIC':True}
    exports_sources = 'utf32_ops.h', 'upstream.py'

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == 'Windows':
            self.options.rm_safe('fPIC')

    def configure(self):
        if self.options.shared:
            self.options.rm_safe('fPIC')

    def requirements(self):
        # uninum.h exposes mpz_t, so GMP is part of the public header/link ABI.
        self.requires('gmp/6.3.0.1', transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        if self.settings.os in ('Linux','OHOS'):
            self.tool_requires('tcl/8.6.16')

    def layout(self):
        self.folders.source = '.'
        self.folders.build = '.'
        self.folders.generators = 'conan'

    def source(self):
        source = self.conan_data['sources']
        archive = self.conf.get('user.libuninum:source_archive', default=None)
        if archive:
            raw = Path(archive).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source['sha256']:
                raise ConanException('local upstream archive SHA-256 mismatch')
            unzip(self, archive, strip_root=True)
        else:
            get(self, **source, strip_root=True)
        if self.export_sources_folder != self.source_folder:
            copy(self, 'utf32_ops.h', src=self.export_sources_folder, dst=self.source_folder)
        path = os.path.join(self.source_folder, 'uninum.c')
        old = ('#define ucslen(x) wcslen((signed long *) x)\n'
               '#define ucscpy(x,y) (UTF32 *)wcscpy((signed long *)x,(signed long *)y)\n'
               '#define ucscat(x,y) (UTF32 *)wcscat((signed long *)x,(signed long *)y)\n'
               '#define ucschr(x,y) (UTF32 *)wcschr((signed long *)x,(signed long)y)\n'
               '#define ucsrchr(x,y) (UTF32 *)wcsrchr((signed long *)x,(signed long)y)\n')
        replace_in_file(self, path, old, '')
        replace_in_file(self, path, '#include "exitcode.h"',
                        '#include "exitcode.h"\n#include "utf32_ops.h"')
        replace_in_file(self, path,
                        '      ChineseToInt(Result,NormalizeChineseNumbers(s));',
                        '''      {
        UTF32 *normalized = NormalizeChineseNumbers(s);
        if (normalized == NULL) {
          uninum_err = NS_ERROR_OUTOFMEMORY;
          SetRvalZero(rvalp, ReturnType);
          return;
        }
        ChineseToInt(Result,normalized);
        free(normalized);
      }''')

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append('--disable-allocaok')
        env = tc.environment()
        if self.settings.os == 'OHOS':
            env.define('CONFIG_SHELL', '/bin/sh')
            env.define('SHELL', '/bin/sh')
            env.define('LD', 'ld.lld')
            env.define('AR', 'llvm-ar')
            env.define('RANLIB', 'llvm-ranlib')
            env.define('NM', 'llvm-nm')
            env.define('STRIP', 'llvm-strip')
        env.prepend_path('LD_LIBRARY_PATH', self.dependencies['gmp'].cpp_info.libdirs)
        tc.generate(env)
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        environment = Environment()
        if self.settings.os == 'OHOS':
            # The shipped config.status creates 0700 confstat directories.
            # HMDFS can reject their contents even for the creating process;
            # mktemp -d retains that mode regardless of the caller's umask.
            configure_path = os.path.join(self.source_folder, 'configure')
            replacements = (
                ('tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null` &&',
                 'tmp="${TMPDIR:-.}/confstat$$-$RANDOM"; (umask 007 && mkdir "$tmp") &&'),
                ('tmp=./confstat$$-$RANDOM',
                 'tmp="${TMPDIR:-.}/confstat$$-$RANDOM"'),
                ('(umask 077 && mkdir $tmp)', '(umask 007 && mkdir "$tmp")'),
            )
            for original, replacement in replacements:
                replace_in_file(self, configure_path, original, replacement, strict=True)
            scratch = Path(self.build_folder, '.autoconf-tmp')
            previous_umask = os.umask(0o007)
            try:
                scratch.mkdir(mode=0o770, exist_ok=False)
            finally:
                os.umask(previous_umask)
            environment.define('TMPDIR', str(scratch))
        if self.settings.os == 'OHOS' and can_run(self):
            # Native config.guess uses the actual compiler, not invented --host/--build flags.
            cc = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict).get('c')
            if not cc:
                raise ConanException('configured C compiler is required')
            output = io.StringIO()
            self.run(shlex.quote(cc) + ' -dumpmachine', stdout=output)
            triplet = output.getvalue().strip()
            if not re.fullmatch(r'aarch64-[A-Za-z0-9_-]*linux-ohos', triplet):
                raise ConanException('unexpected native compiler tuple: ' + triplet)
            guess = Path(self.source_folder, 'config.guess')
            if not guess.is_file() or guess.is_symlink():
                raise ConanException('config.guess is not an ordinary file')
            original = guess.read_bytes()
            backup = Path(self.build_folder, 'config.guess.original')
            if backup.exists():
                raise ConanException('native config.guess backup already exists')
            with backup.open('xb') as stream:
                stream.write(original)
            if backup.read_bytes() != original:
                raise ConanException('config.guess backup verification failed')
            save(self, str(guess), '#!/bin/sh\nprintf "%s\\n" ' + shlex.quote(triplet) + '\n')
        args = load_toolchain_args(self.generators_folder)['configure_args']
        # Profile buildenv can override the toolchain's shell after activation.
        # The OHOS native POSIX shell was tested; do not assume an HNP Bash path.
        configure = ('CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh ./configure '
                     if self.settings.os == 'OHOS' else 'sh ./configure ')
        with environment.vars(self).apply():
            self.run(configure + args)
            autotools = Autotools(self)
            autotools.make(args=['-j1'])
            autotools.make(args=['check'])
            if can_run(self) and self.settings.os in ('Linux','OHOS'):
                self._upstream()

    def _upstream(self):
        cc = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict).get('c', 'cc')
        tcl = self.dependencies.build['tcl']
        gmp = self.dependencies['gmp']
        tclshs = sorted(glob.glob(os.path.join(tcl.package_folder, 'bin', 'tclsh*')))
        tcllibs = sorted(glob.glob(os.path.join(tcl.cpp_info.libdirs[0], 'libtcl*.so')))
        if not tclshs or not tcllibs:
            raise ConanException('published Tcl runtime is incomplete')
        src = Path(self.source_folder)
        run_dir = Path(self.build_folder, 'upstream-tcl')
        run_dir.mkdir()
        output = run_dir / 'tcl_uninum.so'
        include = ' '.join('-I' + shlex.quote(x) for x in [str(src), *tcl.cpp_info.includedirs, *gmp.cpp_info.includedirs])
        self.run(shlex.quote(cc) + ' -shared -fPIC -std=gnu99 -DHAVE_CONFIG_H ' + include +
                 ' uninum.c tcl_uninum_wrap.c -o ' + shlex.quote(str(output)) +
                 ' -L' + shlex.quote(gmp.cpp_info.libdirs[0]) + ' -lgmp -lm')
        command = ' '.join(map(shlex.quote, [sys.executable, os.path.join(self.export_sources_folder, 'upstream.py'),
                     str(src), str(run_dir), tclshs[0], tcllibs[0], str(output)]))
        self.run(command)

    def package(self):
        Autotools(self).install()
        for pattern in ('lib/*.la','bin/NumberConverter.tcl'):
            for path in glob.glob(os.path.join(self.package_folder, pattern)):
                os.remove(path)
        for name in ('COPYING','AUTHORS'):
            copy(self, name, src=self.source_folder, dst=os.path.join(self.package_folder, 'licenses'))

    def package_info(self):
        self.cpp_info.libs = ['uninum']
        self.cpp_info.requires = ['gmp::gmp']
        if self.settings.os in ('Linux','OHOS'):
            self.cpp_info.system_libs = ['m']
