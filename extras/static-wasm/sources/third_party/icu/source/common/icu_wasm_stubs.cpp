#include <stddef.h>
#include <stdio.h>
#include <sys/time.h>
#include <time.h>

#undef getenv
#undef gettimeofday
#undef time
#undef fopen
#undef fread
#undef fclose
#undef fseek
#undef ftell

extern "C" {

char* pdfium_wasm_icu_getenv(const char* name) {
  (void)name;
  return nullptr;
}

int pdfium_wasm_icu_gettimeofday(struct timeval* tv, void* timezone) {
  (void)timezone;
  if (tv != nullptr) {
    tv->tv_sec = 0;
    tv->tv_usec = 0;
  }
  return 0;
}

time_t pdfium_wasm_icu_time(time_t* timer) {
  if (timer != nullptr) {
    *timer = 0;
  }
  return 0;
}

FILE* pdfium_wasm_icu_fopen(const char* filename, const char* mode) {
  (void)filename;
  (void)mode;
  return nullptr;
}

size_t pdfium_wasm_icu_fread(void* buffer,
                             size_t size,
                             size_t count,
                             FILE* stream) {
  (void)buffer;
  (void)size;
  (void)count;
  (void)stream;
  return 0;
}

int pdfium_wasm_icu_fclose(FILE* stream) {
  (void)stream;
  return 0;
}

int pdfium_wasm_icu_fseek(FILE* stream, long offset, int origin) {
  (void)stream;
  (void)offset;
  (void)origin;
  return -1;
}

long pdfium_wasm_icu_ftell(FILE* stream) {
  (void)stream;
  return -1L;
}

}  // extern "C"
