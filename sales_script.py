#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class SalesScript:
    """営業トークスクリプト管理クラス"""
    
    def __init__(self):
        self.script_data = {
            "company": "X商事",
            "salesperson": "高木",
            "product": "近江ブレンド米・小粒タイプ",
            "price": "1kgあたり588円（税別・送料込み）",
            "features": [
                "粒が通常より一回り小さい",
                "弁当箱に詰めやすい",
                "見た目のボリューム感が出しやすい"
            ],
            "target": "弁当店様向け",
            "offer": "無料サンプル",
            "required_info": [
                "お店のお名前",
                "ご住所", 
                "ご担当者様のお名前"
            ]
        }
        
        self.conversation_flow = [
            "greeting",           # 挨拶
            "introduction",       # 自己紹介
            "apology",           # 突然の連絡への謝罪
            "business_intro",    # 事業紹介
            "product_intro",     # 商品紹介
            "features",          # 特徴説明
            "price_info",        # 価格情報
            "sample_offer",      # サンプル提供
            "request_info"       # 情報依頼
        ]
    
    def get_greeting(self):
        """挨拶部分"""
        return "こんにちは。"
    
    def get_introduction(self):
        """自己紹介部分"""
        return f"私、{self.script_data['company']}の{self.script_data['salesperson']}と申します。"
    
    def get_apology(self):
        """謝罪部分"""
        return "突然のお電話失礼いたします。"
    
    def get_business_intro(self):
        """事業紹介部分"""
        return f"弊社では、主に弁当店様向けにお米の販売を行っておりまして、今日はその中でもおすすめの商品をご紹介させていただければと思い、ご連絡いたしました。"
    
    def get_product_intro(self):
        """商品紹介部分"""
        return f"現在ご好評いただいているのが、「{self.script_data['product']}」という商品で、{self.script_data['price']}でご提供しております。"
    
    def get_features(self):
        """特徴説明部分"""
        features_text = "このお米は、粒が通常より一回り小さいのが特徴で、弁当箱に詰めやすく、見た目のボリューム感が出しやすいと好評です。"
        return features_text
    
    def get_sample_offer(self):
        """サンプル提供部分"""
        return f"もしご興味があれば、{self.script_data['offer']}をお届けさせていただいておりますので、よろしければ、お店のお名前・ご住所・ご担当者様のお名前をお教えいただけますでしょうか？"
    
    def get_request_info(self):
        """情報依頼部分"""
        return "よろしければ、お店のお名前・ご住所・ご担当者様のお名前をお教えいただけますでしょうか？"
    
    def get_end_conversation(self):
        """会話終了部分"""
        return "ありがとうございました。ご検討いただき、ありがとうございます。"
    
    def get_full_presentation(self):
        """営業の目的を一気に説明"""
        return f"{self.get_business_intro()} {self.get_product_intro()} {self.get_features()} {self.get_sample_offer()}"
    
    def get_product_details(self):
        """商品詳細を説明"""
        return f"{self.get_product_intro()} {self.get_features()}"
    
    def get_price_and_features(self):
        """価格と特徴を説明"""
        return f"{self.get_product_intro()} {self.get_features()}"
    
    def get_sample_and_info(self):
        """サンプル提供と情報依頼"""
        return f"{self.get_sample_offer()} {self.get_request_info()}"
    
    def get_full_script(self):
        """完全なトークスクリプトを取得"""
        return {
            "greeting": self.get_greeting(),
            "introduction": self.get_introduction(),
            "apology": self.get_apology(),
            "business_intro": self.get_business_intro(),
            "product_intro": self.get_product_intro(),
            "features": self.get_features(),
            "sample_offer": self.get_sample_offer(),
            "request_info": self.get_request_info()
        }
    
    def get_next_step(self, current_step, customer_response):
        """顧客の反応に基づいて次のステップを決定"""
        print(f"🔍 ステップ決定: current_step={current_step}, customer_response={customer_response}")
        
        # 顧客の反応に基づくステップ決定
        if "興味" in customer_response or "詳しく" in customer_response:
            return "product_intro"
        elif "価格" in customer_response or "いくら" in customer_response:
            return "price_info"
        elif "特徴" in customer_response or "どういう" in customer_response:
            return "features"
        elif "サンプル" in customer_response or "試してみたい" in customer_response:
            return "sample_offer"
        elif "情報" in customer_response or "教える" in customer_response:
            return "request_info"
        elif "はい" in customer_response or "ええ" in customer_response or "うん" in customer_response:
            # 肯定的な反応の場合は次のステップに進む
            if current_step == "greeting":
                return "introduction"
            elif current_step == "introduction":
                return "apology"
            elif current_step == "apology":
                return "business_intro"
            elif current_step == "business_intro":
                return "product_intro"
            elif current_step == "product_intro":
                return "features"
            elif current_step == "features":
                return "sample_offer"
            elif current_step == "sample_offer":
                return "request_info"
            else:
                return "business_intro"
        elif "いいえ" in customer_response or "結構" in customer_response or "不要" in customer_response:
            # 否定的な反応の場合は終了
            return "end_conversation"
        else:
            # デフォルトは次の論理的なステップに進む
            if current_step == "greeting":
                return "introduction"
            elif current_step == "introduction":
                return "apology"
            elif current_step == "apology":
                return "business_intro"
            elif current_step == "business_intro":
                return "product_intro"
            elif current_step == "product_intro":
                return "features"
            elif current_step == "features":
                return "sample_offer"
            elif current_step == "sample_offer":
                return "request_info"
            else:
                return "business_intro"

# 使用例
if __name__ == "__main__":
    script = SalesScript()
    full_script = script.get_full_script()
    
    print("📋 営業トークスクリプト")
    print("=" * 50)
    for key, value in full_script.items():
        print(f"{key}: {value}")
    print("=" * 50)
