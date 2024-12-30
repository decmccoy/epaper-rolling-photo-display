from scp import SCPClient
import os


def transfer_files_to_pi(ssh_client, local_folder_path, remote_folder_path):
    """
    Logs in to a Raspberry Pi Zero via SSH and transfers a folder of files to the Pi.

    Parameters:
        hostname (str): The hostname or IP address of the Pi Zero.
        username (str): The SSH username.
        password (str): The SSH password.
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
                    if '.jpg' in relative_path.lower():
                        ssh_client.exec_command(f'mkdir -p "{os.path.dirname(remote_file_path)}"')

                        # Transfer the file
                        scp.put(local_file_path, remote_file_path)
                        print(f'Transferred file {relative_path}')
                    else:
                        print(f'Skipping file {relative_path}, it is not a JPG')

        print("Files successfully transferred!")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        ssh_client.close()


def delete_files_in_remote_folder(ssh_client, remote_folder_path):
    """
    Connects to a Raspberry Pi Zero via SSH and deletes all files in a specified folder.

    Parameters:
    hostname (str): The hostname or IP address of the Raspberry Pi Zero.
    username (str): The SSH username.
    password (str): The SSH password.
    remote_folder_path (str): The path to the remote folder.

    Returns:
    None
    """
    try:
        # Form the command to delete all files in the directory
        command = f"find {remote_folder_path} -type f -delete"

        stdin, stdout, stderr = ssh_client.exec_command(command)

        # Wait for the command to complete
        stdout.channel.recv_exit_status()

        # Check for errors
        error_output = stderr.read().decode()
        if error_output:
            print(f"Error: {error_output}")
        else:
            print(f"All files in {remote_folder_path} have been deleted.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        ssh_client.close()

# Example usage:
# transfer_files_to_pi(hostname="raspberrypi1", username="mom_dad", password="raspberry",
#                      local_folder_path=r"C:\Users\decmc\Downloads\test_photos",
#                      remote_folder_path=r"/home/mom_dad/Documents/donwload_photos_test/")
