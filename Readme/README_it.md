# Sparking Zero Voice Studio — Edizione portatile

## Installazione
1. Estrai tutto lo ZIP in una cartella scrivibile, come Documenti. Non avviare l’app nello ZIP e non installarla in Program Files.
2. Apri `Sparking Zero Voice Studio.exe`. Python, strumenti audio, UnrealPak e Oodle sono inclusi; non devi installare Python, Codex o Excel. `Preparar ferramentas.bat` è un controllo facoltativo.
3. Nelle Impostazioni, seleziona la cartella del gioco. Per Replacer, lascia vuoti CustomProject e Custom Engine per leggere i riferimenti dal gioco. La chiave dei pacchetti è configurata automaticamente; non serve `keys.json`.
4. Salva e apri un banco. Le nuove installazioni partono in inglese. Puoi cambiare lingua prima di selezionare cartelle. Conservando `settings.json` durante l’aggiornamento mantieni la lingua scelta.

## Requisiti
- Windows 10 o 11 a 64 bit; .NET Framework 4.8 e runtime Visual C++ a 64 bit compatibile con gli strumenti Unreal inclusi.
- DRAGON BALL Sparking! ZERO installato, con `.pak`, `.utoc` e `.ucas` della versione utilizzata.
- **Custom Engine e CustomProject non sono inclusi.** L’export Custom richiede una Custom Engine Unreal 5.1 compatibile con plugin CriWare e relative DLL, più CustomProject con riferimenti vocali compatibili. Un’installazione Unreal generica non basta.
- CustomProject è facoltativo per Replacer. Se configurato fornisce i riferimenti; altrimenti l’app legge il gioco e aggiorna la cache quando cambiano i contenitori.

## Funzioni principali
- Banchi US/JP, nomi ufficiali localizzati, Cue IDs, funzioni, tag d’interazione, filtri e voci ripetute; confronto originale/modificato.
- Importazione audio, video e pacchetti esterni; registrazione al microfono; taglio, guadagno, correzione clipping e massimizzazione del volume.
- Miglioramento voce, isolamento del fondo ed effetti locali: riverbero, eco, pitch, bassi/alti, doppia voce, distorsione e radio. Ascolta l’anteprima prima di applicare; la qualità dipende dalla registrazione.
- Velocità da 0,25x a 3,00x, conservazione del tono attiva per impostazione predefinita (disattivabile), anteprima e annulla/ripristina. Mantieni il tono per cambiare solo il ritmo.
- Salvataggio e recupero, progetti recenti, condivisione/unione, migrazione e copia per tag/funzioni. Ctrl+Z annulla; Ctrl+Y o Ctrl+Maiusc+Z ripristina. Interfaccia e guida in 16 lingue.
- Le voci esterne confermate identiche al gioco sono originali, non sostituzioni. L’anteprima esterna è limitata alle differenze confermate. Scegli l’originale o il silenzio per le voci non sostituite.

## Esportazioni Replacer e Custom
**Replacer:** raccoglie `.pak`, `.utoc` e `.ucas` nella cartella del mod. Il banco originale determina il personaggio sostituito; rinominare progetto o cartella non cambia il bersaglio. Il nome della cartella vuoto usa quello ufficiale del personaggio base nella lingua dell’app. Mantieni installato il mod del personaggio personalizzato: il pacchetto vocale non include il personaggio. Importa insieme i PAK/UTOC/UCAS collegati. Replacer non avvia Unreal Editor.

**Custom:** colloca `.uasset` nella cartella del mod per Unreal e `.pak` in quella per il gioco, con prefisso “Custom”; intermedi e rapporti vanno in una cartella di supporto. I nomi seguono la lingua dell’app. Il nome del progetto deve coincidere esattamente con la cartella del mod/plugin in `Plugins` di Unreal. Il banco deve corrispondere all’ID personalizzato e a US/JP. Seleziona CustomProject e Custom Engine nelle Impostazioni.

Gli export sono raggruppati per numero e nome del progetto. Ogni versione inizia con un numero crescente, così la più recente è ultima ordinando per nome. Apri cartella propone export, audio modificato e progetti; senza progetto apre la cartella generale degli export. Verifica sempre nel gioco.

## Progetti e backup
Chiudi l’app e salva una copia della cartella prima di aggiornare. Estrai il nuovo ZIP nella stessa installazione, unendo le cartelle e sostituendo i file del programma. Conserva Projects, Cache, settings.json, preferenze, contatori e preset: non sono inclusi nel nuovo ZIP. Non creare un’altra cartella dell’app dentro quella esistente. Mantieni la posizione: i vecchi progetti possono contenere percorsi audio assoluti. Sono supportati i vecchi progetti senza i nuovi campi facoltativi. Consulta UPDATE.md.

## Problemi e file inclusi
Per accesso negato, estrai in una cartella scrivibile, come Documenti. L’apertura riprova con Esplora file; non richiede amministratore e non cambia i permessi di Windows. Per errori Custom, consulta `import.log` indicato e verifica Engine/CriWare. Gli asset devono corrispondere al banco e alla versione previsti.

Il pacchetto non include progetti personali, registrazioni, export, cache, asset del gioco/riferimenti o impostazioni dell’autore. Chiave standard e strumenti sono inclusi. Le licenze accompagnano runtime e librerie; crediti vocali in `Tools/VoiceAI/NOTICE.txt`. Per assistenza indica versioni dell’app/gioco, banco, modalità e log. I controlli locali non sostituiscono una prova nel gioco.
