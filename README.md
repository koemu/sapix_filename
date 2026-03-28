# sapix-filename

SAPIX のスキャンPDFに対して、表紙からファイル名を推定し、必要に応じてリネーム（または `mv` コマンド形式で出力）する CLI ツールです。

また、PDF のフッターのページ番号を検証し、スキャンの欠落や並び不正を検出します。

## インストール

このリポジトリ直下で以下を実行します。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

## 使い方（コマンドライン）

### 基本

```bash
sapix-filename /path/to/orig.pdf
```

デフォルトでは **実ファイルは変更せず**、標準出力に `mv` コマンド形式で出力します。

### `mv` 形式での出力

```bash
sapix-filename /path/to/orig.pdf
```

出力例（フルパス）:

```bash
mv "/abs/path/orig.pdf" "/abs/path/H350-01_orig.pdf"
```

### 推定ファイル名だけを出力

```bash
sapix-filename --name-only /path/to/orig.pdf
```

出力例:

```text
H350-01_orig.pdf
```

### リネームを実行する

```bash
sapix-filename --apply /path/to/orig.pdf
```

成功時は新しいファイル名を標準出力に出します。

## 推定されるファイル名の形式

推定できた場合、基本的に以下の形式になります。

```text
<推定stem>_<元ファイル名stem>.pdf
```

例:

```text
H350-01_orig.pdf
```

### 1つ目のフォーマット（算数基礎力定着テスト）

表紙テキストに `算数基礎力定着テスト` があり、続く `06①` のようなトークンが読み取れる場合:

```text
算数基礎力定着テスト06①_orig.pdf
```

このフォーマットでは `_Answer_` / `_Question_` / `_Exam_` の付与は行いません。

### 2つ目のフォーマット（四角枠のテキスト番号）

表紙の四角枠の「テキスト番号」を推定します（例: `H350-01`, `WS-01`, `62A-01`, `640-01`, `61-01`）。

```text
H350-01_orig.pdf
62A-01_orig.pdf
```

#### `WS-` の場合の教科名付与

テキスト番号が `WS-` から始まる場合、表紙から教科（`国語/算数/理科/社会`）を抽出して先頭に付与します。

```text
国語WS-01_orig.pdf
```

#### 内容に応じたタグ付与（2つ目フォーマットのみ）

表紙（または文書内）の文言に応じて、以下のタグが付与されます。

```text
<テキスト番号>_Answer_<元stem>.pdf
<テキスト番号>_Question_<元stem>.pdf
<テキスト番号>_Exam_<元stem>.pdf
```

例:

```text
H350-01_Answer_orig.pdf
H350-01_Question_orig.pdf
61-01_Exam_orig.pdf
```

## AI（生成AI / Vision）の利用

スキャンPDFでは `get_text()` で文字が取れないことがあるため、必要に応じて OpenAI の Vision を使って抽出精度を上げます。

### API キー設定

```bash
export OPENAI_API_KEY="..."
```

環境変数名は `--api-key-env` で変更できます。

### AI を無効化

```bash
sapix-filename --no-ai /path/to/orig.pdf
```

### 使用モデルを変更

```bash
sapix-filename --ai-model gpt-5.4-mini /path/to/orig.pdf
```

## ページ番号の精査

実行時に、PDFのフッターにあるページ番号を検証します（2ページ以下は対象外）。

- ページ番号が重複している
- ページ番号が連続していない
- （全ページに番号がある場合に限り）最終ページ番号と実際のページ数が一致しない

上記に該当すると標準エラー出力へメッセージを出し、終了コード `1` で終了します。

## 開発者向け

### テスト

```bash
python -m pip install -e .[dev]
pytest
```
