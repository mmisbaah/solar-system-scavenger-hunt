"""Sprites for the Milky Way map: the galaxy itself, stars, nebulae, a cluster, the central black hole and two neighbouring galaxies.
All procedural (numpy), shaped after what telescope images show. Galaxy geometry matches the game's galaxy units (±440 units, 1 unit = 120 light-years)."""
import json, math, os
import numpy as np
from PIL import Image, ImageFilter
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.py")).read()
exec(src.split("# ---------- build every sprite ----------")[0])
manifest.update(json.load(open(os.path.join(OUT, "manifest.json"))))

def noise2(nz, X, Y, f, octaves=5):
    return nz.fbm(np.stack([X * f, Y * f, np.zeros_like(X) + 0.37], -1), octaves)

def save_rgba(name, rgba, size, margin):
    im = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA")
    if im.size[0] != size: im = im.resize((size, size), Image.LANCZOS)
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=84, method=6)
    manifest[name] = margin
    print(name, size, os.path.getsize(os.path.join(OUT, f"{name}.webp")) // 1024, "KB")

# ---------------- the Milky Way, seen from above ----------------
def milky_way(size=1024):
    U = 880 / size
    lin = (np.arange(size) + 0.5) * U - 440
    X, Y = np.meshgrid(lin, lin)           # screen units, y down; galactic centre at 0,0; Sun at (0, 216.7)
    r = np.hypot(X, Y) + 1e-6; phi = np.arctan2(Y, X)
    k, r0 = math.tan(math.radians(16)), 40.0
    nz = Noise(77)
    clump = np.clip(0.25 + 1.3 * noise2(nz, X, Y, 1 / 30, 6), 0.05, 1.6)
    env = np.clip((r - 25) / 40, 0, 1) * np.exp(-r / 210) * np.clip((440 - r) / 60, 0, 1)
    arms = np.zeros_like(r); dust = np.ones_like(r)
    t_sun = math.degrees(math.log(185 / r0) / k)
    for off, amp in [(0, .75), (90, 1.0), (180, .7), (270, 1.0)]:   # Sagittarius, Perseus, Norma, Scutum–Centaurus
        theta_deg = 90 + t_sun + off   # Sagittarius, Perseus, Norma, Scutum–Centaurus
        ang = math.radians(theta_deg) - np.log(r / r0) / k
        d = (phi - ang + np.pi) % (2 * np.pi) - np.pi            # signed angular offset to the nearest winding
        s = d * r; w = 12 + 0.11 * r
        arms += amp * np.exp(-(s / w) ** 2) * env * clump
        lane = np.exp(-((s + 0.75 * w) / (0.32 * w)) ** 2) * env    # dust lane on the inner edge
        dust *= 1 - 0.55 * amp * lane * np.clip(clump, 0, 1.2)
    # the Orion Spur, the short arm our Sun lives in
    wphi = np.exp(-((phi - math.pi / 2 - 0.05) / 0.42) ** 2)
    r_sp = 216.7 * np.exp(-0.32 * (phi - math.pi / 2))
    arms += 0.55 * np.exp(-((r - r_sp) / 6.5) ** 2) * wphi * clump
    ax = np.array([-0.45, 0.89]); ax /= np.linalg.norm(ax)
    u = X * ax[0] + Y * ax[1]; v = -X * ax[1] + Y * ax[0]
    bar = 0.95 * np.exp(-(u / 105) ** 2 - (v / 28) ** 2)
    bulge = 1.4 * np.exp(-(r / 42) ** 2)
    disk = 0.4 * np.exp(-r / 170) * np.clip((440 - r) / 60, 0, 1) * (0.6 + 0.5 * clump)
    I = (arms * dust + bar + bulge + disk)
    warm = np.array([1.0, 0.86, 0.66]); cool = np.array([0.74, 0.82, 1.0])
    mix = np.clip((bar + bulge) / (arms + bar + bulge + 1e-3), 0, 1)[..., None]
    col = warm * mix + cool * (1 - mix)
    lum = 1 - np.exp(-I * 2.1)
    rgb = col * lum[..., None]
    rng = np.random.default_rng(3)
    # pink star-forming regions dotted along the arms, and a sprinkle of bright stars
    pts = rng.random((9000, 2)) * 880 - 440
    pr = np.hypot(pts[:, 0], pts[:, 1])
    pj = ((pts[:, 0] + 440) / U).astype(int).clip(0, size - 1); pi = ((pts[:, 1] + 440) / U).astype(int).clip(0, size - 1)
    weight = arms[pi, pj]
    for (x, y), wv in zip(pts[:1400], weight[:1400]):
        if rng.random() < wv * 0.55:
            cx, cy = int((x + 440) / U), int((y + 440) / U); rad = rng.uniform(1.2, 3.2)
            y0, y1, x0, x1 = max(cy - 6, 0), min(cy + 7, size), max(cx - 6, 0), min(cx + 7, size)
            yy, xx = np.mgrid[y0:y1, x0:x1]; g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / rad ** 2)[..., None]
            rgb[y0:y1, x0:x1] += g * np.array([0.95, 0.42, 0.62]) * 0.55
    for (x, y), wv in zip(pts[1400:], weight[1400:]):
        if rng.random() < 0.08 + wv * 0.35:
            cx, cy = int((x + 440) / U), int((y + 440) / U)
            if 0 <= cx < size and 0 <= cy < size: rgb[cy, cx] += np.array([0.9, 0.92, 1.0]) * rng.uniform(.25, .8)
    alpha = np.clip(lum * 1.5, 0, 1) * np.clip((440 - r) / 40, 0, 1)
    rgb = np.clip(rgb, 0, 1)
    save_rgba("milkyway", np.concatenate([rgb / np.maximum(alpha[..., None], 1e-3) * np.minimum(alpha[..., None] * 3, 1), alpha[..., None]], -1), size, 1.0)

# ---------------- stars ----------------
def star_fn(stops, freq, contrast, seed):
    nz = Noise(seed)
    def fn(lat, lon, B, N):
        z = np.clip(N[..., 2], 0, 1)
        g = nz.fbm(B * freq, 5)
        base = palette(z ** 0.6, stops)
        return np.clip(base * (1 + contrast * (g - 0.5))[..., None], 0, 1)
    return fn
STARS = {
    "betelgeuse": ([(0, (150, 30, 10)), (0.5, (230, 90, 40)), (1, (255, 170, 110))], 1.6, 0.9, (255, 110, 60, 0.9), 0.14),
    "antares":    ([(0, (160, 40, 14)), (0.5, (236, 104, 46)), (1, (255, 184, 120))], 1.8, 0.8, (255, 120, 70, 0.9), 0.14),
    "proxima":    ([(0, (140, 30, 20)), (0.5, (220, 80, 50)), (1, (255, 150, 110))], 4, 0.4, (255, 90, 60, 0.8), 0.1),
    "polaris":    ([(0, (220, 170, 90)), (0.5, (255, 226, 160)), (1, (255, 248, 222))], 5, 0.25, (255, 230, 170, 0.85), 0.12),
    "sirius":     ([(0, (170, 196, 255)), (0.5, (226, 236, 255)), (1, (255, 255, 255))], 6, 0.15, (190, 215, 255, 0.95), 0.16),
    "vega":       ([(0, (150, 180, 255)), (0.5, (214, 228, 255)), (1, (252, 253, 255))], 6, 0.15, (180, 205, 255, 0.95), 0.15),
    "rigel":      ([(0, (110, 150, 255)), (0.5, (180, 205, 255)), (1, (240, 246, 255))], 6, 0.15, (150, 185, 255, 1.0), 0.18),
}
for name, (stops, freq, con, atm, w) in ([] if os.environ.get("SKIP_STARS") else STARS.items()):
    render(name, 288, star_fn(stops, freq, con, hash(name) % 1000), margin=1.6, limb=0.35, atm=atm, atm_w=w, obs=0,
           sx=1.12 if name == "vega" else 1.0)

# ---------------- 2D objects: nebulae, cluster, black hole, galaxies ----------------
def canvas(size):
    lin = (np.arange(size) + 0.5) / size * 2 - 1
    return np.meshgrid(lin, lin)

def orion_nebula(size=384):
    X, Y = canvas(size); nz = Noise(81)
    wx = X + 0.25 * noise2(nz, X, Y, 2.5, 3); wy = Y + 0.25 * noise2(nz, X + 3, Y, 2.5, 3)
    r = np.hypot(wx * 1.1, wy)
    gas = np.clip(noise2(nz, wx, wy, 3, 6) * 1.3 - 0.1, 0, 1) * np.exp(-(r / 0.62) ** 2)
    core = np.exp(-((X + 0.05) ** 2 + (Y + 0.02) ** 2) / 0.02)
    lanes = np.clip(1 - 0.7 * np.clip(noise2(nz, X + 5, Y, 4, 4) - 0.55, 0, 1) * 3, 0.25, 1)
    teal = np.exp(-((X + 0.05) ** 2 + (Y + 0.02) ** 2) / 0.12)
    rgb = gas[..., None] * np.array([0.98, 0.38, 0.5]) * 1.3 + (gas * teal)[..., None] * np.array([0.2, 0.55, 0.6]) + core[..., None] * np.array([0.8, 0.95, 1.0])
    rgb *= lanes[..., None]
    a = np.clip((gas * 1.2 + core) * lanes, 0, 1)
    stars = np.zeros_like(X); rng = np.random.default_rng(1)
    for _ in range(4): cx, cy = rng.normal(-0.05, .03), rng.normal(-0.02, .03); stars += np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / 0.0004)
    rgb += stars[..., None]; a = np.clip(a + stars, 0, 1)
    save_rgba("orionneb", np.concatenate([np.clip(rgb, 0, 1), a[..., None]], -1), size, 1.0)

def pillars(size=384):
    X, Y = canvas(size); nz = Noise(82)
    haze = np.clip(noise2(nz, X, Y, 2.0, 5) * 1.5 - 0.1, 0, 1) * np.exp(-(np.hypot(X, Y) / 0.95) ** 4)
    sky = np.array([0.3, 0.62, 0.55]) * (1 - (Y[..., None] + 1) / 2) + np.array([0.85, 0.66, 0.38]) * ((Y[..., None] + 1) / 2)
    rgb = haze[..., None] * sky; a = haze * 0.85
    ero = noise2(nz, X, Y, 7, 5) - 0.5
    mask = np.zeros_like(X); lit = np.zeros_like(X)
    for cx, top, w in [(-0.4, -0.62, 0.15), (0.05, -0.18, 0.12), (0.42, 0.05, 0.1)]:   # three pillars, tallest on the left
        t = np.clip((Y - top) / (1.0 - top), 0, 1)
        lean = cx + 0.18 * (Y - top) * (1 if cx < 0 else -0.4)
        width = w * (0.6 + 0.7 * t) * (1 + 0.6 * ero)
        side = (width - np.abs(X - lean)) / 0.025
        cap = (Y - top + 0.06 * ero - 0.04 * np.cos((X - lean) / max(w, .05) * 1.4)) / 0.025
        m = 1 / (1 + np.exp(-side)) * 1 / (1 + np.exp(-cap))
        mask = np.maximum(mask, m)
        lit = np.maximum(lit, m * np.exp(-((Y - top) / 0.12) ** 2))
    body = np.array([0.36, 0.22, 0.13]) * (0.75 + 0.7 * (ero[..., None] + 0.5)) * (0.6 + 0.6 * (1 - (Y[..., None] + 1) / 2))
    rim = np.clip(mask - Image_blur(mask, 3), 0, 1) * 3
    col = body + lit[..., None] * np.array([0.9, 0.7, 0.4]) + rim[..., None] * np.array([1.0, 0.86, 0.6])
    rgb = rgb * (1 - mask[..., None]) + col * mask[..., None]
    a = np.clip(np.maximum(a, mask * 0.98), 0, 1)
    rng = np.random.default_rng(5)
    for _ in range(25):
        x, y = rng.uniform(-.9, .9, 2); st = np.exp(-((X - x) ** 2 + (Y - y) ** 2) / 0.00012) * (1 - mask)
        rgb += st[..., None]; a = np.clip(a + st, 0, 1)
    save_rgba("eagle", np.concatenate([np.clip(rgb, 0, 1), a[..., None]], -1), size, 1.0)

def Image_blur(arr, rad):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad))
    return np.asarray(im, dtype=np.float32) / 255

def crab(size=384):
    X, Y = canvas(size); nz = Noise(83)
    e = np.hypot(X / 0.85, Y / 0.62)
    glow = np.exp(-(e / 0.55) ** 2)
    fil = np.zeros_like(X)
    for kk, f in enumerate([3.0, 5.0, 8.0]):   # thin, tangled filaments
        n = noise2(nz, X + kk * 1.7, Y - kk, f, 4)
        fil += np.exp(-((n - 0.5) / 0.025) ** 2) * (0.9 - 0.2 * kk)
    fil = np.clip(fil, 0, 1.2) * np.clip(1.1 - e, 0, 1) * 1.3
    rgb = glow[..., None] * np.array([0.55, 0.7, 1.0]) * 0.8 + fil[..., None] * np.array([1.0, 0.45, 0.2])
    a = np.clip(glow * 0.75 + fil, 0, 1) * (e < 1.05)
    star = np.exp(-(X ** 2 + Y ** 2) / 0.0006); rgb += star[..., None]; a = np.clip(a + star, 0, 1)
    save_rgba("crab", np.concatenate([np.clip(rgb, 0, 1), a[..., None]], -1), size, 1.0)

def pleiades(size=320):
    X, Y = canvas(size); nz = Noise(84)
    haze = np.clip(noise2(nz, X * 1.5 + 0.3 * Y, Y, 3, 5) - 0.35, 0, 1) * np.exp(-(np.hypot(X, Y) / 0.7) ** 2) * 1.2
    rgb = haze[..., None] * np.array([0.45, 0.6, 1.0]); a = haze * 0.8
    for x, y, m in [(-0.05, -0.05, 1), (0.32, 0.08, .8), (-0.35, 0.18, .75), (0.12, -0.32, .7), (-0.18, -0.4, .6), (0.45, -0.22, .55), (-0.5, -0.1, .5), (0.2, 0.38, .45), (-0.05, 0.3, .4)]:
        d2 = (X - x) ** 2 + (Y - y) ** 2
        core = np.exp(-d2 / (0.0012 * m)) + 0.35 * np.exp(-d2 / (0.012 * m))
        spike = (np.exp(-((X - x) / 0.006) ** 2) * np.exp(-((Y - y) / (0.18 * m)) ** 2) + np.exp(-((Y - y) / 0.006) ** 2) * np.exp(-((X - x) / (0.18 * m)) ** 2)) * 0.5
        s = (core + spike) * m
        rgb += s[..., None] * np.array([0.85, 0.92, 1.0]); a = np.clip(a + s, 0, 1)
    save_rgba("pleiades", np.concatenate([np.clip(rgb, 0, 1), a[..., None]], -1), size, 1.0)

def black_hole(size=320):
    X, Y = canvas(size); r = np.hypot(X, Y); th = np.arctan2(Y, X)
    ring = np.exp(-((r - 0.62) / 0.13) ** 2) * (0.55 + 0.45 * np.cos(th - 1.9)) ** 1.5   # brighter on one side, like the EHT image
    rgb = ring[..., None] * np.array([1.0, 0.62, 0.22]) + (ring ** 3)[..., None] * np.array([0.3, 0.3, 0.2])
    hole = r < 0.42
    a = np.clip(ring * 1.4, 0, 1); a = np.where(hole, 1, a); rgb = np.where(hole[..., None], 0, rgb)
    a = np.where((r < 0.95) & ~hole, np.maximum(a, 0.55 * np.exp(-((r - 0.6) / 0.35) ** 2)), a)
    save_rgba("sgra", np.concatenate([np.clip(rgb, 0, 1), np.clip(a, 0, 1)[..., None]], -1), size, 1.0)

def galaxy_sprite(name, size, incl, rot, irregular=False, seed=90):
    X, Y = canvas(size); nz = Noise(seed)
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    u = X * c + Y * s; v = (-X * s + Y * c) / incl
    r = np.hypot(u, v) + 1e-6; ph = np.arctan2(v, u)
    if irregular:
        body = np.exp(-(np.hypot(u / 1.0, v / 0.7) / 0.5) ** 2) * (0.5 + 0.9 * noise2(nz, X, Y, 4, 5))
        bar = np.exp(-(u / 0.35) ** 2 - (v / 0.1) ** 2)
        I = (body + 0.7 * bar) * 0.45; col = np.array([0.82, 0.86, 1.0])
        rgb = I[..., None] * col * (0.7 + 0.6 * noise2(nz, X + 2, Y, 9, 3))[..., None]
        for _ in range(1):
            d2 = (X - 0.25) ** 2 + (Y + 0.12) ** 2; t = np.exp(-d2 / 0.004); rgb += t[..., None] * np.array([1, .45, .6])   # the Tarantula Nebula
    else:
        arms = 0.5 + 0.5 * np.cos(2 * (ph - np.log(r / 0.08) / 0.32))
        disk = np.exp(-r / 0.32) * (0.4 + 0.8 * arms * (0.6 + 0.6 * noise2(nz, u, v, 6, 4)))
        lanes = 1 - 0.5 * np.exp(-((arms - 0.15) / 0.12) ** 2) * (r > 0.12) * (r < 0.85)
        core = 1.5 * np.exp(-(r / 0.09) ** 2)
        I = disk * lanes + core
        mix = np.clip(core / (I + 1e-3), 0, 1)[..., None]
        rgb = I[..., None] * (np.array([1, .88, .7]) * mix + np.array([.8, .86, 1]) * (1 - mix))
    lum = 1 - np.exp(-I * 2.2)
    a = np.clip(lum * 1.4, 0, 1) * np.clip((1 - r) / 0.15, 0, 1)
    rgb = (1 - np.exp(-rgb * (1.4 if irregular else 2.5))) / np.maximum(lum[..., None], 1e-3) * np.minimum(lum[..., None] * 2, 1)
    a = np.clip(lum * 2.2, 0, 1) * np.clip((1 - r) / 0.15, 0, 1)
    save_rgba(name, np.concatenate([np.clip(rgb, 0, 1), a[..., None]], -1), size, 1.0)

milky_way()
orion_nebula(); pillars(); crab(); pleiades(); black_hole()
galaxy_sprite("andromeda", 320, 0.32, -38)
galaxy_sprite("lmc", 288, 0.8, 20, irregular=True, seed=91)
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=0)
