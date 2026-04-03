import json
from typing import Dict, List, Optional, Any
from app.rag.pinyin_converter import PinyinConverter


ALGORITHM_TERMS = {
    "分治": {"en": "Divide and Conquer", "category": "算法设计", "tags": ["基础", "递归"]},
    "分治法": {"en": "Divide and Conquer Method", "category": "算法设计", "tags": ["基础", "递归"]},
    "动态规划": {"en": "Dynamic Programming", "category": "算法设计", "tags": ["基础", "优化"]},
    "贪心算法": {"en": "Greedy Algorithm", "category": "算法设计", "tags": ["基础", "优化"]},
    "回溯算法": {"en": "Backtracking", "category": "算法设计", "tags": ["搜索", "枚举"]},
    "递归": {"en": "Recursion", "category": "基础概念", "tags": ["基础", "函数"]},
    "迭代": {"en": "Iteration", "category": "基础概念", "tags": ["基础", "循环"]},

    "快速排序": {"en": "Quick Sort", "category": "排序算法", "tags": ["排序", "分治"]},
    "归并排序": {"en": "Merge Sort", "category": "排序算法", "tags": ["排序", "分治"]},
    "堆排序": {"en": "Heap Sort", "category": "排序算法", "tags": ["排序", "堆"]},
    "插入排序": {"en": "Insertion Sort", "category": "排序算法", "tags": ["排序", "基础"]},
    "冒泡排序": {"en": "Bubble Sort", "category": "排序算法", "tags": ["排序", "基础"]},
    "选择排序": {"en": "Selection Sort", "category": "排序算法", "tags": ["排序", "基础"]},

    "二分查找": {"en": "Binary Search", "category": "查找算法", "tags": ["查找", "分治"]},
    "哈希查找": {"en": "Hash Search", "category": "查找算法", "tags": ["查找"]},

    "深度优先搜索": {"en": "DFS", "category": "图算法", "tags": ["搜索", "图"]},
    "广度优先搜索": {"en": "BFS", "category": "图算法", "tags": ["搜索", "图"]},
    "Dijkstra算法": {"en": "Dijkstra Algorithm", "category": "图算法", "tags": ["最短路径"]},
    "Bellman-Ford算法": {"en": "Bellman-Ford Algorithm", "category": "图算法", "tags": ["最短路径"]},
    "Floyd算法": {"en": "Floyd-Warshall Algorithm", "category": "图算法", "tags": ["最短路径"]},
    "Prim算法": {"en": "Prim Algorithm", "category": "图算法", "tags": ["最小生成树"]},
    "Kruskal算法": {"en": "Kruskal Algorithm", "category": "图算法", "tags": ["最小生成树"]},

    "二叉树": {"en": "Binary Tree", "category": "数据结构", "tags": ["树", "基础"]},
    "完全二叉树": {"en": "Complete Binary Tree", "category": "数据结构", "tags": ["树"]},
    "满二叉树": {"en": "Full Binary Tree", "category": "数据结构", "tags": ["树"]},
    "平衡二叉树": {"en": "Balanced Binary Tree", "category": "数据结构", "tags": ["树", "平衡"]},
    "二叉搜索树": {"en": "BST", "category": "数据结构", "tags": ["树", "搜索"]},
    "堆": {"en": "Heap", "category": "数据结构", "tags": ["树", "优先级队列"]},
    "优先队列": {"en": "Priority Queue", "category": "数据结构", "tags": ["队列", "堆"]},
    "栈": {"en": "Stack", "category": "数据结构", "tags": ["基础", "LIFO"]},
    "队列": {"en": "Queue", "category": "数据结构", "tags": ["基础", "FIFO"]},
    "链表": {"en": "Linked List", "category": "数据结构", "tags": ["基础", "线性"]},
    "数组": {"en": "Array", "category": "数据结构", "tags": ["基础", "线性"]},
    "字符串": {"en": "String", "category": "数据结构", "tags": ["基础"]},
    "哈希表": {"en": "Hash Table", "category": "数据结构", "tags": ["查找"]},
    "图": {"en": "Graph", "category": "数据结构", "tags": ["非线性"]},

    "红黑树": {"en": "Red-Black Tree", "category": "高级数据结构", "tags": ["树", "平衡"]},
    "B树": {"en": "B-Tree", "category": "高级数据结构", "tags": ["树"]},
    "B+树": {"en": "B+ Tree", "category": "高级数据结构", "tags": ["树"]},
    "线段树": {"en": "Segment Tree", "category": "高级数据结构", "tags": ["树", "区间"]},
    "树状数组": {"en": "Fenwick Tree", "category": "高级数据结构", "tags": ["树", "前缀和"]},
    "并查集": {"en": "Union-Find", "category": "高级数据结构", "tags": ["集合"]},
    "字典树": {"en": "Trie", "category": "高级数据结构", "tags": ["树", "字符串"]},

    "时间复杂度": {"en": "Time Complexity", "category": "算法分析", "tags": ["复杂度"]},
    "空间复杂度": {"en": "Space Complexity", "category": "算法分析", "tags": ["复杂度"]},
    "最优子结构": {"en": "Optimal Substructure", "category": "算法分析", "tags": ["动态规划"]},
    "重叠子问题": {"en": "Overlapping Subproblems", "category": "算法分析", "tags": ["动态规划"]},

    "位运算": {"en": "Bit Manipulation", "category": "技巧", "tags": ["优化"]},
    "分治法": {"en": "Divide and Conquer", "category": "算法设计", "tags": ["基础"]},
    "双指针": {"en": "Two Pointers", "category": "技巧", "tags": ["优化"]},
    "滑动窗口": {"en": "Sliding Window", "category": "技巧", "tags": ["优化"]},
    "单调栈": {"en": "Monotonic Stack", "category": "技巧", "tags": ["栈"]},
    "前缀和": {"en": "Prefix Sum", "category": "技巧", "tags": ["优化"]},
    "差分数组": {"en": "Difference Array", "category": "技巧", "tags": ["优化"]},
    "逆序对": {"en": "Inversion Pair", "category": "概念", "tags": ["排序"]},

    "欧拉回路": {"en": "Euler Circuit", "category": "图论", "tags": ["回路"]},
    "哈密顿回路": {"en": "Hamiltonian Circuit", "category": "图论", "tags": ["回路"]},
    "拓扑排序": {"en": "Topological Sort", "category": "图论", "tags": ["排序"]},
    "关键路径": {"en": "Critical Path", "category": "图论", "tags": ["项目管理"]},
    "网络流": {"en": "Network Flow", "category": "图论", "tags": ["流量"]},
    "最大流": {"en": "Maximum Flow", "category": "图论", "tags": ["流量"]},
    "最小割": {"en": "Minimum Cut", "category": "图论", "tags": ["流量"]},
    "二分图匹配": {"en": "Bipartite Matching", "category": "图论", "tags": ["匹配"]},

    "穷举法": {"en": "Brute Force", "category": "算法设计", "tags": ["暴力"]},
    "暴力搜索": {"en": "Brute Force Search", "category": "算法设计", "tags": ["暴力", "搜索"]},
    "减治法": {"en": "Reduce and Conquer", "category": "算法设计", "tags": ["基础"]},
    "变治法": {"en": "Transform and Conquer", "category": "算法设计", "tags": ["基础"]},
    "时空权衡": {"en": "Space-Time Tradeoff", "category": "算法设计", "tags": ["优化"]},

    "近似算法": {"en": "Approximation Algorithm", "category": "算法类型", "tags": ["优化"]},
    "随机算法": {"en": "Randomized Algorithm", "category": "算法类型", "tags": ["概率"]},
    "分布式算法": {"en": "Distributed Algorithm", "category": "算法类型", "tags": ["并行"]},
    "并行算法": {"en": "Parallel Algorithm", "category": "算法类型", "tags": ["并行"]},

    "NP完全问题": {"en": "NP-Complete", "category": "计算复杂性", "tags": ["理论"]},
    "P类问题": {"en": "P Problem", "category": "计算复杂性", "tags": ["理论"]},
    "NP类问题": {"en": "NP Problem", "category": "计算复杂性", "tags": ["理论"]},
    "NPC": {"en": "NP-Complete", "category": "计算复杂性", "tags": ["理论"]},
    "NPH": {"en": "NP-Hard", "category": "计算复杂性", "tags": ["理论"]},
}


ASR_ERROR_MAPPING = {
    "分制": "分治",
    "分制法": "分治法",
    "动态鬼话": "动态规划",
    "贪心": "贪心算法",
    "深度优化搜索": "深度优先搜索",
    "广度优化搜索": "广度优先搜索",
    "二叉搜索": "二分查找",
    "堆排": "堆排序",
    "快排": "快速排序",
    "归排": "归并排序",
    "插入排": "插入排序",
    "冒泡排": "冒泡排序",
    "选择排": "选择排序",
    "递归算法": "递归",
    "递归法": "递归",
    "回溯": "回溯算法",
    "哈斯表": "哈希表",
    "哈希表": "哈希表",
    "图算法": "图",
    "树结构": "二叉树",
    "满二叉": "满二叉树",
    "完全二叉": "完全二叉树",
    "平衡二叉": "平衡二叉树",
    "红黑": "红黑树",
    "并查": "并查集",
    "字典": "字典树",
    "线段树状数组": "线段树",
    "分段树": "线段树",
    "位运算": "位运算",
    "前缀": "前缀和",
    "差分": "差分数组",
    "逆序": "逆序对",
    "欧拉": "欧拉回路",
    "哈密顿": "哈密顿回路",
    "拓扑": "拓扑排序",
    "关键": "关键路径",
    "网络": "网络流",
    "最大流": "最大流",
    "最小割": "最小割",
    "二分图": "二分图匹配",
    "二分匹配": "二分图匹配",
    "匹配": "二分图匹配",
    "穷举": "穷举法",
    "暴力": "穷举法",
    "近似": "近似算法",
    "随机": "随机算法",
    "分布式": "分布式算法",
    "并行": "并行算法",
    "NP": "NP完全问题",
    "P类": "P类问题",
    "NP类": "NP类问题",
}

MEDICAL_TERMS = {
    "心肌梗死": {"en": "Myocardial Infarction", "category": "心血管", "tags": ["疾病"]},
    "高血压": {"en": "Hypertension", "category": "心血管", "tags": ["慢病"]},
    "糖尿病": {"en": "Diabetes", "category": "内分泌", "tags": ["慢病"]},
    "阿司匹林": {"en": "Aspirin", "category": "药理", "tags": ["药物"]},
    "冠状动脉": {"en": "Coronary Artery", "category": "解剖", "tags": ["结构"]},
}

MEDICAL_ASR_MAPPING = {
    "星肌梗死": "心肌梗死",
    "高雪压": "高血压",
    "唐尿病": "糖尿病",
    "啊司匹林": "阿司匹林",
    "冠状动卖": "冠状动脉",
}

LEGAL_TERMS = {
    "知识产权": {"en": "Intellectual Property", "category": "民商法", "tags": ["财产权"]},
    "举证责任": {"en": "Burden of Proof", "category": "诉讼法", "tags": ["证据"]},
    "违约责任": {"en": "Liability for Breach", "category": "合同法", "tags": ["责任"]},
    "侵权行为": {"en": "Tort", "category": "民法", "tags": ["侵权"]},
    "合同效力": {"en": "Contract Validity", "category": "合同法", "tags": ["合同"]},
}

LEGAL_ASR_MAPPING = {
    "职责产权": "知识产权",
    "聚证责任": "举证责任",
    "违约责认": "违约责任",
    "侵权行维": "侵权行为",
    "合同笑力": "合同效力",
}

FINANCE_TERMS = {
    "资产负债表": {"en": "Balance Sheet", "category": "财务报表", "tags": ["报表"]},
    "现金流量表": {"en": "Cash Flow Statement", "category": "财务报表", "tags": ["报表"]},
    "净利润": {"en": "Net Profit", "category": "财务指标", "tags": ["盈利"]},
    "市盈率": {"en": "Price Earnings Ratio", "category": "估值", "tags": ["指标"]},
    "资本成本": {"en": "Cost of Capital", "category": "公司金融", "tags": ["估值"]},
}

FINANCE_ASR_MAPPING = {
    "资惨负债表": "资产负债表",
    "现金流量表": "现金流量表",
    "净力润": "净利润",
    "市盈绿": "市盈率",
    "资奔成本": "资本成本",
}

DOMAIN_LIBRARY_DATA: Dict[str, Dict[str, Dict[str, Any]]] = {
    "algorithm": {"terms": ALGORITHM_TERMS, "asr_mapping": ASR_ERROR_MAPPING},
    "medical": {"terms": MEDICAL_TERMS, "asr_mapping": MEDICAL_ASR_MAPPING},
    "legal": {"terms": LEGAL_TERMS, "asr_mapping": LEGAL_ASR_MAPPING},
    "finance": {"terms": FINANCE_TERMS, "asr_mapping": FINANCE_ASR_MAPPING},
}


class TermLibrary:
    def __init__(self, domain: str = "algorithm"):
        if domain not in DOMAIN_LIBRARY_DATA:
            raise ValueError(f"Unsupported domain: {domain}")
        self.domain = domain
        self.terms = DOMAIN_LIBRARY_DATA[domain]["terms"].copy()
        self.asr_mapping = DOMAIN_LIBRARY_DATA[domain]["asr_mapping"].copy()
        self.pinyin_index: Dict[str, Dict] = {}
        self._build_index()

    def _build_index(self):
        converter = PinyinConverter()
        self.pinyin_index = converter.build_pinyin_index(self.terms)

        for wrong, correct in self.asr_mapping.items():
            if correct in self.terms:
                self.pinyin_index[wrong] = self.pinyin_index[correct].copy()
                self.pinyin_index[wrong]["original"] = wrong
                self.pinyin_index[wrong]["is_asr_error"] = True
                self.pinyin_index[wrong]["correct_term"] = correct

    def get_term(self, term: str) -> Optional[Dict]:
        return self.terms.get(term)

    def get_pinyin_index(self) -> Dict[str, Dict]:
        return self.pinyin_index

    def get_asr_mapping(self) -> Dict[str, str]:
        return self.asr_mapping.copy()

    def search_by_pinyin(self, query: str, top_k: int = 5) -> List[tuple]:
        converter = PinyinConverter()
        return converter.find_similar_by_pinyin(query, self.pinyin_index, top_k=top_k)

    def find_correct_term(self, wrong_term: str) -> Optional[str]:
        if wrong_term in self.asr_mapping:
            return self.asr_mapping[wrong_term]
        return None

    def get_all_terms(self) -> List[str]:
        return list(self.terms.keys())

    def get_terms_by_category(self, category: str) -> List[str]:
        result = []
        for term, info in self.terms.items():
            if info.get("category") == category:
                result.append(term)
        return result

    def export_to_json(self) -> str:
        return json.dumps(
            {
                "domain": self.domain,
                "terms": self.terms,
                "asr_mapping": self.asr_mapping,
                "pinyin_index": {k: {kk: vv for kk, vv in v.items() if kk != "info"} for k, v in self.pinyin_index.items()},
            },
            ensure_ascii=False,
            indent=2,
        )


_default_libraries: Dict[str, TermLibrary] = {}


def get_default_library() -> TermLibrary:
    return get_term_library("algorithm")


def get_term_library(domain: str = "algorithm") -> TermLibrary:
    if domain not in _default_libraries:
        _default_libraries[domain] = TermLibrary(domain=domain)
    return _default_libraries[domain]


def search_similar_terms(query: str, top_k: int = 5) -> List[tuple]:
    return get_default_library().search_by_pinyin(query, top_k=top_k)


def find_correct_term(wrong_term: str) -> Optional[str]:
    return get_default_library().find_correct_term(wrong_term)


def export_terms() -> str:
    return get_default_library().export_to_json()


def list_supported_domains() -> List[str]:
    return sorted(DOMAIN_LIBRARY_DATA.keys())


def get_domain_library_data(domain: str) -> Dict[str, Dict[str, Any]]:
    if domain not in DOMAIN_LIBRARY_DATA:
        raise ValueError(f"Unsupported domain: {domain}")
    return {
        "terms": DOMAIN_LIBRARY_DATA[domain]["terms"].copy(),
        "asr_mapping": DOMAIN_LIBRARY_DATA[domain]["asr_mapping"].copy(),
    }
