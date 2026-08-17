# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Zero-Dependency PNG & Image Encoder / Decoder.

Saf Python standart kütüphanesi (zlib, struct) kullanarak
RFC 2083 standardına tam uyumlu PNG kodlama/çözme (Filter 0..4, Paeth, Sub, Up, Average)
ve Blender ile AI servisleri arasında kayıpsız, dikey yönelim (Y-axis) düzeltmeli dönüşüm sağlar.
"""

import struct
import zlib
import numpy as np


def _paeth_predictor(a: int, b: int, c: int) -> int:
    """PNG Filter 4: Paeth Predictor algoritması."""
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    else:
        return c


def _unfilter_scanlines(raw_bytes: bytes, height: int, width: int, bpp: int) -> bytes:
    """Tüm standart PNG filtrelerini (0: None, 1: Sub, 2: Up, 3: Average, 4: Paeth) çözer."""
    stride = 1 + width * bpp
    output = bytearray(height * width * bpp)
    prev_row = bytearray(width * bpp)

    for y in range(height):
        filter_type = raw_bytes[y * stride]
        curr_row = bytearray(raw_bytes[y * stride + 1 : (y + 1) * stride])

        if filter_type == 0:  # None
            pass
        elif filter_type == 1:  # Sub (Sol pikseli ekle)
            for x in range(bpp, len(curr_row)):
                curr_row[x] = (curr_row[x] + curr_row[x - bpp]) & 0xFF
        elif filter_type == 2:  # Up (Üst pikseli ekle)
            for x in range(len(curr_row)):
                curr_row[x] = (curr_row[x] + prev_row[x]) & 0xFF
        elif filter_type == 3:  # Average (Sol ve üst ortalamasını ekle)
            for x in range(len(curr_row)):
                left = curr_row[x - bpp] if x >= bpp else 0
                up = prev_row[x]
                curr_row[x] = (curr_row[x] + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:  # Paeth (Paeth tahminleyicisini ekle)
            for x in range(len(curr_row)):
                left = curr_row[x - bpp] if x >= bpp else 0
                up = prev_row[x]
                up_left = prev_row[x - bpp] if x >= bpp else 0
                curr_row[x] = (curr_row[x] + _paeth_predictor(left, up, up_left)) & 0xFF

        output[y * width * bpp : (y + 1) * width * bpp] = curr_row
        prev_row = curr_row

    return bytes(output)


def numpy_to_png_bytes(array: np.ndarray, flip_y: bool = True) -> bytes:
    """(H, W, 4) veya (H, W, 3) float32/uint8 NumPy dizisini PNG baytlarına dönüştürür.

    Args:
        array: (H, W, 4) veya (H, W, 3) float32 [0-1] ya da uint8 [0-255] dizi
        flip_y: Blender'ın alt-orijin (bottom-left) koordinatını PNG üst-orijin (top-left) standardına çevirir

    Returns:
        Standart PNG ikili bayt verisi (bytes)
    """
    arr = np.asarray(array)

    # float32 ise uint8 [0, 255] aralığına çevir
    if np.issubdtype(arr.dtype, np.floating):
        arr = np.clip(arr * 255.0, 0.0, 255.0).astype(np.uint8)
    elif arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)

    # Blender bottom-up -> PNG top-down dikey çevirme
    if flip_y:
        arr = arr[::-1, :, :].copy()

    h, w = arr.shape[:2]

    # Kanalları RGBA yap
    if arr.ndim == 2:
        alpha = np.full((h, w, 1), 255, dtype=np.uint8)
        arr = np.repeat(arr[..., np.newaxis], 3, axis=-1)
        arr = np.concatenate([arr, alpha], axis=-1)
    elif arr.shape[-1] == 3:
        alpha = np.full((h, w, 1), 255, dtype=np.uint8)
        arr = np.concatenate([arr, alpha], axis=-1)
    elif arr.shape[-1] == 1:
        rgb = np.repeat(arr, 3, axis=-1)
        alpha = np.full((h, w, 1), 255, dtype=np.uint8)
        arr = np.concatenate([rgb, alpha], axis=-1)

    # Her satırın başına Filter 0 baytı ekle
    filter_byte = np.zeros((h, 1), dtype=np.uint8)
    flat_rows = arr.reshape((h, w * 4))
    raw_scanlines = np.concatenate([filter_byte, flat_rows], axis=1).tobytes()

    compressed_data = zlib.compress(raw_scanlines, level=6)

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        return length + chunk_type + data + crc

    png_signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    ihdr_chunk = make_chunk(b"IHDR", ihdr_data)
    idat_chunk = make_chunk(b"IDAT", compressed_data)
    iend_chunk = make_chunk(b"IEND", b"")

    return png_signature + ihdr_chunk + idat_chunk + iend_chunk


def png_bytes_to_numpy(png_bytes: bytes, flip_y: bool = True) -> np.ndarray:
    """PNG bayt verisini (H, W, 4) float32 [0.0 - 1.0] RGBA NumPy dizisine dönüştürür.

    Tüm PNG filtrelerini (None, Sub, Up, Average, Paeth) kayıpsız çözer.

    Args:
        png_bytes: PNG ikili dosya verisi
        flip_y: PNG'nin üst-orijinini Blender alt-orijinine çevirir

    Returns:
        (H, W, 4) float32 [0.0 - 1.0] dizi
    """
    if len(png_bytes) < 8 or png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Geçersiz PNG imzası.")

    offset = 8
    width = 0
    height = 0
    bit_depth = 8
    color_type = 6
    idat_parts = []

    while offset < len(png_bytes):
        length = struct.unpack(">I", png_bytes[offset : offset + 4])[0]
        offset += 4
        chunk_type = png_bytes[offset : offset + 4]
        offset += 4
        chunk_data = png_bytes[offset : offset + length]
        offset += length
        offset += 4  # CRC

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk_data)
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if not idat_parts:
        raise ValueError("PNG içinde IDAT verisi bulunamadı.")

    decompressed = zlib.decompress(b"".join(idat_parts))

    channels = 4
    if color_type == 0:    # Grayscale
        channels = 1
    elif color_type == 2:  # RGB
        channels = 3
    elif color_type == 6:  # RGBA
        channels = 4
    elif color_type == 4:  # Grayscale + Alpha
        channels = 2

    bytes_per_pixel = channels * (bit_depth // 8)

    # Standart filtreleri çöz (Filter 0..4)
    unfiltered_bytes = _unfilter_scanlines(decompressed, height, width, bytes_per_pixel)

    raw_array = np.frombuffer(unfiltered_bytes, dtype=np.uint8).reshape((height, width, channels))

    # RGBA standardına genişlet
    if channels == 3:
        alpha = np.full((height, width, 1), 255, dtype=np.uint8)
        pixels = np.concatenate([raw_array, alpha], axis=-1)
    elif channels == 1:
        rgb = np.repeat(raw_array, 3, axis=-1)
        alpha = np.full((height, width, 1), 255, dtype=np.uint8)
        pixels = np.concatenate([rgb, alpha], axis=-1)
    elif channels == 2:
        rgb = np.repeat(raw_array[..., 0:1], 3, axis=-1)
        alpha = raw_array[..., 1:2]
        pixels = np.concatenate([rgb, alpha], axis=-1)
    else:
        pixels = raw_array

    # PNG top-down -> Blender bottom-up dikey çevirme
    if flip_y:
        pixels = pixels[::-1, :, :].copy()

    return (pixels.astype(np.float32) / 255.0).clip(0.0, 1.0)


def image_bytes_to_numpy(img_bytes: bytes) -> np.ndarray:
    """PNG veya JPEG bayt verisini otomatik tespit ederek (H, W, 4) NumPy dizisine dönüştürür."""
    if img_bytes.startswith(b"\x89PNG"):
        return png_bytes_to_numpy(img_bytes, flip_y=True)

    # Diğer formatlar için (JPEG vb.) Blender imaj yükleyicisi veya fallback
    import tempfile
    import os
    suffix = ".jpg" if img_bytes.startswith(b"\xff\xd8") else ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
        tf.write(img_bytes)
        temp_path = tf.name

    try:
        import bpy
        temp_img = bpy.data.images.load(temp_path)
        from ..blender.image_adapter import BlenderImageAdapter
        arr = BlenderImageAdapter.image_to_numpy(temp_img)
        bpy.data.images.remove(temp_img)
        return arr
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
