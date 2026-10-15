"""Production and intrusive regression builds are intentionally disjoint.

Current native upstream evidence still has genuine NSS/cross-UID failures.
By default any skipped/failed original test blocks packaging. An explicit,
task-scoped capability configuration can continue only the exact demonstrated
NSS/privilege limits while preserving failed/skipped and upstream passed=false.
"""
import os,shlex,sys,shutil,struct,subprocess,hashlib,json,re
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get,apply_conandata_patches,copy,export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson,MesonToolchain
from conan.tools.layout import basic_layout

def configured_archiver(tools):
    """Resolve the configured compiler's real archiver, not a guessed PATH name."""
    explicit=tools.get('ar')
    if explicit:
        candidates=[explicit]
    else:
        cc=tools.get('c')
        compiler=shutil.which(str(cc)) if cc else None
        if not compiler:
            raise ConanInvalidConfiguration('Configured C compiler is not executable')
        reported=subprocess.run([compiler,'-print-prog-name=llvm-ar'],capture_output=True,
                                text=True,check=True,timeout=15).stdout.strip()
        candidates=[reported,str(Path(compiler).resolve().parent/'llvm-ar'),
                    str(Path(compiler).absolute().parent/'llvm-ar'),'llvm-ar']
    for candidate in candidates:
        if not candidate:continue
        executable=shutil.which(str(candidate))
        if executable and Path(executable).is_file() and os.access(executable,os.X_OK):
            subprocess.run([executable,'--version'],capture_output=True,check=True,timeout=15)
            return str(Path(executable).resolve())
    raise ConanInvalidConfiguration('Configured compiler has no executable LLVM archiver; explicit ar required')

class DbusConan(ConanFile):
    name = 'dbus'
    version = '1.16.2.1'
    description='D-Bus IPC library and daemon with real numeric-UID admission'
    license='AFL-2.1 OR GPL-2.0-or-later'
    homepage='https://www.freedesktop.org/wiki/Software/dbus/'
    url='https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos'
    package_type='static-library'
    settings = "os", "arch", "compiler", "build_type"
    # Original intrusive tests link/run GLib on the host. It is not part of
    # production libdbus's public ABI or transitive consumer requirements.
    test_requires='glib/2.84.0.1'
    exports_sources='native_upstream.py','exec_wrapper.c','test_package/harmony_tests/private_socket_root.py'
    def export_sources(self):export_conandata_patches(self)
    def configure(self):
        self.settings.rm_safe('compiler.cppstd')
        self.settings.rm_safe('compiler.libcxx')
    def requirements(self):
        self.requires('expat/2.8.2.1')
    def layout(self):basic_layout(self)
    def source(self):
        entry=self.conan_data['sources'][self.version]
        get(self,url=entry['url'],sha256=entry['sha256'],filename='dbus-1.16.2.tar.xz',strip_root=True)
    def generate(self):
        PkgConfigDeps(self).generate()
        # The published GLib provider contains this original Unix header module,
        # but its Conan components do not generate a gio-unix pkg-config file.
        glib=Path(self.dependencies['glib'].package_folder)
        original=glib/'lib/pkgconfig/gio-unix-2.0.pc'
        if not original.is_file() or not (glib/'include/gio-unix-2.0').is_dir():
            raise ConanInvalidConfiguration('Actual published GLib gio-unix metadata/headers missing')
        text=original.read_text(encoding='utf-8')
        if len(re.findall(r'(?m)^prefix=.*$',text))!=1:
            raise ConanInvalidConfiguration('Ambiguous original gio-unix package prefix')
        relocated=re.sub(r'(?m)^prefix=.*$',lambda _: 'prefix='+glib.as_posix(),text)
        output=Path(self.generators_folder)/original.name
        if output.exists():raise ConanInvalidConfiguration('gio-unix metadata provider collision')
        output.write_text(relocated,encoding='utf-8')
        receipt={'original':str(original),'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
                 'relocated':str(output),'relocated_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                 'change':'actual package prefix only; original module/Requires/Cflags retained'}
        (output.parent/'gio-unix-metadata.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        tc=MesonToolchain(self)
        # MesonToolchain does not translate compiler_executables['ar'] itself.
        tools=self.conf.get('tools.build:compiler_executables',default={},check_type=dict)
        if tools.get('ar') or self.settings.os == 'OHOS':
            tc.ar=configured_archiver(tools)
            self.output.info('Configured LLVM archiver: '+tc.ar)
        tc.project_options.update({'default_library':'static','libdir':'lib',
            'intrusive_tests':False,'modular_tests':'disabled','installed_tests':False,
            'checks':True,'asserts':True,'message_bus':True,'tools':True,
            'traditional_activation':True})
        # The signed native close_range control in this OHOS execution domain
        # terminated by SIGSYS. Do not infer runtime permission from headers.
        # One build option governs both libc and upstream raw-syscall paths.
        if self.settings.os == 'OHOS':
            tc.project_options['close_range']='disabled'
        for name in ('doxygen_docs','ducktype_docs','xml_docs','qt_help','x11_autolaunch',
                     'systemd','selinux','apparmor','libaudit','launchd','valgrind'):
            tc.project_options[name]='disabled'
        tc.generate()
    def build(self):
        apply_conandata_patches(self)
        # Native workers can exhaust their process limit with Meson's CPU default.
        # Use Conan's supported jobs configuration for this recipe's build.
        self.conf.define("tools.build:jobs", 1)
        meson=Meson(self);meson.configure();meson.build()
        if cross_building(self):
            raise ConanInvalidConfiguration('Original full upstream tests require actual target execution; cross compilation is not PASS')
        sys.path.insert(0,self.source_folder)
        from native_upstream import execute_original_upstream
        execute_original_upstream(self)
    def package(self):
        # Never install the intrusive test build: it contains deliberately
        # insecure hooks that must not be distributed as production libdbus.
        Meson(self).install(cli_args=["--no-rebuild"])
        if self.settings.os=='OHOS':
            tools={name:shutil.which(name) for name in ('binary-sign-tool','llvm-readelf','llvm-objcopy')}
            if not all(tools.values()):raise ConanInvalidConfiguration('Actual package signing tool closure required')
            clean=dict(os.environ);clean.pop('LD_LIBRARY_PATH',None)
            package=Path(self.package_folder).resolve()
            for path in sorted(package.rglob('*')):
                if not path.is_file() or path.is_symlink():continue
                with path.open('rb') as stream:header=stream.read(20)
                if len(header)<20 or header[:4]!=b'\x7fELF' or struct.unpack_from('<H',header,16)[0] not in (2,3):continue
                if not path.resolve().is_relative_to(package):raise ConanInvalidConfiguration('Foreign installed ELF')
                if b'.codesign' in subprocess.check_output([tools['llvm-readelf'],'-S',path],env=clean):
                    subprocess.run([tools['llvm-objcopy'],'--remove-section','.codesign',path],env=clean,check=True)
                signed=Path(str(path)+'.signed')
                if signed.exists():raise ConanInvalidConfiguration('Signing output already exists')
                subprocess.run([tools['binary-sign-tool'],'sign','-inFile',path,'-outFile',signed,'-selfSign','1'],env=clean,check=True)
                if b'.codesign' not in subprocess.check_output([tools['llvm-readelf'],'-S',signed],env=clean):
                    raise ConanInvalidConfiguration('Installed ELF signature missing')
                os.replace(signed,path);path.chmod(0o755)
        copy(self,'COPYING',self.source_folder,os.path.join(self.package_folder,'licenses'))
        copy(self,'upstream-summary.json',self.build_folder,os.path.join(self.package_folder,'res/testing'))
    def package_info(self):
        self.cpp_info.libs=['dbus-1']
        self.cpp_info.includedirs=['include/dbus-1.0','lib/dbus-1.0/include']
        self.cpp_info.libdirs=['lib']
        self.cpp_info.requires=['expat::expat']
        self.cpp_info.set_property('cmake_file_name','DBus1')
        self.cpp_info.set_property('cmake_target_name','DBus1::DBus1')
        self.cpp_info.set_property('pkg_config_name','dbus-1')
        if self.settings.os in ('Linux','OHOS'):self.cpp_info.system_libs=['pthread']
