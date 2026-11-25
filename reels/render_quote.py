"""Ma'noli iqtibos-reels: kinematik fon + satrma-satr chiqadigan matn + yumshoq musiqa.
1080x1920, 30 fps. Foydalanish: render(matn_satrlari, chiqish.mp4, uslub="rain"|"stars"|"sunset"|"road", seed=..)
"""
import math, os, random, subprocess, wave
import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, "..", "assets", "fonts", "Montserrat.ttf")
_fc = {}


def font(size, weight="SemiBold"):
    k = (size, weight)
    if k not in _fc:
        f = ImageFont.truetype(FONT, size)
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
        _fc[k] = f
    return _fc[k]


def ease(x):
    x = max(0.0, min(1.0, x)); return 0.5 - 0.5 * math.cos(math.pi * x)


# ---------------- fonlar ----------------
class Background:
    def __init__(self, style, seed):
        self.style = style; self.rnd = random.Random(seed)
        r = self.rnd
        self.drops = [(r.uniform(0, W), r.uniform(0, H), r.uniform(4, 16), r.uniform(0.2, 1)) for _ in range(140)]
        self.bokeh = [(r.uniform(0, W), r.uniform(0, H), r.uniform(40, 140), r.choice([(1, .75, .4), (1, .5, .3), (.5, .7, 1), (1, .9, .6)]),
                       r.uniform(0, 6.28)) for _ in range(26)]
        self.stars = [(r.uniform(0, W), r.uniform(0, H * 0.85), r.uniform(1, 3.2), r.uniform(0, 6.28)) for _ in range(260)]
        self.dust = [(r.uniform(0, W), r.uniform(0, H), r.uniform(2, 6), r.uniform(0, 6.28)) for _ in range(70)]

    def draw(self, ctx, t):
        getattr(self, "_" + self.style)(ctx, t)
        # vinyetka
        g = cairo.RadialGradient(W / 2, H / 2, 300, W / 2, H / 2, 1250)
        g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.75)
        ctx.set_source(g); ctx.paint()

    def _grad(self, ctx, stops):
        g = cairo.LinearGradient(0, 0, 0, H)
        for p, c in stops: g.add_color_stop_rgb(p, *c)
        ctx.set_source(g); ctx.paint()

    def _rain(self, ctx, t):  # tungi shahar, derazadagi yomg'ir
        self._grad(ctx, [(0, (.05, .06, .12)), (.6, (.10, .08, .16)), (1, (.18, .10, .12))])
        for x, y, r, c, ph in self.bokeh:
            rr = r * (1 + 0.08 * math.sin(t * .8 + ph))
            g = cairo.RadialGradient(x, y + 20 * math.sin(t * .3 + ph), 0, x, y, rr)
            g.add_color_stop_rgba(0, *c, .35); g.add_color_stop_rgba(1, *c, 0)
            ctx.set_source(g); ctx.arc(x, y, rr, 0, 6.29); ctx.fill()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for x, y0, ln, sp in self.drops:
            y = (y0 + t * 900 * sp) % (H + 100) - 50
            ctx.set_source_rgba(.8, .85, 1, .10 + .18 * sp); ctx.set_line_width(1.5 + sp * 1.5)
            ctx.move_to(x, y); ctx.line_to(x - 2, y + ln * 3); ctx.stroke()

    def _stars(self, ctx, t):  # yulduzli tun
        self._grad(ctx, [(0, (.01, .02, .07)), (.7, (.05, .07, .20)), (1, (.15, .10, .25))])
        for x, y, r, ph in self.stars:
            a = .35 + .65 * (0.5 + 0.5 * math.sin(t * 2 + ph))
            ctx.set_source_rgba(1, 1, 1, a); ctx.arc(x + t * 4 * (r / 3), y, r, 0, 6.29); ctx.fill()
        # tog' silueti
        ctx.set_source_rgb(.02, .02, .05); ctx.move_to(0, H)
        for i in range(0, W + 60, 60):
            ctx.line_to(i, H - 260 - 120 * math.sin(i * 0.006 + 1) - 60 * math.sin(i * 0.017))
        ctx.line_to(W, H); ctx.close_path(); ctx.fill()

    def _sunset(self, ctx, t):  # quyosh botishi, bulutlar, zarralar
        self._grad(ctx, [(0, (.16, .10, .30)), (.45, (.75, .32, .35)), (.75, (.98, .62, .35)), (1, (.30, .12, .20))])
        sy = 1250 + 30 * math.sin(t * .2)
        g = cairo.RadialGradient(W / 2, sy, 20, W / 2, sy, 420)
        g.add_color_stop_rgba(0, 1, .9, .7, .95); g.add_color_stop_rgba(1, 1, .6, .3, 0)
        ctx.set_source(g); ctx.paint()
        for i in range(5):
            y = 500 + i * 160; off = (t * (12 + i * 6)) % 400
            ctx.set_source_rgba(.35, .15, .30, .18)
            for k in range(-1, 5):
                ctx.save(); ctx.translate(k * 400 - off + i * 70, y); ctx.scale(1, .18)
                ctx.arc(0, 0, 260, 0, 6.29); ctx.restore(); ctx.fill()
        for x, y, r, ph in self.dust:
            ctx.set_source_rgba(1, .9, .7, .5); ctx.arc((x + t * 15) % W, (y - t * 25) % H, r, 0, 6.29); ctx.fill()

    def _road(self, ctx, t):  # tungi yo'l, chiroqlar oqimi
        self._grad(ctx, [(0, (.03, .03, .07)), (.55, (.07, .06, .12)), (1, (.02, .02, .03))])
        hy = 820
        for i in range(40):
            p = ((i / 40) + t * .35) % 1
            z = p ** 2.2
            for side, col in ((-1, (1, .85, .55)), (1, (1, .25, .2))):
                x = W / 2 + side * (40 + z * 900); y = hy + z * 1150
                ctx.set_source_rgba(*col, .25 + .6 * z)
                ctx.arc(x, y, 3 + 22 * z, 0, 6.29); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, .5)
        for i in range(12):
            p = ((i / 12) + t * .5) % 1; z = p ** 2.2
            y = hy + z * 1150; h = 10 + 120 * z; w = 2 + 10 * z
            ctx.rectangle(W / 2 - w / 2, y, w, h); ctx.fill()


# ---------------- matn ----------------
def wrap(d, text, f, maxw, with_para=False):
    out = []; paras = []
    for pi, para in enumerate(text.split("\n")):
        before = len(out)
        cur = ""
        for w in para.split():
            tt = (cur + " " + w).strip()
            if d.textlength(tt, font=f) <= maxw: cur = tt
            else:
                if cur: out.append(cur)
                cur = w
        out.append(cur)
        paras += [pi] * (len(out) - before)
    return (out, paras) if with_para else out


def text_layer(lines, t, line_times, size, accent_idx=None):
    accent = accent_idx if isinstance(accent_idx, (set, list, tuple)) else ({accent_idx} if accent_idx is not None else set())
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(size, "SemiBold"); fa = font(int(size * 1.12), "ExtraBold")
    lh = int(size * 1.38)
    total = lh * len(lines)
    y0 = int(H * 0.40 - total / 2)
    for i, ln in enumerate(lines):
        a = ease((t - line_times[i]) / 0.7)
        if a <= 0: continue
        ff = fa if i in accent else f
        if i in accent:
            k = int(size * 1.12)
            while d.textlength(ln, font=ff) > 990 and k > size * 0.8:
                k -= 2; ff = font(k, "ExtraBold")
        tw = d.textlength(ln, font=ff)
        x = (W - tw) / 2; y = y0 + i * lh + (1 - a) * 25
        col = (255, 214, 120) if i in accent else (255, 255, 255)
        # soya
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        sd.text((x + 3, y + 5), ln, font=ff, fill=(0, 0, 0, int(200 * a)))
        layer.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
        d.text((x, y), ln, font=ff, fill=col + (int(255 * a),))
    return layer


# ---------------- musiqa ----------------
def make_music(dur, path, seed=0):
    sr = 44100; n = int(dur * sr); t = np.arange(n) / sr
    rnd = random.Random(seed)
    progs = [[(220, 261.6, 329.6), (174.6, 220, 261.6), (261.6, 329.6, 392), (196, 246.9, 293.7)],
             [(146.8, 174.6, 220), (116.5, 146.8, 174.6), (174.6, 220, 261.6), (130.8, 164.8, 196)]]
    prog = rnd.choice(progs); seg = dur / 4
    out = np.zeros(n)
    for k, ch in enumerate(prog):
        s = int(k * seg * sr); e = min(n, int((k + 1) * seg * sr) + sr)
        tt = t[: e - s]
        env = np.minimum(1, tt / 0.8) * np.exp(-tt / 5)
        for f0 in ch:
            out[s:e] += (np.sin(2 * np.pi * f0 * tt) + 0.3 * np.sin(4 * np.pi * f0 * tt)) * env * 0.08
        # pianino notasi
        for j in range(4):
            ns = s + int(j * seg / 4 * sr); ne = min(n, ns + int(1.6 * sr)); tn = t[: ne - ns]
            fn = ch[rnd.randrange(3)] * 2
            out[ns:ne] += np.sin(2 * np.pi * fn * tn) * np.exp(-tn * 3) * 0.10
    fade = np.ones(n); fl = int(1.5 * sr); fade[-fl:] = np.linspace(1, 0, fl); fade[:int(.5 * sr)] = np.linspace(0, 1, int(.5 * sr))
    out = np.tanh(out * fade * 1.5) * 0.7
    st = (np.stack([out, out], 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(st.tobytes())


# ---------------- asosiy ----------------
def render(text, out_path, style="rain", seed=1, top_label=None):
    """text: bir nechta satrli iqtibos (\n bilan ajratilgan qism-satrlar bo'lishi mumkin)."""
    tmpimg = Image.new("RGB", (10, 10)); d = ImageDraw.Draw(tmpimg)
    n_par = len([p for p in text.split("\n")])
    size = 72
    while True:
        lines, paras = wrap(d, text, font(size, "SemiBold"), 920, with_para=True)
        if (len(lines) == n_par and len(lines) * size * 1.38 < 950) or size <= 46:
            break
        size -= 2
    last = max(paras) if paras else 0
    accent = {i for i, p in enumerate(paras) if p == last} if n_par >= 3 else set()
    start = 0.8; step = 0.9
    line_times = [start + i * step for i in range(len(lines))]
    dur = max(9.0, line_times[-1] + 4.5)
    dur = min(dur, 20.0)
    bg = Background(style, seed)
    base, _ = os.path.splitext(out_path)
    vtmp = base + ".v.tmp.mp4"; atmp = base + ".a.wav"; otmp = base + ".tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                          "-pix_fmt", "yuv420p", vtmp], stdin=subprocess.PIPE)
    lab = None
    if top_label:
        lab = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lab)
        fl = font(36, "Medium"); tw = ld.textlength(top_label, font=fl)
        ld.text(((W - tw) / 2, 300), top_label, font=fl, fill=(255, 255, 255, 170))
    for i in range(int(dur * FPS)):
        t = i / FPS
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
        z = 1 + 0.06 * t / dur  # sekin zoom
        ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2)
        bg.draw(ctx, t); surf.flush()
        img = Image.frombuffer("RGBA", (W, H), bytes(surf.get_data()), "raw", "BGRA", 0, 1).copy()
        img.alpha_composite(text_layer(lines, t, line_times, size, accent))
        if lab is not None:
            img.alpha_composite(lab)
        fo = min(1, max(0, (dur - t) / 0.6))
        frame = img.convert("RGB")
        if fo < 1:
            frame = Image.blend(Image.new("RGB", (W, H)), frame, fo)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("video render xatosi")
    make_music(dur, atmp, seed)
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vtmp, "-i", atmp, "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", otmp])
    if r.returncode != 0:
        raise RuntimeError("audio qo'shish xatosi")
    os.replace(otmp, out_path)
    for f in (vtmp, atmp):
        try: os.remove(f)
        except OSError: pass
    return out_path


if __name__ == "__main__":
    import sys
    style = sys.argv[2] if len(sys.argv) > 2 else "rain"
    render("Время не лечит.\nОно просто учит жить\nс тем, что болит.\nИ это тоже сила.", sys.argv[1], style, 7, "Как-то так...")
