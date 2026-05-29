import os
import tarfile

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
    _patch_abseil_config(source_dir)
    _write_freetype_wasm_stdlib(source_dir)
    _write_abseil_wasm_debugging(source_dir)
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
    line_content = "if (is_posix || is_wasm) {"
    line_number = f.get_file_line_number_with_content(
        source_file, line_content, strip=True
    )

    if line_number:
        l.bullet("Skipped: rust wasm fxcrt", l.PURPLE)
        return

    f.replace_in_file(source_file, "if (is_posix) {", "if (is_posix || is_wasm) {")
    l.bullet("Applied: rust wasm fxcrt", l.GREEN)


# -----------------------------------------------------------------------------
def _patch_fxge_config(source_dir):
    source_file = os.path.join(source_dir, "core", "fxge", "BUILD.gn")
    line_content = "if (is_linux || is_chromeos || is_wasm) {"
    line_number = f.get_file_line_number_with_content(
        source_file, line_content, strip=True
    )

    if line_number:
        l.bullet("Skipped: rust wasm fxge", l.PURPLE)
        return

    f.replace_in_file(
        source_file,
        "if (is_linux || is_chromeos) {",
        "if (is_linux || is_chromeos || is_wasm) {",
    )
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
    line_content = 'FT_CONFIG_STANDARD_LIBRARY_H="freetype-custom-config/ftstdlib-wasm.h"'
    line_number = f.get_file_line_number_with_content(
        source_file, line_content, strip=True
    )

    if line_number:
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
