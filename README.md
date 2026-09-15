# JuntaAi

Aplicativo desktop portátil para Windows 10/11 focado em unir arquivos de **imagem**, **PDF** e **DOCX** em um único **PDF**.

## Visão geral

O MVP oferece:

- adição de arquivos mistos (`jpg`, `png`, `webp`, `bmp`, `tiff`, `pdf`, `docx`)
- lista central de itens para ordenar com **Subir** e **Descer**
- remoção de itens antes da exportação
- exportação em **PDF** com presets de compressão **Baixa / Média / Alta**
- logs locais em `logs/app.log`
- build portátil para Windows com **PyInstaller --onefile**

> No MVP a ordenação ocorre por **arquivo/item**. PDFs e DOCX preservam a ordem interna de suas páginas.

## Requisitos

- Python **3.11** (versão suportada e usada no build do MVP)
- Windows 10/11 para uso completo do fluxo com DOCX
- Microsoft Word instalado **apenas** quando for necessário converter DOCX para PDF

## Instalação de dependências

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Como executar em modo desenvolvimento

```bash
PYTHONPATH=src python -m juntaai
```

No Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m juntaai
```

## Como gerar o `.exe` portátil no Windows

Use o script incluído no repositório:

```bat
build_windows.bat
```

O script:

1. cria `.venv` se necessário
2. instala as dependências de `requirements.txt`
3. gera `dist\JuntaAi.exe` com `PyInstaller --onefile --windowed`

## Presets de compressão

| Nível | DPI alvo | Qualidade JPEG | Limite da maior dimensão |
| --- | ---: | ---: | ---: |
| Baixa | 300 | 92 | 2600 px |
| Média | 200 | 80 | 1800 px |
| Alta | 120 | 65 | 1280 px |

Os presets impactam principalmente arquivos de **imagem**, reduzindo resolução e qualidade JPEG das páginas geradas antes da montagem do PDF final.

## DOCX no MVP

O aplicativo tenta converter arquivos `.docx` para PDF usando **Microsoft Word via COM/PowerShell** quando executado no Windows.

Se a conversão não estiver disponível no ambiente:

- o app mostra uma mensagem amigável
- o processamento dos demais arquivos continua
- o evento fica registrado em `logs/app.log`

## Estrutura do projeto

```text
src/
  juntaai/
    converters/
    services/
    ui/
tests/
logs/
```

## Teste direcionado

```bash
PYTHONPATH=src python -m unittest tests.test_pdf_exporter
```

## Limitações conhecidas

- Saída suportada no MVP: **PDF**.
- A ordenação é por item/arquivo, não por página individual.
- A compressão atua diretamente nas imagens; páginas importadas de PDFs existentes são preservadas como estão.
- Conversão de DOCX depende de Windows com Microsoft Word disponível.
