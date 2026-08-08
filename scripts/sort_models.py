import pathlib
import subprocess

MODELS_FILE = (pathlib.Path(__file__).parent.parent / "pocket_option" / "models.py").resolve().absolute()
TEMP_MODELS_FILE = (pathlib.Path(__file__).parent.parent / "pocket_option" / "models_tmp.py").resolve().absolute()

text_content = MODELS_FILE.read_text(encoding="utf-8")

content = text_content.split("\n\n\n")

content = content[:7] + sorted(content[7:], key=lambda x: x.removeprefix("class "))
TEMP_MODELS_FILE.write_text("\n\n\n".join(content), encoding="utf-8")
try:
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "poetry",
            "run",
            "ruff",
            "format",
            str(TEMP_MODELS_FILE),
        ],
        check=True,
    )
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "poetry",
            "run",
            "ruff",
            "check",
            str(TEMP_MODELS_FILE),
            "--fix",
            "--unsafe-fixes",
        ],
        check=True,
    )
except subprocess.CalledProcessError as e:
    print("Error occurred while running ruff:", e)
    print("Output:", e.output)
    print("Return code:", e.returncode)
    exit(1)
else:
    MODELS_FILE.write_text(TEMP_MODELS_FILE.read_text(), encoding="utf-8")
finally:
    if TEMP_MODELS_FILE.exists():
        TEMP_MODELS_FILE.unlink()
