import datetime
import os
import random
import shutil
import time
import win32gui
from ctypes import *

import PIL
from PIL import ImageChops, Image
from mss import mss
from pynput.keyboard import Listener, Key, Controller as cont
from pynput.mouse import Button, Controller

import dataHolder
import replay
import windowOps
from operations import moveMouse, loopAndGrabImage, resetMouse
from step import parseSteps, formatStage, Step, OutputType, Stage

# next I need to change out weapon's bay from clicking to numbers
# and I need to see if there is a better way to control the interaction menu
# use home, end, pg up and pg down to expand movement options
# leave shuttle bay door open
# use up and down with the jiffies
# wb has unnessary move at 60_56de7
# page up on planet




# loop until the screen changes, then return the found image.
# if it takes too long, just return
def loopUntilChange():
    sct = mss()
    sct_img = sct.grab(dataHolder.bbox)
    firstImage = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    count = 0
    while True:
        count = count + 1
        sct_img = sct.grab(dataHolder.bbox)
        im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        dif = PIL.ImageChops.difference(firstImage, im)
        if dif is not None and dif.getbbox() is not None:
            print("returning")
            return im
        if count > 500:
            print("leaving")
            return None




def setStep(step):
    dataHolder.stepList.append(step)


def recordWalk(outputType: OutputType, refImage: Image, current: [] = None):
    dataHolder.currentStep = dataHolder.currentStep + 1
    try:
        os.makedirs(".\\" + dataHolder.currentStageName)
    except:
        1
    refImageName = ".\\" + dataHolder.currentStageName + "\\" + str(dataHolder.currentStep) + "_" + '%05x' % random.randrange(
        16 ** 5) + ".png"
    if (refImage):
        refImage.save(refImageName)
        setStep(Step(dataHolder.currentStep, outputType, refImageName, refImage, current))
    else:
        setStep(Step(dataHolder.currentStep, outputType, None, None, current))







def loopAndPress(outputType:OutputType):
    if outputType == OutputType.UP:
        key = Key.up
    if outputType == OutputType.LEFT:
        key = Key.left
    if outputType == OutputType.RIGHT:
        key = Key.right
    if outputType == OutputType.DOWN:
        key = Key.down
    if outputType == OutputType.END:
        key = Key.end
    if outputType == OutputType.PG_DOWN:
        key = Key.page_down
    if outputType == OutputType.PG_UP:
        key = Key.page_up
    if outputType == OutputType.HOME:
        key = Key.home
    preImage = loopAndGrabImage()
    dataHolder.keyboard.press(key)
    dataHolder.keyboard.release(key)
    recordWalk(outputType, preImage)



def on_release(key):
    if not dataHolder.listen:
        return
    if hasattr(key, "name"):
        if key.name == 'ctrl_l':
            dataHolder.ctrlOn = False
        if key.name == 'tab':
            resetMouse()
            recordWalk(OutputType.RESET, None)
        if key.name == 'space':
            if not dataHolder.clickImage:
                dataHolder.clickImage = loopAndGrabImage()
            # save ref image and record click
            dataHolder.mouse.press(Button.left)
            time.sleep(0.05)
            dataHolder.mouse.release(Button.left)
            clickImageTemp = dataHolder.clickImage
            dataHolder.clickImage = False
            recordWalk(OutputType.CLICK, clickImageTemp, [dataHolder.currentMov[0], dataHolder.currentMov[1]])
            if dataHolder.ctrlOn:
                loopUntilChange()
                dataHolder.clickImage = loopAndGrabImage()
        if key.name == 'insert':
            if not dataHolder.clickImage:
                dataHolder.clickImage = loopAndGrabImage()
            # save ref image and record click
            dataHolder.keyboard.press(Key.enter)
            dataHolder.keyboard.release(Key.enter)
            clickImageTemp = dataHolder.clickImage
            dataHolder.clickImage = False
            recordWalk(OutputType.ENTER, clickImageTemp)
            if dataHolder.ctrlOn:
                clickImage = loopUntilChange()
                dataHolder.mouse.press(Button.left)
                time.sleep(0.05)
                dataHolder.mouse.release(Button.left)
                clickImageTemp = clickImage
                dataHolder.clickImage = False
                recordWalk(OutputType.CLICK, clickImageTemp, [dataHolder.currentMov[0], dataHolder.currentMov[1]])

    if hasattr(key, "char"):
        amt = 50
        if dataHolder.ctrlOn:
            amt = 5
        if key.char == 'f':
            moveMouse(0, amt, True)
        if key.char == 'g':
            moveMouse(amt, 0, True)
        if key.char == 'r':
            moveMouse(0, -amt, True)
        if key.char == 'd':
            moveMouse(-amt, 0, True)
        if key.char == 'i':
            if dataHolder.ctrlOn:
                loopAndPress(OutputType.PG_UP)
            else:
                loopAndPress(OutputType.UP)
        if key.char == 'j':
            if dataHolder.ctrlOn:
                loopAndPress(OutputType.HOME)
            else:
                loopAndPress(OutputType.LEFT)
        if key.char == 'k':
            if dataHolder.ctrlOn:
                loopAndPress(OutputType.PG_DOWN)
            else:
                loopAndPress(OutputType.DOWN)
        if key.char == 'l':
            if dataHolder.ctrlOn:
                loopAndPress(OutputType.END)
            else:
                loopAndPress(OutputType.RIGHT)
        if key.char == ';':
            for idx, x in enumerate(dataHolder.stepList):
                replay.replayStep(x)
            print("done: " + dataHolder.currentStageName)
            dataHolder.delay = False
            if dataHolder.stage.nextStageName is None:
                print("ready to read")
                if not dataHolder.append:
                    dataHolder.stage = None
                    dataHolder.stepList = []
                    dataHolder.currentStep = 0
                    dataHolder.currentStageName = ""
            else:
                dataHolder.stage = parseSteps(dataHolder.stage.nextStageName)
                dataHolder.currentStep = 1
                dataHolder.currentStageName = dataHolder.stage.name
                print("ready: " + dataHolder.stage.name)
                dataHolder.stepList = dataHolder.stage.steps
        if key.char == '/':
            try:
                ok = windll.user32.BlockInput(True)
                dataHolder.startTime = datetime.datetime.utcnow()
                replay.replayWhole(dataHolder.currentStageName)
            finally:
                ok = windll.user32.BlockInput(False)


        if key.char == '\'':
            replay.replayStep(dataHolder.stepList[dataHolder.currentStep])
            print("done: " + str(dataHolder.currentStep))
        if key.char == 'z':
            preImage = loopAndGrabImage()
            dataHolder.keyboard.press(Key.f7)
            dataHolder.keyboard.release(Key.f7)
            dataHolder.keyboard.press(Key.f8)
            dataHolder.keyboard.release(Key.f8)
            recordWalk(OutputType.ANIM_OFF, preImage)
        if key.char == '[':
            # start playback
            dataHolder.currentStageName = input('which stage?')
            dataHolder.stage = parseSteps(dataHolder.currentStageName)
            dataHolder.stepList = dataHolder.stage.steps
        if key.char == ']':
            dataHolder.append = not dataHolder.append
            if dataHolder.append:
                print("Mode: append")
            else:
                print("Mode: new")
        if key.char == 'p':
            # stop recording
            currentStageName = input('stage name:')
            f = open(currentStageName + ".dat", "w")
            for step in dataHolder.stepList:
                if step.imageName is not None:
                    step.imageName = step.imageName.replace("\\\\", "\\" + currentStageName + "\\")
            stage = formatStage(Stage(currentStageName, dataHolder.stepList))
            print(stage)
            f.write(stage)
            moveImages(currentStageName)

# moves the images currently saved in root down into a stage's dir
def moveImages(currentStageName):
    try:
        os.mkdir(".\\" + currentStageName)
    except:
        1
    for name in os.listdir("."):
        if name.endswith(".png"):
            shutil.move(name, currentStageName + "\\" + name)


# since we can't detect if control is pressed, we need to record it ourselves
def on_press(key):
    try:
        if key.name == 'ctrl_l':
            dataHolder.ctrlOn = True
    except:
        1


with Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
