from PIL import Image
from waveshare_epd import epd5in65f
import os


def conv_image(input_image, output_image):
    palette = [
        0, 0, 0,
        255, 255, 255,
        255, 0, 0,
        0, 255, 0,
        0, 0, 255,
        255, 255, 0,
        255, 128, 0
    ]
    img = Image.open(input_image)
    p_img = Image.new('P', (600, 448))
    p_img.putpalette(palette)
    img = img.resize((600, 448))  # Resize to match the palette size
    img = img.convert('RGB')
    conv = img.quantize(palette=p_img, dither=Image.FLOYDSTEINBERG, colors=7)
    conv.save(output_image)


def main():
    # Set the image file path
    user_name = 'darcy'
    image_name = 'test_image'
    image_file_type = 'PNG'
    image_path = f"/home/{user_name}/Documents/epaper_proj/{image_name}.{image_file_type}"
    output_path = f"/home/{user_name}/Documents/epaper_proj/{image_name}.bmp"

    if not os.path.exists(output_path):
        print("Converting Image to 7-colour bitmap")
        conv_image(image_path, output_path)

    # Open the image using Pillow
    image = Image.open(image_path)
    image = image.resize((600, 448))
    # Initialize the e-paper display
    epd = epd5in65f.EPD()

    try:
        # Initialize the display
        epd.init()

        # Clear the display
        epd.Clear()

        # Display the image on the e-paper display
        epd.display(epd.getbuffer(image))

        print("Image displayed successfully.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Sleep to allow the display to update
        epd.sleep()


if __name__ == "__main__":
    main()
