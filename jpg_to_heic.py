from PIL import Image
import os
from pillow_heif import register_heif_opener
import zipfile
import shutil
import paramiko
from file_transfer_to_pi import transfer_files_to_pi, delete_files_in_remote_folder
import convert


register_heif_opener()
zip_folder_path = r"C:\Users\decmc\Downloads\Family_Shared_Photo_Frame-001.zip"
album_name = 'Family_Shared_Photo_Frame'
raspberry_pi_info_path = r"C:\Users\decmc\Documents\Code\raspberry_pi_zero_info.txt"




folder_path = zip_folder_path.replace('.zip', '')
local_image_folder = f"{folder_path}/{album_name}"

def unzip_file(zip_file_path, extract_to):
    """
    Unzips a zip file to the specified directory.

    Parameters:
    - zip_file_path (str): The path to the zip file.
    - extract_to (str): The directory where the contents should be extracted.
    """
    # Ensure the output directory exists
    os.makedirs(extract_to, exist_ok=True)

    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Extracted all files to {extract_to}")


def read_pi_info_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    pi_info_list = [line.strip() for line in lines]
    ret = {}
    for line in pi_info_list:
        ret[line.split(' ')[0]] = line.split(' ')[2].strip('"')
    return ret


def create_ssh_client(hostname, username, password):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname, username=username, password=password)
    return ssh_client


def main():
    pi_info = read_pi_info_file(raspberry_pi_info_path)
    hostname = pi_info['host_name']
    username = pi_info['user_name']
    password = pi_info['password']
    remote_folder_path = f"/home/{username}/Documents/epaper_proj/downloaded_photos/"
    
    unzip_file(zip_folder_path, folder_path)
    
    if not folder_path.endswith('/'):
        folder_path += '/'

    if not os.path.exists(folder_path):
        print("Folder does not exist.")
        return

    files = os.listdir(folder_path)
    heic_images = [file for file in files if file.lower().endswith('.heic')]
    for heic in heic_images:
        heic_path = os.path.join(folder_path, heic)
        convert.save_as_jpg(heic_path)
        os.remove(heic_path)
        print(f"Deleted {heic}.")

    jpgs_names = [file for file in files if file.lower().endswith('.jpg')]
    for jpg_name in jpgs_names:
        jpg_path = os.path.join(folder_path, jpg_name)
        jpg = Image.open(jpg_path)
        jpg = convert.resize_and_pad_jpg(jpg, 600, 448)
        bitmap = convert.jpg_to_bitmap(jpg)
        bitmap.save(jpg_path + ".bmp")
        os.remove(jpg)
        print(f"Deleted {jpg}.")

    ssh_client = create_ssh_client(hostname, username, password)
    delete_files_in_remote_folder(ssh_client, remote_folder_path)
    transfer_files_to_pi(ssh_client, local_image_folder, remote_folder_path)


if __name__ == "__main__":
    main()