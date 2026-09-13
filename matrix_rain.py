#!/usr/bin/env python3
import argparse
import os
import random
import signal
import string
import sys

import pygame
from Xlib import display, Xatom, X

running = True


def stop_script(signum=None, frame=None):
    global running
    running = False


signal.signal(signal.SIGINT, stop_script)
signal.signal(signal.SIGTERM, stop_script)


def parse_args():
    parser = argparse.ArgumentParser(description="Matrix rain wallpaper for xwinwrap.")
    parser.add_argument("wid", help="Window ID passed by xwinwrap (hex or decimal).")
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--font-size", type=int, default=24)
    parser.add_argument("--density", type=float, default=0.65)
    parser.add_argument("--speed-min", type=float, default=4.0)
    parser.add_argument("--speed-max", type=float, default=10.0)
    parser.add_argument("--trail-min", type=int, default=7)
    parser.add_argument("--trail-max", type=int, default=55)
    parser.add_argument("--trail-spacing", type=float, default=2)
    parser.add_argument("--spacing-variance", type=float, default=0.2)
    parser.add_argument("--trail-taper", type=float, default=0.5)
    parser.add_argument("--fade-alpha", type=int, default=45)
    parser.add_argument("--charset", default=string.ascii_letters + string.digits)
    return parser.parse_args()


def clamp(value, low, high):
    return max(low, min(value, high))


def apply_window_hints():
    try:
        xdisplay = display.Display()
        window_id = pygame.display.get_wm_info()["window"]
        win = xdisplay.create_resource_object("window", window_id)

        net_wm_state = xdisplay.intern_atom("_NET_WM_STATE")
        net_wm_window_type = xdisplay.intern_atom("_NET_WM_WINDOW_TYPE")

        hints = [
            xdisplay.intern_atom("_NET_WM_STATE_SKIP_TASKBAR"),
            xdisplay.intern_atom("_NET_WM_STATE_SKIP_PAGER"),
            xdisplay.intern_atom("_NET_WM_STATE_BELOW"),
            xdisplay.intern_atom("_NET_WM_STATE_STICKY"),
        ]

        desktop_type = xdisplay.intern_atom("_NET_WM_WINDOW_TYPE_DESKTOP")

        win.change_property(net_wm_state, Xatom.ATOM, 32, hints)
        win.change_property(net_wm_window_type, Xatom.ATOM, 32, [desktop_type])
        win.configure(stack_mode=X.Below)
        xdisplay.flush()  # FIX: flush() instead of sync() — non-blocking

        return xdisplay, win

    except Exception as exc:
        print(f"Window hint warning: {exc}", file=sys.stderr)
        return None, None


def make_column(x, height, args):
    spacing_low = max(0.1, args.trail_spacing - args.spacing_variance)
    spacing_high = max(spacing_low, args.trail_spacing + args.spacing_variance)

    return {
        "x": x,
        "y": random.randint(-height, 0),
        "speed": random.uniform(args.speed_min, args.speed_max),
        "trail": random.randint(args.trail_min, args.trail_max),
        "spacing": random.uniform(spacing_low, spacing_high),
        "speed_jitter": random.uniform(0.85, 1.15),  # FIX: renamed from 'jitter' to reflect what it is
    }


def reset_column(column, height, args):
    column.update(make_column(column["x"], height, args))


def build_char_cache(font, charset, colors):
    return {
        (char, color): font.render(char, True, color)
        for color in colors
        for char in charset
    }


def main():
    args = parse_args()

    args.fps = max(1, args.fps)
    args.font_size = max(6, args.font_size)
    args.density = clamp(args.density, 0.05, 1.0)
    args.fade_alpha = int(clamp(args.fade_alpha, 0, 255))

    if args.speed_min > args.speed_max:
        args.speed_min, args.speed_max = args.speed_max, args.speed_min

    if args.trail_min > args.trail_max:
        args.trail_min, args.trail_max = args.trail_max, args.trail_min

    args.trail_min = max(1, args.trail_min)
    args.trail_max = max(args.trail_min, args.trail_max)

    # FIX: validate charset is not empty — empty charset causes IndexError in main loop
    if not args.charset:
        print("Error: --charset must not be empty.", file=sys.stderr)
        sys.exit(1)

    # FIX: SDL_WINDOWID must be a decimal integer string.
    # xwinwrap passes %WID as a hex string (e.g. '0x1e00004').
    # C atoi() used by SDL stops parsing at 'x', so hex strings produce WID=0,
    # causing SDL to ignore the embedded window and open a new floating window.
    try:
        wid_decimal = str(int(args.wid, 0))  # int(x, 0) handles both 0x... and decimal
    except ValueError:
        print(f"Error: invalid window ID '{args.wid}'", file=sys.stderr)
        sys.exit(1)

    os.environ["SDL_WINDOWID"] = wid_decimal
    os.environ["SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR"] = "0"
    os.environ["SDL_VIDEO_X11_WMCLASS"] = "matrix_wallpaper"

    pygame.init()

    try:
        screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
        width, height = screen.get_size()
        pygame.display.set_caption("Matrix Wallpaper")

        xdisplay, xwin = apply_window_hints()

        clock = pygame.time.Clock()
        font = pygame.font.SysFont("monospace", args.font_size, bold=True)

        black = (0, 0, 0)
        head = (200, 255, 200)
        greens = [
            (0, 255, 0),
            (0, 210, 0),
            (0, 170, 0),
            (0, 120, 0),
            (0, 80, 0),
            (0, 45, 0),
        ]

        fade = pygame.Surface((width, height))
        fade.set_alpha(args.fade_alpha)
        fade.fill(black)

        char_cache = build_char_cache(font, args.charset, [head] + greens)

        columns = []
        col_count = max(1, width // args.font_size)

        for index in range(col_count):
            if random.random() < args.density:
                columns.append(make_column(index * args.font_size, height, args))

        screen.fill(black)
        pygame.display.flip()

        # Rate-limit the X11 stack_mode call — sync every N frames to avoid blocking
        frame_count = 0
        XSYNC_INTERVAL = 30  # re-stack every 30 frames (~2s at 15fps)

        # Fixed pixel gap between head char and first trail char (replaces multiplicative head_gap).
        # The old code used head_gap=1.5 multiplied into tapered_spacing at i==1,
        # which caused the i=1 gap to be LARGER than the i=2 gap — a visual discontinuity.
        HEAD_GAP_PX = args.font_size  # one character-height of extra space after the head

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    stop_script()

            # FIX: rate-limited re-stacking — only flush every XSYNC_INTERVAL frames
            if xdisplay and xwin and (frame_count % XSYNC_INTERVAL == 0):
                try:
                    xwin.configure(stack_mode=X.Below)
                    xdisplay.flush()
                except Exception:
                    pass

            frame_count += 1

            screen.blit(fade, (0, 0))

            for column in columns:
                x = column["x"]
                spacing = column["spacing"]

                for i in range(column["trail"]):
                    # FIX: additive pixel gap after head instead of multiplicative head_gap factor.
                    # Old code: head_gap=1.5 at i==1 compounded into tapered_spacing,
                    # making the i=1 gap larger than the i=2 gap (visual discontinuity).
                    tapered_spacing = spacing * (1 + i * args.trail_taper)
                    extra = HEAD_GAP_PX if i >= 1 else 0
                    y = column["y"] - (i * args.font_size * tapered_spacing + extra)

                    if 0 <= y < height:
                        char = random.choice(args.charset)
                        color = head if i == 0 else greens[min(i, len(greens) - 1)]
                        screen.blit(char_cache[(char, color)], (x, int(y)))

                column["y"] += column["speed"] * column["speed_jitter"]

                max_trail_length = (
                    column["trail"]
                    * args.font_size
                    * spacing
                    * (1 + column["trail"] * args.trail_taper)
                )

                if column["y"] > height + max_trail_length:
                    reset_column(column, height, args)

            pygame.display.update()
            clock.tick(args.fps)

    finally:
        # FIX: close X display connection to release resources
        if xdisplay:
            try:
                xdisplay.close()
            except Exception:
                pass
        pygame.quit()


if __name__ == "__main__":
    main()
