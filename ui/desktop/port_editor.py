from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QCheckBox,
    QVBoxLayout,
    QPushButton,
)

from config import load_settings, add_or_update_port, save_settings


class PortEditorDialog(QDialog):
    def __init__(self, settings_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Ports")
        self.settings_path = settings_path
        self.settings = load_settings(settings_path)
        self.ports = self.settings.get("ports", [])

        self.list_widget = QListWidget()
        for port in self.ports:
            item = QListWidgetItem(port["id"])
            self.list_widget.addItem(item)

        self.port_id = QLineEdit()
        self.device = QComboBox()
        self.device.setEditable(True)
        self.refresh_ports_btn = QPushButton("Refresh COM ports")
        self.refresh_ports_btn.clicked.connect(self.load_com_ports)
        self.baudrate = QSpinBox()
        self.baudrate.setRange(1200, 1000000)
        self.parity = QComboBox()
        self.parity.addItems(["N", "E", "O"])
        self.stopbits = QSpinBox()
        self.stopbits.setRange(1, 2)
        self.bytesize = QSpinBox()
        self.bytesize.setRange(5, 8)
        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(0.1, 60.0)
        self.timeout.setSingleStep(0.1)
        self.unit_id = QSpinBox()
        self.unit_id.setRange(1, 247)
        self.read_address = QSpinBox()
        self.read_address.setRange(0, 99999)
        self.read_count = QSpinBox()
        self.read_count.setRange(1, 125)
        self.value_index = QSpinBox()
        self.value_index.setRange(0, 124)
        self.enabled = QCheckBox("Enabled")
        self.poll_interval = QDoubleSpinBox()
        self.poll_interval.setRange(0.1, 60.0)
        self.poll_interval.setSingleStep(0.1)

        form = QFormLayout()
        form.addRow("Port ID", self.port_id)
        form.addRow("Device", self.device)
        form.addRow("", self.refresh_ports_btn)
        form.addRow("Baudrate", self.baudrate)
        form.addRow("Parity", self.parity)
        form.addRow("Stopbits", self.stopbits)
        form.addRow("Bytesize", self.bytesize)
        form.addRow("Timeout (s)", self.timeout)
        form.addRow("Poll interval (s)", self.poll_interval)
        form.addRow("Unit ID", self.unit_id)
        form.addRow("Read address", self.read_address)
        form.addRow("Read count", self.read_count)
        form.addRow("Value index", self.value_index)
        form.addRow(self.enabled)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_port)
        self.add_btn = QPushButton("Add new")
        self.add_btn.clicked.connect(self.add_new_port)
        btn_row = QHBoxLayout()
        btn_row.addWidget(buttons)
        btn_row.addWidget(self.delete_btn)
        btn_row.addWidget(self.add_btn)

        layout = QHBoxLayout()
        layout.addWidget(self.list_widget)
        form_wrap = QVBoxLayout()
        form_wrap.addLayout(form)
        form_wrap.addLayout(btn_row)
        layout.addLayout(form_wrap)

        self.setLayout(layout)
        self.list_widget.currentRowChanged.connect(self.load_selected)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        self.load_com_ports()

    def load_com_ports(self) -> None:
        """Populate device combo with available serial ports."""
        ports = []
        try:
            from serial.tools import list_ports  # type: ignore

            ports = [p.device for p in list_ports.comports()]
        except Exception:
            ports = []
        current = self.device.currentText()
        self.device.clear()
        if ports:
            self.device.addItems(ports)
        self.device.setEditText(current)

    def load_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.ports):
            return
        port = self.ports[row]
        self.port_id.setText(port.get("id", ""))
        self.device.setEditText(port.get("device", ""))
        self.baudrate.setValue(int(port.get("baudrate", 9600)))
        idx = self.parity.findText(str(port.get("parity", "N")))
        self.parity.setCurrentIndex(max(0, idx))
        self.stopbits.setValue(int(port.get("stopbits", 1)))
        self.bytesize.setValue(int(port.get("bytesize", 8)))
        self.timeout.setValue(float(port.get("timeout", 1.0)))
        self.poll_interval.setValue(float(port.get("poll_interval", 1.0)))
        self.unit_id.setValue(int(port.get("unit_id", 1)))
        self.read_address.setValue(int(port.get("read_address", 0)))
        self.read_count.setValue(int(port.get("read_count", 10)))
        self.value_index.setValue(int(port.get("value_index", 0)))
        self.enabled.setChecked(bool(port.get("enabled", True)))

    def save(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.ports):
            self.reject()
            return
        port = self.ports[row]
        updated: Dict[str, Any] = {
            "id": self.port_id.text().strip() or port["id"],
            "device": self.device.currentText().strip(),
            "baudrate": self.baudrate.value(),
            "parity": self.parity.currentText(),
            "stopbits": self.stopbits.value(),
            "bytesize": self.bytesize.value(),
            "timeout": self.timeout.value(),
            "poll_interval": self.poll_interval.value(),
            "unit_id": self.unit_id.value(),
            "read_address": self.read_address.value(),
            "read_count": self.read_count.value(),
            "value_index": self.value_index.value(),
            "enabled": self.enabled.isChecked(),
        }
        action, _ = add_or_update_port(self.settings, updated)
        save_settings(self.settings, self.settings_path)
        self.accept()

    def delete_port(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.ports):
            return
        port_id = self.ports[row].get("id")
        if not port_id:
            return
        self.ports = [p for p in self.ports if p.get("id") != port_id]
        self.settings["ports"] = self.ports
        save_settings(self.settings, self.settings_path)
        self.list_widget.takeItem(row)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self.port_id.clear()
            self.device.setEditText("")

    def add_new_port(self) -> None:
        base_id = f"port_{len(self.ports)+1}"
        # ensure unique
        existing_ids = {p.get("id") for p in self.ports}
        new_id = base_id
        counter = 1
        while new_id in existing_ids:
            counter += 1
            new_id = f"{base_id}_{counter}"
        new_port = {
            "id": new_id,
            "device": "",
            "baudrate": 9600,
            "parity": "N",
            "stopbits": 1,
            "bytesize": 8,
            "timeout": 1.0,
            "poll_interval": 1.0,
            "unit_id": 1,
            "read_address": 0,
            "read_count": 10,
            "value_index": 0,
            "enabled": True,
        }
        self.ports.append(new_port)
        item = QListWidgetItem(new_id)
        self.list_widget.addItem(item)
        self.list_widget.setCurrentItem(item)
