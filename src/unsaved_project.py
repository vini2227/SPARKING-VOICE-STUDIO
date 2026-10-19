import support_report
"""Explicit project saves and confirmation before leaving unsaved edits."""
import json
import ui_reliability
import trim_history
import tkinter as tk
from tkinter import messagebox
from modern_theme import BG, FG, MUTED


class UnsavedProjectMixin:
    def project_edit_snapshot(self):
        return json.dumps({"replacements": self.replacements, "gains": self.gains,
            "variations": self.variations, "trim_originals": trim_history.active(self.trim_originals,self.replacements), "processing_originals": trim_history.active(self.processing_originals,self.replacements), "effects_originals": trim_history.active(self.effects_originals,self.replacements), "speed_originals": trim_history.active(self.speed_originals,self.replacements), "duplicate_originals": trim_history.active(self.duplicate_originals,self.replacements), "keep_imported": self.keep_imported.get(),
            "export_name": self.export_name.get().strip(), "project_name": self.project_name}, sort_keys=True)

    def has_unsaved_changes(self):
        return bool(self.bank and self.project and self._saved_project_snapshot is not None
                    and self.project_edit_snapshot() != self._saved_project_snapshot)

    def ask_unsaved_changes(self):
        previous_grab=self.grab_current()
        # Transient dialogs can remain hidden while their parent is minimized.
        if self.state()=='iconic':
            self.deiconify()
            self.update_idletasks()
        win = tk.Toplevel(self)
        win.title(self.tr("Alterações não salvas"))
        win.configure(bg=BG)
        win.transient(self)
        win.resizable(False, False)
        result = ["cancel"]
        ui_reliability.event("unsaved_dialog_opened")
        def choose(value):
            ui_reliability.event("unsaved_dialog_choice",choice=value)
            result[0] = value
            win.destroy()
        tk.Label(win, text=self.tr("Salvar as alterações do projeto?"), bg=BG, fg=FG,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=24, pady=(24, 10))
        tk.Label(win, text=self.project_name, bg=BG, fg=MUTED,
                 wraplength=460, justify="left").pack(anchor="w", padx=24)
        tk.Label(win, text=self.tr("Não salvar mantém a última versão salva."),
                 bg=BG, fg=MUTED).pack(anchor="w", padx=24, pady=(8, 18))
        buttons = tk.Frame(win, bg=BG)
        buttons.pack(fill="x", padx=24, pady=(0, 24))
        self.button(buttons, "Salvar", lambda: choose("save"), True).pack(side="left", padx=(0, 8))
        self.button(buttons, "Não salvar", lambda: choose("discard")).pack(side="left", padx=(0, 8))
        self.button(buttons, "Cancelar", lambda: choose("cancel")).pack(side="left")
        win.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))
        win.bind("<Escape>", lambda event: choose("cancel"))
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_reqwidth()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - win.winfo_reqheight()) // 2
        win.geometry(f"+{max(0,x)}+{max(0,y)}")
        win.wait_visibility()
        win.lift()
        win.grab_set()
        win.focus_set()
        self.wait_window(win)
        if result[0]=='cancel' and previous_grab is not None:
            try:
                if previous_grab.winfo_exists() and previous_grab.winfo_viewable():
                    previous_grab.grab_set();previous_grab.focus_set()
            except tk.TclError:pass
        ui_reliability.event("unsaved_dialog_closed",choice=result[0])
        return result[0]

    def confirm_leaving_project(self):
        if not self.has_unsaved_changes():
            return True
        choice = self.ask_unsaved_changes()
        if choice == "cancel":
            return False
        if choice == "save":
            try:
                self.save_project(False, force=True)
            except Exception as error:
                support_report.show(self,str(error),parent=self,title=self.tr('Falha ao salvar projeto'))
                return False
        return True
