#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def check_fish_audio_capabilities():
    """Fish Audio APIの実際の機能を確認"""
    
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
    
    print("🔍 Fish Audio APIの機能を確認中...")
    print("=" * 60)
    
    # 利用可能なエンドポイントを確認
    endpoints_to_check = [
        "/v1/models",
        "/v1/voices",
        "/v1/health",
        "/v1/status",
        "/v1/info",
        "/v1/",
        "/",
        "/health",
        "/status"
    ]
    
    print("🔍 利用可能なエンドポイントを確認中...")
    for endpoint in endpoints_to_check:
        url = f"{base_url}{endpoint}"
        print(f"\n🔍 テスト中: {endpoint}")
        print(f"📡 URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"📥 ステータス: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ 成功: {endpoint}")
                try:
                    data = response.json()
                    print(f"📊 レスポンス内容: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
                except:
                    print(f"📊 レスポンス内容: {response.text[:500]}...")
            elif response.status_code == 404:
                print(f"❌ 404 Not Found: {endpoint}")
            elif response.status_code == 405:
                print(f"⚠️  405 Method Not Allowed: {endpoint} (POSTメソッドが必要)")
            else:
                print(f"⚠️  予期しないステータス: {response.status_code}")
                print(f"📊 レスポンス内容: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ エラー: {e}")
    
    print("\n" + "=" * 60)
    
    # TTSエンドポイントの詳細確認
    print("\n🔍 TTSエンドポイントの詳細確認...")
    tts_url = f"{base_url}/v1/tts"
    
    try:
        # POSTメソッドでTTSエンドポイントをテスト
        test_payload = {
            "text": "Hello, this is a test.",
            "voice_id": "japanese-female-1"
        }
        
        print(f"📡 POSTリクエスト送信: {tts_url}")
        print(f"📤 ペイロード: {json.dumps(test_payload, indent=2)}")
        
        response = requests.post(tts_url, headers=headers, json=test_payload, timeout=10)
        print(f"📥 ステータス: {response.status_code}")
        print(f"📥 レスポンスヘッダー: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ TTSエンドポイントが正常に動作しています")
            print(f"📊 レスポンスサイズ: {len(response.content)} bytes")
        elif response.status_code == 400:
            print("⚠️  400 Bad Request: リクエストパラメータに問題があります")
            print(f"📊 エラー詳細: {response.text}")
        elif response.status_code == 401:
            print("❌ 401 Unauthorized: APIキーが無効です")
        elif response.status_code == 404:
            print("❌ 404 Not Found: TTSエンドポイントが存在しません")
        else:
            print(f"⚠️  予期しないステータス: {response.status_code}")
            print(f"📊 レスポンス内容: {response.text[:500]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ リクエストエラー: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 機能確認完了！")

if __name__ == "__main__":
    check_fish_audio_capabilities()



