# Sparking Zero Voice Studio — 可攜版

## 安裝
1. 將整個 ZIP 解壓縮到可寫入資料夾，例如「文件」。不要在 ZIP 內執行，也不要安裝到 Program Files。
2. 開啟 `Sparking Zero Voice Studio.exe`。已包含 Python、音訊工具、UnrealPak 和 Oodle，無須另行安裝 Python、Codex 或 Excel。`Preparar ferramentas.bat` 是選用的工具檢查。
3. 在設定中選擇遊戲安裝目錄。Replacer 模式下將 CustomProject 和 Custom Engine 留空，即可直接讀取遊戲參考資料。遊戲封裝金鑰自動設定，無須 `keys.json`。
4. 儲存設定並開啟語音庫。新安裝預設使用英語。選擇資料夾之前也能變更語言。更新時保留原有 `settings.json` 可保留已選語言。

## 系統需求
- 64 位元 Windows 10 或 11、.NET Framework 4.8，以及與隨附 Unreal 工具相容的 64 位元 Visual C++ 執行階段。
- 已安裝 DRAGON BALL Sparking! ZERO，包含所用遊戲版本的 `.pak`、`.utoc`、`.ucas` 檔案。
- **不包含 Custom Engine 和 CustomProject。** Custom 匯出需要相容的 Unreal 5.1 Custom Engine、CriWare 外掛及其 DLL，以及包含相容語音參考的 CustomProject。一般 Unreal 安裝不足以完成此匯出。
- Replacer 的 CustomProject 為選用項目。設定後使用其參考資料；未設定則讀取遊戲，遊戲容器變更時更新快取。

## 主要功能
- US/JP 語音庫、官方在地化角色名、Cue IDs、功能、互動標籤、篩選器、重複語音及原始/編輯音訊比較。
- 匯入音訊、影片和外部語音封裝；麥克風錄音；裁剪、增益、削波修正及音量最大化。
- 本機語音增強、背景分離及殘響、回音、音高、低音/高音、雙重語音、失真、收音機效果。套用前請試聽，品質取決於錄音。
- 0.25x 至 3.00x 速度、預設啟用保留音高（可關閉）、預覽及復原/重做。保留音高時只改變節奏。
- 儲存與復原、最近專案、分享/合併、語音庫遷移、按標籤/功能複製。Ctrl+Z 復原，Ctrl+Y 或 Ctrl+Shift+Z 重做。介面與說明支援 16 種語言。
- 經確認與遊戲相同的外部語音視為原始語音，而非替換。外部試聽僅限確認有差異的語音。未替換語音可選擇保留原音或靜音。

## Replacer 與 Custom 匯出
**Replacer：**將 `.pak`、`.utoc`、`.ucas` 一起放入 Mod 資料夾。原始語音庫決定被替換的角色，重新命名專案或資料夾不會改變目標。Replacer 資料夾名稱留空時使用應用程式語言中的基礎角色官方名。自訂角色本身的 Mod 必須保持安裝，語音封裝不包含角色。匯入時請將相關的 PAK/UTOC/UCAS 放在一起。Replacer 不啟動 Unreal Editor。

**Custom：**將 `.uasset` 放入 Unreal Mod 資料夾，將 `.pak` 放入遊戲 Mod 資料夾，兩者均帶「Custom」前綴；中間檔案與報告放入輔助資料夾。資料夾名稱隨應用程式語言變更。專案名稱必須與 Unreal 的 `Plugins` 中 Mod/外掛資料夾名完全一致。語音庫須符合自訂角色 ID 及 US/JP。請在設定中選擇 CustomProject 和 Custom Engine。

匯出按專案編號和名稱分組。每個版本以遞增編號開頭，按名稱排序時最新版本排在最後。開啟資料夾選單依序提供匯出、編輯音訊、專案；沒有專案時開啟總匯出目錄。務必在遊戲內測試。

## 專案與備份
更新前關閉應用程式並備份現有資料夾。將新ZIP解壓縮至同一安裝位置，合併資料夾並取代程式檔案。保留Projects、Cache、settings.json、偏好、計數器及預設；新ZIP不包含這些個人檔案。不要再多建一層應用程式資料夾。保持原位置：舊專案可能包含音訊的絕對路徑。仍支援缺少新選用欄位的舊專案。參閱UPDATE.md。

## 疑難排解與包含檔案
遇到存取遭拒，請解壓縮到「文件」等可寫入目錄。開啟資料夾時會透過 Windows 檔案總管重試，不要求系統管理員權限，也不變更 Windows 權限。Custom 匯入錯誤請查看應用程式指出的 `import.log` 並檢查相容 Engine/CriWare。資產必須對應目標語音庫及遊戲版本。

軟體包不包含個人專案、錄音、匯出、快取、遊戲/參考資產或作者個人設定。包含預設金鑰和工具。授權隨執行階段及相關程式庫附帶，語音引擎說明位於 `Tools/VoiceAI/NOTICE.txt`。請求支援時提供應用程式/遊戲版本、語音庫、匯出模式和記錄。本機技術驗證不能取代遊戲內測試。
