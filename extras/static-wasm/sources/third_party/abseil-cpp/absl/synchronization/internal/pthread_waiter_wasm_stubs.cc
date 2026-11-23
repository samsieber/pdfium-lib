#include <pthread.h>

#include <cerrno>

#undef pthread_cond_signal
#undef pthread_cond_timedwait
#undef pthread_cond_wait
#undef pthread_mutex_lock
#undef pthread_mutex_unlock

extern "C" int pdfium_wasm_absl_pthread_cond_signal(pthread_cond_t* cond) {
  (void)cond;
  return 0;
}

extern "C" int pdfium_wasm_absl_pthread_cond_timedwait(
    pthread_cond_t* cond,
    pthread_mutex_t* mutex,
    const struct timespec* abstime) {
  (void)cond;
  (void)mutex;
  (void)abstime;
  return ETIMEDOUT;
}

extern "C" int pdfium_wasm_absl_pthread_cond_wait(pthread_cond_t* cond,
                                                  pthread_mutex_t* mutex) {
  (void)cond;
  (void)mutex;
  return 0;
}

extern "C" int pdfium_wasm_absl_pthread_mutex_lock(pthread_mutex_t* mutex) {
  (void)mutex;
  return 0;
}

extern "C" int pdfium_wasm_absl_pthread_mutex_unlock(pthread_mutex_t* mutex) {
  (void)mutex;
  return 0;
}
