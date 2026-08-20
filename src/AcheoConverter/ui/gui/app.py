# ui/gui/app.py

"""
Minimal PyQt5 GUI for ArcheoConverter.
"""

from __future__ import annotations
import sys
import logging
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTextEdit
)
from PyQt5.QtCore import Qt

from ..core.model_store import ArchiModel
from ..import_export.archimate_parser import parse_archimate_xml
from ..converter.version_migrator import VersionMigrator
from ..comparison.differ import ModelDiffer

logger = logging.getLogger(__name__)


class ArcheoConverterGUI(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArcheoConverter")
        self.resize(1024, 768)
        
        # Current state
        self.model_a: "ArchiModel" = None
        self.model_b: "ArchiModel" = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        load_a_btn = QPushButton("Load Model A (XML)")
        load_b_btn = QPushButton("Load Model B (XML)")
        convert_btn = QPushButton("Convert/Compare Models")
        clear_btn = QPushButton("Clear All")
        
        for btn in [load_a_btn, load_b_btn, convert_btn, clear_btn]:
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
        
        # Output text area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)
        
        # Connect signals
        load_a_btn.clicked.connect(lambda: self._load_model_a())
        load_b_btn.clicked.connect(lambda: self._load_model_b())
        convert_btn.clicked.connect(self._convert_or_compare)
        clear_btn.clicked.connect(self._clear_models)
    
    def _load_model_a(self):
        """Load first model."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ArchiMate Model A",
            "",
            "ArchiMate XML (*.xml);;All Files (*)"
        )
        
        if not path:
            return
        
        try:
            result = parse_archimate_xml(Path(path))
            
            self.model_a = ArchiModel(
                id=result.model_id,
                name=result.model_name,
                version=result.version,
                elements=[],
                relationships=[]
            )
            for elem in result.elements:
                self.model_a.add_element(elem)
            
            self.output_area.append(f"✅ Model A loaded: {self.model_a.name} (v{self.model_a.version})")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load model A: {e}")
            logger.error(f"Failed to load model A: {e}", exc_info=True)
    
    def _load_model_b(self):
        """Load second model."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ArchiMate Model B",
            "",
            "ArchiMate XML (*.xml);;All Files (*)"
        )
        
        if not path:
            return
        
        try:
            result = parse_archimate_xml(Path(path))
            
            self.model_b = ArchiModel(
                id=result.model_id,
                name=result.model_name,
                version=result.version,
                elements=[],
                relationships=[]
            )
            for elem in result.elements:
                self.model_b.add_element(elem)
            
            self.output_area.append(f"✅ Model B loaded: {self.model_b.name} (v{self.model_b.version})")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load model B: {e}")
            logger.error(f"Failed to load model B: {e}", exc_info=True)
    
    def _convert_or_compare(self):
        """Handle convert/compare action."""
        if not self.model_a and not self.model_b:
            QMessageBox.information(self, "Info", "Please load at least one model.")
            return
        
        try:
            output_lines = []
            
            # Model A migration
            if self.model_a:
                migrator = VersionMigrator()
                
                to_version = "4.0" if self.model_a.version == "3.2" else "3.2"
                
                result = migrator.migrate(self.model_a, self.model_a.version, to_version)
                
                output_lines.append(f"Model A (v{self.model_a.version}) → v{to_version}: {len(result.warnings)} warnings")
            
            # Model B migration
            if self.model_b:
                migrator = VersionMigrator()
                
                to_version = "4.0" if self.model_b.version == "3.2" else "3.2"
                
                result = migrator.migrate(self.model_b, self.model_b.version, to_version)
                
                output_lines.append(f"Model B (v{self.model_b.version}) → v{to_version}: {len(result.warnings)} warnings")
            
            # Compare
            if self.model_a and self.model_b:
                differ = ModelDiffer()
                result = differ.compare(self.model_a, self.model_b)
                
                output_lines.append(f"Comparison: {result.match_score} match score")
                output_lines.append(
                    f"- Elements in A: {len(self.model_a.elements)}, B: {len(self.model_b.elements)}"
                )
            
            # Output
            if output_lines:
                self.output_area.append("🔍 Analysis Results:")
                for line in output_lines:
                    self.output_area.append(f"• {line}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {e}")
            logger.error(f"Analysis failed: {e}", exc_info=True)
    
    def _clear_models(self):
        """Clear loaded models."""
        self.model_a = None
        self.model_b = None
        self.output_area.clear()
        self.output_area.append("Models cleared")


def run_gui():
    """Run the PyQt5 application."""
    app = QApplication(sys.argv)
    
    window = ArcheoConverterGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_gui()
