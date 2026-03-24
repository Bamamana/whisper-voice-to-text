# Show And Tell Draft

## Title

Free local Whisper voice-to-text app for Windows and Linux with desktop launchers, local model cache, a working Windows installer, and Windows NVIDIA GPU support

## Post body

I have been working on a free local Whisper voice-to-text app that runs from one repo on both Windows and Linux.

Repo:
https://github.com/Bamamana/whisper-voice-to-text

What it currently does:
- microphone recording
- audio and video file transcription
- desktop shortcut or icon setup on both Windows and Linux
- local model caching in `model-cache/`
- optional model pre-downloads so switching models is faster later
- Windows NVIDIA GPU support with CUDA runtime libraries installed into the app environment
- automatic CPU fallback if CUDA is unavailable

Windows installer:
- the packaged Windows installer is `WhisperVoiceToTextSetup.exe`
- if you build it from the repo, run `build_windows_installer.bat`
- the generated installer is written to `dist\windows-installer\WhisperVoiceToTextSetup.exe`
- the installer copies the app into `%LOCALAPPDATA%\Programs\Whisper Voice To Text`, creates Start Menu shortcuts, can create a desktop shortcut, and runs the Windows setup flow for you
- on a clean Windows machine it can bootstrap Python and download an app-local FFmpeg build automatically when they are missing

If someone wants the repo-based Windows path instead of the packaged installer, they can still just run `setup_windows.bat` from the repo folder.

What I focused on:
- making the repo usable by non-developers
- clear setup docs for Windows and Linux
- keeping everything local and offline after the initial setup and model downloads
- making models download once and then be reused locally

Main docs:
- `README.md`
- `QUICKSTART.md`
- `FIRST_RUN.md`
- `WINDOWS_NOTES.md`

Current status:
- the repo-based install flow is working on Windows and Linux
- the packaged Windows installer is now working
- desktop shortcut or icon setup is working on both platforms
- Windows NVIDIA GPU support is working
- the launcher falls back to CPU automatically if CUDA is not available

This is more of a free practical repo for people who want local voice-to-text that they can run and control themselves, not a polished commercial dictation product.

If people are interested, I can share more about the Windows installer flow, the Windows CUDA setup, or the cross-platform launcher setup.

## Short version

Built a free local Whisper voice-to-text repo for Windows and Linux:
https://github.com/Bamamana/whisper-voice-to-text

It supports mic recording, file transcription, desktop launchers, local model caching, a working Windows installer, and Windows NVIDIA GPU support.

Windows installer file: `WhisperVoiceToTextSetup.exe`
If you build it from the repo, it is generated at `dist\windows-installer\WhisperVoiceToTextSetup.exe`.