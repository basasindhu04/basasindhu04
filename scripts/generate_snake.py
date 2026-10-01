import urllib.request
import json
import os
import re
import collections

def get_contribution_data(username):
    # Method 1: Scrape official GitHub public contributions page (exact heatmap shown on github.com)
    try:
        url = f"https://github.com/users/{username}/contributions"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8')
            
            # Find total contributions
            total_match = re.search(r'([0-9,]+)\s+contributions\s+in\s+(?:the\s+last\s+year|\d{4})', html)
            total_count = int(total_match.group(1).replace(',', '')) if total_match else 0
            
            # Find all td cells with data-date and data-level
            pattern = re.compile(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"')
            matches = pattern.findall(html)
            
            if matches:
                color_map = {
                    "0": "#161b22",
                    "1": "#0e4429",
                    "2": "#006d32",
                    "3": "#26a641",
                    "4": "#39d353"
                }
                
                # Group matches into 7-day weeks
                weeks = []
                current_week = []
                for date_str, level_str in matches:
                    cnt = int(level_str)
                    current_week.append({
                        "date": date_str,
                        "contributionCount": cnt,
                        "color": color_map.get(level_str, "#161b22")
                    })
                    if len(current_week) == 7:
                        weeks.append({"contributionDays": current_week})
                        current_week = []
                if current_week:
                    weeks.append({"contributionDays": current_week})
                
                # Keep last 52 weeks
                if len(weeks) > 52:
                    weeks = weeks[-52:]
                
                # Calculate active days
                active_days = sum(1 for _, lvl in matches if int(lvl) > 0)
                
                print(f"Scraped official GitHub page successfully: Total {total_count}, Active Days {active_days}")
                return {
                    "totalContributions": total_count,
                    "activeDays": active_days,
                    "weeks": weeks
                }
    except Exception as e:
        print(f"Scraping failed: {e}")

    # Method 2: GraphQL API fallback
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        query = """
        query($username: String!) {
          user(login: $username) {
            contributionsCollection {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    date
                    contributionCount
                    color
                  }
                }
              }
            }
          }
        }
        """
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": query, "variables": {"username": username}}).encode('utf-8'),
            headers={
                "User-Agent": "Python",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
                return calendar
        except Exception as e:
            print(f"GraphQL request failed: {e}")

    # Method 3: Public contributions API
    try:
        url = f"https://github-contributions-api.jogruber.de/v4/{username}?y=last"
        req = urllib.request.Request(url, headers={"User-Agent": "Python"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            contributions = data.get("contributions", [])
            total = sum(c["count"] for c in contributions)
            active = sum(1 for c in contributions if c["count"] > 0)
            
            weeks = []
            current_week = []
            for c in contributions:
                count = c["count"]
                if count == 0:
                    color = "#161b22"
                elif count < 3:
                    color = "#0e4429"
                elif count < 6:
                    color = "#006d32"
                elif count < 9:
                    color = "#26a641"
                else:
                    color = "#39d353"
                
                current_week.append({
                    "date": c["date"],
                    "contributionCount": count,
                    "color": color
                })
                if len(current_week) == 7:
                    weeks.append({"contributionDays": current_week})
                    current_week = []
            if current_week:
                weeks.append({"contributionDays": current_week})
            
            if len(weeks) > 52:
                weeks = weeks[-52:]

            return {
                "totalContributions": total,
                "activeDays": active,
                "weeks": weeks
            }
    except Exception as e:
        print(f"Fallback failed: {e}")
        weeks = []
        for w in range(52):
            days = []
            for d in range(7):
                days.append({"date": "", "contributionCount": 0, "color": "#161b22"})
            weeks.append({"contributionDays": days})
        return {"totalContributions": 0, "activeDays": 0, "weeks": weeks}

def simulate_snake_game(weeks, max_steps=140):
    COLS = len(weeks)
    ROWS = 7
    
    grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
    color_grid = [["#161b22" for _ in range(ROWS)] for _ in range(COLS)]
    food_coords = set()
    active_days = 0

    for c in range(COLS):
        days = weeks[c].get("contributionDays", [])
        for r in range(min(ROWS, len(days))):
            cnt = days[r].get("contributionCount", 0)
            col = days[r].get("color", "#161b22")
            grid[c][r] = cnt
            color_grid[c][r] = col
            if cnt > 0:
                food_coords.add((c, r))
                active_days += 1

    # Snake state: list of (col, row), head is snake[0]
    snake = [(2, 0), (1, 0), (0, 0)]
    eaten_history = {} # (c, r) -> step_idx
    snake_history = [] # list of snake segment positions at each step

    def get_neighbors(pos):
        c, r = pos
        res = []
        for dc, dr in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nc, nr = c + dc, r + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                res.append((nc, nr))
        return res

    def bfs_path(start, targets, obstacles):
        queue = collections.deque([[start]])
        visited = set(obstacles)
        visited.add(start)
        while queue:
            path = queue.popleft()
            curr = path[-1]
            if curr in targets:
                return path
            for nxt in get_neighbors(curr):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(path + [nxt])
        # Fallback to any open neighbor
        for nxt in get_neighbors(start):
            if nxt not in obstacles:
                return [start, nxt]
        return [start, get_neighbors(start)[0]]

    remaining_food = set(food_coords)
    step = 0
    snake_history.append(list(snake))

    while step < max_steps and remaining_food:
        head = snake[0]
        obstacles = set(snake[:-1])
        path = bfs_path(head, remaining_food, obstacles)
        
        if len(path) <= 1:
            break
            
        for nxt_pos in path[1:]:
            step += 1
            is_food = nxt_pos in remaining_food
            if is_food:
                remaining_food.remove(nxt_pos)
                eaten_history[nxt_pos] = step
                # Grow snake: do not pop tail
                snake = [nxt_pos] + snake
            else:
                # Normal move
                snake = [nxt_pos] + snake[:-1]
                
            snake_history.append(list(snake))
            if step >= max_steps or not remaining_food:
                break

    return grid, color_grid, snake_history, eaten_history, active_days

def generate_clean_snake_svg(calendar_data, dark_mode=True):
    weeks = calendar_data.get("weeks", [])
    total_contributions = calendar_data.get("totalContributions", 0)
    scraped_active = calendar_data.get("activeDays", 0)
    
    grid, color_grid, snake_history, eaten_history, active_days_sim = simulate_snake_game(weeks, max_steps=140)
    active_days = scraped_active if scraped_active > 0 else active_days_sim
    
    COLS = len(weeks)
    ROWS = 7
    CELL_SIZE = 10
    CELL_GAP = 3
    MARGIN_X = 25
    MARGIN_TOP = 40
    MARGIN_BOTTOM = 20
    
    total_steps = len(snake_history)
    step_dur = 0.22 # Reduced, smooth, observable speed (220ms/step)
    total_duration = round(total_steps * step_dur, 2)
    
    # Always render the dark theme aesthetic so any account or browser sees the exact same card
    bg_color = "#0d1117"
    empty_cell_color = "#161b22"
    snake_head_color = "#00D2FF"
    snake_body_color = "#39d353"
    snake_tail_color = "#006d32"
    border_color = "#30363d"
    text_color = "#c9d1d9"
    sub_color = "#8b949e"
    accent_color = "#00D2FF"
    green_accent = "#39d353"
    
    svg_width = MARGIN_X * 2 + COLS * (CELL_SIZE + CELL_GAP) - CELL_GAP
    svg_height = MARGIN_TOP + ROWS * (CELL_SIZE + CELL_GAP) - CELL_GAP + MARGIN_BOTTOM
    
    # 1. Build grid cells
    cells_svg = []
    for c in range(COLS):
        for r in range(ROWS):
            x = MARGIN_X + c * (CELL_SIZE + CELL_GAP)
            y = MARGIN_TOP + r * (CELL_SIZE + CELL_GAP)
            initial_color = color_grid[c][r]
            
            if (c, r) in eaten_history:
                eaten_step = eaten_history[(c, r)]
                eaten_time = round(eaten_step * step_dur, 2)
                
                cell_xml = f"""
    <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="2" fill="{initial_color}">
      <animate attributeName="fill" to="#ffffff" begin="{eaten_time}s" dur="0.12s" fill="freeze" />
      <animate attributeName="fill" to="{empty_cell_color}" begin="{round(eaten_time + 0.12, 2)}s" dur="0.2s" fill="freeze" />
    </rect>"""
            else:
                cell_xml = f'<rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="2" fill="{initial_color}" />'
            cells_svg.append(cell_xml)

    # 2. Build snake segments
    max_snake_len = max(len(s) for s in snake_history)
    snake_segments_svg = []
    
    for seg_idx in range(max_snake_len):
        x_values = []
        y_values = []
        opacity_values = []
        
        for step_idx, s in enumerate(snake_history):
            if seg_idx < len(s):
                c, r = s[seg_idx]
                px = MARGIN_X + c * (CELL_SIZE + CELL_GAP)
                py = MARGIN_TOP + r * (CELL_SIZE + CELL_GAP)
                x_values.append(str(px))
                y_values.append(str(py))
                opacity_values.append("1")
            else:
                x_values.append("-50")
                y_values.append("-50")
                opacity_values.append("0")

        if seg_idx == 0:
            fill_color = snake_head_color
            rx_val = "3"
        elif seg_idx == max_snake_len - 1:
            fill_color = snake_tail_color
            rx_val = "2"
        else:
            fill_color = snake_body_color
            rx_val = "2"
            
        x_anim = ";".join(x_values)
        y_anim = ";".join(y_values)
        op_anim = ";".join(opacity_values)
        
        seg_xml = f"""
    <rect width="{CELL_SIZE}" height="{CELL_SIZE}" rx="{rx_val}" fill="{fill_color}">
      <animate attributeName="x" values="{x_anim}" dur="{total_duration}s" repeatCount="indefinite" calcMode="discrete" />
      <animate attributeName="y" values="{y_anim}" dur="{total_duration}s" repeatCount="indefinite" calcMode="discrete" />
      <animate attributeName="opacity" values="{op_anim}" dur="{total_duration}s" repeatCount="indefinite" calcMode="discrete" />
    </rect>"""
        snake_segments_svg.append(seg_xml)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">
  <style>
    .bg {{ fill: {bg_color}; stroke: {border_color}; stroke-width: 1px; rx: 6px; }}
    .title {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 12px; font-weight: 600; fill: {text_color}; }}
    .metric-label {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 11px; fill: {sub_color}; }}
    .metric-val {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 11px; font-weight: 700; }}
  </style>

  <!-- Clean Background Container -->
  <rect class="bg" width="{svg_width}" height="{svg_height}" />

  <!-- Integrated Header Bar with Dynamic Active Days & Contributions -->
  <g transform="translate({MARGIN_X}, 22)">
    <text class="title" x="0" y="0">Contribution Heatmap</text>
    
    <text class="metric-label" x="{svg_width - 250}" y="0">Active Days:</text>
    <text class="metric-val" x="{svg_width - 180}" y="0" fill="{accent_color}">{active_days}</text>
    
    <text class="metric-label" x="{svg_width - 140}" y="0">Contributions:</text>
    <text class="metric-val" x="{svg_width - 55}" y="0" fill="{green_accent}">{total_contributions}</text>
  </g>

  <!-- Aligned GitHub Contribution Grid -->
  <g id="grid">
    {"".join(cells_svg)}
  </g>

  <!-- Connected Traditional Snake -->
  <g id="snake">
    {"".join(snake_segments_svg)}
  </g>
</svg>"""

    return svg_content, active_days, total_contributions

def main():
    username = "basasindhu04"
    print(f"Generating exact heatmap snake for {username}...")
    calendar_data = get_contribution_data(username)
    
    os.makedirs("output", exist_ok=True)
    
    dark_svg, active_days, total_contributions = generate_clean_snake_svg(calendar_data, dark_mode=True)
    
    # Save both light and dark as the same unified dark card so all visitors see the identical heatmap
    with open("output/github-contribution-grid-snake-dark.svg", "w", encoding="utf-8") as f:
        f.write(dark_svg)
        
    with open("output/github-contribution-grid-snake.svg", "w", encoding="utf-8") as f:
        f.write(dark_svg)
        
    print(f"Generated identical SVGs. Active Days: {active_days}, Total Contributions: {total_contributions}")

if __name__ == "__main__":
    main()
