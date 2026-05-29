# Build for Rust static WASM

This is an experimental path for producing a `libpdfium.a` intended to link
into Rust's browser-oriented `wasm32-unknown-unknown` target. It is
intentionally separate from the existing Emscripten WASM flow documented in
`BUILD_WASM.md`.

The intended final consumer is a `wasm-pack` / `wasm-bindgen` browser build.
Do not switch the final Rust crate to `wasm32-wasip1` for that path. WASI can be
useful as a temporary C/C++ sysroot probe, but any final archive must link into
the browser module without `wasi_snapshot_preview1` imports unless a deliberate
WASI polyfill layer is added.

The current prototype stops after `gn gen`. That is deliberate: the generated
target graph and unresolved symbols need to be reviewed before running Ninja.

## Prototype flow

1. Install the normal PDFium build prerequisites and depot tools.

2. Fetch a separate PDFium checkout:

```sh
python3 make.py build-pdfium-rust-wasm
```

3. Apply the Rust static WASM patch scaffold:

```sh
python3 make.py patch-rust-wasm
```

4. Generate GN files only:

```sh
python3 make.py build-rust-wasm
```

5. Inspect the generated graph:

```sh
python3 make.py analyze-rust-wasm
```

## What this prototype changes

- Uses `build/rust-wasm/pdfium` instead of `build/emscripten/pdfium`.
- Adds a custom `target_os = "wasm32"` GN path.
- Adds `build/config/rust_wasm:compiler`.
- Adds `build/toolchain/rust_wasm:wasm`.
- Keeps `pdf_is_complete_lib=true` so the intended output remains a static
  archive.
- Avoids Emscripten packaging flags such as `MODULARIZE`, `ccall`, and
  `STANDALONE_WASM` for the Rust link path.
- Adds an `analyze-rust-wasm` checkpoint to inspect GN args, target metadata,
  and accidental Emscripten references before attempting compilation.
- Accepts `RUST_WASM_SYSROOT=/path/to/sysroot` when C/C++ headers and libc-like
  symbols are needed by Pdfium's C/C++ dependencies.
- Accepts `RUST_WASM_SYSROOT_TARGET=wasm32-wasip1` for a WASI headers probe
  while still compiling objects as `wasm32-unknown-unknown`.
- Scans generated build files for `wasi_snapshot_preview1` so a WASI sysroot
  experiment does not silently become a WASI runtime dependency.

## Review checkpoints before compiling

- Confirm `gn gen` accepts the custom toolchain on the selected PDFium revision.
- Inspect the generated build graph for host tools accidentally assigned to the
  `wasm32` toolchain.
- Confirm the final archive does not require Emscripten JS runtime imports.
- Identify libc, C++ ABI, allocator, and filesystem symbols that must either be
  removed, stubbed, or provided by a compatible sysroot and the Rust final link.

## Current known blocker

The pure `wasm32-unknown-unknown` target does not provide C library headers.
The first compile attempt currently fails in `third_party/libjpeg_turbo` on
`#include <stdlib.h>`.

For a browser build, a WASI sysroot is only valid as a diagnostic step if the
resulting static archive can still be linked into a `wasm32-unknown-unknown`
Rust module without WASI imports. The next prototype decision is whether to use
a WASI-like sysroot to enumerate missing libc/C++ assumptions, an Emscripten
sysroot as headers-only input without the JS packaging layer, or a small custom
libc/header shim tailored to the Pdfium subset.

## Browser compatibility rule

The final `wasmpdf` artifact should pass all of these checks:

- Rust target remains `wasm32-unknown-unknown`.
- `wasm-bindgen` can process the final `.wasm`.
- Generated imports do not include `wasi_snapshot_preview1`.
- Generated imports do not require Emscripten runtime modules.
- PDFium file access uses memory/callback APIs rather than browser-inaccessible
  POSIX filesystem calls.

## Current compile probe

With `wasi-sysroot-32.0` used as a headers probe, the build reaches ICU C++
sources. ICU must be told that the browser-oriented wasm32 target does not have
POSIX timezone globals such as `tzset`, `timezone`, or `tzname`, and that it
must not select the POSIX `mmap` implementation.

After those ICU settings, the next compile blocker moves into Pdfium font code
through FreeType's `ftstdlib.h`, which includes WASI `setjmp.h`. That header
requires wasm SJLJ/exception support, so the next decision is whether to disable
or replace FreeType's setjmp path instead of enabling exception machinery for
the browser build.
