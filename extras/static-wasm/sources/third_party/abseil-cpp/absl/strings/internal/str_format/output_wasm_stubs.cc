#include <cstddef>
#include <cstdio>

#undef fwrite

extern "C" size_t pdfium_wasm_absl_str_format_fwrite(const void* ptr,
                                                      size_t size,
                                                      size_t count,
                                                      FILE* stream) {
  (void)ptr;
  (void)size;
  (void)count;
  (void)stream;
  return 0;
}
