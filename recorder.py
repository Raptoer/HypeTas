import os
import random
import shutil
import sys
import time
import win32gui

from mss import mss


import PIL
import math
import pyscreenshot as ImageGrab
from PIL import ImageOps, ImageChops, Image
from pynput.keyboard import Listener, Key, Controller as cont, KeyCode
from pynput.mouse import Button, Controller

import windowOps
from step import parseSteps, formatStage, Step, OutputType, Stage

keyboard = cont()

shiftOn = False
ctrlOn = False
firstImage = False
accumulatorImage = False
refImage = False
currentMov = [0, 0]
mouse = Controller()
refImageName = None

currentStageName = ''
stepList = []
stage = None
delay = False
currentStep = 0

window = windowOps.find_window("DOSBox")
hwndChild = win32gui.GetWindowRect(window)
bbox = (hwndChild[0] + 4, hwndChild[1] + 4, hwndChild[2] - 4, hwndChild[3] - 4)
windowXmiddle = (hwndChild[0] + hwndChild[2]) / 2
windowYMiddle = ((hwndChild[1] + hwndChild[3]) / 2) + 12
append = False



#loops for 20 runs and puts together the refImage
def loopAndGrabImage():
    global bbox
    sct = mss()
    firstImage = None
    accumulatorImage = None
    for i in range(20):
        try:
            sct_img = sct.grab(bbox)
            im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            if not firstImage:
                firstImage = im
            else:
                im = PIL.ImageChops.difference(im, firstImage)
                if not accumulatorImage:
                    accumulatorImage = im
                else:
                    accumulatorImage = PIL.ImageChops.add(im, accumulatorImage)
        except:
            print(sys.exc_info())

    screen = PIL.ImageOps.invert(accumulatorImage.point(lambda x: 0 if x == 0 else 255))
    im = ImageGrab.grab(bbox=bbox, childprocess=False)
    im = PIL.ImageOps.invert(PIL.ImageChops.subtract(screen, im))
    return im

def resetMouse():
    mouse.position = (-1300, -1300)
    print('Mouse reset')
    keyboard.press(KeyCode.from_char('N'))
    keyboard.release(KeyCode.from_char('N'))
    global currentMov
    currentMov = [0, 0]

clickImage = False


def moveMouse(x, y, recordImage:bool = False):
    if recordImage:
        global clickImage
        if not clickImage:
            clickImage = loopAndGrabImage()
        else:
            time.sleep(0.1)
    global currentMov
    currentMov[0] = currentMov[0] + x
    currentMov[0] = 0 if currentMov[0] < 0 else currentMov[0]
    currentMov[1] = currentMov[1] + y
    currentMov[1] = 0 if currentMov[1] < 0 else currentMov[1]
    print("moving mouse by:" + str(x) + "," + str(y) + " to " + str(currentMov[0]) + ", " + str(currentMov[1]))
    xPos = 1 if x > 0 else -1
    yPos = 1 if y > 0 else -1
    x = math.fabs(x)
    y = math.fabs(y)
    if x == 0 and y == 0:
        return False
    while x > 0 or y > 0:
        tempX = 0
        tempY = 0
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
        mouse.position = (windowXmiddle + (xPos * tempX), windowYMiddle + (yPos * tempY))
        if x > 0 or y > 0:
            time.sleep(0.018)
    return True


def setStep(step):
    if currentStep > len(stepList):
        stepList.append(step)
    else:
        print("adding: " + step.output.name + " at " + str(currentStep-1) + " (0indexed)")
        stepList[currentStep-1] = step


def recordWalk(outputType: OutputType, refImage:Image, current: [] = None):
    global currentStep
    currentStep = currentStep + 1
    try:
        os.makedirs(".\\" + currentStageName)
    except:
        1
    refImageName = ".\\" + currentStageName + "\\" + str(currentStep) + "_" + '%05x' % random.randrange(16**5) +  ".bmp"
    if (refImage):
        refImage.save(refImageName)
        setStep(Step(currentStep, outputType, refImageName, refImage, current))
    else:
        setStep(Step(currentStep, outputType, None, None, current))


sct = mss()

def replayStep(step: Step):
    global currentStep
    global delay
    currentStep  = currentStep + 1
    print("playing:" + str(currentStep))
    if step.readyImage is not None:
        count = 0
        #if difference between current image and reference image is all black
        ignoreMask = step.readyImage.point(lambda x: 255 if x == 255 else 0)
        transparencyMask = ignoreMask.convert("1", dither = 0)
        ignoreMask.putalpha(transparencyMask)
        count = 0
        delaysGrab = []
        delaysConvert = []
        delaysAlpha = []
        delaysDifference = []
        while True:
            timeStart = time.perf_counter()
            sct_img = sct.grab(bbox)
            im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            delaysGrab.append(time.perf_counter() - timeStart)
            timeStart = time.perf_counter()
            im = im.convert("RGBA")
            delaysConvert.append(time.perf_counter() - timeStart)
            timeStart = time.perf_counter()
            im = Image.alpha_composite(im, ignoreMask)
            delaysAlpha.append(time.perf_counter() - timeStart)
            timeStart = time.perf_counter()
            dif = ImageChops.difference(im, step.readyImage)
            delaysDifference.append(time.perf_counter() - timeStart)
            count = count + 1
            if count % 5 == 0:
                print("Waiting on:" + step.imageName)
            count = count + 1
            if dif.getbbox() is None or dif.getbbox()[3] < 20:
                break
        else:
            time.sleep(0.01)
    if step.output == OutputType.UP:
        keyboard.press(Key.up)
        keyboard.release(Key.up)
    if step.output == OutputType.LEFT:
        keyboard.press(Key.left)
        keyboard.release(Key.left)
    if step.output == OutputType.DOWN:
        keyboard.press(Key.down)
        keyboard.release(Key.down)
    if step.output == OutputType.RIGHT:
        keyboard.press(Key.right)
        keyboard.release(Key.right)
    if step.output == OutputType.CLICK:
        moved = moveMouse(step.clickPos[0] - currentMov[0], (step.clickPos[1] - currentMov[1]))
        if moved:
            time.sleep(0.07)
        if delay:
            print("extra sleep")
            time.sleep(0.1)
        mouse.press(Button.left)
        time.sleep(0.02)
        if delay:
            time.sleep(0.03)
        mouse.release(Button.left)
    if step.output == OutputType.LONG_CLICK:
        moved = moveMouse(step.clickPos[0] - currentMov[0], (step.clickPos[1] - currentMov[1]))
        if moved:
            time.sleep(0.07)
        mouse.press(Button.left)
        time.sleep(0.1)
        mouse.release(Button.left)
    if step.output == OutputType.RESET:
        resetMouse()
        time.sleep(0.02)
        resetMouse()
        time.sleep(0.02)
        resetMouse()
        time.sleep(0.02)
        resetMouse()
    if step.output == OutputType.DELAY:
        delay = not delay
    return currentStep

override = False

def on_release(key):
    global ctrlOn
    global currentStageName
    global currentStep
    global shiftOn
    global stepList
    global refImageName
    global stage
    global clickImage
    global append
    global delay
    global override
    if hasattr(key, "name"):
        if key.name == 'shift':
            if shiftOn:
                shiftOn = False
        if key.name == 'ctrl_l':
            ctrlOn = False
        if key.name == 'tab':
            resetMouse()
            recordWalk(OutputType.RESET, None)
        if key.name == 'space':
            if not clickImage:
               clickImage = loopAndGrabImage()
            # save ref image and record click
            mouse.press(Button.left)
            time.sleep(0.005)
            mouse.release(Button.left)
            clickImageTemp = clickImage
            clickImage = False
            recordWalk(OutputType.CLICK, clickImageTemp, [currentMov[0], currentMov[1]])
    if hasattr(key, "char"):
        amt = 50
        if ctrlOn:
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
            preImage = loopAndGrabImage()
            keyboard.press(Key.up)
            keyboard.release(Key.up)
            recordWalk(OutputType.UP, preImage)
        if key.char == 'j':
            preImage = loopAndGrabImage()
            keyboard.press(Key.left)
            keyboard.release(Key.left)
            recordWalk(OutputType.LEFT, preImage)
        if key.char == 'k':
            preImage = loopAndGrabImage()
            keyboard.press(Key.down)
            keyboard.release(Key.down)
            recordWalk(OutputType.DOWN, preImage)
        if key.char == 'l':
            preImage = loopAndGrabImage()
            keyboard.press(Key.right)
            keyboard.release(Key.right)
            recordWalk(OutputType.RIGHT, preImage)
        if key.char == ';':
            for x in stepList:
                replayStep(x)
            print("done: " + currentStageName)
            delay = False
            if stage.nextStageName is None:
                print("ready to read")
                if not append:
                    stage = None
                    stepList = []
                    currentStep = 0
                    currentStageName = ""
            else:
                stage = parseSteps(stage.nextStageName)
                currentStep = 0
                currentStageName = stage.name
                print("ready: " + stage.name)
                stepList = stage.steps
        if key.char == '\'':
            replayStep(stepList[currentStep])
            print("done: " + str(currentStep))
        if key.char == '[':
            # start playback
            if currentStageName != '' and not override:
                override = True
                print("warning, already loaded, did you mean to press record instead? Pressing again will override")
            else:
                currentStageName = input('which stage?')
                stage = parseSteps(currentStageName)
                stepList = stage.steps
        if key.char == ']':

            append = not append
            if append:
                print("Mode: append")
            else:
                print("Mode: new")
        if key.char == 'p':
            # stop recording
            currentStageName = input('stage name:')
            f = open(currentStageName + ".dat", "w")
            for step in stepList:
                if step.imageName is not None:
                    step.imageName = step.imageName.replace("\\\\", "\\" + currentStageName + "\\")
            stage = formatStage(Stage(currentStageName, stepList))
            print(stage)
            f.write(stage)
            moveImages(currentStageName)

def moveImages(currentStageName):
    os.mkdir(".\\" + currentStageName)
    for name in os.listdir("."):
        if name.endswith(".bmp"):
            shutil.move(name, currentStageName + "\\" + name)

def on_press(key):
    try:
        if key.name == 'shift':
            global shiftOn
            if not shiftOn:
                shiftOn = True
        if key.name == 'ctrl_l':
            global ctrlOn
            ctrlOn = True
    except:
        1


with Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()

    # hokai, so
    # push edcv to move cursor
    # hold down shift to start capturing
    # release shift, take final image. Push space to indicate click is output
    # otherwise push ijkl to indicate direction key
