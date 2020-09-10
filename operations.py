import math
import sys
import time
import dataHolder

from pynput.keyboard import KeyCode

import PIL
from PIL import ImageChops, Image

def pressAndRelease(key):
    dataHolder.keyboard.press(key)
    dataHolder.keyboard.release(key)



def resetMouse():
    dataHolder.mouse.position = (-1300, -1300)
    print('Mouse reset')
    # reset the text area, so we don't get differences between loads  and run throughs
    dataHolder.keyboard.press(KeyCode.from_char('N'))
    dataHolder.keyboard.release(KeyCode.from_char('N'))
    dataHolder.currentMov = [0, 0]


# loops for 3 runs and puts together the refImage
def loopAndGrabImage():
    firstImage = None
    accumulatorImage = None
    for i in range(3):
        try:
            sct_img = dataHolder.sct.grab(dataHolder.bbox)
            im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            if not firstImage:
                firstImage = im
            else:
                # take the new image, find the difference between it and the first image, convert it to greyscale, then make any colored pixel white
                # the goal is to end up with a black image with only the differences in white
                dif = PIL.ImageChops.difference(im, firstImage).convert("L").point((lambda x: 0 if x == 0 else 255))
                if not accumulatorImage:
                    accumulatorImage = dif
                else:
                    # add the different difs together, so we end up with the union of all the differences
                    accumulatorImage = PIL.ImageChops.add(dif, accumulatorImage)
            time.sleep(0.04)
        except:
            print(sys.exc_info())

    screen = accumulatorImage.convert("RGB")
    return PIL.ImageChops.add(firstImage, screen)



def moveMouse(x, y, recordImage: bool = False):
    # we want to record the ref image before we move the mouse the first time
    if recordImage:
        if not dataHolder.clickImage:
            dataHolder.clickImage = loopAndGrabImage()
        else:
            time.sleep(0.1)
    dataHolder.currentMov[0] = dataHolder.currentMov[0] + x
    dataHolder.currentMov[0] = 0 if dataHolder.currentMov[0] < 0 else dataHolder.currentMov[0]
    dataHolder.currentMov[1] = dataHolder.currentMov[1] + y
    dataHolder.currentMov[1] = 0 if dataHolder.currentMov[1] < 0 else dataHolder.currentMov[1]
    print("moving mouse by:" + str(x) + "," + str(y) + " to " + str(dataHolder.currentMov[0]) + ", " + str(dataHolder.currentMov[1]))
    # x and y positive
    xPos = 1 if x > 0 else -1
    yPos = 1 if y > 0 else -1
    x = math.fabs(x)
    y = math.fabs(y)
    # if we're not moving, just exit
    if x == 0 and y == 0:
        return False
    while x > 0 or y > 0:
        tempX = 0
        tempY = 0
        # we can only reliably move 230px in one go
        if x > 0:
            if x > 230:
                tempX = 230
            else:
                tempX = x
        if y > 0:
            if y > 230:
                tempY = 230
            else:
                tempY = y
        y = y - 230
        x = x - 230
        # windows always thinks the mouse is located at the middle of the window, even if we move it will end up back in the middle
        dataHolder.mouse.position = (dataHolder.windowXmiddle + (xPos * tempX), dataHolder.windowYMiddle + (yPos * tempY))
        if x > 0 or y > 0:
            time.sleep(0.03)
            dataHolder.timedDelays += 0.05
    return True

