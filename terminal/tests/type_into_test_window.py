"""Optional real X11 key-path test; targets only our exact verification window."""
import ctypes as c
import time
import sys

x = c.CDLL('libX11.so.6')
t = c.CDLL('libXtst.so.6')
x.XOpenDisplay.argtypes = [c.c_char_p]
x.XOpenDisplay.restype = c.c_void_p
x.XDefaultRootWindow.argtypes = [c.c_void_p]
x.XDefaultRootWindow.restype = c.c_ulong
x.XQueryTree.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_ulong), c.POINTER(c.c_ulong), c.POINTER(c.POINTER(c.c_ulong)), c.POINTER(c.c_uint)]
x.XFetchName.argtypes = [c.c_void_p, c.c_ulong, c.POINTER(c.c_char_p)]
x.XFree.argtypes = [c.c_void_p]
x.XSetInputFocus.argtypes = [c.c_void_p, c.c_ulong, c.c_int, c.c_ulong]
x.XGetInputFocus.argtypes = [c.c_void_p, c.POINTER(c.c_ulong), c.POINTER(c.c_int)]
x.XStringToKeysym.argtypes = [c.c_char_p]
x.XStringToKeysym.restype = c.c_ulong
x.XKeysymToKeycode.argtypes = [c.c_void_p, c.c_ulong]
x.XKeysymToKeycode.restype = c.c_uint
x.XSync.argtypes = [c.c_void_p, c.c_int]
x.XCloseDisplay.argtypes = [c.c_void_p]
t.XTestFakeKeyEvent.argtypes = [c.c_void_p, c.c_uint, c.c_int, c.c_ulong]
d = x.XOpenDisplay(None)
assert d, 'X11 test requires DISPLAY and GDK_BACKEND=x11'

def find_window(window):
    name = c.c_char_p()
    if x.XFetchName(d, window, c.byref(name)) and name:
        title = 'cAIman Terminal · verification'
        match = name.value in (title.encode('utf-8'), title.encode('latin-1'))
        x.XFree(name)
        if match:
            return window
    root, parent, count = c.c_ulong(), c.c_ulong(), c.c_uint()
    children = c.POINTER(c.c_ulong)()
    if x.XQueryTree(d, window, c.byref(root), c.byref(parent), c.byref(children), c.byref(count)):
        ids = list(children[:count.value])
        if children:
            x.XFree(children)
        for child in ids:
            found = find_window(child)
            if found:
                return found
    return None

window = find_window(x.XDefaultRootWindow(d))
assert window, 'Verification window not found; no keys sent'
x.XSetInputFocus(d, window, 2, 0)
x.XSync(d, 0)
focus, revert = c.c_ulong(), c.c_int()
x.XGetInputFocus(d, c.byref(focus), c.byref(revert))
assert focus.value == window, 'Verification window not focused; no keys sent'
text = sys.argv[1] if len(sys.argv) == 2 else 'find'
assert text in ('find', 'ps -'), 'Only fixed test inputs are allowed'
for char in text:
    key = x.XKeysymToKeycode(d, x.XStringToKeysym({' ': b'space', '-': b'minus'}.get(char, char.encode())))
    assert key
    t.XTestFakeKeyEvent(d, key, 1, 0)
    t.XTestFakeKeyEvent(d, key, 0, 0)
    x.XSync(d, 0)
    time.sleep(.02)
x.XCloseDisplay(d)
