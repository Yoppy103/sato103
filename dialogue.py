import re


class DialogueManager:
    """Twilioの音声通話用: 自然会話で許可確認→スロット収集→クロージング。

    ステート:
      - permission: 許可確認中
      - collect: スロット収集中（contact_name → shop_name → address の順）

    next_turn(text) -> (reply_text, done)
    """

    def __init__(self):
        self.state = "permission"
        self.slots = {"contact_name": "", "shop_name": "", "address": ""}
        self.reask_count = 0

    @staticmethod
    def _strip_suffixes(text: str) -> str:
        t = (text or "").strip()
        t = re.sub(r"(と申します|申します|です|でございます|になります)[。\s]*$", "", t)
        t = re.sub(r"[。・、,.\s]+$", "", t)
        return t

    @staticmethod
    def _clean_company(name: str) -> str:
        n = DialogueManager._strip_suffixes(name)
        if not n:
            return n
        n = re.sub(r"の[^、。\s]+$", "", n)
        n = re.sub(r"(様|さん)$", "", n)
        return n.strip()

    @staticmethod
    def _clean_person(name: str) -> str:
        n = DialogueManager._strip_suffixes(name)
        if not n:
            return n
        n = re.sub(r"(様|さん)$", "", n)
        return n.strip()

    def _extract(self, text: str):
        t = (text or "").strip()
        # 会社名の担当者です
        pair = re.search(r"(?P<company>(?:株式会社|合同会社|有限会社)\s*[^、。\s]+|[^、。\s]+(?:商店|店|株式会社))の(?P<person>[^、。\s]+?)です", t)
        if pair:
            self.slots["shop_name"] = self.slots["shop_name"] or self._clean_company(pair.group("company"))
            self.slots["contact_name"] = self.slots["contact_name"] or self._clean_person(pair.group("person"))
        # 単独の担当者名
        if not self.slots["contact_name"]:
            m = re.search(r"(?:(?:担当|ご担当)[:：]?\s*)?(?P<p>[^、。\s]+?)(?:と申します|申します|です)(?:。|$)", t)
            if m:
                self.slots["contact_name"] = self._clean_person(m.group("p"))
        # 会社名
        if not self.slots["shop_name"]:
            m = re.search(r"(?P<c>(?:株式会社|合同会社|有限会社)\s*[^、。\s]+|[^、。\s]+(?:商店|店|株式会社))", t)
            if m:
                self.slots["shop_name"] = self._clean_company(m.group("c"))
        # 住所（都道府県から）
        if not self.slots["address"]:
            addr = re.search(r"(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)[^、。\n]*", t)
            if addr:
                self.slots["address"] = addr.group(0).strip()

    def _is_positive(self, text: str) -> bool:
        return bool(re.search(r"(はい|お願いします|大丈夫|構いません|どうぞ|いいですよ)", text or ""))

    def _is_negative(self, text: str) -> bool:
        return bool(re.search(r"(いいえ|今は|忙しい|また今度|後で|不要|結構|間に合って|嫌です|いりません)", text or ""))

    def _sama(self, name: str) -> str:
        n = (name or "").strip()
        return n if not n else (n if n.endswith("様") else f"{n}様")

    def next_turn(self, user_text: str):
        # 許可確認フェーズ
        if self.state == "permission":
            if self._is_negative(user_text):
                return ("承知いたしました。本日は失礼いたします。お時間をいただき、ありがとうございました。", True)
            if self._is_positive(user_text):
                self.state = "collect"
                return ("ありがとうございます。では、まずご担当者様のお名前をお伺いしてもよろしいでしょうか？", False)
            # よく分からない返答→再確認は1回のみ
            if self.reask_count == 0:
                self.reask_count += 1
                return ("30秒ほどで要点だけご案内いたします。今お時間よろしいでしょうか？", False)
            # 収束しない場合は丁寧に終了
            return ("また改めてご案内いたします。お時間をいただき、ありがとうございました。", True)

        # 収集フェーズ
        self._extract(user_text)
        missing_order = ["contact_name", "shop_name", "address"]
        missing = [k for k in missing_order if not self.slots[k]]

        if missing:
            next_key = missing[0]
            labels = {"contact_name": "ご担当者様のお名前", "shop_name": "会社名（店名）", "address": "ご住所"}
            known_parts = []
            if self.slots["shop_name"]:
                known_parts.append(f"会社名は『{self._sama(self.slots['shop_name'])}』")
            if self.slots["contact_name"]:
                known_parts.append(f"ご担当者様は『{self._sama(self.slots['contact_name'])}』")
            if self.slots["address"]:
                known_parts.append(f"ご住所は『{self.slots['address']}』")
            prefix = ("、".join(known_parts) + "。") if known_parts else ""
            return (f"{prefix}差し支えなければ、{labels[next_key]}を教えていただけますか？", False)

        # すべて揃ったら締め
        closing = (
            f"ありがとうございます。ご担当者様は『{self._sama(self.slots['contact_name'])}』、"
            f"会社名は『{self._sama(self.slots['shop_name'])}』、ご住所は『{self.slots['address']}』ですね。"
            "本日はありがとうございました。"
        )
        return (closing, True)



