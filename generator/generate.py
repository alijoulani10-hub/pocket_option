from __future__ import annotations

import logging
import pathlib
import subprocess

import jinja2
import pydantic
import yaml
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)


TEMPLATES_FORLDER = pathlib.Path(__file__).parent / "templates"
EVENTS_FOLDER = pathlib.Path(__file__).parent / "events"
GENERATED_CLIENT_FILE = pathlib.Path(
    pathlib.Path(__file__).parent.parent, "pocket_option", "generated_client.py"
).absolute()


class OnMethod(pydantic.BaseModel):
    name: str
    event: str
    return_type: str
    category: str | None = None
    doc: str | None = None
    pydantic_model: str | None = None


class EmitMethodArg(pydantic.BaseModel):
    name: str
    type: str
    doc: str | None = None
    default: str | None = None
    pydantic_model: str | None = None
    cast: str | None = None


class EmitMethod(pydantic.BaseModel):
    name: str
    event: str
    category: str | None = None
    doc: str | None = None
    args: EmitMethodArg | None = None


class Data(pydantic.BaseModel):
    on: list[OnMethod]
    emit: list[EmitMethod]


env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_FORLDER), autoescape=False)  # noqa: S701


def generate():
    data = Data.model_validate(
        {
            "on": yaml.safe_load(
                pathlib.Path(EVENTS_FOLDER, "on.yaml").read_text(encoding="utf-8"),
            ),
            "emit": yaml.safe_load(
                pathlib.Path(EVENTS_FOLDER, "emit.yaml").read_text(encoding="utf-8"),
            ),
        },
    )

    layout = env.get_template("layout.jinja2")
    GENERATED_CLIENT_FILE.write_text(layout.render(data=data))

    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "poetry",
            "run",
            "ruff",
            "format",
            str(GENERATED_CLIENT_FILE),
        ],
        check=True,
    )
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "poetry",
            "run",
            "ruff",
            "check",
            str(GENERATED_CLIENT_FILE),
            "--fix",
            "--unsafe-fixes",
        ],
        check=True,
    )


if __name__ == "__main__":
    generate()
