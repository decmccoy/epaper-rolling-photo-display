from PIL import Image
import os
import zipfile
from pillow_heif import register_heif_opener


def unzip_file(zip_file_path, extract_to):
    """
    Unzips a zip file to the specified directory.

    Parameters:
    - zip_file_path (str): The path to the zip file.
    - extract_to (str): The directory where the contents should be extracted.
    """
    os.makedirs(extract_to, exist_ok=True)

    with zipfile.ZipFile(zip_file_path, 'r') as zip:
        zip.extractall(extract_to)
    print(f"Extracted all files to {extract_to}")


def resize_jpg(image_path, destination_folder, target_width, target_height):
    os.makedirs(destination_folder, exist_ok=True)
    image_name = os.path.basename(image_path).split('.')[0]
    
    with Image.open(image_path) as image:
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
        
        padded_image.save(f'{destination_folder}/{image_name}.jpg', 'JPEG')
    print(f"Saved '{image_name}' as resized jpg to '{destination_folder}'")


def jpg_to_bitmap(image_path, destination_folder):
    os.makedirs(destination_folder, exist_ok=True)
    image_name = os.path.basename(image_path).split('.')[0]
    palette = [
        0, 0, 0,
        255, 255, 255,
        255, 0, 0,
        0, 255, 0,
        0, 0, 255,
        255, 255, 0,
        255, 128, 0
    ]
    
    with Image.open(image_path) as image:
        image_palette = Image.new('P', (600, 448))
        image_palette.putpalette(palette)
        image = image.resize((600, 448))  # Resize to match the palette size
        bitmap = image.quantize(palette=image_palette, dither=Image.FLOYDSTEINBERG, colors=7)
        bitmap.save(f'{destination_folder}/{image_name}.bmp')
    print(f"Saved '{image_name}' as bitmap to '{destination_folder}'")


def save_as_jpg(image_path, destination_folder):
    register_heif_opener()
    os.makedirs(destination_folder, exist_ok=True)
    image_name = os.path.basename(image_path).split('.')[0]
    
    with Image.open(image_path) as image:
        image.convert('RGB').save(f'{destination_folder}/{image_name}.jpg', 'JPEG')
    print(f"Saved '{image_name}' as jpg to '{destination_folder}'")
            
