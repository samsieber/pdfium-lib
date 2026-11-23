#include <cstdio>

#undef fprintf

extern "C" int pdfium_wasm_absl_random_fprintf(FILE* stream,
                                                const char* format,
                                                ...) {
  (void)stream;
  (void)format;
  return 0;
}
