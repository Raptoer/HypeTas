import multiprocessing
import os
import sys
import threading
import time
import win32gui

import PIL
import pyscreenshot as ImageGrab
from PIL import ImageOps, ImageChops
from pynput.keyboard import Listener, Key, Controller as cont
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
currentStep = 0

window = windowOps.find_window("DOSBox")
hwndChild = win32gui.GetWindowRect(window)
bbox = (hwndChild[0] + 4, hwndChild[1] + 4, hwndChild[2] - 4, hwndChild[3] - 4)
windowXmiddle = (hwndChild[0] + hwndChild[2]) / 2
windowYMiddle = ((hwndChild[1] + hwndChild[3]) / 2) + 12


def imageLoop():
    if __name__ == "__main__" and shiftOn:
        # fullscreen
        if window:
            global firstImage
            global accumulatorImage
            global bbox
            multiprocessing.freeze_support()
            try:
                im = ImageGrab.grab(bbox, childprocess=False)
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
    if not shiftOn and accumulatorImage:
        screen = PIL.ImageOps.invert(accumulatorImage.point(lambda x: 0 if x == 0 else 255))
        im = ImageGrab.grab(bbox=bbox, childprocess=False)
        im = PIL.ImageOps.invert(PIL.ImageChops.subtract(screen, im))
        global refImage
        refImage = im
        accumulatorImage = False
        firstImage = False
    return True


times = []
timeCount = 0


def runTimer():
    while 1:
        imageLoop()
        time.sleep(0.001)


job_thread = threading.Thread(target=runTimer)
job_thread.start()


def resetMouse():
    mouse.position = (-100000, -100000)
    print('Mouse reset')
    global currentMov
    currentMov = [0, 0]


def on_press(key):
    key_press = key
    try:
        if key.name == 'shift':
            global shiftOn
            if not shiftOn:
                print("shift on!")
                shiftOn = True
        if key.name == 'ctrl_l':
            global ctrlOn
            ctrlOn = True
    except:
        1


def moveMouse(x, y):
    global currentMov
    currentMov[0] = currentMov[0] + x
    currentMov[1] = currentMov[1] + y
    while x > 0 or y > 0:
        if x > 230:
            tempX = 230
        else:
            tempX = x
        if y > 230:
            tempY = 230
        else:
            tempY = x
        y = y - 230
        x = x - 230
        mouse.position = (windowXmiddle + tempX, windowYMiddle + tempY)


def recordWalk(outputType: OutputType, current: [] = None):
    global currentStep
    global refImage
    currentStep = currentStep + 1
    try:
        os.makedirs(".\\" + currentStageName)
    except:
        1
    refImageName = ".\\" + currentStageName + "\\" + str(currentStep) + ".bmp"
    if (refImage):
        refImage.save(refImageName)
        stepList.append(Step(currentStep, outputType, refImageName, refImage, current))
        refImage = False
    else:
        stepList.append(Step(currentStep, outputType, None, None, current))


listen = True


def replayStep(step: Step):
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
        moveMouse(step.clickPos[0] - currentMov[0], (step.clickPos[1] - currentMov[1]))
        time.sleep(0.1)
        mouse.press(Button.left)
        time.sleep(0.02)
        mouse.release(Button.left)
    if step.output == OutputType.RESET:
        resetMouse()
        time.sleep(0.02)
        resetMouse()
        time.sleep(0.02)
        resetMouse()
        time.sleep(0.02)
        resetMouse()


def on_release(key):
    global ctrlOn
    global currentStageName
    global currentStep
    global shiftOn
    global stepList
    global refImageName
    global listen
    if not listen:
        return
    if hasattr(key, "name"):
        if key.name == 'shift':
            if shiftOn:
                shiftOn = False
                print("shift off!")
        if key.name == 'ctrl_l':
            ctrlOn = False
        if key.name == 'tab':
            resetMouse()
        if key.name == 'space':
            # save ref image and record click
            mouse.press(Button.left)
            time.sleep(0.05)
            mouse.release(Button.left)
            recordWalk(OutputType.CLICK, [currentMov[0], currentMov[1]])
    if hasattr(key, "char"):
        amt = 50
        if ctrlOn:
            amt = 5
        if key.char == 'f':
            moveMouse(0, amt)
        if key.char == 'g':
            moveMouse(amt, 0)
        if key.char == 'r':
            moveMouse(0, -amt)
        if key.char == 'd':
            moveMouse(-amt, 0)
        if key.char == 'i':
            keyboard.press(Key.up)
            keyboard.release(Key.up)
            recordWalk(OutputType.UP)
        if key.char == 'j':
            keyboard.press(Key.left)
            keyboard.release(Key.left)
            recordWalk(OutputType.LEFT)
        if key.char == 'k':
            keyboard.press(Key.down)
            keyboard.release(Key.down)
            recordWalk(OutputType.DOWN)
        if key.char == 'l':
            keyboard.press(Key.right)
            keyboard.release(Key.right)
            recordWalk(OutputType.RIGHT)
        if key.char == '[':
            # start playback
            listen = False
            currentStageName = input('which stage?')
            stage = parseSteps(currentStageName + ".dat")
            print("starting in 5")
            time.sleep(5)
            print("starting")
            for x in stage.steps:
                replayStep(x)
                time.sleep(0.5)
            listen = True
        if key.char == 'o':
            # start recording
            listen = False
            currentStageName = input('stage name:')
            listen = True
            stepList = [Step(0, OutputType.RESET, None, None)]
        if key.char == 'p':
            # stop recording
            f = open(currentStageName + ".dat", "w")
            stage = formatStage(Stage(currentStageName, stepList))
            print(stage)
            f.write(stage)


with Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()

    # hokai, so
    # push edcv to move cursor
    # hold down shift to start capturing
    # release shift, take final image. Push space to indicate click is output
    # otherwise push ijkl to indicate direction key
