import urllib.request
import json
import os
import sys

def get_contribution_data(username):
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
            print(f"GraphQL request failed: {e}, using public API fallback.")

    # Public API fallback
    try:
        url = f"https://github-contributions-api.jogruber.de/v4/{username}?y=last"
        req = urllib.request.Request(url, headers={"User-Agent": "Python"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            contributions = data.get("contributions", [])
            total = sum(c["count"] for c in contributions)
            active_days = sum(1 for c in contributions if c["count"] > 0)
            
            # Group into 52 weeks x 7 days
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

            return {
                "totalContributions": total,
                "weeks": weeks
            }
    except Exception as e:
        print(f"Public API fallback failed: {e}")
        # Default empty fallback grid if API offline
        weeks = []
        for w in range(52):
            days = []
            for d in range(7):
                days.append({"date": "", "contributionCount": 0, "color": "#161b22"})
            weeks.append({"contributionDays": days})
        return {"totalContributions": 0, "weeks": weeks}

def build_snake_svg(calendar_data, dark_mode=True):
    weeks = calendar_data.get("weeks", [])
    total_contributions = calendar_data.get("totalContributions", 0)
    
    active_days = 0
    active_coords = []
    
    cell_size = 11
    cell_gap = 3
    margin_x = 35
    margin_y = 45

    # Process grid
    rects_xml = []
    for w_idx, week in enumerate(weeks):
        days = week.get("contributionDays", [])
        for d_idx, day in enumerate(days):
            cnt = day.get("contributionCount", 0)
            color = day.get("color", "#161b22")
            if dark_mode and color.lower() in ["#ebedf0", "#9be9a8"]:
                color = "#161b22"
            elif not dark_mode and color.lower() == "#161b22":
                color = "#ebedf0"
                
            if cnt > 0:
                active_days += 1
                x = margin_x + w_idx * (cell_size + cell_gap)
                y = margin_y + d_idx * (cell_size + cell_gap)
                active_coords.append((x, y))
            
            x = margin_x + w_idx * (cell_size + cell_gap)
            y = margin_y + d_idx * (cell_size + cell_gap)
            
            # Assign unique id for active cells to add subtle spark animation
            cell_id = f"c_{w_idx}_{d_idx}"
            rects_xml.append(
                f'<rect id="{cell_id}" class="day-cell" x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" rx="2" fill="{color}" />'
            )

    # Compute path for snake across active coordinates or default snake path
    if not active_coords:
        # Default smooth serpentine path across grid
        path_points = []
        for w_idx in range(0, min(52, len(weeks)), 2):
            x1 = margin_x + w_idx * (cell_size + cell_gap) + 5
            x2 = margin_x + (w_idx + 1) * (cell_size + cell_gap) + 5
            path_points.append(f"M {x1} {margin_y + 5} L {x1} {margin_y + 6*(cell_size+cell_gap) + 5} L {x2} {margin_y + 6*(cell_size+cell_gap) + 5} L {x2} {margin_y + 5}")
        path_d = " ".join(path_points)
    else:
        # Build path visiting active cells smoothly
        path_cmds = [f"M {active_coords[0][0]+5} {active_coords[0][1]+5}"]
        for (x, y) in active_coords[1:]:
            path_cmds.append(f"L {x+5} {y+5}")
        # Loop back smoothly
        path_cmds.append(f"Z")
        path_d = " ".join(path_cmds)

    bg_color = "#0d1117" if dark_mode else "#ffffff"
    text_color = "#c9d1d9" if dark_mode else "#24292f"
    accent_color = "#00D2FF" if dark_mode else "#0969da"
    sub_color = "#8b949e" if dark_mode else "#57606a"
    snake_head_color = "#00D2FF"
    snake_body_color = "#39d353"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="820" height="175" viewBox="0 0 820 175">
  <style>
    .bg {{ fill: {bg_color}; rx: 8px; }}
    .title {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 13px; font-weight: 600; fill: {text_color}; }}
    .stat-label {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 11px; fill: {sub_color}; }}
    .stat-value {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 12px; font-weight: 700; fill: {accent_color}; }}
    .day-cell {{ transition: filter 0.3s ease, opacity 0.3s ease; }}
    
    /* Subtle spark glow animation on contribution cells when snake passes */
    @keyframes spark-glow {{
      0% {{ filter: none; }}
      50% {{ filter: drop-shadow(0px 0px 5px {snake_head_color}) brightness(1.4); }}
      100% {{ filter: none; }}
    }}
    .active-spark {{ animation: spark-glow 1.5s ease-in-out infinite; }}
  </style>

  <!-- Background -->
  <rect class="bg" width="820" height="175" />

  <!-- Header Dashboard Metrics: Active Days & Total Contributions -->
  <g transform="translate(35, 25)">
    <text class="title" x="0" y="0">GitHub Contribution Activity</text>
    
    <text class="stat-label" x="480" y="0">Active Days:</text>
    <text class="stat-value" x="555" y="0">{active_days}</text>
    
    <text class="stat-label" x="615" y="0">Contributions:</text>
    <text class="stat-value" x="705" y="0">{total_contributions}</text>
  </g>

  <!-- Contribution Grid -->
  <g>
    {"".join(rects_xml)}
  </g>

  <!-- Smooth Motion Path for Snake -->
  <path id="snake-path" d="{path_d}" fill="none" stroke="none" />

  <!-- Constant-size Snake Traveling Smoothly (5 fixed segments, zero growth/shrinkage) -->
  <g id="snake">
    <!-- Snake Body Segment 4 -->
    <circle r="4" fill="{snake_body_color}" opacity="0.4">
      <animateMotion dur="22s" repeatCount="indefinite" begin="-1.2s">
        <mpath href="#snake-path" />
      </animateMotion>
    </circle>
    <!-- Snake Body Segment 3 -->
    <circle r="4.5" fill="{snake_body_color}" opacity="0.6">
      <animateMotion dur="22s" repeatCount="indefinite" begin="-0.9s">
        <mpath href="#snake-path" />
      </animateMotion>
    </circle>
    <!-- Snake Body Segment 2 -->
    <circle r="5" fill="{snake_body_color}" opacity="0.8">
      <animateMotion dur="22s" repeatCount="indefinite" begin="-0.6s">
        <mpath href="#snake-path" />
      </animateMotion>
    </circle>
    <!-- Snake Body Segment 1 -->
    <circle r="5.5" fill="{snake_head_color}" opacity="0.9">
      <animateMotion dur="22s" repeatCount="indefinite" begin="-0.3s">
        <mpath href="#snake-path" />
      </animateMotion>
    </circle>
    <!-- Snake Head (Constant size, leading position) -->
    <circle r="6" fill="{snake_head_color}">
      <animateMotion dur="22s" repeatCount="indefinite" begin="0s">
        <mpath href="#snake-path" />
      </animateMotion>
    </circle>
  </g>
</svg>
"""
    return svg

def main():
    username = "basasindhu04"
    print(f"Fetching contribution data for {username}...")
    calendar_data = get_contribution_data(username)
    
    os.makedirs("output", exist_ok=True)
    
    dark_svg = build_snake_svg(calendar_data, dark_mode=True)
    light_svg = build_snake_svg(calendar_data, dark_mode=False)
    
    with open("output/github-contribution-grid-snake-dark.svg", "w", encoding="utf-8") as f:
        f.write(dark_svg)
        
    with open("output/github-contribution-grid-snake.svg", "w", encoding="utf-8") as f:
        f.write(light_svg)
        
    print("Snake SVGs successfully generated in output/")

if __name__ == "__main__":
    main()
