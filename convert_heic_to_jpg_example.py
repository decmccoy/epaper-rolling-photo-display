from PIL import Image
from pillow_heif import register_heif_opener




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
    register_heif_opener()
    img = Image.open(input_image)
    p_img = Image.new('P', (600, 448))
    p_img.putpalette(palette)
    img = img.resize((600, 448))  # Resize to match the palette size
    conv = img.quantize(palette=p_img, dither=Image.FLOYDSTEINBERG, colors=7)
    conv.save(output_image)


conv_image("C:/Users/decmc/Downloads/Photos/IMG_0936.heic", "C:/Users/decmc/Downloads/final_test_1.bmp")