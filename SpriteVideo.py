#!/usr/bin/env python3
"""
SpriteVideo.py

Script minimalista para convertir un sprite sheet (1 sola fila de frames) en un video MP4
centrado sobre un fondo negro en la resolución que elijas.

Inputs interactivos:
- Ruta del sprite sheet
- Número total de frames (1-based, humano)
- Frame inicial (1-based)
- Frame final (1-based)
- Escala de la animación (float, 1 = tamaño original)
- Duración total de la animación en segundos (float)
- Resolución de salida (elige preset o escribe WxH)

Dependencias:
    py -m pip install pillow imageio imageio-ffmpeg

Instalacion(arch):
    python -m pip install imageio imageio-ffmpeg pillow numpy
"""

import imageio.v3 as iio
from PIL import Image
from pathlib import Path
import numpy as np


PRESETS = {
    "720p":  (1280, 720),
    "1080p": (1920, 1080),
    "2k":    (2560, 1440),
    "4k":    (3840, 2160),
}


def ask_path(prompt: str):
    while True:
        user_input = input(prompt).strip().strip('"')

        if not user_input:
            return None

        p = Path(user_input).expanduser()

        if p.exists():
            return p

        print(f"No encontré ese archivo en {p} Intenta otra vez.")

def ask_int(prompt: str, min_val=1, max_val=None, default=None):
    while True:
        txt = input(f"{prompt}" + (f" [{default}]" if default is not None else "") + ": ").strip()
        if not txt and default is not None:
            return default
        try:
            v = int(txt)
            if v < min_val:
                print(f"Debe ser >= {min_val}.")
                continue
            if max_val is not None and v > max_val:
                print(f"Debe ser <= {max_val}.")
                continue
            return v
        except ValueError:
            print("Ingresa un número entero.")


def ask_float(prompt: str, min_val=None, default=None):
    while True:
        txt = input(f"{prompt}" + (f" [{default}]" if default is not None else "") + ": ").strip()
        if not txt and default is not None:
            return default
        try:
            v = float(txt)
            if min_val is not None and v < min_val:
                print(f"Debe ser >= {min_val}.")
                continue
            return v
        except ValueError:
            print("Ingresa un número (puede ser decimal).")

def ask_time_format():
    print(f"\n: -- Duracion del Video -- :")
    print("[s] Segundos")
    print("[m] Minutos")
    print("[h] Horas")
    choice = input("Seleccioné la opción (s/m/h) [s]: ").strip().lower()
    if not choice: choice = 's'
    val = ask_float("Cantidad", default=4.0)

    if choice == 'm': return val * 60
    if choice == 'h': return val * 3600
    return val

# Resolution
def ask_resolution():
    txt = input("Resolución (720p/1080p/2k/4k o WxH) [1080p]: ").strip().lower()
    if not txt:
        return PRESETS["1080p"]
    if txt in PRESETS:
        return PRESETS[txt]
    # Parse WxH
    if "x" in txt:
        try:
            w, h = txt.lower().split("x")
            w = int(w)
            h = int(h)
            if w > 0 and h > 0:
                return (w, h)
        except Exception:
            pass
    print("Entrada inválida, uso 1080p.")
    return PRESETS["1080p"]

# Slice
def slice_horizontal(sheet_img: Image.Image, total_frames: int):
    sw, sh = sheet_img.size
    frame_w = sw // total_frames
    frames = []
    x = 0
    for i in range(total_frames):
        box = (x, 0, x + frame_w, sh)
        fr = sheet_img.crop(box)
        frames.append(fr)
        x += frame_w
    return frames

# Sprite Center
def composite_center(frame: Image.Image, out_size, scale=1.0):
    W, H = out_size

    if scale != 1.0:
        new_w = max(1, int(round(frame.width * scale)))
        new_h = max(1, int(round(frame.height * scale)))
        frame = frame.resize((new_w, new_h), Image.NEAREST)

    # Canvas negro
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    x = (W - frame.width) // 2
    y = (H - frame.height) // 2
    canvas.alpha_composite(frame.convert("RGBA"), (x, y))
    return canvas.convert("RGB")


def main():
    print(f"\n: -- SpriteSheet > Video -- :")
    print("# Para Salir Presione ENTER Sin Escribir Nada #")
    print(f"\n: -- Propiedades del SpriteSheet -- :")
    sheet_path = ask_path("Ruta del sprite: ")

    if sheet_path is None:
        print("- Saliendo...")
        return

    sheet = Image.open(sheet_path).convert("RGBA")
    sw, sh = sheet.size
    print(f"- Sprite sheet: W:{sw}px H:{sh}px")

    canvas_size = ask_int("Tamaño del lienzo (px)", min_val=1, default=64 )
    total_frames = sw // canvas_size
    print(f"- Detectados: {total_frames} frames totales.")

    print(f"\n: -- Propiedades de la Animación -- :")
    start_frame = ask_int("startFrame (1-based)", min_val=1, max_val=total_frames, default=1)
    end_frame = ask_int("endFrame (1-based)", min_val=start_frame, max_val=total_frames, default=total_frames)
    scale = ask_float("animationScale (1 = tamaño original)", min_val=0.01, default=1.0)
    duration_s = ask_time_format()
    out_w, out_h = ask_resolution()
    all_frames = slice_horizontal(sheet, total_frames)

    s = start_frame - 1
    e = end_frame - 1
    sel_frames = all_frames[s : e + 1]
    used_count = len(sel_frames)

    # Calcular fps según duración total deseada
    fps = used_count / duration_s
    print(f"- Generando video: {used_count} frames en {duration_s}s -> FPS ≈ {fps:.3f}")

    # Componer frames en canvas negro
    video_frames = []
    for fr in sel_frames:
        composed = composite_center(fr, (out_w, out_h), scale=scale)
        video_frames.append(np.array(composed))

    out_name = sheet_path.with_suffix(".mp4")
    out_txt = input(f"Nombre de salida [.mp4] [{out_name.name}]: ").strip()
    if out_txt:
        out_name = Path(out_txt if out_txt.lower().endswith(".mp4") else out_txt + ".mp4")

    print("- Renderizando (esto puede tardar un poco)...\n")
    # iio.imwrite(out_name, video_frames, fps=fps, codec="libx264", in_pixel_format="rgb24", out_pixel_format="yuv420p")
    iio.imwrite(out_name, video_frames, fps=fps, codec="libx264", pixelformat="yuv420p")

    print(f"\n- Listo: {out_name.resolve()}")


if __name__ == "__main__":
    main()
