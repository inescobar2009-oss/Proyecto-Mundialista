"""Genera 'guia_basica_minecraft.mp4': vídeo explicativo con texto en pantalla.

Guía no oficial. Todos los gráficos (bloques, colores, cubos) se dibujan aquí
mismo con formas simples; no se usan logotipos ni texturas del juego.

Uso:  python3 video/generar_video.py
Requiere: Pillow, numpy y ffmpeg.
"""
import math
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(OUT_DIR, "guia_basica_minecraft.mp4")

F_TITLE = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf"
F_BODY = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ---------------------------------------------------------------- contenido
SLIDES = [
    {"type": "cover",
     "title": "GUÍA BÁSICA DE MINECRAFT",
     "sub": "Todo lo que necesitas para tu primer día",
     "tag": "Guía no oficial · Para principiantes"},
    {"title": "¿Qué es Minecraft?", "icon": "grass",
     "items": ["Un juego de mundo abierto hecho de bloques",
               "Puedes explorar, construir y sobrevivir",
               "Cada mundo es distinto y casi infinito",
               "No hay una única forma de jugar: ¡tú decides!"]},
    {"title": "Modos de juego", "icon": "stone",
     "items": ["Supervivencia: consigue recursos y no mueras",
               "Creativo: bloques infinitos y puedes volar",
               "Aventura: para mapas creados por otros jugadores",
               "Dificultad: Pacífico, Fácil, Normal o Difícil"]},
    {"title": "Controles básicos (PC)", "icon": "wood", "keys": True,
     "items": ["W A S D|Moverse",
               "Espacio|Saltar",
               "Shift|Agacharse (no te caes de los bordes)",
               "Clic izquierdo|Romper bloques / atacar",
               "Clic derecho|Colocar bloques / usar objetos",
               "E|Abrir el inventario",
               "1 – 9|Elegir objeto de la barra rápida"]},
    {"title": "Tu primer día", "icon": "wood", "numbered": True,
     "items": ["Golpea árboles para conseguir troncos",
               "Convierte los troncos en tablones",
               "Fabrica una mesa de crafteo (4 tablones)",
               "Haz palos y un pico de madera",
               "Construye un refugio antes de que anochezca"]},
    {"title": "Crafteo y herramientas", "icon": "iron",
     "items": ["La mesa de crafteo te da una cuadrícula de 3 × 3",
               "Herramientas: pico, hacha, pala, espada y azada",
               "Mejora tus materiales poco a poco:",
               "Madera  →  Piedra  →  Hierro  →  Diamante"]},
    {"title": "Cuidado con la noche", "icon": "night",
     "items": ["Al oscurecer aparecen monstruos hostiles",
               "Zombis, esqueletos, arañas… ¡y creepers que explotan!",
               "Antorchas (carbón + palo) evitan que aparezcan",
               "Cama (3 lanas + 3 tablones) para saltarte la noche"]},
    {"title": "Vida, hambre y experiencia", "icon": "heart",
     "items": ["Corazones: tu vida. Si llegan a cero, reapareces",
               "Muslos: tu hambre. Come para recuperar vida",
               "Cocina la carne en un horno: alimenta mucho más",
               "Experiencia: sirve para encantar objetos"]},
    {"title": "Minería sin peligro", "icon": "diamond",
     "items": ["Nunca caves recto hacia abajo: baja en escalera",
               "Lleva antorchas y marca el camino de vuelta",
               "Ojo con la lava: un cubo de agua te salva",
               "Los diamantes están en las capas más profundas"]},
    {"title": "Consejos finales", "icon": "chest",
     "items": ["Lleva siempre comida encima",
               "Guarda tus cosas en cofres dentro de tu casa",
               "Pon la cama en tu base: ahí reaparecerás",
               "Experimenta, construye… ¡y diviértete!"]},
    {"type": "end",
     "title": "¡A CONSTRUIR!",
     "sub": "Ya conoces lo básico. Ahora te toca a ti."},
]

# ------------------------------------------------------------ paleta/estilo
SKY_TOP = (88, 150, 230)
SKY_BOT = (170, 210, 250)
NIGHT_TOP = (14, 18, 46)
NIGHT_BOT = (40, 48, 98)
PANEL = (24, 26, 32)
ACCENT = (110, 190, 70)
GOLD = (250, 205, 70)
WHITE = (245, 245, 245)
MUTED = (190, 196, 205)

BLOCKS = {  # (cara superior, cara izquierda, cara derecha)
    "grass": ((106, 176, 62), (134, 96, 62), (110, 78, 50)),
    "dirt": ((150, 108, 72), (128, 92, 60), (104, 74, 48)),
    "stone": ((150, 150, 150), (122, 122, 122), (100, 100, 100)),
    "wood": ((176, 138, 84), (120, 88, 52), (96, 70, 42)),
    "iron": ((216, 206, 196), (176, 166, 158), (146, 138, 130)),
    "diamond": ((120, 230, 225), (70, 190, 190), (50, 156, 158)),
    "gold": ((250, 214, 80), (214, 170, 40), (176, 136, 28)),
    "chest": ((180, 128, 56), (150, 100, 40), (122, 80, 30)),
    "night": ((60, 64, 120), (40, 44, 92), (28, 30, 70)),
    "heart": ((226, 64, 64), (184, 40, 40), (150, 28, 28)),
}


def font(path, size):
    return ImageFont.truetype(path, size)


def iso_cube(size, kind, outline=True):
    """Cubo isométrico dibujado con polígonos planos."""
    top, left, right = BLOCKS[kind]
    s = size
    w, h = int(s * 1.732), int(s * 2)
    img = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = w / 2 + 2
    p_top = [(cx, 2), (cx + w / 2, s / 2 + 2), (cx, s + 2), (cx - w / 2, s / 2 + 2)]
    p_left = [(cx - w / 2, s / 2 + 2), (cx, s + 2), (cx, 2 * s + 2), (cx - w / 2, 1.5 * s + 2)]
    p_right = [(cx + w / 2, s / 2 + 2), (cx, s + 2), (cx, 2 * s + 2), (cx + w / 2, 1.5 * s + 2)]
    ol = (20, 20, 20, 255) if outline else None
    for poly, col in ((p_left, left), (p_right, right), (p_top, top)):
        d.polygon(poly, fill=col + (255,), outline=ol)
    # pequeño detalle "pixelado" en la cara superior
    rng = np.random.default_rng(abs(hash(kind)) % 1000)
    for _ in range(6):
        u, v = rng.uniform(0.2, 0.8, 2)
        x = cx + (u - v) * w / 2
        y = 2 + (u + v) * s / 2
        r = max(2, s // 10)
        shade = tuple(min(255, c + 22) for c in top)
        d.rectangle([x - r, y - r / 2, x + r, y + r / 2], fill=shade + (255,))
    return img


def gradient(top, bot):
    t = np.linspace(0, 1, H)[:, None]
    arr = (np.array(top)[None, None, :] * (1 - t[..., None]) +
           np.array(bot)[None, None, :] * t[..., None])
    arr = np.repeat(arr, W, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def make_background(night=False):
    bg = gradient(NIGHT_TOP, NIGHT_BOT) if night else gradient(SKY_TOP, SKY_BOT)
    d = ImageDraw.Draw(bg)
    if night:
        rng = np.random.default_rng(7)
        for _ in range(140):
            x, y = rng.integers(0, W), rng.integers(0, int(H * 0.7))
            r = int(rng.integers(1, 4))
            d.rectangle([x, y, x + r, y + r], fill=(230, 230, 255))
        d.rectangle([1580, 90, 1700, 210], fill=(235, 235, 220))  # luna cuadrada
        d.rectangle([1600, 120, 1630, 150], fill=(205, 205, 190))
    else:
        d.rectangle([1600, 80, 1740, 220], fill=(255, 236, 120))  # sol cuadrado
        d.rectangle([1620, 100, 1720, 200], fill=(255, 248, 170))
    # suelo de bloques: franja de hierba + tierra con cuadros
    B = 60
    ground_y = H - 2 * B
    rng = np.random.default_rng(3)
    for col in range(W // B + 1):
        x = col * B
        g = BLOCKS["grass"][0]
        g = tuple(int(c * (0.55 if night else 1)) for c in g)
        d.rectangle([x, ground_y, x + B - 1, ground_y + 18], fill=g)
        for row in range(2):
            y = ground_y + row * B + (18 if row == 0 else 0)
            hgt = B - (18 if row == 0 else 0)
            base = np.array(BLOCKS["dirt"][0]) * (rng.uniform(0.9, 1.05))
            if night:
                base *= 0.55
            d.rectangle([x, y, x + B - 1, y + hgt - 1], fill=tuple(base.astype(int)))
        d.line([x, ground_y, x, H], fill=(0, 0, 0), width=1)
    return bg


BG_DAY = make_background(False)
BG_NIGHT = make_background(True)

FLOATERS = []
_rng = np.random.default_rng(11)
for i, k in enumerate(["grass", "stone", "wood", "diamond", "gold", "iron", "dirt", "grass"]):
    FLOATERS.append({
        "img": iso_cube(int(_rng.integers(26, 46)), k),
        "x": float(_rng.uniform(0, W)),
        "y": float(_rng.uniform(60, H - 300)),
        "vx": float(_rng.uniform(12, 30)) * (1 if i % 2 else -1),
        "phase": float(_rng.uniform(0, 6.28)),
    })


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def with_alpha(img, a):
    if a >= 1:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return out


def text_img(txt, fnt, fill, shadow=True):
    bbox = fnt.getbbox(txt)
    w, h = bbox[2] + 8, bbox[3] + 8
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if shadow:
        d.text((4, 4), txt, font=fnt, fill=(0, 0, 0, 160))
    d.text((0, 0), txt, font=fnt, fill=fill + (255,))
    return img


# ------------------------------------------------------- preparar escenas
def build_slide(sl):
    """Devuelve dict con capas pre-renderizadas y la duración."""
    kind = sl.get("type", "content")
    s = {"kind": kind, "night": sl.get("icon") == "night"}
    if kind in ("cover", "end"):
        s["title"] = text_img(sl["title"], font(F_TITLE, 104 if kind == "cover" else 130), WHITE)
        s["sub"] = text_img(sl["sub"], font(F_BOLD, 46), GOLD)
        s["tag"] = text_img(sl["tag"], font(F_BODY, 32), WHITE) if sl.get("tag") else None
        s["cubes"] = [iso_cube(70, k) for k in ("grass", "wood", "stone", "diamond", "gold")]
        s["dur"] = 6.0 if kind == "cover" else 5.0
        return s

    s["title"] = text_img(sl["title"], font(F_TITLE, 72), WHITE)
    s["icon"] = iso_cube(48, sl["icon"])
    items = []
    fb, fbb = font(F_BODY, 44), font(F_BOLD, 40)
    n = len(sl["items"])
    big = n <= 5
    fb = font(F_BODY, 46 if big else 38)
    for i, it in enumerate(sl["items"]):
        if sl.get("keys"):
            key, desc = it.split("|")
            kt = text_img(key, font(F_TITLE, 34), (30, 30, 30), shadow=False)
            kw = max(kt.width + 40, 150)
            kimg = Image.new("RGBA", (kw, 62), (0, 0, 0, 0))
            kd = ImageDraw.Draw(kimg)
            kd.rectangle([0, 6, kw - 1, 61], fill=(90, 90, 90, 255))
            kd.rectangle([0, 0, kw - 1, 54], fill=(225, 225, 225, 255), outline=(40, 40, 40, 255), width=3)
            kimg.alpha_composite(kt, ((kw - kt.width) // 2, 6))
            dt = text_img(desc, font(F_BODY, 38), WHITE)
            row = Image.new("RGBA", (390 + dt.width, 70), (0, 0, 0, 0))
            row.alpha_composite(kimg, (0, 2))
            row.alpha_composite(dt, (390, 12))
            items.append(row)
        else:
            if sl.get("numbered"):
                badge = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                bd = ImageDraw.Draw(badge)
                bd.rectangle([0, 0, 63, 63], fill=ACCENT + (255,), outline=(20, 60, 20, 255), width=4)
                nt = text_img(str(i + 1), font(F_TITLE, 40), WHITE, shadow=False)
                badge.alpha_composite(nt, ((64 - nt.width) // 2 + 3, 4))
            else:
                badge = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                bd = ImageDraw.Draw(badge)
                bd.rectangle([18, 18, 46, 46], fill=ACCENT + (255,), outline=(20, 60, 20, 255), width=3)
            tt = text_img(it, fb, WHITE)
            row = Image.new("RGBA", (90 + tt.width, max(70, tt.height + 8)), (0, 0, 0, 0))
            row.alpha_composite(badge, (0, 0))
            row.alpha_composite(tt, (90, 6))
            items.append(row)
    s["items"] = items
    s["gap"] = 100 if big else 88
    first = 1.6
    per = 1.9 if not sl.get("keys") else 1.4
    s["item_t"] = [first + i * per for i in range(n)]
    s["dur"] = first + n * per + 3.2
    return s


SCENES = [build_slide(sl) for sl in SLIDES]
TOTAL = sum(sc["dur"] for sc in SCENES)


def draw_floaters(frame, t, night):
    for f in FLOATERS:
        x = (f["x"] + f["vx"] * t) % (W + 200) - 100
        y = f["y"] + 18 * math.sin(t * 0.9 + f["phase"])
        img = f["img"] if not night else with_alpha(f["img"], 0.55)
        frame.alpha_composite(img, (int(x), int(y)))


def render_frame(sc, lt, gt, idx):
    base = (BG_NIGHT if sc["night"] else BG_DAY).convert("RGBA")
    draw_floaters(base, gt, sc["night"])
    d = ImageDraw.Draw(base)

    if sc["kind"] in ("cover", "end"):
        # fila de cubos que "caen" y rebotan
        n = len(sc["cubes"])
        total_w = n * 140
        for i, c in enumerate(sc["cubes"]):
            t0 = 0.15 * i
            p = ease_out((lt - t0) / 0.7)
            y = int(-200 + (250 + 200) * p)
            x = (W - total_w) // 2 + i * 140 + 10
            if lt > t0:
                base.alpha_composite(c, (x, y))
        a = ease_out((lt - 0.8) / 0.8)
        ti = with_alpha(sc["title"], a)
        base.alpha_composite(ti, ((W - ti.width) // 2, int(520 + 40 * (1 - a))))
        a2 = ease_out((lt - 1.5) / 0.8)
        si = with_alpha(sc["sub"], a2)
        base.alpha_composite(si, ((W - si.width) // 2, 680))
        if sc["tag"] is not None:
            a3 = ease_out((lt - 2.2) / 0.8)
            tg = with_alpha(sc["tag"], a3)
            pad = 18
            if a3 > 0:
                d.rectangle([(W - tg.width) // 2 - pad, 780 - pad // 2,
                             (W + tg.width) // 2 + pad, 780 + tg.height + pad // 2],
                            fill=PANEL)
            base.alpha_composite(tg, ((W - tg.width) // 2, 780))
    else:
        # panel principal
        pa = ease_out(lt / 0.6)
        px0, py0, px1, py1 = 140, 90, W - 140, H - 160
        off = int(60 * (1 - pa))
        panel = Image.new("RGBA", (px1 - px0, py1 - py0), PANEL + (int(248 * pa),))
        pd = ImageDraw.Draw(panel)
        pd.rectangle([0, 0, panel.width - 1, panel.height - 1], outline=(10, 10, 12, 255), width=6)
        pd.rectangle([0, 0, panel.width - 1, 14], fill=ACCENT + (int(255 * pa),))
        base.alpha_composite(panel, (px0, py0 + off))
        ta = ease_out((lt - 0.3) / 0.6)
        base.alpha_composite(with_alpha(sc["icon"], ta), (px0 + 60, py0 + 50 + off))
        base.alpha_composite(with_alpha(sc["title"], ta), (px0 + 180, py0 + 62 + off))
        d.rectangle([px0 + 60, py0 + 190 + off, px0 + 60 + int(500 * ta), py0 + 196 + off], fill=GOLD)
        y = py0 + 240 + off
        for it, t0 in zip(sc["items"], sc["item_t"]):
            a = ease_out((lt - t0) / 0.5)
            if a > 0:
                base.alpha_composite(with_alpha(it, a), (px0 + 70 + int(-50 * (1 - a)), y))
            y += sc["gap"]
        # número de diapositiva
        num = text_img(f"{idx}/{len(SCENES) - 2}", font(F_TITLE, 30), MUTED, shadow=False)
        base.alpha_composite(num, (px1 - num.width - 40, py1 - num.height - 24 + off))

    # barra de progreso estilo "experiencia"
    prog = gt / TOTAL
    bx0, bx1, by = 460, W - 460, H - 60
    d.rectangle([bx0 - 4, by - 4, bx1 + 4, by + 22], fill=(15, 15, 15))
    d.rectangle([bx0, by, bx1, by + 18], fill=(50, 60, 40))
    d.rectangle([bx0, by, bx0 + int((bx1 - bx0) * prog), by + 18], fill=(128, 230, 60))
    seg = (bx1 - bx0) / 18
    for k in range(1, 18):
        x = int(bx0 + k * seg)
        d.line([x, by, x, by + 18], fill=(15, 15, 15), width=2)

    # fundido entre escenas
    fade = 0.45
    a = 1.0
    if lt < fade:
        a = lt / fade
    elif lt > sc["dur"] - fade:
        a = (sc["dur"] - lt) / fade
    frame = base.convert("RGB")
    if a < 1:
        frame = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), frame, max(0.0, a))
    return frame


# ------------------------------------------------------------- música
def make_music(path, seconds):
    """Melodía chiptune original y sencilla (onda cuadrada suave)."""
    sr = 44100
    n = int(seconds * sr)
    t = np.arange(n) / sr
    bpm = 96
    beat = 60 / bpm
    # progresión Do - La m - Fa - Sol (notas MIDI de la raíz)
    roots = [48, 45, 41, 43]
    melody_pat = [0, 4, 7, 12, 7, 4, 7, 4]

    def sq(freq, tt):
        return np.sign(np.sin(2 * np.pi * freq * tt)) * 0.5 + 0.5 * np.sin(2 * np.pi * freq * tt)

    out = np.zeros(n)
    step = beat / 2
    steps = int(seconds / step) + 1
    for k in range(steps):
        s0 = int(k * step * sr)
        s1 = min(n, int((k + 1) * step * sr))
        if s0 >= n:
            break
        tt = t[s0:s1] - t[s0]
        bar = (k // 8) % 4
        root = roots[bar]
        env = np.exp(-tt * 6)
        note = root + 24 + melody_pat[k % 8]
        f = 440 * 2 ** ((note - 69) / 12)
        out[s0:s1] += 0.10 * sq(f, tt) * env
        if k % 2 == 0:
            fb = 440 * 2 ** ((root - 69 + 12) / 12)
            out[s0:s1] += 0.12 * np.sin(2 * np.pi * fb * tt) * np.exp(-tt * 3)
    # fade in/out
    fi = int(1.5 * sr)
    out[:fi] *= np.linspace(0, 1, fi)
    out[-3 * sr:] *= np.linspace(1, 0, 3 * sr)
    out = out / (np.abs(out).max() + 1e-9) * 0.35
    data = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def main():
    wav = os.path.join(OUT_DIR, "_musica.wav")
    make_music(wav, TOTAL)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest",
           "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    gt = 0.0
    frame_no = 0
    for idx, sc in enumerate(SCENES):
        nfr = int(round(sc["dur"] * FPS))
        for f in range(nfr):
            lt = f / FPS
            img = render_frame(sc, lt, gt + lt, idx)
            proc.stdin.write(img.tobytes())
            frame_no += 1
        gt += nfr / FPS
        print(f"escena {idx + 1}/{len(SCENES)} lista", flush=True)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    print("OK ->", OUT, f"({TOTAL:.1f} s, {frame_no} fotogramas)")


if __name__ == "__main__":
    main()
