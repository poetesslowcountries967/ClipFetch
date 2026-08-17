from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALES_DIR = (
    ROOT
    / "clipfetch"
    / "i18n"
    / "locales"
)

REQUIRED_META = {
    "code",
    "name",
    "native_name",
    "date_format",
    "datetime_format",
}

CORE_STRINGS = {
    "Downloads",
    "Histórico",
    "Preferências",
    "Configurações",
    "Analisar e adicionar",
    "Fontes suportadas",
    "Baixar fila",
    "Mostrar detalhes técnicos",
    "Salvar preferências",
    "Idioma:",
    "Redefinir aplicativo",
    "Apagar dados do aplicativo e restaurar padrões",
    "Modo desenvolvedor",
}


def validate_mapping(
    path,
    name,
    value,
):
    if not isinstance(
        value,
        dict,
    ):
        raise SystemExit(
            (
                f"ERRO {path.name}: "
                f"{name} deve ser um objeto JSON."
            )
        )

    invalid = any(
        not isinstance(key, str)
        or not isinstance(text, str)
        for key, text
        in value.items()
    )

    if invalid:
        raise SystemExit(
            (
                f"ERRO {path.name}: "
                f"{name} aceita apenas strings."
            )
        )


def main():
    seen = set()

    for path in sorted(
        LOCALES_DIR.glob(
            "*.json"
        )
    ):
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        meta = (
            data.get("meta")
            or {}
        )

        missing_meta = (
            REQUIRED_META
            - set(meta)
        )

        if missing_meta:
            raise SystemExit(
                (
                    f"ERRO {path.name}: "
                    "meta ausente: "
                    f"{sorted(missing_meta)}"
                )
            )

        code = str(
            meta["code"]
        ).strip()

        if (
            not code
            or code in seen
        ):
            raise SystemExit(
                (
                    f"ERRO {path.name}: "
                    "código inválido/duplicado"
                )
            )

        seen.add(code)

        strings = data.get(
            "strings",
            {},
        )
        replacements = data.get(
            "replacements",
            {},
        )

        validate_mapping(
            path,
            "strings",
            strings,
        )
        validate_mapping(
            path,
            "replacements",
            replacements,
        )

        if code != "pt-BR":
            missing_strings = (
                CORE_STRINGS
                - set(strings)
            )

            if missing_strings:
                raise SystemExit(
                    (
                        f"ERRO {path.name}: "
                        "traduções essenciais ausentes: "
                        f"{sorted(missing_strings)}"
                    )
                )

        print(
            "✓",
            path.name,
            "->",
            code,
        )

    if "pt-BR" not in seen:
        raise SystemExit(
            "ERRO: pt-BR ausente"
        )

    print(
        "✓",
        len(seen),
        "idioma(s) válido(s)",
    )


if __name__ == "__main__":
    main()
