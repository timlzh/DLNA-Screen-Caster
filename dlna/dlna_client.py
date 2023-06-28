# -*- coding: utf-8 -*-

from . import dlna_util as util
from .device import Device


def get_devices(timeout: int = 5) -> list:
    devices = util.get_device(timeout)

    if not devices:
        print("No online devices.")
        return []

    for i, d in enumerate(devices, start=1):
        print(
            f"=> Device {i}:\n{d}\n")

    return devices


def play(device_location: str, src: str, query_device: str = None, timeout: int = 5):
    src_info = {"file_video": src}

    try:
        if device_location:
            device = Device(util.parse_xml(device_location))
        elif query_device:
            device = list(filter(lambda x: query_device.lower(
            ) in x["friendly_name"].lower(), util.get_device(timeout)))[0]
        else:
            device = util.get_device(timeout)[0]
    except Exception:
        device = None

    if not device:
        print("No online devices.")
        return None

    print(f"Current play device: {device['friendly_name']}")

    if src.startswith("http"):
        util.play(src.replace("&", "&amp;").replace("\\", ""), device, True)
    else:
        serve_ip = util.get_serve_ip(util.get_serve_ip(device["host"]))
        files_urls = util.start_server(src_info, serve_ip)
        util.play(files_urls, device)
    return device


def stop(device: Device):
    util.stop(device)
