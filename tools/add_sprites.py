import json, math, os, numpy as np
from PIL import Image
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.py")).read()
exec(src.split("# ---------- build every sprite ----------")[0])
manifest.update(json.load(open(os.path.join(OUT, "manifest.json"))))

def callisto_extra(rgb, lat, lon, B, nz):
    r = np.random.default_rng(7)
    for _ in range(140):  # bright fresh crater dots on a dark surface
        c = r.normal(size=3); c /= np.linalg.norm(c); rad = 0.008 + 0.03 * r.random() ** 2
        d = np.arccos(np.clip(B @ c, -1, 1)); s = np.exp(-((d / rad) ** 2))[..., None]
        rgb = rgb * (1 - 0.7 * s) + np.array([0.86, 0.84, 0.8]) * 0.7 * s
    return rgb

def mimas_extra(rgb, lat, lon, B, nz):  # Herschel: one crater a third of the moon's width, with a central peak
    c = np.array([0.45, 0.15, 0.88]); c /= np.linalg.norm(c)
    d = np.arccos(np.clip(B @ c, -1, 1)); t = d / 0.36
    g = B - np.outer((B @ c).ravel(), c).reshape(B.shape); side = (g @ LIGHT) / (np.linalg.norm(g, axis=-1) + 1e-6)
    m = np.where(t < 1, 0.82 - 0.22 * side * t, 1) + 0.25 * np.exp(-((t - 1) / 0.12) ** 2) * (0.6 + 0.4 * side) + 0.35 * np.exp(-((t) / 0.12) ** 2)
    return rgb * m[..., None]

def miranda_extra(rgb, lat, lon, B, nz):  # patchwork "coronae": banded grooves in a few regions
    for k, c in enumerate([np.array([0.2, -0.5, 0.84]), np.array([-0.6, 0.2, 0.77]), np.array([0.7, 0.4, 0.6])]):
        c = c / np.linalg.norm(c); d = np.arccos(np.clip(B @ c, -1, 1))
        inside = (d < 0.55 + 0.08 * np.sin(np.arctan2(B[..., 1], B[..., 0]) * 3 + k))[..., None]
        bands = 0.9 + 0.1 * np.sin(d * (90 + 20 * k) + nz.fbm(B * 4 + k, 3) * 9)[..., None]
        rgb = np.where(inside, rgb * bands * (0.92 if k % 2 else 1.05), rgb)
    return rgb

def top_shape(th):  # Bennu is shaped like a spinning top: a diamond outline with a soft equator ridge
    p = 1.35
    return 1 / (np.abs(np.cos(th)) ** p + np.abs(np.sin(th) * 1.08) ** p) ** (1 / p) * (1 + 0.03 * np.sin(7 * th))

def bennu_extra(rgb, lat, lon, B, nz):
    boulders = (nz.fbm(B * 14, 2) > 0.62)[..., None]
    return np.where(boulders, rgb * 1.35, rgb)

render("callisto", 320, proc(34, [(0, (52, 46, 40)), (0.6, (82, 74, 64)), (1, (104, 96, 86))], 2.5, 5, (40, 0.02, 0.12, 0.7), callisto_extra), limb=0.3)
render("mimas", 256, proc(35, [(0, (150, 150, 154)), (1, (206, 206, 210))], 3, 5, (60, 0.02, 0.12, 0.9), mimas_extra), limb=0.25)
render("miranda", 256, proc(36, [(0, (120, 124, 128)), (1, (190, 194, 198))], 3, 4, (20, 0.02, 0.08, 0.6), miranda_extra), limb=0.25, obs=-30)
render("bennu", 224, proc(37, [(0, (34, 32, 30)), (0.6, (58, 54, 50)), (1, (82, 78, 72))], 4, 5, (8, 0.04, 0.15, 0.6), bennu_extra), shape=top_shape, margin=1.4, limb=0.2)
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=0)
