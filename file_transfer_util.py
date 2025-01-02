import json
from scp import SCPClient
import os
import paramiko


def read_pi_secrets(file_path):
    with open(file_path, "r") as json_file:
        data = json.load(json_file)  # Load the JSON data
    return data


def create_ssh_client(hostname, username, password):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname, username=username, password=password)
    return ssh_client


def transfer_files_to_pi(ssh_client, local_folder_path, remote_folder_path, close_SSH_client=True):
    """
    Logs in to a Raspberry Pi Zero via SSH and transfers a folder of files to the Pi.

    Parameters:
        ssh_client (SSHClient): The ssh client already connected with password and username.
        local_folder_path (str): Path to the local folder to transfer.
        remote_folder_path (str): Path to the remote folder on the Pi Zero where files will be copied.

    Returns:
        None
    """
    try:
        # Create an SCP client for file transfer
        with SCPClient(ssh_client.get_transport()) as scp:
            # Iterate through files in the local folder and transfer them
            for root, _, files in os.walk(local_folder_path):
                for file in files:
                    local_file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_file_path, local_folder_path)
                    remote_file_path = os.path.join(remote_folder_path, relative_path)

                    # Create remote directory structure
                    if '.bmp' in relative_path.lower():
                        ssh_client.exec_command(f'mkdir -p "{os.path.dirname(remote_file_path)}"')

                        # Transfer the file
                        scp.put(local_file_path, remote_file_path)
                        print(f'Transferred file {relative_path}')
                    else:
                        print(f'Skipping file {relative_path}, it is not a Bitmap')

        print("Files successfully transferred!")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if close_SSH_client:
            ssh_client.close()


def delete_files_in_remote_folder(ssh_client, remote_folder_path, close_SSH_client=True):
    """
    Connects to a Raspberry Pi Zero via SSH and deletes all files in a specified folder.

    Parameters:
    ssh_client (SSHClient): The ssh client already connected with password and username.
    remote_folder_path (str): The path to the remote folder.

    Returns:
    None
    """
    try:
        delete_files_command = f"find {remote_folder_path} -type f -delete"
        stdin, stdout, stderr = ssh_client.exec_command(delete_files_command)

        # Wait for the command to complete
        stdout.channel.recv_exit_status()

        error_output = stderr.read().decode()
        if error_output:
            print(f"Error: {error_output}")
        else:
            print(f"All files in {remote_folder_path} have been deleted.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if close_SSH_client:
            ssh_client.close()

# Example usage:
# transfer_files_to_pi(hostname="raspberrypi1", username="mom_dad", password="raspberry",
#                      local_folder_path=r"C:\Users\decmc\Downloads\test_photos",
#                      remote_folder_path=r"/home/mom_dad/Documents/donwload_photos_test/")
