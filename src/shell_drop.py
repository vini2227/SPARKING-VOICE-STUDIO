"""Native Windows file drops for a Tk widget; no external runtime package."""
import ctypes
from collections import deque
from ctypes import wintypes as w

WM_DROPFILES=0x0233
WM_NCDESTROY=0x0082
CALLBACK=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM,ctypes.c_size_t,ctypes.c_size_t)
shell=ctypes.WinDLL('shell32',use_last_error=True)
common=ctypes.WinDLL('comctl32',use_last_error=True)
shell.DragAcceptFiles.argtypes=[w.HWND,w.BOOL]
shell.DragAcceptFiles.restype=None
shell.DragQueryFileW.argtypes=[w.HANDLE,w.UINT,w.LPWSTR,w.UINT]
shell.DragQueryFileW.restype=w.UINT
shell.DragFinish.argtypes=[w.HANDLE]
shell.DragFinish.restype=None
common.SetWindowSubclass.argtypes=[w.HWND,CALLBACK,ctypes.c_size_t,ctypes.c_size_t]
common.SetWindowSubclass.restype=w.BOOL
common.RemoveWindowSubclass.argtypes=[w.HWND,CALLBACK,ctypes.c_size_t]
common.RemoveWindowSubclass.restype=w.BOOL
common.DefSubclassProc.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
common.DefSubclassProc.restype=ctypes.c_ssize_t

class FileDrop:
    def __init__(self,widget,on_drop):
        self.widget=widget;self.on_drop=on_drop;self.hwnd=widget.winfo_id()
        self.callback=CALLBACK(self._message);self.token=id(self)
        self.active=False;self.pending=deque();self.poll_after=None
        if not common.SetWindowSubclass(self.hwnd,self.callback,self.token,0):
            raise OSError('Could not register file drop target')
        self.active=True
        shell.DragAcceptFiles(self.hwnd,True)
        widget.bind('<Destroy>',self._destroy,add='+')
        self.poll_after=widget.after(50,self._poll)

    def _message(self,hwnd,message,wp,lp,token,data):
        if message==WM_DROPFILES:
            paths=[]
            try:
                for index in range(shell.DragQueryFileW(wp,0xffffffff,None,0)):
                    length=shell.DragQueryFileW(wp,index,None,0)
                    buffer=ctypes.create_unicode_buffer(length+1)
                    shell.DragQueryFileW(wp,index,buffer,length+1)
                    paths.append(buffer.value)
            finally:
                shell.DragFinish(wp)
            # Never call Tk/Tcl from a native callback. During mainloop this
            # callback can run while _tkinter has released its thread state.
            self.pending.append(paths)
            return 0
        if message==WM_NCDESTROY:
            self.active=False
            common.RemoveWindowSubclass(hwnd,self.callback,self.token)
        return common.DefSubclassProc(hwnd,message,wp,lp)

    def _destroy(self,event):
        if event.widget is self.widget:self.close()

    def _poll(self):
        self.poll_after=None
        if not self.active:return
        try:
            while self.pending and self.active:self.on_drop(self.pending.popleft())
        finally:
            if self.active:self.poll_after=self.widget.after(50,self._poll)

    def close(self):
        if self.active:
            self.active=False
            shell.DragAcceptFiles(self.hwnd,False)
            common.RemoveWindowSubclass(self.hwnd,self.callback,self.token)
        if self.poll_after:
            self.widget.after_cancel(self.poll_after);self.poll_after=None
        self.pending.clear()
