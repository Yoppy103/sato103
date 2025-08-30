#!/usr/bin/env python3
"""
Fish Audio アプリケーションのテストスクリプト
"""

import os
import requests
import json
from dotenv import load_dotenv

def test_environment():
    """環境変数の設定をテスト"""
    print("🔍 環境変数の確認...")
    
    load_dotenv()
    api_key = os.getenv('FISH_AUDIO_API_KEY')
    
    if api_key:
        print("✅ FISH_AUDIO_API_KEY が設定されています")
        print(f"   キー: {api_key[:8]}...{api_key[-4:]}")
    else:
        print("❌ FISH_AUDIO_API_KEY が設定されていません")
        print("   .env ファイルにAPIキーを設定してください")
        return False
    
    return True

def test_dependencies():
    """必要なパッケージがインストールされているかテスト"""
    print("\n🔍 依存関係の確認...")
    
    required_packages = [
        'flask',
        'flask_socketio',
        'requests',
        'dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  不足しているパッケージ: {', '.join(missing_packages)}")
        print("   pip install -r requirements.txt を実行してください")
        return False
    
    return True

def test_flask_app():
    """Flaskアプリケーションの起動テスト"""
    print("\n🔍 Flaskアプリケーションのテスト...")
    
    try:
        from app import app
        print("✅ Flaskアプリケーションのインポート成功")
        
        # アプリケーションの設定を確認
        if app.config.get('SECRET_KEY'):
            print("✅ シークレットキーが設定されています")
        else:
            print("⚠️  シークレットキーが設定されていません")
        
        return True
        
    except Exception as e:
        print(f"❌ Flaskアプリケーションのインポート失敗: {e}")
        return False

def test_fish_audio_api():
    """Fish Audio APIの接続テスト"""
    print("\n🔍 Fish Audio API接続テスト...")
    
    try:
        from app import fish_audio
        
        if fish_audio.api_key:
            print("✅ Fish Audio APIクライアントが初期化されています")
            print(f"   ベースURL: {fish_audio.headers.get('Content-Type', 'N/A')}")
        else:
            print("❌ Fish Audio APIクライアントの初期化に失敗")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Fish Audio APIテスト失敗: {e}")
        return False

def main():
    """メインテスト関数"""
    print("🐟 Fish Audio アプリケーション テスト開始\n")
    
    tests = [
        test_environment,
        test_dependencies,
        test_flask_app,
        test_fish_audio_api
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ テスト実行中にエラーが発生: {e}")
    
    print(f"\n📊 テスト結果: {passed}/{total} 成功")
    
    if passed == total:
        print("🎉 すべてのテストが成功しました！")
        print("   アプリケーションを起動できます: python app.py")
    else:
        print("⚠️  一部のテストが失敗しました")
        print("   上記のエラーを修正してから再実行してください")

if __name__ == "__main__":
    main()
