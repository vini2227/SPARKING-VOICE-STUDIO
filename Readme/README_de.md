# Sparking Zero Voice Studio — Portable Ausgabe

## Installation
1. Entpacke die gesamte ZIP in einen beschreibbaren Ordner, zum Beispiel Dokumente. Starte die App nicht in der ZIP und installiere sie nicht in Program Files.
2. Öffne `Sparking Zero Voice Studio.exe`. Python, Audiowerkzeuge, UnrealPak und Oodle sind enthalten; Python, Codex oder Excel müssen nicht separat installiert werden. `Preparar ferramentas.bat` prüft die Werkzeuge optional.
3. Wähle in den Einstellungen den Installationsordner des Spiels. Für Replacer bleiben CustomProject und Custom Engine leer, um Referenzen direkt aus dem Spiel zu lesen. Der Paketschlüssel wird automatisch eingerichtet; `keys.json` ist nicht nötig.
4. Speichere und öffne eine Sprachbank. Neue Installationen starten auf Englisch. Die Sprache lässt sich auch vor der Ordnerauswahl ändern. Bei Updates mit deiner bisherigen `settings.json` bleibt deine Sprachauswahl erhalten.

## Voraussetzungen
- Windows 10 oder 11, 64 Bit; .NET Framework 4.8 und eine mit den enthaltenen Unreal-Werkzeugen kompatible Visual-C++-Laufzeit für 64 Bit.
- Installiertes DRAGON BALL Sparking! ZERO mit `.pak`, `.utoc` und `.ucas` deiner Spielversion.
- **Custom Engine und CustomProject sind nicht enthalten.** Custom-Export benötigt eine kompatible Unreal-5.1-Custom-Engine mit CriWare-Plugin und dessen DLLs sowie CustomProject mit passenden Sprachreferenzen. Eine gewöhnliche Unreal-Installation reicht nicht aus.
- CustomProject ist für Replacer optional. Wenn eingerichtet, liefert es Referenzen; sonst liest die App sie aus dem Spiel und erneuert den Cache bei geänderten Containern.

## Hauptfunktionen
- US/JP-Banken, offizielle lokalisierte Figurennamen, Cue IDs, Funktionen, Interaktions-Tags, Filter und wiederholte Stimmen; Original/bearbeitet vergleichen.
- Audio, Video und externe Sprachpakete importieren; Mikrofonaufnahme; Zuschneiden, Verstärkung, Clipping-Korrektur und Lautstärkemaximierung.
- Lokale Sprachverbesserung, Hintergrundisolierung und Effekte: Hall, Echo, Tonhöhe, Bässe/Höhen, Doppelstimme, Verzerrung und Radio. Vorschau vor dem Anwenden anhören; die Qualität hängt von der Aufnahme ab.
- Geschwindigkeit 0,25x bis 3,00x, standardmäßig aktivierte Tonhöhenerhaltung (abschaltbar), Vorschau und Rückgängig/Wiederholen. Tonhöhe erhalten, um nur das Tempo zu ändern.
- Speichern und Wiederherstellen, zuletzt verwendete Projekte, Teilen/Zusammenführen, Bankmigration und Kopieren nach Tags/Funktionen. Ctrl+Z macht rückgängig; Ctrl+Y oder Ctrl+Shift+Z wiederholt. Oberfläche und Hilfe in 16 Sprachen.
- Externe Stimmen, die nachweislich mit dem Spiel identisch sind, gelten als Originale statt Ersetzungen. Externe Vorschau ist auf bestätigte Unterschiede begrenzt. Nicht ersetzte Stimmen können original bleiben oder stumm werden.

## Replacer- und Custom-Exports
**Replacer:** liefert `.pak`, `.utoc` und `.ucas` gemeinsam im Modordner. Die Originalbank bestimmt die ersetzte Figur; Umbenennen von Projekt oder Ordner ändert dieses Ziel nicht. Ein leerer Replacer-Ordnername verwendet den offiziellen Namen der Basisfigur in der App-Sprache. Der Mod einer eigenen Figur muss installiert bleiben: Das Sprachpaket enthält die Figur nicht. Zusammengehörige PAK/UTOC/UCAS beim Import zusammenlassen. Replacer startet Unreal Editor nicht.

**Custom:** legt `.uasset` in den Unreal-Modordner und `.pak` in den Spiel-Modordner, jeweils mit Präfix „Custom“; Zwischendateien und Berichte kommen in einen Hilfsordner. Ordnernamen folgen der App-Sprache. Der Projektname muss exakt dem Mod/Plugin-Ordner unter `Plugins` in Unreal entsprechen. Die Bank muss zur eigenen Figuren-ID und zu US/JP passen. CustomProject und Custom Engine in Einstellungen auswählen.

Exports werden nach Projektnummer und -name gruppiert. Jede Version beginnt mit einer aufsteigenden Nummer, sodass die neueste bei Namenssortierung zuletzt steht. Ordner öffnen bietet Exports, bearbeitetes Audio und Projekte; ohne Projekt öffnet es den allgemeinen Exportordner. Immer im Spiel testen.

## Projekte und Sicherungen
Schließen Sie die App und sichern Sie den vorhandenen Ordner vor dem Update. Entpacken Sie das neue ZIP in dieselbe Installation, führen Sie Ordner zusammen und ersetzen Sie Programmdateien. Projects, Cache, settings.json, Einstellungen, Zähler und Presets bleiben erhalten; sie sind nicht im ZIP enthalten. Keinen zusätzlichen App-Unterordner anlegen. Den Installationsort beibehalten: ältere Projekte können absolute Audiopfade enthalten. Alte Projekte ohne neue optionale Felder werden weiterhin unterstützt. Siehe UPDATE.md.

## Probleme und enthaltene Dateien
Bei Zugriff verweigert in einen beschreibbaren Ordner wie Dokumente entpacken. Das Öffnen versucht alternativ Windows Explorer; es fordert keine Administratorrechte und ändert keine Windows-Berechtigungen. Bei Custom-Fehlern die angezeigte `import.log` und Engine/CriWare prüfen. Assets müssen zur vorgesehenen Bank und Spielversion passen.

Keine persönlichen Projekte, Aufnahmen, Exports, Caches, Spiel-/Referenzassets oder Autoreneinstellungen sind enthalten. Standardschlüssel und Werkzeuge sind enthalten. Lizenzen liegen bei Laufzeit und Bibliotheken; Sprach-Credits unter `Tools/VoiceAI/NOTICE.txt`. Beim Support App-/Spielversion, Bank, Modus und Log angeben. Lokale technische Prüfungen ersetzen keinen Spieltest.
