import os
import re

from PIL import Image

import step

list = os.listdir(".")
for i in list:
    if i.endswith(".dat"):
        dir = i.replace(".dat", "")
        allFiles = os.listdir(dir + "\\")
        for f in allFiles:
            Image.open(dir + "\\" + f).save(dir+"\\" + f.replace(".bmp", ".png"), "png")
            os.remove(dir + "\\" + f)
