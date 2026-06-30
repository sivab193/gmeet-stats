import csv
import os
from collections import Counter, defaultdict
from datetime import datetime

CSV_FILE = os.path.join(os.path.dirname(__file__), "conference_history_records.csv")

def parse_duration_to_seconds(dur_str):
    if not dur_str or not isinstance(dur_str, str):
        return 0
    parts = dur_str.strip().split(':')
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1 and parts[0].isdigit():
            return int(parts[0])
    except ValueError:
        pass
    return 0

def format_seconds(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

def load_and_clean_data(filepath=None):
    target_file = filepath or CSV_FILE
    if not os.path.exists(target_file):
        return []
    
    records = []
    with open(target_file, mode="r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            start_str = row.get("Start Time", "").strip()
            end_str = row.get("End Time", "").strip()
            dur_str = row.get("Duration", "").strip()
            meeting_code = row.get("Meeting Code", "").strip() or "Direct Call / Unknown"
            part_state = row.get("Participation State", "").strip() or "INVITED_OR_CALENDAR"
            
            # Parse datetime
            start_dt = None
            if start_str and len(start_str) >= 19:
                try:
                    start_dt = datetime.strptime(start_str[:19], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
            
            duration_sec = parse_duration_to_seconds(dur_str)
            
            records.append({
                "id": idx + 1,
                "item_id": row.get("Item Id", ""),
                "meeting_code": meeting_code,
                "start_time": start_str,
                "start_dt": start_dt.isoformat() if start_dt else None,
                "year": str(start_dt.year) if start_dt else "Unknown",
                "month": start_dt.strftime("%Y-%m") if start_dt else "Unknown",
                "day_of_week": start_dt.strftime("%A") if start_dt else "Unknown",
                "hour": start_dt.hour if start_dt else -1,
                "duration_str": dur_str,
                "duration_sec": duration_sec,
                "duration_fmt": format_seconds(duration_sec),
                "participation": part_state,
                "call_direction": row.get("Call Direction", "").strip(),
            })
    return records

def compute_analytics(records=None, year_filter=None, room_filter=None):
    if records is None:
        records = load_and_clean_data()
        
    filtered = records
    if year_filter and year_filter != "ALL":
        filtered = [r for r in filtered if r["year"] == str(year_filter)]
    if room_filter and room_filter != "ALL":
        filtered = [r for r in filtered if r["meeting_code"].lower() == room_filter.lower()]
        
    total_meetings = len(filtered)
    total_sec = sum(r["duration_sec"] for r in filtered)
    total_hours = round(total_sec / 3600, 2)
    avg_duration_min = round((total_sec / 60) / total_meetings, 1) if total_meetings > 0 else 0
    
    participated_count = sum(1 for r in filtered if r["participation"] == "PARTICIPATED")
    
    # Longest meeting
    longest = max(filtered, key=lambda x: x["duration_sec"]) if filtered else None
    
    # Duration Buckets
    buckets = {
        "Quick (<15m)": 0,
        "Standard (15-30m)": 0,
        "Long (30-60m)": 0,
        "Marathon (>1h)": 0,
    }
    for r in filtered:
        s = r["duration_sec"]
        if s < 900:
            buckets["Quick (<15m)"] += 1
        elif s < 1800:
            buckets["Standard (15-30m)"] += 1
        elif s < 3600:
            buckets["Long (30-60m)"] += 1
        else:
            buckets["Marathon (>1h)"] += 1
            
    # Monthly Trends
    monthly_map = defaultdict(lambda: {"count": 0, "sec": 0})
    for r in filtered:
        m = r["month"]
        if m != "Unknown":
            monthly_map[m]["count"] += 1
            monthly_map[m]["sec"] += r["duration_sec"]
            
    monthly_trend = [
        {
            "month": m,
            "count": data["count"],
            "hours": round(data["sec"] / 3600, 1)
        }
        for m, data in sorted(monthly_map.items())
    ]
    
    # Day of Week Heatmap
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_map = {day: 0 for day in dow_order}
    for r in filtered:
        dow = r["day_of_week"]
        if dow in dow_map:
            dow_map[dow] += 1
            
    # Hourly Distribution
    hourly_map = {h: 0 for h in range(24)}
    for r in filtered:
        h = r["hour"]
        if 0 <= h < 24:
            hourly_map[h] += 1
            
    # Top Meeting Rooms
    room_map = defaultdict(lambda: {"count": 0, "sec": 0})
    for r in filtered:
        code = r["meeting_code"]
        room_map[code]["count"] += 1
        room_map[code]["sec"] += r["duration_sec"]
        
    top_rooms = sorted(room_map.items(), key=lambda x: x[1]["count"], reverse=True)[:8]
    top_rooms_list = [
        {
            "code": code,
            "count": data["count"],
            "hours": round(data["sec"] / 3600, 1)
        }
        for code, data in top_rooms
    ]
    
    # Available years for filtering
    years = sorted(list(set(r["year"] for r in records if r["year"] != "Unknown")))
    
    # Behavioral Insights Generation
    insights = []
    
    # 1. Marathon Insight
    marathon_hours = round(sum(r["duration_sec"] for r in filtered if r["duration_sec"] >= 3600) / 3600, 1)
    if buckets["Marathon (>1h)"] > 0:
        insights.append({
            "icon": "⚡",
            "title": "Marathon Grinder",
            "description": f"You participated in {buckets['Marathon (>1h)']} meetings exceeding 1 hour, accounting for {marathon_hours} total hours of deep focus and collaboration.",
            "tag": "High Endurance"
        })
        
    # 2. Weekend Warrior
    weekend_count = dow_map.get("Saturday", 0) + dow_map.get("Sunday", 0)
    if weekend_count > 0:
        weekend_pct = round((weekend_count / total_meetings) * 100, 1) if total_meetings else 0
        insights.append({
            "icon": "🌴",
            "title": "Weekend Warrior",
            "description": f"You logged {weekend_count} calls ({weekend_pct}% of activity) on Saturdays and Sundays.",
            "tag": "Always On"
        })
        
    # 3. Room Loyalty
    if top_rooms_list:
        top_room = top_rooms_list[0]
        loyalty_pct = round((top_room["count"] / total_meetings) * 100, 1) if total_meetings else 0
        insights.append({
            "icon": "👑",
            "title": "Primary Hub Loyalty",
            "description": f"Room '{top_room['code']}' is your primary virtual office, hosting {top_room['count']} meetings ({loyalty_pct}% of total volume).",
            "tag": "Hub Room"
        })
        
    # 4. Peak Time
    peak_hour = max(hourly_map.items(), key=lambda x: x[1])[0] if hourly_map else 15
    insights.append({
        "icon": "⏰",
        "title": "Peak Activity Hour",
        "description": f"Your heaviest meeting activity occurs around {peak_hour:02d}:00 UTC, showing consistent daily synchronization habits.",
        "tag": "Schedule Rhythm"
    })

    return {
        "kpi": {
            "total_meetings": total_meetings,
            "total_hours": total_hours,
            "total_days": round(total_hours / 24, 1),
            "avg_duration_min": avg_duration_min,
            "participated_count": participated_count,
            "longest_meeting": {
                "code": longest["meeting_code"] if longest else "N/A",
                "duration_fmt": longest["duration_fmt"] if longest else "0m",
                "date": longest["start_time"][:10] if longest else "N/A"
            } if longest else None
        },
        "buckets": buckets,
        "monthly_trend": monthly_trend,
        "day_of_week": dow_map,
        "hourly": hourly_map,
        "top_rooms": top_rooms_list,
        "insights": insights,
        "years": years
    }
