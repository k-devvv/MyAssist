"""Windows hotkey and guarded Unicode input worker. Reads only configured shortcut state."""
import ctypes, json, queue, sys, threading, time
from ctypes import wintypes
user32=ctypes.WinDLL('user32',use_last_error=True)
MOD_CONTROL,MOD_SHIFT,MOD_ALT,MOD_WIN,MOD_NOREPEAT=0x0002,0x0004,0x0001,0x0008,0x4000
WM_HOTKEY=0x0312; HOTKEY_TALK=1; HOTKEY_TOGGLE=2; KEYEVENTF_KEYUP=0x0002; KEYEVENTF_UNICODE=0x0004
PM_REMOVE=0x0001; INPUT_KEYBOARD=1
class KEYBDINPUT(ctypes.Structure):
    _fields_=[('wVk',wintypes.WORD),('wScan',wintypes.WORD),('dwFlags',wintypes.DWORD),('time',wintypes.DWORD),('dwExtraInfo',ctypes.POINTER(ctypes.c_ulong))]
class MOUSEINPUT(ctypes.Structure):
    _fields_=[('dx',wintypes.LONG),('dy',wintypes.LONG),('mouseData',wintypes.DWORD),('dwFlags',wintypes.DWORD),('time',wintypes.DWORD),('dwExtraInfo',ctypes.POINTER(ctypes.c_ulong))]
class HARDWAREINPUT(ctypes.Structure):
    _fields_=[('uMsg',wintypes.DWORD),('wParamL',wintypes.WORD),('wParamH',wintypes.WORD)]
class INPUTUNION(ctypes.Union):
    _fields_=[('ki',KEYBDINPUT),('mi',MOUSEINPUT),('hi',HARDWAREINPUT)]
class INPUT(ctypes.Structure):
    _fields_=[('type',wintypes.DWORD),('union',INPUTUNION)]
# ctypes defaults Win32 return values to 32-bit integers. Explicit signatures
# preserve 64-bit HWND values and correctly marshal INPUT/MSG pointers.
user32.GetForegroundWindow.restype=wintypes.HWND
user32.GetForegroundWindow.argtypes=[]
user32.IsWindow.restype=wintypes.BOOL
user32.IsWindow.argtypes=[wintypes.HWND]
user32.GetAsyncKeyState.restype=wintypes.SHORT
user32.GetAsyncKeyState.argtypes=[ctypes.c_int]
user32.RegisterHotKey.restype=wintypes.BOOL
user32.RegisterHotKey.argtypes=[wintypes.HWND,ctypes.c_int,wintypes.UINT,wintypes.UINT]
user32.UnregisterHotKey.restype=wintypes.BOOL
user32.UnregisterHotKey.argtypes=[wintypes.HWND,ctypes.c_int]
user32.PeekMessageW.restype=wintypes.BOOL
user32.PeekMessageW.argtypes=[ctypes.POINTER(wintypes.MSG),wintypes.HWND,wintypes.UINT,wintypes.UINT,wintypes.UINT]
user32.TranslateMessage.restype=wintypes.BOOL
user32.TranslateMessage.argtypes=[ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype=ctypes.c_ssize_t
user32.DispatchMessageW.argtypes=[ctypes.POINTER(wintypes.MSG)]
user32.SendInput.restype=wintypes.UINT
user32.SendInput.argtypes=[wintypes.UINT,ctypes.POINTER(INPUT),ctypes.c_int]
def emit(action, **payload):
    sys.stdout.write(json.dumps({'action':action,**payload},separators=(',',':'))+'\n'); sys.stdout.flush()
def down(vk): return bool(user32.GetAsyncKeyState(vk)&0x8000)
def modifier_flags(virtual_keys):
    flags=MOD_NOREPEAT
    mapping={0x11:MOD_CONTROL,0x10:MOD_SHIFT,0x12:MOD_ALT,0x5B:MOD_WIN,0x5C:MOD_WIN}
    for vk in virtual_keys:
        if vk not in mapping: raise ValueError(f'Unsupported shortcut modifier: {vk}')
        flags|=mapping[vk]
    return flags
def read_commands(q):
    for line in sys.stdin:
        try: q.put(json.loads(line))
        except Exception: pass
def insert_text(target, text):
    hwnd=wintypes.HWND(int(target))
    if not user32.IsWindow(hwnd): emit('insert-failed',reason='target-closed'); return
    if int(user32.GetForegroundWindow() or 0)!=int(target): emit('insert-failed',reason='focus-changed'); return
    units=[]
    for char in str(text):
        value=ord(char)
        if value>0xFFFF:
            value-=0x10000; units.extend((0xD800+(value>>10),0xDC00+(value&0x3FF)))
        else: units.append(value)
    inputs=(INPUT*(len(units)*2))()
    for i,unit in enumerate(units):
        inputs[i*2].type=1; inputs[i*2].union.ki=KEYBDINPUT(0,unit,KEYEVENTF_UNICODE,0,None)
        inputs[i*2+1].type=1; inputs[i*2+1].union.ki=KEYBDINPUT(0,unit,KEYEVENTF_UNICODE|KEYEVENTF_KEYUP,0,None)
    sent=user32.SendInput(len(inputs),inputs,ctypes.sizeof(INPUT))
    emit('inserted' if sent==len(inputs) else 'insert-failed',**({} if sent==len(inputs) else {'reason':'windows-blocked'}))
def main():
    config=json.loads(sys.stdin.readline() or '{}')
    talk_vk=int(config.get('talkVk',0x20)); talk_mods=[int(v) for v in config.get('talkModifiers',[0x11,0x10])]
    toggle_vk=int(config.get('toggleVk',0x4D)); toggle_mods=[int(v) for v in config.get('toggleModifiers',[0x11,0x10])]
    cancel_vk=int(config.get('cancelVk',0x1B)); commands=queue.Queue(); threading.Thread(target=read_commands,args=(commands,),daemon=True).start()
    try:
        talk_flags=modifier_flags(talk_mods); toggle_flags=modifier_flags(toggle_mods)
    except ValueError as error: emit('worker-error',reason=str(error)); return 4
    if not user32.RegisterHotKey(None,HOTKEY_TALK,talk_flags,talk_vk):
        code=ctypes.get_last_error()
        emit('shortcut-conflict' if code==1409 else 'worker-error',shortcut='talk',windowsError=code)
        return 2 if code==1409 else 4
    if not user32.RegisterHotKey(None,HOTKEY_TOGGLE,toggle_flags|MOD_NOREPEAT,toggle_vk):
        code=ctypes.get_last_error(); user32.UnregisterHotKey(None,HOTKEY_TALK)
        emit('shortcut-conflict' if code==1409 else 'worker-error',shortcut='toggle',windowsError=code)
        return 3 if code==1409 else 4
    emit('ready'); msg=wintypes.MSG(); running=True
    try:
        while running:
            try:
                command=commands.get_nowait()
                if command.get('kind')=='insert': insert_text(command.get('target',0),command.get('text',''))
                elif command.get('kind')=='shutdown': running=False
            except queue.Empty: pass
            while user32.PeekMessageW(ctypes.byref(msg),None,0,0,PM_REMOVE):
                if msg.message==WM_HOTKEY and msg.wParam==HOTKEY_TOGGLE: emit('toggle')
                elif msg.message==WM_HOTKEY and msg.wParam==HOTKEY_TALK:
                    target=int(user32.GetForegroundWindow() or 0); emit('talk-start',target=target)
                    cancelled=False
                    while down(talk_vk) and all(down(v) for v in talk_mods):
                        if down(cancel_vk): cancelled=True; emit('talk-cancel'); break
                        time.sleep(.012)
                    emit('talk-end',target=target,cancelled=cancelled)
                user32.TranslateMessage(ctypes.byref(msg)); user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(.008)
    finally:
        user32.UnregisterHotKey(None,HOTKEY_TALK); user32.UnregisterHotKey(None,HOTKEY_TOGGLE)
    return 0
if __name__=='__main__': raise SystemExit(main())
