// Copyright 2026 The PDFium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "core/fxcrt/fx_folder.h"

#include <memory>

// static
std::unique_ptr<FX_Folder> FX_Folder::OpenFolder(const ByteString& path) {
  (void)path;
  return nullptr;
}
