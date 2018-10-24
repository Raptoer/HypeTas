import datetime
import gc
import math
import os
import random
import shutil
import sys
import threading
import time
import weakref
import win32gui

import os, win32api, win32con, win32process
import PIL
from PIL import ImageChops, Image
from mss import mss
from pynput.keyboard import Listener, Key, Controller as cont, KeyCode
from pynput.mouse import Button, Controller

import windowOps
from step import parseSteps, formatStage, Step, OutputType, Stage

keyboard = cont()

ctrlOn = False
firstImage = False
refImage = False
currentMov = [0, 0]
mouse = Controller()

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


#loops for 20 runs and puts together the refImage
def loopAndGrabImage():
    global bbox
    firstImage = None
    accumulatorImage = None
    sct_img = sct.grab(bbox)
    im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    return im

def resetMouse():
    mouse.position = (-1300, -1300)
    print('Mouse reset')
    #reset the text area, so we don't get differences between loads  and run throughs
    keyboard.press(KeyCode.from_char('N'))
    keyboard.release(KeyCode.from_char('N'))
    global currentMov
    currentMov = [0, 0]

clickImage = False


def moveMouse(x, y, recordImage:bool = False):
    #we want to record the ref image before we move the mouse the first time
    if recordImage:
        global clickImage
        if not clickImage:
            clickImage = loopAndGrabImage()
        else:
            time.sleep(0.1)
    global currentMov
    global timedDelays
    currentMov[0] = currentMov[0] + x
    currentMov[0] = 0 if currentMov[0] < 0 else currentMov[0]
    currentMov[1] = currentMov[1] + y
    currentMov[1] = 0 if currentMov[1] < 0 else currentMov[1]
    #x and y positive
    xPos = 1 if x > 0 else -1
    yPos = 1 if y > 0 else -1
    x = math.fabs(x)
    y = math.fabs(y)
    #if we're not moving, just exit
    if x == 0 and y == 0:
        return False
    while x > 0 or y > 0:
        tempX = 0
        tempY = 0
        #we can only reliably move 230px in one go
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
        #windows always thinks the mouse is located at the middle of the window, even if we move it will end up back in the middle
        mouse.position = (windowXmiddle + (xPos * tempX), windowYMiddle + (yPos * tempY))
        if x > 0 or y > 0:
            time.sleep(0.03)
            timedDelays += 0.05
    return True


def setStep(step):
    stepList.append(step)


def recordWalk(outputType: OutputType, refImage:Image, current: [] = None):
    global currentStep
    currentStep = currentStep + 1
    try:
        os.makedirs(".\\" + currentStageName)
    except:
        1
    refImageName = ".\\" + currentStageName + "\\" + str(currentStep) + "_" + '%05x' % random.randrange(16**5) +  ".png"
    if (refImage):
        refImage.save(refImageName)
        setStep(Step(currentStep, outputType, refImageName, refImage, current))
    else:
        setStep(Step(currentStep, outputType, None, None, current))


sct = mss()

def targetJiffy(im:Image):
    whitePix = targetJiffyInner(im, (255, 255, 255))
    if whitePix:
        return whitePix
    bluePix = targetJiffyInner(im, (159,198,255))
    if bluePix:
        return bluePix
    return None


def targetJiffyInner(im:Image, targetPixel:(int, int, int)):
    #crop down to just the inner field
    im = im.crop((50, 120, 600, 275))
    found_pixels = [i for i, pixel in enumerate(im.getdata()) if pixel == targetPixel]
    found_pixels_coords = [divmod(index, im.size[0]) for index in found_pixels]
    if len(found_pixels_coords) > 0:
        #50 and 120 are offsets caused by the cropping, 1.85 is a scaling factor caused by dosbox's mouse support
        return [found_pixels_coords[0][1] + 50, int((found_pixels_coords[0][0] + 120) * 1.85)]
    return None



timedDelays = 0


def moveAndClick(step, currentMov, postMoveDelay, midClickDelay, postMoveAlways):
    global timedDelays
    global newStepList
    moved = False
    if step.clickPos:
        moved = moveMouse(step.clickPos[0] - currentMov[0], (step.clickPos[1] - currentMov[1]))
    if postMoveAlways > 0.0:
        time.sleep(postMoveAlways)

    if moved:
        time.sleep(postMoveDelay)
        timedDelays += postMoveDelay
    if moved and step.imageName is not None and step.imageName != "":
        img = loopAndGrabImage()
        imageName = step.imageName.replace(".png", "_move.png")
        img.save(imageName, "png")
        newStepList.append(Step(-1, OutputType.MOVE, imageName, img, step.clickPos))

    mouse.press(Button.left)
    time.sleep(midClickDelay)
    timedDelays += midClickDelay
    mouse.release(Button.left)
    pass


def replayStep(step: Step):
    global currentStep
    global delay
    global replayLast
    global timedDelays
    global newStepList
    currentStep = currentStep + 1
    if step.readyImage is not None:
        count = 0
        #if difference between current image and reference image is all black
        if step.hasAlpha:
            #create out ignore mask, this is an image where any transparent part of the readyImage will be transparent on the check image
            ignoreMask = step.readyImage
        else:
            #create our ignore mask, this is an image where any white part of the readyImage will be white on the check image
            ignoreMask = step.readyImage.point(lambda x: 255 if x == 255 else 0)
            transparencyMask = ignoreMask.convert("1", dither = 0)
            ignoreMask.putalpha(transparencyMask)
        count = 1
        while True:
            sct_img = sct.grab(bbox)
            im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            im = im.convert("RGBA")
            if step.hasAlpha:
                im2 = Image.alpha_composite(im, ignoreMask)
                dif = ImageChops.difference(im2, im)
            else:
                im = Image.alpha_composite(im, ignoreMask)
                dif = ImageChops.difference(im, step.readyImage)
            count = count + 1
            if step.output == OutputType.ENTER_UNTIL:
                keyboard.press(Key.enter)
                keyboard.release(Key.enter)
            if count % 50 == 0:
                print("Waiting on:" + step.imageName + " it will be a " + str(step.output))
                if step.imageName.endswith("2_cc112.png"):
                    dif.show()
                    dif.save("dif.png")
                    step.readyImage.show()
                    os._exit(0)
            if count % 2000 == 0:
                print("Waiting on:" + step.imageName + " it will be a " + str(step.output))
                dif.show()
                dif.save("dif.png")
                step.readyImage.show()
                os._exit(0)
            if dif.getbbox() is None or dif.getbbox()[3] < 20:
                break
    if step.output == OutputType.TARGET_JIFFY:
        sct_img = sct.grab(bbox)
        im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        coords = targetJiffy(im)
        if coords is not None:
            print("TARGET LOCK: " + str(coords))
            moveMouse(coords[0] - currentMov[0], (coords[1] - currentMov[1]))
            time.sleep(0.07)
            mouse.press(Button.left)
            time.sleep(0.02)
            mouse.release(Button.left)

            timedDelays += 0.09
        else:
            print("TARGET FAILED TO COORD")
    if step.output == OutputType.UP:
        keyboard.press(Key.up)
        keyboard.release(Key.up)
    if step.output == OutputType.WAIT:
            time.sleep(0.05)
            timedDelays += 0.05
    if step.output == OutputType.WAIT_GAME:
            time.sleep(0.05)
            timedDelays += 0.05
            keyboard.press("w")
            keyboard.release("w")
    if step.output == OutputType.ESCAPE:
            keyboard.press(Key.esc)
            keyboard.release(Key.esc)
    if step.output == OutputType.LEFT:
        keyboard.press(Key.left)
        keyboard.release(Key.left)
    if step.output == OutputType.DOWN:
        keyboard.press(Key.down)
        keyboard.release(Key.down)
    if step.output == OutputType.ENTER:
        keyboard.press(Key.enter)
        keyboard.release(Key.enter)
    if step.output == OutputType.PG_UP:
        keyboard.press(Key.page_up)
        keyboard.release(Key.page_up)
    if step.output == OutputType.PG_DOWN:
        keyboard.press(Key.page_down)
        keyboard.release(Key.page_down)
    if step.output == OutputType.HOME:
        keyboard.press(Key.home)
        keyboard.release(Key.home)
    if step.output == OutputType.END:
        keyboard.press(Key.END)
        keyboard.release(Key.END)
    if step.output == OutputType.MOVE:
        moved = moveMouse(step.clickPos[0] - currentMov[0], (step.clickPos[1] - currentMov[1]))
    if step.output == OutputType.ANIM_OFF:
        print("anim off")
        keyboard.press(Key.f7)
        time.sleep(0.02)
        keyboard.release(Key.f7)
        time.sleep(0.02)
        keyboard.press(Key.f8)
        time.sleep(0.02)
        keyboard.release(Key.f8)
        time.sleep(0.02)
        timedDelays += 0.08
    if step.output == OutputType.RIGHT:
        keyboard.press(Key.right)
        keyboard.release(Key.right)
    if step.output == OutputType.CLICK:

        if delay:
            print("delay")
        moveAndClick(step, currentMov, 0.07, 0.05 if delay else 0.02, 0.1 if delay else 0)
    if step.output == OutputType.LONG_CLICK:

        moveAndClick(step, currentMov, 0.07, 0.1, 0)
    if step.output == OutputType.RESET:
        resetMouse()
        time.sleep(0.02)
        resetMouse()
        time.sleep(0.02)
        resetMouse()
        time.sleep(0.02)
        resetMouse()

        timedDelays += 0.06
    if step.output == OutputType.DELAY:
        delay = not delay
    if step.output == OutputType.JACOB:
        pressAndRelease("1")
        pressAndRelease("2")
        pressAndRelease("3")
        pressAndRelease("4")
        pressAndRelease("5")
        pressAndRelease("6")
        pressAndRelease("7")
        pressAndRelease("2")
        pressAndRelease("8")
        pressAndRelease("8")
        pressAndRelease("9")
        pressAndRelease("0")
        pressAndRelease(Key.enter)
    if step.output == OutputType.INV_LEFT:
        moveMouse(0 - currentMov[0], (650 - currentMov[1]))
        time.sleep(0.1)
        moveMouse(0 - currentMov[0], (550 - currentMov[1]))
    if step.output == OutputType.TIME:
        global startTime
        print(datetime.datetime.utcnow() - startTime)
        print(timedDelays)
    return currentStep

startTime = None
newStepList = []

def pressAndRelease(key):
    keyboard.press(key)
    keyboard.release(key)

def on_release(key):
    global currentStageName
    global currentStep
    global stepList
    global stage
    global clickImage
    global delay
    global newStepList
    global startTime
    if hasattr(key, "char"):
        if key.char == '/':

            startTime = datetime.datetime.utcnow()
            if len(currentStageName) == 0:
                stages = {"planet": parseSteps("planet")}
            else:
                stages = {currentStageName: parseSteps(currentStageName)}
            for x in stages:
                stage = stages[x]
            while True:
                if stage.nextStageName:
                    # I know this creates a race condition, I just don't care
                    threading.Thread(target=loadNext, args=(stages, stage.nextStageName)).start()
                currentStep = 0
                delay = False
                currentStageName = stage.name
                stepList = stage.steps
                newStepList = []
                for idx, x in enumerate(stepList):
                    replayStep(x)
                    newStepList.append(x)
                print("done: " + currentStageName)
                for i, step in enumerate(newStepList):
                    if step.output == OutputType.MOVE:
                        if newStepList[i+1].output == OutputType.CLICK or newStepList[i+1].output == OutputType.LONG_CLICK:
                            stepImage = step.imageName
                            nextStep = newStepList[i+1]
                            nextStepImage = nextStep.imageName
                            step.imageName = nextStepImage
                            nextStep.imageName = stepImage
                f = open(currentStageName + ".dat", "w")
                stage = formatStage(Stage(currentStageName, newStepList))
                f.write(stage)

                han = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, 0,
                                           os.getpid())
                process_memory = int(win32process.GetProcessMemoryInfo(han)['WorkingSetSize'])
                print("memory:" + str(process_memory))
                nextStageName = stages[currentStageName].nextStageName
                stage = stages[nextStageName]
                if nextStageName is None:
                    break



def loadNext(stages, nextStageName):
    stages[nextStageName] = parseSteps(nextStageName)


with Listener(on_release=on_release) as listener:
    listener.join()
