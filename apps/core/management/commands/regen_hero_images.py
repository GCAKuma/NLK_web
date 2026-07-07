"""Regenerate clean, premium hero-slide background art.

The original seed baked each slide's TITLE into its image, which showed as an
ugly faded duplicate behind the headline. This produces tasteful abstract
navy/cyan art with NO text, overwriting the existing hero images.

    docker compose exec web python manage.py regen_hero_images
"""
import random
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from content.models import HeroSlide

NAVY = (7, 26, 47)
SLATE = (18, 38, 63)


def hero_art(seed_index, size=(1600, 800)):
    img = Image.new("RGB", size, NAVY)
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = size

    # Solid slate wedge on the right (flat colour, no gradient)
    draw.polygon(
        [(w * 0.58, 0), (w, 0), (w, h), (w * 0.78, h)], fill=SLATE + (255,)
    )

    rnd = random.Random(seed_index + 11)
    # Scattered thin cyan rings on the right half only (keeps left clear for text)
    for _ in range(22):
        x = rnd.randint(int(w * 0.6), w)
        y = rnd.randint(0, h)
        r = rnd.randint(8, 30)
        alpha = rnd.randint(18, 60)
        draw.ellipse([x - r, y - r, x + r, y + r], outline=(0, 217, 255, alpha), width=2)

    # A couple of bold accent rings
    for cx, cy, r in [(w * 0.84, h * 0.34, 130), (w * 0.92, h * 0.72, 82)]:
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r], outline=(0, 217, 255, 95), width=3
        )

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=86)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Regenerate clean premium hero slide background images."

    def handle(self, *args, **options):
        slides = HeroSlide.objects.all()
        if not slides:
            self.stdout.write("No hero slides found. Run seed_demo first.")
            return
        for i, slide in enumerate(slides):
            slide.image.save(f"hero-{i}.jpg", hero_art(i), save=True)
            self.stdout.write(f"  regenerated hero art: {slide.title}")
        self.stdout.write(self.style.SUCCESS("Done."))
