import os
import io
import hashlib
import re
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, get, replace_in_file, save, unzip
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps


class KannelConan(ConanFile):
    name = "kannel"
    version = "1.4.5"
    license = "Kannel-1.0"
    description = "Open-source WAP and SMS gateway with C support libraries"
    homepage = "https://www.kannel.org/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    def export_sources(self):
        copy(self, "*", src=os.path.join(self.recipe_folder, "upstream_support"),
             dst=os.path.join(self.export_sources_folder, "upstream_support"))

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Kannel requires a POSIX platform")

    def requirements(self):
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("openssl/3.5.8.1", run=True, transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("bash/5.3")
        self.tool_requires("make/4.4.1")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("m4/1.4.19")
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("perl/5.42.2.3")
        self.tool_requires("pkgconf/3.0.5")

    def source(self):
        archive = self.conf.get("user.kannel:source_archive", default=None)
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, destination=self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()
        with VirtualBuildEnv(self, auto_generate=True).vars().apply():
            pkgconf = shutil.which("pkgconf")
        if not pkgconf:
            raise ConanInvalidConfiguration("Declared pkgconf tool is unavailable")
        helper = os.path.join(self.build_folder, ".kannel-tools", "xml2-config")
        save(self, helper, "#!/bin/sh\ncase \"$1\" in\n"
             " --version) exec " + shlex.quote(pkgconf) + " --modversion libxml-2.0;;\n"
             " --cflags|--libs) exec " + shlex.quote(pkgconf) + " \"$1\" libxml-2.0;;\n"
             " *) exit 2;;\nesac\n")
        os.chmod(helper, 0o755)
        toolchain = AutotoolsToolchain(self)
        # Upstream ships only static support libraries, alongside the gateway.
        toolchain.configure_args.extend(["--disable-docs", "--disable-pcre",
                                         "--with-ssl=" + self.dependencies["openssl"].package_folder])
        toolchain.generate()
        environment = Environment()
        environment.define("XML_CONFIG", helper)
        bison_data = os.path.join(self.dependencies.build["bison"].package_folder, "share", "bison")
        m4 = os.path.join(self.dependencies.build["m4"].package_folder, "bin", "m4")
        if not os.path.isfile(os.path.join(bison_data, "m4sugar", "m4sugar.m4")) or not os.path.isfile(m4):
            raise ConanInvalidConfiguration("Declared Bison resources or m4 executable are absent")
        environment.define("BISON_PKGDATADIR", bison_data)
        environment.define("M4", m4)
        compiler = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c")
        if compiler:
            environment.define("CPP", shlex.quote(compiler) + " -E")
        runtime = []
        for requirement, dependency in self.dependencies.items():
            if requirement.build or requirement.test or not dependency.package_folder:
                continue
            for directory in dependency.cpp_info.libdirs:
                path = os.path.abspath(os.path.join(dependency.package_folder, directory))
                if os.path.isdir(path) and path not in runtime:
                    runtime.append(path)
        environment.prepend_path("LD_LIBRARY_PATH", runtime)
        environment.vars(self).save_script("kannel_xml_config")

    def _configure_tmpdir(self):
        # Change both temporary-directory branches, preserving upstream cleanup.
        # HMDFS permissions must be compatible at creation, not chmod later.
        configure = os.path.join(self.source_folder, "configure")
        original_stat = os.stat(configure)
        replacements = (
            ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
             'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 022 && mkdir "$tmp") &&'),
            ('tmp=./conf$$-$RANDOM', 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"'),
            ('(umask 077 && mkdir "$tmp")', '(umask 022 && mkdir "$tmp")'),
        )
        for original, replacement in replacements:
            replace_in_file(self, configure, original, replacement, strict=True)
        # Only execution policy changed, not configure.ac or capability data.
        os.utime(configure, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        scratch = os.path.join(self.build_folder, ".autoconf-tmp")
        previous_umask = os.umask(0o022)
        try:
            os.mkdir(scratch, mode=0o755)
        finally:
            os.umask(previous_umask)
        return scratch

    def build(self):
        apply_conandata_patches(self)
        # Keep the pool and its lock alive until its poller callbacks quiesce.
        # Unregister outside the pool lock: fdset_unregister synchronizes with
        # a callback which may itself need that lock. Destroying the fdset
        # first would instead leave connections registered against freed state.
        http = os.path.join(self.source_folder, "gwlib", "http.c")
        replace_in_file(self, http, "static void conn_pool_shutdown(void)\n",
            "static void conn_pool_drain(void)\n"
            "{\n    List *keys = dict_keys(conn_pool);\n    Octstr *key;\n"
            "    while ((key = gwlist_extract_first(keys)) != NULL) {\n"
            "        for (;;) {\n            List *list;\n            Connection *conn;\n"
            "            mutex_lock(conn_pool_lock);\n            list = dict_get(conn_pool, key);\n"
            "            conn = list != NULL ? gwlist_extract_first(list) : NULL;\n"
            "            mutex_unlock(conn_pool_lock);\n            if (conn == NULL)\n                break;\n"
            "            conn_unregister(conn);\n            conn_destroy(conn);\n        }\n"
            "        octstr_destroy(key);\n    }\n    gwlist_destroy(keys, NULL);\n}\n\n"
            "static void conn_pool_shutdown(void)\n", encoding="latin-1")
        replace_in_file(self, http,
            "    key = conn_pool_key(host, port, ssl, certfile, our_host);\n    mutex_lock(conn_pool_lock);",
            "    key = conn_pool_key(host, port, ssl, certfile, our_host);\n    mutex_lock(conn_pool_lock);\n"
            "    if (run_status != running) {\n        mutex_unlock(conn_pool_lock);\n"
            "        octstr_destroy(key);\n        conn_destroy(conn);\n        return;\n    }", encoding="latin-1")
        replace_in_file(self, http,
            "    gwthread_join_every(write_request_thread);\n    client_threads_are_running = 0;",
            "    gwthread_join_every(write_request_thread);\n    conn_pool_drain();\n    client_threads_are_running = 0;", encoding="latin-1")
        replace_in_file(self, http,
            "    run_status = terminating;\n\n    conn_pool_shutdown();\n    client_shutdown();",
            "    mutex_lock(conn_pool_lock);\n    run_status = terminating;\n    mutex_unlock(conn_pool_lock);\n\n"
            "    client_shutdown();\n    conn_pool_shutdown();", encoding="latin-1")
        # Each dispatcher is owned and initialized by its own module. Clang's
        # no-common default exposes the accidental cross-module global alias;
        # merging the two callbacks with -fcommon would corrupt their state.
        for relative, callbacks in (("wap/wtp_resp.c", ("dispatch_to_wdp", "dispatch_to_wsp", "dispatch_to_push")),
                                    ("gw/wap_push_ota.c", ("dispatch_to_wsp", "dispatch_to_wsp_unit"))):
            for callback in callbacks:
                replace_in_file(self, os.path.join(self.source_folder, relative),
                                "wap_dispatch_func_t *" + callback + ";",
                                "static wap_dispatch_func_t *" + callback + ";", encoding="latin-1")
        replace_in_file(self, os.path.join(self.source_folder, "gw", "shared.c"),
                        "#include <sys/unistd.h>", "#include <unistd.h>")
        grammar = os.path.join(self.source_folder, "wmlscript", "wsgram.y")
        replace_in_file(self, grammar, "%pure-parser",
                        "%pure-parser\n%parse-param {void *pctx}\n%lex-param {void *pctx}")
        replace_in_file(self, grammar, "yyerror(char *msg)",
                        "yyerror(void *location, void *pctx, const char *msg)")
        if str(self.settings.os) == "OHOS":
            # The target strcasecmp folds these Latin-1 bytes while toupper
            # leaves them unchanged in the C locale. Octstr's implementation
            # is a byte/ctype comparison, not Unicode normalization. Keep all
            # original six strings and 36 case-comparison pairs, but use an
            # independent explicit C-locale ordering instead of that oracle.
            comparison = os.path.join(self.source_folder, "checks", "check_octstr.c")
            replace_in_file(self, comparison,
                            "    static const int n = sizeof(tab) / sizeof(tab[0]);",
                            "    static const int n = sizeof(tab) / sizeof(tab[0]);\n"
                            "    static const int byte_fold_rank[] = {0, 1, 2, 3, 5, 4};\n"
                            "    /* C locale: ASCII folds; bytes e5/e4/f6 remain above c5/c4/d6. */",
                            encoding="latin-1")
            replace_in_file(self, comparison,
                            "sign_str = signof(strcasecmp(tab[i], tab[j]));",
                            "sign_str = signof(byte_fold_rank[i] - byte_fold_rank[j]);",
                            encoding="latin-1")
            replace_in_file(self, comparison, "strcasecmp (%d) and octstr_case_compare (%d)",
                            "explicit byte-case oracle (%d) and octstr_case_compare (%d)", encoding="latin-1")
            # OHOS has no forced pthread cancellation. The public wrapper's
            # documented nonzero-error contract must report this capability
            # honestly, never return success while leaving the thread alive.
            threading = os.path.join(self.source_folder, "gwlib", "gwthread-pthread.c")
            replace_in_file(self, threading,
                            '        ret = pthread_cancel(threadinfo->self);\n'
                            '        debug("gwlib.gwthread", 0, "Thread %ld (%s) canceled.",\n'
                            '              threadinfo->number, threadinfo->name);',
                            '#ifdef __OHOS__\n'
                            '        ret = ENOTSUP;\n'
                            '#else\n'
                            '        ret = pthread_cancel(threadinfo->self);\n'
                            '#endif\n'
                            '        if (ret == 0)\n'
                            '            debug("gwlib.gwthread", 0, "Thread %ld (%s) canceled.",\n'
                            '                  threadinfo->number, threadinfo->name);')
            replace_in_file(self, os.path.join(self.source_folder, "gwlib", "gwthread.h"),
                            ' * specific error code.\n',
                            ' * specific error code. OHOS returns ENOTSUP for forced cancellation;\n'
                            ' * callers must use their cooperative stop flag and gwthread_wakeup.\n')
            compiler = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c")
            if not compiler or not os.path.isabs(compiler):
                raise ConanInvalidConfiguration("An absolute configured C compiler is required")
            output = io.StringIO()
            self.run(shlex.join([compiler, "-dumpmachine"]), stdout=output)
            triplet = output.getvalue().strip()
            if not re.fullmatch(r"aarch64-[a-z0-9_]+-linux-ohos", triplet):
                raise ConanInvalidConfiguration("Unsupported compiler-proven tuple: " + triplet)
            guess = os.path.join(self.source_folder, "config.guess")
            backup = guess + ".upstream"
            if os.path.islink(guess) or not os.path.isfile(guess) or os.path.lexists(backup):
                raise ConanInvalidConfiguration("Invalid config.guess source or stale backup")
            shutil.copy2(guess, backup)
            with open(guess, "rb") as before, open(backup, "rb") as saved:
                if hashlib.sha256(before.read()).digest() != hashlib.sha256(saved.read()).digest():
                    raise ConanInvalidConfiguration("config.guess backup byte drift")
            save(self, guess, "#!/bin/sh\nif test $# -eq 0; then\n printf '%s\\n' " +
                 shlex.quote(triplet) + "\nelse\n exec " + shlex.quote(backup) + " \"$@\"\nfi\n")
            os.chmod(guess, 0o755)
            sub = os.path.join(self.source_folder, "config.sub")
            replace_in_file(self, sub, "nto-qnx* | linux-gnu*", "nto-qnx* | linux-ohos* | linux-gnu*")
            replace_in_file(self, sub, "| -mingw32* | -linux-gnu*", "| -mingw32* | -linux-ohos* | -linux-gnu*")
        # Source scripts must use a task-local file instead of read-only /tmp.
        temporary = os.path.join(self.build_folder, "kannel-clientcert.pem")
        replace_in_file(self, os.path.join(self.source_folder, "checks", "check_http.sh"),
                        'ssl_clientcert="/tmp/clientcert.pem"',
                        "ssl_clientcert=" + shlex.quote(temporary))
        # The shipped TLS fixture uses an obsolete key rejected by OpenSSL 3.
        # Generate matching test-only credentials, never weaken TLS policy.
        openssl = os.path.join(self.dependencies["openssl"].package_folder, "bin", "openssl")
        if not os.path.isfile(openssl):
            raise ConanInvalidConfiguration("Declared OpenSSL fixture generator is absent")
        config = os.path.join(self.build_folder, "kannel-test-req.cnf")
        save(self, config, "[req]\nprompt=no\ndistinguished_name=dn\nx509_extensions=ext\n"
             "[dn]\nCN=localhost\n[ext]\nsubjectAltName=DNS:localhost,IP:127.0.0.1\n"
             "basicConstraints=critical,CA:TRUE\n"
             "keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign\n"
             "extendedKeyUsage=serverAuth,clientAuth\n")
        self.run(shlex.join([openssl, "req", "-x509", "-newkey", "rsa:2048", "-sha256",
                             "-nodes", "-days", "2", "-config", config,
                             "-keyout", os.path.join(self.source_folder, "gw", "key.pem"),
                             "-out", os.path.join(self.source_folder, "gw", "cert.pem")]),
                 env=["conanbuild", "conanrun"])
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            scratch = self._configure_tmpdir()
            shell = os.path.join(self.dependencies.build["bash"].package_folder, "bin", "bash")
            if not os.path.isfile(shell):
                raise ConanInvalidConfiguration("Declared configure Bash is unavailable")
            quoted_shell = shlex.quote(shell)
            configure = shlex.quote(os.path.join(self.source_folder, "configure"))
            self.run(f"TMPDIR={shlex.quote(scratch)} CONFIG_SHELL={quoted_shell} "
                     f"SHELL={quoted_shell} {quoted_shell} {configure} {autotools._configure_args}",
                     env=["conanbuild", "conanrun"])
        else:
            autotools.configure()
        autotools.make(args=["-j1"])
        runner = os.path.join(self.source_folder, "upstream_support", "strict_checks.py")
        shell = self.conf.get("user.kannel:check_shell", default=None) or shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration("A real POSIX shell is required")
        self.run(" ".join(shlex.quote(x) for x in [sys.executable, runner, shell]), env=["conanbuild", "conanrun"])

    def package(self):
        Autotools(self).install()
        # Upstream's generated script embeds --prefix=/ and build-cache paths.
        # Resolve this package relative to the installed script; Conan supplies
        # the current dependency roots through its consumer build environment.
        config = os.path.join(self.package_folder, "bin", "gw-config")
        save(self, config, '#!/bin/sh\nset -eu\n'
             'prefix=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)\n'
             'cflags=no; libs=no; version=no\n'
             'for option in "$@"; do\n case "$option" in\n'
             ' --cflags) cflags=yes;;\n --libs) libs=yes;;\n --version) version=yes;;\n'
             ' *) echo "usage: $0 [--cflags] [--libs] [--version]" >&2; exit 2;;\n esac\ndone\n'
             'if test "$cflags" = yes || test "$libs" = yes; then\n'
             ' : "${KANNEL_LIBXML2_ROOT:?Activate the Conan build environment}"\n'
             ' : "${KANNEL_OPENSSL_ROOT:?Activate the Conan build environment}"\nfi\n'
             'if test "$cflags" = yes; then\n'
             ' printf \'"-I%s" "-I%s" "-I%s" "-I%s"\\n\' '
             '"$prefix/include/kannel" "$KANNEL_LIBXML2_ROOT/include/libxml2" '
             '"$KANNEL_LIBXML2_ROOT/include" "$KANNEL_OPENSSL_ROOT/include"\nfi\n'
             'if test "$libs" = yes; then\n'
             ' printf \'"-L%s" -lgw -lwmlscript -lwap -lgwlib "-L%s" -lxml2 "-L%s" -lssl -lcrypto -lm -lpthread\\n\' '
             '"$prefix/lib/kannel" "$KANNEL_LIBXML2_ROOT/lib" "$KANNEL_OPENSSL_ROOT/lib"\nfi\n'
             'if test "$version" = yes; then printf \'%s\\n\' "1.4.5"; fi\n')
        os.chmod(config, 0o755)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["gw", "wmlscript", "wap", "gwlib"]
        self.cpp_info.libdirs = ["lib/kannel"]
        self.cpp_info.includedirs = ["include/kannel"]
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "kannel")
        self.cpp_info.set_property("cmake_target_name", "kannel::kannel")
        self.buildenv_info.define("KANNEL_LIBXML2_ROOT", self.dependencies["libxml2"].package_folder)
        self.buildenv_info.define("KANNEL_OPENSSL_ROOT", self.dependencies["openssl"].package_folder)
