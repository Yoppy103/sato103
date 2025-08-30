#!/usr/bin/env python3
# -*- coding: utf-8 -*-

try:
    from fish_audio_sdk import TTSRequest
    print("✅ Fish Audio SDKが利用可能です")
    
    # TTSRequestのパラメータを確認
    print("\n🔍 TTSRequestのパラメータ確認:")
    
    # 基本的なTTSRequestを作成
    basic_request = TTSRequest(text="テスト")
    print(f"基本的なTTSRequest: {basic_request}")
    
    # 利用可能な属性を確認
    print(f"\n📋 TTSRequestの属性:")
    for attr in dir(basic_request):
        if not attr.startswith('_'):
            try:
                value = getattr(basic_request, attr)
                print(f"  {attr}: {value}")
            except:
                print(f"  {attr}: アクセス不可")
    
    # speedパラメータのテスト
    print(f"\n🎯 speedパラメータのテスト:")
    try:
        speed_request = TTSRequest(text="テスト", speed=2.0)
        print(f"speed=2.0の設定: {speed_request}")
        print(f"speed値: {getattr(speed_request, 'speed', '属性なし')}")
    except Exception as e:
        print(f"speedパラメータエラー: {e}")
    
    # その他のパラメータもテスト
    print(f"\n🔧 その他のパラメータテスト:")
    test_params = ['pitch', 'volume', 'rate', 'tempo']
    for param in test_params:
        try:
            test_request = TTSRequest(text="テスト", **{param: 1.5})
            print(f"{param}=1.5の設定: 成功")
        except Exception as e:
            print(f"{param}=1.5の設定: 失敗 - {e}")
    
except ImportError:
    print("❌ Fish Audio SDKが利用できません")
except Exception as e:
    print(f"❌ エラー: {e}")




