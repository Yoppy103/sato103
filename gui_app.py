#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fish Audio GUI アプリケーション
音声会話、営業スクリプト、会話管理エンジンを含むデスクトップアプリ
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import base64
import json
import time
import os
import sys
from datetime import datetime

# 既存のモジュールをインポート
try:
    from fish_audio_api import FishAudioAPI
    from chat_gpt_api import ChatGPTAPI
    from sales_script import SalesScript
    from conversation_adapter import ConversationAdapter
    print("✅ 全モジュールのインポート成功")
except ImportError as e:
    print(f"⚠️ モジュールインポートエラー: {e}")
    # フォールバック用のダミークラス
    class FishAudioAPI:
        def __init__(self): pass
        def text_to_speech(self, text, voice_id): return {"audio": "dummy"}
        def speech_to_text(self, audio_data): return {"text": "テスト音声"}
    
    class ChatGPTAPI:
        def __init__(self): pass
        def chat(self, text, history, mode): return "テスト応答"
    
    class SalesScript:
        def __init__(self): pass
        def get_greeting(self): return "こんにちは"
    
    class ConversationAdapter:
        def __init__(self, chat_gpt): pass
        def process_conversation(self, text, mode): return {"response": "テスト応答"}

class FishAudioGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Fish Audio 会話アプリ")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # 音声録音関連
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.recording_thread = None
        
        # APIクライアントの初期化
        self.init_api_clients()
        
        # GUIの構築
        self.build_gui()
        
        # 会話履歴
        self.conversation_history = []
        
        # 定期的な更新
        self.root.after(100, self.update_gui)
    
    def init_api_clients(self):
        """APIクライアントの初期化"""
        try:
            # Fish Audio API
            self.fish_audio = FishAudioAPI()
            print("✅ Fish Audio API初期化完了")
            
            # ChatGPT API
            self.chat_gpt = ChatGPTAPI()
            print("✅ ChatGPT API初期化完了")
            
            # 営業スクリプト
            self.sales_script = SalesScript()
            print("✅ 営業スクリプト初期化完了")
            
            # 会話管理エンジン
            try:
                self.conversation_adapter = ConversationAdapter(self.chat_gpt)
                print("✅ 会話管理エンジン初期化完了")
            except:
                self.conversation_adapter = None
                print("⚠️ 会話管理エンジンが利用できません")
                
        except Exception as e:
            print(f"❌ API初期化エラー: {e}")
            messagebox.showerror("エラー", f"API初期化に失敗しました: {e}")
    
    def build_gui(self):
        """GUIの構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タイトル
        title_label = ttk.Label(main_frame, text="Fish Audio 会話アプリ", 
                               font=('Helvetica', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 左側のコントロールパネル
        self.build_control_panel(main_frame)
        
        # 中央の会話エリア
        self.build_conversation_area(main_frame)
        
        # 右側の情報パネル
        self.build_info_panel(main_frame)
        
        # グリッドの重み設定
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    
    def build_control_panel(self, parent):
        """左側のコントロールパネル"""
        control_frame = ttk.LabelFrame(parent, text="コントロール", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 音声モデル選択
        ttk.Label(control_frame, text="音声モデル:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.voice_var = tk.StringVar(value="japanese-female-1")
        voice_combo = ttk.Combobox(control_frame, textvariable=self.voice_var, 
                                  values=["japanese-female-1", "japanese-male-1", "english-female-1"])
        voice_combo.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # 録音ボタン
        self.record_button = ttk.Button(control_frame, text="🎤 録音開始", 
                                       command=self.toggle_recording)
        self.record_button.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # 営業スクリプトボタン
        script_frame = ttk.LabelFrame(control_frame, text="営業スクリプト", padding="5")
        script_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        script_buttons = [
            ("挨拶", "greeting"),
            ("自己紹介", "introduction"),
            ("事業紹介", "business_intro"),
            ("商品紹介", "product_intro"),
            ("サンプル提供", "sample_offer")
        ]
        
        for i, (text, step) in enumerate(script_buttons):
            btn = ttk.Button(script_frame, text=text, 
                           command=lambda s=step: self.execute_sales_script(s))
            btn.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
        
        # 全編再生ボタン
        full_script_btn = ttk.Button(script_frame, text="🎬 全編再生", 
                                   command=self.play_full_script)
        full_script_btn.grid(row=len(script_buttons), column=0, sticky=(tk.W, tk.E), pady=5)
        
        # 会話管理エンジンの状態
        if self.conversation_adapter:
            engine_frame = ttk.LabelFrame(control_frame, text="会話管理エンジン", padding="5")
            engine_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=10)
            
            self.state_label = ttk.Label(engine_frame, text="状態: 初期化中")
            self.state_label.grid(row=0, column=0, sticky=tk.W, pady=2)
            
            self.slot_label = ttk.Label(engine_frame, text="スロット: 0%")
            self.slot_label.grid(row=1, column=0, sticky=tk.W, pady=2)
    
    def build_conversation_area(self, parent):
        """中央の会話エリア"""
        conv_frame = ttk.LabelFrame(parent, text="会話", padding="10")
        conv_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 会話履歴表示
        self.conversation_text = scrolledtext.ScrolledText(conv_frame, height=20, width=60)
        self.conversation_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # テキスト入力
        input_frame = ttk.Frame(conv_frame)
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.text_input = ttk.Entry(input_frame, width=50)
        self.text_input.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        self.text_input.bind('<Return>', self.send_text_message)
        
        send_button = ttk.Button(input_frame, text="送信", command=self.send_text_message)
        send_button.grid(row=0, column=1)
        
        input_frame.columnconfigure(0, weight=1)
        conv_frame.columnconfigure(0, weight=1)
        conv_frame.rowconfigure(0, weight=1)
    
    def build_info_panel(self, parent):
        """右側の情報パネル"""
        info_frame = ttk.LabelFrame(parent, text="情報", padding="10")
        info_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        # 録音状態
        self.recording_status = ttk.Label(info_frame, text="録音状態: 停止中")
        self.recording_status.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # 音声レベル
        self.audio_level = ttk.Label(info_frame, text="音声レベル: 0")
        self.audio_level.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # 音声レベルバー
        self.level_bar = ttk.Progressbar(info_frame, length=150, mode='determinate')
        self.level_bar.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # ログ表示
        log_frame = ttk.LabelFrame(info_frame, text="ログ", padding="5")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=30)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(3, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def log_message(self, message):
        """ログメッセージを追加"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        print(message)
    
    def add_conversation_message(self, text, sender="user"):
        """会話履歴にメッセージを追加"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[{timestamp}] {sender}: {text}\n"
        self.conversation_text.insert(tk.END, message)
        self.conversation_text.see(tk.END)
        
        # 履歴に保存
        self.conversation_history.append({
            "timestamp": timestamp,
            "sender": sender,
            "text": text
        })
    
    def toggle_recording(self):
        """録音の開始/停止"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """録音開始"""
        self.is_recording = True
        self.record_button.config(text="⏹️ 録音停止")
        self.recording_status.config(text="録音状態: 録音中")
        self.log_message("🎤 録音開始")
        
        # 録音スレッド開始
        self.recording_thread = threading.Thread(target=self.recording_worker, daemon=True)
        self.recording_thread.start()
    
    def stop_recording(self):
        """録音停止"""
        self.is_recording = False
        self.record_button.config(text="🎤 録音開始")
        self.recording_status.config(text="録音状態: 停止中")
        self.log_message("⏹️ 録音停止")
    
    def recording_worker(self):
        """録音処理ワーカー"""
        try:
            # ここで実際の音声録音処理を実装
            # 現在はシミュレーション
            for i in range(50):  # 5秒間
                if not self.is_recording:
                    break
                
                # 音声レベルをシミュレート
                level = min(100, i * 2)
                self.audio_queue.put(("level", level))
                
                time.sleep(0.1)
            
            if self.is_recording:
                # 録音完了
                self.audio_queue.put(("complete", None))
                
        except Exception as e:
            self.log_message(f"❌ 録音エラー: {e}")
            self.audio_queue.put(("error", str(e)))
    
    def execute_sales_script(self, step):
        """営業スクリプトの実行"""
        try:
            self.log_message(f"📋 営業スクリプト実行: {step}")
            
            # 営業スクリプトの内容を取得
            if step == "greeting":
                script_text = self.sales_script.get_greeting()
            elif step == "introduction":
                script_text = self.sales_script.get_introduction()
            elif step == "business_intro":
                script_text = self.sales_script.get_business_intro()
            elif step == "product_intro":
                script_text = self.sales_script.get_product_intro()
            elif step == "sample_offer":
                script_text = self.sales_script.get_sample_offer()
            else:
                script_text = "スクリプトが見つかりません"
            
            # 会話履歴に追加
            self.add_conversation_message(f"営業スクリプト: {step}", "system")
            self.add_conversation_message(script_text, "assistant")
            
            # 音声合成（非同期）
            threading.Thread(target=self.synthesize_speech, 
                           args=(script_text,), daemon=True).start()
            
        except Exception as e:
            self.log_message(f"❌ スクリプト実行エラー: {e}")
            messagebox.showerror("エラー", f"スクリプト実行に失敗しました: {e}")
    
    def play_full_script(self):
        """営業スクリプト全編再生"""
        try:
            self.log_message("🎬 営業スクリプト全編再生開始")
            self.add_conversation_message("営業スクリプト全編再生を開始します", "system")
            
            steps = ["greeting", "introduction", "business_intro", "product_intro", "sample_offer"]
            
            def play_sequence():
                for step in steps:
                    if not self.is_recording:  # 録音中は停止
                        break
                    self.execute_sales_script(step)
                    time.sleep(2)  # 2秒間隔
                
                self.add_conversation_message("営業スクリプト全編再生が完了しました", "system")
                self.log_message("🎬 営業スクリプト全編再生完了")
            
            threading.Thread(target=play_sequence, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"❌ 全編再生エラー: {e}")
            messagebox.showerror("エラー", f"全編再生に失敗しました: {e}")
    
    def send_text_message(self, event=None):
        """テキストメッセージの送信"""
        text = self.text_input.get().strip()
        if not text:
            return
        
        # 入力フィールドをクリア
        self.text_input.delete(0, tk.END)
        
        # 会話履歴に追加
        self.add_conversation_message(text, "user")
        
        # AI応答を生成（非同期）
        threading.Thread(target=self.generate_ai_response, 
                       args=(text,), daemon=True).start()
    
    def generate_ai_response(self, user_text):
        """AI応答の生成"""
        try:
            self.log_message(f"🤖 AI応答生成中: {user_text}")
            
            # 会話管理エンジンを使用
            if self.conversation_adapter:
                result = self.conversation_adapter.process_conversation(user_text, 'intelligent')
                ai_response = result['response']
                self.log_message(f"🎯 会話状態: {result.get('conversation_state', 'unknown')}")
            else:
                # フォールバック: ChatGPT
                ai_response = self.chat_gpt.chat(user_text, [], 'normal')
            
            # 会話履歴に追加
            self.add_conversation_message(ai_response, "assistant")
            
            # 音声合成（非同期）
            threading.Thread(target=self.synthesize_speech, 
                           args=(ai_response,), daemon=True).start()
            
        except Exception as e:
            self.log_message(f"❌ AI応答生成エラー: {e}")
            error_msg = f"AI応答の生成に失敗しました: {e}"
            self.add_conversation_message(error_msg, "system")
    
    def synthesize_speech(self, text):
        """音声合成"""
        try:
            self.log_message(f"🎵 音声合成開始: {text[:50]}...")
            
            # Fish Audio APIで音声合成
            voice_id = self.voice_var.get()
            result = self.fish_audio.text_to_speech(text, voice_id)
            
            if result and 'audio' in result:
                self.log_message("✅ 音声合成完了")
                # ここで音声再生処理を実装
                # 現在はログ出力のみ
            else:
                self.log_message("❌ 音声合成失敗")
                
        except Exception as e:
            self.log_message(f"❌ 音声合成エラー: {e}")
    
    def update_gui(self):
        """GUIの定期更新"""
        try:
            # 音声レベルの更新
            while not self.audio_queue.empty():
                msg_type, data = self.audio_queue.get_nowait()
                
                if msg_type == "level":
                    self.audio_level.config(text=f"音声レベル: {data}")
                    self.level_bar['value'] = data
                elif msg_type == "complete":
                    self.log_message("✅ 録音完了")
                elif msg_type == "error":
                    self.log_message(f"❌ 録音エラー: {data}")
            
            # 会話管理エンジンの状態更新
            if self.conversation_adapter:
                try:
                    status = self.conversation_adapter.get_conversation_status()
                    state_name = status['conversation_manager']['state_name']
                    slot_rate = status['conversation_manager']['slot_completion_rate']
                    
                    self.state_label.config(text=f"状態: {state_name}")
                    self.slot_label.config(text=f"スロット: {slot_rate:.1%}")
                except:
                    pass
            
        except Exception as e:
            self.log_message(f"❌ GUI更新エラー: {e}")
        
        # 100ms後に再度更新
        self.root.after(100, self.update_gui)

def main():
    """メイン関数"""
    try:
        root = tk.Tk()
        app = FishAudioGUI(root)
        
        # ウィンドウを閉じる際の処理
        def on_closing():
            if app.is_recording:
                app.stop_recording()
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # アプリケーション開始
        app.log_message("🚀 Fish Audio GUI アプリケーション起動")
        root.mainloop()
        
    except Exception as e:
        print(f"❌ アプリケーション起動エラー: {e}")
        messagebox.showerror("致命的エラー", f"アプリケーションの起動に失敗しました: {e}")

if __name__ == "__main__":
    main()


