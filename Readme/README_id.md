# Sparking Zero Voice Studio — Edisi portabel

## Instalasi
1. Ekstrak seluruh ZIP ke folder yang dapat ditulis, misalnya Documents. Jangan jalankan dari dalam ZIP atau pasang di Program Files.
2. Buka `Sparking Zero Voice Studio.exe`. Python, alat audio, UnrealPak, dan Oodle sudah disertakan; tidak perlu memasang Python, Codex, atau Excel terpisah. `Preparar ferramentas.bat` adalah pemeriksaan alat opsional.
3. Pilih folder instalasi game di Pengaturan. Untuk Replacer, kosongkan CustomProject dan Custom Engine agar referensi dibaca dari game. Kunci paket diatur otomatis; tidak memerlukan `keys.json`.
4. Simpan pengaturan dan buka bank suara. Instalasi baru dimulai dalam bahasa Inggris. Bahasa dapat diubah sebelum memilih folder. Pembaruan dengan `settings.json` lama mempertahankan pilihan bahasa.

## Persyaratan
- Windows 10 atau 11, 64-bit; .NET Framework 4.8 dan runtime Visual C++ 64-bit yang kompatibel dengan alat Unreal yang disertakan.
- DRAGON BALL Sparking! ZERO terpasang, dengan file `.pak`, `.utoc`, dan `.ucas` untuk versi game yang digunakan.
- **Custom Engine dan CustomProject tidak disertakan.** Ekspor Custom memerlukan Custom Engine Unreal 5.1 yang kompatibel dengan plugin CriWare beserta DLL-nya, serta CustomProject dengan referensi suara yang kompatibel. Instalasi Unreal biasa tidak cukup.
- CustomProject opsional untuk Replacer. Jika diatur, referensi berasal darinya; jika tidak, aplikasi membacanya dari game dan memperbarui cache ketika kontainer game berubah.

## Fitur utama
- Bank US/JP, nama karakter resmi sesuai bahasa, Cue IDs, fungsi, tag interaksi, filter, suara berulang, serta perbandingan audio asli dan hasil edit.
- Impor audio, video, dan paket suara eksternal; rekaman mikrofon; pemotongan, gain, perbaikan clipping, dan maksimalisasi volume.
- Peningkatan suara, isolasi latar, dan efek lokal: reverb, echo, pitch, bass/treble, suara ganda, distorsi, dan radio. Dengarkan pratinjau sebelum menerapkan; kualitas bergantung pada rekaman.
- Kecepatan 0,25x–3,00x, mempertahankan nada aktif secara default (dapat dinonaktifkan), pratinjau, dan undo/redo. Pertahankan nada untuk mengubah tempo saja.
- Simpan dan pulihkan, proyek terbaru, berbagi/gabung, migrasi bank, dan salin berdasarkan tag/fungsi. Ctrl+Z membatalkan; Ctrl+Y atau Ctrl+Shift+Z mengulangi. Antarmuka dan bantuan mendukung 16 bahasa.
- Suara eksternal yang dipastikan identik dengan game dianggap asli, bukan pengganti. Pratinjau eksternal hanya untuk perbedaan yang dikonfirmasi. Pilih audio asli atau senyap untuk suara yang belum diganti.

## Ekspor Replacer dan Custom
**Replacer:** menempatkan `.pak`, `.utoc`, dan `.ucas` bersama di folder mod. Bank asli menentukan karakter yang diganti; mengganti nama proyek atau folder tidak mengubah target. Nama folder kosong memakai nama resmi karakter dasar dalam bahasa aplikasi. Mod karakter kustom harus tetap terpasang: paket suara tidak menyertakan karakter. Saat mengimpor, simpan PAK/UTOC/UCAS terkait bersama. Replacer tidak menjalankan Unreal Editor.

**Custom:** menempatkan `.uasset` di folder mod Unreal dan `.pak` di folder mod game, masing-masing berawalan “Custom”; file perantara dan laporan masuk ke folder pendukung. Nama folder mengikuti bahasa aplikasi. Nama proyek harus sama persis dengan folder mod/plugin di `Plugins` Unreal. Bank harus sesuai ID karakter kustom dan US/JP. Pilih CustomProject dan Custom Engine di Pengaturan.

Ekspor dikelompokkan menurut nomor dan nama proyek. Setiap versi diawali nomor meningkat, sehingga yang terbaru berada terakhir saat diurutkan berdasarkan nama. Buka folder menawarkan ekspor, audio edit, lalu proyek; tanpa proyek membuka folder ekspor umum. Selalu uji di dalam game.

## Proyek dan cadangan
Tutup aplikasi dan cadangkan folder sebelum memperbarui. Ekstrak ZIP baru ke instalasi yang sama, gabungkan folder dan ganti file program. Pertahankan Projects, Cache, settings.json, preferensi, penghitung dan preset; file pribadi tidak disertakan dalam ZIP baru. Jangan membuat folder aplikasi bertingkat tambahan. Pertahankan lokasi karena proyek lama dapat berisi jalur audio absolut. Proyek lama tanpa kolom opsional baru tetap didukung. Lihat UPDATE.md.

## Masalah dan file yang disertakan
Jika akses ditolak, ekstrak ke folder yang dapat ditulis seperti Documents. Pembukaan folder mencoba lagi melalui Windows Explorer; tidak meminta hak administrator atau mengubah izin Windows. Untuk kesalahan Custom, periksa `import.log` yang ditunjukkan dan kompatibilitas Engine/CriWare. Assets harus sesuai bank dan versi yang dituju.

Paket tidak berisi proyek pribadi, rekaman, ekspor, cache, assets game/referensi, atau pengaturan pribadi pembuat. Kunci standar dan alat disertakan. Lisensi menyertai runtime dan pustaka; kredit mesin suara ada di `Tools/VoiceAI/NOTICE.txt`. Untuk dukungan, berikan versi aplikasi/game, bank, mode ekspor, dan log. Pemeriksaan lokal tidak menggantikan pengujian di dalam game.
