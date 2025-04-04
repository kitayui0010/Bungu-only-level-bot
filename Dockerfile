# Python 3.9 の公式イメージを使用
FROM python:3.9

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコンテナ内にコピー
COPY . /app

# 依存パッケージをインストール
RUN pip install discord.py

# 環境変数を設定（Northflank の環境変数を使用）
ENV YOUR_BOT_TOKEN=${YOUR_BOT_TOKEN}

# ボットを起動
CMD ["python", "bot.py"]
