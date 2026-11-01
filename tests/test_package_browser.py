import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import package_import,package_browser

def bank(name,label,group):
 return {'bank_name':name,'package_origin':{'bank_info':{'label':label,'group_key':group,'language':name[-2:]}}}

class PackageBrowserTests(unittest.TestCase):
 def test_languages_share_a_character_group(self):
  banks=[bank('BTLCV_Toas_11_US','Super17','Mods/GT/S17'),bank('BTLCV_Toas_11_JP','Super17','Mods/GT/S17'),bank('BTLCV_Toas_14_JP','Haze','Mods/GT/Haze')]
  result=package_browser.groups(banks)
  self.assertEqual(len(result),2)
  self.assertEqual(len(package_browser.groups(banks,'super17')[0]['banks']),2)
  self.assertEqual(sum(len(g['banks']) for g in package_browser.groups(banks,'US')),1)
 def test_same_label_different_mounts_stay_separate(self):
  banks=[bank('BTLCV_A_01_US','Haze','Mods/One/Haze'),bank('BTLCV_B_01_US','Haze','Mods/Two/Haze')]
  self.assertEqual(len(package_browser.groups(banks)),2)
 def test_search_ignores_accents_without_changing_names(self):
  item=bank('BTLCV_A_01_US','Personágem','Mods/Test/Character')
  self.assertEqual(package_browser.groups([item],'personagem')[0]['label'],'Personágem')
 def test_custom_names_require_an_exact_safe_mod_mount(self):
  origin={'voice_asset_path':'SparkingZERO/Mods/GT/Content/Haze/BTLCV_Toas_14_US.uasset'}
  self.assertTrue(package_import.custom_asset_name('BTLCV_Toas_14_US',origin))
  self.assertFalse(package_import.custom_asset_name('BTLCV_Toas_11_US',origin))
  for path in ('SparkingZERO/Mods/../GT/BTLCV_Toas_14_US.uasset','SparkingZERO/Content/BTLCV_Toas_14_US.uasset','C:/BTLCV_Toas_14_US.uasset'):
   self.assertFalse(package_import.custom_asset_name('BTLCV_Toas_14_US',{'voice_asset_path':path}))
  self.assertFalse(package_import.custom_asset_name('../BTLCV_Toas_14_US',origin))
 def test_standard_single_bank_still_recognized(self):
  self.assertTrue(package_import.VOICE.fullmatch('BTLCV_0070_00_US.awb'))
  self.assertTrue(package_import.VOICE.fullmatch('BTLCV_Toas_14_JP.uasset'))
  self.assertFalse(package_import.VOICE.fullmatch('CharacterSound.uasset'))

if __name__=='__main__':unittest.main(verbosity=2)
