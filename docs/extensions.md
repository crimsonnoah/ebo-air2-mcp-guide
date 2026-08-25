# Tested MCP extensions

This directory adds the features verified during the EBO Air 2 project:

- movement caps of speed 80 and 30 seconds
- reliable three-frame software stop
- persistent photos with an immediate image preview
- persistent continuous MP4 recording from the live RTSP stream
- short ordered-frame observation for visual change detection
- ten single-cycle Skill Actions
- twelve Skill Expressions
- Fish Audio WAV TTS through the existing RTC talk channel
- a continuous faster-whisper microphone listener

The drop-in MCP file is based on upstream `Playcolors-co/ha-enabot` version 0.26.100, file SHA `54cf4195ac5fc8c75f7719a63cc7e08e39cefcca`. Review changes carefully before applying it to a later upstream release.

## 1. Install the MCP extension

Clone the upstream engine and this guide next to each other, or download the patch and installer:

```bash
git clone https://github.com/Playcolors-co/ha-enabot.git /opt/ha-enabot
git clone https://github.com/crimsonnoah/ebo-air2-mcp-guide.git /opt/ebo-air2-mcp-guide
sudo bash /opt/ebo-air2-mcp-guide/scripts/install-mcp-extension.sh /opt/ha-enabot
```

The installer creates a timestamped backup and runs Python syntax validation.

In `/opt/ha-enabot/docker-compose.yml`, build from the local source:

```yaml
services:
  ebo-engine:
    # image: ghcr.io/playcolors-co/ebo-engine:latest
    build: ./ebo
```

Expose MCP only where needed. For a same-host client, bind it to loopback:

```yaml
ports:
  - "127.0.0.1:8100:8100"
```

Ensure `data/options.json` has `"mcp": true`. Then rebuild:

```bash
cd /opt/ha-enabot
docker compose up -d --build ebo-engine
docker compose logs --since=2m ebo-engine | grep -Ei 'mcp|8100|RTM|RTC'
```

## 2. Actions and expressions

The new tools are:

- `ebo_action(action=...)`
- `ebo_expression(expression=...)`

Actions require a recent `ebo_look`, clear floor space, and a robot that is not docked. They run one firmware cycle and normally finish without `ebo_stop`.

Expressions wake the robot if necessary, then use opcode 103003 with one `emojiId`.

These IDs were verified on EBO Air 2. Treat other models as experimental.

### Saving photos

`ebo_look` remains a temporary safety view and does not fill the disk with a
photo before every move. When an agent deliberately wants to keep what it sees,
call `ebo_photo` instead:

```text
ebo_photo(node="ebo", label="optional-memory-name")
```

The tool returns both an image preview and the saved path. By default photos are
written privately to `/data/ebo-photos/`, which corresponds to
`./data/ebo-photos/` on a host using the example Compose volume. They survive
container rebuilds and are already covered by the repository's `data/` ignore
rule. This captures the current live JPEG on the server; it does not add the
photo to EBO HOME or the robot's SD-card album.

### Recording continuous video

Use `ebo_record` when the goal is to keep a real continuous video rather
than ask the AI to compare sampled still frames:

```text
ebo_record(node="ebo", seconds=10, label="optional-memory-name", include_audio=true)
```

Recordings default to 10 seconds and are capped at 30 seconds by
`EBO_RECORD_MAX_SECONDS`. They are stored privately under
`/data/ebo-recordings/` (normally `./data/ebo-recordings/` on the
Compose host), survive container rebuilds, and are not uploaded to EBO HOME or
the robot's SD card. The tool copies the existing H.264 video stream without
re-encoding; when an audio track exists and `include_audio` is true, it is
converted to AAC for broad MP4 compatibility. A JPEG cover preview is returned
with the saved path and file size.

Call `ebo_wake` first. Recording refuses a known stale pre-wake frame and
also refuses when the camera or RTSP stream is unavailable. The MP4 itself is a
saved artifact for people or downstream video-capable software; use
`ebo_watch` when the current AI client needs to reason about motion through an
ordered set of images.

### Watching short changes

`ebo_watch` samples the live camera over a short period and returns timestamped
JPEG frames in chronological order so an image-capable agent can compare what
changed:

```text
ebo_watch(node="ebo", seconds=6, interval=1)
```

The default observation is six seconds with one requested frame per second.
For safety and response-size control, the server caps observations at 12 seconds
and 12 frames. When that cap applies, samples are spread across the full requested
duration. Watch frames are temporary and are not added to `/data/ebo-photos/`;
call `ebo_photo` to preserve a chosen moment.

This is ordered still-frame observation, not continuous video understanding or
an EBO HOME recording. Wake the camera first if EBO is asleep. Live Air 2
testing confirmed that an image-capable agent could compare the ordered frames
and identify gesture changes.

The extended `ebo_wake` records the pre-wake JPEG, sends both the full wake and
camera-on commands, and waits up to 20 seconds for different JPEG bytes before
reporting that the live camera is ready. This prevents the panel's intentionally
persisted last-good frame from being mistaken for a current view. While that
freshness check is pending, `ebo_look`, `ebo_watch`, and `ebo_photo` refuse the
known pre-wake image rather than presenting or saving it as live.

## 3. Fish Audio TTS

Copy the sanitized template into the private runtime directory:

```bash
cp /opt/ebo-air2-mcp-guide/examples/fishaudio-config.example.json \
  /opt/ha-enabot/data/fishaudio-config.json
chmod 600 /opt/ha-enabot/data/fishaudio-config.json
```

Replace `YOUR_FISH_AUDIO_API_KEY` and `YOUR_FISH_AUDIO_VOICE_ID`, and set `"talk": true` in `data/options.json`.

The extended `ebo_say`:

1. reuses a healthy RTC session instead of rebuilding it for every sentence;
2. opens camera/RTC only when it is actually off;
3. asks Fish Audio for a 16 kHz WAV;
4. submits the file to the bridge's existing `talk` command;
5. maintains `data/ebo-speaking-until` so the ASR listener ignores EBO's own voice.

Test without movement:

```text
Call ebo_say and say: The EBO voice test is working.
```

Useful logs:

```bash
docker compose logs --since=5m ebo-engine \
  | grep -E '\[say-timing\]|\[talk\]|\[RTC\]'
```

## 4. Local faster-whisper ASR

The listener runs on the Docker host and reads the RTSP audio track through ffmpeg inside the container.

```bash
cd /opt/ebo-air2-mcp-guide
python3 -m venv asr-venv
asr-venv/bin/pip install -r requirements-asr.txt
```

The sample service expects the upstream engine at `/opt/ha-enabot` and this guide at `/opt/ebo-air2-mcp-guide`. Install it:

```bash
sudo cp systemd/ebo-asr-listener.service.example /etc/systemd/system/ebo-asr-listener.service
sudo systemctl daemon-reload
sudo systemctl enable --now ebo-asr-listener.service
sudo journalctl -u ebo-asr-listener.service -f
```

The default output is the journal. To connect transcripts to an AI/chat bridge, configure exactly one adapter in the service:

- `EBO_ASR_WEBHOOK_URL` plus an optional bearer token; or
- `EBO_ASR_COMMAND`, which receives the transcript on stdin.

There are no Telegram usernames, tmux sessions, or personal paths in the public listener.

Tested latency-oriented defaults:

| Setting | Value |
|---|---:|
| model | `small` |
| compute | CPU int8 |
| language | `zh` |
| beam size | 3 |
| end silence | 1.0 s |
| VAD | on |

Non-empty partial PCM frames are padded with silence. Only a zero-byte frame triggers recovery. After repeated empty streams, the listener cycles microphone listen off/on without unnecessarily rebuilding a healthy RTC session.

## 5. Roll back

Stop the container, restore the timestamped `ebo_mcp.py.backup-*` file, and rebuild:

```bash
cd /opt/ha-enabot
cp ebo/ebo_mcp.py.backup-YYYYMMDD-HHMMSS ebo/ebo_mcp.py
docker compose up -d --build ebo-engine
```

Keep all credentials in `data/`; this repository's `.gitignore` excludes the common secret paths.
