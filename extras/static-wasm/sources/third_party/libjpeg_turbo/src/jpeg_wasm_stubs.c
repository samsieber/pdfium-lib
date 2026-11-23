#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>

#undef fread
#undef fwrite
#undef fflush
#undef fprintf

size_t pdfium_wasm_libjpeg_fread(void* buffer,
                                 size_t size,
                                 size_t count,
                                 FILE* stream) {
  (void)buffer;
  (void)size;
  (void)count;
  (void)stream;
  return 0;
}

size_t pdfium_wasm_libjpeg_fwrite(const void* buffer,
                                  size_t size,
                                  size_t count,
                                  FILE* stream) {
  (void)buffer;
  (void)size;
  (void)count;
  (void)stream;
  return 0;
}

int pdfium_wasm_libjpeg_fflush(FILE* stream) {
  (void)stream;
  return 0;
}

int pdfium_wasm_libjpeg_fprintf(FILE* stream, const char* format, ...) {
  va_list args;
  (void)stream;
  va_start(args, format);
  va_end(args);
  return 0;
}
