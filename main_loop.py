from download_photos import download_and_delete_photos
from load_pic_onto_frame import load_pic_onto_screen, conv_image
import os
import time

album_name = "Family_Shared_Photo_Frame"
download_folder_path = "downloaded_photos"
bitmap_folder = 'bitmap_photos'

# Create the download folder if it doesn't exist
os.makedirs(download_folder_path, exist_ok=True)
os.makedirs(bitmap_folder, exist_ok=True)
time_check = True

while True:

    download_and_delete_photos(album_name, download_folder_path)
    list_of_photos = os.listdir("downloaded_photos")
    for photo in list_of_photos:
        bitmap_name = bitmap_folder + '/' + photo.split('.')[0] + '.bmp'
        if not os.path.exists(bitmap_name):
            print("Converting Image to 7-colour bitmap")
            conv_image(download_folder_path + '/' + photo, bitmap_name)
    time_check = True
    # time.sleep(5*60)
    while time_check:
        list_of_bitmaps = os.listdir(bitmap_folder)
        for bitmap in list_of_bitmaps:
            load_pic_onto_screen(bitmap_folder + '/' + bitmap)
            time.sleep(10)
            current_time = time.strftime("%H:%M")
            hour = int(current_time.split(':')[0])
            minute = int(current_time.split(':')[1])
            if (hour == 12) and (minute < 8):
                time_check = False




