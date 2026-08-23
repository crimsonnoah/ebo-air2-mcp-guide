# EBO Air 2 MCP deployment guide

This guide describes the tested Docker/amd64 path for connecting an EBO Air 2 to an MCP-capable AI client. It uses the unofficial community engine from [Playcolors-co/ha-enabot](https://github.com/Playcolors-co/ha-enabot).

> [!WARNING]
> This is an unofficial, reverse-engineered integration. It depends on Enabot cloud services and may break after app, firmware, or cloud changes. Supervise the robot whenever movement is enabled.

## 1. What you need

- An Enabot EBO Air 2 registered in the EBO HOME app
- A Linux **x86_64/amd64** host; the bundled Agora SDK is not available for ARM
- Docker Engine with Docker Compose v2
- The Enabot account email and password
- The two app crypto constants obtained from **your own** EBO HOME APK
- A long random token for the local API and MCP server
- Optional: Home Assistant, Fish Audio, and a local ASR listener

The robot and Docker host do not have to share a LAN for the cloud control channel. Camera viewing and remote MCP access still need appropriate network routing.

## 2. Prepare a clean directory

```bash
sudo mkdir -p /opt/ebo-air2-mcp
sudo chown "$USER":"$USER" /opt/ebo-air2-mcp
cd /opt/ebo-air2-mcp
mkdir -p data
```

Download this repository's two example files into that directory:

- `examples/docker-compose.example.yml` as `docker-compose.yml`
- `examples/options.example.json` as `data/options.json`

Keep `data/` private. It contains account credentials and the MCP token.

## 3. Obtain the app crypto constants

The engine needs `payload_key` and `sign_key`. They are app-level constants embedded in EBO HOME and are deliberately not included in this repository.

Use the instructions in the upstream [app-key guide](https://github.com/Playcolors-co/ha-enabot/blob/main/ebo/docs/GET-APP-KEYS.md):

1. Export your own EBO HOME APK (`com.enabot.ebox.intl`) with an APK extractor or Android platform-tools/ADB.
2. Open the APK in jadx.
3. Find `com.enabot.lib_ebo.netWork.ServerEncryptHelper`.
4. Identify the AES payload constant and signature constant.
5. Put them only in your private `data/options.json`.

Do not publish the APK, extracted proprietary libraries, or either constant.

## 4. Configure the engine

Edit `data/options.json` and replace every `YOUR_...` placeholder. Generate the API token locally:

```bash
openssl rand -hex 32
```

Recommended tested values:

- `mcp`: `true`
- `video`: `true`
- `audio`: `true`
- `talk`: `true` only when the talk/TTS extension is installed
- `log_level`: `info` for normal use, `debug` only while diagnosing
- movement cap in Compose: speed `80`, duration `30.0`

Protect the file:

```bash
chmod 600 data/options.json
```

## 5. Start the container

```bash
cd /opt/ebo-air2-mcp
docker compose pull
docker compose up -d
docker compose logs --since=2m ebo-engine
```

A healthy startup normally contains messages similar to:

```text
[MQTT] connected rc=0
[RTM] login and subscribe ok
[RTC] connected
[panel] data API on :8098
[mcp] EBO MCP server on http://0.0.0.0:8100
```

Only one active control session per account is reliable. Close the official EBO HOME live-control screen while using the bridge.

## 6. Verify the private data API

Run the check inside the container so the token is not copied into the command:

```bash
docker compose exec -T ebo-engine sh -c '
T=$(cat /data/api_token 2>/dev/null || jq -r .api_token /data/options.json)
curl -fsS -H "X-Enabot-Token: $T" http://127.0.0.1:8098/api/robots | jq
'
```

Expected result: at least one robot with `online: true`.

## 7. Verify MCP without moving the robot

Connect a client using:

- URL: `http://127.0.0.1:8100/mcp` when the client runs on the same host
- Authentication: `Authorization: Bearer YOUR_API_TOKEN`

First call only safe tools:

1. `ebo_list`
2. `ebo_state`
3. `ebo_wake`
4. wait 2–3 seconds
5. `ebo_look`

Do not test movement until the robot is on a flat, open floor away from stairs and edges.

## 8. Movement test

The tested Air 2 did not reliably move at speed 8. Begin around speed 20:

1. Call `ebo_look` and confirm the path is clear.
2. Call `ebo_move` with `direction=forward`, `speed=20`, `seconds=1`.
3. Confirm it stops automatically.
4. Re-look before every following movement.

The configured upper bounds are speed 80 and 30 seconds. These are caps, not recommended defaults.

`ebo_stop` stops ordinary MCP wheel-vector movement. It is software over a cloud link and is **not** a hardware emergency stop. Single-cycle Skill Actions normally finish on their own and do not need a stop call.

## 9. Optional layers

- Home Assistant: follow the upstream [standalone guide](https://github.com/Playcolors-co/ha-enabot/blob/main/STANDALONE.md).
- Client configuration: see [client-setup.md](client-setup.md).
- Failures and logs: see [troubleshooting.md](troubleshooting.md).
- Fish Audio TTS and local faster-whisper ASR are optional extensions. Their credentials must stay outside Git.

## 10. Updating

```bash
cd /opt/ebo-air2-mcp
cp data/options.json data/options.json.backup
docker compose pull
docker compose up -d
docker compose logs --since=2m ebo-engine
```

Back up only to a private location. Never attach the real options file to a public GitHub issue.
