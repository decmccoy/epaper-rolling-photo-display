from load_pic_onto_frame import load_pic_onto_screen, conv_image
import os
import time


def conv_GMT_to_EST(hour):
    if hour > 4:
        hour -= 5
    else:
        hour += 19
    return hour


def night_time_pause(pause_at=0, pause_until=8):
    assert pause_at < pause_until  # Darcy was too lazy to code for the case where this is not True
    night_time = True
    while night_time:
        current_time = time.strftime("%H:%M")
        hour = conv_GMT_to_EST(int(current_time.split(':')[0]))
        if (hour > pause_at) and (hour < pause_until):
            print('on night time pause')
            time.sleep(60 * 10)
        else:
            night_time = False


download_folder_path = "downloaded_photos"
bitmap_folder = 'bitmap_photos'

# Create the bitmap folder if it doesn't exist
os.makedirs(bitmap_folder, exist_ok=True)

while True:
    list_of_photos = os.listdir("downloaded_photos")
    for photo in list_of_photos:
        bitmap_name = bitmap_folder + '/' + photo.split('.')[0] + '.bmp'
        if not os.path.exists(bitmap_name):
            print("Converting Image to 7-colour bitmap")
            conv_image(download_folder_path + '/' + photo, bitmap_name)

    list_of_bitmaps = os.listdir(bitmap_folder)
    for bitmap in list_of_bitmaps:
        for photo in list_of_photos:
            if bitmap.split('.')[0] == photo.split('.')[0]:
                break
            if photo == list_of_photos[-1]:
                os.remove(bitmap_folder + '/' + bitmap)
    try:
        for bitmap in list_of_bitmaps:
            night_time_pause()
            load_pic_onto_screen(bitmap_folder + '/' + bitmap)
            time.sleep(60 * 3)
    except FileNotFoundError:
        pass

