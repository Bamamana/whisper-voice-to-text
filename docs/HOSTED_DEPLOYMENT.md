# Hosted Deployment Runbook

This guide deploys updates to the hosted Whisper and Voice Grading app at
`https://whisper.classprepped.com`.

The Cloudflare tunnel and Access policy already point to the local hosted app.
Normal application updates only require rebuilding the browser file and
restarting its user-level systemd service.

## Architecture

```text
Browser -> Cloudflare Access/Tunnel -> 127.0.0.1:8179 hosted_server.py -> Lemonade 127.0.0.1:13305
```

- Source UI: `webapp-api-only/index.html` and `webapp-api-only/js/`
- Build script: `webapp-api-only/build_singlefile.py`
- Deployed browser file: `Whisper-V1-API.html`
- Hosted service: `whisper-v1-hosted.service`
- Lemonade service: `lemond.service`

## Deploy An App Update

Run these commands on the Linux server:

```bash
cd /home/steven/github/Bamamana/whisper-voice-to-text

# Check JavaScript syntax for the files changed in this update.
node --input-type=module --check < webapp-api-only/js/voice-grading.js

# Generate the single-file page served by the hosted service.
python3 webapp-api-only/build_singlefile.py

# Check the generated page's inlined JavaScript.
awk 'BEGIN { scripts = 0 } /<script>/{ scripts += 1; if (scripts == 2) { in_script = 1; next } } in_script && /<\/script>/{ exit } in_script { print }' Whisper-V1-API.html | node --input-type=module --check

# Put the rebuilt page into service.
systemctl --user restart whisper-v1-hosted.service
systemctl --user is-active whisper-v1-hosted.service
```

Expected final output is `active`.

## Verify The Deployment

Check that the local service serves the rebuilt app:

```bash
curl --fail --silent http://127.0.0.1:8179/ > /dev/null
```

Then open `https://whisper.classprepped.com`, sign in through Cloudflare Access,
and hard-refresh the page with `Ctrl+Shift+R`.

For a UI change, search the served page for a unique phrase from that change:

```bash
curl --fail --silent http://127.0.0.1:8179/ | rg -q 'unique text from the update'
```

## Check Service Health And Logs

```bash
systemctl --user status whisper-v1-hosted.service --no-pager
systemctl --user status lemond.service --no-pager
journalctl --user -u whisper-v1-hosted.service -n 100 --no-pager
journalctl --user -u lemond.service -n 100 --no-pager
```

The hosted service needs Lemonade available at `http://127.0.0.1:13305` for
transcription, AI grading, model discovery, and live transcription.

## When The Server Code Changes

Changes to `webapp-api-only/hosted_server.py` do not require a browser rebuild
unless the browser source also changed. Validate Python syntax and restart:

```bash
cd /home/steven/github/Bamamana/whisper-voice-to-text
python3 -m py_compile webapp-api-only/hosted_server.py
systemctl --user restart whisper-v1-hosted.service
systemctl --user is-active whisper-v1-hosted.service
```

## If The Service Will Not Start

The server requires the generated file at `Whisper-V1-API.html`. Rebuild it and
read the service logs:

```bash
cd /home/steven/github/Bamamana/whisper-voice-to-text
python3 webapp-api-only/build_singlefile.py
systemctl --user restart whisper-v1-hosted.service
journalctl --user -u whisper-v1-hosted.service -n 100 --no-pager
```

If requests to `/v1/*` fail after the page loads, verify Lemonade separately:

```bash
systemctl --user is-active lemond.service
curl --fail --silent http://127.0.0.1:13305/v1/models > /dev/null
```

## Roll Back A Bad Update

Use Git to restore the last known-good application source, rebuild, and restart.
Do not use `git reset --hard` if the working tree includes unrelated changes.

```bash
cd /home/steven/github/Bamamana/whisper-voice-to-text
git log --oneline -5
git restore --source <known-good-commit> -- webapp-api-only/index.html webapp-api-only/js
python3 webapp-api-only/build_singlefile.py
systemctl --user restart whisper-v1-hosted.service
systemctl --user is-active whisper-v1-hosted.service
```

Review the restored files with `git diff` before rebuilding if the server has
uncommitted work that must be preserved.

## Service Definition

The installed user-level service is:

```text
~/.config/systemd/user/whisper-v1-hosted.service
```

It runs:

```text
/usr/bin/python3 /home/steven/github/Bamamana/whisper-voice-to-text/webapp-api-only/hosted_server.py --port 8179
```

After changing this service definition, reload systemd before restarting:

```bash
systemctl --user daemon-reload
systemctl --user restart whisper-v1-hosted.service
```