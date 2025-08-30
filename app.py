import os
import json
import base64
import time
import threading
import csv
import io
import random
import re
from collections import OrderedDict
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import requests

# Fish Audio SDKのインポート
try:
    from fish_audio_sdk import Session
    FISH_AUDIO_SDK_AVAILABLE = True
    print("✅ Fish Audio SDKが利用可能です")
except ImportError:
    FISH_AUDIO_SDK_AVAILABLE = False
    print("⚠️  Fish Audio SDKが利用できません。pip install fish-audio-sdk を実行してください")
    print("   直接APIを使用します")

# ChatGPT APIのインポート
try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
    print("✅ OpenAI SDKが利用可能です")
except ImportError:
    OPENAI_SDK_AVAILABLE = False
    print("⚠️  OpenAI SDKが利用できません。pip install openai を実行してください")



# 営業トークスクリプトのインポート
try:
    from sales_script import SalesScript
    SALES_SCRIPT_AVAILABLE = True
    print("✅ 営業トークスクリプトが利用可能です")
except ImportError:
    SALES_SCRIPT_AVAILABLE = False
    print("⚠️  営業トークスクリプトが利用できません")

# 会話管理エンジンのインポート
try:
    from conversation_adapter import ConversationAdapter
    CONVERSATION_ENGINE_AVAILABLE = True
    print("✅ 会話管理エンジンが利用可能です")
except ImportError:
    CONVERSATION_ENGINE_AVAILABLE = False
    print("⚠️  会話管理エンジンが利用できません")

# 応答ルールエンジンのインポート/初期化
try:
    from response_engine import ResponseEngine
    RESPONSE_ENGINE_AVAILABLE = True
    response_engine = ResponseEngine()
    print("✅ 応答ルールエンジンが利用可能です")
except Exception as e:
    RESPONSE_ENGINE_AVAILABLE = False
    response_engine = None
    print(f"⚠️  応答ルールエンジン初期化エラー: {e}")

# 環境変数から設定を読み込み
from dotenv import load_dotenv
load_dotenv()

# API設定
FISH_AUDIO_API_KEY = os.getenv('FISH_AUDIO_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER')  # E.164形式
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL')  # 例: https://xxxx.ngrok.io

# 正しいFish Audio APIエンドポイント
FISH_AUDIO_BASE_URL = "https://api.fish.audio"

# すべてのTTSで使用する固定の音声ID（環境変数 DEFAULT_VOICE_ID があれば優先）
# ご指定がない場合の既定値
DEFAULT_VOICE_ID = os.getenv('DEFAULT_VOICE_ID') or '63bc41e652214372b15d9416a30a60b4'

# TTS前の発音正規化バージョン（キャッシュ無効化用）
NORMALIZATION_VERSION = "pronorm-kg1-uketama1-oumi1-renraku1-teikyo1"

def normalize_pronunciation(text: str) -> str:
    """TTS直前の発音最適化ルールを適用する。
    - "1kg" → "1キログラム"（大小写/全角ｋｇも許容）
    - "承りました" → "うけたまわりました"
    表示テキストは変更せず、TTS入力のみ正規化する目的。
    """
    if not text:
        return text
    t = text
    # 数字+kg → キログラム（例: 1kg, 2 kg, 3KG, ４ｋｇ）
    t = re.sub(r"(\d+)\s*(kg|ｋｇ|Kg|KG|kG)", r"\1キログラム", t)
    # 承りました → うけたまわりました
    t = t.replace("承りました", "うけたまわりました")
    # 近江ブレンド米 → おうみぶれんどまい
    t = t.replace("近江ブレンド米", "おうみぶれんどまい")
    # ご連絡いたしました（致しました）→ ひらがなで滑らかに
    t = t.replace("ご連絡いたしました", "ごれんらくいたしました")
    t = t.replace("ご連絡致しました", "ごれんらくいたしました")
    # ご提供しております → ひらがな化で滑らかに
    t = t.replace("ご提供しております", "ごていきょうしております")
    t = t.replace("ご提供いたしております", "ごていきょういたしております")
    t = t.replace("ご提供致しております", "ごていきょういたしております")
    return t

class FishAudioAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = FISH_AUDIO_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # 旧仕様: 毎回requestsを直接使用（シンプル版）
        self.http = None
        
        # SDKが利用可能な場合は初期化
        if FISH_AUDIO_SDK_AVAILABLE:
            try:
                self.sdk = Session(api_key)
                print("✅ Fish Audio SDKが初期化されました")
            except Exception as e:
                print(f"⚠️  SDK初期化エラー: {e}")
                self.sdk = None
        else:
            self.sdk = None
        # TTS結果の簡易LRUキャッシュ（同一テキストは即返却）
        self.tts_cache = OrderedDict()
        self.tts_cache_max = 64
        
        # OpenAI Whisper APIクライアントを初期化
        try:
            import openai
            self.whisper_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            print("✅ OpenAI Whisper APIクライアントが初期化されました")
        except Exception as e:
            print(f"⚠️  OpenAI Whisper API初期化エラー: {e}")
            self.whisper_client = None
    
    def text_to_speech(self, text, voice_id="japanese-female-1"):
        """テキストを音声に変換"""
        
        # 発音正規化を適用（TTS入力のみ）
        norm_text = normalize_pronunciation(text)

        # キャッシュ確認
        cache_key = f"{voice_id}|{norm_text}|2.0|1.0"
        cached = self.tts_cache.get(cache_key)
        if cached:
            # LRU更新
            self.tts_cache.move_to_end(cache_key)
            return cached

        # SDKが利用可能な場合はSDKを使用
        if self.sdk:
            try:
                print(f"🔍 SDKを使用したTTS呼び出し: voice_id={voice_id}")
                
                # SDKのTTSRequestを使用
                from fish_audio_sdk import TTSRequest
                
                # カスタムボイスの場合はreference_idを使用
                if voice_id.startswith('fbea') or len(voice_id) == 32:
                    # カスタムボイスモデル
                    tts_request = TTSRequest(
                        text=norm_text,
                        reference_id=voice_id,
                        rate=2.0
                    )
                else:
                    # 標準的な音声モデル
                    tts_request = TTSRequest(
                        text=norm_text,
                        voice_id=voice_id,
                        rate=2.0
                    )
                
                # SDKでTTS実行
                audio_chunks = []
                for chunk in self.sdk.tts(tts_request):
                    audio_chunks.append(chunk)
                
                if audio_chunks:
                    # 音声データを結合
                    audio_data = b''.join(audio_chunks)
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    result = {
                        "audio": audio_base64,
                        "format": "mp3"
                    }
                    # キャッシュ追加
                    self.tts_cache[cache_key] = result
                    if len(self.tts_cache) > self.tts_cache_max:
                        self.tts_cache.popitem(last=False)
                    return result
                else:
                    print("⚠️  SDKから音声データが取得できませんでした")
                    return None
                    
            except Exception as e:
                print(f"⚠️  SDK TTS エラー: {e}")
                print("直接APIを使用します")
        
        # 直接APIを使用（フォールバック）
        url = f"{self.base_url}/v1/tts"
        payload = {"text": norm_text, "voice_id": voice_id, "rate": 2.0, "pitch": 1.0}
        
        try:
            print(f"🔍 直接API TTS呼び出し: {url}")
            print(f"📤 ペイロード: {payload}")
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            print(f"📥 レスポンスステータス: {response.status_code}")
            print(f"📥 レスポンスヘッダー: {dict(response.headers)}")
            print(f"📥 レスポンス内容: {response.content[:100]}...")
            
            response.raise_for_status()
            
            # Fish Audio APIは音声データを直接返す
            if response.content:
                # 音声データをbase64エンコードして返す
                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                result = {
                    "audio": audio_base64,
                    "format": "mp3"
                }
                # キャッシュ追加
                self.tts_cache[cache_key] = result
                if len(self.tts_cache) > self.tts_cache_max:
                    self.tts_cache.popitem(last=False)
                return result
            else:
                print("⚠️  空のレスポンスが返されました")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"TTS API Error: {e}")
            return None
    
    def create_wav_header(self, data_size):
        """WAVヘッダーを作成"""
        # 44.1kHz, 16bit, モノラルのWAVヘッダー
        header = bytearray()
        
        # RIFFヘッダー
        header.extend(b'RIFF')
        header.extend((data_size + 36).to_bytes(4, 'little'))  # ファイルサイズ
        header.extend(b'WAVE')
        
        # fmtチャンク
        header.extend(b'fmt ')
        header.extend((16).to_bytes(4, 'little'))  # fmtチャンクサイズ
        header.extend((1).to_bytes(2, 'little'))   # 音声形式（PCM）
        header.extend((1).to_bytes(2, 'little'))   # チャンネル数（モノラル）
        header.extend((44100).to_bytes(4, 'little'))  # サンプリングレート
        header.extend((88200).to_bytes(4, 'little'))  # バイトレート
        header.extend((2).to_bytes(2, 'little'))   # ブロックアライメント
        header.extend((16).to_bytes(2, 'little'))  # ビット深度
        
        # データチャンク
        header.extend(b'data')
        header.extend(data_size.to_bytes(4, 'little'))
        
        return bytes(header)
    
    def speech_to_text(self, audio_data):
        """音声をテキストに変換（OpenAI Whisper API使用）"""
        
        # OpenAI Whisper APIを使用
        if self.whisper_client:
            try:
                print("🔍 OpenAI Whisper APIを使用したSTT呼び出し")
                
                # 音声データを一時ファイルに保存（複数の形式を試行）
                import tempfile
                import os
                
                # まずWebM形式で試行
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                    temp_file.write(audio_data)
                    temp_file_path = temp_file.name
                
                print(f"📁 一時ファイル作成: {temp_file_path}")
                
                try:
                    # Whisper APIで音声認識
                    with open(temp_file_path, "rb") as audio_file:
                        transcript = self.whisper_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="ja"  # 日本語を指定
                        )
                    
                    # 一時ファイルを削除
                    os.unlink(temp_file_path)
                    
                    if transcript and hasattr(transcript, 'text'):
                        recognized_text = transcript.text.strip()
                        if recognized_text:
                            print(f"✅ Whisper API STT 成功: {recognized_text}")
                            return {"text": recognized_text}
                        else:
                            print("⚠️  Whisper APIから空のテキストが返されました")
                    else:
                        print("⚠️  Whisper APIからテキストが取得できませんでした")
                        return None
                        
                except Exception as e:
                    # 一時ファイルを削除
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                    print(f"⚠️  Whisper API STT 詳細エラー: {e}")
                    
                    # WebMが失敗した場合、WAV形式で再試行
                    print("🔄 WebM形式が失敗、WAV形式で再試行...")
                    try:
                        # 音声データをWAV形式に変換（簡易的な変換）
                        wav_header = self.create_wav_header(len(audio_data))
                        wav_data = wav_header + audio_data
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                            temp_file.write(wav_data)
                            temp_file_path = temp_file.name
                        
                        print(f"📁 WAV一時ファイル作成: {temp_file_path}")
                        
                        with open(temp_file_path, "rb") as audio_file:
                            transcript = self.whisper_client.audio.transcriptions.create(
                                model="whisper-1",
                                file=audio_file,
                                language="ja"
                            )
                        
                        os.unlink(temp_file_path)
                        
                        if transcript and hasattr(transcript, 'text'):
                            recognized_text = transcript.text.strip()
                            if recognized_text:
                                print(f"✅ WAV形式で音声認識成功: {recognized_text}")
                                return {"text": recognized_text}
                    
                    except Exception as wav_error:
                        if os.path.exists(temp_file_path):
                            os.unlink(temp_file_path)
                        print(f"⚠️  WAV形式でも失敗: {wav_error}")
                    
                    raise e
                    
            except Exception as e:
                print(f"⚠️  Whisper API STT エラー: {e}")
                print("フォールバック方法を試行します")
        
        # フォールバック: 音声データの検証とエラーメッセージ
        print("🔍 音声データの検証とフォールバック処理")
        
        # 音声データのサイズをチェック
        if len(audio_data) < 1000:
            print("⚠️  音声データが小さすぎます（1KB未満）")
            return {"text": "音声データが小さすぎます。もう一度録音してください。", "error": "音声データが小さすぎます"}
        
        # 音声データの形式をチェック（WAV、WebM、MP4形式をサポート）
        print(f"🔍 音声データの詳細分析:")
        print(f"   - データサイズ: {len(audio_data)} バイト")
        print(f"   - 最初の4バイト: {audio_data[:4].hex()}")
        print(f"   - 最初の8バイト: {audio_data[:8].hex()}")
        
        is_valid_format = False
        detected_format = "不明"
        
        # WAV形式のチェック
        if len(audio_data) >= 4 and audio_data[:4] == b'RIFF':
            is_valid_format = True
            detected_format = "WAV"
            print("✅ WAV形式の音声データを検出")
        
        # WebM形式のチェック（WebMヘッダー: 1A 45 DF A3）
        elif len(audio_data) >= 4 and audio_data[:4] == b'\x1a\x45\xdf\xa3':
            is_valid_format = True
            detected_format = "WebM"
            print("✅ WebM形式の音声データを検出")
        
        # MP4形式のチェック（MP4ヘッダー: 00 00 00 20 66 74 79 70）
        elif len(audio_data) >= 8 and audio_data[4:8] == b'ftyp':
            is_valid_format = True
            detected_format = "MP4"
            print("✅ MP4形式の音声データを検出")
        
        # より柔軟なWebM検出（ChromeのWebM形式）
        elif len(audio_data) >= 4:
            # Chromeが生成するWebMの可能性をチェック
            if any(byte in audio_data[:10] for byte in [0x1a, 0x45, 0xdf, 0xa3]):
                is_valid_format = True
                detected_format = "WebM (Chrome)"
                print("✅ Chrome WebM形式の音声データを検出")
            # その他の一般的な音声形式
            elif any(byte in audio_data[:10] for byte in [0x00, 0x01, 0x02, 0x03]):
                is_valid_format = True
                detected_format = "一般的な音声形式"
                print("✅ 一般的な音声形式を検出")
        
        if not is_valid_format:
            print(f"⚠️  サポートされていない音声形式です (検出された形式: {detected_format})")
            print(f"   - 音声データの最初の16バイト: {audio_data[:16].hex()}")
            
            # 最後の手段: 音声データを強制的に受け入れて処理を試行
            print("🔄 音声形式が不明ですが、処理を試行します...")
            try:
                # 一時ファイルに保存してWhisper APIで処理を試行
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                    temp_file.write(audio_data)
                    temp_file_path = temp_file.name
                
                try:
                    # Whisper APIで音声認識を試行
                    with open(temp_file_path, "rb") as audio_file:
                        transcript = self.whisper_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="ja"
                        )
                    
                    # 一時ファイルを削除
                    os.unlink(temp_file_path)
                    
                    if transcript and hasattr(transcript, 'text'):
                        recognized_text = transcript.text.strip()
                        if recognized_text:
                            print(f"✅ 強制処理で音声認識成功: {recognized_text}")
                            return {"text": recognized_text}
                
                except Exception as e:
                    # 一時ファイルを削除
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                    print(f"⚠️  強制処理でも音声認識失敗: {e}")
                    
            except Exception as e:
                print(f"⚠️  強制処理エラー: {e}")
            
            return {"text": "音声データの形式が正しくありません。ブラウザを再読み込みしてから再度お試しください。", "error": "サポートされていない音声形式"}
        
        print("⚠️  音声認識に失敗しました。テキスト入力を使用してください。")
        return {"text": "音声認識に失敗しました。テキスト入力を使用してください。", "error": "音声認識に失敗しました"}

    def get_available_voices(self):
        """利用可能な音声モデルの一覧を取得"""
        
        # SDKが利用可能な場合はSDKを使用
        if self.sdk:
            try:
                print(f"🔍 SDKを使用した音声モデル一覧取得")
                models_response = self.sdk.list_models()
                
                # PaginatedResponseからモデルリストを取得
                if hasattr(models_response, 'items'):
                    models = list(models_response.items)
                    print(f"📊 SDKから取得された音声モデル数: {len(models)}")
                    print(f"📊 音声モデル一覧: {models}")
                    return models
                elif hasattr(models_response, '__iter__'):
                    # イテレータの場合はリストに変換
                    models = list(models_response)
                    print(f"📊 SDKから取得された音声モデル数: {len(models)}")
                    print(f"📊 音声モデル一覧: {models}")
                    return models
                else:
                    print(f"⚠️  予期しないレスポンス形式: {type(models_response)}")
                    print(f"📊 レスポンス内容: {models_response}")
                    return None
                    
            except Exception as e:
                print(f"⚠️  SDK音声モデル一覧取得エラー: {e}")
                print("直接APIを使用します")
        
        # 直接APIを使用（フォールバック）
        # 複数のエンドポイントを試行
        test_endpoints = [
            "/v1/voices",
            "/v1/models", 
            "/models",
            "/voices"
        ]
        
        for endpoint in test_endpoints:
            url = f"{self.base_url}{endpoint}"
            
            try:
                print(f"🔍 直接API音声モデル一覧取得: {url}")
                
                if self.http:
                    response = self.http.get(url, timeout=10)
                else:
                    response = requests.get(url, headers=self.headers, timeout=10)
                print(f"📥 レスポンスステータス: {response.status_code}")
                print(f"📥 レスポンスヘッダー: {dict(response.headers)}")
                
                if response.status_code == 200:
                    try:
                        voices = response.json()
                        print(f"📊 直接APIから取得された音声モデル数: {len(voices) if isinstance(voices, list) else '不明'}")
                        print(f"📊 音声モデル一覧: {voices}")
                        return voices
                    except json.JSONDecodeError:
                        print(f"⚠️  JSONデコードエラー: {response.text[:200]}...")
                        continue
                else:
                    print(f"⚠️  エンドポイント {endpoint} は {response.status_code} を返しました")
                    continue
                    
            except requests.exceptions.RequestException as e:
                print(f"エンドポイント {endpoint} エラー: {e}")
                continue
        
        print("⚠️  すべてのエンドポイントで音声モデル一覧取得に失敗しました")
        return None

class ChatGPTAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        if OPENAI_SDK_AVAILABLE:
            try:
                self.client = OpenAI(api_key=api_key)
                print("✅ ChatGPT APIクライアントが初期化されました")
            except Exception as e:
                print(f"⚠️  ChatGPT API初期化エラー: {e}")
                self.client = None
        else:
            self.client = None
        

    
    def chat(self, message, conversation_history=None, mode="normal"):
        """ChatGPTと会話"""
        if not self.client:
            return "ChatGPT APIが利用できません。"
        
        try:
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            
            # システムプロンプトを追加
            if mode == "confirm":
                # 復唱重視モード（STT直後に相手の内容を確認）
                system_content = (
                    "あなたは日本語の対話AIです。ユーザーの直前の発話内容を自然な口語で復唱して確認し、"
                    "必要に応じて不足情報を1点だけ丁寧に質問してください。"
                    "必ず1文目は復唱から始め、2文目で簡潔な質問を行います。"
                    "全体で60〜120字程度、棒読みにならない自然さで話してください。"
                )
            else:
                # 通常モード（復唱→共感→質問の流れ）
                system_content = (
                    "あなたは日本語の対話AIです。相手の発話を短く復唱して確認し、"
                    "簡潔に共感し、その後に次の質問を1つだけ丁寧に行ってください。"
                    "返答は1〜2文、合計で40〜120字程度に保ち、自然な口語で話してください。"
                    "会話の目的は、店名・住所・担当者名を正確に伺うことです。既に取得済みの情報は再度尋ねず、残りを自然に伺ってください。"
                )
            
            messages.append({
                "role": "system",
                "content": system_content
            })
            
            # ユーザーメッセージを追加
            messages.append({
                "role": "user",
                "content": message
            })
            
            # ChatGPT APIを呼び出し
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=300,
                temperature=0.6
            )
            
            # レスポンスを取得
            ai_response = response.choices[0].message.content
            
            return ai_response
            
        except Exception as e:
            print(f"ChatGPT API エラー: {e}")
            return f"エラーが発生しました: {str(e)}"
    


# Flaskアプリケーションの初期化
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Fish Audio APIインスタンス
fish_audio = FishAudioAPI(FISH_AUDIO_API_KEY)

# ChatGPT APIインスタンス
chat_gpt = ChatGPTAPI(OPENAI_API_KEY)

# 固定オープナーテキストと音声キャッシュ
OPENER_TEXT = (
    "こんにちは。\n"
    "私、X商事の高木と申します。\n\n"
    "突然のお電話失礼いたします。\n"
    "弊社では、主に弁当店様向けにお米の販売を行っておりまして、今日はその中でもおすすめの商品をご紹介させていただければと思い、ご連絡いたしました。\n\n"
    "現在ご好評いただいているのが、\n"
    "「近江ブレンド米・小粒タイプ」という商品で、\n"
    "1kgあたり588円（税別・送料込み）でご提供しております。\n\n"
    "このお米は、粒が通常より一回り小さいのが特徴で、\n"
    "弁当箱に詰めやすく、見た目のボリューム感が出しやすいと好評です。\n\n"
    "もしご興味があれば、無料サンプルをお届けさせていただいておりますので、\n"
    "よろしければ、お店のお名前・ご住所・ご担当者様のお名前をお教えいただけますでしょうか？"
)
CACHED_OPENER_AUDIO = None  # {"audio": base64, "format": "mp3"}

# 会話内で収集するスロット（担当者名・会社名・住所）
slot_state = {
    "shop_name": "",       # 会社名/店名
    "address": "",
    "contact_name": "",   # 担当者名
}

def reset_slots():
    slot_state["shop_name"] = ""
    slot_state["address"] = ""
    slot_state["contact_name"] = ""

def extract_fields_with_chatgpt(text: str):
    """ChatGPTでテキストから 店名(会社名)/住所/担当者名 を抽出して返す"""
    try:
        if not getattr(chat_gpt, 'client', None):
            return None
        prompt = (
            "次の会話テキストから、以下の3項目を可能なら抽出してください。\n"
            "- 店名(会社名)\n- 住所\n- 担当者名\n"
            "応答は必ずJSONで、キーは shop_name, address, contact_name のみ。値が不明なら空文字。\n"
            f"テキスト:\n{text}"
        )
        resp = chat_gpt.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "日本語で回答。出力は必ずJSONのみ。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        content = resp.choices[0].message.content.strip()
        try:
            parsed = json.loads(content)
        except Exception:
            start = content.find('{'); end = content.rfind('}')
            if start != -1 and end != -1 and end > start:
                parsed = json.loads(content[start:end+1])
            else:
                parsed = {"shop_name": "", "address": "", "contact_name": ""}
        return {
            "shop_name": (parsed.get('shop_name') or '').strip(),
            "address": (parsed.get('address') or '').strip(),
            "contact_name": (parsed.get('contact_name') or '').strip(),
        }
    except Exception as e:
        print(f"抽出エラー: {e}")
        return None

def build_confirm_response(user_text: str) -> dict:
    """confirmモードの応答を構築: スロット更新→不足確認→クロージング"""
    # クリーニング関数
    def strip_suffixes(text: str) -> str:
        t = (text or "").strip()
        if not t:
            return t
        # よくある語尾の除去
        t = re.sub(r"(と申します|申します|です|でございます|になります)[。\s]*$", "", t)
        # 末尾の記号・敬称の除去（会社名はこの時点では様・さんを除く）
        t = re.sub(r"[。・、,.\s]+$", "", t)
        return t

    def clean_company_name(name: str) -> str:
        n = strip_suffixes(name)
        if not n:
            return n
        # 「会社名の○○」の後段を除去
        n = re.sub(r"の[^、。\s]+$", "", n)
        # 敬称の除去
        n = re.sub(r"(様|さん)$", "", n)
        return n.strip()

    def clean_person_name(name: str) -> str:
        n = strip_suffixes(name)
        if not n:
            return n
        n = re.sub(r"(様|さん)$", "", n)
        return n.strip()

    def clean_address(addr: str) -> str:
        a = strip_suffixes(addr)
        return a
    # 0) まずは軽量な正規表現での即時抽出（ChatGPT呼び出し前に試行）
    try:
        text_norm = (user_text or "").strip()
        # 1) 「会社名の担当者です」パターンを優先
        pair = re.search(r"(?P<company>(?:株式会社|合同会社|有限会社)\s*[^、。\s]+|[^、。\s]+(?:商店|店|株式会社))の(?P<person>[^、。\s]+?)です", text_norm)
        if pair:
            comp = clean_company_name(pair.group('company'))
            pers = clean_person_name(pair.group('person'))
            if comp and not slot_state.get("shop_name"):
                slot_state["shop_name"] = comp
            if pers and not slot_state.get("contact_name"):
                slot_state["contact_name"] = pers
        # 2) 単独の担当者名「○○です」「○○と申します」
        if not slot_state.get("contact_name"):
            m = re.search(r"(?:(?:担当|ご担当)[:：]?\s*)?(?P<p>[^、。\s]+?)(?:と申します|申します|です)(?:。|$)", text_norm)
            if m:
                slot_state["contact_name"] = clean_person_name(m.group('p'))
        # 3) 会社名の抽出（語尾の切り落とし）
        if not slot_state.get("shop_name"):
            m = re.search(r"(?P<c>(?:株式会社|合同会社|有限会社)\s*[^、。\s]+|[^、。\s]+(?:商店|店|株式会社))", text_norm)
            if m:
                slot_state["shop_name"] = clean_company_name(m.group('c'))
        # 4) 住所（都道府県から始まる文字列をフルマッチで）
        if not slot_state.get("address"):
            addr = re.search(r"(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)[^、。\n]*", text_norm)
            if addr:
                slot_state["address"] = clean_address(addr.group(0))
    except Exception:
        pass
    def add_sama(name: str) -> str:
        n = (name or "").strip()
        if not n:
            return n
        return n if n.endswith("様") else f"{n}様"
    # 1) 最新発話から抽出（軽量抽出で埋まらない場合のみChatGPTを使用）
    pre_missing = [k for k in ("shop_name","address","contact_name") if not slot_state.get(k)]
    fields = {}
    if pre_missing:
        fields = extract_fields_with_chatgpt(user_text) or {}
    # 2) 既存スロットを埋める（未設定のみ上書き）
    for k in ("shop_name", "address", "contact_name"):
        val = (fields.get(k) or "").strip()
        if not val or slot_state.get(k):
            continue
        if k == "shop_name":
            slot_state[k] = clean_company_name(val)
        elif k == "contact_name":
            slot_state[k] = clean_person_name(val)
        elif k == "address":
            slot_state[k] = clean_address(val)
    # 3) 不足項目の判定（優先順）
    missing_order = ["contact_name", "shop_name", "address"]
    missing = [k for k in missing_order if not slot_state.get(k)]
    # 4) 応答生成
    if missing:
        next_key = missing[0]
        labels = {"contact_name": "ご担当者名", "shop_name": "会社名（店名）", "address": "ご住所"}
        # 簡単な復唱＋不足確認（1点だけ質問）
        known_parts = []
        if slot_state.get("shop_name"): known_parts.append(f"会社名は『{add_sama(slot_state['shop_name'])}』")
        if slot_state.get("contact_name"): known_parts.append(f"ご担当者様は『{add_sama(slot_state['contact_name'])}』")
        if slot_state.get("address"): known_parts.append(f"ご住所は『{slot_state['address']}』")
        known_summary = "、".join(known_parts) if known_parts else ""
        question = f"差し支えなければ、{labels[next_key]}を教えていただけますか？"
        reply = f"{known_summary}。{question}" if known_summary else question
        return {"text": reply, "closed": False}
    # すべて揃ったらクロージング
    closing = (
        f"ありがとうございます。ご担当者様は『{add_sama(slot_state['contact_name'])}』、会社名は『{add_sama(slot_state['shop_name'])}』、"
        f"ご住所は『{slot_state['address']}』ですね。後日、改めてお電話にてご案内いたします。よろしくお願いいたします。"
    )
    # リセットして次会話に備える
    reset_slots()
    return {"text": closing, "closed": True}

def get_or_build_opener_audio():
    global CACHED_OPENER_AUDIO
    # 静的ファイルがあれば優先
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    static_path = os.path.join(static_dir, 'opener.mp3')
    static_id_path = os.path.join(static_dir, 'opener.voice.txt')
    try:
        # モデルIDが一致する場合のみ静的ファイルを使用
        if os.path.exists(static_path) and os.path.exists(static_id_path):
            with open(static_id_path, 'r', encoding='utf-8') as vf:
                id_file = (vf.read() or '').strip().splitlines()
            saved_voice_id = id_file[0] if id_file else ''
            saved_norm_ver = id_file[1] if len(id_file) > 1 else ''
            if saved_voice_id == DEFAULT_VOICE_ID and saved_norm_ver == NORMALIZATION_VERSION:
                print("🎯 オープナー: 静的ファイルから読み込み（モデル一致）")
                with open(static_path, 'rb') as f:
                    audio_b64 = base64.b64encode(f.read()).decode('utf-8')
                return {"audio": audio_b64, "format": "mp3"}
            else:
                print(f"ℹ️  オープナー: キャッシュ不一致 → 再生成 (saved_voice={saved_voice_id}, saved_norm={saved_norm_ver}, current_voice={DEFAULT_VOICE_ID}, current_norm={NORMALIZATION_VERSION})")
    except Exception as e:
        print(f"⚠️  opener.mp3読込エラー: {e}")
    # メモリキャッシュ
    if CACHED_OPENER_AUDIO:
        print("🎯 オープナー: メモリキャッシュから返却")
        return CACHED_OPENER_AUDIO
    # 生成
    try:
        print("🛠️  オープナー: TTS生成中（初回のみ）")
        # 発音正規化も反映されるよう、ノーマライズされたテキストで生成
        opener_norm = normalize_pronunciation(OPENER_TEXT)
        tts = fish_audio.text_to_speech(opener_norm, DEFAULT_VOICE_ID)
        if tts and 'audio' in tts:
            CACHED_OPENER_AUDIO = {"audio": tts['audio'], "format": tts.get('format', 'mp3')}
            # ディスクにも保存（以後はファイルを即返却）
            try:
                os.makedirs(static_dir, exist_ok=True)
                with open(static_path, 'wb') as f:
                    f.write(base64.b64decode(tts['audio']))
                with open(static_id_path, 'w', encoding='utf-8') as vf:
                    # モデルIDと正規化バージョンを記録
                    vf.write(f"{DEFAULT_VOICE_ID}\n{NORMALIZATION_VERSION}")
                print("✅ オープナー: opener.mp3 を生成・保存しました")
            except Exception as e:
                print(f"⚠️  opener.mp3保存エラー: {e}")
            return CACHED_OPENER_AUDIO
    except Exception as e:
        print(f"⚠️  オープナーTTS生成エラー: {e}")
    return None

# 会話管理エンジンの初期化
if CONVERSATION_ENGINE_AVAILABLE:
    conversation_adapter = ConversationAdapter(chat_gpt)
    print("✅ 会話管理エンジンを初期化しました")
else:
    conversation_adapter = None
    print("⚠️  会話管理エンジンが利用できません")

# 会話履歴を管理（セッションごと）
conversation_histories = {}
# ======================
# Twilio 発信クライアント
# ======================
try:
    from twilio.rest import Client as TwilioClient
    from twilio.twiml.voice_response import VoiceResponse
    TWILIO_AVAILABLE = True
    twilio_client = None
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("✅ Twilioクライアント初期化完了")
    else:
        print("⚠️  Twilio認証情報が未設定です。環境変数を設定してください")
except Exception as e:
    TWILIO_AVAILABLE = False
    twilio_client = None
    print(f"⚠️  Twilioモジュール未利用: {e}")


# ======================
# オートダイヤラー（簡易シミュレーション）
# ======================
dialer_data = {
    "status": "idle",           # idle | running | stopping
    "queue": [],                 # 待機中の通話タスク [{phone, name}]
    "current": None,             # 現在の通話タスク
    "results": [],               # 完了結果の履歴 [{phone, name, result, started_at, ended_at}]
    "started_at": None,
    "stopped_at": None,
}

def dialer_worker():
    """簡易ダイヤラーのバックグラウンド処理（シミュレーション）"""
    while dialer_data["status"] == "running":
        if not dialer_data["queue"]:
            # キューが空なら停止
            dialer_data["status"] = "idle"
            dialer_data["current"] = None
            dialer_data["stopped_at"] = time.time()
            break

        task = dialer_data["queue"].pop(0)
        dialer_data["current"] = {
            "phone": task.get("phone"),
            "name": task.get("name"),
            "started_at": time.time()
        }
        # 発信シミュレーション（接続までの待ち）
        time.sleep(2)

        # 簡易ロジック: 末尾の数字で接続可否を決定（デモ用・決 determinism）
        phone = str(task.get("phone", ""))
        connected = phone and phone[-1].isdigit() and int(phone[-1]) % 2 == 0
        result = "connected" if connected else "no_answer"

        # 会話シミュレーション（接続時のみ）
        if result == "connected":
            # 挨拶→質問の最短フローを1往復だけ実行
            user_utterance = "こんにちは。仕入れについて相談です。"
            try:
                if conversation_adapter:
                    _ = conversation_adapter.process_conversation(user_utterance, 'intelligent')
                else:
                    _ = chat_gpt.chat(user_utterance, [], 'normal')
            except Exception:
                pass
            time.sleep(1)

        # 結果確定
        ended_at = time.time()
        dialer_data["results"].append({
            "phone": task.get("phone"),
            "name": task.get("name"),
            "result": result,
            "started_at": dialer_data["current"]["started_at"],
            "ended_at": ended_at,
        })
        dialer_data["current"] = None

        # 停止指示が出ていたら抜ける
        if dialer_data["status"] != "running":
            dialer_data["stopped_at"] = time.time()
            break

# ======================
# 管理画面/ダイヤラーAPI
# ======================
@app.route('/admin')
def admin_index():
    return render_template('admin.html')

@app.route('/admin/api/upload', methods=['POST'])
def admin_upload():
    """CSVアップロード: phone,name カラムを想定"""
    try:
        if 'file' not in request.files:
            return jsonify({"ok": False, "error": "ファイルが選択されていません"}), 400
        file = request.files['file']
        if not file.filename:
            return jsonify({"ok": False, "error": "無効なファイル名"}), 400

        content = file.read().decode('utf-8', errors='ignore')
        reader = csv.DictReader(io.StringIO(content))
        added = 0
        for row in reader:
            phone = (row.get('phone') or '').strip()
            name = (row.get('name') or '').strip()
            if not phone:
                continue
            dialer_data['queue'].append({"phone": phone, "name": name})
            added += 1
        return jsonify({"ok": True, "added": added, "queue": len(dialer_data['queue'])})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/tts', methods=['POST'])
def http_tts():
    """与えられたテキストをそのままTTSして返す最小API"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        text = (data.get('text') or '').strip()
        use_opener_cache = bool(data.get('use_opener_cache'))
        # シンプル版はrate/pitchを受け付けない
        if not text:
            return jsonify({"ok": False, "error": "textが空です"}), 400
        # 固定オープナーのときはキャッシュを優先
        if use_opener_cache and text == OPENER_TEXT:
            cached = get_or_build_opener_audio()
            if cached:
                return jsonify({"ok": True, "audio": cached['audio'], "format": cached.get('format', 'mp3'), "cached": True})
        voice_id = DEFAULT_VOICE_ID
        tts = fish_audio.text_to_speech(text, voice_id)
        if not tts or 'audio' not in tts:
            return jsonify({"ok": False, "error": "TTSに失敗しました"}), 500
        return jsonify({"ok": True, "audio": tts['audio'], "format": tts.get('format', 'mp3'), "cached": False})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/extract', methods=['POST'])
def extract_fields():
    """STTテキストから 店名/住所/担当者名 を抽出して返す。"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({"ok": False, "error": "textが空です"}), 400
        if not getattr(chat_gpt, 'client', None):
            return jsonify({"ok": False, "error": "ChatGPT未設定"}), 500
        prompt = (
            "次の会話テキストから、以下の3項目を可能なら抽出してください。\n"
            "- 店名\n- 住所\n- 担当者名\n"
            "応答は必ずJSONで、キーは shop_name, address, contact_name のみ。値が不明なら空文字。\n"
            f"テキスト:\n{text}"
        )
        resp = chat_gpt.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "日本語で回答。出力は必ずJSONのみ。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        content = resp.choices[0].message.content.strip()
        try:
            parsed = json.loads(content)
        except Exception:
            # JSON断片を単純抽出
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1 and end > start:
                parsed = json.loads(content[start:end+1])
            else:
                parsed = {"shop_name": "", "address": "", "contact_name": ""}
        return jsonify({"ok": True, "fields": {
            "shop_name": parsed.get('shop_name', ''),
            "address": parsed.get('address', ''),
            "contact_name": parsed.get('contact_name', ''),
        }})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/admin/api/start', methods=['POST'])
def admin_start():
    if dialer_data['status'] == 'running':
        return jsonify({"ok": True, "message": "既に実行中です"})
    if not dialer_data['queue']:
        return jsonify({"ok": False, "error": "キューが空です。CSVを取り込んでください。"}), 400
    dialer_data['status'] = 'running'
    dialer_data['started_at'] = time.time()
    threading.Thread(target=dialer_worker, daemon=True).start()
    return jsonify({"ok": True, "status": dialer_data['status']})

@app.route('/admin/api/stop', methods=['POST'])
def admin_stop():
    if dialer_data['status'] == 'running':
        dialer_data['status'] = 'stopping'
        return jsonify({"ok": True, "status": dialer_data['status']})
    return jsonify({"ok": True, "status": dialer_data['status']})

@app.route('/admin/api/status')
def admin_status():
    data = {
        "status": dialer_data['status'],
        "queue_length": len(dialer_data['queue']),
        "current": dialer_data['current'],
        "results": dialer_data['results'][-20:],
        "started_at": dialer_data['started_at'],
        "stopped_at": dialer_data['stopped_at'],
    }
    return jsonify({"ok": True, "data": data})

@app.route('/admin/api/clear', methods=['POST'])
def admin_clear():
    dialer_data['queue'].clear()
    dialer_data['results'].clear()
    dialer_data['current'] = None
    dialer_data['status'] = 'idle'
    return jsonify({"ok": True})

# ======================
# Twilio: 発信テスト & TwiML
# ======================
@app.route('/admin/api/twilio/test', methods=['POST'])
def twilio_test_call():
    if not TWILIO_AVAILABLE or not twilio_client:
        return jsonify({"ok": False, "error": "Twilio未設定です"}), 400
    to_number = (request.json or {}).get('to')
    if not to_number:
        return jsonify({"ok": False, "error": "宛先電話番号(to)が必要です"}), 400
    if not TWILIO_FROM_NUMBER:
        return jsonify({"ok": False, "error": "TWILIO_FROM_NUMBERが未設定です"}), 400
    if not PUBLIC_BASE_URL:
        return jsonify({"ok": False, "error": "PUBLIC_BASE_URLが未設定です(ngrokなどで公開URLを設定)"}), 400

    try:
        call = twilio_client.calls.create(
            to=to_number,
            from_=TWILIO_FROM_NUMBER,
            url=f"{PUBLIC_BASE_URL}/twilio/voice",
            status_callback=f"{PUBLIC_BASE_URL}/twilio/status",
            status_callback_event=['initiated', 'ringing', 'answered', 'completed']
        )
        return jsonify({"ok": True, "sid": call.sid})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/twilio/voice', methods=['POST'])
def twilio_voice():
    # シンプルなTTS応答（まずは固定文）
    try:
        vr = VoiceResponse()
        vr.say("お電話ありがとうございます。こちらは自動音声です。数秒後に通話を終了します。", language='ja-JP', voice='alice')
        vr.pause(length=2)
        vr.hangup()
        return Response(str(vr), mimetype='text/xml')
    except Exception as e:
        return Response(f"<Response><Say>{str(e)}</Say></Response>", mimetype='text/xml')

@app.route('/twilio/status', methods=['POST'])
def twilio_status():
    # ステータスログのみ
    try:
        data = dict(request.form)
        print("📞 Twilio Status:", data)
    except Exception as e:
        print("📞 Twilio Status parse error:", e)
    return ("", 204)

def get_sales_script_response(step):
    """営業スクリプトの応答を取得"""
    if not SALES_SCRIPT_AVAILABLE:
        return "営業トークスクリプトが利用できません。"
    
    try:
        sales_script = SalesScript()
        
        if step == "greeting":
            return sales_script.get_greeting()
        elif step == "introduction":
            return sales_script.get_introduction()
        elif step == "apology":
            return sales_script.get_apology()
        elif step == "business_intro":
            return sales_script.get_business_intro()
        elif step == "product_intro":
            return sales_script.get_product_intro()
        elif step == "features":
            return sales_script.get_features()
        elif step == "sample_offer":
            return sales_script.get_sample_offer()
        elif step == "request_info":
            return sales_script.get_request_info()
        else:
            return "指定された営業スクリプトが見つかりません。"
    except Exception as e:
        print(f"営業スクリプト取得エラー: {e}")
        return "営業スクリプトの取得中にエラーが発生しました。"



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simple')
def index_simple():
    return render_template('index_simple.html')

@app.route('/text', methods=['POST'])
def simple_text():
    """最小テキスト→応答→TTSのAPI"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        text = (data.get('text') or '').strip()
        mode = (data.get('mode') or 'normal').strip()
        # クライアント指定を無視し、固定の音声IDを使用
        voice_id = DEFAULT_VOICE_ID
        if not text:
            return jsonify({"ok": False, "error": "textが空です"}), 400

        # confirmモードは必ずChatGPTで復唱（ルール/会話エンジンをバイパス）
        if mode == 'confirm':
            # スロット収集ロジック（復唱＋不足確認 or クロージング）
            flow = build_confirm_response(text)
            ai_response = flow['text']
        else:
            # ルール→会話エンジン→ChatGPT
            ai_response = None
            if 'response_engine' in globals() and response_engine:
                rr = response_engine.respond(text)
                if rr and rr.get('response'):
                    ai_response = rr['response']
            if not ai_response and 'conversation_adapter' in globals() and conversation_adapter:
                cr = conversation_adapter.process_conversation(text, 'intelligent')
                ai_response = cr['response']
            if not ai_response:
                ai_response = chat_gpt.chat(text, [], 'normal')

        tts = fish_audio.text_to_speech(ai_response, voice_id)
        audio_b64 = tts['audio'] if tts and 'audio' in tts else None
        audio_format = tts.get('format', 'mp3') if tts else None
        return jsonify({"ok": True, "text": ai_response, "audio": audio_b64, "format": audio_format})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/stt', methods=['POST'])
def http_stt():
    """最小のSTTエンドポイント: multipartのfile もしくは JSONのbase64(audio) を受け付け"""
    try:
        audio_bytes = None
        if 'file' in request.files:
            f = request.files['file']
            audio_bytes = f.read()
        else:
            data = request.get_json(force=True, silent=True) or {}
            b64 = (data.get('audio') or '').strip()
            if b64:
                try:
                    audio_bytes = base64.b64decode(b64)
                except Exception:
                    return jsonify({"ok": False, "error": "base64デコードに失敗"}), 400
        # WebMヘッダ(1A 45 DF A3)などを確認し、サイズが小さくても処理を試行
        if not audio_bytes or len(audio_bytes) < 200:
            return jsonify({"ok": False, "error": "音声データが不足しています"}), 400
        stt = fish_audio.speech_to_text(audio_bytes)
        if stt and stt.get('text'):
            return jsonify({"ok": True, "text": stt['text']})
        err = stt.get('error') if isinstance(stt, dict) else '音声認識に失敗しました'
        return jsonify({"ok": False, "error": err}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """クライアント接続時の処理"""
    print("Client connected")
    # 新しいセッションIDを生成
    session_id = request.sid
    conversation_histories[session_id] = []
    print(f"新しいセッションが作成されました: {session_id}")

@socketio.on('disconnect')
def handle_disconnect():
    """クライアント切断時の処理"""
    print("Client disconnected")
    # セッションIDを取得して会話履歴を削除
    session_id = request.sid
    if session_id in conversation_histories:
        del conversation_histories[session_id]
        print(f"セッションが削除されました: {session_id}")

@socketio.on('audio_data')
def handle_audio_data(data):
    """クライアントから送信された音声データを処理"""
    try:
        # base64デコード
        audio_data = base64.b64decode(data['audio'])
        
        # 音声モデルを取得（デフォルトは日本語女性）
        # クライアント指定を無視し、固定の音声IDを使用
        voice_id = DEFAULT_VOICE_ID
        session_id = request.sid
        
        print("=" * 50)
        print("🎤 音声データ受信")
        print(f"🎵 受信したvoice_id: {voice_id}")
        print(f"🔍 セッションID: {session_id}")
        print(f"🎵 音声データサイズ: {len(audio_data)} バイト")
        
        # Fish Audio APIで音声認識
        stt_result = fish_audio.speech_to_text(audio_data)
        
        if stt_result and 'text' in stt_result:
            recognized_text = stt_result['text']
            print(f"📝 認識されたテキスト: {recognized_text}")
            
            # エラーメッセージの場合は、クライアントにエラーを送信
            if stt_result.get('error'):
                print(f"⚠️  音声認識エラー: {stt_result['error']}")
                emit('stt_error', {
                    'error': stt_result['error'],
                    'message': recognized_text
                })
                return
            
            # 1) 応答ルール → 2) 会話管理エンジン → 3) ChatGPT
            ai_response = None
            if RESPONSE_ENGINE_AVAILABLE:
                rule_result = response_engine.respond(recognized_text)
                if rule_result and rule_result.get('response'):
                    ai_response = rule_result['response']
                    print(f"📏 ルール応答: {rule_result.get('rule_id')} -> {ai_response}")
            if not ai_response and conversation_adapter:
                print("🤖 会話管理エンジンで会話処理中...")
                conversation_result = conversation_adapter.process_conversation(recognized_text, 'intelligent')
                ai_response = conversation_result['response']
                print(f"🤖 会話管理エンジンからの応答: {ai_response}")
            if not ai_response:
                print("🤖 ChatGPTと会話中...")
                ai_response = chat_gpt.chat(recognized_text, conversation_histories.get(session_id, []), 'normal')
                print(f"🤖 ChatGPTからの応答: {ai_response}")

            # 会話履歴を更新
            if session_id in conversation_histories:
                conversation_histories[session_id].extend([
                    {"role": "user", "content": recognized_text},
                    {"role": "assistant", "content": ai_response}
                ])
                if len(conversation_histories[session_id]) > 20:
                    conversation_histories[session_id] = conversation_histories[session_id][-20:]
            
            # 認識されたテキストをクライアントに送信
            emit('text_recognized', {'text': recognized_text})
            
            # AIの応答を音声に変換
            print(f"🎯 TTS API呼び出し開始 - 使用するvoice_id: {voice_id}")
            tts_result = fish_audio.text_to_speech(ai_response, voice_id)
            
            if tts_result and 'audio' in tts_result:
                print(f"✅ 音声合成成功 - 使用されたvoice_id: {voice_id}")
                # 音声データとテキストをクライアントに送信
                emit('audio_response', {
                    'audio': tts_result['audio'],
                    'text': ai_response,
                    'user_text': recognized_text
                })
            else:
                print(f"❌ 音声合成失敗 - 使用されたvoice_id: {voice_id}")
                emit('error', {'message': '音声合成に失敗しました'})
        else:
            print(f"❌ 音声認識失敗")
            emit('error', {'message': '音声認識に失敗しました。もう一度録音してください。'})
        
        print("=" * 50)
            
    except Exception as e:
        print(f"Error processing audio: {e}")
        emit('error', {'message': f'エラーが発生しました: {str(e)}'})



@socketio.on('realtime_tts')
def handle_realtime_tts(data):
    """リアルタイムTTS用のテキストを処理"""
    try:
        text = data['text']
        # クライアント指定を無視し、固定の音声IDを使用
        voice_id = DEFAULT_VOICE_ID
        session_id = request.sid
        
        print("=" * 30)
        print("🎵 リアルタイムTTS要求受信")
        print(f"📝 受信したテキスト: {text}")
        print(f"🎵 使用するvoice_id: {voice_id}")
        print(f"🔍 セッションID: {session_id}")
        
        # テキストを音声に変換
        print(f"🎯 リアルタイムTTS API呼び出し開始")
        tts_result = fish_audio.text_to_speech(text, voice_id)
        
        if tts_result and 'audio' in tts_result:
            print(f"✅ リアルタイムTTS成功")
            # 音声データをクライアントに送信
            emit('realtime_tts_result', {
                'audio': tts_result['audio'],
                'text': text
            })
        else:
            print(f"❌ リアルタイムTTS失敗")
            emit('error', {'message': 'リアルタイム音声合成に失敗しました'})
        
        print("=" * 30)
            
    except Exception as e:
        print(f"Error processing realtime TTS: {e}")
        emit('error', {'message': f'リアルタイム音声合成エラー: {str(e)}'})

@socketio.on('text_message')
def handle_text_message(data):
    """テキストメッセージを処理"""
    try:
        text = data['text']
        # 常に固定ボイスIDを使用
        voice_id = DEFAULT_VOICE_ID
        mode = data.get('mode', 'normal')
        session_id = request.sid
        
        print("=" * 50)
        print("📨 テキストメッセージ受信")
        print(f"📝 受信したテキスト: {text}")
        print(f"🎵 受信したvoice_id: {voice_id}")
        print(f"🎯 会話モード: {mode}")
        print(f"🔍 セッションID: {session_id}")
        
        # 営業スクリプトモードの場合は直接スクリプトを取得
        if mode == "sales" and "営業スクリプト:" in text:
            script_step = text.split(":")[1].strip()
            print(f"📋 営業スクリプト実行: {script_step}")
            ai_response = get_sales_script_response(script_step)
        else:
            # 1) 応答ルール → 2) 会話管理エンジン → 3) ChatGPT
            ai_response = None
            if RESPONSE_ENGINE_AVAILABLE:
                rule_result = response_engine.respond(text)
                if rule_result and rule_result.get('response'):
                    ai_response = rule_result['response']
                    print(f"📏 ルール応答: {rule_result.get('rule_id')} -> {ai_response}")
            if not ai_response and conversation_adapter:
                print("🤖 会話管理エンジンで会話処理中...")
                conversation_result = conversation_adapter.process_conversation(text, 'intelligent')
                ai_response = conversation_result['response']
                print(f"🤖 会話管理エンジンからの応答: {ai_response}")
            if not ai_response:
                print("🤖 ChatGPTと会話中...")
                ai_response = chat_gpt.chat(text, conversation_histories.get(session_id, []), 'normal')
                print(f"🤖 ChatGPTからの応答: {ai_response}")
        
        # 会話履歴を更新
        if session_id in conversation_histories:
            conversation_histories[session_id].extend([
                {"role": "user", "content": text},
                {"role": "assistant", "content": ai_response}
            ])
            # 履歴が長くなりすぎないように制限（最新20件）
            if len(conversation_histories[session_id]) > 20:
                conversation_histories[session_id] = conversation_histories[session_id][-20:]
        
        # AIの応答を音声に変換
        print(f"🎯 TTS API呼び出し開始 - 使用するvoice_id: {voice_id}")
        tts_result = fish_audio.text_to_speech(ai_response, voice_id)
        
        if tts_result and 'audio' in tts_result:
            print(f"✅ 音声合成成功 - 使用されたvoice_id: {voice_id}")
            # 音声データとテキストをクライアントに送信
            emit('audio_response', {
                'audio': tts_result['audio'],
                'text': ai_response,
                'user_text': text
            })
        else:
            print(f"❌ 音声合成失敗 - 使用されたvoice_id: {voice_id}")
            emit('error', {'message': '音声合成に失敗しました'})
        
        print("=" * 50)
            
    except Exception as e:
        print(f"Error processing text: {e}")
        emit('error', {'message': f'エラーが発生しました: {str(e)}'})

if __name__ == '__main__':
    if not FISH_AUDIO_API_KEY:
        print("警告: FISH_AUDIO_API_KEYが設定されていません")
        print("環境変数ファイル(.env)にAPIキーを設定してください")
    
    if not OPENAI_API_KEY:
        print("警告: OPENAI_API_KEYが設定されていません")
        print("環境変数ファイル(.env)にAPIキーを設定してください")
    
    # Fish Audio SDKの動作確認
    if FISH_AUDIO_SDK_AVAILABLE:
        print("🔍 Fish Audio SDKの動作確認中...")
        try:
            # 利用可能な音声モデル一覧を取得
            print("🔍 利用可能な音声モデル一覧を取得中...")
            available_voices = fish_audio.get_available_voices()
            
            if available_voices:
                print("✅ SDK経由で音声モデル一覧取得成功")
                print(f"📊 利用可能なモデル数: {len(available_voices)}")
            else:
                print("⚠️  SDK経由で音声モデル一覧取得失敗")
        except Exception as e:
            print(f"⚠️  SDK動作確認エラー: {e}")
    else:
        print("⚠️  Fish Audio SDKが利用できません")
    
    # ChatGPT APIの動作確認
    if OPENAI_SDK_AVAILABLE:
        print("🔍 ChatGPT APIの動作確認中...")
        try:
            # テストメッセージでChatGPTと会話
            test_message = "こんにちは、AIアシスタントです。"
            print(f"🔍 ChatGPTにテストメッセージを送信: {test_message}")
            ai_response = chat_gpt.chat(test_message)
            print(f"📝 ChatGPTからの応答: {ai_response}")
        except Exception as e:
            print(f"⚠️  ChatGPT動作確認エラー: {e}")
    else:
        print("⚠️  ChatGPT APIが利用できません")
    
    # 会話管理エンジンの動作確認
    if conversation_adapter:
        print("🔍 会話管理エンジンの動作確認中...")
        try:
            status = conversation_adapter.get_conversation_status()
            print(f"✅ 会話管理エンジン初期化成功")
            print(f"📊 初期状態: {status['conversation_manager']['state_name']}")
            print(f"📊 スロット充足率: {status['conversation_manager']['slot_completion_rate']:.1%}")
        except Exception as e:
            print(f"❌ 会話管理エンジン動作確認エラー: {e}")
    else:
        print("⚠️  会話管理エンジンが利用できません")
    
    print("=" * 50)
    print("🌐 アプリケーションが起動しました！")
    print("📱 ブラウザで http://localhost:8001 にアクセスしてください")
    print("=" * 50)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8001)
