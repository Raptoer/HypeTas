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
            if f.endswith(".bmp"):
                Image.open(dir + "\\" + f).save(dir+"\\" + f.replace(".bmp", ".png"), "png")
                os.remove(dir + "\\" + f)


list = os.listdir(".")
for i in list:
    if i.endswith(".dat"):
        stage = step.parseSteps(i.replace(".dat", ""))
        files = [re.sub(".*?\\\\", "", s.imageName) for s in stage.steps if s.imageName is not None]
        dir = stage.name
        print(files)
        print(dir)
        allFiles = os.listdir(dir + "\\")
        for f in allFiles:
            if f not in files:
                os.remove(dir + "\\" + f)
