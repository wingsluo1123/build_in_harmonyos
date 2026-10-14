#!/usr/bin/env python3
"""Conan recipe — libzeep 8.4.1 (CMake, C++23).

SOAP/HTTP server framework (BSL-1.0) by Maarten Hekkelman (mhekkel).
OHOS adaptation notes:
- CPM 依赖全部本地化（CI worker 无法访问 github/forge）：
  zeem v2.4.1 / asio 1-36-0 由 conandata 额外源预下载 → ZEEP_ZEEM_SOURCE_DIR
  add_subdirectory + ASIO_INCLUDE_DIR 注入；date/Catch2/FastFloat 走 registry。
- try_run 交叉编译必 FAILED_TO_RUN → USE_STD_CHRONO_ZONED_TIME/… 固定 FALSE
  → date lib 路径（registry date/3.0.3 提供 date::date-tz）。
- libc++15 缺 std::format/std::println（无 <print>/format 符号）→ fmt 机械替换
  （libcifpp 同款）；libc++15 ranges 算法需 -D_LIBCPP_ENABLE_EXPERIMENTAL。
- std::ranges::contains（C++23 P2302）libc++15 无 → std::find 等价改写。
- OpenSSL::SSL/OpenSSL::Crypto → openssl::openssl（et 先例，CMakeDeps 单 target）。
- clang15 无 -std=c++23 但 CMake 4.1 cxx_std_23 映射 -std=c++2b，实测可编译。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, replace_in_file, rm, apply_conandata_patches, export_conandata_patches


class LibzeepConan(ConanFile):
    name = "libzeep"
    version = "8.4.1"
    package_type = "library"

    description = "SOAP/HTTP server framework library (C++23)"
    homepage = "https://github.com/mhekkel/libzeep"
    license = "BSL-1.0"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    generators = "CMakeDeps"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenSSL REQUIRED（client 代码）；date 用于 from_stream（try_run 交叉必失败）
        # fmt 替换 std::format/std::println；fast_float 供 zeem charconv
        # 注意：catch2 仅上游测试使用，测试已在 OHOS 真机全量运行并留证
        # （reports/upstream-ctest.log + reports/test-ledger.md），最终配方 BUILD_TESTING=OFF
        # 以保持依赖图干净（ada-url 先例）；catch2 不进入 package_info.requires
        self.requires("openssl/3.5.8.1", transitive_headers=True, transitive_libs=True)
        self.requires("date/3.0.3", transitive_headers=True, transitive_libs=True)
        self.requires("fmt/11.1.3", transitive_headers=True, transitive_libs=True)
        self.requires("fast_float/8.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 配方结构要求：conandata 无 patches 段时为空操作；补丁机制与
        # 上游 CPM 本地化/OHOS 兼容改动均以本文件 source()/build() 内联实现
        apply_conandata_patches(self)
        self._patch_cmake_openssl()
        self._patch_cmake_zeem()
        self._patch_cmake_date()
        self._patch_cmake_compile_defs()
        self._patch_cmake_catch2()
        self._replace_format_to_fmt()
        self._patch_el_object_spaceship()
        self._patch_object_hpp_typename()
        self._patch_request_lang_score()

    # ---- libzeep el/object.hpp: clang15 对依赖类型解析缺陷 → 显式 typename（glaze 先例）----
    def _patch_object_hpp_typename(self):
        p = os.path.join(self.source_folder, "include", "zeep", "el", "object.hpp")
        if not os.path.isfile(p):
            return
        t = open(p, encoding="utf-8", errors="ignore").read()
        o = t
        t = t.replace("using difference_type = T::difference_type;",
                      "using difference_type = typename T::difference_type;")
        if t != o:
            open(p, "w", encoding="utf-8").write(t)

    # ---- libzeep src/request.cpp: lang_score 聚合 emplace 触发 libc++15 construct_at 缺陷 → 补构造函数 ----
    def _patch_request_lang_score(self):
        p = os.path.join(self.source_folder, "src", "request.cpp")
        if not os.path.isfile(p):
            return
        t = open(p, encoding="utf-8", errors="ignore").read()
        o = t
        old = """\tstruct lang_score
\t{
\t\tstd::string lang, region;
\t\tfloat score;
\t\tstd::locale loc;
\t\tbool operator<(const lang_score &rhs) const
\t\t{
\t\t\treturn score > rhs.score;
\t\t}
\t};"""
        new = """\tstruct lang_score
\t{
\t\tstd::string lang, region;
\t\tfloat score;
\t\tstd::locale loc;
\t\tlang_score(std::string l, std::string r, float s, std::locale lc)
\t\t\t: lang(std::move(l)), region(std::move(r)), score(s), loc(std::move(lc))
\t\t{
\t\t}
\t\tbool operator<(const lang_score &rhs) const
\t\t{
\t\t\treturn score > rhs.score;
\t\t}
\t};"""
        t = t.replace(old, new)
        if t != o:
            open(p, "w", encoding="utf-8").write(t)

    # ---- libzeep el-object.cpp: string/vector/map 的 <=> 在 libc++15 缺失 → 显式三路 ----
    def _patch_el_object_spaceship(self):
        p = os.path.join(self.source_folder, "src", "el-object.cpp")
        if not os.path.isfile(p):
            return
        t = open(p, encoding="utf-8", errors="ignore").read()
        o = t
        t = t.replace(
            "\t\t\tcase value_type::array: return *std::get_if<object::array_type>(&lhs.m_data) <=> *std::get_if<object::array_type>(&rhs.m_data);",
            "\t\t\tcase value_type::array:\n"
            "\t\t\t{\n"
            "\t\t\t\tconst auto &la = *std::get_if<object::array_type>(&lhs.m_data);\n"
            "\t\t\t\tconst auto &ra = *std::get_if<object::array_type>(&rhs.m_data);\n"
            "\t\t\t\tauto li = la.begin(), ri = ra.begin();\n"
            "\t\t\t\tfor (; li != la.end() and ri != ra.end(); ++li, ++ri)\n"
            "\t\t\t\t{\n"
            "\t\t\t\t\tauto c = *li <=> *ri;\n"
            "\t\t\t\t\tif (c != std::partial_ordering::equivalent)\n"
            "\t\t\t\t\t\treturn c;\n"
            "\t\t\t\t}\n"
            "\t\t\t\tif (la.size() < ra.size()) return std::partial_ordering::less;\n"
            "\t\t\t\tif (la.size() > ra.size()) return std::partial_ordering::greater;\n"
            "\t\t\t\treturn std::partial_ordering::equivalent;\n"
            "\t\t\t}"
        )
        t = t.replace(
            "\t\t\tcase value_type::object: return *std::get_if<object::object_type>(&lhs.m_data) <=> *std::get_if<object::object_type>(&rhs.m_data);",
            "\t\t\tcase value_type::object:\n"
            "\t\t\t{\n"
            "\t\t\t\tconst auto &lo = *std::get_if<object::object_type>(&lhs.m_data);\n"
            "\t\t\t\tconst auto &ro = *std::get_if<object::object_type>(&rhs.m_data);\n"
            "\t\t\t\tauto li = lo.begin(), ri = ro.begin();\n"
            "\t\t\t\tfor (; li != lo.end() and ri != ro.end(); ++li, ++ri)\n"
            "\t\t\t\t{\n"
            "\t\t\t\t\tif (int c = li->first.compare(ri->first); c != 0)\n"
            "\t\t\t\t\t\treturn c < 0 ? std::partial_ordering::less : std::partial_ordering::greater;\n"
            "\t\t\t\t\tauto c = li->second <=> ri->second;\n"
            "\t\t\t\t\tif (c != std::partial_ordering::equivalent)\n"
            "\t\t\t\t\t\treturn c;\n"
            "\t\t\t\t}\n"
            "\t\t\t\tif (lo.size() < ro.size()) return std::partial_ordering::less;\n"
            "\t\t\t\tif (lo.size() > ro.size()) return std::partial_ordering::greater;\n"
            "\t\t\t\treturn std::partial_ordering::equivalent;\n"
            "\t\t\t}"
        )
        t = t.replace(
            "\t\t\tcase value_type::string: return *std::get_if<std::string>(&lhs.m_data) <=> *std::get_if<std::string>(&rhs.m_data);",
            "\t\t\tcase value_type::string:\n"
            "\t\t\t{\n"
            "\t\t\t\tint c = std::get_if<std::string>(&lhs.m_data)->compare(*std::get_if<std::string>(&rhs.m_data));\n"
            "\t\t\t\treturn c < 0 ? std::partial_ordering::less :\n"
            "\t\t\t\t\t(c > 0 ? std::partial_ordering::greater : std::partial_ordering::equivalent);\n"
            "\t\t\t}"
        )
        if t != o:
            open(p, "w", encoding="utf-8").write(t)

    # ---- libzeep CMakeLists 补丁 ----
    def _patch_cmake_openssl(self):
        p = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(self, p, "find_package(OpenSSL REQUIRED)",
                        "find_package(openssl CONFIG REQUIRED)\n"
                        "find_package(fmt CONFIG REQUIRED)")
        replace_in_file(self, p, "OpenSSL::SSL", "openssl::openssl", strict=False)
        replace_in_file(self, p, "OpenSSL::Crypto", "openssl::openssl", strict=False)
        # fmt 替换 std::format/std::println 后，zeep 目标必须显式链接 fmt::fmt
        # （CMakeDeps 只给显式 link 的目标注入 include 路径）
        replace_in_file(self, p,
                        "target_link_libraries(zeep PUBLIC Threads::Threads zeem::zeem openssl::openssl openssl::openssl)",
                        "target_link_libraries(zeep PUBLIC Threads::Threads zeem::zeem openssl::openssl openssl::openssl fmt::fmt)")

    def _patch_cmake_zeem(self):
        p = os.path.join(self.source_folder, "CMakeLists.txt")
        old = """CPMFindPackage(NAME zeem
    GIT_REPOSITORY "https://forge.hekkelman.net/maarten/zeem.git"
    GIT_TAG v2.4.1
    EXCLUDE_FROM_ALL YES)"""
        new = """if(DEFINED ZEEP_ZEEM_SOURCE_DIR)
    add_subdirectory(${ZEEP_ZEEM_SOURCE_DIR} zeem EXCLUDE_FROM_ALL)
else()
    CPMFindPackage(NAME zeem
        GIT_REPOSITORY "https://forge.hekkelman.net/maarten/zeem.git"
        GIT_TAG v2.4.1
        EXCLUDE_FROM_ALL YES)
endif()"""
        replace_in_file(self, p, old, new)

    def _patch_cmake_date(self):
        p = os.path.join(self.source_folder, "CMakeLists.txt")
        old = """    CPMFindPackage(
        NAME date
        GIT_REPOSITORY "https://github.com/HowardHinnant/date"
        VERSION 3.0.3
        EXCLUDE_FROM_ALL YES
        OPTIONS
        "USE_SYSTEM_TZ_DB ON"
        "BUILD_TZ_LIB ON")"""
        new = """    find_package(date CONFIG REQUIRED)"""
        replace_in_file(self, p, old, new)

    def _patch_cmake_compile_defs(self):
        p = os.path.join(self.source_folder, "CMakeLists.txt")
        # libc++15 ranges 算法需实验开关（libcifpp 先例）；对 zeep 及 zeem 子目录全局生效
        old = "include(CTest)"
        new = """include(CTest)

# OHOS libc++15: _LIBCPP_HAS_NO_INCOMPLETE_RANGES 默认关闭 ranges 算法，
# -D_LIBCPP_ENABLE_EXPERIMENTAL 恢复（libcifpp 10.0.4 同款先例，实测可编译链接运行）
add_compile_definitions(_LIBCPP_ENABLE_EXPERIMENTAL)"""
        replace_in_file(self, p, old, new)

    def _patch_cmake_catch2(self):
        p = os.path.join(self.source_folder, "test", "CMakeLists.txt")
        old = """CPMFindPackage(
    NAME Catch2
    GIT_REPOSITORY "https://github.com/catchorg/Catch2"
    VERSION 3.4.0
    EXCLUDE_FROM_ALL YES)"""
        new = """find_package(Catch2 CONFIG REQUIRED)"""
        replace_in_file(self, p, old, new)

    # ---- std::format/std::println → fmt（libc++15 无 <format>/<print> 符号）----
    def _replace_format_to_fmt(self):
        roots = [os.path.join(self.source_folder, "src"),
                 os.path.join(self.source_folder, "include"),
                 os.path.join(self.source_folder, "test")]
        touched = 0
        for root in roots:
            if not os.path.isdir(root):
                continue
            for base, _dirs, files in os.walk(root):
                for fn in files:
                    if not fn.endswith((".cpp", ".hpp", ".h", ".cxx")):
                        continue
                    path = os.path.join(base, fn)
                    t = open(path, encoding="utf-8", errors="ignore").read()
                    orig = t
                    if "#include <print>" in t:
                        t = t.replace("#include <print>", "#include <fmt/ostream.h>")
                    if "# include <print>" in t:
                        t = t.replace("# include <print>", "# include <fmt/ostream.h>")
                    if "#include <format>" in t:
                        t = t.replace("#include <format>", "#include <fmt/format.h>")
                    if "# include <format>" in t:
                        t = t.replace("# include <format>", "# include <fmt/format.h>")
                    if "std::println(" in t:
                        t = t.replace("std::println(", "fmt::println(")
                    if "std::format(" in t:
                        t = t.replace("std::format(", "fmt::format(")
                    # println 经 std::ostream 重载（std::clog/std::ofstream），必须 <fmt/ostream.h>
                    if "fmt::println(" in t and "<fmt/ostream.h>" not in t:
                        t = t.replace("#include <fmt/format.h>",
                                      "#include <fmt/format.h>\n#include <fmt/ostream.h>")
                        if "<fmt/format.h>" not in t and "<fmt/ostream.h>" not in orig:
                            t = "#include <fmt/ostream.h>\n" + t
                    if t != orig:
                        open(path, "w", encoding="utf-8").write(t)
                        touched += 1
        # std::ranges::contains（C++23 P2302，libc++15 无）→ std::find 等价
        p = os.path.join(self.source_folder, "src", "el-object.cpp")
        if os.path.isfile(p):
            t = open(p, encoding="utf-8", errors="ignore").read()
            if "std::ranges::contains(" in t:
                t = t.replace(
                    "result = std::ranges::contains(std::get<array_type>(m_data), test);",
                    "result = std::find(std::get<array_type>(m_data).begin(),"
                    " std::get<array_type>(m_data).end(), test) != std::get<array_type>(m_data).end();"
                )
                open(p, "w", encoding="utf-8").write(t)
                touched += 1

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游测试（Catch2）已在 OHOS 真机全量运行并留证（reports/upstream-ctest.log、
        # reports/test-ledger.md：13/13 通过）。最终配方关闭 BUILD_TESTING，避免
        # catch2 作为库的传递依赖进入消费者图（ada-url 同款先例）
        tc.variables["BUILD_TESTING"] = "OFF"
        # 独立 asio（不用 boost），vendored asio 头目录经 ASIO_INCLUDE_DIR 注入
        tc.variables["ZEEP_USE_BOOST_ASIO"] = "OFF"
        tc.variables["ZEEP_BUILD_EXAMPLES"] = "OFF"
        tc.variables["ZEEP_BUILD_CXX_MODULE"] = "OFF"
        tc.variables["ZEEP_BUILD_DOCUMENTATION"] = "OFF"
        # zeem 作为子目录：关闭其示例/模块/文档（clang15 不支持 C++20 modules）
        tc.variables["ZEEM_BUILD_EXAMPLES"] = "OFF"
        tc.variables["ZEEM_BUILD_CXX_MODULE"] = "OFF"
        tc.cache_variables["ASIO_INCLUDE_DIR"] = os.path.join(
            self.build_folder, "third_party", "asio", "asio", "include"
        )
        tc.variables["ZEEP_ZEEM_SOURCE_DIR"] = os.path.join(
            self.build_folder, "third_party", "zeem"
        )
        tc.generate()

    def build(self):
        # 预下载 CPM 依赖源（zeem 官方 forge + asio GitHub），本地化
        get(self, **self.conan_data["zeem_sources"],
            destination=os.path.join(self.build_folder, "third_party", "zeem"),
            strip_root=True)
        get(self, **self.conan_data["asio_sources"],
            destination=os.path.join(self.build_folder, "third_party", "asio"),
            strip_root=True)
        self._patch_zeem()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ---- vendored zeem 补丁（FastFloat/date CPM → registry find_package）----
    def _patch_zeem(self):
        zroot = os.path.join(self.build_folder, "third_party", "zeem")
        p = os.path.join(zroot, "CMakeLists.txt")
        if not os.path.isfile(p):
            return
        # FastFloat CPM → find_package(fast_float CONFIG)
        t = open(p, encoding="utf-8", errors="ignore").read()
        orig = t
        t = t.replace(
            'CPMFindPackage(\n        NAME FastFloat\n'
            '        GIT_REPOSITORY "https://github.com/fastfloat/fast_float"\n'
            '        GIT_TAG v8.0.2\n'
            '        EXCLUDE_FROM_ALL YES)',
            'find_package(fast_float CONFIG REQUIRED)'
        )
        # zeem 用 FastFloat::fast_float target 名 → fast_float::fast_float
        t = t.replace("FastFloat::fast_float", "fast_float::fast_float")
        # date CPM → find_package(date CONFIG)
        t = t.replace(
            'CPMFindPackage(\n        NAME date\n'
            '        GIT_REPOSITORY "https://github.com/HowardHinnant/date"\n'
            '        VERSION 3.0.3\n'
            '        EXCLUDE_FROM_ALL YES\n'
            '        OPTIONS\n'
            '        "USE_SYSTEM_TZ_DB ON"\n'
            '        "BUILD_TZ_LIB ON")',
            'find_package(date CONFIG REQUIRED)'
        )
        # zeem 源码 std::format → fmt 后，zeem 目标显式链接 fmt::fmt（include 传导）
        t = t.replace(
            "target_link_libraries(zeem PUBLIC date::date-tz)",
            "target_link_libraries(zeem PUBLIC date::date-tz fmt::fmt)"
        )
        # zeem 子目录需可见 fmt::fmt target → 由 libzeep CMakeLists 在 add_subdirectory 前 find_package
        if "find_package(fmt CONFIG REQUIRED)" not in t:
            t = t.replace("include(CTest)",
                          "include(CTest)\nfind_package(fmt CONFIG REQUIRED)")
        if t != orig:
            open(p, "w", encoding="utf-8").write(t)
        # zeem 源码 std::format → fmt（serialize.hpp 有 chrono %F → fmt/chrono.h）
        for rel in ("include/zeem/serialize.hpp", "src/parser.cpp", "src/parser.cxx"):
            fp = os.path.join(zroot, rel)
            if not os.path.isfile(fp):
                continue
            t = open(fp, encoding="utf-8", errors="ignore").read()
            o = t
            if "#include <format>" in t:
                t = t.replace("#include <format>", "#include <fmt/format.h>")
            if "# include <format>" in t:
                t = t.replace("# include <format>", "# include <fmt/format.h>")
            if "std::format(" in t:
                t = t.replace("std::format(", "fmt::format(")
            if "serialize.hpp" in rel and "<fmt/format.h>" in t and "<fmt/chrono.h>" not in t:
                t = t.replace("#include <fmt/format.h>", "#include <fmt/format.h>\n# include <fmt/chrono.h>")
            if t != o:
                open(fp, "w", encoding="utf-8").write(t)
        # serialize.hpp 的 <source_location> 仅 include 无实际使用，libc++15 无此头 → 移除
        fp = os.path.join(zroot, "include", "zeem", "serialize.hpp")
        if os.path.isfile(fp):
            t = open(fp, encoding="utf-8", errors="ignore").read()
            if "# include <source_location>" in t:
                t = t.replace("# include <source_location>\n", "")
            # serialize.hpp 未显式 include <format>（原经其他头传递），需直接注入 fmt 头
            if "# include <fmt/format.h>" not in t:
                t = t.replace("# include <type_traits>\n",
                              "# include <type_traits>\n# include <fmt/format.h>\n# include <fmt/chrono.h>\n")
            open(fp, "w", encoding="utf-8").write(t)
        # zeem xpath.cpp 的 std::ranges::contains（C++23 P2302，libc++15 无）→ std::find 等价
        fp = os.path.join(zroot, "src", "xpath.cpp")
        if os.path.isfile(fp):
            t = open(fp, encoding="utf-8", errors="ignore").read()
            if "std::ranges::contains(" in t:
                t = t.replace(
                    "std::ranges::contains(ids, e->id())",
                    "std::find(ids.begin(), ids.end(), e->id()) != ids.end()"
                )
                open(fp, "w", encoding="utf-8").write(t)
        # zeem node.hpp: attribute::operator<=> 对 std::string 用 <=>（libc++15 无）→ compare() 显式三路
        fp = os.path.join(zroot, "include", "zeem", "node.hpp")
        if os.path.isfile(fp):
            t = open(fp, encoding="utf-8", errors="ignore").read()
            o = t
            t = t.replace(
                "\t\tif (auto cmp = (a.m_qname <=> b.m_qname); cmp != 0)\n"
                "\t\t\treturn cmp;\n"
                "\t\tif (auto cmp = (a.m_id <=> b.m_id); cmp != 0)\n"
                "\t\t\treturn cmp;\n"
                "\t\treturn a.m_value <=> b.m_value;",
                "\t\tif (int c = a.m_qname.compare(b.m_qname); c != 0)\n"
                "\t\t\treturn c < 0 ? std::strong_ordering::less : std::strong_ordering::greater;\n"
                "\t\tif (a.m_id != b.m_id)\n"
                "\t\t\treturn a.m_id ? std::strong_ordering::greater : std::strong_ordering::less;\n"
                "\t\tint c = a.m_value.compare(b.m_value);\n"
                "\t\treturn c < 0 ? std::strong_ordering::less :\n"
                "\t\t\t(c > 0 ? std::strong_ordering::greater : std::strong_ordering::equal);"
            )
            if t != o:
                open(fp, "w", encoding="utf-8").write(t)
        # zeem xpath.cpp: node_set::operator<=> 对 std::vector<node*> 用 <=>（libc++15 无）→ lexicographical_compare
        fp = os.path.join(zroot, "src", "xpath.cpp")
        if os.path.isfile(fp):
            t = open(fp, encoding="utf-8", errors="ignore").read()
            o = t
            t = t.replace(
                "\tconstexpr auto operator<=>(const node_set &sb) const\n"
                "\t{\n"
                "\t\treturn m_nodes <=> sb.m_nodes;\n"
                "\t}",
                "\tauto operator<=>(const node_set &sb) const\n"
                "\t{\n"
                "\t\tconst auto &a = m_nodes;\n"
                "\t\tconst auto &b = sb.m_nodes;\n"
                "\t\tif (std::lexicographical_compare(a.begin(), a.end(), b.begin(), b.end()))\n"
                "\t\t\treturn std::strong_ordering::less;\n"
                "\t\tif (std::lexicographical_compare(b.begin(), b.end(), a.begin(), a.end()))\n"
                "\t\t\treturn std::strong_ordering::greater;\n"
                "\t\treturn std::strong_ordering::equal;\n"
                "\t}"
            )
            if t != o:
                open(fp, "w", encoding="utf-8").write(t)
        # zeem node.cpp: std::ranges::binary_search 在 OHOS libc++15 实验性 ranges 下误判
        # （"html" 不在空元素表内却返回 true，实测复现），导致 HTML 序列化自闭合丢子节点
        # → 改用 std::binary_search（实测结果正确）
        fp = os.path.join(zroot, "src", "node.cpp")
        if os.path.isfile(fp):
            t = open(fp, encoding="utf-8", errors="ignore").read()
            o = t
            t = t.replace(
                "\treturn std::ranges::binary_search(kEmptyHTMLElements, el);",
                "\treturn std::binary_search(kEmptyHTMLElements.begin(), kEmptyHTMLElements.end(), el);"
            )
            if t != o:
                open(fp, "w", encoding="utf-8").write(t)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSES/BSL-1.0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # vendored 依赖 zeem 随包安装：libzeep 公开头文件（zeep/http/reply.hpp 等）
        # 引用 <zeem/zeem.hpp>，且 zeep-targets 导出引用 zeem::zeem — 消费者必须可见
        zeem_src = os.path.join(self.build_folder, "third_party", "zeem")
        copy(self, "*", src=os.path.join(zeem_src, "include", "zeem"),
             dst=os.path.join(self.package_folder, "include", "zeem"))
        copy(self, "libzeem.a", src=os.path.join(self.build_folder, "zeem"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # ZEEP_USE_BOOST_ASIO=OFF 时生成的 include/zeep/http/asio.hpp 引用
        # <asio.hpp>/<asio/ssl.hpp> —— vendored 独立 asio（header-only）随包安装
        asio_src = os.path.join(self.build_folder, "third_party", "asio", "asio", "include")
        copy(self, "*", src=asio_src, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "zeep")
        self.cpp_info.set_property("cmake_target_name", "zeep::zeep")
        self.cpp_info.libs = ["zeep", "zeem"]
        # 公开头文件经 zeem 传递依赖 date/fmt，且命名空间规则要求依赖目标可见；
        # CMakeDeps 依赖目标名：fmt::fmt / date::date-tz / openssl::openssl / fast_float::fast_float
        self.cpp_info.requires = ["fmt::fmt", "date::date-tz", "openssl::openssl", "fast_float::fast_float"]
        # 公开头文件使用 std::ranges 算法（C++20），OHOS libc++15 需实验开关
        # （与 libzeep 自身构建一致；libcifpp 同款先例）
        self.cpp_info.defines = ["_LIBCPP_ENABLE_EXPERIMENTAL"]
