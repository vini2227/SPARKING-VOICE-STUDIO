# Sparking Zero Voice Studio — 便携版

## 安装
1. 将整个 ZIP 解压到可写文件夹，例如“文档”。不要在 ZIP 内运行，也不要安装到 Program Files。
2. 打开 `Sparking Zero Voice Studio.exe`。已包含 Python、音频工具、UnrealPak 和 Oodle，无需另行安装 Python、Codex 或 Excel。`Preparar ferramentas.bat` 是可选的工具检查。
3. 在设置中选择游戏安装目录。Replacer 模式下将 CustomProject 和 Custom Engine 留空，即可直接读取游戏参考数据。游戏包密钥自动配置，无需 `keys.json`。
4. 保存设置并打开语音库。新安装默认使用英语。选择文件夹之前也可更改语言。更新时保留原有 `settings.json` 可保留已选语言。

## 系统要求
- 64 位 Windows 10 或 11、.NET Framework 4.8，以及与所附 Unreal 工具兼容的 64 位 Visual C++ 运行库。
- 已安装 DRAGON BALL Sparking! ZERO，并包含所用游戏版本的 `.pak`、`.utoc`、`.ucas` 文件。
- **不包含 Custom Engine 和 CustomProject。** Custom 导出需要兼容的 Unreal 5.1 Custom Engine、CriWare 插件及其 DLL，以及包含兼容语音参考的 CustomProject。普通 Unreal 安装不足以完成此导出。
- Replacer 的 CustomProject 为可选项。配置后使用其参考数据；未配置则读取游戏，游戏容器变化时更新缓存。

## 主要功能
- US/JP 语音库、官方本地化角色名、Cue IDs、功能、互动标签、筛选器、重复语音及原始/编辑音频比较。
- 导入音频、视频和外部语音包；麦克风录音；裁剪、增益、削波修复及音量最大化。
- 本地语音增强、背景分离及混响、回声、音高、低音/高音、双重语音、失真、收音机效果。应用前请试听，质量取决于录音。
- 0.25x 至 3.00x 速度、默认启用保留音高（可关闭）、预览及撤销/重做。保留音高时只改变节奏。
- 保存与恢复、最近项目、共享/合并、语音库迁移、按标签/功能复制。Ctrl+Z 撤销，Ctrl+Y 或 Ctrl+Shift+Z 重做。界面与帮助支持 16 种语言。
- 经确认与游戏相同的外部语音视为原始语音，而非替换。外部试听仅限确认存在差异的语音。未替换语音可选择保留原音或静音。

## Replacer 与 Custom 导出
**Replacer：**将 `.pak`、`.utoc`、`.ucas` 一起放入 Mod 文件夹。原始语音库决定被替换的角色，重命名项目或文件夹不会改变目标。Replacer 文件夹名称留空时使用应用语言中的基础角色官方名。自定义角色本身的 Mod 必须保持安装，语音包不包含角色。导入时请将关联的 PAK/UTOC/UCAS 放在一起。Replacer 不启动 Unreal Editor。

**Custom：**将 `.uasset` 放入 Unreal Mod 文件夹，将 `.pak` 放入游戏 Mod 文件夹，两者均带“Custom”前缀；中间文件与报告放入辅助文件夹。文件夹名称随应用语言变化。项目名称必须与 Unreal 的 `Plugins` 中 Mod/插件文件夹名完全一致。语音库须匹配自定义角色 ID 及 US/JP。请在设置中选择 CustomProject 和 Custom Engine。

导出按项目编号和名称分组。每个版本以递增编号开头，按名称排序时最新版本排在最后。打开文件夹菜单依次提供导出、编辑音频、项目；没有项目时打开总导出目录。务必在游戏内测试。

## 项目与备份
更新前关闭应用并备份现有文件夹。将新ZIP解压到同一安装位置，合并文件夹并替换程序文件。保留Projects、Cache、settings.json、偏好、计数器和预设；新ZIP不包含这些个人文件。不要再嵌套一层应用文件夹。保持原位置：旧项目可能包含音频的绝对路径。仍支持缺少新可选字段的旧项目。参阅UPDATE.md。

## 故障排查与包含文件
遇到访问被拒绝，请解压到“文档”等可写目录。打开文件夹时会通过 Windows 文件资源管理器重试，不请求管理员权限，也不更改 Windows 权限。Custom 导入错误请查看应用指出的 `import.log` 并检查兼容 Engine/CriWare。资源必须对应目标语音库及游戏版本。

软件包不包含个人项目、录音、导出、缓存、游戏/参考资源或作者个人设置。包含默认密钥和工具。许可证随运行库及相关库附带，语音引擎说明位于 `Tools/VoiceAI/NOTICE.txt`。请求支持时请提供应用/游戏版本、语音库、导出模式和日志。本地技术验证不能代替游戏内测试。
