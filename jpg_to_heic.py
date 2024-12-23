from PIL import Image
import os
from pillow_heif import register_heif_opener
import zipfile


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


# Example usage
folder_path = r'C:\Users\decmc\Downloads\Photos-001.zip'
unzip_file(folder_path, folder_path.replace('.zip', ''))
convert_heic_to_jpg(folder_path.replace('.zip', ''))