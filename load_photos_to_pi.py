from PIL import Image
import os
from pillow_heif import register_heif_opener
from file_transfer_util import create_ssh_client, read_pi_secrets, transfer_files_to_pi, delete_files_in_remote_folder
from conversion_util import unzip_file, save_as_jpg, resize_jpg, jpg_to_bitmap


register_heif_opener()
zip_folder_path = r"C:\Users\decmc\Downloads\Family_Shared_Photo_Frame-001.zip"
root_path = os.path.dirname(zip_folder_path)
raspberry_pi_info_path = f"{root_path}/raspberry_pi_zero_info.txt"
working_path = "/working/"
working_unzipped_path = f"{root_path}{working_path}unzipped"
working_jpg_path = f"{root_path}{working_path}jpg"
working_resized_path = f"{root_path}{working_path}resized"
working_bitmap_path = f"{root_path}{working_path}bitmap"

pi_secrets = read_pi_secrets(raspberry_pi_info_path)
remote_folder_path = f"/home/{pi_secrets['user_name']}/Documents/epaper_proj/downloaded_photos/"

unzip_file(zip_folder_path, working_unzipped_path)

unzipped_files = os.listdir(working_unzipped_path)
heic_images = [file for file in unzipped_files if file.lower().endswith('.heic')]
for heic in heic_images:
    heic_path = os.path.join(working_unzipped_path, heic)
    save_as_jpg(heic_path, working_jpg_path)
    
jpg_images = [file for file in unzipped_files if file.lower().endswith('.jpg')]
for jpg in jpg_images:
    jpg_path = os.path.join(working_unzipped_path, jpg)
    save_as_jpg(jpg_path, working_jpg_path)

jpg_images = [file for file in working_jpg_path if file.lower().endswith('.jpg')]
for jpg in jpg_images:
    jpg_path = os.path.join(working_jpg_path, jpg)
    resize_jpg(jpg_path, working_resized_path, 600, 448)
    
resized_images = [file for file in working_resized_path if file.lower().endswith('.jpg')]
for resized_jpg in resized_images:
    jpg_path = os.path.join(working_resized_path, resized_jpg)
    jpg_to_bitmap(jpg_path, working_bitmap_path)

ssh_client = create_ssh_client(pi_secrets['host_name'], pi_secrets['user_name'], pi_secrets['password'])
delete_files_in_remote_folder(ssh_client, remote_folder_path)
transfer_files_to_pi(ssh_client, working_bitmap_path, remote_folder_path)

os.remove(working_path)
print(f"Deleted {working_path}.")
