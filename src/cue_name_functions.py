"""Conservative broad categories derived from named ACB cues, not numeric ranges."""
import re

MENU_NAME=re.compile(r'SEL_\d{4}_(?:\d{2}_\d{3}_\d{4}|\d{3}_\d{4})')
LABELS={'pt':'Seleção / interação de menu','en':'Selection / menu interaction','es':'Selección / interacción de menú','es-419':'Selección / interacción de menú','fr':'Sélection / interaction de menu','it':'Selezione / interazione nel menu','de':'Auswahl / Menüinteraktion','ja':'選択／メニューでの会話','ko':'선택 / 메뉴 상호작용','zh-Hans':'选择／菜单互动','zh-Hant':'選擇／選單互動','ru':'Выбор / взаимодействие в меню','pl':'Wybór / interakcja w menu','ar':'الاختيار / تفاعل القائمة','th':'การเลือก / บทสนทนาในเมนู','id':'Pemilihan / interaksi menu'}

def label(language):return LABELS.get(language,LABELS['en'])

NOTES={'pt': 'Categoria deduzida do prefixo SEL_ no nome do cue; o evento exato e a execução no jogo não foram confirmados.', 'en': 'Category inferred from the SEL_ cue-name prefix; the exact event and in-game playback have not been confirmed.', 'es': 'Categoría deducida del prefijo SEL_ del nombre del cue; el evento exacto y la reproducción en el juego no se han confirmado.', 'es-419': 'Categoría deducida del prefijo SEL_ del nombre del cue; el evento exacto y la reproducción en el juego no se han confirmado.', 'fr': 'Catégorie déduite du préfixe SEL_ du nom du cue ; l’événement exact et la lecture dans le jeu ne sont pas confirmés.', 'it': 'Categoria dedotta dal prefisso SEL_ del nome del cue; l’evento esatto e la riproduzione nel gioco non sono stati confermati.', 'de': 'Kategorie aus dem Präfix SEL_ des Cue-Namens abgeleitet; das genaue Ereignis und die Wiedergabe im Spiel wurden nicht bestätigt.', 'ja': 'キュー名の接頭辞SEL_から推定した分類です。正確なイベントとゲーム内での再生は確認されていません。', 'ko': '큐 이름의 SEL_ 접두사에서 추정한 분류입니다. 정확한 이벤트와 게임 내 재생은 확인되지 않았습니다.', 'zh-Hans': '根据提示名称的 SEL_ 前缀推断类别；尚未确认具体事件及游戏内播放。', 'zh-Hant': '根據提示名稱的 SEL_ 前綴推斷類別；尚未確認具體事件及遊戲內播放。', 'ru': 'Категория определена по префиксу SEL_ в имени cue; точное событие и воспроизведение в игре не подтверждены.', 'pl': 'Kategoria wywnioskowana z prefiksu SEL_ w nazwie cue; dokładne zdarzenie i odtwarzanie w grze nie zostały potwierdzone.', 'ar': 'الفئة مستنتجة من بادئة SEL_ في اسم المقطع؛ لم يتم تأكيد الحدث المحدد أو التشغيل داخل اللعبة.', 'th': 'หมวดหมู่อนุมานจากคำนำหน้า SEL_ ในชื่อคิว ยังไม่ได้ยืนยันเหตุการณ์ที่แน่นอนและการเล่นเสียงในเกม', 'id': 'Kategori disimpulkan dari awalan SEL_ pada nama cue; peristiwa yang tepat dan pemutaran dalam game belum dikonfirmasi.'}

def details(context,language):
    note=NOTES.get(language,NOTES['en'])
    return label(language)+' | '+context['cue_name']+' | '+note

def contexts(bank_name,byid):
    asset='SS/Sounds/Battle_VOICE/'+bank_name[-2:]+'/'+bank_name+'.uasset'
    return [dict(action='MenuSelection',cue_id=id,cue_name=name,root=asset,child=asset,chain=[],source_kind='cue_name_pattern',reference_validation='current_acb_name_pattern',confidence='name_pattern')
            for id,names in byid.items() for name in sorted(names) if MENU_NAME.fullmatch(name)]

def eligible(row):
    import user_voice_functions
    return not (row.get('_manual') or row.get('interactions') or row.get('emotes') or row.get('usage_contexts') or row.get('attack_contexts') or any(v and v!='Unclassified' for v in row.get('english',[])) or user_voice_functions.functions(row))
