import shutil
from PIL import Image
from waveshare_epd import epd5in65f
import os
import time
import logger


debug_mode = False
parent_directory = r'/home/mom_dad/Documents/epaper_proj/'
download_folder = f"{parent_directory}downloaded_photos"
display_folder = f"{parent_directory}bitmap_photos"
downloaded_names = os.listdir(download_folder)
display_names = os.listdir(display_folder)


def copy_bitmaps_if_necessary():
    for downloaded_name in downloaded_names:
        display_bitmap_path = display_folder + '/' + downloaded_name.split('.')[0] + '.bmp'
        if not os.path.exists(display_bitmap_path):
            logger.log(debug_mode, "Copying bitmap to display folder")
            shutil.copyfile(download_folder + '/' + downloaded_name, display_bitmap_path)


def delete_bitmaps_if_necessary():
    for display_name in display_names:
        for downloaded_name in downloaded_names:
            if display_name.split('.')[0] == downloaded_name.split('.')[0]:
                break
            if downloaded_name == downloaded_names[-1]:
                os.remove(display_folder + '/' + display_name)


def conv_GMT_to_EST(hour):
    if hour > 4:
        hour -= 5
    else:
        hour += 19
    return hour


def pause_if_nighttime(pause_at=0, pause_until=8):
    assert pause_at < pause_until  # Darcy was too lazy to code for the case where this is not True
    nighttime = True
    while nighttime:
        current_time = time.strftime("%H:%M")
        hour = conv_GMT_to_EST(int(current_time.split(':')[0]))
        if (hour > pause_at) and (hour < pause_until):
            logger.log(debug_mode, "On night time pause")
            time.sleep(60 * 10)
        else:
            nighttime = False


def load_pic_onto_screen(image_name):
    logger.log(debug_mode, "Loading image onto screen")
    image = Image.open(image_name)
    epaper_frame = epd5in65f.EPD()
    try:
        epaper_frame.init()
        epaper_frame.Clear()
        epaper_frame.display(epaper_frame.getbuffer(image))
        logger.log(debug_mode, "Image displayed successfully")
    except Exception as e:
        logger.log(debug_mode, f"Error: {e}")
    finally:
        epaper_frame.sleep()


os.makedirs(display_folder, exist_ok=True)
time.sleep(120)  # 2 min wait so that pi can exit boot sequence (this is necessary)

while True:
    try:
        copy_bitmaps_if_necessary()
        delete_bitmaps_if_necessary()
        for display_name in display_names:
            pause_if_nighttime()
            load_pic_onto_screen(display_folder + '/' + display_name)
            time.sleep(60 * 3)
    except Exception as e:
        logger.log(debug_mode, f"Error: {e}")
        time.sleep(60 * 10)
    