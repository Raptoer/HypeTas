import datetime
import math
import os
import random
import shutil
import sys
import threading
import time
import win32gui

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
append = False

#loop until the screen changes, then return the found image.
#if it takes too long, just return
def loopUntilChange():
    global bbox
    sct = mss()
    sct_img = sct.grab(bbox)
    firstImage = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    count = 0
    while True:
        count = count + 1
        sct_img = sct.grab(bbox)
        im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        dif = PIL.ImageChops.difference(firstImage, im)
        if dif is not None and dif.getbbox() is not None:
            print("returning")
            return im
        if count > 500:
            print("leaving")
            return None



#loops for 20 runs and puts together the refImage
def loopAndGrabImage():
    global bbox
    firstImage = None
    accumulatorImage = None
    for i in range(20):
        try:
            sct_img = sct.grab(bbox)
            im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            if not firstImage:
                firstImage = im
            else:
                #take the new image, find the difference between it and the first image, convert it to greyscale, then make any colored pixel white
                #the goal is to end up with a black image with only the differences in white
                dif = PIL.ImageChops.difference(im, firstImage).convert("L").point((lambda x: 0 if x == 0 else 255))
                if not accumulatorImage:
                    accumulatorImage = dif
                else:
                    #add the different difs together, so we end up with the union of all the differences
                    accumulatorImage = PIL.ImageChops.add(dif, accumulatorImage)
        except:
            print(sys.exc_info())

    screen = accumulatorImage.convert("RGB")
    return PIL.ImageChops.add(firstImage, screen)

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
    currentMov[0] = currentMov[0] + x
    currentMov[0] = 0 if currentMov[0] < 0 else currentMov[0]
    currentMov[1] = currentMov[1] + y
    currentMov[1] = 0 if currentMov[1] < 0 else currentMov[1]
    print("moving mouse by:" + str(x) + "," + str(y) + " to " + str(currentMov[0]) + ", " + str(currentMov[1]))
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


#grab a first image, then wait and grab a next image, if nothing has changed, replay the step
def threadedReattempt(step:Step, middleDelay:float):
    global replayLast
    if not delay:
        sct2 = mss()
        sct_img = sct2.grab(bbox)
        im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        time.sleep(middleDelay)
        sct_img2 = sct2.grab(bbox)
        im2 = Image.frombytes("RGB", sct_img2.size, sct_img2.bgra, "raw", "BGRX")
        dif = ImageChops.difference(im, im2)
        if dif.getbbox() is None or dif.getbbox()[3] < 20:
            print("WARNING: REPLAYING ON FOR" + step.imageName)
            replayLast = True

replayLast = False

timedDelays = 0

def replayStep(step: Step, previousStep:Step):
    global currentStep
    global delay
    global replayLast
    global timedDelays
    currentStep  = currentStep + 1
    print("playing:" + str(currentStep))
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
        count = 0
        while True:
            sct_img = sct.grab(bbox)
            im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            im = im.convert("RGBA")
            if step.hasAlpha:
                print(step.imageName + " has alpha")
                im2 = Image.alpha_composite(im, ignoreMask)
                dif = ImageChops.difference(im2, im)
            else:
                im = Image.alpha_composite(im, ignoreMask)
                dif = ImageChops.difference(im, step.readyImage)
            count = count + 1
            if step.output == OutputType.ENTER_UNTIL:
                keyboard.press(Key.enter)
                keyboard.release(Key.enter)
            if replayLast:
                if previousStep:
                    print("WARNING: REPLAYING: " + previousStep.imageName)
                    currentStep = currentStep - 1
                    replayLast = False
                    thread = threading.Thread(target=threadedReattempt, args=(step,0.3))
                    thread.start()
                    mouse.press(Button.left)
                    time.sleep(0.02)
                    mouse.release(Button.left)
            if count % 50 == 0:
                print("Waiting on:" + step.imageName)
                if step.imageName.endswith("63_96d7a.png"):
                    dif.show()
                    dif.save("dif.png")
            if dif.getbbox() is None or dif.getbbox()[3] < 20:
                break
        else:
            time.sleep(0.01)
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
        if step.clickPos:
            moved = moveMouse(step.clickPos[0] - currentMov[0], (step.clickPos[1] - currentMov[1]))
            if moved:
                time.sleep(0.07)
                timedDelays += 0.07
            if delay:
                print("extra sleep")
                time.sleep(0.1)
                timedDelays += 0.1
        thread = threading.Thread(target=threadedReattempt, args=(step,0.2))
        thread.start()
        mouse.press(Button.left)
        time.sleep(0.02)
        timedDelays += 0.02
        if delay:
            time.sleep(0.03)
            timedDelays += 0.03
        mouse.release(Button.left)
    if step.output == OutputType.LONG_CLICK:
        moved = moveMouse(step.clickPos[0] - currentMov[0], (step.clickPos[1] - currentMov[1]))
        if moved:
            time.sleep(0.07)

            timedDelays += 0.08
        thread = threading.Thread(target=threadedReattempt, args=(step,0.2))
        thread.start()
        mouse.press(Button.left)
        time.sleep(0.1)
        timedDelays += 0.1
        mouse.release(Button.left)
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

override = False
listen = True
startTime = None


def pressAndRelease(key):
    keyboard.press(key)
    keyboard.release(key)

def on_release(key):
    #I'm somewhat embarassed by how many global variables I use here
    global ctrlOn
    global currentStageName
    global currentStep
    global stepList
    global stage
    global clickImage
    global append
    global delay
    global override
    global startTime
    global listen
    if not listen:
        return
    if hasattr(key, "name"):
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
            time.sleep(0.08)
            mouse.release(Button.left)
            clickImageTemp = clickImage
            clickImage = False
            recordWalk(OutputType.CLICK, clickImageTemp, [currentMov[0], currentMov[1]])
            if ctrlOn:
                loopUntilChange()
                clickImage = loopAndGrabImage()
        if key.name == 'end':
            if not clickImage:
               clickImage = loopAndGrabImage()
            # save ref image and record click
            mouse.press(Button.left)
            time.sleep(0.08)
            mouse.release(Button.left)
            clickImageTemp = clickImage
            clickImage = False
            recordWalk(OutputType.LONG_CLICK, clickImageTemp, [currentMov[0], currentMov[1]])
            time.sleep(0.05)
            clickImage = loopAndGrabImage()
            # save ref image and record click
            mouse.press(Button.left)
            time.sleep(0.08)
            mouse.release(Button.left)
            clickImageTemp = clickImage
            clickImage = False
            recordWalk(OutputType.LONG_CLICK, clickImageTemp, [currentMov[0], currentMov[1]])
            loopUntilChange()
            clickImage = loopAndGrabImage()
            # save ref image and record click
            mouse.press(Button.left)
            time.sleep(0.08)
            mouse.release(Button.left)
            clickImageTemp = clickImage
            clickImage = False
            recordWalk(OutputType.LONG_CLICK, clickImageTemp, [currentMov[0], currentMov[1]])
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
            time.sleep(0.05)
            keyboard.release(Key.up)
            recordWalk(OutputType.UP, preImage)
        if key.char == 'j':
            preImage = loopAndGrabImage()
            keyboard.press(Key.left)
            time.sleep(0.05)
            keyboard.release(Key.left)
            recordWalk(OutputType.LEFT, preImage)
        if key.char == 'k':
            preImage = loopAndGrabImage()
            keyboard.press(Key.down)
            time.sleep(0.05)
            keyboard.release(Key.down)
            recordWalk(OutputType.DOWN, preImage)
        if key.char == 'l':
            preImage = loopAndGrabImage()
            keyboard.press(Key.right)
            time.sleep(0.05)
            keyboard.release(Key.right)
            recordWalk(OutputType.RIGHT, preImage)
        if key.char == ';':
            for idx, x in enumerate(stepList):
                replayStep(x, stepList[idx-1] if idx > 0 else None)
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
                currentStep = 1
                currentStageName = stage.name
                print("ready: " + stage.name)
                stepList = stage.steps
        if key.char == '/':
            startTime = datetime.datetime.utcnow()
            if len(currentStageName) == 0:
                stages = [parseSteps("d2")]
            else:
                stages = [parseSteps(currentStageName)]
            while True:
                stages.append(parseSteps(stages[len(stages)-1].nextStageName))
                if stages[len(stages)-1].nextStageName is None:
                    break
            for stage in stages:
                currentStep = 0
                delay = False
                currentStageName = stage.name
                stepList = stage.steps
                for idx, x in enumerate(stepList):
                    replayStep(x, stepList[idx-1] if idx > 0 else None)
                print("done: " + currentStageName)
        if key.char == '\'':
            replayStep(stepList[currentStep], None)
            print("done: " + str(currentStep))
        if key.char == 'z':
            preImage = loopAndGrabImage()
            keyboard.press(Key.f7)
            keyboard.release(Key.f7)
            keyboard.press(Key.f8)
            keyboard.release(Key.f8)
            recordWalk(OutputType.ANIM_OFF, preImage)
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


#moves the images currently saved in root down into a stage's dir
def moveImages(currentStageName):
    try:
        os.mkdir(".\\" + currentStageName)
    except:
        1
    for name in os.listdir("."):
        if name.endswith(".png"):
            shutil.move(name, currentStageName + "\\" + name)

#since we can't detect if control is pressed, we need to record it ourselves
def on_press(key):
    try:
        if key.name == 'ctrl_l':
            global ctrlOn
            ctrlOn = True
    except:
        1


with Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
