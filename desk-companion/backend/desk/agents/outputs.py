"""Explicitly launched actuator worker; simulated by default.

Live mode requires a locally commissioned configuration and a normally-closed
physical stop circuit. Neither a web client nor a language model selects angles.
"""

import argparse
import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from desk.outputs import PRESETS


def validate_config(config):
    if config.get("commissioned") is not True:
        raise ValueError("Hardware configuration is not commissioned")
    channels = config.get("channels", [])
    if not 2 <= len(channels) <= 3:
        raise ValueError("Use two or three calibrated servo channels")
    used = set()
    for channel in channels:
        index = channel["channel"]
        if not isinstance(index, int) or not 0 <= index < 16 or index in used:
            raise ValueError("Invalid servo channel")
        used.add(index)
        if (
            not 0 <= channel["min_angle"] < channel["max_angle"] <= 180
            or channel["max_angle"] - channel["min_angle"] > 90
        ):
            raise ValueError("Set a bounded, calibrated angle range")
        if not 500 <= channel["min_pulse"] < channel["max_pulse"] <= 2500:
            raise ValueError("Invalid calibrated pulse range")
    if not isinstance(config.get("stop_gpio"), int) or not 0 <= config["stop_gpio"] <= 27:
        raise ValueError("A normally-closed physical stop GPIO is required")
    if config.get("light_gpio") is not None and (
        not isinstance(config["light_gpio"], int)
        or not 0 <= config["light_gpio"] <= 27
        or config["light_gpio"] == config["stop_gpio"]
    ):
        raise ValueError("Invalid indicator GPIO")
    poses = config.get("poses", {})
    if set(poses) != PRESETS["arm"]:
        raise ValueError("Define only the three named arm presets")
    for angles in poses.values():
        if len(angles) != len(channels) or any(
            not channel["min_angle"] <= angle <= channel["max_angle"]
            for angle, channel in zip(angles, channels)
        ):
            raise ValueError("A preset exceeds a calibrated limit")
    return config


class Simulator:
    capabilities = ["arm", "light"]

    def stopped(self):
        return False

    def stop(self):
        pass

    def execute(self, command, allowed):
        if not allowed():
            return False
        time.sleep(0.02)
        return allowed()


class ServoDriver:
    def __init__(self, config):
        validate_config(config)
        from adafruit_servokit import ServoKit
        from gpiozero import Button, LED

        self.config = config
        self.stop_switch = Button(config["stop_gpio"], pull_up=True, bounce_time=0.03)
        self.light = LED(config["light_gpio"]) if config.get("light_gpio") is not None else None
        self.kit = ServoKit(channels=16)
        self.angles = list(config["poses"]["rest"])
        self.capabilities = ["arm"] + (["light"] if self.light else [])
        for channel in config["channels"]:
            servo = self.kit.servo[channel["channel"]]
            servo.actuation_range = 180
            servo.set_pulse_width_range(channel["min_pulse"], channel["max_pulse"])
            servo.angle = None
        self.known_position = False

    def stopped(self):
        # Closed to ground means healthy. Pressing stop or breaking the wire opens it.
        return not self.stop_switch.is_pressed

    def stop(self):
        for channel in self.config["channels"]:
            self.kit.servo[channel["channel"]].angle = None
        if self.light:
            self.light.off()
        self.known_position = False

    def execute(self, command, allowed):
        if not allowed() or self.stopped():
            self.stop()
            return False
        if command["kind"] == "light" and self.light:
            self.light.off() if command["preset"] == "off" else self.light.on()
            return True
        if command["kind"] != "arm":
            return False
        # Without encoders, re-energising a servo cannot guarantee a smooth move.
        # Start only with the user-set rest pose documented in commissioning.
        if not self.known_position and command["preset"] != "rest":
            return False
        target = self.config["poses"][command["preset"]]
        start = self.angles[:]
        steps = max(1, int(max(abs(a - b) for a, b in zip(start, target)) * 2))
        if steps * 0.02 > 3:
            return False
        for step in range(1, steps + 1):
            if not allowed() or self.stopped():
                self.stop()
                return False
            for index, (channel, a, b) in enumerate(zip(self.config["channels"], start, target)):
                self.angles[index] = a + (b - a) * step / steps
                self.kit.servo[channel["channel"]].angle = self.angles[index]
            time.sleep(0.02)
        self.known_position = True
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8831")
    parser.add_argument("--runtime", type=Path, default=Path(".runtime"))
    parser.add_argument("--driver", choices=["simulator", "pca9685"], default="simulator")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    from urllib.parse import urlsplit

    uri = urlsplit(args.api)
    if uri.scheme != "https" and not (
        uri.scheme == "http" and uri.hostname in {"127.0.0.1", "localhost"}
    ):
        parser.error("Use loopback HTTP or a configured HTTPS endpoint")
    if args.driver == "pca9685" and not args.config:
        parser.error("Live output needs --config with calibrated limits")
    driver = (
        ServoDriver(json.loads(args.config.read_text()))
        if args.driver == "pca9685"
        else Simulator()
    )
    source = "live" if args.driver == "pca9685" else "replay"
    token = json.loads((args.runtime / "agent.json").read_text())["token"]
    headers = {"Authorization": "Bearer " + token, "X-Desk-Request": "1"}
    status = {"stopped": True, "checked": 0.0}
    ending = threading.Event()

    def guard():
        with httpx.Client(
            trust_env=False, base_url=args.api, headers=headers, timeout=0.7
        ) as client:
            while not ending.is_set():
                try:
                    r = client.post(
                        "/api/agent/outputs/heartbeat",
                        json={
                            "source": source,
                            "capabilities": driver.capabilities,
                            "hardware_verified": True,
                            "stopped": driver.stopped(),
                        },
                    )
                    r.raise_for_status()
                    status.update(stopped=r.json()["stopped"], checked=time.monotonic())
                except (httpx.HTTPError, ValueError, KeyError):
                    status["stopped"] = True
                ending.wait(0.2)

    thread = threading.Thread(target=guard, daemon=True)
    thread.start()
    try:
        with httpx.Client(trust_env=False, base_url=args.api, headers=headers, timeout=1) as client:
            while True:
                if (
                    status["stopped"]
                    or time.monotonic() - status["checked"] > 1
                    or driver.stopped()
                ):
                    driver.stop()
                    time.sleep(0.1)
                    continue
                try:
                    response = client.post("/api/agent/outputs/claim", json={})
                    response.raise_for_status()
                    for command in response.json()["commands"]:
                        if command["source"] != source:
                            continue
                        deadline = datetime.fromisoformat(
                            command["expires_at"].replace("Z", "+00:00")
                        ).timestamp()

                        def allowed():
                            return (
                                not status["stopped"]
                                and time.monotonic() - status["checked"] <= 1
                                and datetime.now(UTC).timestamp() < deadline
                                and not driver.stopped()
                            )

                        succeeded = driver.execute(command, allowed)
                        receipt = {
                            "status": "executed" if succeeded else "failed",
                            "detail": "simulation"
                            if source == "replay"
                            else "driver_completed"
                            if succeeded
                            else "stopped",
                        }
                        client.post(
                            "/api/agent/outputs/" + command["id"] + "/receipt", json=receipt
                        ).raise_for_status()
                    time.sleep(0.1)
                except (httpx.HTTPError, ValueError, KeyError):
                    driver.stop()
                    time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        ending.set()
        driver.stop()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
