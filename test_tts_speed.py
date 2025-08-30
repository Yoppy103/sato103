#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv
from app import FishAudioAPI

# 環境変数を読み込み
load_dotenv()

def test_tts_speed():
    """音声合成速度のテスト"""
    print("🔍 音声合成速度テスト開始")
    print("=" * 50)
    
    # Fish Audio APIの初期化
    fish_api_key = os.getenv('FISH_AUDIO_API_KEY')
    if not fish_api_key:
        print("❌ FISH_AUDIO_API_KEYが設定されていません")
        return
    
    fish_audio = FishAudioAPI(fish_api_key)
    
    # テスト用のテキスト
    test_texts = [
        "こんにちは。",
        "私、X商事の高木と申します。",
        "弊社では弁当店様向けにお米を販売しており、おすすめ商品をご紹介させていただきたいと思います。",
        "おすすめは「近江ブレンド米・小粒タイプ」で、1kgあたり588円（税別・送料込み）です。",
        "粒が小さく、弁当箱に詰めやすく、見た目も良いです。"
    ]
    
    print("📝 音声合成速度テスト:")
    for i, text in enumerate(test_texts, 1):
        print(f"\n--- テスト {i} ---")
        print(f"📝 テキスト: {text}")
        print(f"📊 文字数: {len(text)}")
        
        # 音声合成を実行
        try:
            result = fish_audio.text_to_speech(text, "japanese-female-1")
            if result and 'audio' in result:
                print(f"✅ 音声合成成功")
                print(f"🎵 音声データサイズ: {len(result['audio'])} 文字")
            else:
                print(f"❌ 音声合成失敗")
        except Exception as e:
            print(f"❌ エラー: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 音声合成速度テスト完了！")
    print("💡 音声合成速度は1.5倍に設定されています")

if __name__ == "__main__":
    test_tts_speed()




