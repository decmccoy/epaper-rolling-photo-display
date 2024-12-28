from PIL import Image
from waveshare_epd import epd5in65f
import os


def resize_and_pad(image, target_width, target_height):
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


def convert_image(input_path, output_path):
    print("converting image")

    palette = [
        0, 0, 0,
        255, 255, 255,
        255, 0, 0,
        0, 255, 0,
        0, 0, 255,
        255, 255, 0,
        255, 128, 0
    ]
    image = Image.open(input_path)
    image_palette = Image.new('P', (600, 448))
    image_palette.putpalette(palette)

    resized_image = resize_and_pad(image, 600, 448)

    converted_image = resized_image.quantize(palette=image_palette, dither=Image.FLOYDSTEINBERG, colors=7)
    converted_image.save(output_path)

def load_pic_onto_screen(image_name):
    print("loading image onto screen")
    image = Image.open(image_name)
    epd = epd5in65f.EPD()

    try:
        epd.init()
        epd.Clear()
        epd.display(epd.getbuffer(image))
        print("Image displayed successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        epd.sleep()


def main():
    # For testing only
    image_path = r"C:\Users\darcy\Documents\Personal\Projects\epaper_project\test_image_3.JPG"
    output_path = r"C:\Users\darcy\Documents\Personal\Projects\epaper_project\test_image_3.bmp"
    convert_image(image_path, output_path)


if __name__ == "__main__":
    main()

