#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
AI Texture Painter — Extension Packaging & Release Builder.

Blender 5.x Extensions Platform standardında temiz bir .zip paketi üretir.
blender_manifest.toml dosyasını ZIP'in doğrudan KÖK (ROOT) dizinine yerleştirir.
"""

import os
import zipfile
import sys


ADDON_DIR_NAME = "ai_texture_painter"
DIST_DIR = "dist"

EXCLUDE_PATTERNS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    ".gitignore",
    ".DS_Store",
    "Thumbs.db",
    "tests",
}


def get_version_from_manifest(manifest_path: str) -> str:
    """blender_manifest.toml içinden sürüm numarasını okur."""
    if not os.path.exists(manifest_path):
        return "0.1.0"

    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("version ="):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "0.1.0"


def should_exclude(rel_path: str) -> bool:
    """Dosya veya klasörün elenmesi gerekip gerekmediğini denetler."""
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts:
        if part in EXCLUDE_PATTERNS or part.endswith(".pyc") or part.endswith(".pyo"):
            return True
    return False


def build_package() -> str:
    """Blender 5.x Extensions Platform uyumlu KÖK dizinli .zip paketi oluşturur."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(script_dir, ADDON_DIR_NAME)
    manifest_file = os.path.join(source_dir, "blender_manifest.toml")

    if not os.path.isdir(source_dir):
        print(f"HATA: '{source_dir}' dizini bulunamadı!")
        sys.exit(1)

    version = get_version_from_manifest(manifest_file)
    dist_path = os.path.join(script_dir, DIST_DIR)
    os.makedirs(dist_path, exist_ok=True)

    zip_filename = f"{ADDON_DIR_NAME}-{version}.zip"
    zip_full_path = os.path.join(dist_path, zip_filename)

    if os.path.exists(zip_full_path):
        os.remove(zip_full_path)

    file_count = 0
    with zipfile.ZipFile(zip_full_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)

                if should_exclude(rel_path):
                    continue

                # Blender 5.x Extension KURALI: blender_manifest.toml ve dosyalar ZIP KÖKÜNDE olmalıdır!
                arc_name = rel_path.replace("\\", "/")
                zf.write(full_path, arc_name)
                file_count += 1

    zip_size_kb = round(os.path.getsize(zip_full_path) / 1024.0, 2)

    print("==================================================")
    print(f"AI Texture Painter v{version} Extension Paketi Olusturuldu!")
    print(f"Konum: {zip_full_path}")
    print(f"Dosya Sayisi: {file_count}")
    print(f"Paket Boyutu: {zip_size_kb} KB")
    print("==================================================")
    print("Kurulum Talimati (Blender 5.x / 4.2+):")
    print("1. Blender acin -> Edit > Preferences > Get Extensions")
    print("2. Sag ustteki menuden 'Install from Disk...' secin.")
    print(f"3. '{zip_filename}' dosyasini secin.")
    print("4. Eklenti resmi Extension olarak kurulacak, Uninstall butonu aktif olacaktir.")
    print("==================================================")

    return zip_full_path


if __name__ == "__main__":
    build_package()
