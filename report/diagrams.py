"""Chapter IV figures. Layout and arrows come from PlantUML, not hand-placed boxes."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUML = ROOT / "puml"
JAR = ROOT / "plantuml.jar"

SOURCES = (
    "architecture.puml",
    "dfd_context.puml",
    "dfd_level1.puml",
    "usecase.puml",
    "class_diagram.puml",
    "sequence.puml",
    "activity.puml",
    "er.puml",
)


def draw_all(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    dot = shutil.which("dot")
    command = [
        "java",
        "-Djava.awt.headless=true",
        "-jar",
        str(JAR),
        "-tpng",
        "-charset",
        "UTF-8",
        "-o",
        str(folder),
    ]
    if dot:
        command.extend(["-graphvizdot", dot])
    command.extend(str(PUML / name) for name in SOURCES)
    subprocess.run(command, check=True)
