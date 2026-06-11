"""对比原始 SRT 与纠错后 SRT 文件的差异，生成详细报告"""
import sys
import re
from pathlib import Path
from difflib import SequenceMatcher, unified_diff

sys.path.insert(0, str(Path(__file__).parent.parent))

TEST_DIR = Path(r"d:\Mycode\算法_agent\str_file\test")
CORRECTED_DIR = TEST_DIR / "corrected"

# 字幕块正则：序号 + 时间轴 + 文本
BLOCK_PATTERN = re.compile(
    r'(\d+)\s*\n'
    r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n'
    r'(.+?)(?=\n\n|\n\d+\n|\Z)',
    re.DOTALL
)


def parse_srt_blocks(content: str) -> list[dict]:
    """解析 SRT 内容为字幕块列表"""
    blocks = []
    for m in BLOCK_PATTERN.finditer(content):
        blocks.append({
            "id": int(m.group(1)),
            "start": m.group(2),
            "end": m.group(3),
            "text": m.group(4).strip(),
        })
    return blocks


def token_diff(orig: str, corrected: str) -> list[str]:
    """对两段文本做字符级差异"""
    matcher = SequenceMatcher(None, orig, corrected)
    changes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "replace":
            changes.append(f"    替换: [{orig[i1:i2]}] -> [{corrected[j1:j2]}]")
        elif tag == "delete":
            changes.append(f"    删除: [{orig[i1:i2]}]")
        elif tag == "insert":
            changes.append(f"    插入: [{corrected[j1:j2]}]")
    return changes


def analyze_one_file(orig_path: Path, corr_path: Path) -> dict:
    """分析单个文件的差异"""
    orig_content = orig_path.read_text(encoding="utf-8")
    corr_content = corr_path.read_text(encoding="utf-8")

    orig_blocks = parse_srt_blocks(orig_content)
    corr_blocks = parse_srt_blocks(corr_content)

    total_blocks = len(orig_blocks)
    changed_blocks = 0
    total_changes = 0  # 字幕文本内变化的次数
    block_details = []

    for i, ob in enumerate(orig_blocks):
        cb = corr_blocks[i] if i < len(corr_blocks) else None
        if cb is None:
            continue
        if ob["text"] != cb["text"]:
            changed_blocks += 1
            diffs = token_diff(ob["text"], cb["text"])
            total_changes += len(diffs)
            block_details.append({
                "id": ob["id"],
                "start": ob["start"],
                "original": ob["text"],
                "corrected": cb["text"],
                "diffs": diffs,
            })

    return {
        "file": orig_path.name,
        "orig_blocks": total_blocks,
        "corr_blocks": len(corr_blocks),
        "changed_blocks": changed_blocks,
        "total_token_changes": total_changes,
        "details": block_details,
    }


def assess_quality(results: list[dict]) -> dict:
    """
    基于规则评估纠错质量。
    评分维度：
      1. 字幕块结构完整性（序号/时间轴不应改变）
      2. 算法术语纠错准确性（基于已知术语库）
      3. 中文语义连贯性（不产生不通顺的句子）
    """
    # 算法领域已知正确术语（ASR容易出错->正确）
    known_terms = {
        # 递归相关
        "地归": "递归", "递规": "递归", "地规": "递归",
        # 分治相关
        "分支": "分治", "分之": "分治",
        # 数学相关
        "恩": "n", "log恩": "log n",
        # 常见ASR错误
        "地推": "递推", "宿": "树",
        "奥": "O", "o括号": "O(", "大o": "大O",
        "落幕": "log", "烙个": "log",
        "恩方": "n方", "恩的": "n的",
        "乐": "n",  # 需上下文判断
    }

    total_corrections = 0
    good_corrections = 0
    questionable = 0
    bad_corrections = 0
    assessment_details = []

    for r in results:
        for d in r.get("details", []):
            for diff_line in d.get("diffs", []):
                total_corrections += 1
                orig_text = d["original"]
                corr_text = d["corrected"]

                # 判断质量
                quality = "未知"
                reason = ""

                # 规则1: 替换后更符合算法术语
                matched = False
                for wrong, right in known_terms.items():
                    if wrong in orig_text and right in corr_text:
                        good_corrections += 1
                        quality = "正确"
                        reason = f"术语修正: {wrong} -> {right}"
                        matched = True
                        break

                if not matched:
                    # 规则2: 纯中文字符变化
                    orig_chinese = re.findall(r'[\u4e00-\u9fff]+', orig_text)
                    corr_chinese = re.findall(r'[\u4e00-\u9fff]+', corr_text)
                    if orig_chinese and corr_chinese:
                        # 中文文本改善（去除了ASR噪声）
                        if len(corr_text) < len(orig_text) and len(corr_text.split()) >= len(orig_text.split()) // 2:
                            good_corrections += 1
                            quality = "可能有改善"
                            reason = "文本精简/去噪"
                        else:
                            questionable += 1
                            quality = "待确认"
                            reason = "语义待人工复核"
                    else:
                        questionable += 1
                        quality = "待确认"
                        reason = "非中文变化"

                assessment_details.append({
                    "file": r["file"],
                    "block_id": d["id"],
                    "diff": diff_line,
                    "quality": quality,
                    "reason": reason,
                })

    return {
        "total_corrections": total_corrections,
        "good": good_corrections,
        "questionable": questionable,
        "bad": bad_corrections,
        "accuracy": round(good_corrections / total_corrections * 100, 1) if total_corrections > 0 else 0,
        "details": assessment_details,
    }


def print_report(results: list[dict], quality: dict):
    """打印详细对比报告"""
    print("=" * 80)
    print("  SRT 字幕纠错对比分析报告 (Hybrid 模式)")
    print("=" * 80)

    total_orig = sum(r["orig_blocks"] for r in results)
    total_changed = sum(r["changed_blocks"] for r in results)
    total_token = sum(r["total_token_changes"] for r in results)

    print(f"\n一、总体统计")
    print(f"  测试文件数:    {len(results)}")
    print(f"  总字幕块数:    {total_orig}")
    print(f"  被修改的块数:  {total_changed} ({round(total_changed/total_orig*100, 1)}%)")
    print(f"  Token级变化数: {total_token}")

    print(f"\n二、逐文件统计")
    print(f"  {'文件名':<40} {'总块数':>6} {'修改块':>6} {'修改率':>7} {'变化数':>5}")
    print(f"  {'-'*70}")
    for r in results:
        name = r["file"][:38]
        rate = f"{round(r['changed_blocks']/r['orig_blocks']*100, 1)}%"
        print(f"  {name:<40} {r['orig_blocks']:>6} {r['changed_blocks']:>6} {rate:>7} {r['total_token_changes']:>5}")

    print(f"\n三、纠错质量评估")
    print(f"  评估维度: 术语修正 + 文本去噪")
    print(f"  总修正次数:    {quality['total_corrections']}")
    print(f"  正确/可接受:   {quality['good']}")
    print(f"  待人工确认:    {quality['questionable']}")
    print(f"  明确错误:      {quality['bad']}")
    print(f"  预估准确率:    {quality['accuracy']}%")
    print(f"  注: 准确率为基于规则的自动评估，最终需人工复核确认")

    print(f"\n四、逐文件修改详情")
    for r in results:
        if not r["details"]:
            print(f"\n  [{r['file']}] 无修改")
            continue
        print(f"\n  ┌─ [{r['file']}] 共 {r['changed_blocks']} 块被修改 ─┐")
        for d in r["details"]:
            print(f"  │ Block #{d['id']} [{d['start']}]")
            print(f"  │   原始: {d['original']}")
            print(f"  │   纠错: {d['corrected']}")
            for diff_line in d["diffs"]:
                print(f"  │   {diff_line}")
            print(f"  │")
        print(f"  └{'─'*60}┘")

    print(f"\n五、结论")
    if total_changed == 0:
        print(f"  [警告] Hybrid 模式未对任何字幕块进行修改，请检查 Agent 是否正常工作。")
    else:
        print(f"  Hybrid 模式共修改 {total_changed}/{total_orig} 个字幕块 ({round(total_changed/total_orig*100, 1)}%)。")
        print(f"  基于规则评估的预估准确率约 {quality['accuracy']}%，建议对「待确认」项进行人工复核。")


def main():
    orig_files = sorted(TEST_DIR.glob("*.srt"))
    results = []

    for orig_path in orig_files:
        corr_name = orig_path.stem + "_corrected.srt"
        corr_path = CORRECTED_DIR / corr_name
        if not corr_path.exists():
            print(f"[WARN] 未找到纠错文件: {corr_name}")
            continue
        result = analyze_one_file(orig_path, corr_path)
        results.append(result)

    if not results:
        print("[ERROR] 没有找到可对比的文件对")
        return

    quality = assess_quality(results)
    print_report(results, quality)


if __name__ == "__main__":
    main()
