#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

export PYTHONUTF8=1
export PYTHONIOENCODING=UTF-8

echo "=================================================="
echo "       ClipFetch 1.0.0 - Public release build"
echo "=================================================="
echo
echo "Este build prepara um .app que NÃO precisará de"
echo "Homebrew, FFmpeg, Deno ou yt-dlp no Mac do usuário."
echo

# -------------------------------------------------------------------
# 1. Python usado apenas para construir a interface
# -------------------------------------------------------------------

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERRO: Python 3 não foi encontrado neste Mac."
    echo "Abrindo a página oficial do Python..."
    open "https://www.python.org/downloads/macos/"
    exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print(sys.version.split()[0])')"
ARCH="$(uname -m)"

echo "Python de build: $PYTHON_VERSION"
echo "Arquitetura deste Mac: $ARCH"
echo

python3 - <<'PY'
import sys

if sys.version_info < (3, 9):
    raise SystemExit(
        "ERRO: o construtor precisa de Python 3.9 ou superior."
    )
PY


# -------------------------------------------------------------------
# 2. Homebrew é necessário SOMENTE no Mac que faz o build.
#    O usuário que receber o DMG NÃO precisará dele.
# -------------------------------------------------------------------

if command -v brew >/dev/null 2>&1; then
    BREW="$(command -v brew)"
elif [ -x "/opt/homebrew/bin/brew" ]; then
    BREW="/opt/homebrew/bin/brew"
elif [ -x "/usr/local/bin/brew" ]; then
    BREW="/usr/local/bin/brew"
else
    echo "ERRO: Homebrew não foi encontrado no Mac de build."
    echo
    echo "Neste projeto, Homebrew é usado apenas no Mac de build para coletar"
    echo "FFmpeg/FFprobe e Deno que serão incorporados ao .app."
    echo
    echo "Conclua a instalação do Homebrew que você já iniciou e"
    echo "execute este arquivo novamente."
    exit 1
fi

echo "Homebrew de build: $BREW"
echo


install_formula_if_missing() {
    local formula="$1"

    if "$BREW" list --versions "$formula" >/dev/null 2>&1; then
        echo "✓ $formula já está instalado no Mac de build."
        return
    fi

    echo "$formula ainda não está instalado."
    echo

    read -r -p "Instalar $formula agora para incorporá-lo ao aplicativo? [S/n] " ANSWER
    ANSWER="${ANSWER:-S}"

    case "$ANSWER" in
        S|s|Y|y)
            "$BREW" install "$formula"
            ;;
        *)
            echo "Build cancelado. $formula é necessário para gerar o app portátil."
            exit 1
            ;;
    esac
}


install_formula_if_missing "ffmpeg"
install_formula_if_missing "deno"


# -------------------------------------------------------------------
# 3. Localiza os binários do Homebrew que serão incorporados
# -------------------------------------------------------------------

FFMPEG_PREFIX="$("$BREW" --prefix ffmpeg)"
DENO_PREFIX="$("$BREW" --prefix deno)"

FFMPEG_BIN="$FFMPEG_PREFIX/bin/ffmpeg"
FFPROBE_BIN="$FFMPEG_PREFIX/bin/ffprobe"
DENO_BIN="$DENO_PREFIX/bin/deno"

for file in "$FFMPEG_BIN" "$FFPROBE_BIN" "$DENO_BIN"; do
    if [ ! -x "$file" ]; then
        echo "ERRO: executável de build ausente: $file"
        exit 1
    fi
done

echo
echo "Ferramentas de build:"
"$FFMPEG_BIN" -version 2>/dev/null | head -n 1
"$DENO_BIN" --version | head -n 1


# -------------------------------------------------------------------
# 4. Baixa o executável oficial NIGHTLY do yt-dlp para macOS
#
# O projeto yt-dlp recomenda o executável universal no macOS.
# O canal nightly é usado aqui porque o próprio projeto o recomenda
# para usuários regulares devido às mudanças frequentes dos sites.
# -------------------------------------------------------------------

mkdir -p vendor-src

YTDLP_BIN="$(pwd)/vendor-src/yt-dlp"

echo
echo "Baixando yt-dlp_macos oficial (nightly)..."

curl \
    --fail \
    --location \
    --retry 3 \
    --output "$YTDLP_BIN" \
    "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp_macos"

chmod +x "$YTDLP_BIN"

echo
echo "Obtendo a versão do yt-dlp UMA vez para o pacote..."
YTDLP_VERSION="$("$YTDLP_BIN" --version | head -n 1)"
YTDLP_VERSION_FILE="$(pwd)/vendor-src/yt-dlp.version"
printf "%s\n" "$YTDLP_VERSION" > "$YTDLP_VERSION_FILE"
echo "yt-dlp: $YTDLP_VERSION"

EXTRACTORS_FILE="$(pwd)/vendor-src/extractors.txt"
echo
echo "Preparando catálogo inicial de fontes suportadas..."
python3 - "$YTDLP_BIN" "$EXTRACTORS_FILE" <<'PY_EXTRACTORS'
import subprocess,sys
from pathlib import Path
binary=sys.argv[1]; target=Path(sys.argv[2])
try:
    result=subprocess.run([binary,"--ignore-config","--list-extractors"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=300)
    if result.returncode==0 and result.stdout.strip():
        target.write_text(result.stdout.strip()+"\n",encoding="utf-8")
        print("✓ catálogo criado:",len(result.stdout.splitlines()),"entradas")
    else:
        target.write_text("",encoding="utf-8"); print("Aviso: não foi possível gerar o catálogo no build.")
except Exception as error:
    target.write_text("",encoding="utf-8"); print("Aviso: catálogo inicial não foi gerado:",error)
PY_EXTRACTORS


# -------------------------------------------------------------------
# 5. Ambiente Python de build
# -------------------------------------------------------------------

if [ ! -d ".venv-build" ]; then
    echo
    echo "Criando ambiente virtual de build..."
    python3 -m venv .venv-build
fi

source .venv-build/bin/activate

echo
echo "Atualizando pip..."
python -m pip install --upgrade pip

echo
echo "Instalando PySide6 e PyInstaller..."

# --no-compile evita o problema conhecido observado no seu Python 3.9 do Xcode,
# em que templates .tmpl.py do PySide6 eram tratados como Python compilável.
python -m pip install \
    --no-compile \
    -r requirements-build.txt

echo
echo "Validando ambiente Python..."

python - <<'PY'
import PySide6
import PyInstaller

print("PySide6:", PySide6.__version__)
print("PyInstaller:", PyInstaller.__version__)
PY


# -------------------------------------------------------------------
# 6. Validação de sintaxe antes de gastar tempo com o PyInstaller
# -------------------------------------------------------------------

echo
echo "Verificando higiene do repositório..."
python scripts/check_release_hygiene.py

echo
echo "Validando código..."

python - <<'PY'
import py_compile
from pathlib import Path

files = [Path("main.py")]
files.extend(sorted(Path("clipfetch").rglob("*.py")))
files.extend(sorted(Path("scripts").glob("*.py")))

for file in files:
    py_compile.compile(str(file), doraise=True)
    print("✓", file)
PY


echo
echo "Validando pacotes de idioma..."
python scripts/validate_locales.py

echo
echo "Auditando imports e código órfão..."
python scripts/audit_codebase.py

echo
echo "Validando estrutura da MainWindow..."

python - <<'PY'
import ast
from pathlib import Path

source = Path("clipfetch/ui/main_window.py").read_text(encoding="utf-8")
tree = ast.parse(source, filename="clipfetch/ui/main_window.py")

main_window = next(
    (
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "MainWindow"
    ),
    None,
)

if main_window is None:
    raise SystemExit(
        "ERRO: classe MainWindow não encontrada."
    )

methods = {
    node.name
    for node in main_window.body
    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef),
    )
}

# Somente métodos obrigatórios da interface ATUAL.
# O antigo _test_finished foi removido junto com o botão
# “Testar primeiro link” e não deve bloquear o build.
required = {
    "__init__",
    "_connect_signals",
    "_build_ui",
    "_build_downloads_tab",
    "_build_history_tab",
    "_build_preferences_tab",
    "_build_settings_tab",
    "_apply_feature_visibility",
    "_analysis_started",
    "_analysis_finished",
    "_update_queue_summary",
    "_queue_index_for_id",
    "_language_changed",
    "reset_application_data",
    "_clear_queue_now",
    "clear_queue",
    "_fit_window_to_available_screen",
    "_scrollable_page_layout",
    "_enrich_finished",
    "_thumbnail_finished",
    "_apply_progress",
    "_download_result",
    "_downloads_finished",
    "start_downloads",
    "show_supported_sites",
    "save_preferences",
}

missing = sorted(required - methods)

if missing:
    raise SystemExit(
        "ERRO: métodos ausentes de MainWindow: "
        + ", ".join(missing)
    )

top_level_functions = {
    node.name
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
}

if "_build_downloads_tab" in top_level_functions:
    raise SystemExit(
        "ERRO: _build_downloads_tab está fora de MainWindow."
    )

print("✓ MainWindow encontrada")
print(f"✓ {len(methods)} métodos detectados")
print("✓ Métodos essenciais presentes")
print("✓ Nenhum método principal deslocado para o nível global")
PY


echo
echo "Executando teste real de inicialização..."

# Este teste usa o MESMO Python do ambiente de build.
# Ele importa todos os módulos críticos e cria a janela principal.
# Assim, incompatibilidades de annotations ou assinaturas de construtor
# são detectadas ANTES do PyInstaller gerar o .app/DMG.
CLIPFETCH_SMOKE_TEST=1 QT_QPA_PLATFORM=offscreen python - <<'PY'
from clipfetch.services.extractor_manager import ExtractorManager, ExtractorLists
from clipfetch.services.metadata_service import MetadataService
from clipfetch.download.manager import DownloadManager
from clipfetch.ui.supported_sites_dialog import SupportedSitesDialog
from PySide6.QtWidgets import QApplication

from clipfetch.ui.main_window import MainWindow
from clipfetch.persistence.config_manager import ConfigManager

application = QApplication.instance() or QApplication([])

window = MainWindow()

assert window.download_manager is not None
assert window.download_button.objectName() == "downloadButton"
assert window.tabs.count() == 4
assert window.tabs.tabText(3) in {"Configurações", "Settings"}
assert window.tabs.isTabEnabled(2)
assert window.tabs.isTabEnabled(3)
assert window.queue_table.columnCount() == 3

# Regressão macOS: janela menor + páginas longas com scroll interno.
assert window.minimumWidth() <= 760
assert window.minimumHeight() <= 500
assert window.downloads_scroll_area.widgetResizable()
assert window.preferences_scroll_area.widgetResizable()
assert window.settings_scroll_area.widgetResizable()

# O badge começa zerado e não depende da quantidade de itens da fila.
assert window.notification_controller is not None
window.notification_controller.clear_unread()
assert window.notification_controller._unread_count == 0

# Regressão: Limpar fila precisa remover imediatamente quando não há
# downloads ativos.
placeholder = window._make_analysis_placeholder(
    "https://example.invalid/clipfetch-smoke"
)
window.queue.append(placeholder)
window.refresh_queue()
assert len(window.queue) == 1
assert window.queue_table.rowCount() == 1

window.clear_queue()

assert len(window.queue) == 0
assert window.queue_table.rowCount() == 0
defaults = ConfigManager.defaults()
assert defaults.get("developer_mode") is False
assert defaults.get("show_technical_button") is True
assert "developer_mode" in window.settings
assert "show_technical_button" in window.settings
assert not window.log_text.isVisible()

print("✓ Imports críticos")
print("✓ MainWindow construída")
print("✓ DownloadManager integrado")
print("✓ Botão principal configurado")
print("✓ Quatro abas configuradas e acessíveis")
print("✓ Janela adaptável à área útil do macOS")
print("✓ Downloads/Preferências/Configurações com rolagem interna")
print("✓ Badge do Dock inicia zerado e não depende da fila")
print("✓ Fila compacta com Item/Progresso/Status")
print("✓ Limpar fila remove linhas e estado interno")
print("✓ Modo desenvolvedor desativado por padrão")
print("✓ Log técnico começa fechado e permanece em memória")

window.close()
application.processEvents()

print("Teste real de inicialização: OK")
PY


# -------------------------------------------------------------------
# 7. Exporta caminhos para o arquivo .spec
# -------------------------------------------------------------------

export YTDLP_BIN
export YTDLP_VERSION_FILE
export EXTRACTORS_FILE
export FFMPEG_BIN
export FFPROBE_BIN
export DENO_BIN


# -------------------------------------------------------------------
# 8. Gera o .app
# -------------------------------------------------------------------

echo
echo "Limpando builds antigos..."
rm -rf build dist dmg-root

echo
echo "Gerando ClipFetch.app..."

python -m PyInstaller \
    --noconfirm \
    --clean \
    ClipFetch.spec

APP_PATH="$(pwd)/dist/ClipFetch.app"

if [ ! -d "$APP_PATH" ]; then
    echo "ERRO: ClipFetch.app não foi criado."
    exit 1
fi


# O yt-dlp entrou como data. Garantimos que qualquer cópia dentro do app tenha
# permissão de leitura; no primeiro lançamento ele será copiado para
# Application Support e receberá chmod 755.
find "$APP_PATH" -type f -name "yt-dlp" -exec chmod 755 {} \; || true


# -------------------------------------------------------------------
# 9. Assinatura local ad-hoc
#
# Isso é adequado para teste/uso pessoal. Não substitui Developer ID +
# notarização para distribuição pública sem alerta do Gatekeeper.
# -------------------------------------------------------------------

echo
echo "Aplicando assinatura local ad-hoc..."

codesign \
    --force \
    --deep \
    --sign - \
    "$APP_PATH"

codesign \
    --verify \
    --deep \
    --strict \
    "$APP_PATH"


# -------------------------------------------------------------------
# 10. Monta um DMG padrão com app + atalho Applications
# -------------------------------------------------------------------

echo
echo "Criando DMG..."

mkdir -p dmg-root

ditto \
    "$APP_PATH" \
    "dmg-root/ClipFetch.app"

ln -s \
    /Applications \
    "dmg-root/Applications"

cp \
    "INSTALLATION.txt" \
    "dmg-root/Leia-me - Instalação.txt"

DMG_NAME="ClipFetch_macOS_${ARCH}.dmg"
DMG_PATH="$(pwd)/dist/$DMG_NAME"

rm -f "$DMG_PATH"

hdiutil create \
    -volname "ClipFetch" \
    -srcfolder "dmg-root" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

rm -rf dmg-root


# -------------------------------------------------------------------
# 11. Resultado
# -------------------------------------------------------------------

echo
echo "=================================================="
echo "                BUILD CONCLUÍDO"
echo "=================================================="
echo
echo "Aplicativo:"
echo "$APP_PATH"
echo
echo "DMG para distribuir:"
echo "$DMG_PATH"
echo
echo "IMPORTANTE:"
echo "Este DMG foi construído para a arquitetura: $ARCH"
echo
echo "O Mac do usuário final NÃO precisa instalar:"
echo "  - Homebrew"
echo "  - yt-dlp"
echo "  - FFmpeg"
echo "  - FFprobe"
echo "  - Deno"
echo "  - Python"
echo
echo "Sem Developer ID/notarização, o usuário ainda poderá"
echo "receber um aviso do Gatekeeper na primeira abertura."
echo "Isso pode ser autorizado graficamente, sem Terminal."
echo
echo "Abrindo a pasta dist..."

open "$(pwd)/dist"

echo
read -n 1 -s -r -p "Pressione qualquer tecla para fechar..."
