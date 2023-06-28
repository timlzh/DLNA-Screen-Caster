import os
import pkgutil
import re
import socket
import sys
import threading
import urllib.request as urllibreq
from urllib.parse import urljoin, urlparse

import requests
from lxml import etree
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.static import File

from .device import Device

SSDP_BROADCAST_ADDR = "239.255.255.250"
SSDP_BROADCAST_PORT = 1900
SSDP_BROADCAST_PARAMS = [
    "M-SEARCH * HTTP/1.1",
    f"HOST: {SSDP_BROADCAST_ADDR}:{SSDP_BROADCAST_PORT}",
    "MAN: \"ssdp:discover\"",
    "MX: 10",
    "ST: ssdp:all",
    "", ""
]
SSDP_BROADCAST_MSG = "\r\n".join(SSDP_BROADCAST_PARAMS)
UPNP_DEFAULT_SERVICE_TYPE = "urn:schemas-upnp-org:service:AVTransport:1"


def get_serve_ip(target_ip, target_port=80):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((target_ip, target_port))
    serve_ip = s.getsockname()[0]
    s.close()
    return serve_ip


def set_files(files, serve_ip, serve_port):

    files_index = {file_key: (os.path.basename(file_path),
                              os.path.abspath(file_path),
                              os.path.dirname(os.path.abspath(file_path)))
                   for file_key, file_path in files.items()}

    files_serve = {file_name: file_path
                   for file_name, file_path, file_dir in files_index.values()}

    files_urls = {
        file_key: "http://{0}:{1}/{2}/{3}".format(
            serve_ip, serve_port, file_key, file_name)
        for file_key, (file_name, file_path, file_dir)
        in files_index.items()}

    return files_index, files_serve, files_urls


def start_server(files, serve_ip, serve_port=9000):

    # import sys
    # log.startLogging(sys.stdout)

    files_index, files_serve, files_urls = set_files(
        files, serve_ip, serve_port)

    root = Resource()
    for file_key, (file_name, file_path, file_dir) in files_index.items():
        root.putChild(file_key.encode("utf-8"), Resource())
        root.children[file_key.encode("utf-8")].putChild(
            file_name.encode("utf-8"), File(file_path))

    reactor.listenTCP(serve_port, Site(root))
    threading.Thread(
        target=reactor.run, kwargs={"installSignalHandlers": False}).start()

    return files_urls


def parse_xml(url):
    node = etree.XML(re.sub(" xmlns=\"[^\"]+\"", "", requests.get(
        url).content.decode(), count=1).encode(), parser=etree.XMLParser(recover=True))
    friendly_name = node.xpath("//friendlyName/text()")
    manufacturer_url = node.xpath("//manufacturerURL/text()")
    control_url = node.xpath(
        "//serviceType[contains(text(), 'AVTransport')]/../controlURL/text()")
    manufacturer = node.xpath("//manufacturer/text()")
    data = {
        "location": url,
        "host": urlparse(url).hostname,
        "friendly_name": friendly_name and friendly_name[0],
        "action_url": urljoin(url, control_url and control_url[0]),
        "manufacturer": manufacturer and manufacturer[0],
        "manufacturer_url": manufacturer_url and manufacturer_url[0],
        "st": UPNP_DEFAULT_SERVICE_TYPE,
        "help": "leesoar.com/real | Wechat MP: GMapi | core@111.com, chat with me.",
    }
    return data


def get_device(timeout=10):
    print("Scanning...")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
    s.bind(("", SSDP_BROADCAST_PORT + 10))

    s.sendto(SSDP_BROADCAST_MSG.encode(),
             (SSDP_BROADCAST_ADDR, SSDP_BROADCAST_PORT))
    s.settimeout(timeout)

    scanned_devices = []
    devices = {}
    while 1:
        try:
            data, addr = s.recvfrom(1024)
        except socket.timeout:
            break

        def serialize(x):
            try:
                k, v = x.split(":", maxsplit=1)
            except ValueError:
                pass
            else:
                return k.lower(), v.lstrip()

        device = dict(map(serialize, filter(
            lambda x: x.count(":") >= 1, data.decode().split("\r\n"))))
        if device in scanned_devices:
            continue
        if "AVTransport" in device["st"]:
            devices.update({device["location"]: Device(
                parse_xml(device["location"]))})
        scanned_devices.append(device)
    return list(devices.values())


def send_dlna_action(device, data, action):

    action_data = pkgutil.get_data(
        "dlna", "templates/action-{0}.xml".format(action)).decode("UTF-8")
    action_data = action_data.format(**data).encode("UTF-8")

    headers = {
        "Content-Type": "text/xml; charset=\"utf-8\"",
        "Content-Length": "{0}".format(len(action_data)),
        "Connection": "close",
        "SOAPACTION": "\"{0}#{1}\"".format(device["st"], action)
    }

    request = urllibreq.Request(device["action_url"], action_data, headers)
    urllibreq.urlopen(request)


def play(files_urls, device, is_net=False):
    if is_net:
        video_data = {
            "uri_video": files_urls,
            "type_video": "leesoar.com",
            "metadata": "",
        }
    else:
        video_data = {
            "uri_video": files_urls["file_video"],
            "type_video": os.path.splitext(files_urls["file_video"])[1][1:],
            "metadata": "",
        }

    send_dlna_action(device, video_data, "SetAVTransportURI")
    send_dlna_action(device, video_data, "Play")


def stop(device):
    send_dlna_action(device, {}, "Stop")
