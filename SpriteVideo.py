#!/usr/bin/env python3
"""
SpriteVideo Modular & Memory Safe
    Script minimalista para convertir un sprite sheet (1 sola fila de frames) en un video MP4
    centrado sobre un fondo negro en la resolución que elijas.
Instalacion(arch dentro de un entorno [venv]):
    python -m pip install imageio imageio-ffmpeg pillow numpy
"""

import imageio.v3 as iio
from PIL import Image
from pathlib import Path
import numpy as np

PRESETS = {
    "1":    (1280, 720),
    "2":    (1920, 1080),
    "3":    (2560, 1440),
    "4":    (3840, 2160),
}

class SpriteUI:
# pregunta de la ruta de la imagen
    @staticmethod
    def ask_path(prompt: str):
        while True:
            user_input = input(prompt).strip().strip('"')
            if not user_input: return None
            p = Path(user_input).expanduser()
            if p.exists(): return p
            print(f"No encontré el archivo en {p}")
# pregunta para valores enteros
    @staticmethod
    def ask_int(prompt: str, min_val=1, max_val=None, default=None):
        while True:
            txt = input(f"{prompt} [{default}]: ").strip()
            if not txt and default is not None: return default
            try:
                v = int(txt)
                if (min_val and v < min_val) or (max_val and v > max_val): continue
                return v
            except ValueError: print("Ingresa un número entero.")
# pregunta para valores decimales
    @staticmethod
    def ask_float(prompt: str, min_val=None, default=None):
        while True:
            txt = input(f"{prompt} [{default}]: ").strip()
            if not txt and default is not None: return default
            try:
                v = float(txt)
                if min_val is not None and v < min_val: continue
                return v
            except ValueError: print("Ingresa un número decimal.")
# pregunta para cualquier duracion
    @staticmethod
    def ask_time_format():
        print(f"\n: -- Duración del Video -- :")
        print("[s] Segundos | [m] Minutos | [h] Horas")
        choice = input("Selecciona unidad [s]: ").strip().lower() or 's'

        val = SpriteUI.ask_float("Cantidad", default=4.0)

        if choice == 'm': return val * 60
        if choice == 'h': return val * 3600
        return val
# pregunta para la orientacion (canvas) del video
    @staticmethod
    def ask_video_setup():
        ori = input("Orientación del video [v (Vertical) / H (Horizontal)]: ").lower()
        print("\nCalidad:\n1) 720\n2) 1080\n3) 2k\n4) 4k\nc) Custom")
        choice = input("Selecciona [2]: ").strip().lower() or '2'

        if choice == 'c':
            w = SpriteUI.ask_int("Ancho (px)", default=1920)
            h = SpriteUI.ask_int("Alto (px)", default=1080)
            return (w, h)

        base_res = PRESETS.get(choice, (1920, 1080))
        if ori == 'v':
            return (base_res[1], base_res[0])
        return base_res
# proceso del sprite
class SpriteEngine:
    def __init__(self, sheet_path: Path, canvas_px: int):
        self.sheet = Image.open(sheet_path).convert("RGBA")
        self.canvas_px = canvas_px
        self.total_frames = self.sheet.width // canvas_px

    def get_base_processed(self, start, end, out_size, scale):
        """
        ESTA ES LA OPTIMIZACIÓN: Solo procesamos los frames originales UNA VEZ.
        Esto se queda en RAM, pero es muy poco (aprox 100-200MB).
        """
        W, H = out_size
        base_frames = []

        for i in range(start - 1, end):
            x = i * self.canvas_px
            box = (x, 0, x + self.canvas_px, self.sheet.height)
            fr = self.sheet.crop(box)

            if scale != 1.0:
                new_size = (int(fr.width * scale), int(fr.height * scale))
                fr = fr.resize(new_size, Image.NEAREST)

            canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            pos = ((W - fr.width) // 2, (H - fr.height) // 2)
            canvas.alpha_composite(fr.convert("RGBA"), pos)
            base_frames.append(np.array(canvas.convert("RGB")))

        return base_frames
# proceso de renderizacion
class VideoRenderer:
    @staticmethod
    def render(out_name, base_frames, duration_s, anim_duration, is_loop, fps):
        """
        ESTO ES EL STREAMING: Enviamos los frames uno a uno usando un generador.
        """
        num_base = len(base_frames)
        # Se calcula los frames totales que tendrá el video final
        total_video_frames = int(duration_s * fps)

        def frame_generator():
            for i in range(total_video_frames):
                # Lógica de Loop o Frame Final (Padding)
                if is_loop:
                    # Usamos el operador modulo para ciclar sobre la semilla
                    idx = i % num_base
                    # Pero si no es loop infinito, verificamos si ya cubrimos el tiempo de anim
                    # (En este script, si es loop, llenamos todo el video)
                    img = base_frames[idx]
                else:
                    # Si no es loop, mostramos la animación una vez y luego congelamos el último
                    if i < num_base:
                        img = base_frames[i]
                    else:
                        img = base_frames[-1]

                if (i + 1) % 50 == 0 or (i + 1) == total_video_frames:
                    print(f"\r- Enviando a GPU: {i+1}/{total_video_frames} frames", end="", flush=True)
                yield img

        print(f"- Renderizando {total_video_frames} frames a {fps:.3f} FPS...")

        try:
            iio.imwrite(out_name, frame_generator(), fps=fps, extension=".mp4",
                        codec="h264_nvenc", pixelformat="yuv420p", is_batch=True)
        except Exception as e:
            print(f"\n! NVENC falló, usando CPU: {e}")
            iio.imwrite(out_name, frame_generator(), fps=fps, extension=".mp4",
                        codec="libx264", pixelformat="yuv420p", is_batch=True)

def main():
    ui = SpriteUI()
    print(f"\n: -- SpriteSheet > Video -- :")

    # PREGUNTAS Y LLAMADAS A LOS DEFS
    # Ruta del sprite
    path = ui.ask_path("Ruta del sprite: ")
    if not path: return
    # Informacion sobre el sprite
    canvas_px = ui.ask_int("Tamaño del lienzo (px)", default=64)
    engine = SpriteEngine(path, canvas_px)
    start = ui.ask_int("Frame inicial", default=1, max_val=engine.total_frames)
    end = ui.ask_int("Frame final", default=engine.total_frames, max_val=engine.total_frames)
    scale = ui.ask_float("Escala", default=1.0)
    # Video y renderizacion
    res_video = ui.ask_video_setup()
    duration_s = ui.ask_time_format()
    # Tiempos de la animación
    print(f"\n: -- Velocidad de Animación -- :")
    manual = input("¿Velocidad manual para el sprite? [s/N]: ").lower() == 's'
    anim_time = ui.ask_float("Segundos por vuelta", default=1.0) if manual else duration_s
    loop = input("¿Activar Bucle (Loop)? [s/N]: ").lower() == 's'

    # 1. Cacheo la semilla (Poco uso de RAM)
    print("- Procesando frames base...")
    base_frames = engine.get_base_processed(start, end, res_video, scale)

    # 2. Calculo de los FPS reales para que la animación dure lo que se pidio
    final_fps = max(0.1, len(base_frames) / anim_time)

    # 3. Renderizamos (Streaming - No usa RAM extra)
    out_file = path.with_suffix(".mp4")
    VideoRenderer.render(out_file, base_frames, duration_s, anim_time, loop, final_fps)

    print(f"\n- ¡Listo! {out_file.name}")

if __name__ == "__main__":
    main()
