"""Interface translations; game identifiers and function tags are never translated."""
import tkinter as tk
import json
from pathlib import Path

from language_render import display as render_text

LANGUAGES={"en":"English","pt":"Português (Brasil)","es":"Español (España)","es-419":"Español (Latinoamérica)","fr":"Français","it":"Italiano","ja":"日本語","de":"Deutsch","ru":"Русский","pl":"Polski","ar":render_text("العربية","ar"),"zh-Hans":"简体中文","zh-Hant":"繁體中文","ko":"한국어","th":"ไทย","id":"Bahasa Indonesia"}
DATA=r"""
Mostrar ajustes e detalhes|Show adjustments and details|Mostrar ajustes y detalles
Ocultar ajustes e detalhes|Hide adjustments and details|Ocultar ajustes y detalles
Todos os tipos|All types|Todos los tipos
Funções sem interações|Functions without interactions|Funciones sin interacciones
Somente interações|Interactions only|Solo interacciones
Somente emotes|Emotes only|Solo emotes
Contextos do banco original:|Original bank contexts:|Contextos del banco original:
Corrigir clipping|Fix clipping|Corregir clipping
Banco aberto|Open bank|Banco abierto
Todos os projetos salvos|All saved projects|Todos los proyectos guardados
Executar correção|Run correction|Ejecutar corrección
Reduz somente os ganhos necessários para manter os picos em −1 dBFS.|Only reduces gains needed to keep peaks at −1 dBFS.|Reduce solo las ganancias necesarias para mantener los picos en −1 dBFS.
A distorção já presente no áudio não é reconstruída.|Existing audio distortion is not reconstructed.|La distorsión ya presente en el audio no se reconstruye.
Vozes ajustadas: |Adjusted voices: |Voces ajustadas: 
Projetos analisados: |Projects analyzed: |Proyectos analizados: 
Projetos com erro: |Projects with errors: |Proyectos con errores: 
Relatório: |Report: |Informe: 
Asset + AWB .pak (custom)|Asset + AWB .pak (custom)|Asset + AWB .pak (custom)
Asset para Unreal + AWB .pak|Unreal editor asset + AWB .pak|Asset para Unreal + AWB .pak
Asset para jogo + ACB + AWB|Game asset + ACB + AWB|Asset para juego + ACB + AWB
Nome dos arquivos (modo Asset)|File name (Asset mode)|Nombre de archivos (modo Asset)
Mesmo nome para UASSET, UEXP, ACB e AWB|Same name for UASSET, UEXP, ACB and AWB|Mismo nombre para UASSET, UEXP, ACB y AWB
Sua voz. Os IDs originais.|Your voice. Original IDs.|Tu voz. Los IDs originales.
Configurações|Settings|Configuración
Continuar projeto|Continue project|Continuar proyecto
Abrir voz externa|Open external voice|Abrir voz externa
Compare o original, escolha suas substituições e exporte silêncio nas demais entradas.|Compare the original, choose replacements and export silence for the remaining entries.|Compara el original, elige reemplazos y exporta silencio en las demás entradas.
BANCO ATUAL|CURRENT BANK|BANCO ACTUAL
VOZES DO BANCO|BANK VOICES|VOCES DEL BANCO
NOVAS SUBSTITUIÇÕES|NEW REPLACEMENTS|NUEVOS REEMPLAZOS
SERÃO SILENCIADOS|WILL BE SILENCED|SE SILENCIARÁN
BANCOS DE VOZ|VOICE BANKS|BANCOS DE VOZ
Abrir banco|Open bank|Abrir banco
Manter vozes importadas\nsem nova substituição|Keep imported voices\nwithout new replacements|Mantener voces importadas\nsin nuevos reemplazos
US e JP preservados.\nDuplo clique para abrir.|US and JP preserved.\nDouble-click to open.|US y JP conservados.\nDoble clic para abrir.
Buscar nome, ID ou função:|Search name, ID or function:|Buscar nombre, ID o función:
Nome do banco|Bank name|Nombre del banco
Quantidade de vozes|Voice count|Cantidad de voces
Mín.|Min.|Mín.
Máx.|Max.|Máx.
Nome: A–Z|Name: A–Z|Nombre: A–Z
Nome: Z–A|Name: Z–A|Nombre: Z–A
Vozes: menor quantidade|Voices: lowest count|Voces: menor cantidad
Vozes: maior quantidade|Voices: highest count|Voces: mayor cantidad
Função: A–Z|Function: A–Z|Función: A–Z
Função: Z–A|Function: Z–A|Función: Z–A
Ordenar áudios|Sort audio|Ordenar audios
Todas as funções|All functions|Todas las funciones
Nome do projeto|Project name|Nombre del proyecto
Digite o nome do seu projeto:|Enter your project name:|Escribe el nombre de tu proyecto:
Projeto renomeado: |Project renamed: |Proyecto renombrado: 
Renomeando projeto...|Renaming project...|Renombrando proyecto...
Use um nome de 1 a 80 caracteres, sem caracteres inválidos para pastas.|Use a name of 1 to 80 characters, without invalid folder characters.|Usa un nombre de 1 a 80 caracteres, sin caracteres no válidos para carpetas.
Este nome é reservado pelo Windows. Escolha outro.|This name is reserved by Windows. Choose another.|Este nombre está reservado por Windows. Elige otro.
O projeto deve estar dentro da pasta Projects do app para ser renomeado.|The project must be inside the app's Projects folder to rename it.|El proyecto debe estar dentro de la carpeta Projects de la app para renombrarlo.
Já existe um projeto nesta pasta. Escolha outro nome.|A project already exists in this folder. Choose another name.|Ya existe un proyecto en esta carpeta. Elige otro nombre.
Finalizando os áudios do projeto...|Finishing project audio...|Finalizando los audios del proyecto...
Falha ao atualizar os áudios do projeto: |Failed to update project audio: |Error al actualizar los audios del proyecto: 
Variação da voz|Voice variation|Variación de voz
1 — Original|1 — Original|1 — Original
2 — Mais rápida|2 — Faster|2 — Más rápida
3 — Mais lenta|3 — Slower|3 — Más lenta
semitom|semitone|semitono
ritmo|tempo|ritmo
Variação de voz inválida.|Invalid voice variation.|Variación de voz no válida.
Há variações sem voz importada correspondente.|Some variations have no imported voice.|Hay variaciones sin una voz importada correspondiente.
Personagem|Character|Personaje
ID|ID|ID
Aguarde a operação atual antes de adicionar um WAV.|Wait for the current operation before adding a WAV.|Espera a que termine la operación actual antes de añadir un WAV.
Selecione uma voz antes de arrastar um WAV.|Select a voice before dropping a WAV.|Selecciona una voz antes de arrastrar un WAV.
Arraste um único arquivo WAV para a voz selecionada.|Drop a single WAV file for the selected voice.|Arrastra un solo archivo WAV para la voz seleccionada.
Vozes exibidas: {shown} de {total}|Voices shown: {shown} of {total}|Voces mostradas: {shown} de {total}
Somente funções identificadas|Identified functions only|Solo funciones identificadas
Sem função identificada|Unmapped function|Función sin identificar
Todas|All|Todas
Substituídas|Replaced|Reemplazadas
WAVs repetidos|Repeated WAVs|WAV repetidos
REPETIDA COM|REPEATED WITH|REPETIDA CON
Comparar repetidas da selecionada|Compare selected voice duplicates|Comparar repetidas de la seleccionada
Todas as repetidas|All repeated voices|Todas las repetidas
Esta voz está repetida com:|This voice is repeated with:|Esta voz está repetida con:
Nenhuma repetição nesta comparação.|No duplicates in this comparison.|No hay repetidas en esta comparación.
WAV REPETIDO|REPEATED WAV|WAV REPETIDO
Repetidas: {voices} em {groups} grupos|Repeated: {voices} in {groups} groups|Repetidas: {voices} en {groups} grupos
Grupo {group} • {count} vozes|Group {group} • {count} voices|Grupo {group} • {count} voces
Mesmo WAV de origem; volume e variação podem ser diferentes.|Same source WAV; volume and variation may differ.|Mismo WAV de origen; el volumen y la variación pueden ser diferentes.
Entradas com este WAV:|Entries using this WAV:|Entradas con este WAV:
Silêncio|Silence|Silencio
NOME ORIGINAL|ORIGINAL NAME|NOMBRE ORIGINAL
FUNÇÃO / TAG ORIGINAL|ORIGINAL FUNCTION / TAG|FUNCIÓN / TAG ORIGINAL
CUE IDs|CUE IDs|IDs DE CUE
BASE (s)|BASE (s)|BASE (s)
EXPORTAÇÃO|EXPORT|EXPORTACIÓN
Escolha uma entrada de voz|Select a voice entry|Selecciona una entrada de voz
A voz original continua disponível após a substituição.|The original voice remains available after replacement.|La voz original sigue disponible después del reemplazo.
▶ Ouvir original|▶ Play original|▶ Escuchar original
▶ Ouvir importado|▶ Play imported|▶ Escuchar importado
▶ Ouvir custom|▶ Play custom|▶ Escuchar custom
■ Parar|■ Stop|■ Detener
Adicionar WAV|Add WAV|Añadir WAV
Remover substituição|Remove replacement|Quitar reemplazo
Mod (.pak / .utoc / .ucas)|Mod (.pak / .utoc / .ucas)|Mod (.pak / .utoc / .ucas)
Asset (.uasset + ACB + AWB)|Asset (.uasset + ACB + AWB)|Asset (.uasset + ACB + AWB)
Escolher pasta|Choose folder|Elegir carpeta
Abrir destino|Open destination|Abrir destino
Exportar banco|Export bank|Exportar banco
Salvar projeto|Save project|Guardar proyecto
Salvar configurações|Save settings|Guardar configuración
Pastas de referência • somente leitura|Reference folders • read only|Carpetas de referencia • solo lectura
Projeto com BTLCV|Project with BTLCV|Proyecto con BTLCV
Instalação do jogo|Game installation|Instalación del juego
Arquivo de chave do pacote|Package key file|Archivo de clave del paquete
Idioma do app|App language|Idioma de la aplicación
Idioma da interface; os nomes e tags do jogo permanecem originais.|Interface language; game names and tags remain unchanged.|Idioma de la interfaz; los nombres y tags del juego se mantienen originales.
Configuração|Settings|Configuración
Confira as pastas e o arquivo de chave.|Check the folders and package key file.|Comprueba las carpetas y el archivo de clave.
Configuração salva. Abra novamente o banco desejado.|Settings saved. Reopen the desired bank.|Configuración guardada. Vuelve a abrir el banco deseado.
Lendo os bancos de referência...|Reading reference banks...|Leyendo bancos de referencia...
Nenhum BTLCV encontrado. Configure as pastas de referência.|No BTLCV found. Configure the reference folders.|No se encontró ningún BTLCV. Configura las carpetas de referencia.
Contando vozes...|Counting voices...|Contando voces...
{count} bancos|{count} banks|{count} bancos
{count} vozes|{count} voices|{count} voces
Informe quantidades inteiras, de zero em diante.|Enter whole numbers of zero or greater.|Introduce cantidades enteras desde cero.
O mínimo não pode ultrapassar o máximo.|Minimum cannot exceed maximum.|El mínimo no puede superar el máximo.
Sem bancos para este filtro.|No banks match this filter.|Ningún banco coincide con este filtro.
Importada|Imported|Importada
Customizada|Custom|Personalizada
Sem função|Unmapped|Sin función
Descrição em inglês: |English description: |Descripción en inglés: 
Função ainda não identificada nos dados do jogo.|Function not yet identified in the game data.|Función aún no identificada en los datos del juego.
Nomes dos cues: |Cue names: |Nombres de los cues: 
IDs dos cues: |Cue IDs: |IDs de los cues: 
Função / tag original: |Original function / tag: |Función / tag original: 
Base: banco externo importado (cópia interna; arquivos de origem preservados).|Base: imported external bank (internal copy; source files preserved).|Base: banco externo importado (copia interna; archivos de origen conservados).
Original do jogo: |Game original: |Original del juego: 
Importado: |Imported: |Importado: 
Custom completo: |Full custom: |Personalizado completo: 
WAV customizado: |Custom WAV: |WAV personalizado: 
channel(s)|channel(s)|canal(es)
samples|samples|muestras
Áudio compartilhado: esta substituição se aplica a TODOS os cues listados.|Shared audio: this replacement applies to ALL listed cues.|Audio compartido: este reemplazo se aplica a TODOS los cues listados.
▶ Ouça o original para visualizar a forma de onda.|▶ Play the original to view its waveform.|▶ Escucha el original para ver su forma de onda.
Abra um ACB + AWB ou um asset de voz já editado|Open ACB + AWB or a previously edited voice asset|Abre ACB + AWB o un asset de voz ya editado
Voz Unreal ou CRI|Unreal or CRI voice|Voz Unreal o CRI
Banco ACB|ACB bank|Banco ACB
Asset Unreal|Unreal asset|Asset Unreal
Selecione o ACB ou o .uexp associado à voz|Select the ACB or .uexp associated with the voice|Selecciona el ACB o .uexp asociado a la voz
ACB ou export Unreal|ACB or Unreal export|ACB o export Unreal
Export Unreal|Unreal export|Export Unreal
Selecione o AWB correspondente à voz editada|Select the AWB matching the edited voice|Selecciona el AWB correspondiente a la voz editada
Banco de áudio CRI|CRI audio bank|Banco de audio CRI
Idioma do banco|Bank language|Idioma del banco
Informe JP ou US para escolher o template original:|Enter JP or US to select the original template:|Introduce JP o US para elegir la plantilla original:
Abrindo |Opening |Abriendo 
ACB + AWB abertos e atribuídos ao template BTLCV. |ACB + AWB opened and attached to the BTLCV template. |ACB + AWB abiertos y asignados a la plantilla BTLCV. 
Voz externa aberta. |External voice opened. |Voz externa abierta. 
Áudios importados mantidos; fontes preservadas.|Imported audio retained; sources preserved.|Audios importados mantenidos; fuentes conservadas.
Original do jogo disponível para comparação.|Game original available for comparison.|Original del juego disponible para comparar.
Referência original do jogo indisponível.|Original game reference unavailable.|Referencia original del juego no disponible.
Banco verificado • arquivos originais somente para leitura.|Bank verified • original files are read only.|Banco verificado • archivos originales de solo lectura.
INCOMPATÍVEL: o AWB diverge do ACB. Exportação bloqueada.|INCOMPATIBLE: AWB differs from ACB. Export blocked.|INCOMPATIBLE: el AWB difiere del ACB. Exportación bloqueada.
Vozes importadas sem nova substituição serão mantidas.|Imported voices without new replacements will be kept.|Se mantendrán las voces importadas sin nuevos reemplazos.
Vozes sem nova substituição serão exportadas como silêncio.|Voices without new replacements will be exported as silence.|Las voces sin nuevos reemplazos se exportarán como silencio.
Preparando voz original do jogo...|Preparing original game voice...|Preparando la voz original del juego...
Preparando voz importada...|Preparing imported voice...|Preparando la voz importada...
Reproduzindo |Playing |Reproduciendo 
Escolha sua voz customizada|Choose your custom voice|Elige tu voz personalizada
Voz adicionada: |Voice added: |Voz añadida: 
s completos. Original mantido como referência.|s in full. Original retained as reference.|s completos. Original mantenido como referencia.
Preparando WAV customizado...|Preparing custom WAV...|Preparando WAV personalizado...
Substituição removida. A voz importada será mantida.|Replacement removed. The imported voice will be kept.|Reemplazo eliminado. Se mantendrá la voz importada.
Substituição removida. Esta entrada será exportada como silêncio.|Replacement removed. This entry will be exported as silence.|Reemplazo eliminado. Esta entrada se exportará como silencio.
Projeto salvo: |Project saved: |Proyecto guardado: 
Projeto|Project|Proyecto
Banco do projeto não encontrado.|Project bank not found.|No se encontró el banco del proyecto.
Cópia importada do projeto não encontrada: |Imported project copy not found: |No se encontró la copia importada del proyecto: 
WAV do projeto não encontrado: |Project WAV not found: |No se encontró el WAV del proyecto: 
Escolha a pasta exata para os arquivos exportados|Choose the exact folder for exported files|Elige la carpeta exacta para los archivos exportados
Destino: |Destination: |Destino: 
A pasta de destino será criada ao exportar.|The destination folder will be created on export.|La carpeta de destino se creará al exportar.
Exportação concluída: |Export completed: |Exportación completada: 
Exportação concluída|Export completed|Exportación completada
Pacote .pak / .utoc / .ucas|Package .pak / .utoc / .ucas|Paquete .pak / .utoc / .ucas
Asset Zen .uasset completo com ACB, .acb e .awb|Full Zen .uasset with ACB, .acb and .awb|Asset Zen .uasset completo con ACB, .acb y .awb
Asset .uasset + .uexp com ACB atualizado, .acb e .awb|Asset .uasset + .uexp with updated ACB, .acb and .awb|Asset .uasset + .uexp con ACB actualizado, .acb y .awb
Arquivos salvos diretamente em:|Files saved directly in:|Archivos guardados directamente en:
Nomes, IDs e tags verificados. Originais preservados.|Names, IDs and tags verified. Originals preserved.|Nombres, IDs y tags verificados. Originales conservados.
O teste dentro do jogo ainda deve ser realizado.|In-game testing is still required.|Todavía falta realizar la prueba en el juego.
Preparando exportação...|Preparing export...|Preparando exportación...
Operação em andamento|Operation in progress|Operación en curso
Aguarde a operação terminar antes de fechar.|Wait for the operation to finish before closing.|Espera a que termine la operación antes de cerrar.
Convertendo |Converting |Convirtiendo 
Empacotando arquivos .pak / .utoc / .ucas...|Packing .pak / .utoc / .ucas files...|Empaquetando archivos .pak / .utoc / .ucas...
Os arquivos gerados devem ficar dentro de D:\APP_DE_VOZ.|Generated working files must stay inside D:\APP_DE_VOZ.|Los archivos de trabajo generados deben permanecer en D:\APP_DE_VOZ.
Formato de asset diferente das referências analisadas.|Asset format differs from the analyzed references.|El formato del asset difiere de las referencias analizadas.
Cabeçalho de funções não suportado.|Unsupported function header.|Cabecera de funciones no compatible.
Selecione o asset com o nome original BTLCV_####_##_JP ou _US.|Select the asset with its original BTLCV_####_##_JP or _US name.|Selecciona el asset con su nombre original BTLCV_####_##_JP o _US.
O AWB selecionado não corresponde ao hash do ACB atribuído ao asset.|The selected AWB does not match the hash of the ACB attached to the asset.|El AWB seleccionado no coincide con el hash del ACB asignado al asset.
O AWB/ACB não contém todas as faixas referenciadas.|The AWB/ACB does not contain all referenced tracks.|El AWB/ACB no contiene todas las pistas referenciadas.
Os nomes do ACB e do AWB indicam bancos diferentes.|ACB and AWB names indicate different banks.|Los nombres del ACB y del AWB indican bancos distintos.
Nome do banco inválido.|Invalid bank name.|Nombre de banco no válido.
O ACB contém dados fora da tabela principal; formato não suportado.|ACB contains data outside the main table; unsupported format.|El ACB contiene datos fuera de la tabla principal; formato no compatible.
ACB sem hash do AWB; associação não pôde ser verificada.|ACB has no AWB hash; the association could not be verified.|El ACB no tiene hash del AWB; no se pudo verificar la asociación.
O AWB selecionado não corresponde ao ACB.|The selected AWB does not match the ACB.|El AWB seleccionado no corresponde al ACB.
O ACB não pertence ao BTLCV de referência escolhido.|The ACB does not belong to the selected reference BTLCV.|El ACB no pertenece al BTLCV de referencia seleccionado.
Os nomes ou IDs dos cues diferem do template. Importe o asset completo para preservar essa estrutura.|Cue names or IDs differ from the template. Import the complete asset to preserve that structure.|Los nombres o IDs de los cues difieren de la plantilla. Importa el asset completo para conservar esa estructura.
Cabeçalho BulkData Zen não reconhecido.|Unrecognized Zen BulkData header.|Cabecera BulkData Zen no reconocida.
Quantidade de exports Zen não suportada.|Unsupported Zen export count.|Cantidad de exports Zen no compatible.
O WAV customizado deve conter áudio.|The custom WAV must contain audio.|El WAV personalizado debe contener audio.
Campo de ACB não editável.|ACB field is not editable.|El campo del ACB no es editable.
Cabeçalho BulkData diferente do formato validado; exportação interrompida.|BulkData header differs from the validated format; export stopped.|La cabecera BulkData difiere del formato validado; exportación detenida.
O BTLCV deve conter exatamente um export.|BTLCV must contain exactly one export.|El BTLCV debe contener exactamente un export.
Tamanho do export Unreal não corresponde ao arquivo.|Unreal export size does not match the file.|El tamaño del export Unreal no coincide con el archivo.
Escolha uma pasta de saída fora das referências e da instalação do jogo.|Choose an output folder outside the references and game installation.|Elige una carpeta de salida fuera de las referencias y de la instalación del juego.
O destino deve ser uma pasta.|The destination must be a folder.|El destino debe ser una carpeta.
O AWB desta instalação diverge do BTLCV. Use um par da mesma versão.|This installation's AWB differs from BTLCV. Use a matching version pair.|El AWB de esta instalación difiere del BTLCV. Usa un par de la misma versión.
O projeto contém IDs de áudio que não existem neste banco.|The project contains audio IDs absent from this bank.|El proyecto contiene IDs de audio que no existen en este banco.
Hash AWB incorreto na exportação.|Incorrect AWB hash in the export.|Hash del AWB incorrecto en la exportación.
IDs originais de AWB foram alterados.|Original AWB IDs were changed.|Se modificaron los IDs originales del AWB.
O ACB de referência não corresponde ao pacote Zen original.|The reference ACB does not match the original Zen package.|El ACB de referencia no corresponde al paquete Zen original.
Quantidade de exports Zen diferente do formato validado.|Zen export count differs from the validated format.|La cantidad de exports Zen difiere del formato validado.
O pacote gerado não preservou o BTLCV completo.|The generated package did not preserve the complete BTLCV.|El paquete generado no conservó el BTLCV completo.
Tabela CRI inválida.|Invalid CRI table.|Tabla CRI no válida.
AWB inválido.|Invalid AWB.|AWB no válido.
IDs do AWB foram alterados.|AWB IDs were changed.|Se modificaron los IDs del AWB.
Hash do índice do jogo inválido.|Invalid game index hash.|Hash del índice del juego no válido.
Pacote sem índice de diretórios.|Package has no directory index.|El paquete no tiene índice de directorios.
Hash do diretório inválido.|Invalid directory hash.|Hash del directorio no válido.
Pacote incompleto.|Incomplete package.|Paquete incompleto.
Registro de função não suportado.|Unsupported function record.|Registro de función no compatible.
O .acb selecionado difere do ACB atribuído ao asset. Selecione o conjunto correspondente.|The selected .acb differs from the ACB attached to the asset. Select the matching set.|El .acb seleccionado difiere del ACB asignado al asset. Selecciona el conjunto correspondiente.
Áudio original indisponível nesta versão do jogo.|Original audio unavailable in this game version.|Audio original no disponible en esta versión del juego.
Selecione o ACB e o AWB correspondentes.|Select the matching ACB and AWB.|Selecciona el ACB y el AWB correspondientes.
Use um WAV PCM sem compressão.|Use an uncompressed PCM WAV.|Usa un WAV PCM sin compresión.
Destino redirecionado para fora da pasta selecionada.|Destination redirected outside the selected folder.|Destino redirigido fuera de la carpeta seleccionada.
Exporte em outra pasta para preservar os arquivos importados.|Export to a different folder to preserve imported files.|Exporta a otra carpeta para conservar los archivos importados.
O tamanho do cabeçalho AWB não corresponde à referência.|AWB header size does not match the reference.|El tamaño de la cabecera AWB no coincide con la referencia.
Offsets de AWB inválidos.|Invalid AWB offsets.|Offsets de AWB no válidos.
Compressão de áudio não suportada.|Unsupported audio compression.|Compresión de audio no compatible.
Quantidade de blocos inválida.|Invalid block count.|Cantidad de bloques no válida.
Arquivo .uexp não encontrado.|.uexp file not found.|Archivo .uexp no encontrado.
O asset selecionado não contém um ACB atribuído.|The selected asset has no attached ACB.|El asset seleccionado no contiene un ACB asignado.
O áudio original não corresponde aos metadados da referência.|Original audio does not match reference metadata.|El audio original no corresponde a los metadatos de referencia.
Cópia de importação inconsistente.|Inconsistent import copy.|Copia de importación inconsistente.
Use WAV mono ou estéreo.|Use mono or stereo WAV.|Usa WAV mono o estéreo.
O encoder não produziu o HCA.|The encoder did not produce HCA.|El codificador no generó el HCA.
O mapa de nomes do asset importado difere da referência Zen; exporte como Asset.|Imported asset name map differs from the Zen reference; export as Asset.|El mapa de nombres del asset importado difiere de la referencia Zen; exporta como Asset.
O layout do asset externo não corresponde ao pacote Zen de referência; exporte como Asset.|External asset layout does not match the reference Zen package; export as Asset.|La estructura del asset externo no corresponde al paquete Zen de referencia; exporta como Asset.
Não foi possível descompactar o áudio.|Could not decompress audio.|No se pudo descomprimir el audio.
O asset precisa do .uexp correspondente, ou ser um .uasset Zen completo suportado.|The asset needs its matching .uexp or must be a supported complete Zen .uasset.|El asset necesita su .uexp correspondiente o debe ser un .uasset Zen completo compatible.
Formato PCM não suportado.|Unsupported PCM format.|Formato PCM no compatible.
Duração compartilhada não suportada.|Shared duration is not supported.|Duración compartida no compatible.
Não foi possível identificar o banco e idioma. Use o nome original BTLCV_####_##_JP/US ou selecione o idioma.|Could not identify bank and language. Use the original BTLCV_####_##_JP/US name or select the language.|No se pudo identificar el banco y el idioma. Usa el nombre original BTLCV_####_##_JP/US o selecciona el idioma.
Arquivo já existe e foi preservado: |File already exists and was preserved: |El archivo ya existe y se ha conservado: 
. Escolha outra pasta.|. Choose another folder.|. Elige otra carpeta.
Arquivo de saída ausente: |Missing output file: |Archivo de salida ausente: 
Falha na verificação de cópia: |Copy verification failed: |Error al verificar la copia: 
Referência BTLCV necessária para atribuir este ACB ao asset não está disponível: |The BTLCV reference needed to attach this ACB is unavailable: |La referencia BTLCV necesaria para asignar este ACB no está disponible: 
Existem cues sem mapeamento: |Some cues are unmapped: |Hay cues sin asignación: 
Duração não possui armazenamento individual: |Duration has no individual storage: |La duración no tiene almacenamiento individual: 
Cue com duração sequencial não suportada: |Unsupported sequential cue duration: |Duración secuencial de cue no compatible: 
Duração CueInfos não identificada com segurança: |CueInfos duration could not be identified safely: |No se pudo identificar con seguridad la duración CueInfos: 
Metadados originais alterados: |Original metadata changed: |Metadatos originales modificados: 
Estrutura de tabela alterada: |Table structure changed: |Estructura de tabla modificada: 
Nomes, IDs ou tags alterados: |Names, IDs or tags changed: |Nombres, IDs o tags modificados: 
Arquivo de mod não gerado: |Mod file not generated: |Archivo del mod no generado: 
Versão de pacote não suportada: |Unsupported package version: |Versión de paquete no compatible: 
AWB não encontrado no jogo: |AWB not found in game: |AWB no encontrado en el juego: 
Configurações salvas.|Settings saved.|Configuración guardada.
Nenhum áudio corresponde a estes filtros.|No audio matches these filters.|Ningún audio coincide con estos filtros.
{rate} Hz • {channels} canais • {samples} amostras|{rate} Hz • {channels} channel(s) • {samples} samples|{rate} Hz • {channels} canal(es) • {samples} muestras
Pacote Zen original não encontrado.|Original Zen package not found.|Paquete Zen original no encontrado.
UTOC inválido.|Invalid UTOC.|UTOC no válido.
Índice criptografado do mod não está alinhado.|The mod's encrypted index is not aligned.|El índice cifrado del mod no está alineado.
Codec IoStore não suportado: |Unsupported IoStore codec: |Códec IoStore no compatible: 
Personagem ou código BTLCV|Character or BTLCV code|Personaje o código BTLCV
BTLCV: menor número|BTLCV: lowest number|BTLCV: menor número
BTLCV: maior número|BTLCV: highest number|BTLCV: mayor número
Personagem: A–Z|Character: A–Z|Personaje: A–Z
Personagem: Z–A|Character: Z–A|Personaje: Z–A
Nome não listado na planilha|Name not listed in spreadsheet|Nombre no incluido en la hoja de cálculo
Seu estúdio de vozes|Your voice studio|Tu estudio de voces
Referência original, vozes customizadas e volume no mesmo lugar.|Original reference, custom voices and volume in one place.|Referencia original, voces personalizadas y volumen en un solo lugar.
Idioma das funções|Function language|Idioma de las funciones
FUNÇÃO|FUNCTION|FUNCIÓN
TAG ORIGINAL|ORIGINAL TAG|ETIQUETA ORIGINAL
Áudio e volume|Audio and volume|Audio y volumen
Detalhes e tags|Details and tags|Detalles y etiquetas
ORIGINAL|ORIGINAL|ORIGINAL
IMPORTADA|IMPORTED|IMPORTADA
APÓS AJUSTE|AFTER ADJUSTMENT|TRAS EL AJUSTE
Ganho da voz importada|Imported voice gain|Ganancia de la voz importada
Igualar ao original|Match original|Igualar al original
Zerar ganho|Reset gain|Restablecer ganancia
Pico|Peak|Pico
RMS ativo|Active RMS|RMS activo
Adicione um WAV ou abra um banco editado para ajustar o volume.|Add a WAV or open an edited bank to adjust volume.|Añade un WAV o abre un banco editado para ajustar el volumen.
Medindo áudio selecionado...|Measuring selected audio...|Midiendo el audio seleccionado...
Não foi possível medir: |Could not measure: |No se pudo medir: 
Clipping: reduza o ganho antes de ouvir ou exportar.|Clipping: reduce gain before playback or export.|Saturación: reduce la ganancia antes de escuchar o exportar.
Diferença para o original: |Difference from original: |Diferencia con el original: 
O ganho afeta a prévia e a exportação.|Gain applies to preview and export.|La ganancia se aplica a la vista previa y a la exportación.
Sem fala ativa mensurável. Ajuste automático indisponível.|No measurable active speech. Automatic matching unavailable.|No hay voz activa medible. Ajuste automático no disponible.
Referência original indisponível. O ganho afeta a prévia e a exportação.|Original reference unavailable. Gain applies to preview and export.|Referencia original no disponible. La ganancia se aplica a la vista previa y a la exportación.
Preparando prévia com volume ajustado...|Preparing preview with adjusted volume...|Preparando vista previa con volumen ajustado...
O ganho deve ficar entre -48 e +24 dB.|Gain must be between -48 and +24 dB.|La ganancia debe estar entre -48 y +24 dB.
O ganho causa clipping. Reduza o volume ou use Igualar ao original.|Gain causes clipping. Reduce volume or use Match original.|La ganancia causa saturación. Reduce el volumen o usa Igualar al original.
Não há fala ativa suficiente para igualar os volumes.|Not enough active speech to match levels.|No hay suficiente voz activa para igualar los niveles.
Há ajustes de volume sem voz importada correspondente.|Some volume adjustments have no corresponding imported voice.|Hay ajustes de volumen sin una voz importada correspondiente.

"""
CATALOG={}
for line in DATA.splitlines():
    if line:
        parts=line.split("|")
        if len(parts)!=3:raise ValueError("Invalid translation entry: "+line)
        source,en,es=[p.replace(r"\n","\n") for p in parts]
        CATALOG[source]={"en":en,"es":es}

for source,translations in json.loads((Path(__file__).resolve().parents[1]/'Data/interface_languages.json').read_text(encoding='utf-8')).items():
    CATALOG.setdefault(source,{}).update(translations)

class Translator:
    def __init__(self,language="en"):self.language=language if language in LANGUAGES else "en"
    def logical(self,value):
        value=str(value)
        if self.language=="pt":return value
        if value in CATALOG:return CATALOG[value].get(self.language,CATALOG[value].get("en",value))
        for original in sorted(CATALOG,key=len,reverse=True):
            if len(original)>=8 and original in value:
                value=value.replace(original,CATALOG[original].get(self.language,CATALOG[original].get("en",original)))
        return value
    def display(self,value,measure=None,width=None):return render_text(value,self.language,measure,width)
    def text(self,value):return self.display(self.logical(value))

class LocalizedVar(tk.StringVar):
    def __init__(self,master,translator,value=""):
        self.translator=translator;self.raw=str(value)
        super().__init__(master,value=translator.text(value))
    def set(self,value):
        self.raw=str(value);super().set(self.translator.text(value))
    def refresh(self):super().set(self.translator.text(self.raw))
