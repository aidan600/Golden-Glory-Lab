"""Generate the bundled calculator icon PNGs (dev-only helper).

Each icon is drawn at 8x and downsampled with LANCZOS so the shipped 14-28 px
assets keep smooth, consistent line weight.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "golden_glory_lab"
    / "desktop"
    / "icons"
)

SUPERSAMPLE = 8
CANVAS = 144  # 18 px * 8
GOLD = (176, 138, 46, 255)
MUTED = (110, 102, 89, 255)
WHITE = (255, 255, 255, 255)
STROKE = 12
THIN = 8


def new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image)


def outline(draw: ImageDraw.ImageDraw, points, colour, width=STROKE) -> None:
    draw.line([*points, points[0]], fill=colour, width=width, joint="curve")


def save(name: str, image: Image.Image, size: int = 18) -> None:
    resized = image.resize((size, size), Image.LANCZOS)
    path = OUT / f"{name}.png"
    resized.save(path, "PNG")
    print(f"{path.name:20s} {size:>3}px {path.stat().st_size:>5} bytes")


def helmet(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.arc([24, 16, 120, 112], 180, 360, fill=colour, width=STROKE)
    d.line([24, 64, 30, 106], fill=colour, width=STROKE)
    d.line([120, 64, 114, 106], fill=colour, width=STROKE)
    d.line([30, 106, 114, 106], fill=colour, width=STROKE)
    d.rounded_rectangle([42, 56, 102, 76], radius=8, fill=colour)
    d.line([72, 76, 72, 100], fill=colour, width=THIN)
    return image


def body_armour(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    outline(
        d,
        [(72, 18), (112, 34), (116, 82), (94, 114), (72, 126), (50, 114), (28, 82), (32, 34)],
        colour,
    )
    d.line([72, 46, 72, 108], fill=colour, width=THIN)
    return image


def gloves(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.rounded_rectangle([48, 14, 112, 92], radius=26, outline=colour, width=STROKE)
    d.rounded_rectangle([16, 52, 52, 86], radius=16, outline=colour, width=STROKE)
    d.rounded_rectangle([44, 94, 116, 128], radius=10, outline=colour, width=STROKE)
    return image


def boots(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    outline(
        d,
        [(40, 20), (80, 20), (80, 82), (114, 96), (118, 122), (40, 122)],
        colour,
    )
    d.line([40, 96, 80, 96], fill=colour, width=THIN)
    return image


def main_hand(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.polygon([(52, 88), (66, 102), (122, 26)], fill=colour)
    d.line([42, 80, 82, 120], fill=colour, width=STROKE)
    d.line([54, 104, 32, 126], fill=colour, width=STROKE)
    return image


def off_hand(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    outline(
        d,
        [(72, 18), (118, 34), (112, 88), (72, 126), (32, 88), (26, 34)],
        colour,
    )
    d.line([72, 44, 72, 104], fill=colour, width=THIN)
    d.line([44, 66, 100, 66], fill=colour, width=THIN)
    return image


def amulet(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.arc([18, 6, 126, 114], 205, 335, fill=colour, width=STROKE)
    outline(d, [(72, 62), (102, 96), (72, 132), (42, 96)], colour)
    return image


def ring(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.ellipse([28, 44, 116, 126], outline=colour, width=STROKE)
    outline(d, [(72, 12), (92, 34), (72, 56), (52, 34)], colour, THIN)
    return image


def belt(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.rounded_rectangle([14, 54, 130, 92], radius=12, outline=colour, width=STROKE)
    d.rounded_rectangle([54, 40, 90, 106], radius=10, outline=colour, width=STROKE)
    d.line([72, 58, 72, 88], fill=colour, width=THIN)
    return image


def passive_tree(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.line([72, 126, 72, 76], fill=colour, width=STROKE)
    d.line([72, 92, 38, 56], fill=colour, width=THIN)
    d.line([72, 92, 106, 56], fill=colour, width=THIN)
    d.ellipse([54, 24, 90, 60], outline=colour, width=STROKE)
    d.ellipse([16, 30, 46, 60], outline=colour, width=THIN)
    d.ellipse([98, 30, 128, 60], outline=colour, width=THIN)
    d.ellipse([64, 34, 80, 50], fill=colour)
    return image


def other(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.ellipse([16, 16, 128, 128], outline=colour, width=STROKE)
    for x in (48, 72, 96):
        d.ellipse([x - 8, 64, x + 8, 80], fill=colour)
    return image


def jewel(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    outline(d, [(44, 34), (100, 34), (128, 66), (72, 128), (16, 66)], colour)
    d.line([16, 66, 128, 66], fill=colour, width=THIN)
    d.line([44, 34, 58, 66], fill=colour, width=THIN)
    d.line([100, 34, 86, 66], fill=colour, width=THIN)
    d.line([58, 66, 72, 128], fill=colour, width=THIN)
    d.line([86, 66, 72, 128], fill=colour, width=THIN)
    return image


def sun(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.ellipse([48, 48, 96, 96], outline=colour, width=STROKE)
    rays = [
        (72, 12, 72, 34),
        (72, 110, 72, 132),
        (12, 72, 34, 72),
        (110, 72, 132, 72),
        (30, 30, 46, 46),
        (98, 98, 114, 114),
        (98, 46, 114, 30),
        (30, 114, 46, 98),
    ]
    for x0, y0, x1, y1 in rays:
        d.line([x0, y0, x1, y1], fill=colour, width=STROKE)
    return image


def calculator(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.rounded_rectangle([28, 16, 116, 128], radius=14, outline=colour, width=STROKE)
    d.rounded_rectangle([46, 34, 98, 58], radius=6, outline=colour, width=THIN)
    for row in (78, 104):
        for col in (52, 72, 92):
            d.ellipse([col - 7, row - 7, col + 7, row + 7], fill=colour)
    return image


def plus(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.line([72, 30, 72, 114], fill=colour, width=STROKE + 2)
    d.line([30, 72, 114, 72], fill=colour, width=STROKE + 2)
    return image


def check(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.line([28, 76, 60, 106, 118, 38], fill=colour, width=STROKE + 3, joint="curve")
    return image


def refresh(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.arc([26, 26, 118, 118], 60, 350, fill=colour, width=STROKE)
    outline(d, [(96, 8), (120, 34), (86, 40)], colour, THIN)
    return image


def info(colour=GOLD) -> Image.Image:
    image, d = new_canvas()
    d.ellipse([16, 16, 128, 128], outline=colour, width=STROKE)
    d.ellipse([64, 40, 80, 56], fill=colour)
    d.line([72, 68, 72, 106], fill=colour, width=STROKE)
    return image


def _indicator(fill, border, tick) -> Image.Image:
    """24x16 indicator: a 16 px box on the left, transparent gap on the right."""

    image = Image.new("RGBA", (192, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle([4, 4, 124, 124], radius=20, fill=fill, outline=border, width=10)
    if tick is not None:
        d.line([32, 66, 56, 92, 98, 38], fill=tick, width=16, joint="curve")
    return image


def indicators() -> None:
    off = _indicator((255, 255, 255, 255), (201, 194, 180, 255), None)
    on = _indicator(GOLD, GOLD, WHITE)
    for name, image in (("check_off", off), ("check_on", on)):
        resized = image.resize((24, 16), Image.LANCZOS)
        path = OUT / f"{name}.png"
        resized.save(path, "PNG")
        print(f"{path.name:20s}  24x16 {path.stat().st_size:>5} bytes")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    slots = {
        "helmet": helmet,
        "body_armour": body_armour,
        "gloves": gloves,
        "boots": boots,
        "main_hand": main_hand,
        "off_hand": off_hand,
        "amulet": amulet,
        "ring": ring,
        "belt": belt,
        "passive_tree": passive_tree,
        "other": other,
        "jewel": jewel,
    }
    for name, factory in slots.items():
        save(name, factory(), 18)

    save("sun", sun(), 18)
    save("sun_large", sun(), 28)
    save("calculator", calculator(), 18)
    save("plus", plus(GOLD), 14)
    save("check_light", check(WHITE), 14)
    save("refresh", refresh(MUTED), 14)
    save("info", info(MUTED), 14)
    indicators()

    print(f"wrote {len(list(OUT.glob('*.png')))} icons to {OUT}")


if __name__ == "__main__":
    main()
