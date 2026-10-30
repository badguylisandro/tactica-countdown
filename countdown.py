"""TACTICA launch countdown: renders a neon banner and edits one Discord webhook message."""
import datetime as dt
import io
import json
import os
import urllib.request

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

LAUNCH = dt.datetime(2026, 11, 21, 20, 0, tzinfo=dt.timezone.utc)  # 20:00 Lisbon (WET = UTC)
TS = int(LAUNCH.timestamp())
W, H = 1200, 480
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-ExtraBold.ttf"
FONT_PATH = os.environ.get("FONT_PATH", "Poppins-ExtraBold.ttf")
STATE = "message_id.txt"

YELLOW, CYAN, PINK, GREEN = (255, 210, 63), (60, 240, 255), (255, 90, 240), (125, 240, 154)
INK = (11, 14, 26)


def font(size):
    if not os.path.exists(FONT_PATH):
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    return ImageFont.truetype(FONT_PATH, size)


def background():
    img = Image.new("RGB", (W, H), INK)
    glow = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(glow)
    d.ellipse((W / 2 - 700, H - 260, W / 2 + 700, H + 560), fill=(91, 20, 112))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(140)), 1.0)
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    for x in range(0, W, 60):
        g.line((x, 0, x, H), fill=(60, 240, 255, 26), width=2)
    for y in range(0, H, 60):
        g.line((0, y, W, y), fill=(60, 240, 255, 26), width=2)
    fade = Image.linear_gradient("L").resize((W, H))  # dark at top, light at bottom
    grid.putalpha(Image.composite(grid.getchannel("A"), Image.new("L", (W, H), 0), fade))
    img = img.convert("RGBA")
    img.alpha_composite(grid)
    return img


def glow_text(img, xy, text, size, color, stroke=8, glow=18, spacing=0):
    f = font(size)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = xy
    if spacing:
        total = sum(d.textlength(c, font=f) + spacing for c in text) - spacing
        x = x - total / 2
        for c in text:
            d.text((x, y), c, font=f, fill=color + (255,), anchor="lm")
            x += d.textlength(c, font=f) + spacing
    else:
        d.text((x, y), text, font=f, fill=color + (255,), anchor="mm")
    if glow:
        halo = layer.filter(ImageFilter.GaussianBlur(glow))
        img.alpha_composite(halo)
        img.alpha_composite(halo)
    if stroke:
        s = Image.new("RGBA", img.size, (0, 0, 0, 0))
        s.putalpha(layer.getchannel("A").filter(ImageFilter.MaxFilter(stroke // 2 * 2 + 1)))
        img.alpha_composite(Image.composite(Image.new("RGBA", img.size, INK + (255,)), s, s))
    img.alpha_composite(layer)


def box(img, x0, y0, w, h, color, number, label):
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).rounded_rectangle((x0, y0, x0 + w, y0 + h), 28, outline=color + (255,), width=10)
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), 28, fill=(14, 16, 32, 235), outline=color + (255,), width=5)
    glow_text(img, (x0 + w / 2, y0 + 82), number, 118, (255, 255, 255), stroke=0, glow=10)
    glow_text(img, (x0 + w / 2, y0 + 168), label, 24, color, stroke=0, glow=0, spacing=6)


def render(now):
    img = background()
    left = LAUNCH - now
    if left.total_seconds() > 0:
        mins = int(left.total_seconds() // 60)
        days, hours, minutes = mins // 1440, mins % 1440 // 60, mins % 60
        glow_text(img, (W / 2, 82), "TACTICA LAUNCHES IN", 64, YELLOW, spacing=6)
        glow_text(img, (W / 2, 136), "SAT 21 NOV · 20:00 LISBON", 26, CYAN, stroke=0, glow=0, spacing=8)
        bw, gap = 300, 40
        x = (W - 3 * bw - 2 * gap) / 2
        for i, (n, lab, c) in enumerate([(days, "DAYS", PINK), (hours, "HOURS", CYAN), (minutes, "MINUTES", YELLOW)]):
            box(img, x + i * (bw + gap), 172, bw, 200, c, f"{n:02d}", lab)
        glow_text(img, (W / 2, 438), "LAUNCH WEEK: EXCLUSIVE NEON CORE SKIN + NEON TAG", 22, (255, 255, 255), stroke=0, glow=0, spacing=3)
    else:
        glow_text(img, (W / 2, 150), "TACTICA", 140, YELLOW, glow=24, spacing=10)
        glow_text(img, (W / 2, 290), "IS LIVE!", 110, PINK, glow=24, spacing=8)
        glow_text(img, (W / 2, 410), "PLAY NOW ON ROBLOX", 34, CYAN, stroke=0, glow=8, spacing=8)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def content(now):
    if now < LAUNCH:
        return (f"# 🚀 TACTICA IS LAUNCHING\n"
                f"⏳ **Launch:** <t:{TS}:R>\n📅 **Your local time:** <t:{TS}:F>\n\n"
                "🎁 Play during **Launch Week (21–28 Nov)** to unlock the exclusive **Neon Core** skin + **NEON** tag!\n"
                "🔔 Grab the notification role so you don't miss the drop.")
    return "# 🟢 TACTICA IS LIVE!\nJump in now and unlock the **Neon Core** skin during Launch Week!"


def main():
    hook = os.environ["DISCORD_WEBHOOK"].strip()
    now = dt.datetime.now(dt.timezone.utc)
    png = render(now)
    payload = {"content": content(now), "allowed_mentions": {"parse": []}, "attachments": [{"id": 0, "filename": "countdown.png"}]}
    files = {"files[0]": ("countdown.png", png, "image/png")}
    data = {"payload_json": json.dumps(payload)}
    mid = open(STATE).read().strip() if os.path.exists(STATE) else ""
    if mid:
        r = requests.patch(f"{hook}/messages/{mid}", data=data, files=files, timeout=30)
        if r.status_code != 404:
            r.raise_for_status()
            print("edited", mid)
            return
    r = requests.post(f"{hook}?wait=true", data=data, files=files, timeout=30)
    r.raise_for_status()
    open(STATE, "w").write(r.json()["id"])
    print("posted", r.json()["id"])


if __name__ == "__main__":
    if os.environ.get("PREVIEW"):
        at = dt.datetime.fromisoformat(os.environ["PREVIEW"])
        open("preview.png", "wb").write(render(at))
    else:
        main()
