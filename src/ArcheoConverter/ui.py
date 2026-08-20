"""Minimal tkinter UI for ArcheoConverter."""

import tkinter as tk

from tkinter import filedialog, messagebox, ttk

from .parser import parse_archimate_stream
from .converter import migrate_model
from .comparator import compare_models, integrate_models
from .navigator import search_elements, get_folder_tree
from .reporter import generate_model_summary
from .exporter import export_to_xml
from .logger_setup import get_logger

logger = get_logger(__name__)

class ArcheoConverterUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ArcheoConverter - Enterprise Architecture Manager")
        self.root.geometry("900x600")
        self.model = None
        self.model_b = None
        self._build_ui()

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tabs = [
            ("Import", self._import_tab),
            ("Navigate", self._navigate_tab),
            ("Compare", self._compare_tab),
            ("Convert", self._convert_tab),
            ("Export", self._export_tab),
            ("Admin", self._admin_tab)
        ]
        for title, builder in tabs:
            frame = ttk.Frame(notebook)
            builder(frame)
            notebook.add(frame, text=title)

    def _import_tab(self, parent: ttk.Frame):
        ttk.Button(parent, text="Load Model A", command=self._load_model_a).pack(pady=5)
        ttk.Button(parent, text="Load Model B", command=self._load_model_b).pack(pady=5)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(parent, textvariable=self.status_var).pack(pady=5)

    def _navigate_tab(self, parent: ttk.Frame):
        ttk.Label(parent, text="Search Query:").pack(pady=5)
        self.search_entry = ttk.Entry(parent)
        self.search_entry.pack(pady=5)
        ttk.Button(parent, text="Search", command=self._run_search).pack(pady=5)
        self.result_var = tk.StringVar(value="Results: ")
        ttk.Label(parent, textvariable=self.result_var).pack(pady=5)

    def _compare_tab(self, parent: ttk.Frame):
        ttk.Button(parent, text="Compare Models", command=self._run_compare).pack(pady=5)
        ttk.Button(parent, text="Integrate (Merge)", command=self._run_integrate).pack(pady=5)
        self.compare_var = tk.StringVar(value="Compare Results: ")
        ttk.Label(parent, textvariable=self.compare_var).pack(pady=5)

    def _convert_tab(self, parent: ttk.Frame):
        ttk.Label(parent, text="Target Version:").pack(pady=5)
        self.version_var = tk.StringVar(value="4.0")
        ttk.Combobox(parent, textvariable=self.version_var, values=["3.2", "4.0"]).pack(pady=5)
        ttk.Button(parent, text="Migrate Model A", command=self._run_convert).pack(pady=5)
        self.convert_var = tk.StringVar(value="Conversion Status: ")
        ttk.Label(parent, textvariable=self.convert_var).pack(pady=5)

    def _export_tab(self, parent: ttk.Frame):
        ttk.Button(parent, text="Export Model A to XML", command=self._run_export).pack(pady=5)
        self.export_var = tk.StringVar(value="Export Status: ")
        ttk.Label(parent, textvariable=self.export_var).pack(pady=5)

    def _admin_tab(self, parent: ttk.Frame):
        ttk.Label(parent, text="ArcheoConverter v1.0.0").pack(pady=10)
        ttk.Label(parent, text="Enterprise Architecture Model Management System").pack(pady=5)
        ttk.Button(parent, text="View Model Summary", command=self._show_summary).pack(pady=5)
        self.admin_var = tk.StringVar(value="Admin Info: ")
        ttk.Label(parent, textvariable=self.admin_var).pack(pady=5)

    # Actions
    def _load_model_a(self):
        path = filedialog.askopenfilename(filetypes=[("ArchiMate XML", "*.xml")])
        if path:
            self.model = parse_archimate_stream(path)
            self.status_var.set(f"Model A loaded: {self.model.name} (v{self.model.version})")

    def _load_model_b(self):
        path = filedialog.askopenfilename(filetypes=[("ArchiMate XML", "*.xml")])
        if path:
            self.model_b = parse_archimate_stream(path)
            self.status_var.set(f"Model B loaded: {self.model_b.name} (v{self.model_b.version})")

    def _run_search(self):
        if not self.model:
            self.result_var.set("No model loaded.")
            return
        q = self.search_entry.get()
        results = search_elements(self.model, q)
        self.result_var.set(f"Found {len(results)} elements: {results[:5]}...")

    def _run_compare(self):
        if not self.model or not self.model_b:
            self.compare_var.set("Load both models first.")
            return
        report = compare_models(self.model, self.model_b)
        self.compare_var.set(f"Added: {len(report.added_elements)}, Removed: {len(report.removed_elements)}, Modified: {len(report.modified_elements)}")

    def _run_integrate(self):
        if not self.model or not self.model_b:
            self.compare_var.set("Load both models first.")
            return
        integrate_models(self.model, self.model_b, "merge")
        self.compare_var.set("Integration completed (merge).")

    def _run_convert(self):
        if not self.model:
            self.convert_var.set("Load Model A first.")
            return
        target = self.version_var.get()
        self.model = migrate_model(self.model, target)
        self.convert_var.set(f"Migrated to v{target}")

    def _run_export(self):
        if not self.model:
            self.export_var.set("Load Model A first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xml", filetypes=[("ArchiMate XML", "*.xml")])
        if path:
            export_to_xml(self.model, path)
            self.export_var.set(f"Exported to {path}")

    def _show_summary(self):
        if not self.model:
            self.admin_var.set("No model loaded.")
            return
        summary = generate_model_summary(self.model)
        self.admin_var.set(f"Elements: {summary['total_elements']}, Relationships: {summary['total_relationships']}, Views: {summary['total_views']}")

def run_ui():
    root = tk.Tk()
    ArcheoConverterUI(root)
    root.mainloop()
