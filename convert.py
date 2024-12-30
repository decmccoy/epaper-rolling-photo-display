from PIL import Image
import os


def resize_and_pad_jpg(image, target_width, target_height):
    width, height = image.size
    aspect_ratio = width / height

    if width > height:
        new_width = target_width
        new_height = int(target_width / aspect_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * aspect_ratio)

    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    padded_image = Image.new("RGB", (target_width, target_height), (255, 255, 255))
    
    left_padding = (target_width - new_width) // 2
    top_padding = (target_height - new_height) // 2

    padded_image.paste(resized_image, (left_padding, top_padding))

    return padded_image


def jpg_to_bitmap(image):
    palette = [
        0, 0, 0,
        255, 255, 255,
        255, 0, 0,
        0, 255, 0,
        0, 0, 255,
        255, 255, 0,
        255, 128, 0
    ]
    try:
        image_palette = Image.new('P', (600, 448))
        image_palette.putpalette(palette)
        return image.quantize(palette=image_palette, dither=Image.FLOYDSTEINBERG, colors=7)
    except Exception as e:
            print(f"Error converting jpg to bitmap: {e}")


def save_as_jpg(image_path):
        try:
            with Image.open(image_path) as image:
                image.convert('RGB').save(image_path, 'JPEG')
            print(f"Converted to jpg")
        except Exception as e:
            print(f"Error converting to jpg: {e}")
