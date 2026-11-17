"""Genera 'aventura_en_bloques.mp4': un personaje recorre un mundo de bloques
(tala un árbol, fabrica herramientas, construye su casa, pasa la noche y baja a
la mina) mientras el texto en pantalla explica lo básico de Minecraft.

Guía no oficial: el personaje, las texturas y la música son originales y se
generan aquí con formas simples.

Uso:  python3 video/aventura_bloques.py
"""
import math
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ------------------------------------------------------------------ ajustes
FPS = 30
LW, LH = 384, 216          # resolución interna (pixel art)
SCALE = 5                  # 384x216 -> 1920x1080
W, H = LW * SCALE, LH * SCALE
T = 16                     # tamaño de bloque en píxeles internos
WW, WH = 80, 40            # mundo en bloques
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(OUT_DIR, "aventura_en_bloques.mp4")

F_TITLE = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf"
F_BODY = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_fc = {}


def font(p, s):
    if (p, s) not in _fc:
        _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]


# ------------------------------------------------------------- texturas
RNG = np.random.default_rng(42)


def noise_tex(base, var=14, chunk=2, seed=0):
    r = np.random.default_rng(seed)
    n = r.integers(-var, var + 1, (T // chunk, T // chunk, 1))
    n = np.kron(n, np.ones((chunk, chunk, 1)))
    a = np.clip(np.array(base)[None, None, :] + n, 0, 255).astype(np.uint8)
    img = Image.fromarray(a, "RGB").convert("RGBA")
    return img


def spots(img, color, pts):
    d = ImageDraw.Draw(img)
    for x, y in pts:
        d.rectangle([x, y, x + 2, y + 1], fill=color)
        d.point((x + 1, y + 2), fill=color)
    return img


def make_textures():
    tx = {}
    tx["dirt"] = noise_tex((134, 96, 64), 14, 2, 1)
    g = noise_tex((134, 96, 64), 14, 2, 2)
    d = ImageDraw.Draw(g)
    top = noise_tex((96, 170, 64), 16, 2, 3)
    g.paste(top.crop((0, 0, T, 4)), (0, 0))
    for x in range(0, T, 3):
        d.rectangle([x, 4, x + 1, 4 + (x * 7) % 3], fill=(86, 156, 58))
    tx["grass"] = g
    tx["stone"] = noise_tex((128, 128, 132), 12, 2, 4)
    c = noise_tex((120, 120, 124), 14, 2, 5)
    d = ImageDraw.Draw(c)
    for line in [[(0, 5), (6, 5), (6, 0)], [(6, 5), (6, 11), (16, 11)], [(10, 0), (10, 11)],
                 [(0, 11), (3, 11), (3, 16)], [(12, 11), (12, 16)]]:
        d.line(line, fill=(80, 80, 84))
    tx["cobble"] = c
    lg = noise_tex((112, 82, 50), 10, 2, 6)
    d = ImageDraw.Draw(lg)
    for x in (2, 7, 12):
        d.line([(x, 0), (x, 15)], fill=(84, 60, 36))
    tx["log"] = lg
    pl = noise_tex((186, 146, 92), 8, 2, 7)
    d = ImageDraw.Draw(pl)
    for y in (3, 7, 11, 15):
        d.line([(0, y), (15, y)], fill=(130, 98, 58))
    for x, y in ((5, 0), (11, 4), (3, 8), (9, 12)):
        d.line([(x, y), (x, y + 2)], fill=(130, 98, 58))
    tx["planks"] = pl
    rf = noise_tex((168, 64, 52), 10, 2, 8)
    d = ImageDraw.Draw(rf)
    for y in (3, 7, 11, 15):
        d.line([(0, y), (15, y)], fill=(112, 40, 34))
    tx["roof"] = rf
    lv = noise_tex((60, 140, 50), 22, 2, 9)
    d = ImageDraw.Draw(lv)
    for x, y in ((2, 3), (9, 1), (12, 9), (4, 11), (7, 6)):
        d.rectangle([x, y, x + 1, y + 1], fill=(36, 96, 32))
    tx["leaves"] = lv
    tx["coal_ore"] = spots(noise_tex((128, 128, 132), 12, 2, 10), (30, 30, 30),
                           [(2, 3), (9, 2), (5, 9), (11, 11)])
    tx["iron_ore"] = spots(noise_tex((128, 128, 132), 12, 2, 11), (214, 170, 130),
                           [(3, 2), (10, 4), (2, 10), (9, 11)])
    tx["diamond_ore"] = spots(noise_tex((128, 128, 132), 12, 2, 12), (90, 236, 230),
                              [(2, 2), (10, 3), (5, 9), (11, 11)])
    tx["deep"] = noise_tex((46, 46, 52), 12, 2, 13)
    lava = noise_tex((236, 110, 20), 30, 2, 14)
    d = ImageDraw.Draw(lava)
    for x, y in ((3, 3), (10, 6), (5, 12)):
        d.rectangle([x, y, x + 2, y + 1], fill=(255, 220, 80))
    tx["lava"] = lava
    gl = Image.new("RGBA", (T, T), (180, 220, 240, 70))
    d = ImageDraw.Draw(gl)
    d.rectangle([0, 0, 15, 15], outline=(220, 240, 250, 255))
    d.line([(3, 3), (6, 6)], fill=(255, 255, 255, 200))
    tx["glass"] = gl
    tb = tx["planks"].copy()
    d = ImageDraw.Draw(tb)
    d.rectangle([0, 0, 15, 3], fill=(150, 110, 64))
    d.rectangle([3, 6, 7, 10], outline=(80, 56, 30))
    d.rectangle([9, 6, 13, 10], outline=(80, 56, 30))
    tx["table"] = tb
    ch = noise_tex((176, 124, 52), 8, 2, 15)
    d = ImageDraw.Draw(ch)
    d.rectangle([0, 0, 15, 15], outline=(90, 60, 24))
    d.line([(0, 6), (15, 6)], fill=(90, 60, 24))
    d.rectangle([6, 5, 9, 8], fill=(200, 200, 210))
    tx["chest"] = ch
    for part in ("door_t", "door_b"):
        dr = noise_tex((150, 108, 60), 8, 2, 16)
        d = ImageDraw.Draw(dr)
        d.rectangle([1, 0, 14, 15], outline=(96, 66, 34))
        if part == "door_t":
            d.rectangle([4, 3, 11, 9], fill=(170, 210, 230))
            d.rectangle([4, 3, 11, 9], outline=(96, 66, 34))
        else:
            d.rectangle([11, 4, 12, 6], fill=(60, 60, 60))
        tx[part] = dr
    bh = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(bh)
    d.rectangle([0, 6, 15, 12], fill=(186, 146, 92))
    d.rectangle([1, 3, 9, 7], fill=(240, 240, 240))
    d.rectangle([0, 0, 1, 15], fill=(120, 88, 52))
    d.rectangle([9, 5, 15, 9], fill=(200, 50, 50))
    tx["bed_h"] = bh
    bf = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(bf)
    d.rectangle([0, 6, 15, 12], fill=(186, 146, 92))
    d.rectangle([0, 5, 14, 9], fill=(200, 50, 50))
    d.rectangle([14, 2, 15, 15], fill=(120, 88, 52))
    tx["bed_f"] = bf
    tr = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(tr)
    d.rectangle([7, 7, 8, 15], fill=(120, 86, 50))
    d.rectangle([6, 4, 9, 7], fill=(255, 190, 40))
    d.rectangle([7, 3, 8, 5], fill=(255, 245, 160))
    tx["torch"] = tr
    tx["air"] = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    # paredes traseras (más oscuras)
    for k in ("dirt", "stone", "planks", "deep"):
        b = tx[k].copy()
        a = np.asarray(b).astype(float)
        a[..., :3] *= 0.5
        tx["back_" + k] = Image.fromarray(a.astype(np.uint8), "RGBA")
    return tx


TX = make_textures()


def item_sprite(name):
    if name in TX and name not in ("air",):
        return TX[name]
    im = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if name == "stick":
        d.line([(3, 13), (12, 2)], fill=(120, 86, 50), width=2)
    elif name.endswith("pick"):
        col = {"wpick": (176, 136, 80), "spick": (140, 140, 146), "ipick": (225, 225, 230)}[name]
        d.line([(3, 14), (11, 5)], fill=(120, 86, 50), width=2)
        d.line([(4, 3), (8, 2), (12, 3), (13, 7), (14, 11)], fill=col, width=3)
    elif name == "coal":
        d.polygon([(4, 6), (8, 3), (12, 5), (13, 10), (8, 13), (3, 10)], fill=(36, 36, 40))
        d.point((7, 6), fill=(90, 90, 96))
    elif name == "iron":
        d.polygon([(2, 9), (6, 5), (14, 5), (12, 10), (3, 10)], fill=(220, 214, 206))
        d.line([(6, 5), (3, 9)], fill=(250, 250, 250))
    elif name == "diamond":
        d.polygon([(8, 2), (14, 7), (8, 14), (2, 7)], fill=(90, 236, 230))
        d.polygon([(8, 2), (10, 7), (8, 14), (6, 7)], fill=(170, 255, 250))
    elif name == "furnace":
        d.rectangle([1, 1, 14, 14], fill=(110, 110, 116), outline=(60, 60, 64))
        d.rectangle([4, 8, 11, 12], fill=(255, 140, 30))
    return im


_icon_cache = {}


def icon(name, px=48):
    k = (name, px)
    if k not in _icon_cache:
        _icon_cache[k] = item_sprite(name).resize((px, px), Image.NEAREST)
    return _icon_cache[k]


# ----------------------------------------------------------------- mundo
SOLID_EXCLUDE = {"air", "torch", "door_t", "door_b", "bed_h", "bed_f", "chest",
                 "table", "lava", "glass", "leaves"}
OPAQUE_EXCLUDE = {"air", "log", "torch", "door_t", "door_b", "bed_h", "bed_f", "chest",
                  "table", "lava", "glass", "leaves"}


class World:
    def __init__(self):
        self.tiles = [["air"] * WW for _ in range(WH)]
        self.surface = [18] * WW
        for x in range(WW):
            if x < 6:
                self.surface[x] = 15 + x // 2
            elif x > 64:
                self.surface[x] = max(14, 18 - (x - 64) // 3)
        self.front = Image.new("RGBA", (WW * T, WH * T), (0, 0, 0, 0))
        self.back = Image.new("RGBA", (WW * T, WH * T), (0, 0, 0, 0))
        self.solid = np.zeros((WH, WW), bool)
        self.opaque = np.zeros((WH, WW), bool)
        self.lights = []
        for x in range(WW):
            s = self.surface[x]
            for y in range(s, WH):
                if y == s:
                    k = "grass"
                elif y <= s + 3:
                    k = "dirt"
                elif y >= WH - 1:
                    k = "deep"
                else:
                    k = "stone"
                self.set(x, y, k, update_lights=False)
                if y > s:
                    bk = "back_dirt" if y <= s + 3 else "back_stone"
                    self.back.paste(TX[bk], (x * T, y * T))
        # menas decorativas
        r = np.random.default_rng(5)
        for _ in range(28):
            x, y = int(r.integers(2, WW - 2)), int(r.integers(23, WH - 2))
            self.set(x, y, "coal_ore" if r.random() < 0.6 else "iron_ore", update_lights=False)
        # menas del camino
        for x, y in ((44, 20), (45, 21)):
            self.set(x, y, "coal_ore", False)
        for x, y in ((49, 25), (50, 25)):
            self.set(x, y, "iron_ore", False)
        for x, y in ((61, 31), (61, 32), (62, 32)):
            self.set(x, y, "diamond_ore", False)
        for x, y in ((57, 33), (58, 33), (57, 34), (58, 34), (56, 35), (57, 35), (58, 35), (59, 35)):
            self.set(x, y, "lava", False)
        self.set(20, 18, "coal_ore", False)
        # árbol
        for y in range(14, 18):
            self.set(14, y, "log", False)
        for y, xs in ((10, range(13, 16)), (11, range(12, 17)), (12, range(12, 17)), (13, range(12, 17))):
            for x in xs:
                if not (x == 14 and y == 13):
                    self.set(x, y, "leaves", False)
        self.set(14, 13, "log", False)
        # árboles decorativos lejanos
        for tx0 in (3, 70, 75):
            s = self.surface[tx0]
            for y in range(s - 4, s):
                self.set(tx0, y, "log", False)
            for y in range(s - 7, s - 4):
                for x in range(tx0 - 2, tx0 + 3):
                    self.set(x, y, "leaves", False)
        self.refresh_lights()

    def get(self, x, y):
        if 0 <= x < WW and 0 <= y < WH:
            return self.tiles[y][x]
        return "deep"

    def set(self, x, y, k, update_lights=True):
        self.tiles[y][x] = k
        self.front.paste(TX[k], (x * T, y * T))
        self.solid[y, x] = k not in SOLID_EXCLUDE
        self.opaque[y, x] = k not in OPAQUE_EXCLUDE
        if update_lights:
            self.refresh_lights()

    def set_back(self, x, y, k):
        self.back.paste(TX[k], (x * T, y * T))

    def refresh_lights(self):
        self.lights = [(x + 0.5, y + 0.5, 7.5 if self.tiles[y][x] == "torch" else 4.0)
                       for y in range(WH) for x in range(WW)
                       if self.tiles[y][x] in ("torch", "lava")]


WORLD = World()

YY, XX = np.mgrid[0:WH, 0:WW]


def light_map(state):
    op = WORLD.opaque
    above = np.cumsum(op, axis=0) - op  # bloques opacos por encima
    sky = np.clip(1 - 0.17 * above, 0, 1)
    for _ in range(5):  # propagación lateral
        nb = np.maximum.reduce([np.roll(sky, 1, 0), np.roll(sky, -1, 0),
                                np.roll(sky, 1, 1), np.roll(sky, -1, 1)]) * 0.8
        sky = np.maximum(sky, np.where(op, sky, nb))
    L = sky * state.day
    for lx, ly, rad in WORLD.lights:
        dist = np.hypot(XX + 0.5 - lx, YY + 0.5 - ly)
        L = np.maximum(L, np.clip(1 - dist / rad, 0, 1) * 1.05)
    c = state.c
    dist = np.hypot(XX + 0.5 - c.x, YY + 0.5 - (c.y - 1))
    L = np.maximum(L, np.clip(0.5 - dist / 7, 0, 1))
    L = np.clip(L, 0.05, 1)
    return Image.fromarray((L * 255).astype(np.uint8), "L").resize((WW * T, WH * T), Image.BILINEAR)


# ------------------------------------------------------------- personaje
class Char:
    def __init__(self):
        self.x, self.y = 7.5, 18.0
        self.facing = 1
        self.walk_phase = 0.0
        self.walking = False
        self.arm = 10.0
        self.tool = None
        self.sleeping = False
        self.target = None
        self.progress = 0.0


def limb(d, px, py, length, w, ang, col):
    a = math.radians(ang)
    dx, dy = math.sin(a), math.cos(a)
    nx, ny = math.cos(a), -math.sin(a)
    h = w / 2
    pts = [(px + nx * h, py + ny * h), (px - nx * h, py - ny * h),
           (px - nx * h + dx * length, py - ny * h + dy * length),
           (px + nx * h + dx * length, py + ny * h + dy * length)]
    d.polygon(pts, fill=col)
    return px + dx * length, py + dy * length


SKIN, HELMET, SHIRT, SCARF, PANTS, BOOT = (226, 180, 138), (244, 190, 40), (86, 118, 62), (204, 52, 44), (78, 80, 96), (70, 46, 30)


def char_sprite(c):
    im = Image.new("RGBA", (40, 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = 20
    leg = 28 * math.sin(c.walk_phase) if c.walking else 0
    back_arm = -leg * 0.8 if c.walking else -8
    limb(d, cx, 31, 11, 4, -leg, (60, 62, 76))
    limb(d, cx, 21, 10, 3, back_arm, (66, 94, 48))
    d.rectangle([cx - 3, 20, cx + 3, 31], fill=SHIRT)
    d.rectangle([cx - 3, 20, cx + 3, 21], fill=SCARF)
    d.rectangle([cx - 4, 30, cx + 3, 32], fill=(60, 44, 30))
    ex, ey = limb(d, cx, 31, 11, 4, leg, PANTS)
    d.rectangle([ex - 2, ey - 2, ex + 3, ey], fill=BOOT)
    d.rectangle([cx - 4, 11, cx + 4, 20], fill=SKIN)
    d.rectangle([cx - 4, 11, cx - 3, 15], fill=(90, 60, 36))
    d.rectangle([cx - 5, 9, cx + 4, 12], fill=HELMET)
    d.rectangle([cx + 4, 12, cx + 6, 12], fill=HELMET)
    d.rectangle([cx - 1, 9, cx + 1, 10], fill=(255, 240, 170))
    d.point((cx + 2, 15), fill=(20, 20, 20))
    d.point((cx + 3, 15), fill=(20, 20, 20))
    d.line([(cx + 1, 18), (cx + 3, 18)], fill=(150, 90, 70))
    hx, hy = limb(d, cx, 21, 10, 3, c.arm, SHIRT)
    d.rectangle([hx - 1, hy - 1, hx + 1, hy + 1], fill=SKIN)
    if c.tool:
        a = math.radians(c.arm)
        dx, dy = math.sin(a), math.cos(a)
        tip = (hx + dx * 7, hy + dy * 7)
        d.line([(hx, hy), tip], fill=(120, 86, 50), width=2)
        col = {"wpick": (176, 136, 80), "spick": (150, 150, 156), "ipick": (230, 230, 236)}[c.tool]
        nx, ny = math.cos(a), -math.sin(a)
        d.line([(tip[0] + nx * 4, tip[1] + ny * 4), (tip[0] - nx * 4 + dx * 1.5, tip[1] - ny * 4 + dy * 1.5)],
               fill=col, width=2)
    if c.facing < 0:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im


def monster_sprite(t):
    im = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([1, 3, 16, 17], fill=(120, 60, 160), outline=(60, 24, 90))
    d.rectangle([3, 5, 14, 9], fill=(150, 90, 190))
    return im


# --------------------------------------------------------------- estado
class State:
    def __init__(self):
        self.c = Char()
        self.day = 1.0
        self.cam = [0.0, 0.0]
        self.focus = None
        self.caption = ""
        self.chapter = ""
        self.title = None
        self.popup = None
        self.popup_t = 0
        self.fade = 0.0
        self.monster = None
        self.particles = []
        self.inv = {}
        self.inv_pop = {}
        self.t = 0.0
        self.zzz = False
        self.cam_init = False


S = State()
INV_ORDER = ["log", "planks", "stick", "dirt", "cobble", "coal", "torch", "iron", "diamond"]
DROPS = {"grass": "dirt", "dirt": "dirt", "stone": "cobble", "log": "log",
         "coal_ore": "coal", "iron_ore": "iron", "diamond_ore": "diamond"}
HARD = {"grass": 0.35, "dirt": 0.35, "stone": 0.45, "cobble": 0.45, "log": 0.8,
        "leaves": 0.15, "coal_ore": 0.6, "iron_ore": 0.7, "diamond_ore": 0.9}
COLORS = {"grass": (96, 170, 64), "dirt": (134, 96, 64), "stone": (128, 128, 132),
          "log": (112, 82, 50), "leaves": (60, 140, 50), "coal_ore": (40, 40, 40),
          "iron_ore": (214, 170, 130), "diamond_ore": (90, 236, 230), "cobble": (120, 120, 124)}


def add_inv(k, n=1):
    S.inv[k] = S.inv.get(k, 0) + n
    S.inv_pop[k] = S.t


# --------------------------------------------------------------- acciones
def frames(n):
    for _ in range(max(1, int(n))):
        yield


def wait(sec):
    yield from frames(sec * FPS)


def ground_y(col, from_y):
    r0 = int(round(from_y)) - 1
    for r in range(max(0, r0), WH):
        if WORLD.solid[r, col]:
            return r
    return WH - 1


def walk(tx, speed=3.2):
    c = S.c
    c.walking = True
    c.facing = 1 if tx > c.x else -1
    while abs(tx - c.x) > 0.02:
        step = speed / FPS
        c.x += max(-step, min(step, tx - c.x))
        c.walk_phase += 0.42
        gy = ground_y(int(c.x), c.y)
        c.y += max(-0.25, min(0.2, gy - c.y))
        c.arm = 28 * math.sin(c.walk_phase) * -1
        yield
    c.x = tx
    for _ in range(6):
        gy = ground_y(int(c.x), c.y)
        c.y += max(-0.25, min(0.2, gy - c.y))
        yield
    c.walking = False
    c.arm = 10


def walk_to(tx, ty, sec=0.45):
    c = S.c
    c.walking = True
    c.facing = 1 if tx > c.x else -1
    x0, y0 = c.x, c.y
    n = int(sec * FPS)
    for i in range(1, n + 1):
        p = i / n
        c.x = x0 + (tx - x0) * p
        c.y = y0 + (ty - y0) * p
        c.walk_phase += 0.42
        yield
    c.walking = False
    c.arm = 10


def aim_angle(tx, ty):
    c = S.c
    sx, sy = c.x, c.y - 1.45
    dx, dy = abs(tx + 0.5 - sx), (ty + 0.5) - sy
    return math.degrees(math.atan2(dx, dy))


def mine(tx, ty, sec=None):
    c = S.c
    k = WORLD.get(tx, ty)
    if k == "air":
        return
    if abs(tx + 0.5 - c.x) > 0.2:
        c.facing = 1 if tx + 0.5 > c.x else -1
    sec = sec if sec is not None else HARD.get(k, 0.5)
    base = aim_angle(tx, ty)
    n = int(sec * FPS)
    c.target = (tx, ty)
    for i in range(n):
        c.progress = (i + 1) / n
        c.arm = base + 40 * math.sin(i * 0.9)
        yield
    c.target = None
    c.progress = 0
    WORLD.set(tx, ty, "air")
    col = COLORS.get(k, (150, 150, 150))
    for _ in range(10):
        S.particles.append([tx * T + 8 + RNG.uniform(-5, 5), ty * T + 8 + RNG.uniform(-5, 5),
                            RNG.uniform(-40, 40), RNG.uniform(-70, -10), col, 0.6])
    if k in DROPS:
        add_inv(DROPS[k])
    c.arm = 10


def place(tx, ty, k, sec=0.16, back=False):
    c = S.c
    if abs(tx + 0.5 - c.x) > 0.2:
        c.facing = 1 if tx + 0.5 > c.x else -1
    base = aim_angle(tx, ty)
    n = max(2, int(sec * FPS))
    for i in range(n):
        c.arm = base - 30 + 30 * (i / n)
        yield
    if back:
        WORLD.set_back(tx, ty, k)
    else:
        WORLD.set(tx, ty, k)
    c.arm = 10


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def tween(attr, to, sec):
    fr = getattr(S, attr)
    n = int(sec * FPS)
    for i in range(1, n + 1):
        setattr(S, attr, fr + (to - fr) * ease(i / n))
        yield


def popup(inputs, out, count, label, sec=3.2):
    S.popup = {"in": inputs, "out": out, "n": count, "label": label}
    S.popup_t = S.t
    yield from wait(sec)
    S.popup = None


def cap(text, chapter=None):
    S.caption = text
    if chapter is not None:
        S.chapter = chapter


# ---------------------------------------------------------------- guion
def story():
    c = S.c
    S.focus = (20, 13)
    S.title = ("UN DÍA EN MI MUNDO DE BLOQUES", "Aprende lo básico de Minecraft jugando", S.t)
    yield from wait(4.5)
    S.title = None
    S.focus = None

    # 1 · madera
    cap("Despiertas en un mundo nuevo. Lo primero: ¡conseguir madera!", "1 · Conseguir madera")
    yield from walk(13.35)
    cap("Mantén pulsado el clic izquierdo para romper bloques. Golpea el tronco.")
    for y in (17, 16, 15, 14, 13):
        yield from mine(14, y)
    cap("Las hojas que quedan sueltas desaparecen solas.")
    for y in (13, 12, 11, 10):
        for x in range(12, 17):
            if WORLD.get(x, y) == "leaves":
                WORLD.set(x, y, "air")
                for _ in range(3):
                    S.particles.append([x * T + 8, y * T + 8, RNG.uniform(-30, 30),
                                        RNG.uniform(-40, 0), (60, 140, 50), 0.5])
        yield from wait(0.25)
    yield from wait(1.0)

    # 2 · fabricar
    cap("Abre el inventario (tecla E) y convierte los troncos en tablones.", "2 · Fabricar herramientas")
    yield from popup(["log", None, None, None, None, None, None, None, None], "planks", 4,
                     "1 tronco = 4 tablones")
    S.inv["log"] = 1
    add_inv("planks", 16)
    yield from popup(["planks", "planks", None, "planks", "planks", None, None, None, None], "table", 1,
                     "4 tablones = mesa de crafteo")
    cap("Coloca la mesa de crafteo con el clic derecho: te da una cuadrícula de 3 × 3.")
    yield from walk(15.6)
    yield from place(17, 17, "table", 0.3)
    yield from wait(0.8)
    add_inv("stick", 4)
    cap("En la mesa: tablones arriba y palos en el centro = ¡tu primer pico!")
    yield from popup(["planks", "planks", "planks", None, "stick", None, None, "stick", None], "wpick", 1,
                     "Pico de madera")
    c.tool = "wpick"
    yield from walk(19.4)
    cap("¡Carbón a la vista! Con el pico puedes picar piedra y minerales.")
    yield from mine(20, 18)
    yield from wait(0.4)
    yield from popup([None, "coal", None, None, "stick", None, None, None, None], "torch", 4,
                     "Carbón + palo = 4 antorchas")
    add_inv("torch", 4)
    S.inv["coal"] = 0

    # 3 · casa
    cap("Antes de que anochezca necesitas un refugio. ¡Hora de construir!", "3 · Construir tu casa")
    yield from walk(26.2)
    S.focus = (27.5, 14.5)
    cap("Clic derecho para colocar bloques. Primero las paredes…")
    c.tool = None
    for y, k in ((17, "planks"), (16, "planks"), (15, "glass"), (14, "planks")):
        yield from place(24, y, k)
    yield from walk(28.6)
    for y, k in ((14, "planks"), (15, "planks"), (16, "door_t"), (17, "door_b")):
        yield from place(30, y, k)
    cap("…luego el tejado. Una puerta para entrar y una ventana para ver fuera.")
    yield from walk(27.5)
    for x in range(23, 32):
        yield from place(x, 13, "roof", 0.1)
    for x in range(24, 31):
        yield from place(x, 12, "roof", 0.1)
    for x in range(26, 29):
        yield from place(x, 11, "roof", 0.1)
    for y in (17, 16, 15, 14):
        for x in range(25, 30):
            WORLD.set_back(x, y, "back_planks")
        yield from wait(0.12)
    cap("Dentro: una cama para dormir, una antorcha para la luz y un cofre.")
    yield from place(26, 17, "bed_h", 0.25)
    yield from place(27, 17, "bed_f", 0.25)
    yield from place(25, 15, "torch", 0.25)
    S.inv["torch"] -= 1
    yield from place(29, 17, "chest", 0.25)
    yield from wait(1.2)
    S.focus = None

    # 4 · noche
    cap("El sol se pone… y por la noche aparecen monstruos.", "4 · Sobrevivir a la noche")
    S.focus = (30, 14.5)
    S.monster = {"x": 44.0}
    yield from tween("day", 0.22, 4.0)
    cap("¡Uno se acerca! Quédate en casa, con la puerta cerrada y bien iluminado.")
    for _ in range(int(3.5 * FPS)):
        S.monster["x"] = max(32.6, S.monster["x"] - 2.6 / FPS)
        yield
    cap("Duerme en la cama para que pase la noche. ¡Además será tu punto de reaparición!")
    yield from walk(26.6)
    c.sleeping = True
    S.zzz = True
    yield from wait(2.4)
    yield from tween("fade", 1.0, 0.8)
    S.day = 1.0
    S.monster = None
    c.sleeping = False
    S.zzz = False
    c.x = 27.5
    yield from wait(0.3)
    cap("¡Buenos días! Ya es seguro salir.")
    yield from tween("fade", 0.0, 0.8)
    yield from wait(1.2)
    S.focus = None

    # 5 · mina
    cap("Ahora, ¡a la mina! Ahí abajo están los mejores materiales.", "5 · Bajar a la mina")
    c.tool = "wpick"
    yield from walk(40.5)
    cap("Regla de oro: nunca caves recto hacia abajo. Baja en escalera.")
    for k in range(15):
        cx, fy = 40 + k, 18 + k
        n = cx + 1
        if k == 3:
            cap("¡Carbón! Para más antorchas y para encender el horno.")
        if k == 5:
            cap("Pon antorchas: verás mejor y sabrás cómo volver.")
        if k == 8:
            cap("¡Hierro! Muy útil para herramientas y armaduras.")
        if k == 11:
            cap("Cuanto más profundo, más oscuro… y más valioso.")
        for r in (fy - 2, fy - 1, fy):
            if WORLD.solid[r, n]:
                yield from mine(n, r)
        yield from walk_to(n + 0.5, fy + 1)
        if k == 2:
            cap("Con piedra fabricas un pico mejor, más rápido y resistente.")
            yield from popup(["cobble", "cobble", "cobble", None, "stick", None, None, "stick", None],
                             "spick", 1, "Pico de piedra", 2.6)
            c.tool = "spick"
        if k in (5, 9, 13):
            yield from place(n - 1, fy - 2, "torch", 0.2)
            S.inv["torch"] = max(0, S.inv.get("torch", 0) - 1)
        if k == 9:
            yield from popup(["iron", "furnace", None, None, None, None, None, None, None], "ipick", 1,
                             "Horno: hierro → lingotes → pico de hierro", 3.0)
            c.tool = "ipick"

    # 6 · profundidades
    cap("En las capas más profundas se esconden los diamantes. ¡Cavemos un túnel!", "6 · Las profundidades")
    for col in range(56, 63):
        for r in (31, 32):
            if WORLD.solid[r, col]:
                if WORLD.get(col, r) == "diamond_ore" and S.caption[:3] != "¡DI":
                    cap("¡DIAMANTES! Solo se pueden picar con un pico de hierro o mejor.")
                yield from mine(col, r)
        if col == 57:
            cap("¡Cuidado! Lava. Nunca la pises: tápala con bloques.")
            yield from wait(1.0)
            yield from place(57, 33, "cobble", 0.35)
            yield from place(58, 33, "cobble", 0.35)
            yield from wait(0.8)
        if col == 59:
            yield from place(58, 31, "torch", 0.2)
        if col < 62:
            yield from walk_to(col + 0.5, 33, 0.35)
    yield from wait(2.0)

    # 7 · vuelta
    cap("Con tus tesoros en la mochila, vuelves siguiendo las antorchas…", "7 · De vuelta a casa")
    yield from tween("fade", 1.0, 0.8)
    c.x, c.y = 28.0, 18.0
    c.facing = 1
    c.tool = None
    S.focus = (27.5, 14.5)
    S.cam_init = False
    S.day = 0.8
    yield from tween("fade", 0.0, 0.8)
    cap("Guarda tus cosas en el cofre: si mueres, no las perderás.")
    yield from place(29, 17, "chest", 0.3)
    yield from popup(["diamond", "iron", "coal", "cobble", "dirt", None, None, None, None], "chest", 1,
                     "Cofre: tu almacén seguro", 3.0)
    for k in ("diamond", "iron", "coal", "cobble", "dirt"):
        S.inv[k] = 0
    cap("Ya sabes lo básico: madera, herramientas, refugio, noche y mina.")
    yield from wait(3.0)
    cap("")
    S.chapter = ""
    S.title = ("¡TU MUNDO TE ESPERA!", "Explora · Construye · Sobrevive", S.t)
    yield from tween("day", 0.55, 4.0)
    yield from wait(1.5)
    yield from tween("fade", 1.0, 1.0)


# --------------------------------------------------------------- render
SKY_DAY = ((96, 156, 236), (176, 214, 250))
SKY_SET = ((90, 80, 150), (250, 160, 100))
SKY_NIGHT = ((10, 14, 40), (34, 44, 88))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sky_colors(day):
    if day >= 0.6:
        t = (1 - day) / 0.4
        return lerp(SKY_DAY[0], SKY_SET[0], t), lerp(SKY_DAY[1], SKY_SET[1], t)
    t = min(1, (0.6 - day) / 0.38)
    return lerp(SKY_SET[0], SKY_NIGHT[0], t), lerp(SKY_SET[1], SKY_NIGHT[1], t)


STARS = [(int(RNG.integers(0, LW)), int(RNG.integers(0, 130))) for _ in range(70)]
CLOUDS = [(float(RNG.uniform(0, 600)), float(RNG.uniform(10, 80)), int(RNG.integers(3, 7))) for _ in range(7)]


def render_sky():
    top, bot = sky_colors(S.day)
    t = np.linspace(0, 1, LH)[:, None, None]
    arr = np.array(top)[None, None, :] * (1 - t) + np.array(bot)[None, None, :] * t
    arr = np.repeat(arr, LW, axis=1).astype(np.uint8)
    sky = Image.fromarray(arr, "RGB").convert("RGBA")
    d = ImageDraw.Draw(sky)
    night = max(0.0, (0.6 - S.day) / 0.38)
    if night > 0:
        for x, y in STARS:
            v = int(255 * min(1, night))
            d.point((x, y), fill=(v, v, v))
    sun_y = 24 + (1 - S.day) * 180
    d.rectangle([300, sun_y, 330, sun_y + 30], fill=(255, 236, 120))
    d.rectangle([305, sun_y + 5, 325, sun_y + 25], fill=(255, 250, 190))
    if night > 0.3:
        my = 140 - night * 110
        d.rectangle([70, my, 92, my + 22], fill=(232, 232, 218))
        d.rectangle([75, my + 5, 81, my + 11], fill=(200, 200, 186))
    cl = lerp((255, 255, 255), (60, 64, 100), night)
    for x0, y0, wdt in CLOUDS:
        x = (x0 + S.t * 5 - S.cam[0] * 0.2) % 640 - 80
        y = y0 - S.cam[1] * 0.1 + 15
        d.rectangle([x, y, x + wdt * 10, y + 8], fill=cl)
        d.rectangle([x + 10, y - 6, x + wdt * 6, y], fill=cl)
    return sky


def update_camera():
    c = S.c
    if S.focus:
        tx, ty = S.focus[0] * T - LW / 2, S.focus[1] * T - LH / 2
    else:
        tx, ty = c.x * T - LW / 2, (c.y - 1) * T - LH * 0.40
    tx = max(0, min(WW * T - LW, tx))
    ty = max(0, min(WH * T - LH, ty))
    if not S.cam_init:
        S.cam = [tx, ty]
        S.cam_init = True
    S.cam[0] += (tx - S.cam[0]) * 0.07
    S.cam[1] += (ty - S.cam[1]) * 0.07


CRACK = [(int(RNG.integers(2, 14)), int(RNG.integers(2, 14))) for _ in range(40)]


def render_low():
    ox, oy = int(S.cam[0]), int(S.cam[1])
    box = (ox, oy, ox + LW, oy + LH)
    layer = WORLD.back.crop(box)
    front = WORLD.front.crop(box)
    if any(WORLD.get(x, y) == "lava" for x in range(ox // T, ox // T + 31) for y in range(oy // T, oy // T + 18)):
        pass
    layer.alpha_composite(front)
    d = ImageDraw.Draw(layer)
    c = S.c
    # grietas
    if c.target:
        tx, ty = c.target
        n = int(len(CRACK) * c.progress)
        for (px, py) in CRACK[:n]:
            d.point((tx * T + px - ox, ty * T + py - oy), fill=(20, 20, 20, 255))
            d.point((tx * T + px - ox + 1, ty * T + py - oy), fill=(20, 20, 20, 200))
    # personaje
    if c.sleeping:
        spr = char_sprite(c).rotate(90, expand=True)
        layer.alpha_composite(spr, (int(26 * T - ox - 6), int(17 * T - oy - 14)))
    else:
        spr = char_sprite(c)
        layer.alpha_composite(spr, (int(c.x * T - ox - 20), int(c.y * T - oy - 42)))
    # monstruo
    if S.monster:
        hop = abs(math.sin(S.t * 5)) * 5
        mx = int(S.monster["x"] * T - ox - 9)
        my = int(18 * T - oy - 18 - hop)
        layer.alpha_composite(monster_sprite(S.t), (mx, my))
    # partículas
    for p in S.particles:
        d.rectangle([p[0] - ox, p[1] - oy, p[0] - ox + 1, p[1] - oy + 1], fill=p[4] + (255,))
    # iluminación
    L = light_map(S).crop(box)
    a = np.asarray(layer).astype(np.float32)
    lm = np.asarray(L).astype(np.float32)[..., None] / 255.0
    tint = np.array([1.0, 1.0, 1.0]) * 0 + 1
    if S.day < 0.6:
        night = (0.6 - S.day) / 0.38
        tint = np.array([1 - 0.25 * night, 1 - 0.15 * night, 1.0])
    a[..., :3] = a[..., :3] * lm * tint
    layer = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    # ojos brillantes del monstruo
    if S.monster:
        d2 = ImageDraw.Draw(layer)
        d2.rectangle([mx + 4, my + 8, mx + 6, my + 10], fill=(255, 240, 80, 255))
        d2.rectangle([mx + 10, my + 8, mx + 12, my + 10], fill=(255, 240, 80, 255))
    sky = render_sky()
    sky.alpha_composite(layer)
    return sky.convert("RGB")


def text_shadow(d, xy, txt, fnt, fill, anchor="la", sh=4):
    x, y = xy
    d.text((x + sh, y + sh), txt, font=fnt, fill=(0, 0, 0, 170), anchor=anchor)
    d.text((x, y), txt, font=fnt, fill=fill, anchor=anchor)


def wrap(txt, fnt, maxw):
    words, lines, cur = txt.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if fnt.getlength(t) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_overlay(img):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # capítulo
    if S.chapter:
        f = font(F_TITLE, 40)
        w = int(f.getlength(S.chapter))
        d.rectangle([40, 40, 40 + w + 48, 112], fill=(20, 22, 28, 215))
        d.rectangle([40, 40, 52, 112], fill=(110, 190, 70, 255))
        d.text((76, 50), S.chapter, font=f, fill=(250, 250, 250))
    # inventario
    items = [k for k in INV_ORDER if S.inv.get(k, 0) > 0]
    if items:
        x = W - 40 - len(items) * 92
        d.rectangle([x - 14, 36, W - 30, 124], fill=(20, 22, 28, 200))
        for k in items:
            pop = max(0.0, 1 - (S.t - S.inv_pop.get(k, -9)) / 0.4)
            sz = int(56 + 16 * pop)
            ic = icon(k, sz)
            ov.alpha_composite(ic, (x + 8 + (56 - sz) // 2, 44 + (56 - sz) // 2))
            text_shadow(d, (x + 72, 112), str(S.inv[k]), font(F_BOLD, 28), (255, 255, 255), "rs", 2)
            x += 92
    # subtítulo
    if S.caption:
        f = font(F_BOLD, 44)
        lines = wrap(S.caption, f, W - 400)
        lh = 60
        hgt = lh * len(lines) + 40
        y0 = H - 70 - hgt
        d.rectangle([160, y0, W - 160, y0 + hgt], fill=(16, 18, 24, 215))
        d.rectangle([160, y0, W - 160, y0 + 6], fill=(250, 205, 70, 255))
        for i, ln in enumerate(lines):
            text_shadow(d, (W // 2, y0 + 26 + i * lh), ln, f, (255, 255, 255), "ma", 3)
    # receta
    if S.popup:
        p = S.popup
        a = min(1.0, (S.t - S.popup_t) / 0.3)
        pw = max(760, int(font(F_BOLD, 38).getlength(p["label"])) + 80)
        px, py = W // 2 - pw // 2, 230 - int(30 * (1 - a))
        al = int(235 * a)
        d.rectangle([px, py, px + pw, py + 420], fill=(198, 198, 204, al), outline=(40, 40, 44, al), width=6)
        px += (pw - 760) // 2
        for i in range(9):
            sx, sy = px + 50 + (i % 3) * 100, py + 40 + (i // 3) * 100
            d.rectangle([sx, sy, sx + 88, sy + 88], fill=(140, 140, 148, al), outline=(80, 80, 86, al), width=4)
            if p["in"][i]:
                ov.alpha_composite(icon(p["in"][i], 64), (sx + 12, sy + 12))
        d.polygon([(px + 400, py + 140), (px + 470, py + 140), (px + 470, py + 115), (px + 520, py + 170),
                   (px + 470, py + 225), (px + 470, py + 200), (px + 400, py + 200)], fill=(110, 110, 118, al))
        rx, ry = px + 560, py + 110
        d.rectangle([rx, ry, rx + 120, ry + 120], fill=(140, 140, 148, al), outline=(80, 80, 86, al), width=4)
        ov.alpha_composite(icon(p["out"], 88), (rx + 16, ry + 16))
        if p["n"] > 1:
            text_shadow(d, (rx + 112, ry + 112), str(p["n"]), font(F_BOLD, 40), (255, 255, 255), "rs", 3)
        d.text((px + 380, py + 370), p["label"], font=font(F_BOLD, 38), fill=(30, 30, 34, al), anchor="mm")
    # Zzz
    if S.zzz:
        f = font(F_TITLE, 60)
        for i in range(3):
            ph = (S.t * 0.8 + i / 3) % 1
            x = int((26.5 * T - S.cam[0]) * SCALE + 60 + ph * 80)
            y = int((16.4 * T - S.cam[1]) * SCALE - ph * 160)
            d.text((x, y), "Z", font=f, fill=(255, 255, 255, int(255 * (1 - ph))))
    # título
    if S.title:
        tt, sub, t0 = S.title
        a = min(1.0, (S.t - t0) / 0.8)
        f1, f2 = font(F_TITLE, 96), font(F_BOLD, 50)
        w1 = f1.getlength(tt)
        d.rectangle([W / 2 - w1 / 2 - 60, 330, W / 2 + w1 / 2 + 60, 600], fill=(16, 18, 24, int(200 * a)))
        d.rectangle([W / 2 - w1 / 2 - 60, 330, W / 2 + w1 / 2 + 60, 340], fill=(110, 190, 70, int(255 * a)))
        text_shadow(d, (W // 2, 360), tt, f1, (255, 255, 255, int(255 * a)), "ma", 5)
        text_shadow(d, (W // 2, 500), sub, f2, (250, 205, 70, int(255 * a)), "ma", 3)
        if "ESPERA" not in tt:
            d.text((W // 2, 640), "Guía no oficial", font=font(F_BODY, 32),
                   fill=(255, 255, 255, int(220 * a)), anchor="ma")
    img = img.convert("RGBA")
    img.alpha_composite(ov)
    if S.fade > 0:
        img = Image.blend(img, Image.new("RGBA", (W, H), (0, 0, 0, 255)), S.fade)
    return img.convert("RGB")


def update_particles():
    for p in S.particles:
        p[0] += p[2] / FPS
        p[1] += p[3] / FPS
        p[3] += 260 / FPS
        p[5] -= 1 / FPS
    S.particles = [p for p in S.particles if p[5] > 0]


# --------------------------------------------------------------- música
def make_music(path, seconds):
    sr = 44100
    n = int(seconds * sr)
    out = np.zeros(n)
    beat = 60 / 88
    roots = [48, 52, 45, 43]
    pat = [0, 7, 12, 7, 16, 12, 7, 12]
    step = beat / 2
    for k in range(int(seconds / step) + 1):
        s0 = int(k * step * sr)
        s1 = min(n, int((k + 1) * step * sr))
        if s0 >= n:
            break
        tt = np.arange(s1 - s0) / sr
        root = roots[(k // 16) % 4]
        f = 440 * 2 ** ((root + 12 + pat[k % 8] - 69) / 12)
        tone = 0.6 * np.sin(2 * np.pi * f * tt) + 0.25 * np.sign(np.sin(2 * np.pi * f * tt))
        out[s0:s1] += 0.10 * tone * np.exp(-tt * 5)
        if k % 4 == 0:
            fb = 440 * 2 ** ((root - 69) / 12)
            seg = min(s1 - s0 + int(step * sr), n - s0)
            tb = np.arange(seg) / sr
            out[s0:s0 + seg] += 0.14 * np.sin(2 * np.pi * fb * tb) * np.exp(-tb * 1.5)
    fi = int(2 * sr)
    out[:fi] *= np.linspace(0, 1, fi)
    out[-3 * sr:] *= np.linspace(1, 0, 3 * sr)
    out = out / (np.abs(out).max() + 1e-9) * 0.3
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


def main(preview=None):
    if preview:
        n = 0
        for _ in story():
            update_particles()
            update_camera()
            if n in preview:
                render_overlay(render_low().resize((W, H), Image.NEAREST)).resize((960, 540)).save(
                    os.path.join(preview_dir, f"f{n:05d}.png"))
            S.t += 1 / FPS
            n += 1
            if n > max(preview):
                break
        return
    vid = os.path.join(OUT_DIR, "_tmp_video.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-pix_fmt", "yuv420p", vid]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = 0
    for _ in story():
        update_particles()
        update_camera()
        frame = render_overlay(render_low().resize((W, H), Image.NEAREST))
        proc.stdin.write(frame.tobytes())
        S.t += 1 / FPS
        n += 1
        if n % 300 == 0:
            print(f"{n / FPS:.0f} s renderizados", flush=True)
    proc.stdin.close()
    proc.wait()
    secs = n / FPS
    wav = os.path.join(OUT_DIR, "_musica.wav")
    make_music(wav, secs)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", wav, "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", OUT], check=True)
    os.remove(vid)
    os.remove(wav)
    print("OK ->", OUT, f"({secs:.1f} s)")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--preview":
        preview_dir = sys.argv[2]
        main(preview={int(x) for x in sys.argv[3:]})
    else:
        main()
