#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def test_fish_audio_endpoints():
    """Fish Audio APIの正しいエンドポイントをテスト"""
    
    # APIキーとベースURL
    api_key = os.getenv('FISH_AUDIO_API_KEY')
    base_url = "https://api.fish.audio"
    
    if not api_key:
        print("❌ FISH_AUDIO_API_KEYが設定されていません")
        return
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("🔍 Fish Audio APIのエンドポイントをテスト中...")
    print("=" * 60)
    
    # テストするSTTエンドポイント
    stt_endpoints = [
        "/v1/speech-to-text",
        "/v1/stt",
        "/v1/transcribe",
        "/v1/audio/transcribe",
        "/v1/audio/stt",
        "/v1/audio/speech-to-text",
        "/speech-to-text",
        "/stt",
        "/transcribe"
    ]
    
    # 各エンドポイントをテスト
    for endpoint in stt_endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\n🔍 テスト中: {endpoint}")
        print(f"📡 URL: {url}")
        
        try:
            # 簡単なテストリクエスト（実際の音声データなし）
            test_payload = {
                "text": "test",
                "format": "wav"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            print(f"📥 ステータス: {response.status_code}")
            print(f"📥 レスポンス: {response.text[:200]}...")
            
            if response.status_code == 200:
                print(f"✅ 成功: {endpoint}")
                break
            elif response.status_code == 404:
                print(f"❌ 404 Not Found: {endpoint}")
            elif response.status_code == 405:
                print(f"⚠️  405 Method Not Allowed: {endpoint} (POSTメソッドが必要)")
            else:
                print(f"⚠️  予期しないステータス: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ エラー: {e}")
    
    print("\n" + "=" * 60)
    
    # TTSエンドポイントもテスト
    print("\n🔍 TTSエンドポイントもテスト中...")
    tts_endpoints = [
        "/v1/tts",
        "/v1/text-to-speech",
        "/v1/audio/tts",
        "/tts",
        "/text-to-speech"
    ]
    
    for endpoint in tts_endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\n🔍 テスト中: {endpoint}")
        print(f"📡 URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"📥 ステータス: {response.status_code}")
            print(f"📥 レスポンス: {response.text[:200]}...")
            
            if response.status_code == 200:
                print(f"✅ 成功: {endpoint}")
            elif response.status_code == 404:
                print(f"❌ 404 Not Found: {endpoint}")
            elif response.status_code == 405:
                print(f"⚠️  405 Method Not Allowed: {endpoint} (POSTメソッドが必要)")
            else:
                print(f"⚠️  予期しないステータス: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ エラー: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 エンドポイントテスト完了！")

if __name__ == "__main__":
    test_fish_audio_endpoints()



