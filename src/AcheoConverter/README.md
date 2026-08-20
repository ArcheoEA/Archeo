# ArcheoConverter

A Python application for ArchiMate model management, conversion, and comparison.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](https://pytest.org)

## Features

- **Import/Export**: Load ArchiMate models from XML (versions 3.2 and 4.0)
- **Version Migration**: Migrate models between versions (bidirectional: 3.2 ↔ 4.0)
- **Model Comparison**: Compare two models and generate difference reports
- **Search & Navigation**: Query elements, relationships, and folder trees
- **CLI + GUI Interfaces**: Use command-line or graphical interface

## Installation

### Requirements

- Python ≥ 3.9
- PyQt5 (for GUI)
- PyYAML, Jinja2, pydantic

### From source

```bash
git clone https://github.com/your-org/ArcheoConverter.git
cd ArcheoConverter
pip install -e .
