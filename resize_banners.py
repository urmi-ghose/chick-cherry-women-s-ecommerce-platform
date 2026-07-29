from PIL import Image, ImageOps
import os

# Directory containing the banner images
banner_dir = 'static/images/banners/'

# Target size for all banners
target_size = (1600, 600)

# List of banner files
banners = [
    'Brown and Orange Fashion Autumn Sale Banner.png',
    '1600w-JRiBl2QIX-w.webp',
    'Cream Brown Women Fashion Bag Medium Banner.png',
    'Brow Sunglasses on Concrete Floor Shop New Arrivals Banner .png'
]

for banner in banners:
    img_path = os.path.join(banner_dir, banner)
    if os.path.exists(img_path):
        with Image.open(img_path) as img:
            # Resize and crop to fit the target size
            resized_img = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
            resized_img.save(img_path)
            print(f"Resized {banner} to {target_size}")
    else:
        print(f"File {banner} not found")
