from PIL import Image
import os
from pillow_heif import register_heif_opener
import zipfile
import shutil
from file_transfer_to_pi import transfer_files_to_pi, delete_files_in_remote_folder


register_heif_opener()


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


def convert_heic_to_jpg(folder_path):
    # Ensure the folder path ends with '/'
    if not folder_path.endswith('/'):
        folder_path += '/'

    # Check if the folder exists
    if not os.path.exists(folder_path):
        print("Folder does not exist.")
        return

    # List all files in the folder
    files = os.listdir(folder_path)

    # Filter HEIC files
    heic_files = [f for f in files if f.lower().endswith('.heic')]

    if not heic_files:
        print("No HEIC files found in the folder.")
        return

    # Create a directory for converted images
    converted_folder = os.path.join(folder_path, 'converted_jpg')
    os.makedirs(converted_folder, exist_ok=True)

    # Iterate through each HEIC file, convert to JPG, and delete the original
    for heic_file in heic_files:
        heic_path = os.path.join(folder_path, heic_file)
        jpg_file = os.path.splitext(heic_file)[0] + '.jpg'
        jpg_path = os.path.join(converted_folder, jpg_file)

        # Convert HEIC to JPG
        try:
            with Image.open(heic_path) as img:
                img.convert('RGB').save(jpg_path, 'JPEG')
            print(f"Converted {heic_file} to JPG.")

            # Delete the original HEIC file
            os.remove(heic_path)
            print(f"Deleted {heic_file}.")
        except Exception as e:
            print(f"Error converting {heic_file}: {e}")

    print("Conversion complete.")


def transfer_files(source_dir, destination_dir):
    """
    Transfers all files from the source directory to the destination directory.

    Args:
        source_dir (str): Path to the source directory.
        destination_dir (str): Path to the destination directory.

    Raises:
        FileNotFoundError: If the source directory does not exist.
        Exception: If an error occurs during file transfer.
    """
    # Check if source directory exists
    if not os.path.exists(source_dir):
        raise FileNotFoundError(f"Source directory '{source_dir}' does not exist.")

    # Create destination directory if it doesn't exist
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    # Get all files in the source directory
    files = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]

    # Transfer each file
    for file_name in files:
        source_path = os.path.join(source_dir, file_name)
        destination_path = os.path.join(destination_dir, file_name)
        try:
            shutil.move(source_path, destination_path)
            print(f"Transferred: {file_name}")
        except Exception as e:
            print(f"Error transferring {file_name}: {e}")


def read_pi_info_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    pi_info_list = [line.strip() for line in lines]
    ret = {}
    for line in pi_info_list:
        ret[line.split(' ')[0]] = line.split(' ')[2].strip('"')
    return ret


zip_folder_path = r"C:\Users\decmc\Downloads\Family_Shared_Photo_Frame-001.zip"
album_name = 'Family_Shared_Photo_Frame'
raspberry_pi_info_path = r"C:\Users\decmc\Documents\Code\raspberry_pi_zero_info.txt"

pi_info = read_pi_info_file(raspberry_pi_info_path)
host_name = pi_info['host_name']
user_name = pi_info['user_name']
password = pi_info['password']

remote_folder = f"/home/{user_name}/Documents/epaper_proj/downloaded_photos/"


folder_path = zip_folder_path.replace('.zip', '')
local_image_folder = f"{folder_path}/{album_name}"
unzip_file(zip_folder_path, folder_path)
convert_heic_to_jpg(local_image_folder)
transfer_files(f"{local_image_folder}/converted_jpg", local_image_folder)

os.rmdir(f"{local_image_folder}/converted_jpg")

delete_files_in_remote_folder(hostname=host_name, username=user_name, password=password,
                              remote_folder_path=remote_folder)

transfer_files_to_pi(hostname=host_name, username=user_name, password=password, local_folder_path=local_image_folder,
                     remote_folder_path=remote_folder)
