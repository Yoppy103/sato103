import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

class ConversationManager:
    """営業会話を管理するエンジン"""
    
    def __init__(self):
        # 会話の状態管理
        self.conversation_states = {
            'greeting': '挨拶・自己紹介',
            'pain_point_discovery': '課題・不満点の把握',
            'solution_introduction': '解決策の提案',
            'qualification': '条件確認・ヒアリング',
            'appointment_booking': 'アポイント調整',
            'confirmation': '確認・締め',
            'completed': '完了',
            'rejected': '拒否・終了'
        }
        
        # 必須ヒアリング項目（スロット）
        self.required_slots = {
            'decision_maker': {
                'name': '意思決定者',
                'value': None,
                'required': True,
                'question': 'ご担当者様はどちらでしょうか？',
                'validation': lambda x: len(x) > 0
            },
            'purchase_volume': {
                'name': '現在の仕入数量',
                'value': None,
                'required': True,
                'question': '現在、お米はどのくらいの量を仕入れられていますか？',
                'validation': lambda x: len(x) > 0
            },
            'price_range': {
                'name': '単価帯',
                'value': None,
                'required': True,
                'question': '現在お支払いいただいている単価はどのくらいでしょうか？',
                'validation': lambda x: len(x) > 0
            },
            'pain_points': {
                'name': '現在の課題・不満点',
                'value': None,
                'required': True,
                'question': 'お米の仕入れで何かお困りの点はございますか？',
                'validation': lambda x: len(x) > 0
            },
            'timeline': {
                'name': '導入・検討時期',
                'value': None,
                'required': True,
                'question': '新しい仕入れ先の検討はいつ頃を予定されていますか？',
                'validation': lambda x: len(x) > 0
            },
            'email': {
                'name': 'メールアドレス',
                'value': None,
                'required': True,
                'question': '詳細資料をお送りするために、メールアドレスを教えていただけますか？',
                'validation': lambda x: '@' in x and '.' in x
            }
        }
        
        # 会話の現在状態
        self.current_state = 'greeting'
        self.conversation_history = []
        self.slot_filling_progress = 0
        self.user_sentiment = 'neutral'  # positive, neutral, negative
        self.conversation_quality = 0.0  # 0.0-1.0
        
        # ログ設定
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def get_current_state_info(self) -> Dict[str, Any]:
        """現在の会話状態の情報を取得"""
        return {
            'current_state': self.current_state,
            'state_name': self.conversation_states.get(self.current_state, '不明'),
            'slot_completion_rate': self.get_slot_completion_rate(),
            'next_required_slot': self.get_next_required_slot(),
            'conversation_quality': self.conversation_quality,
            'user_sentiment': self.user_sentiment
        }
    
    def get_slot_completion_rate(self) -> float:
        """必須スロットの充足率を計算（0.0-1.0）"""
        filled_slots = sum(1 for slot in self.required_slots.values() if slot['value'] is not None)
        total_slots = len(self.required_slots)
        return filled_slots / total_slots if total_slots > 0 else 0.0
    
    def get_next_required_slot(self) -> Optional[str]:
        """次に埋めるべき必須スロットを取得"""
        for slot_id, slot_info in self.required_slots.items():
            if slot_info['required'] and slot_info['value'] is None:
                return slot_id
        return None
    
    def update_slot(self, slot_id: str, value: str) -> bool:
        """スロットの値を更新"""
        if slot_id in self.required_slots:
            slot_info = self.required_slots[slot_id]
            if slot_info['validation'](value):
                slot_info['value'] = value
                self.logger.info(f"スロット更新: {slot_id} = {value}")
                return True
            else:
                self.logger.warning(f"スロット値の検証失敗: {slot_id} = {value}")
                return False
        return False
    
    def get_slot_question(self, slot_id: str) -> str:
        """指定されたスロットの質問文を取得"""
        if slot_id in self.required_slots:
            return self.required_slots[slot_id]['question']
        return "質問が見つかりません。"
    
    def process_user_input(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """ユーザーの入力を処理し、次のアクションを決定"""
        # 会話履歴に追加
        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'state': self.current_state,
            'context': context or {}
        })
        
        # 感情分析（簡易版）
        self.analyze_sentiment(user_input)
        
        # スロット情報の抽出
        self.extract_slot_information(user_input)
        
        # 次の状態を決定
        next_state = self.determine_next_state(user_input, context)
        
        # 状態を更新
        self.current_state = next_state
        
        # 次のアクションを決定
        next_action = self.determine_next_action()
        
        return {
            'next_state': next_state,
            'next_action': next_action,
            'slot_completion_rate': self.get_slot_completion_rate(),
            'missing_slots': self.get_missing_slots(),
            'conversation_quality': self.conversation_quality
        }
    
    def analyze_sentiment(self, user_input: str):
        """ユーザーの感情を分析（簡易版）"""
        positive_words = ['良い', '素晴らしい', '興味', '検討', '詳しく', 'ありがとう']
        negative_words = ['いらない', '興味ない', '忙しい', '断る', '困る', '問題']
        
        positive_count = sum(1 for word in positive_words if word in user_input)
        negative_count = sum(1 for word in negative_words if word in user_input)
        
        if positive_count > negative_count:
            self.user_sentiment = 'positive'
        elif negative_count > positive_count:
            self.user_sentiment = 'negative'
        else:
            self.user_sentiment = 'neutral'
    
    def extract_slot_information(self, user_input: str):
        """ユーザーの入力からスロット情報を抽出"""
        # メールアドレスの抽出
        if '@' in user_input and '.' in user_input:
            email_parts = user_input.split()
            for part in email_parts:
                if '@' in part and '.' in part:
                    self.update_slot('email', part.strip('.,!?;:'))
                    break
        
        # その他の情報も抽出可能（より高度なNLPが必要）
        # ここでは簡易的な実装
    
    def determine_next_state(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """次の会話状態を決定"""
        current_completion_rate = self.get_slot_completion_rate()
        
        # 拒否・終了の判定
        if self.user_sentiment == 'negative' or '断る' in user_input or '興味ない' in user_input:
            return 'rejected'
        
        # 現在の状態に基づいて次の状態を決定
        if self.current_state == 'greeting':
            if current_completion_rate < 0.3:
                return 'pain_point_discovery'
            else:
                return 'solution_introduction'
        
        elif self.current_state == 'pain_point_discovery':
            if current_completion_rate < 0.5:
                return 'qualification'
            else:
                return 'solution_introduction'
        
        elif self.current_state == 'solution_introduction':
            if current_completion_rate < 0.8:
                return 'qualification'
            else:
                return 'appointment_booking'
        
        elif self.current_state == 'qualification':
            if current_completion_rate >= 0.8:
                return 'appointment_booking'
            else:
                return 'qualification'  # まだ質問が必要
        
        elif self.current_state == 'appointment_booking':
            if current_completion_rate >= 0.9:
                return 'confirmation'
            else:
                return 'qualification'  # 不足情報がある
        
        elif self.current_state == 'confirmation':
            return 'completed'
        
        return self.current_state
    
    def determine_next_action(self) -> Dict[str, Any]:
        """次のアクションを決定"""
        next_slot = self.get_next_required_slot()
        current_completion_rate = self.get_slot_completion_rate()
        
        if self.current_state == 'rejected':
            return {
                'action_type': 'end_conversation',
                'message': 'お忙しい中、お時間をいただきありがとうございました。',
                'reason': 'user_rejected'
            }
        
        elif self.current_state == 'completed':
            return {
                'action_type': 'end_conversation',
                'message': '本日はありがとうございました。詳細資料をお送りいたします。',
                'reason': 'success'
            }
        
        elif next_slot and current_completion_rate < 0.8:
            # スロット埋めが必要
            return {
                'action_type': 'ask_question',
                'slot_id': next_slot,
                'question': self.get_slot_question(next_slot),
                'context': f"現在の充足率: {current_completion_rate:.1%}"
            }
        
        elif self.current_state == 'appointment_booking' and current_completion_rate >= 0.8:
            # アポイント調整
            return {
                'action_type': 'book_appointment',
                'message': 'アポイントの調整をさせていただきたいのですが、',
                'available_slots': self.get_available_appointment_slots()
            }
        
        else:
            # 次の会話ステップ
            return {
                'action_type': 'continue_conversation',
                'message': self.get_state_transition_message(),
                'next_state': self.current_state
            }
    
    def get_missing_slots(self) -> List[str]:
        """不足しているスロットのリストを取得"""
        return [
            slot_id for slot_id, slot_info in self.required_slots.items()
            if slot_info['required'] and slot_info['value'] is None
        ]
    
    def get_available_appointment_slots(self) -> List[str]:
        """利用可能なアポイント枠を取得（簡易版）"""
        # 実際の実装では、カレンダーAPIと連携
        return [
            "明日の午前中",
            "明日の午後",
            "明後日の午前中",
            "明後日の午後"
        ]
    
    def get_state_transition_message(self) -> str:
        """状態遷移時のメッセージを取得"""
        transition_messages = {
            'pain_point_discovery': 'まずは、現在の状況についてお聞かせください。',
            'solution_introduction': 'その課題について、弊社の解決策をご紹介させていただきます。',
            'qualification': 'より具体的なご提案をさせていただくために、いくつかお聞かせください。',
            'appointment_booking': '詳細についてお話しさせていただきたいのですが、',
            'confirmation': '最後に、お聞かせいただいた内容を確認させてください。'
        }
        return transition_messages.get(self.current_state, '')
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """会話の要約を取得"""
        return {
            'start_time': self.conversation_history[0]['timestamp'] if self.conversation_history else None,
            'end_time': datetime.now().isoformat(),
            'total_turns': len(self.conversation_history),
            'final_state': self.current_state,
            'slot_completion_rate': self.get_slot_completion_rate(),
            'filled_slots': {
                slot_id: slot_info['value']
                for slot_id, slot_info in self.required_slots.items()
                if slot_info['value'] is not None
            },
            'missing_slots': self.get_missing_slots(),
            'user_sentiment': self.user_sentiment,
            'conversation_quality': self.conversation_quality
        }
    
    def reset_conversation(self):
        """会話をリセット"""
        self.current_state = 'greeting'
        self.conversation_history = []
        self.slot_filling_progress = 0
        self.user_sentiment = 'neutral'
        self.conversation_quality = 0.0
        
        # スロットをリセット
        for slot_info in self.required_slots.values():
            slot_info['value'] = None
        
        self.logger.info("会話をリセットしました")
    
    def export_conversation_data(self) -> str:
        """会話データをJSON形式でエクスポート"""
        data = {
            'conversation_summary': self.get_conversation_summary(),
            'conversation_history': self.conversation_history,
            'required_slots': self.required_slots
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


