# 🐟 Fish Audio リアルタイム会話アプリ

Fish Audio APIを使用したリアルタイム音声会話Webアプリケーションです。

## 機能

- 🎤 リアルタイム音声録音
- 🔊 音声認識（Speech-to-Text）
- 🗣️ 音声合成（Text-to-Speech）
- 💬 テキストメッセージ送信
- 🔄 WebSocketによるリアルタイム通信
- 📱 レスポンシブデザイン

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. Fish Audio APIキーの取得

1. [Fish Audio API](https://api.fish-audio.com) にアクセス
2. アカウントを作成し、APIキーを取得
3. `.env` ファイルを作成し、APIキーを設定

```bash
# .envファイルを作成
cp env_example.txt .env

# .envファイルを編集してAPIキーを設定
FISH_AUDIO_API_KEY=your_actual_api_key_here
```

### 3. アプリケーションの起動

```bash
python app.py
```

ブラウザで `http://localhost:5000` にアクセスしてください。

## 使用方法

### 音声会話

1. 「🎤 録音開始」ボタンをクリック
2. マイクへのアクセスを許可
3. 話しかける
4. 「⏹️ 録音停止」ボタンをクリック
5. 音声が認識され、応答が音声で返されます

### テキスト会話

1. テキスト入力欄にメッセージを入力
2. 「📤 送信」ボタンをクリック（またはEnterキー）
3. 応答が音声で返されます

## ファイル構成

```
fish-audio-app/
├── app.py                 # Flaskアプリケーション（メイン）
├── requirements.txt       # Python依存関係
├── env_example.txt       # 環境変数設定例
├── README.md             # このファイル
└── templates/
    └── index.html        # フロントエンドUI
```

## 技術仕様

- **バックエンド**: Flask + Flask-SocketIO
- **フロントエンド**: HTML5 + JavaScript + Socket.IO
- **音声処理**: Web Audio API + MediaRecorder
- **通信**: WebSocket（Socket.IO）
- **API**: Fish Audio API（音声認識・合成）

## トラブルシューティング

### マイクへのアクセスが拒否される

- ブラウザの設定でマイクアクセスを許可してください
- HTTPS環境で実行していることを確認してください

### APIキーエラー

- `.env` ファイルに正しいAPIキーが設定されているか確認
- Fish Audio APIの利用制限や課金状況を確認

### 音声が再生されない

- ブラウザの音声再生設定を確認
- 音声ファイルの形式が正しいか確認

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグレポートや機能リクエスト、プルリクエストを歓迎します。

## サポート

問題が発生した場合は、GitHubのIssuesページで報告してください。


