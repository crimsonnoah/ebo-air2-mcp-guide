# Troubleshooting

Start with:

```bash
cd /opt/ha-enabot
docker compose ps
docker compose logs --since=10m ebo-engine | tail -300
```

## Container starts but MCP is missing

Confirm `data/options.json` contains `"mcp": true`, then recreate the container:

```bash
docker compose up -d --force-recreate
docker compose logs --since=2m ebo-engine | grep -Ei 'mcp|8100'
```

Expected: `starting MCP server` and an address ending in `:8100/mcp`.

## HTTP 401 from MCP

The bearer token is missing or wrong. The MCP bearer token must match `api_token` in `data/options.json` or `/data/api_token` inside the container.

Never paste the real token into an issue or screenshot.

## Robot is listed but does not respond

- Close the EBO HOME live-control screen; the app and bridge can compete for the account session.
- Confirm `[RTM] login and subscribe ok` and `[RTC] connected`.
- Wake the robot and wait several seconds before requesting a camera image.
- Recreate the container only after checking the logs.

## MCP command returns success but an action does nothing

A bridge HTTP 200 only confirms that the local command was accepted. It does not prove the firmware executed an opcode.

Enable debug logging temporarily and inspect panel/RTM messages. Action and expression IDs in this project were verified specifically on EBO Air 2; other models and firmware versions may differ.

## Movement does not start

- Speed values around 8 were ineffective on the tested Air 2. Start near 20.
- `ebo_move` requires a fresh `ebo_look`; the safety window expires quickly.
- Movement is refused while charging or docked.
- Confirm the direction name is supported.

## Stop arrives but the robot finishes the whole timed move

Use a recent upstream engine containing the movement control-loop final-zero fix. Then recreate the image/container rather than only restarting an old container.

Remember that an AI may not call `ebo_stop` until it has finished reasoning. For predictable travel, prefer a short `seconds` value on `ebo_move`. Stop is not hardware-grade emergency braking.

## Camera shows an old frame

- Update and reinstall the current MCP extension. Its `ebo_wake` remembers the
  pre-wake JPEG and does not report success until a different frame arrives.
- A successful wake now says `fresh live camera frame confirmed`. If it instead
  says the camera is not fresh yet, inspect RTC/video logs and retry wake; do not
  treat the returned cache as a live view.
- After an unsuccessful wake, `ebo_look`, `ebo_watch`, and `ebo_photo` refuse the
  known stale JPEG until a new frame replaces it.
- Confirm `[RTC] connected` and that fresh video frames appear in logs.
- A cached Home Assistant/dashboard image is not proof that the live camera is updating.

## Microphone repeatedly reconnects

Diagnostic messages such as `short microphone frame: 0/8000` mean the RTC audio stream temporarily stopped. Non-empty short frames can be padded by the optional ASR listener; zero-byte frames require stream recovery.

After recovery, wait for:

```text
microphone PCM connected: 8000-byte frames
READY - SPEAK NOW
```

An icon that says the ear is on does not by itself prove PCM is arriving.

## Speech recognition is slow or inaccurate

The tested CPU/int8 faster-whisper setup used:

- model: `small`
- language: `zh`
- beam size: `3`
- end silence: `1.0` second
- VAD enabled
- `condition_on_previous_text=False`

Measured valid-speech transcription was usually about 2.1–2.7 seconds on the tested host. Hardware and sentence length change this substantially.

## TTS reaches the bridge but EBO is silent

- Confirm the RTC channel is connected.
- Confirm the talk extension is installed; the upstream text `say` command is not the Fish Audio WAV path.
- Check that the generated file is a 16 kHz mono WAV.
- Do not reset a healthy RTC/audio session before every sentence.
- Verify logs show both `playing` and `push-to-talk released`.

## Debug logging

Use `debug` only while diagnosing because raw protocol logs can contain device and network details. Return to `info` afterward and sanitize logs before sharing.

## What to include in an issue

Include:

- EBO model and firmware version
- Docker image/version or source commit
- Exact tool name and sanitized parameters
- Expected and observed behavior
- A short sanitized log excerpt

Remove emails, passwords, keys, tokens, serial numbers, MAC addresses, SSIDs, private/public IP addresses, voice IDs, and Telegram identifiers.
