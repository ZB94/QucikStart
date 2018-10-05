import os
from os import path
import sys
import webbrowser

def startfile(file_path):
    if path.exists(file_path):
        file_dir, file_name = path.split(file_path)
        os.chdir(file_dir)
    webbrowser.open(file_path)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        file_path = sys.argv[1]
        startfile(file_path)
        
        