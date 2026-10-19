# Sparking Zero Voice Studio — Wersja przenośna

## Instalacja
1. Rozpakuj cały ZIP do folderu z prawem zapisu, np. Dokumenty. Nie uruchamiaj aplikacji wewnątrz ZIP ani nie instaluj w Program Files.
2. Otwórz `Sparking Zero Voice Studio.exe`. Python, narzędzia audio, UnrealPak i Oodle są dołączone; nie musisz instalować Python, Codex ani Excel. `Preparar ferramentas.bat` to opcjonalna kontrola narzędzi.
3. W Ustawieniach wybierz folder gry. Dla Replacer pozostaw CustomProject i Custom Engine puste, aby odczytywać wzorce z gry. Klucz pakietów jest ustawiony automatycznie; `keys.json` nie jest potrzebny.
4. Zapisz i otwórz bank głosów. Nowa instalacja uruchamia się po angielsku. Język można zmienić przed wyborem folderów. Aktualizacja z dotychczasowym `settings.json` zachowuje wybrany język.

## Wymagania
- Windows 10 lub 11, 64-bitowy; .NET Framework 4.8 oraz 64-bitowe biblioteki Visual C++ zgodne z dołączonymi narzędziami Unreal.
- Zainstalowane DRAGON BALL Sparking! ZERO z plikami `.pak`, `.utoc` i `.ucas` używanej wersji gry.
- **Custom Engine i CustomProject nie są dołączone.** Eksport Custom wymaga zgodnego Custom Engine Unreal 5.1 z wtyczką CriWare i jej DLL oraz CustomProject ze zgodnymi wzorcami głosów. Zwykła instalacja Unreal nie wystarcza.
- CustomProject jest opcjonalny dla Replacer. Jeśli go ustawisz, dostarcza wzorce; inaczej aplikacja czyta je z gry i odświeża pamięć podręczną po zmianie kontenerów.

## Główne funkcje
- Banki US/JP, oficjalne lokalizowane nazwy postaci, Cue IDs, funkcje, tagi interakcji, filtry i powtarzające się głosy; porównanie oryginału i edycji.
- Import audio, wideo i zewnętrznych pakietów; nagrywanie mikrofonem; przycinanie, wzmocnienie, korekcja clippingu i maksymalizacja głośności.
- Lokalne ulepszanie głosu, izolacja tła i efekty: pogłos, echo, wysokość tonu, bas/soprany, podwójny głos, zniekształcenie i radio. Odsłuchaj przed zastosowaniem; jakość zależy od nagrania.
- Prędkość 0,25x–3,00x, domyślnie włączone zachowanie wysokości tonu (można wyłączyć), odsłuch i cofanie/ponawianie. Zachowaj wysokość tonu, aby zmienić tylko tempo.
- Zapis i odzyskiwanie, ostatnie projekty, udostępnianie/łączenie, migracja banków i kopiowanie według tagów/funkcji. Ctrl+Z cofa; Ctrl+Y lub Ctrl+Shift+Z ponawia. Interfejs i pomoc w 16 językach.
- Zewnętrzne głosy potwierdzone jako identyczne z grą są oryginałami, nie zamiennikami. Ich odsłuch jest ograniczony do potwierdzonych różnic. Niezastąpione głosy mogą pozostać oryginalne lub zostać wyciszone.

## Eksport Replacer i Custom
**Replacer:** umieszcza `.pak`, `.utoc` i `.ucas` razem w folderze moda. Oryginalny bank określa zastępowaną postać; zmiana nazwy projektu lub folderu nie zmienia celu. Pusta nazwa folderu używa oficjalnej nazwy bazowej postaci w języku aplikacji. Zachowaj zainstalowany mod własnej postaci: pakiet głosowy nie zawiera postaci. Przy imporcie trzymaj powiązane PAK/UTOC/UCAS razem. Replacer nie uruchamia Unreal Editor.

**Custom:** umieszcza `.uasset` w folderze moda dla Unreal i `.pak` w folderze moda dla gry, z przedrostkiem „Custom”; pliki pośrednie i raporty trafiają do folderu pomocniczego. Nazwy odpowiadają językowi aplikacji. Nazwa projektu musi dokładnie odpowiadać folderowi moda/wtyczki w `Plugins` Unreal. Bank musi odpowiadać ID własnej postaci i US/JP. W Ustawieniach wybierz CustomProject i Custom Engine.

Eksporty grupowane są według numeru i nazwy projektu. Każda wersja zaczyna się od rosnącego numeru, dzięki czemu najnowsza jest ostatnia przy sortowaniu po nazwie. Otwórz folder oferuje eksporty, edytowane audio i projekty; bez projektu otwiera ogólny folder eksportów. Zawsze testuj w grze.

## Projekty i kopie zapasowe
Przed aktualizacją zamknij aplikację i wykonaj kopię folderu. Rozpakuj nowy ZIP w tej samej instalacji, scalając foldery i zastępując pliki programu. Zachowaj Projects, Cache, settings.json, preferencje, liczniki i presety: nie są dołączane do ZIP-a. Nie twórz dodatkowego zagnieżdżonego folderu aplikacji. Zachowaj lokalizację: stare projekty mogą zawierać bezwzględne ścieżki audio. Starsze projekty bez nowych pól opcjonalnych są obsługiwane. Zobacz UPDATE.md.

## Problemy i zawartość
Przy odmowie dostępu rozpakuj do zapisywalnego folderu, np. Dokumenty. Otwieranie ponawia próbę przez Eksplorator Windows; nie żąda administratora ani nie zmienia uprawnień. Przy błędach Custom sprawdź wskazany `import.log` i Engine/CriWare. Assets muszą odpowiadać zamierzonemu bankowi i wersji.

Pakiet nie zawiera prywatnych projektów, nagrań, eksportów, pamięci podręcznej, assets gry/wzorców ani ustawień autora. Standardowy klucz i narzędzia są dołączone. Licencje towarzyszą środowisku i bibliotekom; informacje o silnikach głosowych: `Tools/VoiceAI/NOTICE.txt`. Przy wsparciu podaj wersje aplikacji/gry, bank, tryb i log. Kontrole lokalne nie zastępują testów w grze.
