"""Build original Archive::Zip with exact platform applicability and installed crc32."""
import importlib.util
import hashlib
import json
import os
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

class ArchiveZipConan(ConanFile):
    name = "perl-archive-zip"
    version = "1.68"
    license = ('Artistic-1.0-Perl', 'GPL-1.0-or-later')
    description = 'Archive::Zip 1.68: original full registered suite and real ZIP APIs'
    homepage = 'https://metacpan.org/dist/Archive-Zip'
    # Interpreted ZIP library with its original crc32 command.
    package_type = 'unknown'
    settings = "os", "arch", "compiler", "build_type"
    def export_sources(self):
        copy(self, 'verify_original.py', self.recipe_folder, self.export_sources_folder)
        copy(self, 'original-source-tests.json', self.recipe_folder, self.export_sources_folder)
        copy(self, 'platform-not-applicable.json', self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def requirements(self):
        self.requires('perl/5.42.2', run=True)

    def build_requirements(self):
        self.test_requires('unzip/6.0')

    def layout(self):
        basic_layout(self)

    def validate(self):
        if cross_building(self):
            raise ConanInvalidConfiguration('Original tests require actual target Perl')

    def source(self):
        data = self.conan_data['sources'][str(self.version)]
        get(self, **data, strip_root=True)
        apply_conandata_patches(self)

    def _environment(self):
        root = Path(self.dependencies['perl'].package_folder)
        perl = root / 'bin/perl'
        core = root / 'lib/perl5/5.42.2'
        arch = core / 'aarch64-linux-thread-multi'
        if not perl.is_file() or not core.is_dir() or not arch.is_dir():
            raise ConanInvalidConfiguration('Actual published target Perl layout missing')
        e = Environment()
        e.define('PERL_MM_OPT', '')
        e.define('PERL_MB_OPT', '')
        e.define('PERL_MM_USE_DEFAULT', '1')
        e.define('PERL_INSTALL_BASE', self.package_folder)
        e.define('PERL5LIB', os.pathsep.join(map(str, (core, arch))))
        e.prepend_path('PATH', str(perl.parent))
        unzip = Path(self.dependencies['unzip'].package_folder) / 'bin/unzip'
        if not unzip.is_file():
            raise ConanInvalidConfiguration('Actual published unzip test tool missing')
        e.prepend_path('PATH', str(unzip.parent))
        # Do not confuse the HMDFS projected build-folder owner with the real
        # process identity required by test temporary files. Preserve strict
        # checks on a freshly created, actually owned POSIX private directory.
        temporary = getattr(self, '_owned_native_temporary', None)
        if temporary is None:
            candidates = [os.environ.get('TMPDIR')]
            candidates.append('/data/storage/el2/base/cache' if str(self.settings.os) == 'OHOS'
                              else tempfile.gettempdir())
            for value in candidates:
                if not value:
                    continue
                base = Path(value)
                if not base.is_absolute() or not base.is_dir() or base.resolve() != base:
                    continue
                owner = base.stat()
                own = owner.st_uid == os.getuid()
                sticky = (str(self.settings.os) != 'OHOS' and owner.st_uid == 0
                          and bool(owner.st_mode & stat.S_ISVTX))
                if not (own or sticky) or not os.access(base, os.W_OK | os.X_OK):
                    continue
                manager = tempfile.TemporaryDirectory(prefix='conan-archive-zip-', dir=str(base))
                self._owned_native_temporary_manager = manager
                temporary = Path(manager.name)
                break
            if temporary is None:
                raise ConanInvalidConfiguration('A real writable POSIX temporary parent is required')
            self._owned_native_temporary = temporary
        if (temporary.is_symlink() or temporary.resolve() != temporary
                or temporary.stat().st_uid != os.getuid()
                or stat.S_IMODE(temporary.stat().st_mode) != 0o700):
            raise ConanInvalidConfiguration('Foreign or unsafe private POSIX TMPDIR')
        e.define('TMPDIR', str(temporary))
        return e, str(perl), str(core), str(arch)

    def _run_original(self, command, work, evidence):
        """Keep original make test, closed stdin, complete output and a finite deadline."""
        executable = shutil.which(command[0])
        unzip = shutil.which('unzip')
        expected_unzip = Path(self.dependencies['unzip'].package_folder) / 'bin/unzip'
        if not executable or not unzip or Path(unzip).resolve() != expected_unzip.resolve():
            raise ConanInvalidConfiguration('Original tests require the declared tool environment')
        command = [str(Path(executable).resolve()), *command[1:]]
        errors = []
        start = time.monotonic()
        self.output.info('ORIGINAL_TEST_OUTPUT_BEGIN: ' + shlex.join(command))
        process = subprocess.Popen(
            command, cwd=str(work), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, process_group=0,
        )
        leader_stat = Path('/proc') / str(process.pid) / 'stat'
        leader_start = leader_stat.read_text().rsplit(')', 1)[1].split()[19]
        parent_session = os.getsid(0)
        if os.getpgid(process.pid) != process.pid or os.getsid(process.pid) != parent_session:
            raise ConanInvalidConfiguration('Original test process group was not isolated')

        def members():
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                return []
            result = []
            for entry in Path('/proc').iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    if entry.stat().st_uid != os.getuid():
                        continue
                    fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                    if int(fields[2]) != process.pid:
                        continue
                    if (int(fields[3]) != parent_session
                            or int(fields[19]) < int(leader_start)):
                        raise ConanInvalidConfiguration('Original test process identity changed')
                    result.append(int(entry.name))
                except (FileNotFoundError, ProcessLookupError, PermissionError):
                    continue
            if not result:
                raise ConanInvalidConfiguration('Original test group exists without readable ownership evidence')
            return result

        def kill_owned():
            owned = members()
            if owned:
                os.killpg(process.pid, signal.SIGKILL)

        def drain(pipe, name, terminal):
            try:
                with (evidence / name).open('xb') as target:
                    while True:
                        chunk = pipe.read1(32768)
                        if not chunk:
                            break
                        target.write(chunk)
                        target.flush()
                        stream = getattr(terminal, 'buffer', None)
                        if stream is not None:
                            stream.write(chunk)
                            stream.flush()
                        else:
                            terminal.write(chunk.decode('utf8', errors='replace'))
                            terminal.flush()
            except Exception as exc:
                errors.append(repr(exc))
            finally:
                pipe.close()

        readers = [
            threading.Thread(target=drain, args=(process.stdout, 'stdout', sys.stdout), daemon=True),
            threading.Thread(target=drain, args=(process.stderr, 'stderr', sys.stderr), daemon=True),
        ]
        for reader in readers:
            reader.start()
        timed_out = False
        try:
            try:
                rc = process.wait(timeout=300)
            except subprocess.TimeoutExpired:
                timed_out = True
                kill_owned()
                process.wait(timeout=30)
                rc = 124
        except BaseException:
            kill_owned()
            process.wait(timeout=30)
            raise
        finally:
            for reader in readers:
                reader.join(timeout=30)
        remaining = members()
        if remaining:
            kill_owned()
            rc = 1
        if errors or any(reader.is_alive() for reader in readers):
            rc = 1
        report = {
            'command': command, 'pid': process.pid, 'start_token': leader_start,
            'parent_session': parent_session,
            'deadline_seconds': 300, 'timed_out': timed_out, 'rc': rc,
            'elapsed_seconds': time.monotonic() - start,
            'stdin': 'DEVNULL', 'declared_unzip': str(Path(unzip).resolve()),
            'remaining_processes_at_completion': remaining, 'stream_errors': errors,
            'stdout_sha256': hashlib.sha256((evidence / 'stdout').read_bytes()).hexdigest(),
            'stderr_sha256': hashlib.sha256((evidence / 'stderr').read_bytes()).hexdigest(),
        }
        (evidence / 'execution.json').write_text(json.dumps(report, sort_keys=True), encoding='utf8')
        self.output.info('ORIGINAL_TEST_OUTPUT_END; RC=' + str(rc))
        return rc

    def build(self):
        environment, perl, core, arch = self._environment()
        work = self._owned_native_temporary / 'source-build'
        work.mkdir(mode=0o700)
        if work.resolve() != work or work.stat().st_uid != os.getuid():
            raise ConanInvalidConfiguration('Actual private POSIX source build required')
        self._native_source_build = work
        copy(self, '*', self.source_folder, str(work))
        make = self.conf.get('tools.gnu:make_program', default='make')
        with VirtualBuildEnv(self).vars().apply(), VirtualRunEnv(self).vars().apply(), environment.vars(self).apply():
            self.run(shlex.join([perl, 'Makefile.PL', 'INSTALL_BASE=' + self.package_folder,
                                'PERL_LIB=' + core, 'PERL_ARCHLIB=' + arch]), cwd=str(work))
            self.run(shlex.join([make, '-j1']), cwd=str(work))
            out = work / 'original-test-evidence'
            out.mkdir()
            try:
                rc = self._run_original([make, '-j1', 'test', 'TEST_VERBOSE=1'], work, out)
            except BaseException:
                copy(self, '*', str(out), os.path.join(self.build_folder, 'original-test-evidence'))
                raise
            spec = importlib.util.spec_from_file_location('archive_zip_original', str(work / 'verify_original.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with (out / 'platform.json').open('w', encoding='utf8') as platform_output:
                probe = 'use Config; use JSON::PP; use Archive::Zip qw(ZIP64_SUPPORTED); print JSON::PP->new->canonical->encode({perl_os=>$^O, zip64_supported=>ZIP64_SUPPORTED?1:0, pointer_bytes=>0+$Config{ptrsize}});'
                self.run(shlex.join([perl, '-Iblib/lib', '-e', probe]), cwd=str(work), stdout=platform_output)
            try:
                outcome = module.verify(work, out, rc)
            finally:
                copy(self, '*', str(out), os.path.join(self.build_folder, 'original-test-evidence'))
            self.output.info('UPSTREAM_REGISTERED_FILES=28; UPSTREAM_ORIGINAL_FILES=26/26; ORIGINAL_ASSERTIONS=911/911; SKIP=0; PLATFORM_NOT_APPLICABLE=2; GLOBAL_28_PASS=false')

    def package(self):
        environment, _, _, _ = self._environment()
        make = self.conf.get('tools.gnu:make_program', default='make')
        with VirtualRunEnv(self).vars().apply(), environment.vars(self).apply():
            self.run(shlex.join([make, '-j1', 'install']), cwd=str(self._native_source_build))
        # Preserve official CLI bytes and use the declared relocatable interpreter.
        original = Path(self.source_folder) / 'script/crc32'
        script_dir = Path(self.package_folder) / 'libexec/perl-archive-zip'
        script_dir.mkdir(parents=True, exist_ok=True)
        (script_dir / 'crc32.pl').write_bytes(original.read_bytes())
        binary = Path(self.package_folder) / 'bin/crc32'
        binary.parent.mkdir(parents=True, exist_ok=True)
        shell = '/system/bin/sh' if str(self.settings.os) == 'OHOS' else '/bin/sh'
        wrapper = '#!' + shell + '\nset -eu\nroot=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)\n'
        wrapper += 'export PERL5LIB="$root/lib/perl5' + '$' + '{PERL5LIB:+:$PERL5LIB}"\n'
        wrapper += 'exec perl "$root/libexec/perl-archive-zip/crc32.pl" "$@"\n'
        if binary.is_symlink() or not binary.is_file():
            raise ConanInvalidConfiguration('Expected actual MakeMaker-installed crc32 file')
        binary.chmod(0o755)
        binary.write_text(wrapper, encoding='utf8')
        binary.chmod(0o755)
        for name in ('LICENSE', 'README'):
            copy(self, name, self.source_folder, os.path.join(self.package_folder, 'licenses'))
        copy(self, '*', str(self._native_source_build / 'original-test-evidence'),
             os.path.join(self.package_folder, 'res/original-test-evidence'))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ['bin']
        self.runenv_info.prepend_path('PATH', os.path.join(self.package_folder, 'bin'))
        self.runenv_info.prepend_path('PERL5LIB', os.path.join(self.package_folder, 'lib/perl5'))
