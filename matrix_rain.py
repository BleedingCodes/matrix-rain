#!/usr/bin/env python3  # Use system Python interpreter
import argparse  # Handle command-line arguments
import os  # Environment variables
import random  # Random numbers for column behavior
import signal  # Handle system signals (stop/restart)
import string  # Character sets
import sys  # System-level functions

import pygame  # Rendering engine
from Xlib import display, Xatom, X  # X11 window control

running = True  # Global flag to control main loop


def stop_script(signum=None, frame=None):  # Signal handler for clean shutdown
    global running
    running = False  # Stop main loop


signal.signal(signal.SIGINT, stop_script)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, stop_script)  # Handle systemd stop


def parse_args():  # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Matrix rain wallpaper for xwinwrap.")
    parser.add_argument("wid", help="Window ID passed by xwinwrap.")
    parser.add_argument("--fps", type=int, default=15)  # Frame rate
    parser.add_argument("--font-size", type=int, default=24)  # Character size
    parser.add_argument("--density", type=float, default=0.65)  # Column density
    parser.add_argument("--speed-min", type=float, default=4.0)  # Min speed
    parser.add_argument("--speed-max", type=float, default=10.0)  # Max speed
    parser.add_argument("--trail-min", type=int, default=7)  # Min trail length
    parser.add_argument("--trail-max", type=int, default=55)  # Max trail length
    parser.add_argument("--trail-spacing", type=float, default=2)  # Base spacing
    parser.add_argument("--spacing-variance", type=float, default=0.2)  # Random spacing
    parser.add_argument("--trail-taper", type=float, default=0.5)  # Trail stretch
    parser.add_argument("--fade-alpha", type=int, default=45)  # Fade strength
    parser.add_argument("--charset", default=string.ascii_letters + string.digits)  # Characters used
    return parser.parse_args()  # Return parsed args


def clamp(value, low, high):  # Clamp value to range
    return max(low, min(value, high))


def apply_window_hints():  # Set window as wallpaper
    try:
        xdisplay = display.Display()  # Connect to X server
        window_id = pygame.display.get_wm_info()["window"]  # Get window ID
        win = xdisplay.create_resource_object("window", window_id)  # Wrap window

        net_wm_state = xdisplay.intern_atom("_NET_WM_STATE")  # State atom
        net_wm_window_type = xdisplay.intern_atom("_NET_WM_WINDOW_TYPE")  # Type atom

        hints = [
            xdisplay.intern_atom("_NET_WM_STATE_SKIP_TASKBAR"),  # Hide from taskbar
            xdisplay.intern_atom("_NET_WM_STATE_SKIP_PAGER"),  # Hide from pager
            xdisplay.intern_atom("_NET_WM_STATE_BELOW"),  # Stay below windows
            xdisplay.intern_atom("_NET_WM_STATE_STICKY"),  # Stick across desktops
        ]

        desktop_type = xdisplay.intern_atom("_NET_WM_WINDOW_TYPE_DESKTOP")  # Desktop type

        win.change_property(net_wm_state, Xatom.ATOM, 32, hints)  # Apply states
        win.change_property(net_wm_window_type, Xatom.ATOM, 32, [desktop_type])  # Set type
        win.configure(stack_mode=X.Below)  # Force behind windows
        xdisplay.sync()  # Apply changes

        return xdisplay, win  # Return handles

    except Exception as exc:
        print(f"Window hint warning: {exc}", file=sys.stderr)  # Print error
        return None, None  # Fallback


def make_column(x, height, args):  # Create one rain column
    spacing_low = max(0.1, args.trail_spacing - args.spacing_variance)  # Min spacing
    spacing_high = max(spacing_low, args.trail_spacing + args.spacing_variance)  # Max spacing

    return {
        "x": x,  # Horizontal position
        "y": random.randint(-height, 0),  # Start above screen
        "speed": random.uniform(args.speed_min, args.speed_max),  # Unique speed
        "trail": random.randint(args.trail_min, args.trail_max),  # Trail length
        "spacing": random.uniform(spacing_low, spacing_high),  # Character spacing
        "jitter": random.uniform(0.85, 1.15),  # Slight randomness per frame
    }


def reset_column(column, height, args):  # Reset column after it exits screen
    column.update(make_column(column["x"], height, args))  # Replace properties


def build_char_cache(font, charset, colors):  # Pre-render characters
    return {
        (char, color): font.render(char, True, color)  # Render once
        for color in colors
        for char in charset
    }


def main():  # Main function
    args = parse_args()  # Get arguments

    args.fps = max(1, args.fps)  # Prevent zero FPS
    args.font_size = max(6, args.font_size)  # Prevent tiny fonts
    args.density = clamp(args.density, 0.05, 1.0)  # Clamp density
    args.fade_alpha = int(clamp(args.fade_alpha, 0, 255))  # Clamp fade

    if args.speed_min > args.speed_max:  # Fix reversed values
        args.speed_min, args.speed_max = args.speed_max, args.speed_min

    if args.trail_min > args.trail_max:  # Fix reversed values
        args.trail_min, args.trail_max = args.trail_max, args.trail_min

    args.trail_min = max(1, args.trail_min)  # Prevent zero trail
    args.trail_max = max(args.trail_min, args.trail_max)  # Ensure valid range

    os.environ["SDL_WINDOWID"] = args.wid  # Attach to xwinwrap window
    os.environ["SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR"] = "0"  # Avoid compositor issues
    os.environ["SDL_VIDEO_X11_WMCLASS"] = "matrix_wallpaper"  # Set window class

    pygame.init()  # Initialize pygame

    try:
        screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)  # Borderless fullscreen
        width, height = screen.get_size()  # Get dimensions
        pygame.display.set_caption("Matrix Wallpaper")  # Window title

        xdisplay, xwin = apply_window_hints()  # Apply X11 hints

        clock = pygame.time.Clock()  # FPS control
        font = pygame.font.SysFont("monospace", args.font_size, bold=True)  # Font

        black = (0, 0, 0)  # Background color
        head = (200, 255, 200)  # Bright head color
        greens = [  # Gradient colors
            (0, 255, 0),
            (0, 210, 0),
            (0, 170, 0),
            (0, 120, 0),
            (0, 80, 0),
            (0, 45, 0),
        ]

        fade = pygame.Surface((width, height))  # Fade overlay
        fade.set_alpha(args.fade_alpha)  # Transparency
        fade.fill(black)  # Fill with black

        char_cache = build_char_cache(font, args.charset, [head] + greens)  # Cache chars

        columns = []  # Store columns
        col_count = max(1, width // args.font_size)  # Number of columns

        for index in range(col_count):  # Build columns
            if random.random() < args.density:
                columns.append(make_column(index * args.font_size, height, args))

        screen.fill(black)  # Clear screen
        pygame.display.flip()  # Apply

        while running:  # Main loop
            for event in pygame.event.get():  # Handle events
                if event.type == pygame.QUIT:
                    stop_script()

            if xdisplay and xwin:  # Keep window behind others
                try:
                    xwin.configure(stack_mode=X.Below)
                    xdisplay.sync()
                except Exception:
                    pass

            screen.blit(fade, (0, 0))  # Apply fade

            for column in columns:  # Update each column
                x = column["x"]
                spacing = column["spacing"]

                for i in range(column["trail"]):  # Draw trail
                    if i == 1:
                        head_gap = 1.5
                    else:
                        head_gap = 1.0

                    tapered_spacing = spacing * (1 + i * args.trail_taper) * head_gap
                    y = column["y"] - i * args.font_size * tapered_spacing

                    if 0 <= y < height:
                        char = random.choice(args.charset)
                        color = head if i == 0 else greens[min(i, len(greens) - 1)]
                        screen.blit(char_cache[(char, color)], (x, int(y)))

                column["y"] += column["speed"] * column["jitter"]  # Move column

                max_trail_length = (
                    column["trail"]
                    * args.font_size
                    * spacing
                    * (1 + column["trail"] * args.trail_taper)
                )

                if column["y"] > height + max_trail_length:
                    reset_column(column, height, args)  # Reset when off-screen

            pygame.display.update()  # Render frame
            clock.tick(args.fps)  # Limit FPS

    finally:
        pygame.quit()  # Cleanup


if __name__ == "__main__":
    main()  # Run program
