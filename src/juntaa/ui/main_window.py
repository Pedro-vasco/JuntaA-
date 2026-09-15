from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QComboBox,
    QProgressBar,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from pypdf import PdfReader

from juntaa.config import COMPRESSION_PRESETS, DOCX_EXTENSIONS, IMAGE_EXTENSIONS, OUTPUT_FORMATS, PDF_EXTENSIONS
from juntaa.converters.docx_adapter import describe_docx
from juntaa.models import MergeItem
from juntaa.services.pdf_exporter import ExportError, export_items_to_pdf

LOGGER = logging.getLogger(__name__)


class ExportWorker(QObject):
    progress = Signal(int, int, str)
    success = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, items: list[MergeItem], destination: Path, compression_label: str) -> None:
        super().__init__()
        self.items = list(items)
        self.destination = destination
        self.compression_label = compression_label

    def run(self) -> None:
        try:
            warnings = export_items_to_pdf(
                self.items,
                self.destination,
                self.compression_label,
                progress_callback=lambda current, total, message: self.progress.emit(current, total, message),
            )
        except ExportError as exc:
            self.error.emit(str(exc))
        else:
            self.success.emit(warnings)
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("JuntaA - Unificador de arquivos")
        self.resize(900, 600)
        self.items: list[MergeItem] = []
        self.export_thread: QThread | None = None
        self.export_worker: ExportWorker | None = None
        self.current_destination: Path | None = None
        self.last_export_succeeded = False

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SingleSelection)

        self.add_button = QPushButton("Adicionar arquivos")
        self.up_button = QPushButton("Subir")
        self.down_button = QPushButton("Descer")
        self.remove_button = QPushButton("Remover")
        self.export_button = QPushButton("Exportar")
        self.browse_button = QPushButton("Salvar em...")

        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(OUTPUT_FORMATS)

        self.compression_combo = QComboBox()
        self.compression_combo.addItems(COMPRESSION_PRESETS.keys())
        self.compression_combo.setCurrentText("Média")

        self.destination_input = QLineEdit()
        self.destination_input.setPlaceholderText("Selecione o PDF de saída")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.addPermanentWidget(self.progress_bar, stretch=1)
        self.status_bar.showMessage("Pronto")

        self._setup_layout()
        self._connect_signals()

    def _setup_layout(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.add_button)
        controls_layout.addWidget(self.up_button)
        controls_layout.addWidget(self.down_button)
        controls_layout.addWidget(self.remove_button)
        controls_layout.addStretch(1)

        form_layout = QFormLayout()
        form_layout.addRow("Formato de saída", self.output_format_combo)
        form_layout.addRow("Compressão", self.compression_combo)

        destination_container = QWidget()
        destination_layout = QHBoxLayout(destination_container)
        destination_layout.setContentsMargins(0, 0, 0, 0)
        destination_layout.addWidget(self.destination_input)
        destination_layout.addWidget(self.browse_button)
        form_layout.addRow("Salvar como", destination_container)

        help_label = QLabel(
            "MVP: itens são reordenados por arquivo. PDFs e DOCX preservam a ordem interna de páginas."
        )
        help_label.setWordWrap(True)

        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.file_list, stretch=1)
        main_layout.addWidget(help_label)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.export_button, alignment=Qt.AlignRight)

    def _connect_signals(self) -> None:
        self.add_button.clicked.connect(self.add_files)
        self.up_button.clicked.connect(self.move_item_up)
        self.down_button.clicked.connect(self.move_item_down)
        self.remove_button.clicked.connect(self.remove_selected_item)
        self.browse_button.clicked.connect(self.pick_destination)
        self.export_button.clicked.connect(self.export_pdf)

    def add_files(self) -> None:
        filters = "Arquivos suportados (*.pdf *.docx *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)"
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Adicionar arquivos", "", filters)
        if not file_paths:
            return

        added = 0
        ignored: list[str] = []
        for file_name in file_paths:
            path = Path(file_name)
            try:
                item = self._build_item(path)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Falha ao adicionar arquivo: %s", path)
                ignored.append(f"{path.name}: {exc}")
                continue

            self.items.append(item)
            self.file_list.addItem(QListWidgetItem(item.display_name))
            added += 1

        self.status_bar.showMessage(f"{added} arquivo(s) adicionado(s).")
        if ignored:
            QMessageBox.warning(
                self,
                "Alguns arquivos foram ignorados",
                "\n".join(ignored),
            )

    def _build_item(self, path: Path) -> MergeItem:
        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            return MergeItem(path=path, item_type="image", description="Imagem • 1 página")
        if suffix in PDF_EXTENSIONS:
            page_count = len(PdfReader(str(path)).pages)
            return MergeItem(path=path, item_type="pdf", description=f"PDF • {page_count} página(s)")
        if suffix in DOCX_EXTENSIONS:
            return MergeItem(path=path, item_type="docx", description=describe_docx(path))
        raise ValueError("Extensão não suportada")

    def move_item_up(self) -> None:
        index = self.file_list.currentRow()
        if index <= 0:
            return
        self.items[index - 1], self.items[index] = self.items[index], self.items[index - 1]
        item = self.file_list.takeItem(index)
        self.file_list.insertItem(index - 1, item)
        self.file_list.setCurrentRow(index - 1)

    def move_item_down(self) -> None:
        index = self.file_list.currentRow()
        if index < 0 or index >= self.file_list.count() - 1:
            return
        self.items[index + 1], self.items[index] = self.items[index], self.items[index + 1]
        item = self.file_list.takeItem(index)
        self.file_list.insertItem(index + 1, item)
        self.file_list.setCurrentRow(index + 1)

    def remove_selected_item(self) -> None:
        index = self.file_list.currentRow()
        if index < 0:
            return
        self.items.pop(index)
        self.file_list.takeItem(index)
        self.status_bar.showMessage("Item removido.")

    def pick_destination(self) -> None:
        destination, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", "saida.pdf", "PDF (*.pdf)")
        if destination:
            destination_path = Path(destination)
            if destination_path.suffix.lower() != ".pdf":
                destination_path = destination_path.with_suffix(".pdf")
            self.destination_input.setText(str(destination_path))

    def export_pdf(self) -> None:
        if self.output_format_combo.currentText() != "PDF":
            QMessageBox.warning(self, "Formato inválido", "O MVP exporta apenas em PDF.")
            return

        if not self.items:
            QMessageBox.warning(self, "Nenhum arquivo", "Adicione ao menos um arquivo antes de exportar.")
            return

        destination_text = self.destination_input.text().strip()
        if not destination_text:
            QMessageBox.warning(self, "Destino obrigatório", "Selecione o arquivo PDF de saída.")
            return

        destination = self._normalize_destination(Path(destination_text))
        self.destination_input.setText(str(destination))
        self.export_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Iniciando exportação...")
        self.current_destination = destination
        self.last_export_succeeded = False

        self.export_thread = QThread(self)
        self.export_worker = ExportWorker(self.items, destination, self.compression_combo.currentText())
        self.export_worker.moveToThread(self.export_thread)

        self.export_thread.started.connect(self.export_worker.run)
        self.export_worker.progress.connect(self._update_progress)
        self.export_worker.success.connect(self._handle_export_success)
        self.export_worker.error.connect(self._handle_export_error)
        self.export_worker.finished.connect(self._finish_export)
        self.export_worker.finished.connect(self.export_thread.quit)
        self.export_worker.finished.connect(self.export_worker.deleteLater)
        self.export_thread.finished.connect(self.export_thread.deleteLater)
        self.export_thread.start()

    def _update_progress(self, current: int, total: int, message: str) -> None:
        percentage = int((current / total) * 100) if total else 0
        self.progress_bar.setValue(percentage)
        self.status_bar.showMessage(message)

    @staticmethod
    def _normalize_destination(destination: Path) -> Path:
        if destination.suffix.lower() != ".pdf":
            return destination.with_suffix(".pdf")
        return destination

    def _handle_export_success(self, warnings: list[str]) -> None:
        destination = self.current_destination
        self.last_export_succeeded = True
        message = f"PDF exportado com sucesso em:\n{destination}" if destination else "PDF exportado com sucesso."
        if warnings:
            message += "\n\nAlguns arquivos foram ignorados:\n" + "\n".join(warnings)
        QMessageBox.information(self, "Exportação concluída", message)
        self.status_bar.showMessage("Exportação concluída")

    def _handle_export_error(self, message: str) -> None:
        self.last_export_succeeded = False
        QMessageBox.critical(self, "Falha na exportação", message)
        self.status_bar.showMessage("Falha na exportação")

    def _finish_export(self) -> None:
        self.export_button.setEnabled(True)
        if self.last_export_succeeded:
            self.progress_bar.setValue(100)
        else:
            self.progress_bar.setValue(0)
        self.export_thread = None
        self.export_worker = None
