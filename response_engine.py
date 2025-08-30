#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from typing import List, Dict, Any, Optional


class ResponseEngine:
    """シンプルなルールベース応答エンジン。
    - response_rules.json のルールを読み込み
    - ユーザー入力に対し、最初にマッチしたルールの response を返す
    - マッチしなければ None を返す（上位で会話エンジン/ChatGPTにフォールバック）
    """

    def __init__(self, rules_path: str = 'response_rules.json'):
        self.rules_path = rules_path
        self.rules: List[Dict[str, Any]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        try:
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
        except Exception as e:
            print(f"⚠️  応答ルール読込エラー: {e}")
            self.rules = []

    def reload(self) -> None:
        self._load_rules()

    def match_rule(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        normalized = text.strip().lower()
        for rule in self.rules:
            match = rule.get('match', {})
            any_keywords: List[str] = match.get('any_keywords', [])
            if any_keywords:
                for kw in any_keywords:
                    if kw.lower() in normalized:
                        return rule
        return None

    def respond(self, text: str) -> Optional[Dict[str, Any]]:
        rule = self.match_rule(text)
        if not rule:
            return None
        return {
            'response': rule.get('response', ''),
            'action': rule.get('action', 'continue_conversation'),
            'rule_id': rule.get('id')
        }




