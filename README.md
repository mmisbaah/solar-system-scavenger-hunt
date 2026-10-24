# Solar System Scavenger Hunt

A space game for kids. Read a clue, find the planet, moon, comet or star on the map, and stamp it into your passport. It started as a paper scavenger hunt around the house and grew from there.

The whole game is one file, `index.html`. There's no build step. Open it in a browser and play, or serve the folder with anything static (GitHub Pages works).

## What's in it

- A zoomable map of the solar system, with a "real distances" mode and orbiting planets, plus a Milky Way map with nearby stars, nebulas and the black hole at the centre.
- Four missions for different ages, a Daily Challenge, a 90-second Speed Run, and a make-your-own mission for teachers.
- 14 short Space School lessons, and a "Look up tonight" page that works out what's in the sky today.
- XP, ranks, badges and a passport. Progress is saved in the browser, one profile per player.

## Folders

```
index.html   the game
img/         rendered sprites (WebP) and manifest.json, which the game reads for sprite sizes
tools/       Python scripts that rendered the sprites
tests/       browser tests (Playwright)
```

## Re-rendering the sprites

You only need this if you want to change the pictures. The scripts use numpy and Pillow, and they read planet texture maps from two npm packages, which go in `tools/pkgs/`:

```
pip install numpy pillow
cd tools
mkdir -p pkgs/gx pkgs/tg
npm pack gravityexp@0.2.0 && tar -xzf gravityexp-0.2.0.tgz -C pkgs/gx
npm pack three-globe     && tar -xzf three-globe-*.tgz   -C pkgs/tg
python render.py && python add_sprites.py && python galaxy_render.py
```

Output lands in `img/`. Bodies with no public map (Haumea, Bennu, the galaxy objects and so on) are drawn procedurally.

## Tests

```
npm install
npx playwright install chromium
npm test
```

- `gametest.mjs` plays a mission start to finish, plus a Speed Run and a Daily Challenge.
- `fit.mjs` checks that the home screen never scrolls, at seven screen sizes.
- `overlap.mjs` opens about 150 screens at several sizes and fails if any two pieces of text overlap.
- `maplbl.mjs` zooms both maps through 1,080 views and checks that no two map labels collide.

`overlap.mjs` and `maplbl.mjs` are slow, a few minutes each. Screenshots they save are git-ignored.

The sky page loads astronomy-engine from jsDelivr, so it needs a network connection.
