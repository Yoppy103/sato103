#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sales_script import SalesScript
from app import ChatGPTAPI
import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def test_phone_sales_conversation():
    """電話応答対応の営業会話テスト"""
    print("🔍 電話応答対応営業トークスクリプトテスト開始")
    print("=" * 50)
    
    # 営業トークスクリプトの初期化
    script = SalesScript()
    
    # 各ステップの内容を表示
    print("📋 電話応答対応営業トークスクリプトの内容:")
    print(f"1. 挨拶: {script.get_greeting()}")
    print(f"2. 自己紹介: {script.get_introduction()}")
    print(f"3. 謝罪: {script.get_apology()}")
    print(f"4. 事業紹介: {script.get_business_intro()}")
    print(f"5. 商品紹介: {script.get_product_intro()}")
    print(f"6. 特徴: {script.get_features()}")
    print(f"7. サンプル提供: {script.get_sample_offer()}")
    print(f"8. 情報依頼: {script.get_request_info()}")
    print(f"9. 会話終了: {script.get_end_conversation()}")
    
    print("\n" + "=" * 50)
    
    # ChatGPT APIのテスト
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        print("🤖 ChatGPT API電話応答モードテスト:")
        
        # 営業モードでChatGPTをテスト
        chat_gpt = ChatGPTAPI(openai_api_key)
        
        # 電話応答のシナリオをテスト
        test_scenarios = [
            "もしもし",
            "はい",
            "興味があります",
            "詳しく教えてください",
            "価格はいくらですか？",
            "特徴を教えてください",
            "サンプルを試してみたいです",
            "情報を教えます"
        ]
        
        conversation_history = []
        
        for i, message in enumerate(test_scenarios):
            print(f"\n--- 電話応答ステップ {i+1} ---")
            print(f"📞 顧客: {message}")
            
            # 営業モードで応答を取得
            response = chat_gpt.chat(message, conversation_history, "sales")
            print(f"🤖 AI: {response}")
            
            # 会話履歴を更新
            conversation_history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": response}
            ])
            
            print(f"📊 会話履歴の長さ: {len(conversation_history)}")
            
            # 電話応答の開始条件をチェック
            if "もしもし" in message or "もし" in message:
                print("📞 電話応答開始が検出されました！")
    else:
        print("❌ OPENAI_API_KEYが設定されていません")
    
    print("\n" + "=" * 50)
    print("🎉 電話応答対応営業トークスクリプトテスト完了！")

if __name__ == "__main__":
    test_phone_sales_conversation()




