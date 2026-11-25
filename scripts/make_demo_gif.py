"""Render assets/demo.gif: a terminal replay of four offline commands.

Every command is run for real, from the repository root, and its standard
output is drawn as printed. Nothing calls the API: the LLM results come from
the committed run in results/eval_results.json.

Needs Pillow (not used by the core or the tests, so CI does not install it):

    pip install pillow
    python scripts/make_demo_gif.py
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "demo.gif"

# (comment shown above the command, command run with the shell)
STEPS = [
    ("1. The test suite: none of the tests calls the API",
     "python -m unittest discover -s tests 2>&1 | tail -3"),
    ("2. The rules on a ticket that discloses a password: escalated, automation blocked",
     "python src/prototype.py --ticket TCK-009 | sed -n '4,16p'"),
    ("3. The rules alone on the 30 labelled tickets: 4 of 21 risky tickets would be automated",
     "python src/eval_set.py | tail -4"),
    ("4. Rules + LLM + guardrail, from the saved run (no API call): 0 of 21 with either prompt",
     "python src/evaluate.py --table results/eval_results.json | sed -n '1,7p' | cut -d'|' -f2,3,7,8,10"),
]

COLS, ROWS = 114, 16
FONT_SIZE = 15
PAD = 18
BG = (24, 26, 33)
FG = (220, 223, 228)
PROMPT = (110, 200, 140)
COMMENT = (130, 140, 160)
HIGHLIGHT = (240, 200, 110)

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "C:/Windows/Fonts/consola.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]


def load_font():
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, FONT_SIZE)
    sys.exit("No monospace font found; add one to FONT_PATHS.")


def run(command):
    result = subprocess.run(command, shell=True, cwd=ROOT, capture_output=True, text=True, check=False)
    lines = result.stdout.rstrip("\n").splitlines()
    wrapped = []
    for line in lines:
        while len(line) > COLS:
            wrapped.append(line[:COLS])
            line = line[COLS:]
        wrapped.append(line)
    return wrapped


class Terminal:
    def __init__(self, font):
        self.font = font
        left, top, right, bottom = font.getbbox("M")
        self.cw = font.getlength("M")
        self.ch = int((bottom - top) * 1.55) + 2
        self.size = (int(self.cw * COLS) + 2 * PAD, self.ch * ROWS + 2 * PAD)
        self.lines = []  # (text, colour)
        self.frames = []
        self.durations = []

    def push(self, text, colour=FG):
        self.lines.append((text, colour))
        self.lines = self.lines[-ROWS:]

    def snap(self, ms, cursor=False):
        image = Image.new("RGB", self.size, BG)
        draw = ImageDraw.Draw(image)
        for row, (text, colour) in enumerate(self.lines):
            y = PAD + row * self.ch
            if text.startswith("$ "):
                draw.text((PAD, y), "$", font=self.font, fill=PROMPT)
                draw.text((PAD + 2 * self.cw, y), text[2:], font=self.font, fill=colour)
            else:
                draw.text((PAD, y), text, font=self.font, fill=colour)
        if cursor and self.lines:
            row = len(self.lines) - 1
            x = PAD + self.cw * len(self.lines[-1][0])
            y = PAD + row * self.ch
            draw.rectangle([x, y + 2, x + self.cw - 2, y + self.ch - 4], fill=FG)
        self.frames.append(image)
        self.durations.append(ms)

    def type_line(self, text, colour, prefix):
        self.push(prefix, colour)
        for i in range(0, len(text), 3):
            self.lines[-1] = (prefix + text[: i + 3], colour)
            self.snap(45, cursor=True)


def main():
    terminal = Terminal(load_font())
    for index, (comment, command) in enumerate(STEPS):
        output = run(command)
        if index:
            terminal.lines = []
        terminal.type_line(comment, COMMENT, "# ")
        terminal.type_line(command, FG, "$ ")
        terminal.snap(500, cursor=True)
        for line in output:
            colour = HIGHLIGHT if "prompt v2" in line or "4/21" in line or "Automation Allowed" in line else FG
            terminal.push(line, colour)
            terminal.snap(40)
        terminal.snap(4200 if index == len(STEPS) - 1 else 3200)

    # One palette shared by every frame, built from the frames that hold longest, so the
    # highlight colour survives even in frames where it covers few pixels.
    held = [frame for frame, ms in zip(terminal.frames, terminal.durations) if ms >= 3000]
    sheet = Image.new("RGB", (terminal.size[0], terminal.size[1] * len(held)))
    for i, frame in enumerate(held):
        sheet.paste(frame, (0, i * terminal.size[1]))
    palette = sheet.quantize(colors=48, dither=Image.Dither.NONE)
    first, *rest = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in terminal.frames]
    first.save(OUT, save_all=True, append_images=rest, duration=terminal.durations, loop=0, optimize=True)
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(terminal.frames)} frames, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
