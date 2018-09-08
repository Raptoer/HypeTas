from ctypes import *

EnumWindows = windll.user32.EnumWindows
EnumWindowsProc = WINFUNCTYPE(c_bool, c_int, POINTER(c_int))
GetWindowText = windll.user32.GetWindowTextW
GetWindowTextLength = windll.user32.GetWindowTextLengthW
IsWindowVisible = windll.user32.IsWindowVisible
GetClassName = windll.user32.GetClassNameW

titles = []


def foreach_window(hwnd, notUsed):
    if IsWindowVisible(hwnd):
        length = GetWindowTextLength(hwnd)
        classname = create_unicode_buffer(100 + 1)
        GetClassName(hwnd, classname, 100 + 1)
        buff = create_unicode_buffer(length + 1)
        GetWindowText(hwnd, buff, length + 1)
        titles.append((hwnd, buff.value.encode, classname.value, windll.user32.IsIconic(hwnd)))
    return True


EnumWindows(EnumWindowsProc(foreach_window), 0)


def refresh_wins():
    del titles[:]
    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return titles


def find_window(title):
    newest_titles = refresh_wins()
    for item in newest_titles:
        if title in str(item[1]()):
            return item[0]
    return False

