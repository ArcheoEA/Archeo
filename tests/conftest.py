"""PyTest fixtures shared by the whole ArcheoConverter test-suite.

The ``src`` directory is added to ``sys.path`` so the tests run directly
from a checkout (``pytest``) without installing the package.

Main fixtures:

* ``config``        - a clean in-memory configuration (no log file);
* ``app``           - a FastAPI application instance;
* ``client``        - an in-process ASGI test client bound to ``app``;
* ``state``         - the application state (repository + services);
* ``data_dir``      - directory containing the sample model files;
* ``sample_*``      - raw bytes of each sample model file;
* ``imported_32``   - a sample ArchiMate 3.2 model imported through the
  import service (unit-level, no HTTP).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `import ArcheoConverter` work without installing the package.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ArcheoConverter.application import AppState, build_state  # noqa: E402
from ArcheoConverter.config import AppConfig  # noqa: E402
from asgi_client import ASGIClient  # noqa: E402


# --------------------------------------------------------------------- #
# Configuration / application
# --------------------------------------------------------------------- #
@pytest.fixture()
def config() -> AppConfig:
    """A minimal configuration (console logging disabled by the app flag)."""
    return AppConfig(
        logging=AppConfig().logging.model_copy(update={"file": None}),
    )


@pytest.fixture()
def state(config: AppConfig) -> AppState:
    """A fresh application state (empty repository)."""
    return build_state(config)


@pytest.fixture()
def app(config: AppConfig):
    """A FastAPI application instance with an isolated state."""
    from ArcheoConverter.application import create_app

    return create_app(config, setup_app_logging=False)


@pytest.fixture()
def client(app) -> ASGIClient:
    """An in-process ASGI test client."""
    return ASGIClient(app)


# --------------------------------------------------------------------- #
# Sample data
# --------------------------------------------------------------------- #
@pytest.fixture()
def data_dir() -> Path:
    """Directory holding the sample model files."""
    return Path(__file__).resolve().parent / "data"


def _read(data_dir: Path, name: str) -> bytes:
    return (data_dir / name).read_bytes()


@pytest.fixture()
def sample_32(data_dir: Path) -> bytes:
    """Raw ArchiMate 3.2 sample file."""
    return _read(data_dir, "sample_32.archimate")


@pytest.fixture()
def sample_40(data_dir: Path) -> bytes:
    """Raw ArchiMate 4.0 sample file (contains the 4.0 'resource' concept)."""
    return _read(data_dir, "sample_40.archimate")


@pytest.fixture()
def sample_bpmn(data_dir: Path) -> bytes:
    """Raw BPMN 2.0 sample file."""
    return _read(data_dir, "sample.bpmn")


@pytest.fixture()
def sample_uml(data_dir: Path) -> bytes:
    """Raw UML XMI sample file."""
    return _read(data_dir, "sample_uml.xmi")


@pytest.fixture()
def sample_sysml(data_dir: Path) -> bytes:
    """Raw SysML XMI sample file."""
    return _read(data_dir, "sample_sysml.xmi")


@pytest.fixture()
def imported_32(state: AppState, sample_32: bytes):
    """The ArchiMate 3.2 sample imported through the import service."""
    result = state.importer.import_content(
        sample_32,
        repository=state.repository,
        filename="sample_32.archimate",
        model_id="model-32",
        name="Sample 3.2",
    )
    return state.repository.get(result.model_id)


@pytest.fixture()
def imported_40(state: AppState, sample_40: bytes):
    """The ArchiMate 4.0 sample imported through the import service."""
    result = state.importer.import_content(
        sample_40,
        repository=state.repository,
        filename="sample_40.archimate",
        model_id="model-40",
        name="Sample 4.0",
    )
    return state.repository.get(result.model_id)
