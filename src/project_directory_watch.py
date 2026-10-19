"""Read-only project monitoring; filesystem work never runs on the Tk thread."""
import queue
import threading


def directory_signature(root):
    records=[]
    for file in root.glob('*/project.json'):
        try:
            stat=file.stat()
            records.append((str(file),stat.st_mtime_ns,stat.st_size))
        except FileNotFoundError:
            continue
    return tuple(sorted(records))


class ProjectDirectoryWatch:
    def __init__(self,window,root,scan,loaded,interval=1.0):
        self.window=window
        self.root=root
        self.scan=scan
        self.loaded=loaded
        self.interval=interval
        self.stopped=threading.Event()
        self.wake=threading.Event()
        self.results=queue.Queue(maxsize=1)
        self.timer=window.after(100,self._deliver)
        self.thread=threading.Thread(target=self._work,daemon=True)
        self.thread.start()

    def refresh(self):
        self.wake.set()

    def _work(self):
        previous=None
        while not self.stopped.is_set():
            self.wake.clear()
            try:
                signature=directory_signature(self.root)
                if signature!=previous:
                    result=self.scan()
                    # Retry changes made during the scan instead of publishing stale rows.
                    if signature==directory_signature(self.root):
                        previous=signature
                        if not self.stopped.is_set():
                            try:self.results.get_nowait()
                            except queue.Empty:pass
                            self.results.put_nowait(result)
            except OSError:
                # Transient access errors must not erase the displayed list.
                pass
            self.wake.wait(self.interval)

    def _deliver(self):
        self.timer=None
        if self.stopped.is_set():return
        try:result=self.results.get_nowait()
        except queue.Empty:pass
        else:self.loaded(result)
        if not self.stopped.is_set():
            self.timer=self.window.after(100,self._deliver)

    def close(self):
        self.stopped.set()
        self.wake.set()
        if self.timer is not None:
            self.window.after_cancel(self.timer)
            self.timer=None
