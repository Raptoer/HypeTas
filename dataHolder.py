import win32gui

from mss import mss
from pynput.keyboard import Controller as cont
from pynput.mouse import Controller

import windowOps

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

sct = mss()
timedDelays = 0

listen = True
startTime = None
clickImage = False