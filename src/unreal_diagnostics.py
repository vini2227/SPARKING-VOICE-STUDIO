"""Select Unreal failure causes without drowning them in the Windows stack."""
import re

def failure_details(log,limit=1800):
    lines=log.splitlines();selected=[]
    def stack(line):
        return ('[Callstack]' in line or 'UnknownFunction' in line
                or re.search(r'LogWindows: Error:\s*$',line)
                or re.search(r'LogWindows: Error:\s*0x[0-9a-f]+',line,re.I))
    for index,line in enumerate(lines):
        if stack(line):continue
        if any(token in line for token in (': Error:', 'Fatal error', 'Assertion failed', 'Unhandled Exception', 'LogModuleManager: Warning')):
            selected.append(line)
            # Fatal/exception reasons may be printed on the following unprefixed lines.
            if any(token in line for token in ('Fatal error','Assertion failed','Unhandled Exception')):
                for following in lines[index+1:index+5]:
                    if following.strip() and not stack(following):selected.append(following)
    selected=list(dict.fromkeys(selected))
    if not selected:
        selected=[line for line in lines if line.strip() and not stack(line)][-5:]
    if len(selected)>8:selected=selected[:4]+selected[-4:]
    # Keep the beginning (usually the cause), rather than truncating to the stack tail.
    return '\n'.join(selected)[:limit]
