import os
import re
import subprocess
import tarfile
from collections import Counter, defaultdict

from pygemstones.io import file as f
from pygemstones.system import runner as r
from pygemstones.util import log as l

import modules.common as cm
import modules.config as c
import modules.pdfium as p


# -----------------------------------------------------------------------------
def run_task_build_pdfium():
    # Keep the Rust static WASM checkout separate from the existing Emscripten
    # build tree. The Pdfium dependency checkout still needs the upstream
    # Emscripten target_os entries because Chromium stores its wasm toolchain
    # support under that target.
    p.get_pdfium_by_target("rust-wasm", checkout_target_os="emscripten")


# -----------------------------------------------------------------------------
def run_task_patch():
    l.colored("Patching files...", l.YELLOW)

    source_dir = os.path.join("build", "rust-wasm", "pdfium")

    _patch_build_config(source_dir)
    _patch_wasm_flag(source_dir)
    _patch_compiler_config(source_dir)
    _patch_emscripten_link_flags(source_dir)
    _patch_fxcrt_config(source_dir)
    _patch_fxge_config(source_dir)
    _patch_icu_config(source_dir)
    _patch_freetype_config(source_dir)
    _patch_freetype_sources(source_dir)
    _patch_zlib_config(source_dir)
    _patch_lcms_config(source_dir)
    _patch_abseil_config(source_dir)
    _patch_abseil_base_config(source_dir)
    _patch_abseil_random_config(source_dir)
    _patch_abseil_time_config(source_dir)
    _write_freetype_wasm_stdlib(source_dir)
    _write_freetype_wasm_system(source_dir)
    _write_abseil_wasm_debugging(source_dir)
    _write_abseil_wasm_base(source_dir)
    _write_abseil_wasm_random(source_dir)
    _write_abseil_wasm_time(source_dir)
    _write_lcms_wasm_stubs(source_dir)
    _write_fxcrt_wasm_files(source_dir)
    _write_fxge_wasm_platform(source_dir)
    _write_rust_wasm_setjmp_header(source_dir)
    _write_rust_wasm_config(source_dir)
    _write_rust_wasm_toolchain(source_dir)

    l.ok()


# -----------------------------------------------------------------------------
def run_task_build():
    l.colored("Generating Rust static WASM build files...", l.YELLOW)

    current_dir = f.current_dir()

    for config in c.configurations_rust_wasm:
        for target in c.targets_rust_wasm:
            out_dir = "{0}-{1}-{2}".format(
                target["target_os"], target["target_cpu"], config
            )
            main_dir = os.path.join("build", "rust-wasm", "pdfium", "out", out_dir)

            f.recreate_dir(main_dir)

            os.chdir(os.path.join("build", "rust-wasm", "pdfium"))

            args = cm.get_build_args(
                config,
                c.shared_lib_rust_wasm,
                target["pdfium_os"],
                target["target_cpu"],
                rust_target=target["rust_target"],
                rust_wasm_sysroot=_get_rust_wasm_sysroot(target),
                rust_wasm_sysroot_target=_get_rust_wasm_sysroot_target(target),
            )
            args_str = " ".join(args)

            command = [
                "gn",
                "gen",
                "out/{0}".format(out_dir),
                "--args='{0}'".format(args_str),
            ]
            r.run(" ".join(command), shell=True)

            l.colored(
                "Prototype stops after `gn gen`; run ninja manually once the "
                "generated graph and unresolved symbols have been reviewed.",
                l.YELLOW,
            )

            os.chdir(current_dir)

    l.ok()


# -----------------------------------------------------------------------------
def run_task_install():
    l.colored("Installing Rust static WASM libraries...", l.YELLOW)

    for config in c.configurations_rust_wasm:
        for target in c.targets_rust_wasm:
            out_dir = "{0}-{1}-{2}".format(
                target["target_os"], target["target_cpu"], config
            )

            source_lib_path = os.path.join(
                "build",
                "rust-wasm",
                "pdfium",
                "out",
                out_dir,
                "obj",
                "libpdfium.a",
            )
            target_root = os.path.join(
                "build", "rust-wasm", target["rust_target"], config
            )
            target_lib_dir = os.path.join(target_root, "lib")
            target_include_dir = os.path.join(target_root, "include")
            target_include_cpp_dir = os.path.join(target_include_dir, "cpp")

            f.create_dir(target_lib_dir)
            f.copy_file(source_lib_path, os.path.join(target_lib_dir, "libpdfium.a"))

            include_dir = os.path.join("build", "rust-wasm", "pdfium", "public")
            include_cpp_dir = os.path.join(include_dir, "cpp")

            f.recreate_dir(target_include_dir)
            f.copy_files(include_dir, target_include_dir, "*.h")
            f.copy_files(include_cpp_dir, target_include_cpp_dir, "*.h")

    l.ok()


# -----------------------------------------------------------------------------
def run_task_analyze():
    l.colored("Analyzing Rust static WASM prototype...", l.YELLOW)

    for config in c.configurations_rust_wasm:
        for target in c.targets_rust_wasm:
            out_dir = "{0}-{1}-{2}".format(
                target["target_os"], target["target_cpu"], config
            )
            source_dir = os.path.join("build", "rust-wasm", "pdfium")
            gn_out_dir = os.path.join("out", out_dir)
            full_out_dir = os.path.join(source_dir, gn_out_dir)

            if not os.path.isdir(full_out_dir):
                l.e(
                    "Missing GN output directory: {0}. Run `python3 make.py "
                    "build-rust-wasm` first.".format(full_out_dir)
                )

            l.colored("GN args...", l.YELLOW)
            r.run(["python3", "-c", f"print(open('{full_out_dir}/args.gn').read())"])

            l.colored("Pdfium target metadata...", l.YELLOW)
            r.run(["gn", "desc", gn_out_dir, "//:pdfium", "outputs"], cwd=source_dir)
            r.run(["gn", "desc", gn_out_dir, "//:pdfium", "cflags"], cwd=source_dir)
            r.run(["gn", "desc", gn_out_dir, "//:pdfium", "cflags_cc"], cwd=source_dir)
            r.run(["gn", "desc", gn_out_dir, "//:pdfium", "ldflags"], cwd=source_dir)

            l.colored("Generated Ninja references to Emscripten...", l.YELLOW)
            _run_generated_file_scan(full_out_dir, "emscripten")

            l.colored("Generated Ninja Emscripten linker settings...", l.YELLOW)
            _run_generated_file_scan(full_out_dir, "ALLOW_MEMORY_GROWTH")
            _run_generated_file_scan(full_out_dir, "LLD_REPORT_UNDEFINED")

            l.colored("Generated Ninja WASI imports...", l.YELLOW)
            _run_generated_file_scan(full_out_dir, "wasi_snapshot_preview1")

            l.colored("Static archive boundary...", l.YELLOW)
            _run_archive_inspection(source_dir, full_out_dir)

    l.ok()


# -----------------------------------------------------------------------------
def _run_generated_file_scan(root_dir, needle):
    command = [
        "python3",
        "-c",
        (
            "from pathlib import Path; "
            "root=Path({0!r}); "
            "needle={1!r}; "
            "hits=[]; "
            "\nfor p in root.rglob('*'):\n"
            "    if not p.is_file():\n"
            "        continue\n"
            "    try:\n"
            "        text=p.read_text(errors='ignore')\n"
            "    except Exception:\n"
            "        continue\n"
            "    if needle.lower() in text.lower():\n"
            "        hits.append(str(p))\n"
            "print('\\n'.join(hits) if hits else "
            "'No ' + needle + ' references found in generated files.')"
        ).format(root_dir, needle),
    ]
    r.run(command)


# -----------------------------------------------------------------------------
def _run_archive_inspection(source_dir, full_out_dir):
    archive_path = os.path.join(full_out_dir, "obj", "libpdfium.a")

    if not os.path.isfile(archive_path):
        l.bullet(
            "Missing archive: {0}. Run ninja for the Pdfium target first.".format(
                archive_path
            ),
            l.YELLOW,
        )
        return

    llvm_dir = os.path.join(
        source_dir, "third_party", "llvm-build", "Release+Asserts", "bin"
    )
    ar_tool = os.path.join(llvm_dir, "llvm-ar")
    nm_tool = os.path.join(llvm_dir, "llvm-nm")

    members = _run_tool([ar_tool, "t", archive_path]).splitlines()
    defined, _ = _read_archive_symbols(nm_tool, archive_path, "--defined-only")
    undefined, undefined_by_symbol = _read_archive_symbols(
        nm_tool, archive_path, "--undefined-only"
    )
    unresolved = Counter(
        {symbol: count for symbol, count in undefined.items() if symbol not in defined}
    )

    archive_size = os.path.getsize(archive_path)
    l.bullet("Archive: {0} ({1:,} bytes)".format(archive_path, archive_size), l.GREEN)
    l.bullet("Objects: {0:,}".format(len(members)), l.GREEN)
    l.bullet("Defined symbols: {0:,}".format(len(defined)), l.GREEN)
    l.bullet("Raw undefined references: {0:,}".format(sum(undefined.values())), l.GREEN)
    l.bullet(
        "External unresolved symbols after archive self-resolution: {0:,}".format(
            len(unresolved)
        ),
        l.GREEN,
    )

    grouped = defaultdict(list)
    for symbol, count in unresolved.most_common():
        grouped[_classify_unresolved_symbol(symbol)].append((symbol, count))

    for category in [
        "browser-sensitive POSIX",
        "C/C++ runtime",
        "compiler/wasm runtime",
        "wasm internals",
        "other",
    ]:
        entries = grouped.get(category, [])
        if not entries:
            continue
        sample = ", ".join(
            "{0} ({1})".format(symbol, count) for symbol, count in entries[:12]
        )
        l.bullet("{0}: {1} symbols; {2}".format(category, len(entries), sample), l.GREEN)

    posix_entries = grouped.get("browser-sensitive POSIX", [])
    if posix_entries:
        l.colored("Browser-sensitive unresolved symbol origins...", l.YELLOW)
        for symbol, count in posix_entries[:20]:
            origins = undefined_by_symbol.get(symbol, Counter()).most_common(5)
            origin_text = ", ".join(
                "{0} ({1})".format(obj, obj_count) for obj, obj_count in origins
            )
            l.bullet("{0} ({1}): {2}".format(symbol, count, origin_text), l.GREEN)


# -----------------------------------------------------------------------------
def _read_archive_symbols(nm_tool, archive_path, nm_mode):
    output = _run_tool([nm_tool, nm_mode, archive_path])
    symbols = Counter()
    by_symbol = defaultdict(Counter)
    current_object = None

    for line in output.splitlines():
        if line.endswith(":") and not line.startswith(" "):
            current_object = line[:-1]
            continue

        parts = line.split()
        if not parts:
            continue

        if parts[0] == "U" and len(parts) >= 2:
            symbol = parts[1]
        else:
            symbol = parts[-1]

        if not _looks_like_symbol(symbol):
            continue

        symbols[symbol] += 1
        if current_object:
            by_symbol[symbol][os.path.basename(current_object)] += 1

    return symbols, by_symbol


# -----------------------------------------------------------------------------
def _looks_like_symbol(symbol):
    return bool(re.search(r"[A-Za-z_]", symbol))


# -----------------------------------------------------------------------------
def _classify_unresolved_symbol(symbol):
    browser_sensitive = {
        "access",
        "chdir",
        "close",
        "closedir",
        "fclose",
        "fcntl",
        "fdopen",
        "fflush",
        "fopen",
        "fprintf",
        "fread",
        "fseek",
        "fstat",
        "fsync",
        "ftell",
        "ftruncate",
        "fwrite",
        "getcwd",
        "getenv",
        "getpid",
        "gettimeofday",
        "isatty",
        "lseek",
        "mkdir",
        "mmap",
        "munmap",
        "open",
        "opendir",
        "pthread_create",
        "pthread_join",
        "pthread_mutex_lock",
        "pthread_mutex_unlock",
        "read",
        "readdir",
        "remove",
        "rename",
        "rmdir",
        "stat",
        "time",
        "unlink",
        "write",
    }
    runtime_symbols = {
        "__assert_fail",
        "__cxa_atexit",
        "__cxa_pure_virtual",
        "__errno_location",
        "__libcpp_verbose_abort",
        "abort",
        "calloc",
        "free",
        "localeconv",
        "malloc",
        "memchr",
        "memcmp",
        "memcpy",
        "memmove",
        "memset",
        "posix_memalign",
        "qsort",
        "realloc",
        "snprintf",
        "sprintf",
        "strcmp",
        "strcpy",
        "strlen",
        "strncmp",
        "strncpy",
        "strtol",
        "strtoul",
        "vsnprintf",
    }
    compiler_runtime_prefixes = (
        "__ashl",
        "__ashr",
        "__div",
        "__fix",
        "__float",
        "__mul",
        "__popcount",
        "__trunc",
        "__udiv",
        "__umod",
    )
    cpp_prefixes = (
        "_ZNSt3__2",
        "_ZSt",
        "_ZTI",
        "_ZTS",
        "_ZTV",
        "_Zda",
        "_Zdl",
        "_Znam",
        "_Znwm",
        "__cxa",
    )
    wasm_internals = {
        "__indirect_function_table",
        "__memory_base",
        "__stack_pointer",
        "__table_base",
    }

    if symbol in browser_sensitive:
        return "browser-sensitive POSIX"
    if symbol in runtime_symbols or symbol.startswith(cpp_prefixes):
        return "C/C++ runtime"
    if symbol in wasm_internals:
        return "wasm internals"
    if symbol.startswith(compiler_runtime_prefixes):
        return "compiler/wasm runtime"
    return "other"


# -----------------------------------------------------------------------------
def _run_tool(command):
    result = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        errors="replace",
    )
    return result.stdout


# -----------------------------------------------------------------------------
def run_task_archive():
    l.colored("Archiving Rust static WASM libraries...", l.YELLOW)

    current_dir = os.getcwd()
    output_filename = os.path.join(current_dir, "rust-wasm.tgz")

    tar = tarfile.open(output_filename, "w:gz")
    tar.add(
        name=os.path.join(current_dir, "build", "rust-wasm", "wasm32-unknown-unknown"),
        arcname="wasm32-unknown-unknown",
    )
    tar.close()

    l.ok()


# -----------------------------------------------------------------------------
def _patch_build_config(source_dir):
    source_file = os.path.join(source_dir, "build", "config", "BUILDCONFIG.gn")

    line_content = '_default_toolchain = "//build/toolchain/rust_wasm:$target_cpu"'
    line_number = f.get_file_line_number_with_content(
        source_file, line_content, strip=True
    )

    if not line_number:
        source = """} else if (target_os == "emscripten") {
  # Because it's too hard to remove all targets from //BUILD.gn that do not work with it.
  assert(
      false,
      "emscripten is not a supported target_os. It is available only as secondary toolchain.")
} else {"""

        target = """} else if (target_os == "emscripten") {
  # Because it's too hard to remove all targets from //BUILD.gn that do not work with it.
  assert(
      false,
      "emscripten is not a supported target_os. It is available only as secondary toolchain.")
} else if (target_os == "wasm32") {
  _default_toolchain = "//build/toolchain/rust_wasm:$target_cpu"
} else {"""

        f.replace_in_file(source_file, source, target)
        l.bullet("Applied: rust wasm build target", l.GREEN)
    else:
        l.bullet("Skipped: rust wasm build target", l.PURPLE)


# -----------------------------------------------------------------------------
def _patch_wasm_flag(source_dir):
    source_file = os.path.join(source_dir, "build", "config", "BUILDCONFIG.gn")

    target = 'is_wasm = current_os == "emscripten" || current_os == "wasm32"'
    line_number = f.get_file_line_number_with_content(source_file, target, strip=True)

    if line_number:
        l.bullet("Skipped: rust wasm is_wasm flag", l.PURPLE)
        return

    f.replace_in_file(
        source_file,
        'is_wasm = current_os == "emscripten"',
        target,
    )
    l.bullet("Applied: rust wasm is_wasm flag", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_compiler_config(source_dir):
    source_file = os.path.join(source_dir, "build", "config", "compiler", "BUILD.gn")

    line_content = 'configs += [ "//build/config/rust_wasm:compiler" ]'
    line_number = f.get_file_line_number_with_content(
        source_file, line_content, strip=True
    )

    if not line_number:
        source = """} else if (current_os == "emscripten") {
    configs += [ "//build/config/wasm:compiler" ]
  }"""

        target = """} else if (current_os == "emscripten") {
    configs += [ "//build/config/wasm:compiler" ]
  } else if (current_os == "wasm32") {
    configs += [ "//build/config/rust_wasm:compiler" ]
  }"""

        if f.file_has_content(source_file, source):
            f.replace_in_file(source_file, source, target)
        else:
            source = """} else if (is_mac) {
    configs += [ "//build/config/mac:compiler" ]
  }"""

            target = """} else if (is_mac) {
    configs += [ "//build/config/mac:compiler" ]
  } else if (current_os == "wasm32") {
    configs += [ "//build/config/rust_wasm:compiler" ]
  }"""

            f.replace_in_file(source_file, source, target)

        f.replace_in_file(
            source_file,
            'if (current_os != "aix") {',
            'if (current_os != "aix" && current_os != "wasm32") {',
        )
        l.bullet("Applied: rust wasm compiler", l.GREEN)
    else:
        l.bullet("Skipped: rust wasm compiler", l.PURPLE)


# -----------------------------------------------------------------------------
def _patch_emscripten_link_flags(source_dir):
    source_file = os.path.join(source_dir, "build", "config", "compiler", "BUILD.gn")

    target = 'if (is_wasm && current_os != "wasm32") {'
    line_number = f.get_file_line_number_with_content(source_file, target, strip=True)

    if line_number:
        l.bullet("Skipped: rust wasm emscripten link flags", l.PURPLE)
        return

    source = """  if (is_wasm) {
    ldflags += [
      "-s",
      "ALLOW_MEMORY_GROWTH=1",
      "-s",
      "LLD_REPORT_UNDEFINED=1",
    ]"""

    replacement = """  if (is_wasm && current_os != "wasm32") {
    ldflags += [
      "-s",
      "ALLOW_MEMORY_GROWTH=1",
      "-s",
      "LLD_REPORT_UNDEFINED=1",
    ]"""

    f.replace_in_file(source_file, source, replacement)
    l.bullet("Applied: rust wasm emscripten link flags", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_fxcrt_config(source_dir):
    source_file = os.path.join(source_dir, "core", "fxcrt", "BUILD.gn")
    line_content = '"cfx_fileaccess_wasm.cpp",'
    line_number = f.get_file_line_number_with_content(
        source_file, line_content, strip=True
    )

    if line_number and f.file_has_content(source_file, "if (is_posix && !is_wasm) {"):
        l.bullet("Skipped: rust wasm fxcrt", l.PURPLE)
        return

    replacement = """  if (is_posix && !is_wasm) {
    sources += [
      "cfx_fileaccess_posix.cpp",
      "cfx_fileaccess_posix.h",
      "fx_folder_posix.cpp",
    ]
  }
  if (is_wasm) {
    sources += [
      "cfx_fileaccess_wasm.cpp",
      "fx_folder_wasm.cpp",
    ]
  }"""

    if f.file_has_content(source_file, "if (is_posix || is_wasm) {"):
        source = """  if (is_posix || is_wasm) {
    sources += [
      "cfx_fileaccess_posix.cpp",
      "cfx_fileaccess_posix.h",
      "fx_folder_posix.cpp",
    ]
  }"""
    elif line_number:
        source = """  if (is_posix) {
    sources += [
      "cfx_fileaccess_posix.cpp",
      "cfx_fileaccess_posix.h",
      "fx_folder_posix.cpp",
    ]
  }
  if (is_wasm) {
    sources += [
      "cfx_fileaccess_wasm.cpp",
      "fx_folder_wasm.cpp",
    ]
  }"""
    else:
        source = """  if (is_posix) {
    sources += [
      "cfx_fileaccess_posix.cpp",
      "cfx_fileaccess_posix.h",
      "fx_folder_posix.cpp",
    ]
  }"""

    f.replace_in_file(source_file, source, replacement)
    l.bullet("Applied: rust wasm fxcrt", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_fxge_config(source_dir):
    source_file = os.path.join(source_dir, "core", "fxge", "BUILD.gn")

    if f.file_has_content(source_file, 'sources += [ "wasm/fx_wasm_impl.cpp" ]'):
        l.bullet("Skipped: rust wasm fxge", l.PURPLE)
        return

    replacement = """  if (is_wasm) {
    sources -= [
      "cfx_folderfontinfo.cpp",
      "cfx_folderfontinfo.h",
    ]
    sources += [ "wasm/fx_wasm_impl.cpp" ]
  } else if (is_linux || is_chromeos) {
    sources += [ "linux/fx_linux_impl.cpp" ]
  }"""

    if f.file_has_content(source_file, "if (is_linux || is_chromeos || is_wasm) {"):
        source = """  if (is_linux || is_chromeos || is_wasm) {
    sources += [ "linux/fx_linux_impl.cpp" ]
  }"""
    else:
        source = """  if (is_linux || is_chromeos) {
    sources += [ "linux/fx_linux_impl.cpp" ]
  }"""

    f.replace_in_file(source_file, source, replacement)
    l.bullet("Applied: rust wasm fxge", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_icu_config(source_dir):
    source_file = os.path.join(source_dir, "third_party", "icu", "BUILD.gn")
    line_content = '"U_HAVE_MMAP=0",'
    line_number = f.get_file_line_number_with_content(
        source_file, line_content, strip=True
    )

    if line_number:
        l.bullet("Skipped: rust wasm ICU", l.PURPLE)
        return

    wasm_block_line = f.get_file_line_number_with_content(
        source_file, 'if (current_os == "wasm32") {', strip=True
    )
    if wasm_block_line:
        f.replace_in_file(
            source_file,
            '"U_HAVE_TZNAME=0",',
            '"U_HAVE_TZNAME=0",\n      "U_HAVE_MMAP=0",',
        )
        l.bullet("Applied: rust wasm ICU", l.GREEN)
        return

    source = """  if (current_cpu == "wasm") {
    # Tell ICU that we are a 32 bit platform, otherwise,
    # double-conversion-utils.h doesn't know how to operate.
    defines += [ "__i386__" ]
  }
}"""

    target = """  if (current_cpu == "wasm") {
    # Tell ICU that we are a 32 bit platform, otherwise,
    # double-conversion-utils.h doesn't know how to operate.
    defines += [ "__i386__" ]
  }

  if (current_os == "wasm32") {
    defines += [
      "U_HAVE_TZSET=0",
      "U_HAVE_TIMEZONE=0",
      "U_HAVE_TZNAME=0",
      "U_HAVE_MMAP=0",
    ]
  }
}"""

    f.replace_in_file(source_file, source, target)
    l.bullet("Applied: rust wasm ICU", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_freetype_config(source_dir):
    source_file = os.path.join(source_dir, "third_party", "BUILD.gn")

    if f.file_has_content(
        source_file,
        '"FT_CONFIG_STANDARD_LIBRARY_H=\\"freetype-custom-config/ftstdlib-wasm.h\\"",',
    ):
        l.bullet("Skipped: rust wasm FreeType", l.PURPLE)
        return

    source = """    defines = [
      # GN currently does not escape '<' and '>' when generating xml based
      # Visual Studio project files. As a result, use quotes instead of pointy
      # brackets in these defines.
      "FT_CONFIG_MODULES_H=\\"freetype-custom-config/ftmodule.h\\"",
      "FT_CONFIG_OPTIONS_H=\\"freetype-custom-config/ftoption.h\\"",
    ]"""

    target = """    defines = [
      # GN currently does not escape '<' and '>' when generating xml based
      # Visual Studio project files. As a result, use quotes instead of pointy
      # brackets in these defines.
      "FT_CONFIG_MODULES_H=\\"freetype-custom-config/ftmodule.h\\"",
      "FT_CONFIG_OPTIONS_H=\\"freetype-custom-config/ftoption.h\\"",
    ]

    if (current_os == "wasm32") {
      defines += [
        "FT_CONFIG_STANDARD_LIBRARY_H=\\"freetype-custom-config/ftstdlib-wasm.h\\"",
      ]
    }"""

    f.replace_in_file(source_file, source, target)
    l.bullet("Applied: rust wasm FreeType", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_freetype_sources(source_dir):
    source_file = os.path.join(source_dir, "third_party", "BUILD.gn")

    if f.file_has_content(
        source_file, '"//third_party/freetype/src/src/base/ftsystem_wasm.c"'
    ):
        l.bullet("Skipped: rust wasm FreeType sources", l.PURPLE)
        return

    source = """      "//third_party/freetype/src/src/base/ftsystem.c",
      "//third_party/freetype/src/src/cff/cff.c","""

    target = """      "//third_party/freetype/src/src/base/ftsystem.c",
      "//third_party/freetype/src/src/cff/cff.c",
    ]

    if (current_os == "wasm32") {
      sources -= [ "//third_party/freetype/src/src/base/ftsystem.c" ]
      sources += [ "//third_party/freetype/src/src/base/ftsystem_wasm.c" ]
    }

    sources += ["""

    f.replace_in_file(source_file, source, target)
    l.bullet("Applied: rust wasm FreeType sources", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_zlib_config(source_dir):
    source_file = os.path.join(source_dir, "third_party", "zlib", "BUILD.gn")

    if f.file_has_content(source_file, 'sources -= [\n      "gzclose.c",'):
        l.bullet("Skipped: rust wasm zlib", l.PURPLE)
        return

    source = """    "zutil.c",
    "zutil.h",
  ]"""

    target = """    "zutil.c",
    "zutil.h",
  ]

  if (current_os == "wasm32") {
    sources -= [
      "gzclose.c",
      "gzlib.c",
      "gzread.c",
      "gzwrite.c",
    ]
  }"""

    f.replace_in_file(source_file, source, target)
    l.bullet("Applied: rust wasm zlib", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_lcms_config(source_dir):
    source_file = os.path.join(source_dir, "third_party", "BUILD.gn")

    if f.file_has_content(source_file, '"lcms/src/cms_wasm_stubs.c"'):
        l.bullet("Skipped: rust wasm LittleCMS", l.PURPLE)
        return

    source = """  sources = [
    "lcms/include/lcms2.h","""

    target = """  defines = []
  sources = [
    "lcms/include/lcms2.h","""

    f.replace_in_file(source_file, source, target)

    source = """    "lcms/src/cmsxform.c",
  ]"""

    target = """    "lcms/src/cmsxform.c",
  ]

  if (current_os == "wasm32") {
    defines += [
      "CMS_NO_PTHREADS=1",
      "fopen=pdfium_wasm_lcms_fopen",
      "fread=pdfium_wasm_lcms_fread",
      "fwrite=pdfium_wasm_lcms_fwrite",
      "fclose=pdfium_wasm_lcms_fclose",
      "fseek=pdfium_wasm_lcms_fseek",
      "ftell=pdfium_wasm_lcms_ftell",
      "remove=pdfium_wasm_lcms_remove",
      "time=pdfium_wasm_lcms_time",
      "gmtime=pdfium_wasm_lcms_gmtime",
      "ctime=pdfium_wasm_lcms_ctime",
    ]
    sources += [ "lcms/src/cms_wasm_stubs.c" ]
  }"""

    f.replace_in_file(source_file, source, target)
    l.bullet("Applied: rust wasm LittleCMS", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_abseil_config(source_dir):
    source_file = os.path.join(
        source_dir, "third_party", "abseil-cpp", "absl", "debugging", "BUILD.gn"
    )
    line_content = '"internal/examine_stack_wasm.cc"'
    line_number = f.get_file_line_number_with_content(
        source_file, line_content, strip=True
    )

    if line_number:
        l.bullet("Skipped: rust wasm Abseil", l.PURPLE)
        return

    f.replace_in_file(
        source_file,
        """absl_source_set("examine_stack") {
  sources = [ "internal/examine_stack.cc" ]""",
        """absl_source_set("examine_stack") {
  sources = []
  if (current_os == "wasm32") {
    sources += [ "internal/examine_stack_wasm.cc" ]
  } else {
    sources += [ "internal/examine_stack.cc" ]
  }""",
    )
    f.replace_in_file(
        source_file,
        """absl_source_set("failure_signal_handler") {
  sources = [ "failure_signal_handler.cc" ]""",
        """absl_source_set("failure_signal_handler") {
  sources = []
  if (current_os == "wasm32") {
    sources += [ "failure_signal_handler_wasm.cc" ]
  } else {
    sources += [ "failure_signal_handler.cc" ]
  }""",
    )
    l.bullet("Applied: rust wasm Abseil", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_abseil_base_config(source_dir):
    source_file = os.path.join(
        source_dir, "third_party", "abseil-cpp", "absl", "base", "BUILD.gn"
    )

    if f.file_has_content(source_file, '"internal/sysinfo_wasm.cc"'):
        l.bullet("Skipped: rust wasm Abseil base", l.PURPLE)
        return

    source = """    "internal/spinlock.cc",
    "internal/sysinfo.cc",
    "internal/thread_identity.cc","""

    target = """    "internal/spinlock.cc",
    "internal/sysinfo.cc",
    "internal/thread_identity.cc",
  ]

  if (current_os == "wasm32") {
    sources -= [ "internal/sysinfo.cc" ]
    sources += [ "internal/sysinfo_wasm.cc" ]
  }

  sources += ["""

    f.replace_in_file(source_file, source, target)
    l.bullet("Applied: rust wasm Abseil base", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_abseil_random_config(source_dir):
    source_file = os.path.join(
        source_dir,
        "third_party",
        "abseil-cpp",
        "absl",
        "random",
        "internal",
        "BUILD.gn",
    )

    if f.file_has_content(source_file, '"seed_material_wasm.cc"'):
        l.bullet("Skipped: rust wasm Abseil random", l.PURPLE)
        return

    source = """  public = [ "seed_material.h" ]
  sources = [ "seed_material.cc" ]"""

    target = """  public = [ "seed_material.h" ]
  sources = []
  if (current_os == "wasm32") {
    sources += [ "seed_material_wasm.cc" ]
  } else {
    sources += [ "seed_material.cc" ]
  }"""

    f.replace_in_file(source_file, source, target)
    l.bullet("Applied: rust wasm Abseil random", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_abseil_time_config(source_dir):
    source_file = os.path.join(
        source_dir,
        "third_party",
        "abseil-cpp",
        "absl",
        "time",
        "internal",
        "cctz",
        "BUILD.gn",
    )

    if f.file_has_content(source_file, '"src/time_zone_if_wasm.cc"'):
        l.bullet("Skipped: rust wasm Abseil time", l.PURPLE)
        return

    source = """    "src/zone_info_source.cc",
  ]"""

    target = """    "src/zone_info_source.cc",
  ]

  if (current_os == "wasm32") {
    sources -= [
      "src/time_zone_if.cc",
      "src/time_zone_info.cc",
      "src/time_zone_info.h",
      "src/time_zone_libc.cc",
      "src/time_zone_libc.h",
      "src/time_zone_lookup.cc",
      "src/tzfile.h",
      "src/zone_info_source.cc",
    ]
    sources += [
      "src/time_zone_if_wasm.cc",
      "src/time_zone_lookup_wasm.cc",
    ]
  }"""

    f.replace_in_file(source_file, source, target)
    l.bullet("Applied: rust wasm Abseil time", l.GREEN)


# -----------------------------------------------------------------------------
def _write_abseil_wasm_debugging(source_dir):
    examine_stack_file = os.path.join(
        source_dir,
        "third_party",
        "abseil-cpp",
        "absl",
        "debugging",
        "internal",
        "examine_stack_wasm.cc",
    )
    failure_signal_file = os.path.join(
        source_dir,
        "third_party",
        "abseil-cpp",
        "absl",
        "debugging",
        "failure_signal_handler_wasm.cc",
    )

    examine_stack_content = """#include "absl/debugging/internal/examine_stack.h"

#include "absl/base/attributes.h"

namespace absl {
ABSL_NAMESPACE_BEGIN
namespace debugging_internal {

namespace {
ABSL_CONST_INIT SymbolizeUrlEmitter debug_stack_trace_hook = nullptr;
}

void RegisterDebugStackTraceHook(SymbolizeUrlEmitter hook) {
  debug_stack_trace_hook = hook;
}

SymbolizeUrlEmitter GetDebugStackTraceHook() {
  return debug_stack_trace_hook;
}

void* GetProgramCounter(void* const vuc) {
  (void)vuc;
  return nullptr;
}

void DumpPCAndFrameSizesAndStackTrace(void* const pc,
                                      void* const stack[],
                                      int frame_sizes[],
                                      int depth,
                                      int min_dropped_frames,
                                      bool symbolize_stacktrace,
                                      OutputWriter* writer,
                                      void* writer_arg) {
  (void)pc;
  (void)stack;
  (void)frame_sizes;
  (void)depth;
  (void)min_dropped_frames;
  (void)symbolize_stacktrace;
  (void)writer;
  (void)writer_arg;
}

void DumpStackTrace(int min_dropped_frames,
                    int max_num_frames,
                    bool symbolize_stacktrace,
                    OutputWriter* writer,
                    void* writer_arg) {
  (void)min_dropped_frames;
  (void)max_num_frames;
  (void)symbolize_stacktrace;
  (void)writer;
  (void)writer_arg;
}

}  // namespace debugging_internal
ABSL_NAMESPACE_END
}  // namespace absl
"""

    failure_signal_content = """#include "absl/debugging/failure_signal_handler.h"

namespace absl {
ABSL_NAMESPACE_BEGIN

void InstallFailureSignalHandler(const FailureSignalHandlerOptions& options) {
  (void)options;
}

namespace debugging_internal {

const char* FailureSignalToString(int signo) {
  (void)signo;
  return "";
}

}  // namespace debugging_internal

ABSL_NAMESPACE_END
}  // namespace absl
"""

    f.set_file_content(examine_stack_file, examine_stack_content)
    f.set_file_content(failure_signal_file, failure_signal_content)
    l.bullet("Applied: rust wasm Abseil debugging", l.GREEN)


# -----------------------------------------------------------------------------
def _write_abseil_wasm_base(source_dir):
    source_file = os.path.join(
        source_dir,
        "third_party",
        "abseil-cpp",
        "absl",
        "base",
        "internal",
        "sysinfo_wasm.cc",
    )

    content = """#include "absl/base/internal/sysinfo.h"

#include "absl/base/config.h"

namespace absl {
ABSL_NAMESPACE_BEGIN
namespace base_internal {

int NumCPUs() {
  return 1;
}

double NominalCPUFrequency() {
  return 1.0;
}

pid_t GetTID() {
  return 1;
}

pid_t GetCachedTID() {
  return GetTID();
}

}  // namespace base_internal
ABSL_NAMESPACE_END
}  // namespace absl
"""

    f.set_file_content(source_file, content)
    l.bullet("Applied: rust wasm Abseil base", l.GREEN)


# -----------------------------------------------------------------------------
def _write_abseil_wasm_random(source_dir):
    source_file = os.path.join(
        source_dir,
        "third_party",
        "abseil-cpp",
        "absl",
        "random",
        "internal",
        "seed_material_wasm.cc",
    )

    content = """#include "absl/random/internal/seed_material.h"

#include <cassert>
#include <cstdint>

#include "absl/base/config.h"
#include "absl/types/optional.h"
#include "absl/types/span.h"

namespace absl {
ABSL_NAMESPACE_BEGIN
namespace random_internal {

bool ReadSeedMaterialFromOSEntropy(absl::Span<uint32_t> values) {
  assert(values.data() != nullptr);
  if (values.data() == nullptr) {
    return false;
  }
  return values.empty();
}

void MixIntoSeedMaterial(absl::Span<const uint32_t> sequence,
                         absl::Span<uint32_t> seed_material) {
  constexpr uint32_t kInitVal = 0x43b0d7e5;
  constexpr uint32_t kHashMul = 0x931e8875;
  constexpr uint32_t kMixMulL = 0xca01f9dd;
  constexpr uint32_t kMixMulR = 0x4973f715;
  constexpr uint32_t kShiftSize = sizeof(uint32_t) * 8 / 2;

  uint32_t hash_const = kInitVal;
  auto hash = [&](uint32_t value) {
    value ^= hash_const;
    hash_const *= kHashMul;
    value *= hash_const;
    value ^= value >> kShiftSize;
    return value;
  };

  auto mix = [&](uint32_t x, uint32_t y) {
    uint32_t result = kMixMulL * x - kMixMulR * y;
    result ^= result >> kShiftSize;
    return result;
  };

  for (const auto& seq_val : sequence) {
    for (auto& elem : seed_material) {
      elem = mix(elem, hash(seq_val));
    }
  }
}

absl::optional<uint32_t> GetSaltMaterial() {
  return absl::nullopt;
}

}  // namespace random_internal
ABSL_NAMESPACE_END
}  // namespace absl
"""

    f.set_file_content(source_file, content)
    l.bullet("Applied: rust wasm Abseil random", l.GREEN)


# -----------------------------------------------------------------------------
def _write_abseil_wasm_time(source_dir):
    cctz_dir = os.path.join(
        source_dir,
        "third_party",
        "abseil-cpp",
        "absl",
        "time",
        "internal",
        "cctz",
        "src",
    )
    time_zone_if_file = os.path.join(cctz_dir, "time_zone_if_wasm.cc")
    time_zone_lookup_file = os.path.join(cctz_dir, "time_zone_lookup_wasm.cc")

    time_zone_if_content = """#include "absl/time/internal/cctz/src/time_zone_if.h"

#include <memory>
#include <string>

#include "absl/base/config.h"
#include "absl/time/internal/cctz/src/time_zone_fixed.h"

namespace absl {
ABSL_NAMESPACE_BEGIN
namespace time_internal {
namespace cctz {

namespace {

class WasmFixedTimeZone : public TimeZoneIf {
 public:
  explicit WasmFixedTimeZone(seconds offset)
      : offset_(offset), name_(FixedOffsetToName(offset)),
        abbr_(FixedOffsetToAbbr(offset)) {}

  time_zone::absolute_lookup BreakTime(
      const time_point<seconds>& tp) const override {
    const auto shifted = civil_second() + ToUnixSeconds(tp) + offset_.count();
    return {shifted, static_cast<int>(offset_.count()), false, abbr_.c_str()};
  }

  time_zone::civil_lookup MakeTime(const civil_second& cs) const override {
    const time_point<seconds> tp =
        FromUnixSeconds(cs - civil_second() - offset_.count());
    return {time_zone::civil_lookup::UNIQUE, tp, tp, tp};
  }

  bool NextTransition(const time_point<seconds>&,
                      time_zone::civil_transition*) const override {
    return false;
  }

  bool PrevTransition(const time_point<seconds>&,
                      time_zone::civil_transition*) const override {
    return false;
  }

  std::string Version() const override {
    return std::string();
  }

  std::string Description() const override {
    return name_;
  }

 private:
  seconds offset_;
  std::string name_;
  std::string abbr_;
};

}  // namespace

std::unique_ptr<TimeZoneIf> TimeZoneIf::UTC() {
  return std::unique_ptr<TimeZoneIf>(new WasmFixedTimeZone(seconds::zero()));
}

std::unique_ptr<TimeZoneIf> TimeZoneIf::Make(const std::string& name) {
  seconds offset;
  if (FixedOffsetFromName(name, &offset)) {
    return std::unique_ptr<TimeZoneIf>(new WasmFixedTimeZone(offset));
  }
  return nullptr;
}

TimeZoneIf::~TimeZoneIf() {}

}  // namespace cctz
}  // namespace time_internal
ABSL_NAMESPACE_END
}  // namespace absl
"""

    time_zone_lookup_content = """#include "absl/time/internal/cctz/include/cctz/time_zone.h"

#include <string>

#include "absl/base/config.h"
#include "absl/time/internal/cctz/src/time_zone_fixed.h"
#include "absl/time/internal/cctz/src/time_zone_impl.h"

namespace absl {
ABSL_NAMESPACE_BEGIN
namespace time_internal {
namespace cctz {

std::string time_zone::name() const { return effective_impl().Name(); }

time_zone::absolute_lookup time_zone::lookup(
    const time_point<seconds>& tp) const {
  return effective_impl().BreakTime(tp);
}

time_zone::civil_lookup time_zone::lookup(const civil_second& cs) const {
  return effective_impl().MakeTime(cs);
}

bool time_zone::next_transition(const time_point<seconds>& tp,
                                civil_transition* trans) const {
  return effective_impl().NextTransition(tp, trans);
}

bool time_zone::prev_transition(const time_point<seconds>& tp,
                                civil_transition* trans) const {
  return effective_impl().PrevTransition(tp, trans);
}

std::string time_zone::version() const { return effective_impl().Version(); }

std::string time_zone::description() const {
  return effective_impl().Description();
}

const time_zone::Impl& time_zone::effective_impl() const {
  if (impl_ == nullptr) {
    return *time_zone::Impl::UTC().impl_;
  }
  return *impl_;
}

bool load_time_zone(const std::string& name, time_zone* tz) {
  return time_zone::Impl::LoadTimeZone(name, tz);
}

time_zone utc_time_zone() {
  return time_zone::Impl::UTC();
}

time_zone fixed_time_zone(const seconds& offset) {
  time_zone tz;
  load_time_zone(FixedOffsetToName(offset), &tz);
  return tz;
}

time_zone local_time_zone() {
  return utc_time_zone();
}

}  // namespace cctz
}  // namespace time_internal
ABSL_NAMESPACE_END
}  // namespace absl
"""

    f.set_file_content(time_zone_if_file, time_zone_if_content)
    f.set_file_content(time_zone_lookup_file, time_zone_lookup_content)
    l.bullet("Applied: rust wasm Abseil time", l.GREEN)


# -----------------------------------------------------------------------------
def _write_lcms_wasm_stubs(source_dir):
    source_file = os.path.join(
        source_dir,
        "third_party",
        "lcms",
        "src",
        "cms_wasm_stubs.c",
    )

    content = """#include <stddef.h>
#include <stdio.h>
#include <time.h>

#undef fopen
#undef fread
#undef fwrite
#undef fclose
#undef fseek
#undef ftell
#undef remove
#undef time
#undef gmtime
#undef ctime

FILE* pdfium_wasm_lcms_fopen(const char* filename, const char* mode) {
  (void)filename;
  (void)mode;
  return NULL;
}

size_t pdfium_wasm_lcms_fread(void* buffer,
                              size_t size,
                              size_t count,
                              FILE* stream) {
  (void)buffer;
  (void)size;
  (void)count;
  (void)stream;
  return 0;
}

size_t pdfium_wasm_lcms_fwrite(const void* buffer,
                               size_t size,
                               size_t count,
                               FILE* stream) {
  (void)buffer;
  (void)size;
  (void)count;
  (void)stream;
  return 0;
}

int pdfium_wasm_lcms_fclose(FILE* stream) {
  (void)stream;
  return 0;
}

int pdfium_wasm_lcms_fseek(FILE* stream, long offset, int origin) {
  (void)stream;
  (void)offset;
  (void)origin;
  return -1;
}

long pdfium_wasm_lcms_ftell(FILE* stream) {
  (void)stream;
  return -1L;
}

int pdfium_wasm_lcms_remove(const char* filename) {
  (void)filename;
  return -1;
}

time_t pdfium_wasm_lcms_time(time_t* timer) {
  if (timer != NULL) {
    *timer = 0;
  }
  return 0;
}

struct tm* pdfium_wasm_lcms_gmtime(const time_t* timer) {
  static struct tm epoch;
  (void)timer;
  epoch.tm_year = 70;
  epoch.tm_mday = 1;
  return &epoch;
}

char* pdfium_wasm_lcms_ctime(const time_t* timer) {
  (void)timer;
  return "Thu Jan  1 00:00:00 1970\\n";
}
"""

    f.set_file_content(source_file, content)
    l.bullet("Applied: rust wasm LittleCMS stubs", l.GREEN)


# -----------------------------------------------------------------------------
def _write_fxcrt_wasm_files(source_dir):
    file_access_file = os.path.join(
        source_dir, "core", "fxcrt", "cfx_fileaccess_wasm.cpp"
    )
    folder_file = os.path.join(source_dir, "core", "fxcrt", "fx_folder_wasm.cpp")

    file_access_content = """// Copyright 2026 The PDFium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "core/fxcrt/fileaccess_iface.h"

#include <memory>

namespace {

class CFX_FileAccess_Wasm final : public FileAccessIface {
 public:
  bool Open(ByteStringView fileName) override {
    (void)fileName;
    return false;
  }

  void Close() override {}
  FX_FILESIZE GetSize() const override { return 0; }
  FX_FILESIZE GetPosition() const override { return static_cast<FX_FILESIZE>(-1); }

  FX_FILESIZE SetPosition(FX_FILESIZE pos) override {
    (void)pos;
    return static_cast<FX_FILESIZE>(-1);
  }

  size_t Read(pdfium::span<uint8_t> buffer) override {
    (void)buffer;
    return 0;
  }

  size_t Write(pdfium::span<const uint8_t> buffer) override {
    (void)buffer;
    return 0;
  }

  size_t ReadPos(pdfium::span<uint8_t> buffer, FX_FILESIZE pos) override {
    (void)buffer;
    (void)pos;
    return 0;
  }

  bool Flush() override { return false; }

  bool Truncate(FX_FILESIZE szFile) override {
    (void)szFile;
    return false;
  }
};

}  // namespace

// static
std::unique_ptr<FileAccessIface> FileAccessIface::Create() {
  return std::make_unique<CFX_FileAccess_Wasm>();
}
"""

    folder_content = """// Copyright 2026 The PDFium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "core/fxcrt/fx_folder.h"

#include <memory>

// static
std::unique_ptr<FX_Folder> FX_Folder::OpenFolder(const ByteString& path) {
  (void)path;
  return nullptr;
}
"""

    f.set_file_content(file_access_file, file_access_content)
    f.set_file_content(folder_file, folder_content)
    l.bullet("Applied: rust wasm fxcrt file access", l.GREEN)


# -----------------------------------------------------------------------------
def _write_fxge_wasm_platform(source_dir):
    source_file = os.path.join(source_dir, "core", "fxge", "wasm", "fx_wasm_impl.cpp")

    content = """// Copyright 2026 The PDFium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <memory>

#include "core/fxcrt/bytestring.h"
#include "core/fxcrt/fx_codepage_forward.h"
#include "core/fxge/cfx_gemodule.h"
#include "core/fxge/systemfontinfo_iface.h"

namespace {

class CFX_WasmFontInfo final : public SystemFontInfoIface {
 public:
  void EnumFontList(CFX_FontMapper* pMapper) override { (void)pMapper; }

  void* MapFont(int weight,
                bool bItalic,
                FX_Charset charset,
                int pitch_family,
                const ByteString& face) override {
    (void)weight;
    (void)bItalic;
    (void)charset;
    (void)pitch_family;
    (void)face;
    return nullptr;
  }

  void* GetFont(const ByteString& face) override {
    (void)face;
    return nullptr;
  }

  size_t GetFontData(void* hFont,
                     uint32_t table,
                     pdfium::span<uint8_t> buffer) override {
    (void)hFont;
    (void)table;
    (void)buffer;
    return 0;
  }

  bool GetFaceName(void* hFont, ByteString* name) override {
    (void)hFont;
    (void)name;
    return false;
  }

  bool GetFontCharset(void* hFont, FX_Charset* charset) override {
    (void)hFont;
    (void)charset;
    return false;
  }

  void DeleteFont(void* hFont) override { (void)hFont; }
};

class CWasmPlatform final : public CFX_GEModule::PlatformIface {
 public:
  void Init() override {}

  std::unique_ptr<SystemFontInfoIface> CreateDefaultSystemFontInfo() override {
    return std::make_unique<CFX_WasmFontInfo>();
  }
};

}  // namespace

// static
std::unique_ptr<CFX_GEModule::PlatformIface>
CFX_GEModule::PlatformIface::Create() {
  return std::make_unique<CWasmPlatform>();
}
"""

    f.set_file_content(source_file, content)
    l.bullet("Applied: rust wasm fxge platform", l.GREEN)


# -----------------------------------------------------------------------------
def _write_freetype_wasm_stdlib(source_dir):
    source_file = os.path.join(
        source_dir,
        "third_party",
        "freetype",
        "include",
        "freetype-custom-config",
        "ftstdlib-wasm.h",
    )

    content = """#ifndef FTSTDLIB_WASM_H_
#define FTSTDLIB_WASM_H_

#include <limits.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ft_ptrdiff_t ptrdiff_t

#define FT_CHAR_BIT CHAR_BIT
#define FT_USHORT_MAX USHRT_MAX
#define FT_INT_MAX INT_MAX
#define FT_INT_MIN INT_MIN
#define FT_UINT_MAX UINT_MAX
#define FT_LONG_MIN LONG_MIN
#define FT_LONG_MAX LONG_MAX
#define FT_ULONG_MAX ULONG_MAX
#ifdef LLONG_MAX
#define FT_LLONG_MAX LLONG_MAX
#endif
#ifdef LLONG_MIN
#define FT_LLONG_MIN LLONG_MIN
#endif
#ifdef ULLONG_MAX
#define FT_ULLONG_MAX ULLONG_MAX
#endif

#define ft_memchr memchr
#define ft_memcmp memcmp
#define ft_memcpy memcpy
#define ft_memmove memmove
#define ft_memset memset
#define ft_strcat strcat
#define ft_strcmp strcmp
#define ft_strcpy strcpy
#define ft_strlen strlen
#define ft_strncmp strncmp
#define ft_strncpy strncpy
#define ft_strrchr strrchr
#define ft_strstr strstr

#define FT_FILE FILE
#define ft_fclose fclose
#define ft_fopen fopen
#define ft_fread fread
#define ft_fseek fseek
#define ft_ftell ftell
#define ft_snprintf snprintf

#define ft_qsort qsort

#define ft_scalloc calloc
#define ft_sfree free
#define ft_smalloc malloc
#define ft_srealloc realloc

#define ft_strtol strtol
#define ft_getenv getenv

typedef int ft_jmp_buf[1];

static inline void ft_wasm_longjmp(ft_jmp_buf buffer, int value) {
  (void)buffer;
  (void)value;
  __builtin_trap();
}

#define ft_longjmp ft_wasm_longjmp
#define ft_setjmp(buffer) 0

#endif /* FTSTDLIB_WASM_H_ */
"""

    f.set_file_content(source_file, content)
    l.bullet("Applied: rust wasm FreeType stdlib", l.GREEN)


# -----------------------------------------------------------------------------
def _write_freetype_wasm_system(source_dir):
    source_file = os.path.join(
        source_dir, "third_party", "freetype", "src", "src", "base", "ftsystem_wasm.c"
    )

    content = """/****************************************************************************
 *
 * ftsystem_wasm.c
 *
 *   Browser-oriented FreeType low-level system interface for Pdfium.
 *
 */

#include <ft2build.h>
#include FT_CONFIG_CONFIG_H
#include <freetype/internal/ftdebug.h>
#include <freetype/internal/ftobjs.h>
#include <freetype/internal/ftstream.h>
#include <freetype/fterrors.h>
#include <freetype/ftsystem.h>
#include <freetype/fttypes.h>

FT_CALLBACK_DEF( void* )
ft_alloc( FT_Memory  memory,
          long       size )
{
  FT_UNUSED( memory );

  return ft_smalloc( (size_t)size );
}

FT_CALLBACK_DEF( void* )
ft_realloc( FT_Memory  memory,
            long       cur_size,
            long       new_size,
            void*      block )
{
  FT_UNUSED( memory );
  FT_UNUSED( cur_size );

  return ft_srealloc( block, (size_t)new_size );
}

FT_CALLBACK_DEF( void )
ft_free( FT_Memory  memory,
         void*      block )
{
  FT_UNUSED( memory );

  ft_sfree( block );
}

#ifndef FT_CONFIG_OPTION_DISABLE_STREAM_SUPPORT

FT_BASE_DEF( FT_Error )
FT_Stream_Open( FT_Stream    stream,
                const char*  filepathname )
{
  if ( !stream )
    return FT_THROW( Invalid_Stream_Handle );

  stream->descriptor.pointer = NULL;
  stream->pathname.pointer   = (char*)filepathname;
  stream->base               = NULL;
  stream->pos                = 0;
  stream->read               = NULL;
  stream->close              = NULL;
  stream->size               = 0;

  return FT_THROW( Cannot_Open_Resource );
}

#endif /* !FT_CONFIG_OPTION_DISABLE_STREAM_SUPPORT */

#ifdef FT_DEBUG_MEMORY

extern FT_Int
ft_mem_debug_init( FT_Memory  memory );

extern void
ft_mem_debug_done( FT_Memory  memory );

#endif

FT_BASE_DEF( FT_Memory )
FT_New_Memory( void )
{
  FT_Memory  memory;


  memory = (FT_Memory)ft_smalloc( sizeof ( *memory ) );
  if ( memory )
  {
    memory->user    = NULL;
    memory->alloc   = ft_alloc;
    memory->realloc = ft_realloc;
    memory->free    = ft_free;
#ifdef FT_DEBUG_MEMORY
    ft_mem_debug_init( memory );
#endif
  }

  return memory;
}

FT_BASE_DEF( void )
FT_Done_Memory( FT_Memory  memory )
{
#ifdef FT_DEBUG_MEMORY
  ft_mem_debug_done( memory );
#endif
  ft_sfree( memory );
}
"""

    f.set_file_content(source_file, content)
    l.bullet("Applied: rust wasm FreeType system", l.GREEN)


# -----------------------------------------------------------------------------
def _write_rust_wasm_setjmp_header(source_dir):
    source_file = os.path.join(
        source_dir, "build", "config", "rust_wasm", "include", "setjmp.h"
    )

    content = """#ifndef RUST_WASM_SETJMP_H_
#define RUST_WASM_SETJMP_H_

#ifdef __cplusplus
extern "C" {
#endif

typedef int jmp_buf[1];

static inline int setjmp(jmp_buf buffer) {
  (void)buffer;
  return 0;
}

static inline void longjmp(jmp_buf buffer, int value) {
  (void)buffer;
  (void)value;
  __builtin_trap();
}

#ifdef __cplusplus
}
#endif

#endif /* RUST_WASM_SETJMP_H_ */
"""

    f.set_file_content(source_file, content)
    l.bullet("Applied: rust wasm setjmp shim", l.GREEN)


# -----------------------------------------------------------------------------
def _write_rust_wasm_config(source_dir):
    source_file = os.path.join(source_dir, "build", "config", "rust_wasm", "BUILD.gn")

    content = """declare_args() {
  rust_wasm_target = "wasm32-unknown-unknown"
  rust_wasm_sysroot = ""
  rust_wasm_sysroot_target = ""
}

config("compiler") {
  include_dirs = [ "//build/config/rust_wasm/include" ]

  defines = [
    "_POSIX_C_SOURCE=200112",
    "__wasi__",
  ]

  cflags = [
    "--target=$rust_wasm_target",
    "-nostdlib",
    "-fvisibility=hidden",
    "-Wno-unknown-warning-option",
  ]

  cflags_cc = [
    "--target=$rust_wasm_target",
    "-nostdlib",
    "-fno-exceptions",
    "-fno-rtti",
    "-Wno-unknown-warning-option",
  ]

  ldflags = [
    "--target=$rust_wasm_target",
    "-nostdlib",
  ]

  if (rust_wasm_sysroot != "") {
    cflags += [ "--sysroot=$rust_wasm_sysroot" ]
    cflags_c = [
      "-isystem",
      "$rust_wasm_sysroot/include/$rust_wasm_sysroot_target",
    ]
    cflags_cc += [
      "-nostdinc++",
      "-isystem",
      "$rust_wasm_sysroot/include/$rust_wasm_sysroot_target/c++/v1",
      "-isystem",
      "$rust_wasm_sysroot/include/$rust_wasm_sysroot_target",
    ]
    ldflags += [ "--sysroot=$rust_wasm_sysroot" ]
  }
}"""

    f.set_file_content(source_file, content)
    l.bullet("Applied: rust wasm config", l.GREEN)


# -----------------------------------------------------------------------------
def _get_rust_wasm_sysroot(target):
    sysroot_env = target.get("sysroot_env")

    if not sysroot_env:
        return None

    return os.getenv(sysroot_env)


# -----------------------------------------------------------------------------
def _get_rust_wasm_sysroot_target(target):
    sysroot_target_env = target.get("sysroot_target_env")

    if not sysroot_target_env:
        return None

    return os.getenv(sysroot_target_env)


# -----------------------------------------------------------------------------
def _write_rust_wasm_toolchain(source_dir):
    source_file = os.path.join(
        source_dir, "build", "toolchain", "rust_wasm", "BUILD.gn"
    )

    content = """import("//build/toolchain/gcc_toolchain.gni")

declare_args() {
  rust_wasm_clang = rebase_path("//third_party/llvm-build/Release+Asserts/bin/clang", root_build_dir)
  rust_wasm_clangxx = rebase_path("//third_party/llvm-build/Release+Asserts/bin/clang++", root_build_dir)
  rust_wasm_ar = rebase_path("//third_party/llvm-build/Release+Asserts/bin/llvm-ar", root_build_dir)
  rust_wasm_ld = rebase_path("//third_party/llvm-build/Release+Asserts/bin/wasm-ld", root_build_dir)
  rust_wasm_readelf = rebase_path("//third_party/llvm-build/Release+Asserts/bin/llvm-readelf", root_build_dir)
}

gcc_toolchain("wasm") {
  cc = rust_wasm_clang
  cxx = rust_wasm_clangxx
  ar = rust_wasm_ar
  ld = rust_wasm_ld
  readelf = rust_wasm_readelf

  toolchain_args = {
    current_cpu = "wasm"
    current_os = "wasm32"
    is_clang = true
  }
}"""

    f.set_file_content(source_file, content)
    l.bullet("Applied: rust wasm toolchain", l.GREEN)
