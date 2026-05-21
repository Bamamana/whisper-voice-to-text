# Whisper Voice To Form - V3 Prototype

This is an experimental version of the app for filling reusable PDF templates from spoken answers and preparing simple flat PDFs as fillable templates.

## What It Does

1. Records microphone audio.
2. Transcribes it locally with `faster-whisper`.
3. Loads a fillable PDF created with Adobe Acrobat Pro's Prepare Form tool.
4. Shows the PDF template with detected fillable fields overlaid.
5. Sends the transcript and PDF field names to Gemini Flash.
6. Shows the proposed field values on the PDF preview and in a review table.
7. Exports a filled PDF copy.
8. Saves fillable PDFs into a local `templates` folder for repeated use.
9. Auto-prepares simple flat PDFs by detecting blank lines and checkbox squares.
10. Reviews auto-prepared fields with Gemini to rename fields and suggest obvious missing fields.
11. Uses Gemini to clean up voice transcripts or turn them into editable email drafts.
12. Creates Gmail drafts through Google's Gmail API after you connect a Gmail account.

Click a highlighted field on the PDF preview to edit it in place, or double-click a row in the field table to edit a value before export.

## Important Limits

- The standard upload flow expects a real fillable PDF with AcroForm fields.
- Flat PDFs should use Auto-Prepare first so V3 can create a reusable fillable template.
- Auto-prepare is experimental and works best on clean digital forms with visible blank lines or square checkboxes.
- Gemini review is a second pass: it improves names and can add clear missing fields, but you should still inspect the template before using it repeatedly.
- Transcript cleanup replaces the text currently shown in the transcript box.
- Email drafting fills editable To, CC, BCC, Subject, and Body fields. Review them before creating a Gmail draft.
- The Google AI Studio API key is stored locally in `.gemini-api-key` in this folder.
- Gmail OAuth data is stored locally in `.gmail-token.json`. Your OAuth client secret file should be named `gmail-credentials.json` and kept local.
- Always review AI-filled values before using the exported PDF.

## Gmail Draft Setup

Gmail draft creation uses Google OAuth and is separate from your Gemini API key.

1. Create a Google Cloud OAuth client for a Desktop app.
2. Enable the Gmail API for that Google Cloud project.
3. Download the OAuth client JSON.
4. Rename it to `gmail-credentials.json`.
5. Place it in this V3 app folder.
6. Click `Connect Gmail` in the app and approve Gmail compose access.

Click `Gmail Setup Help` in the app to open these Option 1 setup steps in a separate window.

V3 requests the Gmail compose scope so it can create drafts. It does not auto-send emails.

## Windows Setup

From this folder, run:

```bat
install_windows_v3.bat
launch_windows_v3.bat
```

Use `windows_launch_v3.pyw` for normal no-console launching after setup.

The default Gemini model is `gemini-flash-latest`, but you can edit the model field in the app if Google changes model access for your account.
