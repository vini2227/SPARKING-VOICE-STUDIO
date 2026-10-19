"""One click switches the reviewed before/after previews; applying stays explicit."""
import voice_effects,core,playback_controls

def setup(dialog,parent):
    dialog.compare_after=False
    dialog.compare_btn=dialog.owner.button(parent,'Alternar Antes/Depois',lambda:toggle(dialog))
    dialog.compare_btn.pack(side='left',padx=10);dialog.compare_btn.configure(state='disabled')

def toggle(dialog):
    if dialog.pending or not dialog.current() or not dialog.result:return
    active=getattr(dialog.owner,'_active_play_button',None)
    after=False if active is dialog.after_btn else True if active is dialog.before_btn else not dialog.compare_after
    dialog.compare_after=after;dialog.listen(after)

def listen(dialog,after):
    if dialog.pending or not dialog.current() or (after and not dialog.result):return
    owner=dialog.owner;dest=dialog.folder/('after_preview.wav' if after else 'before_preview.wav')
    button=dialog.after_btn if after else dialog.before_btn
    def work():
        source=dialog.result if after else (dialog.source or dialog.bank.original(dialog.row))
        gain=voice_effects.safe_gain(source,dialog.row,dialog.gain,dialog.variation)
        core.normalize_wav(source,dest,dialog.row['rate'],dialog.row['channels'],dialog.row['samples'],gain,dialog.variation)
        return dest,gain
    def done(result):
        dialog.compare_after=after;playback_controls.start(owner,result[0],button)
        text=owner.tr('Ouvir depois' if after else 'Ouvir antes')
        if result[1]<dialog.gain:text+=' • '+owner.tr('Ganho ajustado automaticamente para evitar clipping: ')+f'{result[1]:.1f} dB'
        dialog.info.set(text)
    owner.stop();dialog.job(work,done,'Preparando prévia com volume ajustado...')
