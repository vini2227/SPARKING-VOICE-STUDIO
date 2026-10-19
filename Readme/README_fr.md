# Sparking Zero Voice Studio — Édition portable

## Installation
1. Extrayez tout le ZIP dans un dossier accessible en écriture, par exemple Documents. Ne lancez pas l’application depuis le ZIP et ne l’installez pas dans Program Files.
2. Ouvrez `Sparking Zero Voice Studio.exe`. Python, les outils audio, UnrealPak et Oodle sont inclus ; aucune installation de Python, Codex ou Excel n’est nécessaire. `Preparar ferramentas.bat` est une vérification facultative.
3. Dans Paramètres, choisissez le dossier du jeu. Pour Replacer, laissez CustomProject et Custom Engine vides pour lire les références du jeu. La clé des paquets est configurée automatiquement ; `keys.json` n’est pas nécessaire.
4. Enregistrez et ouvrez une banque. Une nouvelle installation démarre en anglais. La langue peut être modifiée avant de choisir des dossiers. Conserver votre `settings.json` lors d’une mise à jour conserve votre langue.

## Configuration requise
- Windows 10 ou 11, 64 bits ; .NET Framework 4.8 et runtime Visual C++ 64 bits compatible avec les outils Unreal inclus.
- DRAGON BALL Sparking! ZERO installé, avec les fichiers `.pak`, `.utoc` et `.ucas` de votre version.
- **Custom Engine et CustomProject ne sont pas inclus.** L’export Custom exige une Custom Engine Unreal 5.1 compatible avec le plugin CriWare et ses DLL, ainsi que CustomProject avec des références vocales compatibles. Une installation Unreal générique ne suffit pas.
- CustomProject est facultatif pour Replacer. S’il est configuré, il fournit les références ; sinon, elles sont lues dans le jeu et le cache est actualisé quand les conteneurs changent.

## Principales fonctions
- Banques US/JP, noms officiels localisés, Cue IDs, fonctions, tags d’interaction, filtres et voix répétées ; comparaison originale/modifiée.
- Import audio, vidéo et paquets externes ; enregistrement au microphone ; découpe, gain, correction de l’écrêtage et maximisation du volume.
- Amélioration vocale, isolation du fond et effets locaux : réverbération, écho, hauteur, graves/aigus, double voix, distorsion et radio. Écoutez l’aperçu avant d’appliquer ; la qualité dépend de l’enregistrement.
- Vitesse de 0,25x à 3,00x, conservation de la hauteur activée par défaut (désactivable), aperçu et annulation/rétablissement. Conservez la hauteur pour modifier uniquement le tempo.
- Sauvegarde et récupération, projets récents, partage/fusion, migration et copie par tags/fonctions. Ctrl+Z annule ; Ctrl+Y ou Ctrl+Maj+Z rétablit. Interface et aide en 16 langues.
- Les voix externes confirmées identiques au jeu sont originales, pas des remplacements. Leur aperçu est limité aux différences confirmées. Choisissez l’audio original ou le silence pour les voix non remplacées.

## Exports Replacer et Custom
**Replacer :** réunit `.pak`, `.utoc` et `.ucas` dans le dossier du mod. La banque originale détermine le personnage remplacé ; renommer le projet ou le dossier ne change pas cette cible. Un nom de dossier vide utilise le nom officiel du personnage de base dans la langue de l’application. Gardez installé le mod d’un personnage personnalisé : le paquet vocal ne contient pas le personnage. Conservez ensemble les PAK/UTOC/UCAS associés lors de l’import. Replacer ne lance pas Unreal Editor.

**Custom :** place le `.uasset` dans le dossier du mod pour Unreal et le `.pak` dans celui pour le jeu, avec le préfixe « Custom » ; les fichiers intermédiaires et rapports vont dans un dossier de support. Les noms suivent la langue de l’application. Le nom du projet doit correspondre exactement au dossier du mod/plugin dans `Plugins` d’Unreal. La banque doit correspondre à l’ID personnalisé et à US/JP. Sélectionnez CustomProject et Custom Engine dans Paramètres.

Les exports sont regroupés par numéro et nom du projet. Chaque version commence par un numéro croissant pour que la plus récente apparaisse en dernier lors du tri par nom. Ouvrir dossier propose exports, audio modifié puis projets ; sans projet, il ouvre le dossier général des exports. Testez toujours dans le jeu.

## Projets et sauvegardes
Fermez l’application et sauvegardez le dossier avant la mise à jour. Extrayez le nouveau ZIP dans la même installation, fusionnez les dossiers et remplacez les fichiers du programme. Conservez Projects, Cache, settings.json, préférences, compteurs et préréglages : ils ne sont pas inclus dans le ZIP. Ne créez pas un dossier imbriqué supplémentaire. Gardez le même emplacement : les anciens projets peuvent contenir des chemins audio absolus. Les anciens projets sans les nouveaux champs facultatifs restent pris en charge. Voir UPDATE.md.

## Problèmes et fichiers inclus
En cas d’accès refusé, extrayez dans un dossier accessible en écriture, comme Documents. L’ouverture réessaie via l’Explorateur Windows ; elle ne demande pas de droits administrateur et ne modifie pas les autorisations. Pour les erreurs Custom, consultez le `import.log` indiqué et vérifiez Engine/CriWare. Les assets doivent correspondre à la banque et version visées.

Le paquet ne contient aucun projet, enregistrement, export, cache, asset du jeu/référence ou réglage personnel de l’auteur. La clé standard et les outils sont inclus. Les licences accompagnent le runtime et les bibliothèques ; crédits vocaux dans `Tools/VoiceAI/NOTICE.txt`. Pour l’assistance, indiquez versions de l’application/jeu, banque, mode et log. Les vérifications locales ne remplacent pas un test dans le jeu.
