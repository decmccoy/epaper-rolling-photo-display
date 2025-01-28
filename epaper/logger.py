from datetime import datetime


def log(debug_mode, message):
    if debug_mode:
        print(datetime.now() + ": " + message)
    else:
        print(message)