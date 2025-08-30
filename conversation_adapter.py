import logging
from typing import Dict, Any, Optional, List
from conversation_manager import ConversationManager

class ConversationAdapter:
    """会話管理エンジンとChatGPTを統合するアダプター"""
    
    def __init__(self, chat_gpt_api):
        self.conversation_manager = ConversationManager()
        self.chat_gpt_api = chat_gpt_api
        self.logger = logging.getLogger(__name__)
        
        # 会話の文脈情報
        self.context = {
            'company_name': 'ココナラ',
            'salesperson_name': '営業担当者',
            'product_name': 'お米',
            'conversation_goal': 'アポイント獲得'
        }
    
    def create_intelligent_prompt(self, user_input: str, conversation_state: str) -> str:
        """会話の状況に応じたインテリジェントなプロンプトを作成"""
        
        # 現在の会話状態とスロット情報を取得
        state_info = self.conversation_manager.get_current_state_info()
        next_action = self.conversation_manager.determine_next_action()
        
        # 基本プロンプト
        base_prompt = f"""
あなたは{self.context['company_name']}の{self.context['salesperson_name']}です。
{self.context['product_name']}の営業活動を行っており、{self.context['conversation_goal']}を目指しています。

現在の会話状況:
- 会話状態: {state_info['state_name']} ({conversation_state})
- スロット充足率: {state_info['slot_completion_rate']:.1%}
- ユーザーの感情: {state_info['user_sentiment']}
- 次のアクション: {next_action.get('action_type', 'unknown')}

会話のルール:
1. 相手の発言に共感し、自然な流れで会話を進める
2. 棒読みは禁止。相手の状況に合わせて柔軟に対応
3. 1ターンで「共感→要約→質問」の流れを心がける
4. 必須項目（意思決定者、仕入数量、単価帯、課題、導入時期、メール）を自然に聞き出す
5. 相手が忙しそうな場合は簡潔に、興味がありそうな場合は詳しく説明

相手の発言: "{user_input}"

上記のルールに従って、自然で親しみやすい営業トークで応答してください。
"""

        # 次のアクションに応じた追加指示
        if next_action.get('action_type') == 'ask_question':
            slot_id = next_action.get('slot_id')
            slot_name = self.conversation_manager.required_slots[slot_id]['name']
            base_prompt += f"\n\n次の質問: {slot_name}について聞き出す必要があります。"
        
        elif next_action.get('action_type') == 'book_appointment':
            base_prompt += "\n\nアポイント調整の段階です。利用可能な日時を提示してください。"
        
        elif next_action.get('action_type') == 'end_conversation':
            base_prompt += "\n\n会話を終了する段階です。丁寧に締めくくってください。"
        
        return base_prompt
    
    def process_conversation(self, user_input: str, mode: str = 'intelligent') -> Dict[str, Any]:
        """会話を処理し、適切な応答を生成"""
        
        try:
            if mode == 'intelligent':
                return self._process_intelligent_conversation(user_input)
            else:
                return self._process_simple_conversation(user_input)
        
        except Exception as e:
            self.logger.error(f"会話処理エラー: {e}")
            return {
                'response': '申し訳ございません。システムエラーが発生しました。',
                'error': str(e),
                'mode': mode
            }
    
    def _process_intelligent_conversation(self, user_input: str) -> Dict[str, Any]:
        """インテリジェントな会話処理"""
        
        # 会話管理エンジンでユーザー入力を処理
        conversation_result = self.conversation_manager.process_user_input(
            user_input, 
            context=self.context
        )
        
        # 現在の状態情報を取得
        current_state = conversation_result['next_state']
        next_action = conversation_result['next_action']
        
        # 次のアクションに基づいて応答を決定
        if next_action['action_type'] == 'end_conversation':
            # 会話終了
            response = next_action['message']
            conversation_summary = self.conversation_manager.get_conversation_summary()
            
            return {
                'response': response,
                'conversation_state': current_state,
                'action_type': 'end_conversation',
                'conversation_summary': conversation_summary,
                'mode': 'intelligent'
            }
        
        elif next_action['action_type'] == 'ask_question':
            # スロット埋めの質問
            slot_id = next_action['slot_id']
            question = next_action['question']
            
            # ChatGPTで質問を自然に変換
            enhanced_question = self._enhance_question_with_context(question, slot_id)
            
            return {
                'response': enhanced_question,
                'conversation_state': current_state,
                'action_type': 'ask_question',
                'slot_id': slot_id,
                'mode': 'intelligent'
            }
        
        elif next_action['action_type'] == 'book_appointment':
            # アポイント調整
            base_message = next_action['message']
            available_slots = next_action['available_slots']
            
            appointment_message = f"{base_message}以下の日時はいかがでしょうか？\n"
            for i, slot in enumerate(available_slots, 1):
                appointment_message += f"{i}. {slot}\n"
            appointment_message += "\nご希望の日時をお教えください。"
            
            return {
                'response': appointment_message,
                'conversation_state': current_state,
                'action_type': 'book_appointment',
                'available_slots': available_slots,
                'mode': 'intelligent'
            }
        
        else:
            # 通常の会話継続
            # ChatGPTで自然な応答を生成
            prompt = self.create_intelligent_prompt(user_input, current_state)
            
            # 会話履歴を取得（最新5件）
            recent_history = self.conversation_manager.conversation_history[-5:] if self.conversation_manager.conversation_history else []
            conversation_history = [
                {"role": "user" if i % 2 == 0 else "assistant", "content": turn['user_input'] if i % 2 == 0 else "応答"}
                for i, turn in enumerate(recent_history)
            ]
            
            # ChatGPTで応答を生成
            ai_response = self.chat_gpt_api.chat(prompt, conversation_history, 'intelligent')
            
            return {
                'response': ai_response,
                'conversation_state': current_state,
                'action_type': 'continue_conversation',
                'mode': 'intelligent'
            }
    
    def _process_simple_conversation(self, user_input: str) -> Dict[str, Any]:
        """シンプルな会話処理（従来の方式）"""
        
        # 従来のChatGPT方式
        ai_response = self.chat_gpt_api.chat(user_input, [], 'normal')
        
        return {
            'response': ai_response,
            'conversation_state': 'simple',
            'action_type': 'continue_conversation',
            'mode': 'simple'
        }
    
    def _enhance_question_with_context(self, base_question: str, slot_id: str) -> str:
        """質問を文脈に合わせて自然に変換"""
        
        slot_info = self.conversation_manager.required_slots[slot_id]
        slot_name = slot_info['name']
        
        # スロットの種類に応じて質問を自然に変換
        if slot_id == 'decision_maker':
            return f"まず、{base_question}お米の仕入れについて最終的なご判断をされるのはどちらでしょうか？"
        
        elif slot_id == 'purchase_volume':
            return f"現在の状況を把握させていただきたいのですが、{base_question}月にどのくらいの量を仕入れられていますか？"
        
        elif slot_id == 'price_range':
            return f"価格についても確認させていただきたいのですが、{base_question}現在お支払いいただいている単価はどのくらいでしょうか？"
        
        elif slot_id == 'pain_points':
            return f"お客様の課題を理解させていただきたいのですが、{base_question}お米の仕入れで何かお困りの点はございますか？"
        
        elif slot_id == 'timeline':
            return f"タイミングについても確認させていただきたいのですが、{base_question}新しい仕入れ先の検討はいつ頃を予定されていますか？"
        
        elif slot_id == 'email':
            return f"最後に、{base_question}詳細資料をお送りするために、メールアドレスを教えていただけますでしょうか？"
        
        else:
            return base_question
    
    def get_conversation_status(self) -> Dict[str, Any]:
        """現在の会話状況を取得"""
        return {
            'conversation_manager': self.conversation_manager.get_current_state_info(),
            'context': self.context,
            'conversation_history_count': len(self.conversation_manager.conversation_history)
        }
    
    def reset_conversation(self):
        """会話をリセット"""
        self.conversation_manager.reset_conversation()
        self.logger.info("会話アダプターをリセットしました")
    
    def export_conversation_data(self) -> str:
        """会話データをエクスポート"""
        return self.conversation_manager.export_conversation_data()
    
    def update_context(self, new_context: Dict[str, Any]):
        """会話の文脈情報を更新"""
        self.context.update(new_context)
        self.logger.info(f"文脈情報を更新: {new_context}")
    
    def get_suggested_responses(self, user_input: str) -> List[str]:
        """ユーザーの入力に対する推奨応答を取得"""
        # 簡易的な推奨応答生成
        suggestions = []
        
        if '忙しい' in user_input or '時間がない' in user_input:
            suggestions.append("お忙しい中、お時間をいただきありがとうございます。簡潔にご説明いたします。")
            suggestions.append("お時間がないとのことですので、要点のみお伝えいたします。")
        
        elif '興味' in user_input or '詳しく' in user_input:
            suggestions.append("ご興味を持っていただきありがとうございます。詳しくご説明いたします。")
            suggestions.append("ぜひ詳しくお聞かせください。弊社の解決策をご紹介いたします。")
        
        elif '価格' in user_input or 'いくら' in user_input:
            suggestions.append("価格について詳しくご説明いたします。まず現在の状況をお聞かせください。")
            suggestions.append("価格は数量や条件によって変わります。現在の仕入量を教えていただけますか？")
        
        return suggestions


