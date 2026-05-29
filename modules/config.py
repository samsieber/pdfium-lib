# general
debug = False
task = ""

# pdfium
pdfium_git_branch = "chromium/7623"
# ^ ref: https://pdfium.googlesource.com/pdfium/+/refs/heads/chromium/7623
# OBS 1: don't forget change in android docker file (docker/android/Dockerfile)
# OBS 2: don't forget change in wasm docker file (docker/wasm/Dockerfile)

# emsdk
emsdk_version = "4.0.15"
# OBS 1: don't forget change in wasm docker file (docker/wasm/Dockerfile)

# macos
configurations_macos = ["release"]
shared_lib_macos = False
targets_macos = [
    {"target_os": "macos", "target_cpu": "x64", "pdfium_os": "mac"},
    {"target_os": "macos", "target_cpu": "arm64", "pdfium_os": "mac"},
]

# ios
configurations_ios = ["release"]
shared_lib_ios = False
targets_ios = [
    {
        "target_os": "ios",
        "target_cpu": "arm64",
        "pdfium_os": "ios",
        "target_environment": "device",
    },
    {
        "target_os": "ios",
        "target_cpu": "x64",
        "pdfium_os": "ios",
        "target_environment": "simulator",
    },
    {
        "target_os": "ios",
        "target_cpu": "arm64",
        "pdfium_os": "ios",
        "target_environment": "simulator",
    },
]

# android
configurations_android = ["release"]
shared_lib_android = True
targets_android = [
    {
        "target_os": "android",
        "target_cpu": "arm",
        "pdfium_os": "android",
        "android_cpu": "armeabi-v7a",
    },
    {
        "target_os": "android",
        "target_cpu": "x86",
        "pdfium_os": "android",
        "android_cpu": "x86",
    },
    {
        "target_os": "android",
        "target_cpu": "arm64",
        "pdfium_os": "android",
        "android_cpu": "arm64-v8a",
    },
    {
        "target_os": "android",
        "target_cpu": "x64",
        "pdfium_os": "android",
        "android_cpu": "x86_64",
    },
]

# wasm
configurations_wasm = ["release"]
shared_lib_wasm = False
targets_wasm = [
    {"target_os": "emscripten", "target_cpu": "wasm", "pdfium_os": "emscripten"},
]

# rust wasm
configurations_rust_wasm = ["release"]
shared_lib_rust_wasm = False
targets_rust_wasm = [
    {
        "target_os": "wasm32",
        "target_cpu": "wasm",
        "pdfium_os": "wasm32",
        "rust_target": "wasm32-unknown-unknown",
        "sysroot_env": "RUST_WASM_SYSROOT",
        "sysroot_target_env": "RUST_WASM_SYSROOT_TARGET",
    },
]
