#include <stddef.h>
#include <stdio.h>
#include <time.h>

#undef fopen
#undef fread
#undef fwrite
#undef fclose
#undef fseek
#undef ftell
#undef remove
#undef time
#undef gmtime
#undef ctime

FILE* pdfium_wasm_lcms_fopen(const char* filename, const char* mode) {
  (void)filename;
  (void)mode;
  return NULL;
}

size_t pdfium_wasm_lcms_fread(void* buffer,
                              size_t size,
                              size_t count,
                              FILE* stream) {
  (void)buffer;
  (void)size;
  (void)count;
  (void)stream;
  return 0;
}

size_t pdfium_wasm_lcms_fwrite(const void* buffer,
                               size_t size,
                               size_t count,
                               FILE* stream) {
  (void)buffer;
  (void)size;
  (void)count;
  (void)stream;
  return 0;
}

int pdfium_wasm_lcms_fclose(FILE* stream) {
  (void)stream;
  return 0;
}

int pdfium_wasm_lcms_fseek(FILE* stream, long offset, int origin) {
  (void)stream;
  (void)offset;
  (void)origin;
  return -1;
}

long pdfium_wasm_lcms_ftell(FILE* stream) {
  (void)stream;
  return -1L;
}

int pdfium_wasm_lcms_remove(const char* filename) {
  (void)filename;
  return -1;
}

time_t pdfium_wasm_lcms_time(time_t* timer) {
  if (timer != NULL) {
    *timer = 0;
  }
  return 0;
}

struct tm* pdfium_wasm_lcms_gmtime(const time_t* timer) {
  static struct tm epoch;
  (void)timer;
  epoch.tm_year = 70;
  epoch.tm_mday = 1;
  return &epoch;
}

char* pdfium_wasm_lcms_ctime(const time_t* timer) {
  (void)timer;
  return "Thu Jan  1 00:00:00 1970\n";
}
