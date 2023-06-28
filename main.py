import os
import sys
from http.server import *

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMessageBox,
                             QTableWidgetItem)

import dlna
import utils
from Ui_main import Ui_MainWindow

screenFileName = "linux_screen.flv"
resolutions = ["1920x1080", "1920x1200", "2560x1440", "2560x1600", "1280x720"]


class Window(QMainWindow, Ui_MainWindow):
    devices: list = []
    current_device: dlna.Device = None

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        icon_path = os.path.join(os.path.dirname(__file__), "static", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setupUi(self)

        self.scan_device_button.clicked.connect(self.scan_device)
        self.device_table.itemDoubleClicked.connect(
            self.device_table_double_clicked)
        self.host_ip_edit.setText(utils.get_host_ip())
        self.resolution_combo.currentIndexChanged.connect(
            self.resolution_combo_changed)
        self.stop_button.clicked.connect(self.stop_button_clicked)

        self.resolution_combo_changed()
        self.scan_device()

    def scan_device(self):
        self.scan_device_button.setEnabled(False)
        self.scan_device_button.setText("Scanning...")
        self.scan_device_thread = ScanDeviceThread(self)
        self.scan_device_thread.signal.connect(self.scan_device_callback)
        self.scan_device_thread.start()

    def scan_device_callback(self, devices):
        self.device_table.setRowCount(len(devices))
        self.devices = devices
        for i, d in enumerate(devices, start=0):
            self.device_table.setItem(
                i, 0, QTableWidgetItem(d["friendly_name"]))
            self.device_table.setItem(i, 1, QTableWidgetItem(d["host"]))
            self.device_table.setItem(
                i, 2, QTableWidgetItem(d["manufacturer"]))
        if len(devices) > 0:
            QMessageBox.information(
                self, "Scan Finished", f"Sacn Finished, {len(devices)} devices found.")
        else:
            QMessageBox.information(self, "Scan Finished", "No device found.")
        self.scan_device_button.setEnabled(True)
        self.scan_device_button.setText("Scan Device")

    def device_table_double_clicked(self):
        src = f"http://{self.host_ip_edit.text()}:8089/cgi-bin/{screenFileName}"
        self.current_device = self.devices[self.device_table.currentRow()]
        dlna.play(self.current_device["location"], src)

    def resolution_combo_changed(self):
        with open(f"cgi-bin/{screenFileName}.template", "r") as f:
            template = f.read()
        with open(f"cgi-bin/{screenFileName}", "w") as f:
            f.write(template.replace(
                "{{resolution}}", resolutions[self.resolution_combo.currentIndex()]))
        if sys.platform == 'linux':
            os.system(f"chmod +x cgi-bin/{screenFileName}")

    def stop_button_clicked(self):
        if self.current_device is None:
            return
        dlna.stop(self.current_device)

    def closeEvent(self, event: QCloseEvent):
        if self.current_device is not None:
            dlna.stop(self.current_device)
        CGIFileServer.stop()
        event.accept()


class ScanDeviceThread(QThread):
    signal = pyqtSignal(list)

    def __init__(self, parent=None):
        super(ScanDeviceThread, self).__init__(parent)
        self.parent = parent
        self.devices = []

    def run(self):
        self.devices = dlna.get_devices()
        self.signal.emit(self.devices)


class CGIFileServerThread(QThread):
    def __init__(self, parent=None):
        super(CGIFileServerThread, self).__init__(parent)
        self.parent = parent
        self.httpd = None
        self.keepRunning = True

    def run(self):
        self.httpd = HTTPServer(('', 8089), CGIHTTPRequestHandler)
        while self.keepRunning:
            self.httpd.handle_request()

    def stop(self):
        self.keepRunning = False


if __name__ == '__main__':
    if sys.platform == 'darwin':
        screenFileName = "mac_screen.flv"
    elif sys.platform == 'win32':
        screenFileName = "win_screen.flv"
    else:
        screenFileName = "linux_screen.flv"

    CGIFileServer = CGIFileServerThread()
    CGIFileServer.start()

    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec_())
