# Sparking Zero Voice Studio — Edición portátil

## Instalación
1. Extrae todo el ZIP en una carpeta donde puedas escribir, como Documentos. No ejecutes la aplicación dentro del ZIP ni la instales en Program Files.
2. Abre `Sparking Zero Voice Studio.exe`. Python, las herramientas de audio, UnrealPak y Oodle están incluidos; no necesitas instalar Python, Codex ni Excel. `Preparar ferramentas.bat` realiza una comprobación opcional.
3. En Configuración, selecciona la carpeta de instalación del juego. Para Replacer, deja CustomProject y Custom Engine vacíos para leer las referencias del juego. La clave de los paquetes se configura automáticamente; no necesitas `keys.json`.
4. Guarda la configuración y abre un banco. Las instalaciones nuevas empiezan en inglés. Puedes cambiar el idioma antes de seleccionar carpetas. Conservar tu `settings.json` al actualizar mantiene tu idioma.

## Requisitos
- Windows 10 u 11 de 64 bits; .NET Framework 4.8 y el runtime Visual C++ de 64 bits compatible con las herramientas Unreal incluidas.
- DRAGON BALL Sparking! ZERO instalado, con los archivos `.pak`, `.utoc` y `.ucas` de la versión utilizada.
- **Custom Engine y CustomProject no están incluidos.** Exportar Custom requiere una Custom Engine Unreal 5.1 compatible con el plugin CriWare y sus DLL, y CustomProject con referencias de voz compatibles. Una instalación genérica de Unreal no basta.
- CustomProject es opcional para Replacer. Si se configura, proporciona las referencias; si no, se leen del juego y la caché se renueva cuando cambian los contenedores.

## Funciones principales
- Bancos US/JP, nombres oficiales por idioma, Cue IDs, funciones, etiquetas de interacción, filtros y voces repetidas; comparación del audio original y editado.
- Importación de audio, vídeo y paquetes externos; grabación con micrófono; recorte; ganancia, corrección de clipping y maximización de volumen.
- Mejora de voz, aislamiento del fondo y efectos locales: reverb, eco, pitch, graves/agudos, voz doble, distorsión y radio. Escucha la vista previa antes de aplicar; la calidad depende de la grabación.
- Velocidad de 0,25x a 3,00x, conservación del tono activada por defecto (se puede desactivar), vista previa y deshacer/rehacer. Conserva el tono para cambiar solo el ritmo.
- Guardado y recuperación, proyectos recientes, compartir/combinar, migración y copia por etiquetas/funciones. Ctrl+Z deshace; Ctrl+Y o Ctrl+Mayús+Z rehace. Interfaz y ayuda en 16 idiomas.
- Las voces externas confirmadas como idénticas al juego se consideran originales, no sustituciones. La reproducción externa se limita a diferencias confirmadas. Elige conservar el original o silenciar las voces sin sustituir.

## Exportaciones Replacer y Custom
**Replacer:** entrega `.pak`, `.utoc` y `.ucas` juntos en la carpeta del mod. El banco original determina el personaje sustituido; renombrar el proyecto o la carpeta no cambia ese objetivo. Un nombre de carpeta vacío usa el nombre oficial del personaje base en el idioma de la aplicación. Mantén instalado el mod del personaje personalizado: el paquete de voz no incluye el personaje. Al importar, conserva juntos los PAK/UTOC/UCAS relacionados. Replacer no inicia Unreal Editor.

**Custom:** entrega el `.uasset` en la carpeta del mod para Unreal y el `.pak` en la carpeta del mod para el juego, ambas con prefijo “Custom”; los intermediarios y los informes van a una carpeta de apoyo. Los nombres siguen el idioma de la aplicación. El nombre del proyecto debe coincidir exactamente con la carpeta del mod/plugin en `Plugins` de Unreal. El banco debe corresponder al ID personalizado y a US/JP. Selecciona CustomProject y Custom Engine en Configuración.

Las exportaciones se agrupan por número y nombre del proyecto. Cada versión empieza con un número creciente para que la última quede al final al ordenar por nombre. Abrir carpeta ofrece primero exports, después audio editado y proyectos; sin proyecto, abre la carpeta general de exports. Prueba siempre el resultado en el juego.

## Proyectos y copias de seguridad
Cierra la aplicación y haz una copia de la carpeta existente antes de actualizar. Extrae el nuevo ZIP en la misma instalación, combinando carpetas y reemplazando los archivos del programa. Conserva Projects, Cache, settings.json, preferencias, contadores y presets. Los archivos personales no se incluyen en el nuevo ZIP. No crees otra carpeta de la aplicación dentro de la anterior. Mantén la ubicación: los proyectos antiguos pueden contener rutas absolutas de audio. Se admiten proyectos antiguos sin los campos opcionales nuevos. Consulta UPDATE.md.

## Problemas y archivos incluidos
Ante acceso denegado, extrae en una carpeta con permiso de escritura, como Documentos. La apertura de carpetas reintenta con el Explorador de Windows; no pide administrador ni cambia permisos. Para errores Custom, consulta el `import.log` indicado y comprueba Engine/CriWare. Los assets deben corresponder al banco y versión previstos.

El paquete no incluye proyectos, grabaciones, exports, caché, assets del juego/referencias ni ajustes personales del autor. Incluye la clave estándar y las herramientas. Las licencias acompañan al runtime y las bibliotecas; los créditos de voz están en `Tools/VoiceAI/NOTICE.txt`. Para soporte, indica las versiones de la aplicación/juego, el banco, el modo y el log. Las pruebas técnicas locales no sustituyen las pruebas en el juego.
