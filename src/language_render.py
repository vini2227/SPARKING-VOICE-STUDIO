"""Display-only Arabic shaping; source strings and project data remain logical Unicode."""
import sys,re
from pathlib import Path
dependency=Path(__file__).resolve().parents[1]/'Tools/PythonDeps'
if str(dependency) not in sys.path:sys.path.insert(0,str(dependency))
import arabic_reshaper
from bidi.algorithm import get_display

def display(text,language,measure=None,width=None):
    text=str(text)
    if language!='ar' or not re.search('[\u0600-\u06ff]',text):return text
    paragraphs=[]
    for paragraph in text.split('\n'):
        if measure and width:
            lines=[];line=''
            for word in paragraph.split():
                candidate=(line+' '+word).strip()
                if line and measure(arabic_reshaper.reshape(candidate))>width:lines.append(line);line=word
                else:line=candidate
            lines.append(line)
        else:lines=[paragraph]
        for line in lines:
            shaped=arabic_reshaper.reshape(line)
            # Keep Python format fields as complete LTR runs inside Arabic text.
            shaped=re.sub(r'\{[^{}]+\}',lambda match:'\u202a'+match.group()+'\u202c',shaped)
            paragraphs.append(get_display(shaped))
    return '\n'.join(paragraphs)
