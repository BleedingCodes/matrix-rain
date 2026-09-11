# matrix-rain

Matrix-style falling character live wallpaper for Linux desktops. Runs inside
an `xwinwrap` window and stays behind all other windows — always-on animated
wallpaper with no visible app frame.

Fully configurable via CLI flags. No config files, no GUI settings panel.

---

## What It Does

- Renders falling green character columns in the Matrix style
- Runs as a live wallpaper attached to your desktop via `xwinwrap`
- Stays below all other windows using X11 window hints
- Configurable: FPS, font size, column density, speed, trail length, fade, character set
- Pre-renders a character cache at startup for smooth frame rates
- Handles `SIGINT` (Ctrl+C) and `SIGTERM` (systemd stop) cleanly

---

## Requirements

- Linux with X11 (not Wayland)
- Python 3.11+
- `xwinwrap` — embeds the script window into the desktop layer
- `pygame` — rendering
- `python-xlib` — X11 window control

---

## Installation

**1. Install xwinwrap**

`xwinwrap` is not in most package managers. Build it from source:

```bash
sudo apt install xorg-dev build-essential
git clone https://github.com/ujjwal96/xwinwrap.git
cd xwinwrap
make
sudo cp xwinwrap /usr/local/bin/
```

**2. Install Python dependencies**

```bash
pip install pygame python-xlib
```

**3. Clone this repo**

```bash
git clone https://github.com/BleedingCodes/matrix-rain.git
cd matrix-rain
```

---

## Usage

### Run as live wallpaper

```bash
xwinwrap -fs -fdt -ni -b -nf -ov -s -- python3 /path/to/matrix_rain.py %WID
```

This runs the script fullscreen, attached to your desktop, behind all windows.

### With options

```bash
xwinwrap -fs -fdt -ni -b -nf -ov -s -- python3 /path/to/matrix_rain.py %WID \
  --fps 20 \
  --font-size 20 \
  --density 0.8 \
  --speed-min 5 \
  --speed-max 12 \
  --trail-min 10 \
  --trail-max 40 \
  --fade-alpha 35
```

### Stop it

```bash
pkill -f matrix_rain.py
```

Or `Ctrl+C` if running in foreground.

---

## All Options

| Flag | Default | Description |
|---|---|---|
| `--fps` | `15` | Frame rate |
| `--font-size` | `24` | Character size in pixels |
| `--density` | `0.65` | Fraction of columns active (0.05–1.0) |
| `--speed-min` | `4.0` | Minimum column fall speed |
| `--speed-max` | `10.0` | Maximum column fall speed |
| `--trail-min` | `7` | Minimum trail length in characters |
| `--trail-max` | `55` | Maximum trail length in characters |
| `--trail-spacing` | `2.0` | Base spacing between trail characters |
| `--spacing-variance` | `0.2` | Random variance added to spacing |
| `--trail-taper` | `0.5` | How much trail stretches toward the tail |
| `--fade-alpha` | `45` | Fade overlay strength (0 = no fade, 255 = instant clear) |
| `--charset` | ASCII letters + digits | Characters to use in the rain |

---

## Run as a systemd Service (Optional)

To start the wallpaper automatically on login, create a user service:

**`~/.config/systemd/user/matrix-rain.service`**

```ini
[Unit]
Description=Matrix Rain Live Wallpaper
After=graphical-session.target

[Service]
Type=simple
Environment=DISPLAY=:0
ExecStart=xwinwrap -fs -fdt -ni -b -nf -ov -s -- python3 /path/to/matrix_rain.py %WID --fps 15 --density 0.7
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical-session.target
```

Enable it:

```bash
systemctl --user daemon-reload
systemctl --user enable matrix-rain
systemctl --user start matrix-rain
```

Stop it:

```bash
systemctl --user stop matrix-rain
```

---

## How It Works

1. `xwinwrap` creates a window covering the desktop and passes its window ID as `%WID`
2. The script reads `%WID` and tells SDL to render into that window via `SDL_WINDOWID`
3. X11 window hints (`_NET_WM_STATE_BELOW`, `_NET_WM_WINDOW_TYPE_DESKTOP`) keep it behind everything
4. Each column is a dict with independent speed, trail length, and spacing — randomized at creation
5. A character surface cache is built at startup so rendering never calls `font.render()` per frame
6. A black fade surface with configurable alpha is blitted each frame to create the trail decay effect
7. `SIGINT` and `SIGTERM` both set a global flag that exits the main loop cleanly

---

## Built by MainbyteLabs

Python tooling for electronics labs, hardware shops, and Linux-based tech teams.

[MainbyteLabs](https://github.com/MR-MainbyteLabs) ·
[LinkedIn](https://linkedin.com/in/michael-rivera-c0ding) ·
mr.mainbytelabs@gmail.com

---

## License

MIT License

Copyright (c) 2026 Michael Rivera

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
