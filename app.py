import csv
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
ISO_CODES = {
    "India": "in", "Australia": "au", "England": "gb-eng", "New Zealand": "nz",
    "South Africa": "za", "West Indies": "wi", "Afghanistan": "af", "Sri Lanka": "lk",
    "Bangladesh": "bd", "Pakistan": "pk", "Ireland": "ie", "Zimbabwe": "zw", "USA": "us",
    "UAE": "ae", "Unknown": "un"
}

def get_initial_teams():
    def get_local_logo(name):
        return f"/static/{name}.png"

    return [
        {"id": 0, "name": "CSK", "logo": get_local_logo("CSK"), "budget": 43.40, "players": [], "overseas": 4, "total_slots_filled": 16, "color": "#F9CD05", "gradient": "linear-gradient(135deg, #F9CD05 0%, #FFA500 100%)", "text": "#fff"},
        {"id": 1, "name": "DC", "logo": get_local_logo("DC"), "budget": 21.80, "players": [], "overseas": 3, "total_slots_filled": 17, "color": "#00008B", "gradient": "linear-gradient(135deg, #17449E 0%, #000 100%)", "text": "#fff"},
        {"id": 2, "name": "GT", "logo": get_local_logo("GT"), "budget": 12.90, "players": [], "overseas": 4, "total_slots_filled": 20, "color": "#1B2133", "gradient": "linear-gradient(135deg, #1B2133 0%, #0B4973 100%)", "text": "#fff"},
        {"id": 3, "name": "KKR", "logo": get_local_logo("KKR"), "budget": 64.30, "players": [], "overseas": 2, "total_slots_filled": 12, "color": "#3A225D", "gradient": "linear-gradient(135deg, #3A225D 0%, #5F259F 100%)", "text": "#fff"},
        {"id": 4, "name": "LSG", "logo": get_local_logo("LSG"), "budget": 22.95, "players": [], "overseas": 4, "total_slots_filled": 19, "color": "#0057E0", "gradient": "linear-gradient(135deg, #008ECC 0%, #0057E0 100%)", "text": "#fff"},
        {"id": 5, "name": "MI", "logo": get_local_logo("MI"), "budget": 2.75, "players": [], "overseas": 7, "total_slots_filled": 20, "color": "#004BA0", "gradient": "linear-gradient(135deg, #004BA0 0%, #002D60 100%)", "text": "#fff"},
        {"id": 6, "name": "PBKS", "logo": get_local_logo("PBKS"), "budget": 11.50, "players": [], "overseas": 6, "total_slots_filled": 21, "color": "#DD1F2D", "gradient": "linear-gradient(135deg, #DD1F2D 0%, #8C0D18 100%)", "text": "#fff"},
        {"id": 7, "name": "RR", "logo": get_local_logo("RR"), "budget": 16.05, "players": [], "overseas": 7, "total_slots_filled": 16, "color": "#EA1A85", "gradient": "linear-gradient(135deg, #EA1A85 0%, #254AA5 100%)", "text": "#fff"},
        {"id": 8, "name": "RCB", "logo": get_local_logo("RCB"), "budget": 16.40, "players": [], "overseas": 6, "total_slots_filled": 17, "color": "#EC1C24", "gradient": "linear-gradient(135deg, #2B2B2B 0%, #EC1C24 100%)", "text": "#fff"},
        {"id": 9, "name": "SRH", "logo": get_local_logo("SRH"), "budget": 25.50, "players": [], "overseas": 6, "total_slots_filled": 15, "color": "#F7A721", "gradient": "linear-gradient(135deg, #F7A721 0%, #E9530F 100%)", "text": "#fff"},
    ]

def get_set_number(price):
    if price >= 2.0: return "Set 1 (Marquee)"
    elif price >= 1.5: return "Set 2"
    elif price >= 1.25: return "Set 3"
    elif price >= 1.0: return "Set 4"
    elif price >= 0.75: return "Set 5"
    elif price >= 0.50: return "Set 6"
    elif price >= 0.40: return "Set 7"
    else: return "Set 8 (Uncapped)"

def load_players_from_csv():
    loaded_players = []
    try:
        with open('players.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                country_name = row.get('Country', 'India').strip()
                iso_code = ISO_CODES.get(country_name, "in")
                
                if country_name == "West Indies":
                    flag_url = None
                    flag_emoji = "🌴"
                else:
                    flag_url = f"https://flagcdn.com/w80/{iso_code}.png"
                    flag_emoji = ""
                
                price = float(row['Base Price (Cr)'])
                loaded_players.append({
                    "id": i,
                    "name": row['Name'],
                    "role": row['Role'],
                    "country": country_name,
                    "flag_url": flag_url,
                    "flag_emoji": flag_emoji,
                    "base_price": price,
                    "set_name": get_set_number(price),
                    "status": "Unsold",
                    "type": row.get('Status', 'Capped')
                })
        loaded_players.sort(key=lambda x: x['base_price'], reverse=True)
        print(f"✅ SUCCESS: Loaded {len(loaded_players)} players.")
    except Exception as e:
        print(f"❌ ERROR: Could not load players.csv. Details: {e}")
        return []
    return loaded_players

# --- STATE MANAGEMENT ---
teams = get_initial_teams()
players = load_players_from_csv()
current_player_index = 0
current_bid = 0
current_holder = None
state_id = 1  # Tracks updates

# Stores the last action (Sold/Unsold) and WHEN it happened
last_action = {"data": None, "timestamp": 0} 

def update_state():
    global state_id
    state_id += 1 

# --- ROUTES ---

@app.route('/')
def index():
    return render_template_with_data('full')

@app.route('/admin')
def admin_view():
    return render_template_with_data('admin')

@app.route('/display')
def display_view():
    return render_template_with_data('display')

def render_template_with_data(view_mode):
    global current_player_index, current_bid, current_holder, last_action, state_id
    
    if not players or current_player_index >= len(players):
        return render_template('index.html', game_over=True, teams=teams, view_mode=view_mode, state_id=state_id)
    
    player = players[current_player_index]
    if current_bid == 0:
        current_bid = player['base_price']
        
    # --- POPUP LOGIC ---
    # Show popup ONLY if the action happened less than 5 seconds ago
    popup_data = None
    if last_action["data"] and (time.time() - last_action["timestamp"] < 5):
        popup_data = last_action["data"]
    
    return render_template('index.html', 
                           player=player, 
                           teams=teams, 
                           current_bid=current_bid, 
                           current_holder=current_holder, 
                           game_over=False, 
                           popup=popup_data,
                           view_mode=view_mode,
                           state_id=state_id)

@app.route('/check_update')
def check_update():
    return jsonify({"id": state_id})

@app.route('/bid/<int:team_id>')
def place_bid(team_id):
    global current_bid, current_holder
    increment = 0.10
    new_bid = round(current_bid + increment, 2)
    if teams[team_id]['budget'] >= new_bid:
        current_bid = new_bid
        current_holder = team_id
        update_state()
    return redirect(url_for('admin_view'))

@app.route('/sell')
def sell_player():
    global current_player_index, current_bid, current_holder, last_action
    if current_holder is not None:
        team = teams[current_holder]
        player = players[current_player_index]
        team['budget'] -= current_bid
        team['players'].append(f"{player['name']} ({current_bid} Cr)")
        team['total_slots_filled'] += 1
        if player['country'] != "India":
            team['overseas'] += 1
        player['status'] = "Sold"
        
        # Save Action with Timestamp
        last_action = {
            "data": {
                "type": "sold", 
                "title": f"SOLD TO {team['name']}", 
                "subtitle": f"For ₹{current_bid} Crores", 
                "color": team['color'], 
                "gradient": team['gradient']
            },
            "timestamp": time.time()
        }
        
        current_player_index += 1
        current_bid = 0
        current_holder = None
        update_state()
    return redirect(url_for('admin_view'))

@app.route('/pass')
def pass_player():
    global current_player_index, current_bid, current_holder, last_action
    
    # Save Action with Timestamp
    last_action = {
        "data": {
            "type": "unsold", 
            "title": "UNSOLD", 
            "subtitle": "Player Passed", 
            "color": "#6c757d", 
            "gradient": "linear-gradient(135deg, #6c757d 0%, #343a40 100%)"
        },
        "timestamp": time.time()
    }
    
    current_player_index += 1
    current_bid = 0
    current_holder = None
    update_state()
    return redirect(url_for('admin_view'))

@app.route('/reset')
def reset_auction():
    global current_player_index, current_bid, current_holder, players, teams, last_action
    current_player_index = 0
    current_bid = 0
    current_holder = None
    last_action = {"data": None, "timestamp": 0}
    players = load_players_from_csv()
    teams = get_initial_teams()
    update_state()
    return redirect(url_for('admin_view'))

if __name__ == '__main__':
    app.run(debug=True)