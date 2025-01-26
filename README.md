# Raspberry Pi Epaper Photo Frame
This project displays photos on a Epaper photo frame using a connected Raspberry Pi Zero. 
This repo holds both the onboard software for the Pi and the script to move photos through wifi from a computer to the Pi.
## Necessary File Structure
#### Onboard Pi Files
- main_loop.py
- logger.py
#### Image Transfer Script Files
- load_photos_to_pi.py
- conversion_util.py
- file_transfer_util.py
## How to Run
- Set up Pi with necessary dependancies and folders
- Use Thonny to move the onboard python files to the Pi
- Download a zip folder of the photos to be moved to the Pi
- Create raspberry_pi_zero_info.json to hold host_name, user_name and password
- Run the load_photos_to_pi.py file