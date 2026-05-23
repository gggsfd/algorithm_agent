import time
import json
import requests
import sys
import os

SRT_PATH = r'd:\Mycode\算法_agent\str_file\4.3\4月11日 (1)(1).srt'
API_URL = 'http://localhost:8000/api/v1/correct'

with open(SRT_PATH, 'r', encoding='utf-8') as f:
    srt_content = f.read()

total_blocks = [b for b in srt_content.strip().split('\n\n') if b.strip()]
print(f'=== Hybrid 模式性能基准测试 ===')
print(f'文件: 4月11日 (1)(1).srt')
print(f'字幕块数: {len(total_blocks)}')
print(f'文件大小: {len(srt_content)} 字符')
print()

print('发送请求 (correction_mode=hybrid, domain=algorithm)...')
start = time.time()

resp = requests.post(API_URL, data={
    'domain': 'algorithm',
    'correction_mode': 'hybrid',
}, files={'file': ('test.srt', srt_content.encode('utf-8'), 'text/plain')}, timeout=600)

elapsed = time.time() - start

if resp.status_code != 200:
    print(f'[ERROR] HTTP {resp.status_code}: {resp.text}')
    sys.exit(1)

result = resp.json()
data = result.get('data', {})

print(f'\n{"="*60}')
print(f'耗时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)')
print(f'Success: {data.get("success")}')
print(f'Correction mode: {data.get("correction_mode")}')
print(f'Effective mode: {data.get("effective_mode")}')
print(f'Degraded: {data.get("degraded")}')
print()

corrected_srt = data.get('corrected_srt', '')
output_path = SRT_PATH.replace('.srt', '_corrected_hybrid.srt')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(corrected_srt)
print(f'已保存到: {output_path}')
print(f'输出大小: {len(corrected_srt)} 字符')
print()

# 分析变更
def extract_text_lines(srt_text):
    lines = []
    blocks = srt_text.strip().split('\n\n')
    for block in blocks:
        block_lines = block.strip().split('\n')
        text_parts = []
        for line in block_lines:
            line = line.strip()
            if not line:
                continue
            if line[0].isdigit() and len(line) <= 4:
                continue
            if '-->' in line:
                continue
            text_parts.append(line)
        if text_parts:
            lines.append(' '.join(text_parts))
    return lines

original_lines = extract_text_lines(srt_content)
corrected_lines = extract_text_lines(corrected_srt)

print('=' * 60)
print(f'原始行数: {len(original_lines)}')
print(f'纠错行数: {len(corrected_lines)}')

changes = []
for i in range(min(len(original_lines), len(corrected_lines))):
    if original_lines[i] != corrected_lines[i]:
        changes.append((i+1, original_lines[i], corrected_lines[i]))

print(f'被修改的字幕行数: {len(changes)}')
if original_lines:
    print(f'修改率: {len(changes)/len(original_lines)*100:.1f}%')
print()

if changes:
    print('=== 具体变更列表 ===')
    for idx, orig, corr in changes:
        print(f'  [#{idx}] "{orig}" -> "{corr}"')
else:
    print('(无变更)')

print()
print(f'=== 测试完成 ===')
