# -*- coding: utf-8 -*-
"""
Convert PNG icon to ICO format for Windows Electron app.
"""
from PIL import Image
import os

png_path = r"c:\Users\dell\Desktop\winners\winners-electron\assets\icon.png"
ico_path = r"c:\Users\dell\Desktop\winners\winners-electron\assets\icon.ico"

img = Image.open(png_path).convert("RGBA")

# Create multi-resolution ICO (16, 32, 48, 64, 128, 256)
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(ico_path, format='ICO', sizes=sizes)

print(f"ICO icon created at: {ico_path}")
print(f"Sizes: {sizes}")
