import re
from typing import Dict, List, Optional, Tuple
from pypinyin import pinyin, Style


class PinyinConverter:
    def __init__(self):
        pass

    def convert(self, text: str, keep_punctuation: bool = False) -> str:
        if not text:
            return ""

        text = self._clean_text(text)

        pinyin_list = pinyin(text, style=Style.TONE3, heteronym=False)

        result = []
        for py in pinyin_list:
            if py and py[0]:
                p = py[0]
                p = self._normalize_pinyin(p)
                if keep_punctuation and not p.isalpha() and p != ' ':
                    result.append(p)
                elif p and p[0].isalpha():
                    result.append(p)

        return " ".join(result)

    def convert_to_initials(self, text: str) -> str:
        if not text:
            return ""

        text = self._clean_text(text)
        pinyin_list = pinyin(text, style=Style.TONE3, heteronym=False)

        initials = []
        for py in pinyin_list:
            if py and py[0]:
                p = py[0]
                p = self._normalize_pinyin(p)
                if p and p[0].isalpha():
                    initials.append(p[0].upper())

        return " ".join(initials)

    def get_pinyin_raw(self, text: str) -> str:
        if not text:
            return ""

        text = self._clean_text(text)
        pinyin_list = pinyin(text, style=Style.TONE3, heteronym=False)

        result = []
        for py in pinyin_list:
            if py and py[0]:
                result.append(self._normalize_pinyin(py[0]))

        return " ".join(result)

    def extract_first_letters(self, text: str) -> str:
        if not text:
            return ""

        pinyin_str = self.convert(text)
        words = pinyin_str.split()

        letters = []
        for word in words:
            if word and word[0].isalpha():
                letters.append(word[0].upper())

        return "".join(letters)

    def _normalize_pinyin(self, pinyin: str) -> str:
        pinyin = re.sub(r'\d', '', pinyin)

        tone_map = {
            'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a',
            'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e',
            'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i',
            'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
            'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u',
            'ǖ': 'v', 'ǘ': 'v', 'ǚ': 'v', 'ǜ': 'v',
            'ń': 'n', 'ň': 'n',
            'm̄': 'm', 'm̀': 'm',
        }

        result = []
        for char in pinyin.lower():
            if char in tone_map:
                result.append(tone_map[char])
            else:
                result.append(char)

        return ''.join(result)

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'[^\u4e00-\u9fff\sa-zA-Z0-9]', ' ', text)
        return text.strip()

    def batch_convert(self, texts: List[str]) -> List[str]:
        return [self.convert(text) for text in texts]

    def build_pinyin_index(self, terms: Dict[str, any]) -> Dict[str, Dict]:
        index = {}
        for term, info in terms.items():
            pinyin_str = self.convert(term)
            pinyin_raw = self.get_pinyin_raw(term)
            first_letters = self.extract_first_letters(term)

            index[term] = {
                "pinyin": pinyin_str,
                "pinyin_raw": pinyin_raw,
                "first_letters": first_letters,
                "original": term,
                "info": info
            }

            if "en" in info:
                en_pinyin = self.convert(info["en"])
                index[term]["en_pinyin"] = en_pinyin

        return index

    def find_similar_by_pinyin(self, query: str, term_dict: Dict[str, Dict], top_k: int = 5) -> List[Tuple[str, float, str]]:
        query_pinyin = self.convert(query)

        if not query_pinyin:
            return []

        results = []
        for term, data in term_dict.items():
            term_pinyin = data.get("pinyin", "")

            if term_pinyin == query_pinyin:
                similarity = 1.0
            else:
                similarity = self._calculate_pinyin_similarity(query_pinyin, term_pinyin)

            if similarity > 0.65:
                en_info = data.get("info", {}).get("en", "") if isinstance(data.get("info"), dict) else ""
                results.append((term, similarity, en_info))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _calculate_pinyin_similarity(self, p1: str, p2: str) -> float:
        if not p1 or not p2:
            return 0.0

        words1 = p1.split()
        words2 = p2.split()

        if not words1 or not words2:
            return 0.0

        if len(words1) == 1 and len(words2) == 1:
            return self._levenshtein_similarity(words1[0], words2[0])

        common = 0
        for w1 in words1:
            for w2 in words2:
                if w1 == w2:
                    common += 1
                    break
                elif len(w1) > 1 and len(w2) > 1:
                    char_sim = self._levenshtein_similarity(w1, w2)
                    if char_sim >= 0.8:
                        common += char_sim
                        break

        word_similarity = common / max(len(words1), len(words2))

        edit_sim = self._levenshtein_similarity(p1, p2)

        return 0.6 * word_similarity + 0.4 * edit_sim

    def _levenshtein_similarity(self, s1: str, s2: str) -> float:
        if not s1 or not s2:
            return 0.0

        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        if abs(len1 - len2) > max(len1, len2) * 0.5:
            return 0.0

        distance = self._levenshtein_distance(s1, s2)
        max_len = max(len1, len2)

        return 1.0 - (distance / max_len)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        len1, len2 = len(s1), len(s2)
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,
                    dp[i][j-1] + 1,
                    dp[i-1][j-1] + cost
                )

        return dp[len1][len2]


_default_converter: Optional[PinyinConverter] = None


def get_default_converter() -> PinyinConverter:
    global _default_converter
    if _default_converter is None:
        _default_converter = PinyinConverter()
    return _default_converter


def text_to_pinyin(text: str) -> str:
    return get_default_converter().convert(text)


def text_to_pinyin_initials(text: str) -> str:
    return get_default_converter().convert_to_initials(text)


def build_pinyin_index(terms: Dict[str, any]) -> Dict[str, Dict]:
    return get_default_converter().build_pinyin_index(terms)
