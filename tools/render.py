"""Render realistic sprites for every solar system object in the game.

Real bodies use equirectangular maps (gravityexp npm package; Earth from NASA Blue Marble via three-globe).
Bodies without a public map are built procedurally from what spacecraft images show.
Output: img/<id>.webp with transparent background, plus img/manifest.json (canvas margin per sprite).
"""
import json, math, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
GX = os.path.join(HERE, "pkgs/gx/package/public/textures")
TG = os.path.join(HERE, "pkgs/tg/package/example")
OUT = os.path.join(HERE, "..", "img")
os.makedirs(OUT, exist_ok=True)
SS = 2  # supersampling
LIGHT = np.array([-0.45, -0.35, 0.82]); LIGHT /= np.linalg.norm(LIGHT)
manifest = {}

def load_tex(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0

def sample_eq(tex, lat, lon):
    H, W = tex.shape[:2]
    u = ((lon / (2 * np.pi) + 0.5) % 1.0) * W - 0.5
    v = np.clip((0.5 - lat / np.pi) * H - 0.5, 0, H - 1.001)
    u0 = np.floor(u).astype(int); v0 = np.floor(v).astype(int)
    du = (u - u0)[..., None]; dv = (v - v0)[..., None]
    u0 %= W; u1 = (u0 + 1) % W; v1 = np.minimum(v0 + 1, H - 1)
    a = tex[v0, u0]; b = tex[v0, u1]; c = tex[v1, u0]; d = tex[v1, u1]
    return (a * (1 - du) + b * du) * (1 - dv) + (c * (1 - du) + d * du) * dv

# ---------- procedural noise on the sphere ----------
class Noise:
    def __init__(self, seed):
        r = np.random.default_rng(seed)
        self.perm = r.permutation(256)
        self.vals = r.random(256).astype(np.float32)
    def _h(self, ix, iy, iz):
        p = self.perm
        return self.vals[p[(p[(p[ix & 255] + iy) & 255] + iz) & 255]]
    def v3(self, P):
        i = np.floor(P).astype(np.int64); f = P - i; w = f * f * (3 - 2 * f)
        x, y, z = i[..., 0], i[..., 1], i[..., 2]
        wx, wy, wz = w[..., 0], w[..., 1], w[..., 2]
        c = lambda a, b, cc: self._h(x + a, y + b, z + cc)
        x00 = c(0,0,0)*(1-wx) + c(1,0,0)*wx; x10 = c(0,1,0)*(1-wx) + c(1,1,0)*wx
        x01 = c(0,0,1)*(1-wx) + c(1,0,1)*wx; x11 = c(0,1,1)*(1-wx) + c(1,1,1)*wx
        return (x00*(1-wy) + x10*wy)*(1-wz) + (x01*(1-wy) + x11*wy)*wz
    def fbm(self, P, octaves=5, lac=2.0, gain=0.5):
        s, a, f, norm = 0.0, 1.0, 1.0, 0.0
        for k in range(octaves):
            s = s + a * self.v3(P * f + k * 17.31); norm += a; a *= gain; f *= lac
        return s / norm

def craters(n, N, seed, count, rmin, rmax, depth=1.0):
    """Albedo/shading change from impact craters. Returns multiplier array."""
    r = np.random.default_rng(seed)
    m = np.ones(N.shape[:-1], dtype=np.float32)
    for _ in range(count):
        c = r.normal(size=3); c /= np.linalg.norm(c)
        rad = rmin * (rmax / rmin) ** (r.random() ** 2.2)
        cosd = np.clip(N @ c, -1, 1)
        near = cosd > math.cos(rad * 1.6)
        if not near.any(): continue
        d = np.arccos(cosd[near]); t = d / rad
        g = N[near] - np.outer(cosd[near], c)
        gl = np.linalg.norm(g, axis=1) + 1e-6
        side = (g @ LIGHT) / gl  # >0: wall faces the light
        inner = np.where(t < 1, -0.28 * depth * side * t - 0.06 * depth, 0)
        rim = 0.22 * depth * np.exp(-((t - 1.0) / 0.16) ** 2) * (0.6 + 0.4 * side)
        ej = np.where(t > 1, 0.05 * depth * np.exp(-(t - 1) * 3), 0)
        m[near] *= 1 + inner + rim + ej
    return m

def palette(t, stops):
    t = np.clip(t, 0, 1); out = np.zeros(t.shape + (3,), np.float32)
    xs = [s[0] for s in stops]; cols = [np.array(s[1], np.float32) / 255 for s in stops]
    for ch in range(3):
        out[..., ch] = np.interp(t, xs, [c[ch] for c in cols])
    return out

# ---------- the sphere renderer ----------
def render(name, size, color_fn, margin=1.08, tilt=0.0, obs=12.0, lon0=0.0, limb=0.55, atm=None, atm_w=0.05,
           sx=1.0, shape=None, extra=None, back=None):
    n = size * SS
    lin = (np.arange(n) + 0.5) / n * 2 - 1
    X, Y = np.meshgrid(lin * margin, lin * margin)
    x = X / sx; y = Y.copy()
    rr = np.sqrt(x * x + y * y)
    if shape is not None:  # lumpy outline
        th = np.arctan2(y, x); R = shape(th); x = x / R; y = y / R; rr = np.sqrt(x * x + y * y)
    inside = rr <= 1.0
    z = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
    N = np.stack([x, -y, z], -1)  # view-space normal, +y up
    # orient the globe: tip toward the viewer by `obs`, then spin the axis by `tilt`
    t = math.radians(tilt); o = math.radians(obs)
    Rz = np.array([[math.cos(t), -math.sin(t), 0], [math.sin(t), math.cos(t), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, math.cos(o), -math.sin(o)], [0, math.sin(o), math.cos(o)]])
    B = N @ Rz @ Rx  # body-frame normal
    lat = np.arcsin(np.clip(B[..., 1], -1, 1)); lon = np.arctan2(B[..., 0], B[..., 2]) + math.radians(lon0)
    rgb = color_fn(lat, lon, B, N)
    # soft studio light + limb darkening (terminator is added live in the game, facing the Sun)
    lam = np.clip(N @ LIGHT, 0, 1)
    shade = (1 - limb * (1 - z ** 0.5)) * (0.72 + 0.38 * lam)
    rgb = rgb * shade[..., None]
    alpha = inside.astype(np.float32)
    if atm is not None:
        ac = np.array(atm[:3], np.float32) / 255; strength = atm[3]
        rim = (1 - z) ** 3 * strength
        rgb = np.where(inside[..., None], rgb * (1 - rim[..., None]) + ac * rim[..., None], rgb)
        out_r = rr - 1
        glow = np.where(~inside, strength * np.exp(-np.maximum(out_r, 0) / atm_w), 0)
        rgb = np.where(inside[..., None], rgb, ac)
        alpha = np.maximum(alpha, glow)
    img = np.concatenate([np.clip(rgb, 0, 1), alpha[..., None]], -1)
    if back is not None: img = over(img, back(X, Y))
    if extra is not None: img = extra(img, X, Y, inside)
    save(name, img, size, margin)

def over(top, bottom):
    a = top[..., 3:4]; b = bottom[..., 3:4]
    out_a = a + b * (1 - a)
    rgb = (top[..., :3] * a + bottom[..., :3] * b * (1 - a)) / np.maximum(out_a, 1e-6)
    return np.concatenate([rgb, out_a], -1)

def save(name, img, size, margin):
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA").resize((size, size), Image.LANCZOS)
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=86, method=6)
    manifest[name] = round(margin, 3)
    print(name, size, os.path.getsize(os.path.join(OUT, f"{name}.webp")) // 1024, "KB")

def tex_fn(path, gain=1.0, gamma=1.0):
    T = load_tex(path)
    return lambda lat, lon, B, N: np.clip(sample_eq(T, lat, lon) * gain, 0, 1) ** gamma

def find_lon(path, region):
    """Longitude (deg) of the reddest pixel inside a latitude band: used to face the Great Red Spot / heart forward."""
    T = load_tex(path); H, W = T.shape[:2]
    y0, y1 = int(H * region[0]), int(H * region[1])
    band = T[y0:y1]; score = band[..., 0] - band[..., 2] if region[2] == "red" else band.mean(-1)
    col = np.argmax(score.mean(0) if region[2] != "red" else score.max(0))
    return (col / W - 0.5) * 360

# ---------- rings ----------
def saturn_rings(incl=22):
    s = math.sin(math.radians(incl))
    bands = [  # inner, outer (planet radii), opacity, brightness
        (1.24, 1.53, 0.18, 0.62), (1.53, 1.95, 0.9, 1.0), (1.95, 2.03, 0.08, 0.5),
        (2.03, 2.21, 0.65, 0.88), (2.21, 2.216, 0.0, 0.0), (2.216, 2.27, 0.55, 0.82)]
    nz = Noise(5)
    def layer(X, Y, front):
        u = X; v = Y / s; r = np.sqrt(u * u + v * v)
        a = np.zeros_like(r); b = np.zeros_like(r)
        for lo, hi, op, br in bands:
            m = (r >= lo) & (r < hi); a[m] = op; b[m] = br
        fine = nz.fbm(np.stack([r * 60, r * 3, r * 0], -1), 3)
        a *= 0.75 + 0.5 * fine; b *= 0.85 + 0.3 * fine
        sel = (Y > 0) if front else (Y <= 0)
        a = np.where(sel, a, 0)
        col = palette(b, [(0, (120, 100, 80)), (0.6, (196, 172, 132)), (1, (236, 220, 186))])
        # the planet's shadow falls across the far rings
        return np.concatenate([col, np.clip(a, 0, 1)[..., None]], -1)
    return layer

def ringed(name, size, color_fn, ring_layer, margin, **kw):
    render(name, size, color_fn, margin=margin, back=lambda X, Y: ring_layer(X, Y, False),
           extra=lambda img, X, Y, inside: over(ring_layer(X, Y, True), img), **kw)

# ---------- procedural surfaces ----------
def proc(seed, base_stops, freq=2.2, octaves=5, crater=None, extra=None, warp=0.0):
    nz = Noise(seed)
    def fn(lat, lon, B, N):
        P = B * freq
        if warp: P = P + warp * np.stack([nz.fbm(P + 3.1, 3), nz.fbm(P + 7.7, 3), nz.fbm(P + 1.3, 3)], -1)
        t = nz.fbm(P, octaves)
        rgb = palette((t - 0.25) / 0.5, base_stops)
        if crater: rgb = rgb * craters(None, B, seed + 1, *crater)[..., None]
        if extra: rgb = extra(rgb, lat, lon, B, nz)
        return rgb
    return fn

def venus_clouds(lat, lon, B, N):
    nz = Noise(11)
    P = B * 2.0
    w = np.stack([nz.fbm(P + 1, 4), nz.fbm(P + 5, 4), nz.fbm(P + 9, 4)], -1)
    swirl = nz.fbm(np.stack([lon * 0.8, lat * 5, lat * 0], -1) + 2.2 * w, 5)
    chevron = np.sin(lat * 7 + np.abs(lat) * 4 + 3 * w[..., 0])
    t = 0.55 * swirl + 0.12 * chevron + 0.25
    return palette(t, [(0, (176, 140, 82)), (0.45, (222, 196, 140)), (0.8, (244, 232, 196)), (1, (252, 246, 224))])

def io_extra(rgb, lat, lon, B, nz):
    r = np.random.default_rng(42)
    for _ in range(26):
        c = r.normal(size=3); c /= np.linalg.norm(c); rad = 0.03 + 0.06 * r.random()
        d = np.arccos(np.clip(B @ c, -1, 1))
        halo = np.exp(-((d / (rad * 2.4)) ** 2))[..., None]
        core = (d < rad * 0.45)[..., None]
        rgb = rgb * (1 - 0.45 * halo) + np.array([0.75, 0.35, 0.12]) * 0.45 * halo
        rgb = np.where(core, np.array([0.12, 0.08, 0.06]), rgb)
    return rgb

def europa_extra(rgb, lat, lon, B, nz):
    for k, f in enumerate([2.0, 3.3, 5.1]):
        v = nz.fbm(B * f + k * 9.3, 4)
        line = np.exp(-((v - 0.5) / 0.012) ** 2)[..., None]
        rgb = rgb * (1 - 0.4 * line) + np.array([0.55, 0.32, 0.2]) * 0.4 * line
    return rgb

def ganymede_extra(rgb, lat, lon, B, nz):
    m = (nz.fbm(B * 1.6 + 4, 4) > 0.5)[..., None]
    grooves = 0.92 + 0.08 * np.sin(nz.fbm(B * 3, 3) * 80)[..., None]
    light = np.array([0.72, 0.68, 0.62]) * grooves
    return np.where(m, rgb * 0.35 + light * 0.65, rgb)

def enceladus_extra(rgb, lat, lon, B, nz):
    south = (lat < -math.radians(50))[..., None]
    k = np.sin((B[..., 0] * 0.8 + B[..., 2] * 0.6) * 22 + nz.fbm(B * 4, 3) * 3)
    stripe = np.exp(-((k - 1) / 0.08) ** 2)[..., None]
    return np.where(south, rgb * (1 - 0.6 * stripe) + np.array([0.45, 0.62, 0.78]) * 0.6 * stripe, rgb)

def triton_extra(rgb, lat, lon, B, nz):
    cell = np.abs(nz.fbm(B * 9, 3) - 0.5)
    rgb = rgb * (0.9 + 0.25 * cell[..., None])
    cap = np.clip((-lat - 0.1) / 0.5, 0, 1)[..., None]
    return rgb * (1 - cap) + np.array([0.93, 0.8, 0.76]) * cap

def charon_extra(rgb, lat, lon, B, nz):
    cap = np.clip((lat - math.radians(55)) / 0.35, 0, 1)[..., None]
    return rgb * (1 - 0.8 * cap) + np.array([0.42, 0.22, 0.15]) * 0.8 * cap

def ceres_extra(rgb, lat, lon, B, nz):
    c = np.array([0.35, 0.3, 0.88]); c /= np.linalg.norm(c)
    d = np.arccos(np.clip(B @ c, -1, 1))
    spot = np.exp(-((d / 0.035) ** 2))[..., None]; spot2 = np.exp(-(((d - 0.06) / 0.015) ** 2))[..., None] * 0.6
    return rgb * (1 - spot - spot2) + (spot + spot2) * np.array([1, 1, 1])

def haumea_extra(rgb, lat, lon, B, nz):
    c = np.array([0.4, -0.1, 0.9]); c /= np.linalg.norm(c)
    d = np.arccos(np.clip(B @ c, -1, 1)); spot = np.exp(-((d / 0.28) ** 2))[..., None]
    return rgb * (1 - 0.55 * spot) + np.array([0.55, 0.28, 0.22]) * 0.55 * spot

def lumpy(seed, amp=0.1, elong=1.0):
    r = np.random.default_rng(seed); ph = r.random(4) * 6.28
    return lambda th: (1 + amp * np.sin(2 * th + ph[0]) + amp * 0.6 * np.sin(3 * th + ph[1]) + amp * 0.4 * np.sin(5 * th + ph[2])) * \
                      np.sqrt(1 / ((np.cos(th) / elong) ** 2 + np.sin(th) ** 2))

# ---------- build every sprite ----------
def sun_fn():
    T = load_tex(f"{GX}/sun.jpg")
    def fn(lat, lon, B, N):
        lum = sample_eq(T, lat, lon).mean(-1)
        z = np.clip(N[..., 2], 0, 1)
        base = palette(z ** 0.7, [(0, (236, 96, 12)), (0.45, (255, 178, 52)), (0.8, (255, 226, 130)), (1, (255, 246, 210))])
        return np.clip(base * (0.9 + 0.35 * (lum - lum.mean()))[..., None], 0, 1)
    return fn

render("sun", 640, sun_fn(), margin=1.55, limb=0.2, atm=(255, 170, 60, 0.9), atm_w=0.16, obs=0)
render("mercury", 384, tex_fn(f"{GX}/mercury.jpg"), lon0=40, limb=0.35)
render("venus", 448, venus_clouds, tilt=3, limb=0.25, atm=(255, 236, 190, 0.55), atm_w=0.03)
CL = np.asarray(Image.open(f"{TG}/clouds/clouds.png").convert("RGBA"), dtype=np.float32)[..., 3:4] / 255.0
EARTH = load_tex(f"{TG}/img/earth-blue-marble.jpg")
def earth_fn(lat, lon, B, N):
    g = sample_eq(EARTH, lat, lon)
    a = np.clip(sample_eq(np.repeat(CL, 3, -1), lat, lon + 0.6)[..., :1] * 1.25, 0, 0.92)
    return g * (1 - a) + a * 0.97
render("earth", 512, earth_fn, tilt=-23, lon0=18, limb=0.3, atm=(110, 170, 255, 0.85), atm_w=0.045)
render("mars", 448, tex_fn(f"{GX}/mars.jpg", 1.05), tilt=-25, lon0=-95, limb=0.35, atm=(255, 170, 130, 0.35), atm_w=0.025)
grs = find_lon(f"{GX}/jupiter.jpg", (0.55, 0.7, "red"))
render("jupiter", 640, tex_fn(f"{GX}/jupiter.jpg", 1.05), tilt=-3, obs=4, lon0=grs + 10, limb=0.6, atm=(240, 220, 190, 0.2), atm_w=0.02)
ringed("saturn", 768, tex_fn(f"{GX}/saturn.jpg", 1.05), saturn_rings(22), margin=2.32, tilt=0, obs=22, limb=0.6)
def uranus_rings(X, Y, front):
    u = Y; v = X / math.sin(math.radians(14)); r = np.sqrt(u * u + v * v)
    a = 0.32 * (np.exp(-((r - 1.95) / 0.012) ** 2) + 0.5 * np.exp(-((r - 1.75) / 0.01) ** 2) + 0.4 * np.exp(-((r - 1.62) / 0.01) ** 2))
    a = np.where((X > 0) if front else (X <= 0), a, 0)
    col = np.ones(X.shape + (3,), np.float32) * np.array([0.75, 0.85, 0.9])
    return np.concatenate([col, a[..., None]], -1)
ringed("uranus", 512, tex_fn(f"{GX}/uranus.jpg", 1.05), uranus_rings, margin=2.05, tilt=-98, obs=10, limb=0.5)
render("neptune", 448, tex_fn(f"{GX}/neptune.jpg", 1.1), tilt=-28, lon0=0, limb=0.55, atm=(120, 160, 255, 0.35), atm_w=0.025)
PL = load_tex(f"{GX}/pluto.jpg")
def pluto_fn(lat, lon, B, N):  # the map is grey; tint it with New Horizons' colours (red-brown lowlands, tan, cream heart)
    lum = sample_eq(PL, lat, lon).mean(-1)
    t = (lum - np.percentile(lum, 3)) / (np.percentile(lum, 99) - np.percentile(lum, 3))
    return palette(t, [(0, (82, 44, 30)), (0.35, (150, 104, 76)), (0.65, (206, 176, 146)), (1, (248, 240, 226))])
render("pluto", 320, pluto_fn, tilt=-15, lon0=30, limb=0.3)
render("moon", 320, tex_fn(f"{GX}/moon.jpg", 1.05), lon0=0, limb=0.25)

grey = [(0, (70, 66, 62)), (0.5, (128, 122, 116)), (1, (176, 170, 162))]
render("ceres", 320, proc(21, [(0, (78, 74, 70)), (0.5, (118, 113, 108)), (1, (150, 146, 140))], 3, 5, (60, 0.03, 0.22, 0.9), ceres_extra), limb=0.3)
render("haumea", 320, proc(22, [(0, (196, 200, 210)), (1, (245, 247, 252))], 2.5, 4, (12, 0.05, 0.15, 0.4), haumea_extra), sx=1.6, margin=1.7, limb=0.3)
render("makemake", 288, proc(23, [(0, (140, 78, 50)), (0.5, (184, 118, 82)), (1, (226, 176, 140))], 2.4, 5), limb=0.3)
render("eris", 288, proc(24, [(0, (196, 198, 206)), (1, (240, 241, 246))], 3, 5, (14, 0.04, 0.12, 0.5)), limb=0.3)
render("phobos", 256, proc(25, [(0, (70, 62, 55)), (0.5, (104, 94, 84)), (1, (132, 120, 108))], 3, 5, (45, 0.04, 0.4, 1.1)),
       shape=lumpy(25, 0.08, 1.35), margin=1.5, limb=0.25)
render("io", 288, proc(26, [(0, (196, 160, 60)), (0.5, (232, 208, 96)), (0.8, (244, 236, 170)), (1, (226, 140, 70))], 2.6, 5, None, io_extra), limb=0.3)
render("europa", 288, proc(27, [(0, (186, 164, 132)), (0.6, (222, 208, 182)), (1, (240, 232, 214))], 2.4, 4, None, europa_extra), limb=0.25)
render("ganymede", 320, proc(28, [(0, (78, 70, 62)), (0.6, (112, 102, 92)), (1, (140, 130, 120))], 2.4, 5, (40, 0.02, 0.12, 0.8), ganymede_extra), limb=0.3)
render("enceladus", 256, proc(29, [(0, (222, 228, 236)), (1, (252, 253, 255))], 3, 4, (25, 0.03, 0.12, 0.5), enceladus_extra), limb=0.2, obs=-25)
render("titan", 320, proc(30, [(0, (196, 136, 54)), (0.5, (220, 160, 74)), (1, (234, 184, 100))], 1.2, 3), limb=0.15, atm=(240, 170, 80, 0.85), atm_w=0.06)
render("triton", 288, proc(31, [(0, (196, 168, 160)), (0.6, (226, 206, 198)), (1, (246, 234, 228))], 2.6, 5, None, triton_extra), limb=0.25, obs=-20)
render("charon", 288, proc(32, [(0, (110, 110, 116)), (0.5, (150, 150, 156)), (1, (184, 184, 190))], 3, 5, (30, 0.03, 0.18, 0.8), charon_extra), limb=0.3, obs=25)
render("halley", 192, proc(33, [(0, (40, 36, 33)), (1, (78, 72, 66))], 3.5, 5, (10, 0.05, 0.2, 0.8)), shape=lumpy(33, 0.18, 1.6), margin=1.7, limb=0.2)

json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=0)
print("total KB", sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) // 1024)
