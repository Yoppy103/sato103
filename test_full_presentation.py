#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sales_script import SalesScript

def test_full_presentation():
    """営業の目的を一気に説明するテスト"""
    print("🔍 営業の目的を一気に説明するテスト開始")
    print("=" * 50)
    
    # 営業トークスクリプトの初期化
    script = SalesScript()
    
    # 新しいステップのテスト
    print("📋 新しいステップのテスト:")
    
    print(f"\n1. 営業の目的を一気に説明:")
    full_presentation = script.get_full_presentation()
    print(f"   {full_presentation}")
    print(f"   文字数: {len(full_presentation)}")
    
    print(f"\n2. 商品詳細を説明:")
    product_details = script.get_product_details()
    print(f"   {product_details}")
    print(f"   文字数: {len(product_details)}")
    
    print(f"\n3. 価格と特徴を説明:")
    price_and_features = script.get_price_and_features()
    print(f"   {price_and_features}")
    print(f"   文字数: {len(price_and_features)}")
    
    print(f"\n4. サンプル提供と情報依頼:")
    sample_and_info = script.get_sample_and_info()
    print(f"   {sample_and_info}")
    print(f"   文字数: {len(sample_and_info)}")
    
    print("\n" + "=" * 50)
    print("🎉 新しいステップのテスト完了！")

if __name__ == "__main__":
    test_full_presentation()




