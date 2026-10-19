"""Open existing folders through Windows Shell, with an Explorer fallback."""
import os,subprocess
from pathlib import Path

def open_folder(path):
    path=Path(path).resolve(strict=True)
    if not path.is_dir():raise NotADirectoryError(str(path))
    try:
        os.startfile(str(path))
    except OSError as shell_error:
        # Some PCs reject the default folder verb but allow Explorer directly.
        # No elevation, command shell, or change to filesystem permissions.
        if os.name!='nt':raise
        explorer=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'explorer.exe'
        if not explorer.is_file():raise shell_error
        try:subprocess.Popen([str(explorer),str(path)],close_fds=True)
        except OSError as error:raise error from shell_error
    return path
