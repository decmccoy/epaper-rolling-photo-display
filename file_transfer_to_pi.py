import paramiko
from scp import SCPClient
import os


def transfer_files_to_pi(hostname, username, password, local_folder_path, remote_folder_path):
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
        # Create an SSH client instance
        ssh = paramiko.SSHClient()

        # Automatically add the server's host key if missing
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the Pi Zero
        ssh.connect(hostname, username=username, password=password)

        # Create an SCP client for file transfer
        with SCPClient(ssh.get_transport()) as scp:
            # Iterate through files in the local folder and transfer them
            for root, _, files in os.walk(local_folder_path):
                for file in files:
                    local_file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_file_path, local_folder_path)
                    remote_file_path = os.path.join(remote_folder_path, relative_path)

                    # Create remote directory structure
                    ssh.exec_command(f'mkdir -p "{os.path.dirname(remote_file_path)}"')

                    # Transfer the file
                    scp.put(local_file_path, remote_file_path)
                    print(f'Transferred file {local_file_path}')

        print("Files successfully transferred!")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the SSH connection
        ssh.close()

# Example usage:
# transfer_files_to_pi(hostname="raspberrypi1", username="mom_dad", password="raspberry",
#                      local_folder_path=r"C:\Users\decmc\Downloads\test_photos",
#                      remote_folder_path=r"/home/mom_dad/Documents/donwload_photos_test/")
