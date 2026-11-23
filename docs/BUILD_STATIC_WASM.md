# Build static PDFium for WebAssembly

This target builds a complete PDFium archive with Chromium Clang for
`wasm32-unknown-unknown`. A consumer can link it into one module. The C and
C++ runtime archives come from the WASI SDK and the host supplies the final
module's WASI Preview 1 imports. The target requires SIMD128.

Follow the common Python and depot_tools setup in the README. Extract the WASI
SDK 32.0 sysroot, set `RUST_WASM_SYSROOT` to that directory, and make GN and
Ninja available on `PATH`. The path below was validated on Apple Silicon.

```sh
python3 make.py build-pdfium-static-wasm
python3 make.py patch-static-wasm
python3 make.py build-static-wasm
python3 make.py install-static-wasm
python3 make.py test-static-wasm
python3 make.py archive-static-wasm
```

Patching twice skips the already applied edits. The install task stages
`lib/libpdfium.a`, the public headers, and the PDFium license in
`build/static-wasm/release`. The test task checks that the archive can be
linked into a WebAssembly module. A Rust final link also provides compiler
builtins such as `__multi3`.

This target is intended for single-threaded, memory-backed rendering with
embedded and bundled fonts. It excludes V8 and XFA. A codec or font error
that calls the patched `longjmp` traps in WebAssembly.

Set `PDFIUM_STATIC_WASM_OPTIMIZE=1` when running the patch task to also apply
the stretch, composition, glyph blend, and JPEG optimizations. Use a fresh
checkout to return to the build with only the platform patches.
