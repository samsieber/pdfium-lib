import os
import shutil
import subprocess
import tarfile

from pygemstones.io import file as f

import modules.common as cm
import modules.config as c
import modules.patch as patch
import modules.pdfium as p


# -----------------------------------------------------------------------------
def run_task_build_pdfium():
    for target in c.targets_static_wasm:
        p.get_pdfium_by_target(target["target_os"], append_target_os=False)


# -----------------------------------------------------------------------------
def run_task_patch():
    for target in c.targets_static_wasm:
        patch.apply_static_wasm(target["target_os"])
        if os.environ.get("PDFIUM_STATIC_WASM_OPTIMIZE") == "1":
            patch.apply_static_wasm_optimizations(target["target_os"])


# -----------------------------------------------------------------------------
def run_task_build():
    sysroot = os.path.abspath(os.environ["RUST_WASM_SYSROOT"])
    runtime = os.path.join(sysroot, "lib", c.static_wasm_sysroot_target)
    if not os.path.isfile(os.path.join(runtime, "libc++.a")):
        raise RuntimeError(
            "RUST_WASM_SYSROOT must point to an extracted WASI SDK sysroot"
        )

    for config in c.configurations_static_wasm:
        for target in c.targets_static_wasm:
            source, out, _ = _paths(target, config)
            args = cm.get_build_args(
                config,
                c.shared_lib_static_wasm,
                target["pdfium_os"],
                target["target_cpu"],
                static_wasm_sysroot=sysroot,
            )
            subprocess.run(
                ["gn", "gen", out, "--args=" + " ".join(args)], cwd=source, check=True
            )
            subprocess.run(
                ["ninja", "-C", out, "obj/libpdfium.a"], cwd=source, check=True
            )


# -----------------------------------------------------------------------------
def run_task_install():
    for config in c.configurations_static_wasm:
        for target in c.targets_static_wasm:
            source, out, stage = _paths(target, config)
            archive = os.path.join(source, out, "obj", "libpdfium.a")
            f.recreate_dir(stage)
            os.mkdir(os.path.join(stage, "lib"))
            shutil.copyfile(archive, os.path.join(stage, "lib", "libpdfium.a"))
            shutil.copytree(
                os.path.join(source, "public"), os.path.join(stage, "include")
            )
            shutil.copyfile(
                os.path.join(source, "LICENSE"), os.path.join(stage, "LICENSE")
            )


# -----------------------------------------------------------------------------
def run_task_test():
    sysroot = os.path.abspath(os.environ["RUST_WASM_SYSROOT"])
    runtime = os.path.join(sysroot, "lib", c.static_wasm_sysroot_target)
    sample = os.path.abspath(os.path.join("extras", "static-wasm", "smoke.c"))
    for config in c.configurations_static_wasm:
        for target in c.targets_static_wasm:
            source, _, stage = _paths(target, config)
            clang = os.path.join(
                source, "third_party", "llvm-build", "Release+Asserts", "bin", "clang"
            )
            subprocess.run(
                [
                    clang,
                    "--target=" + c.static_wasm_target,
                    "--sysroot=" + sysroot,
                    "-nostdlib",
                    "-Wl,--no-entry,--export=pdfium_smoke,--allow-undefined",
                    "-I" + os.path.join(stage, "include"),
                    sample,
                    os.path.join(stage, "lib", "libpdfium.a"),
                    "-L" + runtime,
                    "-lc++",
                    "-lc++abi",
                    "-lc",
                    "-lm",
                    "-o",
                    os.path.join(source, "out", "static-wasm-smoke.wasm"),
                ],
                check=True,
            )


# -----------------------------------------------------------------------------
def run_task_archive():
    with tarfile.open("static-wasm.tgz", "w:gz") as archive:
        for config in c.configurations_static_wasm:
            for target in c.targets_static_wasm:
                _, _, stage = _paths(target, config)
                archive.add(stage, arcname=config)


# -----------------------------------------------------------------------------
def _paths(target, config):
    root = os.path.join("build", target["target_os"])
    source = os.path.join(root, "pdfium")
    out = os.path.join("out", f'{target["target_os"]}-{target["target_cpu"]}-{config}')
    return source, out, os.path.join(root, config)
