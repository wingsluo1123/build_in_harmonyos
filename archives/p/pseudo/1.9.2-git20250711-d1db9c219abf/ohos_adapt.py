"""OHOS ABI adaptations for the pseudo recipe.

The upstream Linux port targets glibc's versioned ``__xstat`` family and
treats ``struct stat64`` as a distinct ABI.  OHOS is 64-bit by default,
exposes the stat family under the unsuffixed POSIX names, and defines
``stat64``/``statvfs64`` as header aliases rather than separate structs.
This module rewrites the unpacked source tree to the native OHOS ABI.
"""

from __future__ import annotations

import re
from pathlib import Path


# OHOS has no glibc __xstat family, so the linux port's stat wrappers can no
# longer delegate to wrap___fxstatat().  Upstream's __fxstatat64 wrapper did
# two things: the real stat, then a database query that installs the fake
# ownership/mode.  Replacing that call with a bare real stat silently
# disabled every database-backed report (mode, uid, gid).
_STAT_DB_QUERY = """\
	pseudo_msg_t *msg;
	int save_errno;

	rc = base_stat(path, buf);
	if (rc == -1) {
		return rc;
	}
	save_errno = errno;
	msg = pseudo_client_op(OP_STAT, 0, -1, AT_FDCWD, path, buf);
	if (msg && msg->result == RESULT_SUCCEED) {
		pseudo_stat_msg(buf, msg);
	}
	errno = save_errno;
"""

_LSTAT_DB_QUERY = """\
	pseudo_msg_t *msg;
	int save_errno;

	rc = base_lstat(path, buf);
	if (rc == -1) {
		return rc;
	}
	save_errno = errno;
	msg = pseudo_client_op(OP_STAT, 0, -1, AT_FDCWD, path, buf);
	if (msg && msg->result == RESULT_SUCCEED) {
		pseudo_stat_msg(buf, msg);
	}
	errno = save_errno;
"""

_FSTAT_DB_QUERY = """\
	pseudo_msg_t *msg;
	int save_errno;

	rc = base_fstat(fd, buf);
	if (rc == -1) {
		return rc;
	}
	save_errno = errno;
	msg = pseudo_client_op(OP_FSTAT, 0, fd, -1, 0, buf);
	if (msg && msg->result == RESULT_SUCCEED) {
		pseudo_stat_msg(buf, msg);
	}
	errno = save_errno;
"""

_FSTATAT_DB_QUERY = """\
	pseudo_msg_t *msg;
	int save_errno;

	rc = base_fstatat(dirfd, path, buf, flags);
	if (rc == -1) {
		return rc;
	}
	save_errno = errno;
	msg = pseudo_client_op(OP_STAT, 0, -1, dirfd, path, buf);
	if (msg && msg->result == RESULT_SUCCEED) {
		pseudo_stat_msg(buf, msg);
	}
	errno = save_errno;
"""


_OHOS_REAL_GETCWD = r"""static char *
pseudo_ohos_real_getcwd(char *buf, size_t size)
{
    static char *(*real_fn)(char *, size_t) = NULL;

    if (!real_fn) {
        dlerror();
        real_fn = (char *(*)(char *, size_t))dlsym(RTLD_NEXT, "getcwd");
    }
    if (real_fn) {
        char *rc = real_fn(buf, size);

        if (rc) {
            return rc;
        }
    }

    /* OHOS mounts /, /data, /data/storage and /data/storage/el2 as 0711
     * directories owned by root, so the userland getcwd() cannot re-read the
     * ancestors of the current directory and fails with EACCES as soon as the
     * cwd lives below /data/storage/el2.  Measured on the device: the prebuilt
     * shell reports "getcwd: cannot access parent directories: Permission
     * denied" there, while the kernel's getcwd(2) resolves the very same
     * directory.  getcwd(2) walks the dentry chain instead of re-reading the
     * parents, so it keeps working; pseudo has to report a correct cwd or the
     * client silently falls back to a stale $PWD. */
    if (syscall(SYS_getcwd, buf, size) >= 0) {
        return buf;
    }
    return NULL;
}
"""

# raw string keeps C escapes such as \n and \0 intact.
_OHOS_ACCOUNT_PARSERS = r"""
#ifndef PSEUDO_OHOS_ACCOUNT_PARSERS
#define PSEUDO_OHOS_ACCOUNT_PARSERS

static int
pseudo_ohos_parse_id(const char *text, unsigned long *value) {
	char *end = NULL;
	unsigned long parsed;

	if (!text || !*text) {
		return EINVAL;
	}
	errno = 0;
	parsed = strtoul(text, &end, 10);
	if (errno || !end || *end) {
		return EINVAL;
	}
	*value = parsed;
	return 0;
}

static int
pseudo_fgetpwent_r(FILE *fp, struct passwd *pbuf, char *buf, size_t buflen,
                   struct passwd **pbufp) {
	char *fields[7];
	char *cursor;
	size_t len;
	unsigned long uid;
	unsigned long gid;
	int i;
	long started_at;

	if (pbufp) {
		*pbufp = NULL;
	}
	if (!fp || !pbuf || !buf || buflen < 2) {
		return EINVAL;
	}
	started_at = ftell(fp);
	if (started_at == -1) {
		return errno ? errno : EIO;
	}
	if (!fgets(buf, (int)buflen, fp)) {
		return errno ? errno : ENOENT;
	}
	len = strlen(buf);
	if (len && buf[len - 1] == '\n') {
		buf[--len] = '\0';
	} else if (len == buflen - 1) {
		int ch = fgetc(fp);
		if (ch != EOF) {
			ungetc(ch, fp);
			fseek(fp, started_at, SEEK_SET);
			return ERANGE;
		}
		clearerr(fp);
	}

	cursor = buf;
	for (i = 0; i < 6; ++i) {
		fields[i] = cursor;
		cursor = strchr(cursor, ':');
		if (!cursor) {
			fseek(fp, started_at, SEEK_SET);
			return EINVAL;
		}
		*cursor++ = '\0';
	}
	fields[6] = cursor;
	if (strchr(fields[6], ':')) {
		fseek(fp, started_at, SEEK_SET);
		return EINVAL;
	}
	if (pseudo_ohos_parse_id(fields[2], &uid) ||
	    pseudo_ohos_parse_id(fields[3], &gid)) {
		fseek(fp, started_at, SEEK_SET);
		return EINVAL;
	}

	pbuf->pw_name = fields[0];
	pbuf->pw_passwd = fields[1];
	pbuf->pw_uid = (uid_t) uid;
	pbuf->pw_gid = (gid_t) gid;
	pbuf->pw_gecos = fields[4];
	pbuf->pw_dir = fields[5];
	pbuf->pw_shell = fields[6];
	if (pbufp) {
		*pbufp = pbuf;
	}
	(void)len;
	return 0;
}

static int
pseudo_fgetgrent_r(FILE *fp, struct group *gbuf, char *buf, size_t buflen,
                   struct group **gbufp) {
	char *name;
	char *passwd;
	char *gid_text;
	char *members_text;
	char **members;
	char *cursor;
	size_t len;
	size_t ptr_offset;
	size_t max_members;
	size_t member = 0;
	unsigned long gid;
	long started_at;

	if (gbufp) {
		*gbufp = NULL;
	}
	if (!fp || !gbuf || !buf || buflen < 2) {
		return EINVAL;
	}
	started_at = ftell(fp);
	if (started_at == -1) {
		return errno ? errno : EIO;
	}
	if (!fgets(buf, (int)buflen, fp)) {
		return errno ? errno : ENOENT;
	}
	len = strlen(buf);
	if (len && buf[len - 1] == '\n') {
		buf[--len] = '\0';
	} else if (len == buflen - 1) {
		int ch = fgetc(fp);
		if (ch != EOF) {
			ungetc(ch, fp);
			fseek(fp, started_at, SEEK_SET);
			return ERANGE;
		}
		clearerr(fp);
	}

	cursor = buf;
	name = cursor;
	cursor = strchr(cursor, ':');
	if (!cursor) {
		fseek(fp, started_at, SEEK_SET);
		return EINVAL;
	}
	*cursor++ = '\0';
	passwd = cursor;
	cursor = strchr(cursor, ':');
	if (!cursor) {
		fseek(fp, started_at, SEEK_SET);
		return EINVAL;
	}
	*cursor++ = '\0';
	gid_text = cursor;
	cursor = strchr(cursor, ':');
	if (!cursor) {
		fseek(fp, started_at, SEEK_SET);
		return EINVAL;
	}
	*cursor++ = '\0';
	members_text = cursor;
	if (pseudo_ohos_parse_id(gid_text, &gid)) {
		fseek(fp, started_at, SEEK_SET);
		return EINVAL;
	}
	ptr_offset = (len + 1 + sizeof(char *) - 1) & ~(sizeof(char *) - 1);
	if (ptr_offset >= buflen || buflen - ptr_offset < sizeof(char *)) {
		fseek(fp, started_at, SEEK_SET);
		return ERANGE;
	}
	members = (char **) (buf + ptr_offset);
	max_members = (buflen - ptr_offset) / sizeof(char *);
	if (*members_text) {
		for (;;) {
			if (member + 1 >= max_members) {
				fseek(fp, started_at, SEEK_SET);
				return ERANGE;
			}
			members[member++] = members_text;
			cursor = strchr(members_text, ',');
			if (!cursor) {
				break;
			}
			*cursor = '\0';
			members_text = cursor + 1;
		}
	}
	members[member] = NULL;
	gbuf->gr_name = name;
	gbuf->gr_passwd = passwd;
	gbuf->gr_gid = (gid_t) gid;
	gbuf->gr_mem = members;
	if (gbufp) {
		*gbufp = gbuf;
	}
	return 0;
}

#endif
"""




def _source_path(conanfile, *parts):
    return Path(conanfile.source_folder).joinpath(*parts)


def _read(path):
    return path.read_text(encoding="utf-8")


def _write(conanfile, path, content):
    path.write_text(content, encoding="utf-8", newline="\n")
    conanfile.output.info(f"OHOS adaptation updated {path.name}")


def _insert_once(conanfile, path, marker, anchor, addition):
    content = _read(path)
    if marker in content:
        return
    if anchor not in content:
        raise RuntimeError(f"OHOS insertion anchor not found in {path}: {anchor!r}")
    _write(conanfile, path, content.replace(anchor, addition + anchor, 1))


def _replace_content(conanfile, path, replacements):
    content = _read(path)
    changed = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            changed = True
        elif new not in content:
            raise RuntimeError(
                f"OHOS adaptation pattern not found in {path}: {old!r}"
            )
    if changed:
        _write(conanfile, path, content)


def _remove_function(conanfile, path, name, content):
    pattern = re.compile(
        rf"(?ms)^int\s*\n?\s*{re.escape(name)}\([^)]*\)\s*\{{.*?^\}}\s*\n?"
    )
    updated, count = pattern.subn("", content)
    if not count and re.search(rf"\b{re.escape(name)}\s*\(", content):
        raise RuntimeError(f"OHOS adaptation could not remove {name} from {path}")
    return updated


def _filter_wrapfuncs(conanfile, path, unsupported, direct_real):
    content = _read(path)
    lines = []
    for line in content.splitlines(keepends=True):
        match = re.match(r"\s*[^#\n][^()]*?\b([A-Za-z_]\w*)\s*\(", line)
        if match:
            name = match.group(1)
            if name in unsupported:
                continue
            if name in direct_real:
                real_func = direct_real[name]
                line = line.replace(f"real_func={real_func}, ", "")
                line = line.replace(f"real_func={real_func}", "")
        lines.append(line)
    filtered = "".join(lines)
    if filtered != content:
        _write(conanfile, path, filtered)


def adapt_ohos_source(conanfile):
    portdefs = _source_path(conanfile, "ports", "linux", "portdefs.h")
    _replace_content(
        conanfile,
        portdefs,
        (
            ("#define PSEUDO_STATBUF_64 1", "#define PSEUDO_STATBUF_64 0"),
            (
                "#define PSEUDO_STATBUF struct stat64",
                "#define PSEUDO_STATBUF struct stat",
            ),
        ),
    )

    client_header = _source_path(conanfile, "pseudo_client.h")
    _insert_once(
        conanfile,
        _source_path(conanfile, "pseudo_client.c"),
        "#include <sys/syscall.h>",
        "#include <stdio.h>\n",
        "#include <sys/syscall.h>\n",
    )
    _insert_once(
        conanfile,
        _source_path(conanfile, "pseudo_client.c"),
        "#include <dlfcn.h>",
        "#include <stdio.h>\n",
        "#include <dlfcn.h>\n",
    )
    _insert_once(
        conanfile,
        _source_path(conanfile, "pseudo_client.c"),
        "pseudo_ohos_real_getcwd",
        "/* GNU extension */",
        _OHOS_REAL_GETCWD + "\n\n",
    )
    _replace_content(
        conanfile,
        _source_path(conanfile, "pseudo_client.c"),
        ((
            "\tif (getcwd(cwd, pseudo_path_max())) {",
            "\tif (pseudo_ohos_real_getcwd(cwd, pseudo_path_max())) {",
        ),),
    )
    _insert_once(
        conanfile,
        _source_path(conanfile, "pseudo_client.c"),
        "#ifndef O_PATH",
        "#include \"pseudo.h\"\n",
        "#ifndef O_PATH\n#define O_PATH 010000000\n#endif\n\n",
    )

    # OHOS mounts / and the other system directories as 0711 (drwx--x--x), so an
    # unprivileged process cannot open(".", O_RDONLY) there.  Without this the
    # client aborts with "Couldn't stash directory before opening socket" for
    # every command whose cwd is /.  O_PATH resolves the directory without read
    # permission and OHOS accepts the descriptor in fchdir() (measured on the
    # device: open(".",O_RDONLY) -> EACCES, open(".",O_PATH) -> fd, fchdir -> 0).
    _replace_content(
        conanfile,
        _source_path(conanfile, "pseudo_client.c"),
        ((
            '\tcwd_fd = open(".", O_RDONLY);\n',
            '\tcwd_fd = open(".", O_RDONLY);\n'
            '\tif (cwd_fd == -1 && errno == EACCES)\n'
            '\t\tcwd_fd = open(".", O_PATH | O_DIRECTORY);\n',
        ),),
    )
    # The repository CI runs an L5 SONAME gate over every linkable shared
    # library in the package.  Upstream links libpseudo.so without a
    # DT_SONAME, which leaves downstream consumers no way to link it except by
    # absolute path; name the library after the file that gets installed so
    # the soname stays a plain relative name.
    _replace_content(
        conanfile,
        _source_path(conanfile, "Makefile.in"),
        ((
            "\t$(CC) $(CFLAGS) $(CFLAGS_PSEUDO) -shared -o $(LIBPSEUDO) \\\n",
            "\t$(CC) $(CFLAGS) $(CFLAGS_PSEUDO) -shared "
            "-Wl,-soname,libpseudo$(SUFFIX).so -o $(LIBPSEUDO) \\\n",
        ),),
    )
    _replace_content(
        conanfile,
        _source_path(conanfile, "pseudo_client.c"),
        (
            (
                "#if PSEUDO_PORT_LINUX\n"
                "extern char *program_invocation_name;\n"
                "#else\n"
                "static char *program_invocation_name = \"unknown\";\n"
                "#endif",
                "static char *program_invocation_name = \"unknown\";",
            ),
        ),
    )

    util = _source_path(conanfile, "pseudo_util.c")
    _replace_content(
        conanfile,
        util,
        (
            (
                "extern char *program_invocation_short_name; /* glibcism */",
                "char *program_invocation_short_name = \"unknown\";",
            ),
        ),
    )
    _replace_content(
        conanfile,
        _source_path(conanfile, "pseudo_wrappers.c"),
        (("extern char *program_invocation_short_name;\n", ""),),
    )

    pseudolog = _source_path(conanfile, "pseudolog.c")
    _insert_once(
        conanfile,
        pseudolog,
        "#ifndef PSEUDO_OHOS_ALLPERMS",
        "#include <sys/stat.h>\n",
        "\n#ifndef PSEUDO_OHOS_ALLPERMS\n"
        "#define ALLPERMS (S_ISUID | S_ISGID | S_ISVTX | S_IRWXU | S_IRWXG | S_IRWXO)\n"
        "#endif\n",
    )
    _replace_content(
        conanfile,
        client_header,
        (
            (
                "#define base_fstatat(dirfd, path, buf, flags) "
                "real___fxstatat(_STAT_VER, dirfd, path, buf, flags)",
                "#define base_fstatat(dirfd, path, buf, flags) "
                "real_fstatat(dirfd, path, buf, flags)",
            ),
        ),
    )

    unsupported = {
        "creat64",
        "fcntl64",
        "fopen64",
        "freopen64",
        "fstat64",
        "fstatat64",
        "ftw64",
        "glob64",
        "lstat64",
        "mkostemp64",
        "mkstemp64",
        "nftw64",
        "open64",
        "openat64",
        "scandir64",
        "stat64",
        "truncate64",
        "__openat_2",
        "__openat64_2",
        "__xstat",
        "__xstat64",
        "__lxstat",
        "__lxstat64",
        "__fxstat",
        "__fxstat64",
        "__fxstatat",
        "__fxstatat64",
        "__xmknod",
        "__xmknodat",
    }
    direct_real = {
        "stat": "pseudo_stat",
        "lstat": "pseudo_lstat",
        "fstat": "pseudo_fstat",
        "mknod": "pseudo_mknod",
        "mknodat": "pseudo_mknodat",
    }

    wrapfuncs = _source_path(conanfile, "ports", "linux", "wrapfuncs.in")
    _filter_wrapfuncs(conanfile, wrapfuncs, unsupported, direct_real)

    statvfs_wrapfuncs = _source_path(
        conanfile, "ports", "linux", "statvfs", "wrapfuncs.in"
    )
    statvfs_content = _read(statvfs_wrapfuncs)
    statvfs_filtered = "".join(
        line
        for line in statvfs_content.splitlines(keepends=True)
        if "statvfs64(" not in line
    )
    if statvfs_filtered != statvfs_content:
        _write(conanfile, statvfs_wrapfuncs, statvfs_filtered)

    linux_wrappers = _source_path(
        conanfile, "ports", "linux", "pseudo_wrappers.c"
    )
    wrapper_content = _read(linux_wrappers)
    wrapper_content = wrapper_content.replace(
        """/* the unix port wants to know that real_stat() and
 * friends exist.  So they do. And because the Linux
 * port really uses stat64 for those...
 */
""",
        "",
    )
    for function in (
        "pseudo_stat",
        "pseudo_lstat",
        "pseudo_fstat",
        "pseudo_stat64",
        "pseudo_lstat64",
        "pseudo_fstat64",
        "pseudo_mknod",
        "pseudo_mknodat",
    ):
        wrapper_content = _remove_function(
            conanfile, linux_wrappers, function, wrapper_content
        )
    wrapper_content = re.sub(
        r"(?ms)^#undef NFTW_NAME\n"
        r".*?^#include \"../unix/guts/nftw_wrapper_base\.c\"\s*\n?",
        "/* nftw64 aliases nftw on OHOS. */\n",
        wrapper_content,
    )
    if "PSEUDO_OHOS_ACCOUNT_PARSERS" not in wrapper_content:
        wrapper_content += "\n" + _OHOS_ACCOUNT_PARSERS + "\n"
    _write(conanfile, linux_wrappers, wrapper_content)

    guts = _source_path(conanfile, "ports", "linux", "guts")
    # The OHOS loader calls getcwd() from libpseudo's constructor before
    # pseudo_cwd exists.  Let that first lookup bypass the wrapper and use
    # the real libc symbol; otherwise the wrapper recursively asks for the
    # CWD it is trying to initialize and the shell cannot start.
    _replace_content(
        conanfile,
        _source_path(conanfile, "ports", "unix", "guts", "getcwd.c"),
        (
            (
                "\tif (!pseudo_cwd) {\n"
                "\t\tpseudo_diag(\"Asked for CWD, but don't have it!\\n\");\n"
                "\t\terrno = EACCES;\n"
                "\t\treturn NULL;\n"
                "\t}\n",
                "\tif (!pseudo_cwd) {\n"
                "\t\tif (!real_getcwd) {\n"
                "\t\t\treal_getcwd = (char *(*)(char *, size_t))dlsym(RTLD_NEXT, \"getcwd\");\n"
                "\t\t}\n"
                "\t\tif (real_getcwd) {\n"
                "\t\t\treturn real_getcwd(buf, size);\n"
                "\t\t}\n"
                "\t\tpseudo_diag(\"Asked for CWD, but don't have it!\\n\");\n"
                "\t\terrno = EACCES;\n"
                "\t\treturn NULL;\n"
                "\t}\n",
            ),
        ),
    )

    _replace_content(
        conanfile,
        guts / "getpwent_r.c",
        (
            (
                "rc = fgetpwent_r(pseudo_pwd, pwbuf, buf, buflen, pwbufp);",
                "rc = pseudo_fgetpwent_r(pseudo_pwd, pwbuf, buf, buflen, pwbufp);",
            ),
        ),
    )
    _replace_content(
        conanfile,
        guts / "getgrent_r.c",
        (
            (
                "rc = fgetgrent_r(pseudo_grp, gbuf, buf, buflen, gbufp);",
                "rc = pseudo_fgetgrent_r(pseudo_grp, gbuf, buf, buflen, gbufp);",
            ),
        ),
    )

    _replace_content(
        conanfile,
        guts / "stat.c",
        (
            (
                "rc = wrap___fxstatat(_STAT_VER, AT_FDCWD, path, buf, 0);",
                _STAT_DB_QUERY,
            ),
        ),
    )
    _replace_content(
        conanfile,
        guts / "lstat.c",
        (
            (
                "rc = wrap___fxstatat(_STAT_VER, AT_FDCWD, path, buf, "
                "AT_SYMLINK_NOFOLLOW);",
                _LSTAT_DB_QUERY,
            ),
        ),
    )
    _replace_content(
        conanfile,
        guts / "fstat.c",
        (("rc = wrap___fxstat(_STAT_VER, fd, buf);", _FSTAT_DB_QUERY),),
    )
    _replace_content(
        conanfile,
        guts / "fstatat.c",
        (
            (
                "rc = wrap___fxstatat(_STAT_VER, dirfd, path, buf, flags);",
                _FSTATAT_DB_QUERY,
            ),
        ),
    )
    _replace_content(
        conanfile,
        guts / "mknod.c",
        (
            (
                "rc = wrap___xmknod(_MKNOD_VER, path, mode, &dev);",
                "rc = real_mknod(path, mode, dev);",
            ),
        ),
    )
    _replace_content(
        conanfile,
        guts / "mknodat.c",
        (
            (
                "rc = wrap___xmknodat(_MKNOD_VER, dirfd, path, mode, &dev);",
                "rc = real_mknodat(dirfd, path, mode, dev);",
            ),
        ),
    )

    _replace_content(
        conanfile,
        guts / "openat.c",
        (
            ("\tstruct stat64 buf;", "\tPSEUDO_STATBUF buf;"),
            (
                "real___fxstatat64(_STAT_VER, dirfd, path, &buf, "
                "(flags & O_NOFOLLOW) ? AT_SYMLINK_NOFOLLOW : 0)",
                "base_fstatat(dirfd, path, &buf, "
                "(flags & O_NOFOLLOW) ? AT_SYMLINK_NOFOLLOW : 0)",
            ),
            (
                "real___lxstat64(_STAT_VER, path, &buf)",
                "base_lstat(path, &buf)",
            ),
            (
                "real___xstat64(_STAT_VER, path, &buf)",
                "base_stat(path, &buf)",
            ),
        ),
    )

    for relative in ("pseudo.h", "pseudo_client.c", "pseudo_util.c"):
        _replace_content(
            conanfile,
            _source_path(conanfile, relative),
            (("struct stat64", "struct stat"),),
        )

    _replace_content(
        conanfile,
        _source_path(conanfile, "pseudo_util.c"),
        (
            (
                "static int (*real_regexec)(const regex_t *__restrict __preg, "
                "const char *__restrict __string, size_t __nmatch, "
                "regmatch_t __pmatch[__restrict_arr], int __eflags);",
                "static int (*real_regexec)(const regex_t *__restrict __preg, "
                "const char *__restrict __string, size_t __nmatch, "
                "regmatch_t *__restrict __pmatch, int __eflags);",
            ),
        ),
    )

    _replace_content(
        conanfile,
        _source_path(conanfile, "ports", "linux", "xattr", "pseudo_wrappers.c"),
        (
            ("\tstruct stat64 buf;", "\tPSEUDO_STATBUF buf;"),
            ("rc = lstat64(path, &buf);", "rc = base_lstat(path, &buf);"),
            ("rc = fstat64(fd, &buf);", "rc = base_fstat(fd, &buf);"),
        ),
    )
