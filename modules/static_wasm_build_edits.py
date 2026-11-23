# Literal source edits for the Chromium 8125 static WebAssembly build.
EDITS = (
    (
        "core/fxcrt/BUILD.gn",
        """  } else {
    sources += [ "fx_memory_malloc.cpp" ]
  }
  if (is_posix) {
    sources += [
      "cfx_fileaccess_posix.cpp",
      "cfx_fileaccess_posix.h",
""",
        """  } else {
    sources += [ "fx_memory_malloc.cpp" ]
  }
  if (is_posix && !is_wasm) {
    sources += [
      "cfx_fileaccess_posix.cpp",
      "cfx_fileaccess_posix.h",
""",
    ),
    (
        "core/fxcrt/BUILD.gn",
        """      "mapped_data_bytes.h",
    ]
  }
  if (is_win) {
    sources += [
      "cfx_fileaccess_windows.cpp",
""",
        """      "mapped_data_bytes.h",
    ]
  }
  if (is_wasm) {
    defines = [
      "getpid=pdfium_wasm_fxcrt_getpid",
      "gettimeofday=pdfium_wasm_fxcrt_gettimeofday",
      "time=pdfium_wasm_fxcrt_time",
      "localtime=pdfium_wasm_fxcrt_localtime",
    ]
    sources += [
      "cfx_fileaccess_wasm.cpp",
      "fx_folder_wasm.cpp",
      "fx_wasm_time_random.cpp",
    ]
  }
  if (is_win) {
    sources += [
      "cfx_fileaccess_windows.cpp",
""",
    ),
    (
        "core/fxge/BUILD.gn",
        """    ]
  }

  if (is_linux || is_chromeos) {
    sources += [ "linux/fx_linux_impl.cpp" ]
  }

""",
        """    ]
  }

  if (is_wasm) {
    sources -= [
      "cfx_folderfontinfo.cpp",
      "cfx_folderfontinfo.h",
    ]
    sources += [ "wasm/fx_wasm_impl.cpp" ]
  } else if (is_linux || is_chromeos) {
    sources += [ "linux/fx_linux_impl.cpp" ]
  }

""",
    ),
    (
        "third_party/BUILD.gn",
        """      "FT_CONFIG_MODULES_H=\\"freetype-custom-config/ftmodule.h\\"",
      "FT_CONFIG_OPTIONS_H=\\"freetype-custom-config/ftoption.h\\"",
    ]
  }

  config("freetype_private_config") {
""",
        """      "FT_CONFIG_MODULES_H=\\"freetype-custom-config/ftmodule.h\\"",
      "FT_CONFIG_OPTIONS_H=\\"freetype-custom-config/ftoption.h\\"",
    ]

    if (current_os == "wasm32") {
      defines += [
        "FT_CONFIG_STANDARD_LIBRARY_H=\\"freetype-custom-config/ftstdlib-wasm.h\\"",
      ]
    }
  }

  config("freetype_private_config") {
""",
    ),
    (
        "third_party/BUILD.gn",
        """      "//third_party/freetype/src/src/base/ftmm.c",
      "//third_party/freetype/src/src/base/ftsystem.c",
      "//third_party/freetype/src/src/cff/cff.c",
      "//third_party/freetype/src/src/cff/cffobjs.h",
      "//third_party/freetype/src/src/cid/type1cid.c",
      "//third_party/freetype/src/src/psaux/psaux.c",
""",
        """      "//third_party/freetype/src/src/base/ftmm.c",
      "//third_party/freetype/src/src/base/ftsystem.c",
      "//third_party/freetype/src/src/cff/cff.c",
    ]

    if (current_os == "wasm32") {
      sources -= [ "//third_party/freetype/src/src/base/ftsystem.c" ]
      sources += [ "//third_party/freetype/src/src/base/ftsystem_wasm.c" ]
    }

    sources += [
      "//third_party/freetype/src/src/cff/cffobjs.h",
      "//third_party/freetype/src/src/cid/type1cid.c",
      "//third_party/freetype/src/src/psaux/psaux.c",
""",
    ),
    (
        "third_party/BUILD.gn",
        """    # Must be after no_chromium_code for warning flags to be ordered correctly.
    ":fx_lcms2_warnings",
  ]
  sources = [
    "lcms/src/include/lcms2.h",
    "lcms/src/include/lcms2_plugin.h",
""",
        """    # Must be after no_chromium_code for warning flags to be ordered correctly.
    ":fx_lcms2_warnings",
  ]
  defines = []
  sources = [
    "lcms/src/include/lcms2.h",
    "lcms/src/include/lcms2_plugin.h",
""",
    ),
    (
        "third_party/BUILD.gn",
        """    "lcms/src/src/cmsxform.c",
    "lcms/src/src/lcms2_internal.h",
  ]
  deps = [ "../core/fxcrt" ]
}

""",
        """    "lcms/src/src/cmsxform.c",
    "lcms/src/src/lcms2_internal.h",
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
  }
  deps = [ "../core/fxcrt" ]
}

""",
    ),
    (
        "third_party/BUILD.gn",
        """}

source_set("fx_libopenjpeg") {
  configs -= [ "//build/config/compiler:chromium_code" ]
  configs += [
    "//build/config/compiler:no_chromium_code",
""",
        """}

source_set("fx_libopenjpeg") {
  defines = []
  configs -= [ "//build/config/compiler:chromium_code" ]
  configs += [
    "//build/config/compiler:no_chromium_code",
""",
    ),
    (
        "third_party/BUILD.gn",
        """    "libopenjpeg/src/thread.h",
    "libopenjpeg/src/tls_keys.h",
  ]
  public_configs = [ ":fx_libopenjpeg_config" ]
  deps = [ "../core/fxcrt" ]
}
""",
        """    "libopenjpeg/src/thread.h",
    "libopenjpeg/src/tls_keys.h",
  ]

  if (current_os == "wasm32") {
    defines += [
      "fopen=pdfium_wasm_openjpeg_fopen",
      "fread=pdfium_wasm_openjpeg_fread",
      "fwrite=pdfium_wasm_openjpeg_fwrite",
      "fclose=pdfium_wasm_openjpeg_fclose",
      "fseek=pdfium_wasm_openjpeg_fseek",
      "ftell=pdfium_wasm_openjpeg_ftell",
      "fseeko=pdfium_wasm_openjpeg_fseeko",
      "ftello=pdfium_wasm_openjpeg_ftello",
      "getenv=pdfium_wasm_openjpeg_getenv",
      "fprintf=pdfium_wasm_openjpeg_fprintf",
    ]
    sources += [ "libopenjpeg/openjpeg_wasm_stubs.c" ]
  }
  public_configs = [ ":fx_libopenjpeg_config" ]
  deps = [ "../core/fxcrt" ]
}
""",
    ),
    (
        "build/config/BUILDCONFIG.gn",
        """  assert(
      false,
      "emscripten is not a supported target_os. It is available only as secondary toolchain.")
} else {
  assert(false, "Unsupported target_os: $target_os")
}
""",
        """  assert(
      false,
      "emscripten is not a supported target_os. It is available only as secondary toolchain.")
} else if (target_os == "wasm32") {
  _default_toolchain = "//build/toolchain/rust_wasm:$target_cpu"
} else {
  assert(false, "Unsupported target_os: $target_os")
}
""",
    ),
    (
        "build/config/BUILDCONFIG.gn",
        """is_ios = current_os == "ios"
is_linux = current_os == "linux"
is_mac = current_os == "mac"
is_wasm = current_os == "emscripten"
is_watchos = current_os == "watchos"
is_win = current_os == "win" || current_os == "winuwp"

""",
        """is_ios = current_os == "ios"
is_linux = current_os == "linux"
is_mac = current_os == "mac"
is_wasm = current_os == "emscripten" || current_os == "wasm32"
is_watchos = current_os == "watchos"
is_win = current_os == "win" || current_os == "winuwp"

""",
    ),
    (
        "build/config/compiler/BUILD.gn",
        """    configs += [ "//build/config/linux:compiler" ]
  } else if (is_mac) {
    configs += [ "//build/config/mac:compiler" ]
  } else if (is_ios) {
    configs += [ "//build/config/ios:compiler" ]
  } else if (is_fuchsia) {
""",
        """    configs += [ "//build/config/linux:compiler" ]
  } else if (is_mac) {
    configs += [ "//build/config/mac:compiler" ]
  } else if (current_os == "wasm32") {
    configs += [ "//build/config/rust_wasm:compiler" ]
  } else if (is_ios) {
    configs += [ "//build/config/ios:compiler" ]
  } else if (is_fuchsia) {
""",
    ),
    (
        "build/config/compiler/BUILD.gn",
        """      } else if (is_chromeos) {
        cflags += [ "-fstack-protector-strong" ]
      } else if (is_posix || is_fuchsia) {
        if (current_os != "aix") {
          # Not available on aix.
          cflags += [ "-fstack-protector" ]
        }
""",
        """      } else if (is_chromeos) {
        cflags += [ "-fstack-protector-strong" ]
      } else if (is_posix || is_fuchsia) {
        if (current_os != "aix" && current_os != "wasm32") {
          # Not available on aix.
          cflags += [ "-fstack-protector" ]
        }
""",
    ),
    (
        "build/config/compiler/BUILD.gn",
        """    cflags_cc += [ "-fexperimental-relative-c++-abi-vtables" ]
  }

  if (is_wasm) {
    ldflags += [
      "-s",
      "ALLOW_MEMORY_GROWTH=1",
""",
        """    cflags_cc += [ "-fexperimental-relative-c++-abi-vtables" ]
  }

  if (is_wasm && current_os != "wasm32") {
    ldflags += [
      "-s",
      "ALLOW_MEMORY_GROWTH=1",
""",
    ),
    (
        "build/gn_logs.gni",
        """  build_gn_logs += [ "### ios_sdk.gni ###" ] + ios_sdk_logs
  build_gn_logs += [ "" ]
}
if (target_os == "mac" || host_os == "mac") {
  import("//build/config/mac/mac_sdk.gni")
  build_gn_logs += [ "### mac_sdk.gni ###" ] + mac_sdk_logs
  build_gn_logs += [ "" ]
""",
        """  build_gn_logs += [ "### ios_sdk.gni ###" ] + ios_sdk_logs
  build_gn_logs += [ "" ]
}
if (target_os == "mac" || (host_os == "mac" && !is_wasm)) {
  import("//build/config/mac/mac_sdk.gni")
  build_gn_logs += [ "### mac_sdk.gni ###" ] + mac_sdk_logs
  build_gn_logs += [ "" ]
""",
    ),
    (
        "third_party/abseil-cpp/absl/base/BUILD.gn",
        """    "internal/spinlock.cc",
    "internal/sysinfo.cc",
    "internal/thread_identity.cc",
    "internal/unscaledcycleclock.cc",
  ]
  public = [
""",
        """    "internal/spinlock.cc",
    "internal/sysinfo.cc",
    "internal/thread_identity.cc",
  ]

  if (current_os == "wasm32") {
    sources -= [ "internal/sysinfo.cc" ]
    sources += [ "internal/sysinfo_wasm.cc" ]
  }

  sources += [
    "internal/unscaledcycleclock.cc",
  ]
  public = [
""",
    ),
    (
        "third_party/abseil-cpp/absl/debugging/BUILD.gn",
        """# absl_test("symbolize_test")

absl_source_set("examine_stack") {
  sources = [ "internal/examine_stack.cc" ]
  public = [ "internal/examine_stack.h" ]
  visibility = [
    ":*",
""",
        """# absl_test("symbolize_test")

absl_source_set("examine_stack") {
  sources = []
  if (current_os == "wasm32") {
    sources += [ "internal/examine_stack_wasm.cc" ]
  } else {
    sources += [ "internal/examine_stack.cc" ]
  }
  public = [ "internal/examine_stack.h" ]
  visibility = [
    ":*",
""",
    ),
    (
        "third_party/abseil-cpp/absl/debugging/BUILD.gn",
        """}

absl_source_set("failure_signal_handler") {
  sources = [ "failure_signal_handler.cc" ]
  public = [ "failure_signal_handler.h" ]
  deps = [
    ":examine_stack",
""",
        """}

absl_source_set("failure_signal_handler") {
  sources = []
  if (current_os == "wasm32") {
    sources += [ "failure_signal_handler_wasm.cc" ]
  } else {
    sources += [ "failure_signal_handler.cc" ]
  }
  public = [ "failure_signal_handler.h" ]
  deps = [
    ":examine_stack",
""",
    ),
    (
        "third_party/abseil-cpp/absl/log/internal/BUILD.gn",
        """
absl_source_set("globals") {
  sources = [ "globals.cc" ]
  public = [ "globals.h" ]
  visibility = [
    ":*",
""",
        """
absl_source_set("globals") {
  sources = [ "globals.cc" ]
  if (current_os == "wasm32") {
    defines = [ "fwrite=pdfium_wasm_absl_log_fwrite" ]
    sources += [ "globals_wasm_stubs.cc" ]
  }
  public = [ "globals.h" ]
  visibility = [
    ":*",
""",
    ),
    (
        "third_party/abseil-cpp/absl/random/internal/BUILD.gn",
        """}

absl_source_set("seed_material") {
  sources = [ "seed_material.cc" ]
  public = [ "seed_material.h" ]
  visibility = [
    ":*",
""",
        """}

absl_source_set("seed_material") {
  sources = []
  if (current_os == "wasm32") {
    sources += [ "seed_material_wasm.cc" ]
  } else {
    sources += [ "seed_material.cc" ]
  }
  public = [ "seed_material.h" ]
  visibility = [
    ":*",
""",
    ),
    (
        "third_party/abseil-cpp/absl/random/internal/BUILD.gn",
        """
absl_source_set("randen_hwaes_impl") {
  sources = [ "randen_hwaes.cc" ]
  public = [ "randen_hwaes.h" ]
  visibility = [
    ":*",
""",
        """
absl_source_set("randen_hwaes_impl") {
  sources = [ "randen_hwaes.cc" ]
  if (current_os == "wasm32") {
    defines = [ "fprintf=pdfium_wasm_absl_random_fprintf" ]
    sources += [ "randen_hwaes_wasm_stubs.cc" ]
  }
  public = [ "randen_hwaes.h" ]
  visibility = [
    ":*",
""",
    ),
    (
        "third_party/abseil-cpp/absl/strings/BUILD.gn",
        """    "internal/str_format/output.cc",
    "internal/str_format/parser.cc",
  ]
  public = [
    "internal/str_format/arg.h",
    "internal/str_format/bind.h",
""",
        """    "internal/str_format/output.cc",
    "internal/str_format/parser.cc",
  ]
  if (current_os == "wasm32") {
    defines = [ "fwrite=pdfium_wasm_absl_str_format_fwrite" ]
    sources += [ "internal/str_format/output_wasm_stubs.cc" ]
  }
  public = [
    "internal/str_format/arg.h",
    "internal/str_format/bind.h",
""",
    ),
    (
        "third_party/abseil-cpp/absl/synchronization/BUILD.gn",
        """    "mutex.cc",
    "notification.cc",
  ]
  public = [
    "barrier.h",
    "blocking_counter.h",
""",
        """    "mutex.cc",
    "notification.cc",
  ]
  if (current_os == "wasm32") {
    defines = [
      "pthread_cond_signal=pdfium_wasm_absl_pthread_cond_signal",
      "pthread_cond_timedwait=pdfium_wasm_absl_pthread_cond_timedwait",
      "pthread_cond_wait=pdfium_wasm_absl_pthread_cond_wait",
      "pthread_mutex_lock=pdfium_wasm_absl_pthread_mutex_lock",
      "pthread_mutex_unlock=pdfium_wasm_absl_pthread_mutex_unlock",
    ]
    sources += [ "internal/pthread_waiter_wasm_stubs.cc" ]
  }
  public = [
    "barrier.h",
    "blocking_counter.h",
""",
    ),
    (
        "third_party/abseil-cpp/absl/time/internal/cctz/BUILD.gn",
        """    "src/tzfile.h",
    "src/zone_info_source.cc",
  ]
  public = [
    "include/cctz/time_zone.h",
    "include/cctz/zone_info_source.h",
""",
        """    "src/tzfile.h",
    "src/zone_info_source.cc",
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
  }
  public = [
    "include/cctz/time_zone.h",
    "include/cctz/zone_info_source.h",
""",
    ),
    (
        "third_party/icu/BUILD.gn",
        """    # double-conversion-utils.h doesn't know how to operate.
    defines += [ "__i386__" ]
  }
}

# Config used to set default visibility to hidden.
""",
        """    # double-conversion-utils.h doesn't know how to operate.
    defines += [ "__i386__" ]
  }

  if (current_os == "wasm32") {
    defines += [
      "U_HAVE_TZSET=0",
      "U_HAVE_TIMEZONE=0",
      "U_HAVE_TZNAME=0",
      "U_HAVE_MMAP=0",
      "getenv=pdfium_wasm_icu_getenv",
      "gettimeofday=pdfium_wasm_icu_gettimeofday",
      "time=pdfium_wasm_icu_time",
      "fopen=pdfium_wasm_icu_fopen",
      "fread=pdfium_wasm_icu_fread",
      "fclose=pdfium_wasm_icu_fclose",
      "fseek=pdfium_wasm_icu_fseek",
      "ftell=pdfium_wasm_icu_ftell",
    ]
  }
}

# Config used to set default visibility to hidden.
""",
    ),
    (
        "third_party/icu/BUILD.gn",
        """      sources += [ "source/stubdata/stubdata.cpp" ]
    }

    defines += [ "U_ICUDATAENTRY_IN_COMMON" ]

    # TODO(fxbug.dev/42180987): workaround for toolchain issues, see bug
""",
        """      sources += [ "source/stubdata/stubdata.cpp" ]
    }

    if (current_os == "wasm32") {
      sources += [ "source/common/icu_wasm_stubs.cpp" ]
    }

    defines += [ "U_ICUDATAENTRY_IN_COMMON" ]

    # TODO(fxbug.dev/42180987): workaround for toolchain issues, see bug
""",
    ),
    (
        "third_party/libjpeg_turbo/BUILD.gn",
        """    "NO_PUTENV",
  ]

  configs += [
    ":libjpeg_config",
    ":libjpeg_simd_config",
""",
        """    "NO_PUTENV",
  ]

  if (current_os == "wasm32") {
    defines += [
      "fread=pdfium_wasm_libjpeg_fread",
      "fwrite=pdfium_wasm_libjpeg_fwrite",
      "fflush=pdfium_wasm_libjpeg_fflush",
      "fprintf=pdfium_wasm_libjpeg_fprintf",
    ]
    sources += [ "src/jpeg_wasm_stubs.c" ]
  }

  configs += [
    ":libjpeg_config",
    ":libjpeg_simd_config",
""",
    ),
    (
        "third_party/zlib/BUILD.gn",
        """    "zutil.h",
  ]

  defines = []
  deps = []

""",
        """    "zutil.h",
  ]

  if (current_os == "wasm32") {
    sources -= [
      "gzclose.c",
      "gzlib.c",
      "gzread.c",
      "gzwrite.c",
    ]
  }

  defines = []
  deps = []

""",
    ),
)

SOURCES = (
    "build/config/rust_wasm/BUILD.gn",
    "build/config/rust_wasm/include/setjmp.h",
    "build/toolchain/rust_wasm/BUILD.gn",
    "core/fxcrt/cfx_fileaccess_wasm.cpp",
    "core/fxcrt/fx_folder_wasm.cpp",
    "core/fxcrt/fx_wasm_time_random.cpp",
    "core/fxge/wasm/fx_wasm_impl.cpp",
    "third_party/abseil-cpp/absl/base/internal/sysinfo_wasm.cc",
    "third_party/abseil-cpp/absl/debugging/failure_signal_handler_wasm.cc",
    "third_party/abseil-cpp/absl/debugging/internal/examine_stack_wasm.cc",
    "third_party/abseil-cpp/absl/log/internal/globals_wasm_stubs.cc",
    "third_party/abseil-cpp/absl/random/internal/randen_hwaes_wasm_stubs.cc",
    "third_party/abseil-cpp/absl/random/internal/seed_material_wasm.cc",
    "third_party/abseil-cpp/absl/strings/internal/str_format/output_wasm_stubs.cc",
    "third_party/abseil-cpp/absl/synchronization/internal/pthread_waiter_wasm_stubs.cc",
    "third_party/abseil-cpp/absl/time/internal/cctz/src/time_zone_if_wasm.cc",
    "third_party/abseil-cpp/absl/time/internal/cctz/src/time_zone_lookup_wasm.cc",
    "third_party/freetype/include/freetype-custom-config/ftstdlib-wasm.h",
    "third_party/freetype/src/src/base/ftsystem_wasm.c",
    "third_party/icu/source/common/icu_wasm_stubs.cpp",
    "third_party/lcms/src/cms_wasm_stubs.c",
    "third_party/libjpeg_turbo/src/jpeg_wasm_stubs.c",
    "third_party/libopenjpeg/openjpeg_wasm_stubs.c",
)
