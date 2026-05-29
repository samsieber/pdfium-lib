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
  accidental Emscripten references, and the static archive's unresolved symbol
  boundary.
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

The current probe replaces FreeType's standard-library header for `wasm32` so
the build can continue without enabling wasm SJLJ. This makes FreeType's
validator longjmp path trap if an invalid table reaches it, so it is a compile
probe and not yet the final runtime-safety answer.

Pdfium's JPEG and PNG codec wrappers also include `<setjmp.h>` directly. The
prototype therefore places a wasm-only `setjmp.h` shim ahead of the sysroot
headers. Like the FreeType override, it treats `longjmp()` as a trap while we
continue mapping the compile/link surface.

After the setjmp shim, the compile probe reaches Abseil debugging targets.
Those include `<csignal>` / `<signal.h>`, where WASI reports that wasm lacks
signal support. The next decision point is whether to remove Abseil debugging
signal/stack targets from this Pdfium configuration or add more browser-wasm
no-op shims.

The current probe keeps Abseil's public debugging APIs linkable but swaps in
wasm-only no-op implementations for stack examination and failure signal
handler sources. Browser wasm has no Unix signal context to inspect, so this is
preferable to linking WASI signal emulation into the final module.

With the Abseil replacements in place, the compile probe reaches `AR
obj/libpdfium.a`.

The archive inspection currently reports:

- `obj/libpdfium.a` is produced with 913 objects.
- The archive has 19,123 defined symbols and 15,832 raw undefined references.
- After subtracting symbols defined by other objects in the archive, 244
  external symbols remain.
- Generated files still contain no Emscripten runtime settings and no
  `wasi_snapshot_preview1` references.
- The main browser-specific risk is the 15 browser-sensitive POSIX symbols,
  led by `fwrite`, `fread`, `time`, `fclose`, `fopen`, `getenv`, `fseek`,
  `pthread_mutex_lock`, `pthread_mutex_unlock`, `fprintf`, `ftell`, and
  `gettimeofday`.

The first POSIX reduction replaces Pdfium's filename-based file access and
folder enumeration with wasm-only unavailable implementations. This removes
`cfx_fileaccess_posix.o` and `fx_folder_posix.o` from the wasm graph. Browser
consumers should use memory/callback document APIs instead of
`FPDF_LoadDocument()` filename paths.

The second POSIX reduction gives wasm its own PDFium graphics platform and
FreeType system layer. The wasm platform returns a no-system-font provider, so
the build no longer includes `cfx_folderfontinfo.o` or `fx_linux_impl.o`.
FreeType now uses `ftsystem_wasm.c`, which preserves allocator hooks but makes
pathname-backed `FT_Stream_Open()` unavailable. Embedded and memory-backed font
loading remain the browser path.

The third POSIX reduction replaces Abseil's `sysinfo.cc` and
`seed_material.cc` with wasm-only sources. The sysinfo replacement reports a
single-threaded browser shape, while the seed-material replacement keeps
Abseil's seed mixing helper but exposes no operating-system entropy source.
That removes Abseil's `/dev/urandom` and CPU/proc probes from the archive. If
Pdfium or a dependency later relies on Abseil random seeding at runtime, the
final browser integration should inject entropy from Rust/JavaScript instead
of pretending a POSIX entropy device exists.

The fourth POSIX reduction replaces CCTZ's file-backed time-zone loading with
wasm-only UTC/fixed-offset support. Named IANA zones now fail back to UTC
through Abseil's normal failed-load path, and `local_time_zone()` returns UTC
instead of reading `TZ`, `LOCALTIME`, or `/etc/localtime`. This removes
`time_zone_info.o`, `time_zone_libc.o`, `time_zone_lookup.o`, and
`zone_info_source.o` from the archive. If browser-local time zones become
important, the final integration should provide them explicitly from
JavaScript rather than reading host files or environment variables.

The fifth POSIX reduction removes zlib's gzip file convenience layer from the
wasm build. Pdfium's PDF streams use zlib's in-memory deflate/inflate APIs, and
the checkout has no non-zlib users of `gzopen()`, `gzread()`, `gzwrite()`, or
`gzclose()`. Dropping `gzclose.c`, `gzlib.c`, `gzread.c`, and `gzwrite.c`
removes the remaining archive references to `open`, `read`, `write`, `close`,
and `lseek`.

The next phase is reducing or isolating the remaining POSIX-facing objects
before attempting to link the archive from Rust. The first places to inspect are
LittleCMS file/debug helpers, ICU data/timezone helpers, OpenJPEG file/debug
helpers, and Pdfium's remaining `fx_extension.o` time call plus
`fx_random.o`'s `getpid` / `gettimeofday` seed path.
