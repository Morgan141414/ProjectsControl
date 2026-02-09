from pathlib import Path


def load_stylesheet(theme: str = "dark", background_path: str | None = None) -> str:
    base_dir = Path(__file__).resolve().parent
    if theme == "dark":
        path = base_dir / "style_dark.qss"
    elif theme == "ios":
        path = base_dir / "style_ios.qss"
    else:
        path = base_dir / "style.qss"

    stylesheet = path.read_text(encoding="utf-8")

    if background_path:
        background_rule = (
            "\nQMainWindow {\n"
            f"    background-image: url(\"{background_path}\");\n"
            "    background-position: center;\n"
            "    background-repeat: no-repeat;\n"
            "    background-attachment: fixed;\n"
            "}\n"
        )
        stylesheet += background_rule

    return stylesheet
