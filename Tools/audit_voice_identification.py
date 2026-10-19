import sys,json,time,datetime,hashlib,collections,re,gc
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
import core,voice_context as vc,live_voice_references as live,game_installation,game_characters,function_refinements as fr,voice_origin_details as origin
cfg=core.config();names=core.available_banks(cfg);started=time.monotonic();pak=core.Pak(cfg)
report={'date':datetime.datetime.now().astimezone().isoformat(),'game_identity':game_installation.identity(cfg),'game_token':live.token(cfg),'banks_expected':len(names),'banks':[],'errors':[],'mismatches':[],'unknown':[],'new_source_candidates':[],'totals':{}}
initial_token=report['game_token'];totals=collections.Counter()
source_files=['src/'+name+'.py' for name in ('core','voice_context','live_voice_references','function_refinements','voice_function_correlations','local_voice_correlations','fusion_voice_relations','manual_origin_reader','voice_origin_details','game_voice_relations','attack_context','audio_function_equivalences','user_voice_functions','compact_functions','i18n')]+['Data/'+name+'.json' for name in ('user_voice_functions','voice_function_correlations','interface_languages','function_languages','compact_function_languages','manual_voice_origins','voice_origin_languages','voice_participant_candidates','audio_function_equivalences')]
report['source_hashes']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in source_files}
label=sys.argv[1] if len(sys.argv)>1 else 'baseline'
if not re.fullmatch(r'[A-Za-z0-9_-]+',label):raise ValueError('Invalid report label')
output=root/'Reports'/('voice_identification_review_'+datetime.datetime.now().strftime('%Y%m%d')+'_'+label+'.json')
try:
 for index,name in enumerate(names,1):
  try:
   bank=core.Bank(cfg,pak,name);count=collections.Counter()
   for r in bank.rows:
    count['physical_rows']+=1
    if not r['samples']:count['empty_rows']+=1;continue
    count['voices']+=1;known=vc.identified(r,'all');count['identified' if known else 'unknown']+=1
    if fr.has_exact_function(r):count['exact_source_rows']+=1
    if r.get('function_correlations'):count['probable_family_rows']+=1
    if r.get('fusion_relations'):count['fusion_relation_rows']+=1
    if r.get('audio_equivalences'):count['audio_equivalence_rows']+=1
    if r.get('participant_relations'):count['participant_relation_rows']+=1
    if r.get('form_change_relations'):count['form_change_relation_rows']+=1
    if origin.eligible(r):
     extra=origin.detail(r,'en')
     assert extra,'Origin detail missing'
     if r.get('origin_evidence'):count['origin_property_rows']+=1
     if any(e.get('callers') for e in r.get('origin_evidence',[])):count['origin_caller_rows']+=1
     if r.get('origin_audio'):count['origin_audio_rows']+=1
     if any(a['bank'][6:10]!=name[6:10] for a in r.get('origin_audio',[])):count['origin_other_character_audio_rows']+=1
     if any(a['bank']!=name and a['bank'][6:10]==name[6:10] for a in r.get('origin_audio',[])):count['origin_other_form_audio_rows']+=1
     count['origin_status_'+origin.status(r)]+=1
    for scope in ('all','functions','interactions','emotes'):
     texts=vc.descriptions(r,'en',scope)
     original=any(v and v!='Unclassified' for v in r.get('english',[])) if scope in ('all','functions') else False
     if vc.matches_scope(r,scope) and vc.identified(r,scope) and not (bool(texts) or original):
      report['mismatches'].append({'bank':name,'key':r['key'],'scope':scope,'reason':'identified_without_description'})
     if (bool(texts) or original) and not vc.identified(r,scope):
      report['mismatches'].append({'bank':name,'key':r['key'],'scope':scope,'descriptions':texts,'english':r.get('english',[]),'refinements':r.get('function_refinements',[])})
     if vc.matches_scope(r,scope):
      assert vc.matches_filter(r,'+',scope)!=vc.matches_filter(r,'~',scope)
      for option,_ in vc.options([r],scope,'en'):
       if not vc.matches_filter(r,option,scope):report['mismatches'].append({'bank':name,'key':r['key'],'scope':scope,'option':option,'reason':'offered_option_does_not_match'})
    if not known:
     item={k:r.get(k) for k in ('key','filename','cue_ids','cue_names','functions','english','duration','function_refinements','attack_contexts','interactions','usage_contexts','emotes')};item['bank']=name
     report['unknown'].append(item)
     # Check references from the named source actor even when the existing
     # enrichment gate did not select the row. Do not infer from waveform IDs.
     for cue_name in r['cue_names']:
      m=re.fullmatch(r'(\d{4}_\d{2})_\d{4}',cue_name)
      if not m:continue
      contexts=fr.source_contexts(initial_token,live.schema_data()[1],m[1],name[-2:],json.dumps(cfg,sort_keys=True))
      exact=[c for c in contexts if c.get('cue_name')==cue_name]
      if exact:report['new_source_candidates'].append({'bank':name,'key':r['key'],'cue_ids':r['cue_ids'],'cue_name':cue_name,'contexts':exact})
   for scope in ('all','functions','interactions','emotes'):
    labels=collections.Counter(label for key,label in vc.options(bank.rows,scope,'en'))
    duplicates=[label for label,amount in labels.items() if amount>1]
    if duplicates:report['mismatches'].append({'bank':name,'scope':scope,'reason':'ambiguous_displayed_options','labels':duplicates})
   totals.update(count);report['banks'].append({'name':name,**count})
  except Exception as e:report['errors'].append({'bank':name,'type':type(e).__name__,'message':str(e)})
  if index%20==0 or index==len(names):
   report['totals']=dict(totals);core.write_json(output,report)
   print(json.dumps({'banks':index,'total':len(names),'voices':totals['voices'],'unknown':totals['unknown'],'mismatches':len(report['mismatches']),'errors':len(report['errors']),'elapsed':round(time.monotonic()-started)},ensure_ascii=False),flush=True)
  gc.collect()
 assert live.token(cfg)==initial_token,'Game changed during complete review'
finally:pak.f.close()
report['elapsed_seconds']=round(time.monotonic()-started,2);report['totals']=dict(totals)
core.write_json(output,report)
report['source_files_unchanged']=all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in report['source_hashes'].items())
report['status']='passed' if not report['errors'] and not report['mismatches'] and report['source_files_unchanged'] else 'failed'
core.write_json(output,report)
print('REPORT',output,report['status'],flush=True)
assert report['status']=='passed', 'Review found errors, inconsistent filters or changing source files; inspect the report'
