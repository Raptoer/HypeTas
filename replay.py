import datetime
import os
import threading
import time

from PIL import Image, ImageChops
from pynput.keyboard import Key
from pynput.mouse import Button

import dataHolder
from operations import pressAndRelease, moveMouse, resetMouse, loopAndGrabImage
from step import Step, parseSteps, OutputType, formatStep


def replayWhole(currentStageName):
    if len(currentStageName) == 0:
        stages = {"d2": parseSteps("d2")}
    else:
        stages = {currentStageName: parseSteps(currentStageName)}
    for x in stages:
        dataHolder.stage = stages[x]
    splitCSV = ""
    while True:
        if dataHolder.stage.nextStageName:
            # I know this creates a race condition, I just don't care
            threading.Thread(target=loadNext, args=(stages, dataHolder.stage.nextStageName)).start()
        dataHolder.currentStep = 0
        dataHolder.delay = False
        currentStageName = dataHolder.stage.name
        dataHolder.stepList = dataHolder.stage.steps
        stageStart = datetime.datetime.now()
        for idx, x in enumerate(dataHolder.stepList):
            replayStep(x)
        splitCSV = splitCSV + ""
        print("done: " + currentStageName)
        if stages[currentStageName].nextStageName is None:
            break
        dataHolder.stage = stages[stages[currentStageName].nextStageName]
        # currentStageName is actually the previous stage's name here

def replayStep(step: Step):
    if step.readyImage is not None:
        # if difference between current image and reference image is all black
        ignoreMask = getIgnoreMask(step)
        count = 1
        while True:
            sct_img = dataHolder.sct.grab(dataHolder.bbox)
            im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            im = im.convert("RGBA")
            if step.hasAlpha:
                im2 = Image.alpha_composite(im, ignoreMask)
                dif = ImageChops.difference(im2, im)
            else:
                im = Image.alpha_composite(im, ignoreMask)
                dif = ImageChops.difference(im, step.readyImage)
            count = count + 1
            if count % 50 == 0:
                print("Waiting on:" + step.imageName)
            if count % 5000 == 0:
                for i in range(dif.size[0]):
                    for j in range(dif.size[1]):
                        pixel = dif.getpixel((i,j))
                        if pixel[0] != 0 or pixel[1] != 0 or pixel[2] != 0 or pixel[3] != 0:
                            print("Found pixel:" + str(i) + "," + str(j))
                dif.show()
                dif.save("dif.png")
                os._exit(0)
            if dif.getbbox() is None or dif.getbbox()[3] < 20:
                break

            if step.output == OutputType.ENTER_UNTIL:
                if count % 4 == 0:
                    dataHolder.keyboard.press(Key.enter)
                    dataHolder.keyboard.release(Key.enter)

            if step.output == OutputType.WAIT_BOMB:
                dataHolder.keyboard.press("w")
                dataHolder.keyboard.release("w")
                time.sleep(0.01)
    if step.output == OutputType.TARGET_JIFFY:
        sct_img = dataHolder.sct.grab(dataHolder.bbox)
        im = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        coords = targetJiffy(im)
        if coords is not None:
            print("TARGET LOCK: " + str(coords))
            moveMouse(coords[0] - dataHolder.currentMov[0], (coords[1] - dataHolder.currentMov[1]))
            time.sleep(0.07)
            dataHolder.mouse.press(Button.left)
            time.sleep(0.02)
            dataHolder.mouse.release(Button.left)

            dataHolder.timedDelays += 0.09
        else:
            print("TARGET FAILED TO COORD")
    if step.output == OutputType.WAIT:
        time.sleep(0.04)
        dataHolder.timedDelays += 0.04
    if step.output == OutputType.WAIT_GAME:
        time.sleep(0.04)
        dataHolder.timedDelays += 0.04
        dataHolder.keyboard.press("w")
        dataHolder.keyboard.release("w")
    if step.output == OutputType.UP:
        dataHolder.keyboard.press(Key.up)
        dataHolder.keyboard.release(Key.up)
    if step.output == OutputType.ESCAPE:
        dataHolder.keyboard.press(Key.esc)
        dataHolder.keyboard.release(Key.esc)
    if step.output == OutputType.LEFT:
        dataHolder.keyboard.press(Key.left)
        dataHolder.keyboard.release(Key.left)
    if step.output == OutputType.DOWN:
        dataHolder.keyboard.press(Key.down)
        dataHolder.keyboard.release(Key.down)
    if step.output == OutputType.PG_UP:
        dataHolder.keyboard.press(Key.page_up)
        dataHolder.keyboard.release(Key.page_up)
    if step.output == OutputType.PG_DOWN:
        dataHolder.keyboard.press(Key.page_down)
        dataHolder.keyboard.release(Key.page_down)
    if step.output == OutputType.HOME:
        dataHolder.keyboard.press(Key.home)
        dataHolder.keyboard.release(Key.home)
    if step.output == OutputType.END:
        dataHolder.keyboard.press(Key.end)
        dataHolder.keyboard.release(Key.end)
    if step.output == OutputType.ENTER:
        dataHolder.keyboard.press(Key.enter)
        dataHolder.keyboard.release(Key.enter)
    if step.output == OutputType.MOVE:
        moved = moveMouse(step.clickPos[0] - dataHolder.currentMov[0], (step.clickPos[1] - dataHolder.currentMov[1]))
    if step.output == OutputType.ANIM_OFF:
        print("anim off")
        dataHolder.keyboard.press(Key.f7)
        time.sleep(0.02)
        dataHolder.keyboard.release(Key.f7)
        time.sleep(0.02)
        dataHolder.keyboard.press(Key.f8)
        time.sleep(0.02)
        dataHolder.keyboard.release(Key.f8)
        time.sleep(0.02)
        dataHolder.timedDelays += 0.08
    if step.output == OutputType.RIGHT:
        dataHolder.keyboard.press(Key.right)
        dataHolder.keyboard.release(Key.right)
    if step.output == OutputType.CLICK:
        if step.clickPos:
            moved = moveMouse(step.clickPos[0] - dataHolder.currentMov[0], (step.clickPos[1] - dataHolder.currentMov[1]))
            if moved:
                time.sleep(0.07)
                dataHolder.timedDelays += 0.07
            if dataHolder.delay:
                print("extra sleep")
                time.sleep(0.1)
                dataHolder.timedDelays += 0.1
        dataHolder.mouse.press(Button.left)
        time.sleep(0.02)
        dataHolder.timedDelays += 0.02
        if dataHolder.delay:
            time.sleep(0.03)
            dataHolder.timedDelays += 0.03
        dataHolder.mouse.release(Button.left)
    if step.output == OutputType.LONG_CLICK:
        moved = moveMouse(step.clickPos[0] - dataHolder.currentMov[0], (step.clickPos[1] - dataHolder.currentMov[1]))
        if moved:
            time.sleep(0.07)
            dataHolder.timedDelays += 0.07
        dataHolder.mouse.press(Button.left)
        time.sleep(0.1)
        dataHolder.timedDelays += 0.1
        dataHolder.mouse.release(Button.left)
    if step.output == OutputType.RESET:
        resetMouse()
        time.sleep(0.02)
        resetMouse()
        time.sleep(0.02)
        resetMouse()
        time.sleep(0.02)
        resetMouse()

        dataHolder.timedDelays += 0.06
    if step.output == OutputType.DELAY:
        dataHolder.delay = not dataHolder.delay
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
        moveMouse(0 - dataHolder.currentMov[0], (650 - dataHolder.currentMov[1]))
        time.sleep(0.1)
        moveMouse(0 - dataHolder.currentMov[0], (550 - dataHolder.currentMov[1]))
    if step.output == OutputType.TIME:
        print(datetime.datetime.utcnow() - dataHolder.startTime)
        print(dataHolder.timedDelays)

    dataHolder.currentStep = dataHolder.currentStep + 1
    return dataHolder.currentStep




def loadNext(stages, nextStageName):
    stages[nextStageName] = parseSteps(nextStageName)


def targetJiffy(im: Image):
    whitePix = targetJiffyInner(im, (255, 255, 255))
    if whitePix:
        return whitePix
    bluePix = targetJiffyInner(im, (159, 198, 255))
    if bluePix:
        return bluePix
    return None

def getIgnoreMask(step):
    if step.hasAlpha:
        # create out ignore mask, this is an image where any transparent part of the readyImage will be transparent on the check image
        ignoreMask = step.readyImage
    else:
        # create our ignore mask, this is an image where any white part of the readyImage will be white on the check image
        ignoreMask = step.readyImage.point(lambda x: 255 if x == 255 else 0)
        transparencyMask = ignoreMask.convert("1", dither=0)
        ignoreMask.putalpha(transparencyMask)
    return ignoreMask

def targetJiffyInner(im: Image, targetPixel: (int, int, int)):
    # crop down to just the inner field
    im = im.crop((50, 120, 600, 275))
    found_pixels = [i for i, pixel in enumerate(im.getdata()) if pixel == targetPixel]
    found_pixels_coords = [divmod(index, im.size[0]) for index in found_pixels]
    if len(found_pixels_coords) > 0:
        # 50 and 120 are offsets caused by the cropping, 1.85 is a scaling factor caused by dosbox's  mouse support
        return [found_pixels_coords[0][1] + 50, int((found_pixels_coords[0][0] + 120) * 1.85)]
    return None