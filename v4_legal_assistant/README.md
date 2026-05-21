# Whisper Voice To Form - V4 Legal Assistant

This version builds on V3 and adds lawyer-focused dictation tools, client/matter context, accessibility controls, and one-hand keyboard shortcuts.

## What It Does

1. Records microphone audio.
2. Transcribes it locally with `faster-whisper`.
3. Loads a fillable PDF created with Adobe Acrobat Pro's Prepare Form tool.
4. Shows the PDF template with detected fillable fields overlaid.
5. Sends the transcript and PDF field names to Gemini Flash.
6. Shows the proposed field values on the PDF preview and in a review table.
7. Exports a filled PDF copy or updates the original PDF after making a backup.
8. Saves fillable PDFs into a local `templates` folder for repeated use.
9. Auto-prepares simple flat PDFs by detecting blank lines and checkbox squares.
10. Reviews auto-prepared fields with Gemini to rename fields and suggest obvious missing fields.
11. Uses Gemini to clean up voice transcripts or turn them into editable email drafts.
12. Creates Gmail drafts through Google's Gmail API after you connect a Gmail account.
13. Turns dictated notes into attorney notes, billing entries, timelines, client letters, and checklists.
14. Extracts client/matter profile fields from a transcript and saves reusable local matter profiles.
15. Provides a Large Controls toggle for easier one-handed use.
16. Adds keyboard shortcuts to reduce mouse travel and small precision clicks.
17. Lets the panels below the transcript box collapse so the current task can stay larger on screen.
18. Copies the transcript to the clipboard with one button.
19. Links a saved matter profile to a local case folder and opens existing documents in their normal desktop app.
20. Points at a parent Dropbox/client folder, lists matter subfolders, and infers profile fields from the selected folder name.

Click a highlighted field on the PDF preview to edit it in place, or double-click a row in the field table to edit a value before export.

## Important Limits

- The standard upload flow expects a real fillable PDF with AcroForm fields.
- Flat PDFs should use Auto-Prepare first so V4 can create a reusable fillable template.
- Auto-prepare is experimental and works best on clean digital forms with visible blank lines or square checkboxes.
- Gemini review is a second pass: it improves names and can add clear missing fields, but you should still inspect the template before using it repeatedly.
- Transcript cleanup replaces the text currently shown in the transcript box.
- Email drafting fills editable To, CC, BCC, Subject, and Body fields. Review them before creating a Gmail draft.
- Legal drafts are editable work product for attorney review, not legal advice. The app marks uncertain items as `TO VERIFY` when possible.
- The Google AI Studio API key is stored locally in `.gemini-api-key` in this folder.
- Gmail OAuth data is stored locally in `.gmail-token.json`. Your OAuth client secret file should be named `gmail-credentials.json` and kept local.
- Matter profiles are stored locally as JSON files in the `matter-profiles` folder.
- Always review AI-filled values before using the exported PDF or updating the original PDF.
- `Update Original PDF` overwrites the loaded PDF only after creating a timestamped backup in the same folder.

## Client / Matter Profiles

Use `Extract From Transcript` after dictation to fill the profile fields from clearly stated details like client name, matter number, court, and opposing party.

After reviewing the fields, click `Save Profile` to save the profile locally. Later, choose it from the `Saved` dropdown and click `Load` to reuse it.

When an active matter folder is loaded, `Save Profile` writes a hidden `.whisper-v4-profile.json` file inside that Dropbox/matter folder. That folder-level profile is the source of truth and follows the folder through Dropbox sync.

When `Load Folder` opens a matter folder, V4 first looks for `.whisper-v4-profile.json`. If it exists, V4 loads the profile from that folder. If it does not exist yet, V4 guesses from the folder name.

The older local `matter-profiles` folder is kept only as a fallback shortcut when no Dropbox/matter folder is active.

Use `Choose Parent` to point V4 at a parent Dropbox/client folder. V4 lists the direct subfolders in `Matter Folder`. Pick a folder and click `Load Folder`; V4 uses that existing folder as the active matter folder. It loads `.whisper-v4-profile.json` from that folder when present, otherwise it tries to infer the client name, matter number, court, and opposing party from the folder name.

Use `Choose Folder` when you want to manually select one specific case or matter folder instead. Supported files in that folder are listed in the profile panel. Select a file and click `Open Selected`, or double-click the file. PDFs open inside V4 for voice-to-text filling and editing. Other files open in their normal Windows app. Saving from Word, Notepad, Excel, or another editor updates that existing file in its original folder.

For PDFs opened inside V4, use `Export Filled PDF` to save a separate copy, or `Update Original PDF` to update the existing PDF in that matter folder. V4 creates a backup first, named like `filename.backup-YYYYMMDD-HHMMSS.pdf`.

Folder-name inference works best when folders include useful labels, such as `Becky Smith - Matter 24-1187 - Travis County Court` or `Becky Smith - Case 24-1187`.

## Legal Assistant Tools

- `Formal Legal Tone` rewrites the transcript in a more formal legal style.
- `Attorney Notes` creates key facts, issues, questions, evidence needed, and next steps.
- `Billing Entry` creates a billing narrative with time marked `TO VERIFY` unless clearly dictated.
- `Timeline` creates a chronology and marks unclear dates as `TO VERIFY`.
- `Client Letter` drafts a client-facing letter and also places it in the email body box.
- `Checklist` creates completed items, pending items, missing information, documents to request, and deadlines to verify.
- `Shortcut Help` lists one-hand keyboard shortcuts for recording, drafting, PDF filling, exporting, page navigation, and large controls.

## One-Hand Shortcuts

- Use the `[v]` / `[>]` buttons above the transcript box to show or hide Matter, Legal Tools, Email, and PDF Fields panels.
- Use `Copy` next to the Transcript title to copy the full transcript to the clipboard.
- `F5` starts recording.
- `F6` stops recording and transcribes.
- `F7` creates an email draft from the transcript.
- `F8` sends the transcript to the loaded PDF fields.
- `F9` exports the filled PDF.
- `F10` updates the original loaded PDF after creating a backup.
- `Alt + Left` and `Alt + Right` move through PDF pages.
- `Ctrl + L` toggles Large Controls.
- `Ctrl + M` focuses the transcript box.
- `Ctrl + H` opens Shortcut Help.

## Gmail Draft Setup

Gmail draft creation uses Google OAuth and is separate from your Gemini API key.

1. Create a Google Cloud OAuth client for a Desktop app.
2. Enable the Gmail API for that Google Cloud project.
3. Download the OAuth client JSON.
4. Rename it to `gmail-credentials.json`.
5. Place it in this V4 app folder.
6. Click `Connect Gmail` in the app and approve Gmail compose access.

Click `Gmail Setup Help` in the app to open these Option 1 setup steps in a separate window.

V4 requests the Gmail compose scope so it can create drafts. It does not auto-send emails.

## Windows Setup

From this folder, run:

```bat
install_windows_v4.bat
launch_windows_v4.bat
```

Use `windows_launch_v4.pyw` for normal no-console launching after setup.

The default Gemini model is `gemini-flash-latest`, but you can edit the model field in the app if Google changes model access for your account.
