#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <sys/types.h>

#undef fopen
#undef fread
#undef fwrite
#undef fclose
#undef fseek
#undef ftell
#undef fseeko
#undef ftello
#undef getenv
#undef fprintf

FILE* pdfium_wasm_openjpeg_fopen(const char* filename, const char* mode) {
  (void)filename;
  (void)mode;
  return NULL;
}

size_t pdfium_wasm_openjpeg_fread(void* buffer,
                                  size_t size,
                                  size_t count,
                                  FILE* stream) {
  (void)buffer;
  (void)size;
  (void)count;
  (void)stream;
  return 0;
}

size_t pdfium_wasm_openjpeg_fwrite(const void* buffer,
                                   size_t size,
                                   size_t count,
                                   FILE* stream) {
  (void)buffer;
  (void)size;
  (void)count;
  (void)stream;
  return 0;
}

int pdfium_wasm_openjpeg_fclose(FILE* stream) {
  (void)stream;
  return 0;
}

int pdfium_wasm_openjpeg_fseek(FILE* stream, long offset, int whence) {
  (void)stream;
  (void)offset;
  (void)whence;
  return -1;
}

long pdfium_wasm_openjpeg_ftell(FILE* stream) {
  (void)stream;
  return -1L;
}

int pdfium_wasm_openjpeg_fseeko(FILE* stream, off_t offset, int whence) {
  (void)stream;
  (void)offset;
  (void)whence;
  return -1;
}

off_t pdfium_wasm_openjpeg_ftello(FILE* stream) {
  (void)stream;
  return -1;
}

char* pdfium_wasm_openjpeg_getenv(const char* name) {
  (void)name;
  return NULL;
}

int pdfium_wasm_openjpeg_fprintf(FILE* stream, const char* format, ...) {
  va_list args;
  (void)stream;
  va_start(args, format);
  va_end(args);
  return 0;
}
