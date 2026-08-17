from __future__ import annotations

from clipfetch.core.errors import AppError


class ErrorTranslator:
    """Translate common yt-dlp failures into stable application errors."""

    RULES = (
        (
            ("private video", "this video is private"),
            "Conteúdo privado",
            (
                "Este conteúdo é privado. Se você tiver acesso, configure os "
                "cookies do navegador nas Preferências."
            ),
            "private",
        ),
        (
            ("sign in", "login required", "authentication"),
            "Login necessário",
            (
                "O site exige uma sessão autenticada. Configure os cookies do "
                "navegador nas Preferências e tente novamente."
            ),
            "authentication",
        ),
        (
            ("unsupported url", "no suitable extractor"),
            "Link não suportado",
            "O yt-dlp não encontrou uma integração compatível com este endereço.",
            "unsupported",
        ),
        (
            ("http error 403", "forbidden"),
            "Acesso recusado pelo site",
            (
                "O servidor recusou o acesso. Atualizar o yt-dlp ou usar cookies "
                "de uma sessão válida pode resolver."
            ),
            "http403",
        ),
        (
            ("http error 404", "not found"),
            "Conteúdo não encontrado",
            "O endereço respondeu com HTTP 404.",
            "http404",
        ),
        (
            ("no space left on device",),
            "Sem espaço no disco",
            "Não há espaço livre suficiente para concluir o download.",
            "disk",
        ),
        (
            ("requested format is not available",),
            "Qualidade indisponível",
            (
                "A resolução ou formato selecionado não está disponível para "
                "este conteúdo."
            ),
            "format",
        ),
        (
            ("age-restricted", "age restricted"),
            "Conteúdo com restrição de idade",
            (
                "O site exige uma sessão autenticada para este conteúdo. "
                "Cookies do navegador podem ser necessários."
            ),
            "age",
        ),
        (
            (
                "only images",
                "storyboard",
                "mhtml",
                "vcodec=images",
                "no real media stream",
            ),
            "Nenhum vídeo/áudio utilizável encontrado",
            (
                "O yt-dlp encontrou apenas imagens de pré-visualização ou "
                "storyboards, não um stream real de vídeo/áudio."
            ),
            "storyboard",
        ),
    )

    @classmethod
    def to_error(
        cls,
        raw_text: str,
        *,
        default_title: str = "Não foi possível concluir a operação",
        default_message: str = (
            "O yt-dlp retornou um erro. Abra os detalhes técnicos se precisar "
            "diagnosticar o problema."
        ),
    ) -> AppError:
        technical = (raw_text or "").strip()
        normalized = technical.casefold()

        for patterns, title, message, code in cls.RULES:
            if any(pattern in normalized for pattern in patterns):
                return AppError(
                    title,
                    message,
                    technical,
                    code,
                )

        return AppError(
            default_title,
            default_message,
            technical,
            "generic",
        )

    @classmethod
    def timeout(
        cls,
        *,
        operation: str,
        seconds: int,
        technical_details: str,
    ) -> AppError:
        if operation == "sources":
            return AppError(
                "A lista de fontes demorou demais",
                (
                    "O yt-dlp não terminou de fornecer a lista dentro do tempo "
                    f"esperado ({seconds}s). O aplicativo continua responsivo; "
                    "tente Recarregar novamente."
                ),
                technical_details,
                "timeout_sources",
            )

        return AppError(
            "A análise do link demorou demais",
            (
                "O yt-dlp não terminou a análise dentro do tempo esperado "
                f"({seconds}s). Isso não significa necessariamente que o link "
                "seja inválido."
            ),
            technical_details,
            "timeout_analysis",
        )
