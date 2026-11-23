#include "fpdfview.h"

int pdfium_smoke(void) {
  FPDF_InitLibrary();
  int result = FPDF_GetLastError();
  FPDF_DestroyLibrary();
  return result;
}
