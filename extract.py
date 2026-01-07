#!/usr/bin/env python3
"""
Вытаскивает все conversation данные в чистый JSON формат.
Поля: datetime, project, role (user/assistant), message
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import re

PROJECTS_DIR = "/Users/larry/.claude/projects/"
WEEK_DAYS = 15  # Берем больше дней

def parse_timestamp(ts_str):
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00').replace('+00:00', ''))
    except:
        return None

def get_project_name(path):
    parts = path.split('/')
    if '-Users-larry' in parts:
        idx = parts.index('-Users-larry')
        if idx + 1 < len(parts):
            name = parts[idx + 1].replace('-', ' ').title()
            name = re.sub(r'^Users\s*Larry\s*', '', name)
            return name.strip() or "Root"
    return Path(path).name

def extract_message_content(entry):
    content = None
    role = None

    if entry.get('type') == 'user':
        msg = entry.get('message', {})
        cont = msg.get('content', '')
        if isinstance(cont, list):
            content = ' '.join([str(c) for c in cont])
        else:
            content = str(cont) if cont else ''
        role = 'user'
    elif entry.get('type') in ['assistant', 'message']:
        msg = entry.get('message', {})
        if isinstance(msg, dict):
            cont = msg.get('content', [])
            if isinstance(cont, list):
                texts = []
                for item in cont:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            texts.append(item.get('text', ''))
                    elif isinstance(item, str):
                        texts.append(item)
                content = '\n'.join(texts).strip()
            else:
                content = str(cont) if cont else ''
        role = 'assistant'

    if content is None:
        content = ''
    elif not isinstance(content, str):
        content = str(content)

    return content, role

def get_file_age_days(filepath):
    mtime = os.path.getmtime(filepath)
    file_date = datetime.fromtimestamp(mtime)
    age = (datetime.now() - file_date).days
    return age

def extract_all_conversations():
    """Извлекает все разговоры в чистом формате"""

    all_entries = []

    for project_path in Path(PROJECTS_DIR).iterdir():
        if project_path.is_dir() and not project_path.name.startswith('.'):
            project_name = get_project_name(str(project_path))

            for filepath in project_path.glob('*.jsonl'):
                # Возраст файла не проверяем - берем все

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f):
                            if not line.strip():
                                continue

                            try:
                                entry = json.loads(line)
                                timestamp = parse_timestamp(entry.get('timestamp') or
                                                           entry.get('snapshot', {}).get('timestamp', ''))
                                if not timestamp:
                                    continue

                                content, role = extract_message_content(entry)

                                if content and content.strip():
                                    # Очищаем от слишком длинного мусора
                                    if len(content) > 10000:
                                        content = content[:10000] + '...[truncated]'

                                    all_entries.append({
                                        'datetime': timestamp.isoformat(),
                                        'date': timestamp.strftime('%Y-%m-%d'),
                                        'time': timestamp.strftime('%H:%M'),
                                        'project': project_name,
                                        'role': role,
                                        'message': content.strip()
                                    })
                            except (json.JSONDecodeError, KeyError, ValueError):
                                continue
                except Exception as e:
                    continue

    # Сортируем по datetime (новые сверху)
    all_entries.sort(key=lambda x: x['datetime'], reverse=True)

    return all_entries

def main():
    print("🔍 Извлекаю все разговоры...")

    entries = extract_all_conversations()

    print(f"📊 Всего найдено записей: {len(entries)}")

    # Группируем по датам для статистики
    by_date = defaultdict(int)
    for entry in entries:
        by_date[entry['date']] += 1

    print(f"\n📅 Активность по датам:")
    for date in sorted(by_date.keys(), reverse=True)[:15]:
        dt = datetime.strptime(date, '%Y-%m-%d')
        print(f"  {dt.strftime('%a %d %b %Y')}: {by_date[date]} сообщений")

    # Сохраняем в JSON
    output_json = "/Users/larry/Клэр/AI-Memory/working/conversations_data.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Данные сохранены: {output_json}")

    # Также сохраняем в читаемом текстовом формате
    output_txt = "/Users/larry/Клэр/AI-Memory/working/conversations_data.txt"
    with open(output_txt, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(f"[{entry['datetime']}] [{entry['role']}] [{entry['project']}]\n")
            f.write(f"{entry['message']}\n")
            f.write("-" * 80 + "\n\n")

    print(f"✅ Текстовый формат: {output_txt}")

    return entries

if __name__ == "__main__":
    main()
