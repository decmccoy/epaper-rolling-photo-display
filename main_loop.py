from download_photos import download_and_delete_photos
from load_pic_onto_frame import load_pic_onto_screen, conv_image
import os
import time


def time_to_download_photos():
    current_time = time.strftime("%H:%M")
    hour = int(current_time.split(':')[0])
    if hour > 4:
        hour = hour - 5
    else:
        hour = 19 + hour
    minute = int(current_time.split(':')[1])
    return (hour == 12) and (minute < 8)

def night_time_pause():
    night_time = True
    while night_time:
        current_time = time.strftime("%H:%M")
        hour = int(current_time.split(':')[0])
        if hour > 4:
            hour = hour - 5
        else:
            hour = 19 + hour
        if hour < 8:
            print('on night time pause')
            time.sleep(60*10)
        else:
            night_time = False 
    return False

album_name = "Family_Shared_Photo_Frame"
download_folder_path = "downloaded_photos"
bitmap_folder = 'bitmap_photos'

# Create the download folder if it doesn't exist
os.makedirs(download_folder_path, exist_ok=True)
os.makedirs(bitmap_folder, exist_ok=True)
time_check = True

while True:
    try:
        download_and_delete_photos(album_name, download_folder_path)
    except:
        pass
    
    list_of_photos = os. listdir("downloaded_photos")
    for photo in list_of_photos:
        bitmap_name = bitmap_folder + '/' + photo.split('.')[0] + '.bmp'
        if not os.path.exists(bitmap_name):
            print("Converting Image to 7-colour bitmap")
            conv_image(download_folder_path + '/' + photo, bitmap_name)
    time_check = True
    time.sleep(5*60)
    
    list_of_bitmaps = os. listdir(bitmap_folder)
    
    for bitmap in list_of_bitmaps:
        for photo in list_of_photos:
            if bitmap.split('.')[0] == photo.split('.')[0]:
                break
            if photo == list_of_photos[-1]:
                os.remove(bitmap_folder + '/' + bitmap)
    
    while time_check:
        for bitmap in list_of_bitmaps:
            
            if time_to_download_photos() or night_time_pause():
                time_check = False
                print('Downloading new photos')
            
            load_pic_onto_screen(bitmap_folder + '/' + bitmap)
            time.sleep(60*5)
            current_time = time.strftime("%H:%M")
            hour = int(current_time.split(':')[0])
            minute = int(current_time.split(':')[1])
            




