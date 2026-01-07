#!/usr/bin/env python3
"""
Анализ истории Claude Code за последнюю неделю.
Собирает данные из всех проектов и строит хронологию.
"""

import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

PROJECTS_DIR = "/Users/larry/.claude/projects/"
WEEK_DAYS = 7

def get_project_name(path):
    """Извлекает понятное имя проекта из пути"""
    parts = path.split('/')
    if '-Users-larry' in parts:
        idx = parts.index('-Users-larry')
        if idx + 1 < len(parts):
            return parts[idx + 1].replace('-', ' ').title()
    return Path(path).name

def parse_timestamp(ts_str):
    """Парсит ISO timestamp"""
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except:
        return None

def get_file_age_days(filepath):
    """Возвращает возраст файла в днях"""
    mtime = os.path.getmtime(filepath)
    file_date = datetime.fromtimestamp(mtime)
    age = (datetime.now() - file_date).days
    return age, file_date

def analyze_jsonl_file(filepath):
    """Анализирует JSONL файл и извлекает данные"""
    data = {
        'entries': [],
        'first_timestamp': None,
        'last_timestamp': None,
        'message_count': 0
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        timestamp = parse_timestamp(entry.get('snapshot', {}).get('timestamp') or
                                                    entry.get('timestamp', ''))
                        if timestamp:
                            data['entries'].append({
                                'timestamp': timestamp,
                                'type': entry.get('type', 'unknown'),
                                'message_id': entry.get('messageId', ''),
                            })
                            data['message_count'] += 1

                            if not data['first_timestamp'] or timestamp < data['first_timestamp']:
                                data['first_timestamp'] = timestamp
                            if not data['last_timestamp'] or timestamp > data['last_timestamp']:
                                data['last_timestamp'] = timestamp
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        pass

    return data

def scan_all_projects():
    """Сканирует все проекты и собирает данные"""
    projects_data = []
    cutoff_date = datetime.now() - timedelta(days=WEEK_DAYS)

    for project_path in Path(PROJECTS_DIR).iterdir():
        if project_path.is_dir() and not project_path.name.startswith('.'):
            project_name = get_project_name(str(project_path))

            # Находим все jsonl файлы
            jsonl_files = list(project_path.glob('*.jsonl'))
            agent_files = list(project_path.glob('agent-*.jsonl'))

            all_files = jsonl_files + agent_files

            recent_activity = []
            total_messages = 0
            earliest_ts = None
            latest_ts = None

            for filepath in all_files:
                age_days, file_date = get_file_age_days(filepath)

                # Берем файлы за последнюю неделю
                if age_days <= WEEK_DAYS:
                    file_data = analyze_jsonl_file(filepath)
                    if file_data['message_count'] > 0:
                        recent_activity.append({
                            'filename': filepath.name,
                            'age_days': age_days,
                            'modified': file_date,
                            'messages': file_data['message_count'],
                            'first_ts': file_data['first_timestamp'],
                            'last_ts': file_data['last_timestamp']
                        })
                        total_messages += file_data['message_count']

                        if file_data['first_timestamp'] and (not earliest_ts or file_data['first_timestamp'] < earliest_ts):
                            earliest_ts = file_data['first_timestamp']
                        if file_data['last_timestamp'] and (not latest_ts or file_data['last_timestamp'] > latest_ts):
                            latest_ts = file_data['last_timestamp']

            if recent_activity:
                projects_data.append({
                    'name': project_name,
                    'path': str(project_path),
                    'total_messages': total_messages,
                    'files_count': len(recent_activity),
                    'earliest_activity': earliest_ts,
                    'latest_activity': latest_ts,
                    'files': sorted(recent_activity, key=lambda x: x['modified'], reverse=True)
                })

    # Сортируем по последней активности
    projects_data.sort(key=lambda x: x['latest_activity'] or datetime.min, reverse=True)
    return projects_data

def build_timeline(projects_data):
    """Строит хронологию по всем записям"""
    timeline = []

    for project in projects_data:
        for file_info in project['files']:
            if file_info['first_ts']:
                timeline.append({
                    'timestamp': file_info['first_ts'],
                    'project': project['name'],
                    'filename': file_info['filename'],
                    'type': 'conversation_start',
                    'messages': file_info['messages']
                })
            if file_info['last_ts']:
                timeline.append({
                    'timestamp': file_info['last_ts'],
                    'project': project['name'],
                    'filename': file_info['filename'],
                    'type': 'last_activity',
                    'messages': file_info['messages']
                })

    timeline.sort(key=lambda x: x['timestamp'], reverse=True)
    return timeline

def generate_html_report(projects_data, timeline):
    """Генерирует HTML отчет"""

    # Группируем по дням
    daily_activity = defaultdict(lambda: {'projects': set(), 'total_messages': 0})
    for item in timeline:
        day_key = item['timestamp'].strftime('%Y-%m-%d')
        daily_activity[day_key]['projects'].add(item['project'])
        daily_activity[day_key]['total_messages'] += item.get('messages', 0)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code Activity - Last Week</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 40px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stat-label {{
            color: #888;
            margin-top: 5px;
        }}
        .timeline {{
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .day-header {{
            font-size: 1.8em;
            margin: 30px 0 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(0,217,255,0.3);
            color: #00d9ff;
        }}
        .day-stats {{
            color: #888;
            margin-bottom: 15px;
            font-size: 0.9em;
        }}
        .project-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #00d9ff;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .project-card:hover {{
            transform: translateX(5px);
            box-shadow: 0 5px 20px rgba(0,217,255,0.2);
        }}
        .project-name {{
            font-size: 1.3em;
            font-weight: bold;
            color: #00ff88;
            margin-bottom: 10px;
        }}
        .project-meta {{
            display: flex;
            gap: 20px;
            color: #aaa;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        .file-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .file-badge {{
            background: rgba(0,217,255,0.15);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            color: #00d9ff;
        }}
        .time {{
            color: #666;
            font-size: 0.85em;
        }}
        .empty {{
            text-align: center;
            color: #666;
            padding: 40px;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .project-card {{
            animation: fadeIn 0.3s ease-out;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Claude Code Activity</h1>
        <p class="subtitle">Хронология активности за последние 7 дней</p>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(projects_data)}</div>
                <div class="stat-label">Активных проектов</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{sum(p['total_messages'] for p in projects_data)}</div>
                <div class="stat-label">Всего сообщений</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{sum(p['files_count'] for p in projects_data)}</div>
                <div class="stat-label">Файлов переписки</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(daily_activity)}</div>
                <div class="stat-label">Дней активности</div>
            </div>
        </div>

        <div class="timeline">
"""

    # Сортируем дни по убыванию
    sorted_days = sorted(daily_activity.items(), key=lambda x: x[0], reverse=True)

    for day_key, day_data in sorted_days:
        date_obj = datetime.strptime(day_key, '%Y-%m-%d')
        day_name = date_obj.strftime('%A, %d %B %Y')
        day_name_ru = {
            'Monday': 'Понедельник', 'Tuesday': 'Вторник', 'Wednesday': 'Среда',
            'Thursday': 'Четверг', 'Friday': 'Пятница', 'Saturday': 'Суббота',
            'Sunday': 'Воскресенье'
        }.get(date_obj.strftime('%A'), date_obj.strftime('%A'))

        month_ru = {
            'January': 'января', 'February': 'февраля', 'March': 'марта',
            'April': 'апреля', 'May': 'мая', 'June': 'июня',
            'July': 'июля', 'August': 'августа', 'September': 'сентября',
            'October': 'октября', 'November': 'ноября', 'December': 'декабря'
        }.get(date_obj.strftime('%B'), date_obj.strftime('%B'))

        html += f"""
            <div class="day-header">
                {day_name_ru}, {date_obj.day} {month_ru} {date_obj.year}
            </div>
            <div class="day-stats">
                Проектов: {len(day_data['projects'])} | Сообщений: {day_data['total_messages']}
            </div>
"""

        # Находим проекты за этот день
        day_projects = defaultdict(list)
        for item in timeline:
            if item['timestamp'].strftime('%Y-%m-%d') == day_key:
                day_projects[item['project']].append(item)

        for project_name, items in sorted(day_projects.items()):
            latest_item = max(items, key=lambda x: x['timestamp'])
            total_msgs = sum(i.get('messages', 0) for i in items)

            html += f"""
            <div class="project-card">
                <div class="project-name">{project_name}</div>
                <div class="project-meta">
                    <span>📨 {total_msgs} сообщений</span>
                    <span>📁 {len(items)} файл(ов)</span>
                    <span class="time">🕐 Последнее: {latest_item['timestamp'].strftime('%H:%M')}</span>
                </div>
                <div class="file-list">
"""

            for item in sorted(items, key=lambda x: x['timestamp'], reverse=True)[:5]:
                html += f'<span class="file-badge">{item["filename"][:30]}...</span>'

            html += """
                </div>
            </div>
"""

    html += """
        </div>
    </div>
</body>
</html>
"""
    return html

def main():
    print("🔍 Сканирую проекты Claude Code...")
    projects_data = scan_all_projects()

    print(f"📊 Найдено {len(projects_data)} активных проектов за последнюю неделю")

    timeline = build_timeline(projects_data)
    print(f"📅 Построена хронология из {len(timeline)} записей")

    html = generate_html_report(projects_data, timeline)

    output_path = "/Users/larry/Клэр/AI-Memory/working/claude_code_weekly.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ HTML отчет сохранен: {output_path}")

    # Также сохраним JSON для анализа
    json_output = "/Users/larry/Клэр/AI-Memory/working/claude_code_weekly.json"
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'week_range': f"{(datetime.now() - timedelta(days=WEEK_DAYS)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}",
            'projects': projects_data,
            'timeline': [
                {**item, 'timestamp': item['timestamp'].isoformat()}
                for item in timeline
            ]
        }, f, indent=2, ensure_ascii=False)

    print(f"📋 JSON данные сохранены: {json_output}")

    return projects_data, timeline

if __name__ == "__main__":
    main()
