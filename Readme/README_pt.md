# Sparking Zero Voice Studio — Edição portátil

## Instalação
1. Extraia o ZIP inteiro para uma pasta onde possa gravar, como Documentos. Não execute dentro do ZIP nem instale em Program Files.
2. Abra `Sparking Zero Voice Studio.exe`. Python, ferramentas de áudio, UnrealPak e Oodle estão incluídos; não precisa instalar Python, Codex ou Excel. `Preparar ferramentas.bat` é uma verificação opcional das ferramentas.
3. Em Configurações, selecione a pasta de instalação do jogo. Para Replacer, deixe CustomProject e Custom Engine vazios para ler as referências do jogo. A chave dos pacotes é configurada automaticamente; não é necessário `keys.json`.
4. Salve as configurações e abra um banco. Novas instalações começam em inglês. É possível mudar o idioma antes de selecionar pastas. Atualizar mantendo seu `settings.json` preserva o idioma escolhido.

## Requisitos
- Windows 10 ou 11 de 64 bits; .NET Framework 4.8 e runtime Visual C++ de 64 bits compatível com as ferramentas Unreal incluídas.
- DRAGON BALL Sparking! ZERO instalado, com os arquivos `.pak`, `.utoc` e `.ucas` da versão do jogo utilizada.
- **Custom Engine e CustomProject não estão incluídos.** Exportar Custom exige uma Custom Engine Unreal 5.1 compatível, com plugin CriWare e suas DLLs, e CustomProject com referências de voz compatíveis. Uma instalação genérica da Unreal não é suficiente.
- CustomProject é opcional para Replacer. Quando configurado, fornece as referências; caso contrário, o app lê o jogo e renova o cache quando os contêineres mudam.

## Principais funções
- Bancos US/JP, nomes oficiais dos personagens por idioma, Cue IDs, funções, tags de interação, filtros e vozes repetidas; comparação do áudio original e editado.
- Importação de áudio, vídeo e pacotes de voz externos; gravação pelo microfone; corte; ganho, correção de clipping e maximização do volume.
- Aprimoramento local, isolamento de fundo e efeitos: reverb, eco, pitch, graves/agudos, voz dupla, distorção e rádio. Compare a prévia antes de aplicar; a qualidade depende da gravação.
- Velocidade de 0,25x a 3,00x, preservação do tom ativada por padrão (pode ser desativada), prévia e desfazer/refazer. Preserve o tom para mudar somente o ritmo.
- Salvamento e recuperação, projetos recentes, compartilhamento/mescla, migração de bancos e cópia por tags/funções. Ctrl+Z desfaz; Ctrl+Y ou Ctrl+Shift+Z refaz. Interface e ajuda em 16 idiomas.
- Vozes externas confirmadas como idênticas ao jogo são originais, não substituições. A prévia externa fica limitada às diferenças confirmadas. Escolha manter o original ou silenciar as vozes não substituídas.

## Exportações Replacer e Custom
**Replacer:** entrega `.pak`, `.utoc` e `.ucas` juntos na pasta do mod. O banco original determina o personagem substituído; renomear projeto ou pasta não muda esse alvo. O nome vazio da pasta Replacer usa o nome oficial do personagem base no idioma do app. Mantenha instalado o mod próprio de um personagem custom: o pacote de voz não inclui o personagem. Ao importar, mantenha PAK/UTOC/UCAS relacionados juntos. Replacer não inicia o Unreal Editor.

**Custom:** entrega o `.uasset` em “Custom - Pasta do mod na Unreal” e o `.pak` em “Custom - Pasta do mod para o game”; intermediários e relatórios ficam em uma pasta de apoio. Os nomes das pastas seguem o idioma do app. O nome do projeto deve ser exatamente o da pasta do mod/plugin em `Plugins` na Unreal. O banco deve corresponder ao ID do personagem custom e ao idioma US/JP. Selecione CustomProject e Custom Engine nas Configurações.

Exports ficam agrupados por número e nome do projeto. Cada versão começa com uma numeração crescente, deixando a última no final ao ordenar por nome. Abrir pasta oferece primeiro exports, depois áudios editados e projetos; sem projeto, abre a pasta geral dos exports. Sempre teste no jogo.

## Projetos e backups
Feche o app e faça backup da pasta existente antes de atualizar. Extraia o novo ZIP do aplicativo na mesma instalação, mesclando as pastas e substituindo os arquivos do programa. Mantenha Projects, Cache, settings.json, preferências, contadores e presets salvos. Esses arquivos pessoais não vêm no novo ZIP. Não crie uma segunda pasta do app dentro da antiga. Mantenha o mesmo local: projetos antigos podem conter caminhos absolutos dos áudios. Os projetos antigos mantêm seu formato, com suporte aos campos opcionais ausentes. Consulte UPDATE.md.

## Problemas e arquivos incluídos
Para acesso negado, extraia em uma pasta onde possa gravar, como Documentos. A abertura de pastas tenta novamente pelo Explorador; não pede administrador nem altera permissões do Windows. Para erros de importação Custom, consulte o `import.log` indicado e confira a Engine/CriWare compatível. Assets importados precisam corresponder ao banco e à versão pretendidos.

O pacote não contém projetos, gravações, exports, cache, assets do jogo/referências ou configurações pessoais do autor. A chave padrão e as ferramentas estão incluídas. As licenças acompanham runtime e bibliotecas; créditos dos motores de voz em `Tools/VoiceAI/NOTICE.txt`. Ao pedir suporte, informe versões do app/jogo, banco, modo de exportação e log. Verificações técnicas locais não substituem o teste no jogo.
