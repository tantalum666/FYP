#!/usr/bin/env python3
"""Opt-in local GPT-SoVITS probe; no cloud provider or production configuration writes."""

import argparse
from array import array
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import wave


def local_endpoint(value):
    uri = urllib.parse.urlsplit(value)
    if (
        uri.scheme != "http"
        or uri.hostname not in {"127.0.0.1", "localhost", "::1"}
        or uri.username
        or uri.password
        or uri.query
        or uri.fragment
        or uri.path not in {"", "/"}
    ):
        raise argparse.ArgumentTypeError("Use the isolated loopback TTS server")
    return value.rstrip("/") + "/tts"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def inspect_wave(data):
    with wave.open(io.BytesIO(data)) as reader:
        if reader.getnchannels() != 1 or reader.getsampwidth() != 2:
            raise ValueError("Expected mono PCM16 WAV")
        rate, frames = reader.getframerate(), reader.getnframes()
        pcm = reader.readframes(frames)
    if (
        rate not in {24000, 32000, 40000, 44100, 48000}
        or not 0.25 <= frames / rate <= 60
        or len(pcm) != frames * 2
    ):
        raise ValueError("Unexpected or empty audio")
    samples = array("h", pcm)
    if not samples or max(abs(v) for v in samples) < 100:
        raise ValueError("Output has no substantial audio signal")
    return {"sample_rate": rate, "duration_seconds": frames / rate, "frames": frames}


def request_audio(endpoint, payload, output, *, timeout, raw_rate=None):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.monotonic()
    first_signal_ms = None
    data = bytearray()
    with opener.open(request, timeout=timeout) as response:
        if not response.headers.get_content_type().startswith("audio/"):
            raise ValueError("TTS did not return audio")
        while chunk := response.read1(4096):
            data.extend(chunk)
            if len(data) > 4_000_000 or time.monotonic() - started > timeout:
                raise TimeoutError("Bounded TTS probe exceeded its audio/time limit")
            if raw_rate and first_signal_ms is None:
                complete = len(data) - len(data) % 2
                samples = array("h", data[:complete])
                if samples and max(abs(v) for v in samples) >= 100:
                    first_signal_ms = round((time.monotonic() - started) * 1000, 2)
    elapsed = time.monotonic() - started
    if raw_rate:
        if len(data) % 2:
            raise ValueError("Truncated PCM16 response")
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(raw_rate)
            writer.writeframes(data)
        data = buffer.getvalue()
    info = inspect_wave(data)
    output.write_bytes(data)
    return {
        **info,
        "request_seconds": round(elapsed, 3),
        "generation_seconds_per_audio_second": round(elapsed / info["duration_seconds"], 3),
        "first_received_nonsilent_pcm_ms": first_signal_ms,
        "playback_latency_measured": False,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", type=local_endpoint, default="http://127.0.0.1:9880")
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--reference-text", type=Path, required=True)
    parser.add_argument("--reference-language", choices=["en", "zh", "yue"], required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--cases", default="en-greeting,zh-greeting,yue-greeting")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--streaming", action="store_true")
    parser.add_argument("--sample-rate", type=int, default=32000)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 240:
        parser.error("Timeout must be between1and240seconds")
    with wave.open(str(args.reference.resolve())) as reference:
        duration = reference.getnframes() / reference.getframerate()
        if not 3 <= duration <= 10:
            parser.error("This GPT-SoVITS reference segment must be3–10seconds")
    transcript = args.reference_text.read_text().strip()
    if not transcript or len(transcript) > 1000:
        parser.error("Provide the reference segment's accurate transcript")
    corpus = {row["id"]: row for row in json.loads(args.corpus.read_text())["samples"]}
    selected = args.cases.split(",")
    if (
        len(selected) > 14
        or len(set(selected)) != len(selected)
        or any(i not in corpus for i in selected)
    ):
        parser.error("Choose up to14distinct case IDs from the corpus")
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"cloud_calls": 0, "owner_voice_accepted": False, "cases": [], "completed": False}
    report_path = args.output / "report.json"
    if report_path.exists():
        parser.error("Choose a new output directory; keep earlier evidence")
    try:
        for name in selected:
            case = corpus[name]
            if case["language"] not in {"en", "zh", "yue"} or len(case["text"]) > 300:
                raise ValueError("This probe accepts bounded single-language cases")
            payload = {
                "text": case["text"],
                "text_lang": case["language"],
                "ref_audio_path": str(args.reference.resolve()),
                "prompt_text": transcript,
                "prompt_lang": args.reference_language,
                "text_split_method": "cut5",
                "batch_size": 1,
                "seed": 20261109,
                "speed_factor": 1.0,
                "media_type": "raw" if args.streaming else "wav",
                "streaming_mode": 2 if args.streaming else False,
                "parallel_infer": True,
            }
            result = request_audio(
                args.base_url,
                payload,
                args.output / f"{name}.wav",
                timeout=args.timeout,
                raw_rate=args.sample_rate if args.streaming else None,
            )
            report["cases"].append(
                {"id": name, "language": case["language"], "streaming": args.streaming, **result}
            )
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report["cases"][-1]), flush=True)
        report["completed"] = True
    except Exception as error:
        report["error"] = type(error).__name__
        if isinstance(error, urllib.error.HTTPError):
            report["http_status"] = error.code
            report["provider_error"] = error.read(2048).decode("utf-8", errors="replace")
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
