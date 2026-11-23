// Copyright 2026 The PDFium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include <sys/time.h>
#include <time.h>

#undef getpid
#undef gettimeofday
#undef time
#undef localtime

extern "C" {

int pdfium_wasm_fxcrt_getpid() {
  return 1;
}

int pdfium_wasm_fxcrt_gettimeofday(struct timeval* tv, void* timezone) {
  (void)timezone;
  if (tv) {
    tv->tv_sec = 0;
    tv->tv_usec = 0;
  }
  return 0;
}

time_t pdfium_wasm_fxcrt_time(time_t* timer) {
  if (timer) {
    *timer = 0;
  }
  return 0;
}

struct tm* pdfium_wasm_fxcrt_localtime(const time_t* timer) {
  static struct tm epoch;
  (void)timer;
  epoch.tm_year = 70;
  epoch.tm_mday = 1;
  return &epoch;
}

}  // extern "C"
