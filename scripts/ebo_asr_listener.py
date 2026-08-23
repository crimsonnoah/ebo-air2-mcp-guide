#!/usr/bin/env python3
"""Continuous EBO microphone ASR with generic output adapters.

The listener reads the audio track from the bridge's RTSP stream, detects an
utterance, transcribes it with faster-whisper, then either prints it, POSTs it
to a webhook, or passes it to a command on stdin.
"""

from __future__ import annotations

import json
import math
import os
import select
import shlex
import subprocess
import sys
import time
import urllib.request

import numpy as np
from faster_whisper import WhisperModel

RATE = int(os.environ.get("EBO_ASR_RATE", "16000"))
CHANNELS = 1
SAMPLE_BYTES = 2
FRAME_SECONDS = float(os.environ.get("EBO_ASR_FRAME_SECONDS", "0.25"))
FRAME_BYTES = int(RATE * CHANNELS * SAMPLE_BYTES * FRAME_SECONDS)
START_RMS_THRESHOLD = float(os.environ.get("EBO_ASR_START_RMS", "0.006"))
END_RMS_THRESHOLD = float(os.environ.get("EBO_ASR_END_RMS", "0.0035"))
END_SILENCE_SECONDS = float(os.environ.get("EBO_ASR_END_SILENCE", "1.0"))
MAX_UTTERANCE_SECONDS = float(os.environ.get("EBO_ASR_MAX_SECONDS", "30"))
PRE_ROLL_FRAMES = int(os.environ.get("EBO_ASR_PRE_ROLL", "3"))
MODEL_NAME = os.environ.get("EBO_ASR_MODEL", "small")
LANGUAGE = os.environ.get("EBO_ASR_LANGUAGE", "zh")
BEAM_SIZE = int(os.environ.get("EBO_ASR_BEAM_SIZE", "3"))
CONTAINER = os.environ.get("EBO_CONTAINER", "ebo-engine")
API = os.environ.get("EBO_API", "http://127.0.0.1:8098").rstrip("/")
RTSP_URL = os.environ.get("EBO_RTSP_URL", "rtsp://127.0.0.1:8554/ebo")
DATA_DIR = os.environ.get("EBO_DATA_DIR", "/opt/ebo-air2-mcp/data")
SPEAKING_UNTIL = os.environ.get(
    "EBO_SPEAKING_UNTIL", os.path.join(DATA_DIR, "ebo-speaking-until")
)
ONCE = "--once" in sys.argv


def log(message: str) -> None:
    print(time.strftime("%F %T"), message, flush=True)


def speaking_until() -> float:
    try:
        with open(SPEAKING_UNTIL, encoding="utf-8") as f:
            return float(f.read().strip())
    except Exception:
        return 0.0


def get_token() -> str:
    if os.environ.get("EBO_API_TOKEN"):
        return os.environ["EBO_API_TOKEN"]
    options = os.path.join(DATA_DIR, "options.json")
    try:
        with open(options, encoding="utf-8") as f:
            token = json.load(f).get("api_token", "")
        if token:
            return token
    except Exception:
        pass
    output = subprocess.check_output(
        ["docker", "inspect", CONTAINER, "--format", "{{range .Config.Env}}{{println .}}{{end}}"],
        text=True,
    )
    for line in output.splitlines():
        if line.startswith("EBO_API_TOKEN="):
            return line.split("=", 1)[1]
    raise RuntimeError("EBO_API_TOKEN not found")


def api_request(token: str, path: str, body: dict | None = None) -> bytes:
    headers = {"X-Enabot-Token": token}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    request = urllib.request.Request(
        API + path,
        headers=headers,
        data=data,
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def post_cmd(token: str, node: str, suffix: str, payload: str) -> None:
    api_request(token, "/api/cmd", {"node": node, "suffix": suffix, "payload": payload})


def ensure_audio_channel(token: str) -> str:
    """Request listening without tearing down a healthy RTC session."""
    while True:
        try:
            robots = json.loads(api_request(token, "/api/robots"))
            if not robots:
                raise RuntimeError("no EBO robot is online yet")
            node = robots[0]["node"]
            while speaking_until() > time.time():
                time.sleep(1)
            camera_on = str(robots[0].get("camera", "")).lower() == "on"
            if not camera_on:
                log("camera is off; opening RTC stream once")
                post_cmd(token, node, "camera/set", "on")
                time.sleep(8)
            post_cmd(token, node, "listen/set", "on")
            log("requested microphone on existing RTC for node=" + node)
            return node
        except Exception as exc:
            log("waiting for EBO RTC: " + repr(exc))
            time.sleep(3)


def start_ffmpeg() -> subprocess.Popen:
    return subprocess.Popen(
        [
            "docker", "exec", CONTAINER,
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-rtsp_transport", "tcp", "-i", RTSP_URL,
            "-map", "0:a:0", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )


def read_exact(proc: subprocess.Popen, size: int, timeout: float = 3.0) -> bytes:
    data = bytearray()
    deadline = time.time() + timeout
    fd = proc.stdout.fileno()
    while len(data) < size and time.time() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.5)
        if not ready:
            if proc.poll() is not None:
                break
            continue
        chunk = os.read(fd, size - len(data))
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def pcm_rms(pcm: bytes) -> float:
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if audio.size == 0:
        return 0.0
    audio /= 32768.0
    return math.sqrt(float(np.mean(audio * audio)))


def read_utterance(proc: subprocess.Popen, stream_announced: list[bool]) -> bytes:
    pre_roll: list[bytes] = []
    utterance = bytearray()
    talking = False
    silence_seconds = 0.0
    hot_frames = 0
    warmup_frames = int(2.0 / FRAME_SECONDS)

    while True:
        frame = read_exact(proc, FRAME_BYTES)
        if not frame:
            raise RuntimeError(f"short microphone frame: 0/{FRAME_BYTES}")
        if len(frame) < FRAME_BYTES:
            # Agora/ffmpeg can yield a partial but valid final packet. Preserve it
            # and pad with silence instead of rebuilding the whole RTC stream.
            frame += b"\x00" * (FRAME_BYTES - len(frame))

        if not stream_announced[0]:
            log(f"microphone PCM connected: {len(frame)}-byte frames")
            log("microphone warming up - please wait")
            stream_announced[0] = True

        if speaking_until() > time.time():
            pre_roll.clear()
            utterance.clear()
            talking = False
            silence_seconds = 0.0
            continue

        if warmup_frames > 0:
            warmup_frames -= 1
            if warmup_frames == 0:
                log("READY - SPEAK NOW")
            continue

        rms = pcm_rms(frame)
        if not talking:
            pre_roll.append(frame)
            pre_roll = pre_roll[-PRE_ROLL_FRAMES:]
            hot_frames = hot_frames + 1 if rms >= START_RMS_THRESHOLD else 0
            if hot_frames >= 2:
                talking = True
                for buffered in pre_roll:
                    utterance.extend(buffered)
                log("speech started")
            continue

        utterance.extend(frame)
        duration = len(utterance) / (RATE * CHANNELS * SAMPLE_BYTES)
        silence_seconds = silence_seconds + FRAME_SECONDS if rms < END_RMS_THRESHOLD else 0.0
        if silence_seconds >= END_SILENCE_SECONDS and duration >= 1.0:
            log(f"speech ended: {duration:.1f}s")
            return bytes(utterance)
        if duration >= MAX_UTTERANCE_SECONDS:
            log(f"maximum utterance reached: {duration:.1f}s")
            return bytes(utterance)


def deliver_transcript(text: str) -> None:
    clean = " ".join(text.split())
    webhook = os.environ.get("EBO_ASR_WEBHOOK_URL", "")
    command = os.environ.get("EBO_ASR_COMMAND", "")

    if webhook:
        token = os.environ.get("EBO_ASR_WEBHOOK_TOKEN", "")
        token_file = os.environ.get("EBO_ASR_WEBHOOK_TOKEN_FILE", "")
        if not token and token_file:
            with open(token_file, encoding="utf-8") as f:
                token = f.read().strip()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(
            webhook,
            data=json.dumps({"text": clean}, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read()
        log("delivered to webhook: " + clean)
    elif command:
        subprocess.run(shlex.split(command), input=clean + "\n", text=True, check=True)
        log("delivered to command: " + clean)
    else:
        log("transcript: " + clean)


def stop_process(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main() -> None:
    log(f"loading faster-whisper {MODEL_NAME} / CPU int8")
    model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    log("model ready")
    token = get_token()
    node = ensure_audio_channel(token)
    last_text = ""
    last_text_time = 0.0
    failures = 0

    while True:
        while speaking_until() > time.time():
            time.sleep(0.5)
        proc = start_ffmpeg()
        log("waiting for microphone PCM")
        stream_announced = [False]
        try:
            while True:
                pcm = read_utterance(proc, stream_announced)
                failures = 0
                audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
                started = time.monotonic()
                log("[asr-timing] Whisper transcribe start")
                segments, _ = model.transcribe(
                    audio,
                    language=LANGUAGE,
                    beam_size=BEAM_SIZE,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                    condition_on_previous_text=False,
                )
                text = "".join(segment.text for segment in segments).strip()
                log(f"[asr-timing] Whisper transcribe done: {time.monotonic()-started:.3f}s")
                if not text:
                    continue
                if text == last_text and time.time() - last_text_time < 15:
                    continue
                deliver_transcript(text)
                log(f"[asr-timing] total speech-to-delivery: {time.monotonic()-started:.3f}s")
                last_text, last_text_time = text, time.time()
                if ONCE:
                    return
        except Exception as exc:
            failures += 1
            log("stream restart: " + repr(exc))
        finally:
            stop_process(proc)

        while speaking_until() > time.time():
            time.sleep(0.5)
        if failures and failures % 5 == 0:
            try:
                robots = json.loads(api_request(token, "/api/robots"))
                robot = next((item for item in robots if item.get("node") == node), robots[0] if robots else {})
                camera_on = str(robot.get("camera", "")).lower() == "on"
                if not camera_on:
                    log("camera stream is off; reopening RTC stream")
                    post_cmd(token, node, "camera/set", "on")
                    time.sleep(8)
                else:
                    log("empty microphone stream; cycling listen off/on")
                    post_cmd(token, node, "listen/set", "off")
                    time.sleep(3)
                    post_cmd(token, node, "listen/set", "on")
                    time.sleep(8)
                log("microphone recovery cycle completed")
            except Exception as exc:
                log("microphone recovery failed: " + repr(exc))
        time.sleep(2)


if __name__ == "__main__":
    main()
