from PIL import Image
from enum import Enum

class OutputType(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    W = "W"
    CLICK = "CLK"
    LONG_CLICK = "LONG_CLICK"
    CLICK_UNTIL = "CLICK_UNTIL"
    RESET="RESET"
    DELAY="DELAY"
    ENTER="ENTER"
    WAIT="WAIT"
    JACOB="JACOB"
    WAIT_GAME="WAIT_GAME"


class Step:
    def __init__(self, number, output, imageName:str, readyImage: Image, clickPos:[]=[]):
        self.number = number
        self.output = output
        self.imageName = imageName
        self.readyImage = readyImage
        self.clickPos = clickPos

class Stage:
    def __init__(self, name: str, steps: [], nextStage:str=''):
        self.name = name
        self.steps = steps
        self.nextStageName = nextStage


def parse(number, line: str):
    split = line.split(";")
    if len(split) == 1:
        return Step(number, OutputType[split[0]],None, None)
    if len(split) == 2 or len(split[2]) == 0:
        return Step(number, OutputType[split[0]],split[1], Image.open(split[1]).convert("RGBA"))
    clickPos = [int(split[2].split(",")[0]), int(split[2].split(",")[1])]
    if len(split[1]) > 0:
        return Step(number, OutputType[split[0]],split[1], Image.open(split[1]).convert("RGBA"), clickPos=clickPos)
    else:
        return  Step(number, OutputType[split[0]],split[1], None, clickPos=clickPos)

def parseSteps(fileName):
    with open(fileName+".dat") as f:
        content = f.readlines()
    content = [x.strip() for x in content]
    nextName = content[len(content) - 1].replace("?", "") if content[len(content) - 1].startswith("?") else None
    return Stage(fileName, [parse(ind, x) for ind, x in enumerate(content) if not x.startswith("#") and not x.startswith("?")], nextName)


def formatStage(stage:Stage):
    out = [formatStep(x) for x in stage.steps]
    return '\n'.join(out)

def formatStep(step:Step):
    if(step.imageName and step.clickPos):
        return step.output.name + ";" + step.imageName+";" + str(step.clickPos[0]) + "," + str(step.clickPos[1])
    if(step.imageName):
        return step.output.name + ";" + step.imageName+";"
    if(step.clickPos):
        return step.output.name + ";;" + str(step.clickPos[0]) + "," + str(step.clickPos[1])
    return step.output.name