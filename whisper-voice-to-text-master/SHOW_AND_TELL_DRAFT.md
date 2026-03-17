# Show And Tell Draft

## Title

Free local Whisper voice-to-text app for Windows and Linux with desktop launchers, local model cache, and Windows NVIDIA GPU support

## Post body

I have been working on a free local Whisper voice-to-text app that runs from one repo on both Windows and Linux.

Current working features:
- microphone recording
- audio and video file transcription
- desktop shortcut/icon setup on both Windows and Linux
- local model caching in `model-cache/`
- optional model pre-downloads for faster later switching
- Windows NVIDIA GPU support with CUDA runtime setup in the repo
- automatic CPU fallback if CUDA is unavailable

What I focused on:
- making the repo usable by non-developers
- clear setup docs for Windows and Linux
- keeping everything local and offline after the initial setup and model downloads

Current docs in the repo:
- `README.md`
- `QUICKSTART.md`
- `FIRST_RUN.md`
- `WINDOWS_NOTES.md`

Current status:
- the repo-based install flow is working on Windows and Linux
- desktop shortcut/icon setup is working on both platforms
- Windows NVIDIA GPU support is working
- a Windows installer definition has been added, but the final packaged `Setup.exe` still needs to be built and tested

This is more of a free practical repo for people who want local voice-to-text that they can run and control themselves, not a polished commercial dictation product.

If people are interested, I can share more about the Windows CUDA setup, the cross-platform launcher flow, or the installer work.

## Short version

Built a free local Whisper voice-to-text repo for Windows and Linux.
It supports mic recording, file transcription, desktop launchers, local model caching, and Windows NVIDIA GPU support.
Repo install flow is working now; packaged Windows installer is scaffolded but not fully built/tested yet.