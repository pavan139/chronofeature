"""Fixed public Open Graph image. No birth data, caller text or external resources."""
from functools import lru_cache
from io import BytesIO


@lru_cache(maxsize=1)
def social_card():
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1200, 630), "#18152b")
    draw = ImageDraw.Draw(image)
    font = lambda size: ImageFont.load_default(size=size)
    draw.rounded_rectangle((740, 50, 1160, 580), radius=36, fill="#6443df")
    for radius in [110, 155, 205]:
        draw.ellipse((955-radius, 290-radius, 955+radius, 290+radius), outline="#b3a2f2", width=2)
    draw.ellipse((925, 260, 985, 320), fill="#d9fa89")
    draw.ellipse((801, 160, 821, 180), fill="#ffffff")
    draw.text((65, 62), "astro.", font=font(52), fill="#d9fa89")
    draw.text((65, 188), "Your charts.", font=font(73), fill="#ffffff")
    draw.text((65, 277), "Made clear.", font=font(73), fill="#ffffff")
    draw.text((68, 407), "Kundali matching  /  Birth charts", font=font(29), fill="#cac3e4")
    draw.text((68, 455), "Explained reports. Private by design.", font=font(27), fill="#cac3e4")
    draw.text((68, 551), "23 interface languages  +  PDF reports", font=font(24), fill="#d9fa89")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
