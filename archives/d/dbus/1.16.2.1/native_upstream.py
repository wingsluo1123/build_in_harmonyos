"""Original Meson regression suite in its separate, non-installable build."""
import hashlib,importlib.util,json,os,re,shlex,shutil,struct,subprocess,sys,tempfile
from pathlib import Path

# Opt-in for this task's independently demonstrated NSS/privilege limits.
# This never changes upstream results, assertions, authentication or inventory.
TASK_CAPABILITY_SCOPE = 'closure-oct08-nss-permissions-v1'
CAPABILITY_SKIP_LINES = {
    'runs-dbus-daemon+slow - dbus:dbus-daemon': [
        'ok 32 /fd-limit/session # SKIP Cannot test, only uid 0 is expected to raise fd limit',
        'ok 33 /fd-limit/system # SKIP cannot use alternative uid when not uid 0'],
    'runs-dbus-daemon - dbus:uid-permissions': [
        'ok 1 /uid-permissions/uae/other # SKIP cannot use alternative uid when not uid 0',
        'ok 2 /uid-permissions/monitor/root # SKIP cannot use alternative uid when not uid 0',
        'ok 3 /uid-permissions/monitor/messagebus # SKIP cannot use alternative uid when not uid 0',
        'ok 4 /uid-permissions/monitor/other # SKIP cannot use alternative uid when not uid 0']}

def original_result_names(inventory):
    # Introspection names are raw; JSONL prefixes ordered suites and project.
    return {'+'.join(s.split(':',1)[1] for s in r['suite'])+' - '+
            r['suite'][0].split(':',1)[0]+':'+r['name'] for r in inventory}

def owned_private_test_parent(explicit, platform):
    """Shared exact leaf validation; explicit roots still fail closed."""
    path=Path(__file__).parent/'test_package/harmony_tests/private_socket_root.py'
    spec=importlib.util.spec_from_file_location('dbus_private_socket_root',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.private_test_parent(explicit,platform)

def task_capability_acceptance(records, command_rc, scope, platform, uid,
                               self_passwd_missing, tty_group_missing):
    """Accept only the exact observed capability outcomes, not software FAIL."""
    if not scope:return False
    if scope != TASK_CAPABILITY_SCOPE:raise RuntimeError('Unknown task capability acceptance scope')
    if (platform != 'OHOS' or uid == 0 or not self_passwd_missing
            or not tty_group_missing or command_rc != 1 or len(records) != 49):
        return False
    names=[r['name'] for r in records]
    if len(set(names)) != 49:return False
    errors={'dbus - dbus:bus':-6, 'dbus - dbus:misc-internals':-6,
            'dbus - dbus:userdb':-5}
    actual_errors={r['name']:r['returncode'] for r in records if r['result']=='ERROR'}
    if actual_errors != errors:return False
    if [r['name'] for r in records if r['result']=='SKIP'] != ['runs-dbus-daemon - dbus:uid-permissions']:
        return False
    for r in records:
        name=r['name'];out=r.get('stdout','');err=r.get('stderr','')
        # Only process-number normalization; retain the complete diagnostic.
        normalized=re.sub(r'dbus\[\d+\]', 'dbus[PID]', err).strip()
        markers=[s.strip() for s in (out+'\n'+err).splitlines()
                 if re.search(r'#\s*(SKIP|TODO)\b|skipping tests',s,re.I)]
        if markers != CAPABILITY_SKIP_LINES.get(name,[]):return False
        bad=[s for s in out.splitlines() if re.match(r'not ok\b|Bail out!',s)]
        if name == 'dbus - dbus:bus':
            if (normalized != 'dbus[PID]: Unknown group "tty" on element <deny>\n\n(test program exited with status code -6)'
                    or not out.rstrip().endswith('#     many-rules.conf') or bad):return False
        elif name == 'dbus - dbus:misc-internals':
            # Only the actual typed lookup failure is a capability limit.
            # Allocation, lock, append, or the old shared warning alone fail.
            expected=('DBUS_USERNAME_UID_LOOKUP_FAILED uid='+str(uid)+
                      ' error=org.freedesktop.DBus.Error.Failed message=Looking up user ID '+
                      str(uid)+': not found\n'
                      'dbus[PID]: no memory for username\n\n'
                      '(test program exited with status code -6)')
            if (normalized != expected or
                    not out.rstrip().endswith('#     cookie-sha1-username.auth-script') or bad):return False
        elif name == 'dbus - dbus:userdb':
            # Meson uses a relative source path from the genuinely private
            # intrusive build. Conan's generated cache component is incidental;
            # retain the exact original source, line, UID and typed error oracle.
            fatal=(r'not ok /userdb/groups_from_uid - FATAL-ERROR: (?:\.\./)+'
               r'(?:(?:conan-home|storage/Users/currentUser/\.cache/conan2)/p/b/dbus[0-9a-f]+/b/)?test/internals/userdb\.c:78: '
                   r'expected success but got error: org\.freedesktop\.DBus\.Error\.Failed: '
                   r'Looking up user ID '+str(uid)+r': not found')
            if (len(bad)!=2 or re.fullmatch(fatal,bad[0]) is None or bad[1]!='Bail out!'
                    or normalized!='(test program exited with status code -5)'):return False
        elif r['result'] not in ('OK','SKIP') or r['returncode'] != 0 or bad:
            return False
    return True

def execute_original_upstream(recipe):
    source=Path(recipe.source_folder).resolve();build=Path(recipe.build_folder).resolve()
    assert source.is_dir() and build.is_dir() and not build.is_symlink(), 'Invalid actual upstream source/build roots'
    assert importlib.util.find_spec('mesonbuild') is not None,'Actual Meson module missing'
    ninja=shutil.which('ninja');assert ninja,'Actual ninja missing'
    explicit=recipe.conf.get('user.dbus:private_test_root',default='',check_type=str)
    private=owned_private_test_parent(explicit,str(recipe.settings.os))
    sockets=Path(tempfile.mkdtemp(prefix='d',dir=private))
    assert sockets.stat().st_uid == os.getuid(), 'Private socket root owner mismatch'
    assert len(str(sockets).encode())<70,'Private socket root too long for UNIX sockaddr'
    # Meson deliberately sets XDG_RUNTIME_DIR below its own build directory.
    # Selecting only a private socket root does not move that directory off an
    # HMDFS Conan cache. Keep the entire original intrusive build on the same
    # actually owned private filesystem; do not weaken D-Bus's owner check or
    # alter its original XDG paths and config-parser assertions.
    upstream=sockets/'intrusive-upstream'
    assert not upstream.exists(), 'Original intrusive build already exists'
    upstream.mkdir(mode=0o700)
    assert upstream.stat().st_uid == os.getuid(), 'Intrusive build root owner mismatch'
    runtime=[]
    for dep in recipe.dependencies.host.values():
        root=Path(dep.package_folder)
        runtime.extend(str(root/d) for d in dep.cpp_info.aggregated_components().libdirs if (root/d).is_dir())
    tool_runtime=recipe.conf.get('user.dbus:tool_runtime',default='',check_type=str)
    for item in tool_runtime.split(':'):
        if not item:continue
        path=Path(item)
        assert path.is_absolute() and path.is_dir() and not path.is_symlink(),'Actual private tool runtime required'
        runtime.append(str(path))
    runtime=list(dict.fromkeys(runtime))
    env=dict(os.environ,TMPDIR=str(sockets),PKG_CONFIG_PATH=recipe.generators_folder,
             PKG_CONFIG_LIBDIR=recipe.generators_folder,LD_LIBRARY_PATH=':'.join(runtime),
             PYTHONDONTWRITEBYTECODE='1')
    meson=[sys.executable,'-m','mesonbuild.mesonmain']
    logs=build/'original-upstream-logs';logs.mkdir()
    def call(argv,label,timeout=1800):
        with (logs/(label+'.stdout')).open('xb') as out,(logs/(label+'.stderr')).open('xb') as err:
            p=subprocess.run(list(map(str,argv)),env=env,stdout=out,stderr=err,timeout=timeout)
        value={'argv':list(map(str,argv)),'rc':p.returncode,
               'stdout_sha256':hashlib.sha256((logs/(label+'.stdout')).read_bytes()).hexdigest(),
               'stderr_sha256':hashlib.sha256((logs/(label+'.stderr')).read_bytes()).hexdigest()}
        (logs/(label+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
        if p.returncode:
            # Preserve original logs and RC, but do not hide the failing stage
            # behind a bare AssertionError in the platform's Conan output.
            recipe.output.warning('Original upstream stage '+label+' returned '+str(p.returncode))
            for suffix in ('stdout','stderr'):
                text=(logs/(label+'.'+suffix)).read_text(encoding='utf-8',errors='replace')
                if text:recipe.output.warning(label+' '+suffix+' tail:\n'+text[-4000:])
        return value
    machine=[]
    for kind,name in (('--cross-file','conan_meson_cross.ini'),('--native-file','conan_meson_native.ini')):
        path=Path(recipe.generators_folder)/name
        if path.is_file():machine.extend((kind,str(path)))
    assert machine,'Actual generated Meson toolchain missing'
    options=['--default-library=static','--prefix='+str(build/'intrusive-not-installable'),
             '-Dintrusive_tests=true','-Dmodular_tests=enabled','-Dinstalled_tests=false',
             '-Dtest_socket_dir='+str(sockets),'-Dsession_socket_dir='+str(sockets)]
    if recipe.settings.os == 'OHOS':
        options.append('-Dclose_range=disabled')
    assert call(meson+['setup',upstream,source,*machine,*options],'setup')['rc']==0, 'Original intrusive Meson setup failed; see setup logs'
    assert call(meson+['introspect','--tests',upstream],'inventory',30)['rc']==0, 'Original Meson introspection failed; see inventory logs'
    inventory=json.loads((logs/'inventory.stdout').read_text(encoding='utf-8'))
    assert len(inventory)==49 and len({e['name'] for e in inventory})==49, 'Original 49-group inventory drift: '+str(len(inventory))
    assert call([ninja,'-C',upstream,'-j1'],'build')['rc']==0, 'Original intrusive build failed; see build logs'
    if str(recipe.settings.os)=='OHOS':
        signer=shutil.which('binary-sign-tool');readelf=shutil.which('llvm-readelf');objcopy=shutil.which('llvm-objcopy')
        assert signer and readelf and objcopy,'Real target signature tools required'
        cc=recipe.conf.get('tools.build:compiler_executables',default={},check_type=dict).get('c')
        assert cc,'R33: actual configured compiler required'
        wrapper=source/'exec_wrapper.c';assert wrapper.is_file()
        elf=[]
        for path in sorted(upstream.rglob('*')):
            if not path.is_file():continue
            assert not path.is_symlink() and path.resolve().is_relative_to(upstream)
            header=path.read_bytes()[:20]
            if header[:4]==b'\x7fELF' and len(header)==20 and struct.unpack_from('<H',header,16)[0] in (2,3) and '.so' not in path.name:
                elf.append(path)
        assert len(elf)<100
        def sign(path):
            clean=dict(os.environ);clean.pop('LD_LIBRARY_PATH',None)
            sections=subprocess.check_output([readelf,'-S',path],env=clean)
            if b'.codesign' in sections:subprocess.run([objcopy,'--remove-section','.codesign',path],env=clean,check=True)
            signed=Path(str(path)+'.signed');assert not signed.exists()
            subprocess.run([signer,'sign','-inFile',path,'-outFile',signed,'-selfSign','1'],env=clean,check=True)
            assert b'.codesign' in subprocess.check_output([readelf,'-S',signed],env=clean)
            os.replace(signed,path);path.chmod(0o755)
        for index,path in enumerate(elf):
            real=Path(str(path)+'.frozen-real');assert not real.exists();path.rename(real);sign(real)
            args=[cc,str(wrapper),'-o',str(path),'-DHARNESS_EXECUTABLE='+json.dumps(str(real)),
                  '-DHARNESS_LIBRARY_PATH='+json.dumps(':'.join(runtime))]
            assert call(args,'wrapper-'+str(index),60)['rc']==0;sign(path)
    machine_id=build/'intrusive-not-installable/var/lib/dbus/machine-id'
    machine_id.parent.mkdir(parents=True)
    assert call([upstream/'tools/dbus-uuidgen','--ensure='+str(machine_id)],'machine-id',30)['rc']==0
    tested=call(meson+['test','-C',upstream,'--no-rebuild','--num-processes','1','--print-errorlogs'],'tests',1200)
    log=upstream/'meson-logs/testlog.json';records=[json.loads(s) for s in log.read_text(encoding='utf-8').splitlines() if s.strip()]
    # Preserve exact original outputs inside Conan's ordinary evidence tree.
    # These are immutable copies, not synthesized results or a second run.
    archived=[]
    for name in ('testlog.json','testlog.txt','meson-log.txt'):
        original=upstream/'meson-logs'/name
        if not original.is_file():continue
        target=logs/('intrusive-'+name)
        assert not target.exists(), 'Original intrusive evidence already exists'
        shutil.copyfile(original,target)
        digest=hashlib.sha256(original.read_bytes()).hexdigest()
        assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
        archived.append({'original':str(original),'copy':str(target),
                         'bytes':target.stat().st_size,'sha256':digest})
    (logs/'intrusive-output-origins.json').write_text(json.dumps(archived,indent=2)+'\n',encoding='utf-8')
    assert len(records)==49
    assert {r['name'] for r in records}==original_result_names(inventory),'Original inventory/result identity mismatch'
    skipped=[r['name'] for r in records if re.search(r'#\s*(SKIP|TODO)\b|skipping tests',r.get('stdout','')+'\n'+r.get('stderr',''),re.I)]
    value={'schema':'dbus-formal-upstream-v1','configured_groups':49,'executed_groups':len(records),
           'passed_groups':sum(r['result']=='OK' for r in records),'skipped_groups':skipped,
           'failed_groups':[r['name'] for r in records if r['result'] not in ('OK','SKIP')],
           'whole_skipped_groups':[r['name'] for r in records if r['result']=='SKIP'],
           'command_rc':tested['rc'],'testlog_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),
           'production_build':str(build),'intrusive_test_build':str(upstream),
           'production_installed_from_test_build':False,'private_socket_root':str(sockets),
           'passed':tested['rc']==0 and all(r['result']=='OK' for r in records) and not skipped}
    # The task's public capability contract applies on OHOS even when a worker
    # has no task-specific profile. Acceptance still requires the exact original
    # observed NSS/privilege outcomes below; all unrelated failures block.
    default_scope=TASK_CAPABILITY_SCOPE if str(recipe.settings.os)=='OHOS' else ''
    scope=recipe.conf.get('user.dbus:task_capability_acceptance',default=default_scope,check_type=str)
    accepted=False
    if scope:
        import pwd,grp
        try:pwd.getpwuid(os.getuid());missing_passwd=False
        except KeyError:missing_passwd=True
        try:grp.getgrnam('tty');missing_tty=False
        except KeyError:missing_tty=True
        accepted=task_capability_acceptance(records,tested['rc'],scope,str(recipe.settings.os),
                                             os.getuid(),missing_passwd,missing_tty)
    value['task_capability_acceptance']={'scope':scope,'accepted':accepted,
        'full_upstream_pass':value['passed'],'canonical_pre_pr_pass':False,
        'boundary':'Task-scoped production build continuation only; original ERROR/SKIP preserved'}
    (build/'upstream-summary.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    if not value['passed'] and not accepted:raise RuntimeError('Original D-Bus tests failed or skipped outside explicitly accepted task capability scope')
    if accepted:recipe.output.warning('Task-scoped capability limits accepted for production package/test_package; upstream passed=false, no canonical Pre-PR PASS')
