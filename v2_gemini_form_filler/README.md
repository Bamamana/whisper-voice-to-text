# Whisper Voice To Form - V2 Prototype

This is an experimental alternative version of the app for filling Adobe-created fillable PDFs from spoken answers.

## What It Does

1. Records microphone audio.
2. Transcribes it locally with `faster-whisper`.
3. Loads a fillable PDF created with Adobe Acrobat Pro's Prepare Form tool.
4. Sends the transcript and PDF field names to Gemini Flash.
5. Shows the proposed field values for review.
6. Exports a filled PDF copy.

## Important Limits

- The uploaded PDF should be a real fillable PDF with AcroForm fields.
- Scanned PDFs and flat PDFs are not supported in this first prototype.
- The Google AI Studio API key is stored locally in `.gemini-api-key` in this folder.
- Always review AI-filled values before using the exported PDF.

## Windows Setup

From this folder, run:

```bat
install_windows_v2.bat
launch_windows_v2.bat
```

The default Gemini model is `gemini-flash-latest`, but you can edit the model field in the app if Google changes model access for your account.
