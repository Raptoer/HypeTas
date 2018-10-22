import os

import cv2
import numpy as np
from matplotlib import pyplot as plt

from step import parseSteps, OutputType

template = cv2.imread('arrowUp.bmp',cv2.IMREAD_COLOR )
d, w, h = template.shape[::-1]

# All the 6 methods for comparison in a list
meth = 'cv2.TM_CCORR_NORMED'

method = eval(meth)



listdir = os.listdir(".")
for file in listdir:
    if file.endswith(".dat"):
        stage = parseSteps(file.replace(".dat", ""))
        for step in stage.steps:
            if step.output == OutputType.CLICK and step.imageName:
                img = cv2.imread(step.imageName,cv2.IMREAD_COLOR)
                res = cv2.matchTemplate(img,template,method)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                if max_val > 0.85:
                    print("Hit on: " + step.imageName)
