# Build for Rust static WASM

This is an experimental path for producing a `libpdfium.a` intended to link
into Rust's `wasm32-unknown-unknown` target. It is intentionally separate from
the existing Emscripten WASM flow documented in `BUILD_WASM.md`.

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
`#include <stdlib.h>`. The next prototype decision is whether to use a WASI-like
sysroot, an Emscripten sysroot without the JS packaging layer, or a small custom
libc/header shim tailored to the Pdfium subset.
