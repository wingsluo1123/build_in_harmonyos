import os

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BcalConan(ConanFile):
    name = "bcal"
    version = "2.5"
    description = "Byte Calculator - storage expression calculator with byte unit conversion, base conversion, and bitwise operations"
    license = "GPLv3"
    homepage = "https://github.com/jarun/bcal"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Create readline stub headers (readline not available on OHOS)
        rl_inc_dir = os.path.join(self.source_folder, "inc", "readline")
        os.makedirs(rl_inc_dir, exist_ok=True)

        save(self, os.path.join(rl_inc_dir, "readline.h"),
             '#ifndef _READLINE_STUB_H\n#define _READLINE_STUB_H\n'
             '#include <stdio.h>\n'
             'typedef int rl_command_func_t(int, int);\n'
             'char *readline(const char *prompt);\nvoid add_history(const char *line);\n'
             'int rl_bind_key(int key, rl_command_func_t *func);\n'
             'int rl_insert(int count, int key);\n'
             '#endif\n')
        save(self, os.path.join(rl_inc_dir, "history.h"),
             '#ifndef _HISTORY_STUB_H\n#define _HISTORY_STUB_H\n'
             'int read_history(const char *filename);\nint write_history(const char *filename);\n'
             '#endif\n')

        # Create readline stub implementation
        save(self, os.path.join(self.source_folder, "src", "readline_stub.c"),
             '#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n'
             'char *readline(const char *prompt) {\n'
             '    if (prompt && *prompt) fprintf(stderr, "%s", prompt);\n'
             '    char *line = NULL; size_t cap = 0;\n'
             '    if (getline(&line, &cap, stdin) < 0) { free(line); return NULL; }\n'
             '    size_t len = strlen(line);\n'
             '    if (len > 0 && line[len-1] == \'\\n\') line[len-1] = \'\\0\';\n'
             '    return line;\n}\n'
             'void add_history(const char *line) { (void)line; }\n'
             'int read_history(const char *f) { (void)f; return 0; }\n'
             'int write_history(const char *f) { (void)f; return 0; }\n'
             'int rl_bind_key(int key, int (*func)(int, int)) { (void)key; (void)func; return 0; }\n'
             'int rl_insert(int count, int key) { (void)count; (void)key; return 0; }\n')

        # Build: override LDLIBS_READLINE to empty (no -lreadline)
        self.run("make -j1 LDLIBS_READLINE=", cwd=self.source_folder)

    def package(self):
        copy(self, "bcal", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "bcal.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
