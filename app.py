from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import plotly.graph_objs as go
import plotly.io as pio


app = Flask(__name__)
app.secret_key = 'supersecretkey'

users = {
    'user_one': 'password',
    'user_two': 'password2'
}


def get_db_connection():
    conn = sqlite3.connect('lac_fullstack_dev.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_lineup_details():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    WITH LineupDetails AS (
        SELECT
            L.game_id,
            L.team_id,
            L.lineup_num,
            L.period,
            MIN(L.time_in) AS time_in,
            MAX(L.time_out) AS time_out,
            MAX(CASE WHEN player_position = 1 THEN L.player_id END) AS player1_id,
            MAX(CASE WHEN player_position = 2 THEN L.player_id END) AS player2_id,
            MAX(CASE WHEN player_position = 3 THEN L.player_id END) AS player3_id,
            MAX(CASE WHEN player_position = 4 THEN L.player_id END) AS player4_id,
            MAX(CASE WHEN player_position = 5 THEN L.player_id END) AS player5_id
        FROM (
            SELECT
                game_id,
                team_id,
                lineup_num,
                period,
                time_in,
                time_out,
                player_id,
                ROW_NUMBER() OVER (PARTITION BY game_id, team_id, lineup_num, period ORDER BY time_in) AS player_position
            FROM lineup
        ) L
        GROUP BY L.game_id, L.team_id, L.lineup_num, L.period
    )
    SELECT
        LD.game_id,
        T.teamName AS team_name,
        LD.lineup_num,
        LD.period,
        LD.time_in,
        LD.time_out,
        (P1.first_name || ' ' || P1.last_name) AS player1_name,
        (P2.first_name || ' ' || P2.last_name) AS player2_name,
        (P3.first_name || ' ' || P3.last_name) AS player3_name,
        (P4.first_name || ' ' || P4.last_name) AS player4_name,
        (P5.first_name || ' ' || P5.last_name) AS player5_name
    FROM LineupDetails LD
    JOIN team T ON LD.team_id = T.team_id
    LEFT JOIN player P1 ON LD.player1_id = P1.player_id
    LEFT JOIN player P2 ON LD.player2_id = P2.player_id
    LEFT JOIN player P3 ON LD.player3_id = P3.player_id
    LEFT JOIN player P4 ON LD.player4_id = P4.player_id
    LEFT JOIN player P5 ON LD.player5_id = P5.player_id
    ORDER BY LD.game_id, LD.team_id, LD.lineup_num, LD.period;
    """
    cursor.execute(query)
    lineup_details = cursor.fetchall()
    conn.close()
    return lineup_details


def fetch_games_by_team(team_name):
    conn = sqlite3.connect('lac_fullstack_dev.db')
    cursor = conn.cursor()
    cursor.execute("""
    SELECT G.game_id, G.game_date, Opp.teamName AS opponent
    FROM game_schedule G
    JOIN team T ON (G.home_id = T.teamId OR G.away_id = T.teamId)
    JOIN team Opp ON (G.home_id = Opp.teamId OR G.away_id = Opp.teamId)
    WHERE T.teamName = ?
    """, (team_name,))
    games = cursor.fetchall()
    conn.close()
    return games


@app.route('/dash', methods=['GET', 'POST'])
def dash():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT teamId, teamName FROM team')
    teams = cursor.fetchall()

    cursor.execute('SELECT player_id, first_name, last_name FROM player')
    players = cursor.fetchall()

    time_labels = []
    time_data = []

    if request.method == 'POST':
        team_id = request.form['team_id']
        player_id = request.form['player_id']

        cursor.execute('''
            SELECT game_id, SUM(time_out - time_in) AS total_time
            FROM lineup
            WHERE player_id = ? AND team_id = ?
            GROUP BY game_id
            ORDER BY game_id
        ''', (player_id, team_id))

        usage_data = cursor.fetchall()

        time_labels = [row['game_id'] for row in usage_data]
        time_data = [row['total_time'] / 60 for row in usage_data]  # Convert to minutes

    conn.close()

    return render_template('dash.html', teams=teams, players=players, time_labels=time_labels, time_data=time_data)





def fetch_lineup_data(game_id):
    conn = sqlite3.connect('lac_fullstack_dev.db')
    cursor = conn.cursor()
    cursor.execute("""
WITH LineupDetails AS (
    SELECT
        game_id,
        team_id,
        lineup_num,
        period,
        MIN(time_in) AS time_in,
        MAX(time_out) AS time_out,
        ROW_NUMBER() OVER (PARTITION BY game_id, team_id, lineup_num, period ORDER BY MIN(time_in)) AS stint_number,
        MAX(CASE WHEN player_position = 1 THEN player_id END) AS player1,
        MAX(CASE WHEN player_position = 2 THEN player_id END) AS player2,
        MAX(CASE WHEN player_position = 3 THEN player_id END) AS player3,
        MAX(CASE WHEN player_position = 4 THEN player_id END) AS player4,
        MAX(CASE WHEN player_position = 5 THEN player_id END) AS player5
    FROM (
        SELECT
            game_id,
            team_id,
            lineup_num,
            period,
            time_in,
            time_out,
            player_id,
            ROW_NUMBER() OVER (PARTITION BY game_id, team_id, lineup_num, period ORDER BY time_in) AS player_position
        FROM lineup
    )
    GROUP BY game_id, team_id, lineup_num, period
),
LineupWithNames AS (
    SELECT
        L.game_id,
        T.teamName || ' (' || T.teamNickname || ')' AS team,
        L.lineup_num,
        L.period,
        L.stint_number,
        ROUND(L.time_in / 60.0, 2) AS time_in_min,
        ROUND(L.time_out / 60.0, 2) AS time_out_min,
        P1.first_name || ' ' || P1.last_name AS player1,
        P2.first_name || ' ' || P2.last_name AS player2,
        P3.first_name || ' ' || P3.last_name AS player3,
        P4.first_name || ' ' || P4.last_name AS player4,
        P5.first_name || ' ' || P5.last_name AS player5
    FROM LineupDetails L
    LEFT JOIN player P1 ON L.player1 = P1.player_id
    LEFT JOIN player P2 ON L.player2 = P2.player_id
    LEFT JOIN player P3 ON L.player3 = P3.player_id
    LEFT JOIN player P4 ON L.player4 = P4.player_id
    LEFT JOIN player P5 ON L.player5 = P5.player_id
    LEFT JOIN Team T ON L.team_id = T.teamId
    WHERE L.game_id = ?
)
SELECT * FROM LineupWithNames
ORDER BY stint_number;

    """, (game_id,))
    data = cursor.fetchall()
    conn.close()
    return data

@app.route('/lineup_dashboard', methods=['GET'])
def lineups():
    conn = sqlite3.connect('lac_fullstack_dev.db')
    cursor = conn.cursor()
    
    selected_team = request.args.get('team')
    selected_game = request.args.get('game')

    cursor.execute("SELECT DISTINCT teamName FROM team")
    teams = [row[0] for row in cursor.fetchall()]

    games = []
    if selected_team:
        games = fetch_games_by_team(selected_team)

    results = []
    if selected_game:
        results = fetch_lineup_data(selected_game)

    conn.close()

    # Plotly graph
    if results:
        traces = []
        for lineup in results:
            trace = go.Scatter(
                x=[lineup[4]],  # Stint number
                y=[lineup[5]],  # Time in minutes
                mode='markers+lines',
                name=f"Stint {lineup[4]}: {lineup[7]} - {lineup[8]}"  # Stint number and players
            )
            traces.append(trace)

        layout = go.Layout(
            title='Lineup Timeseries',
            xaxis={'title': 'Stint Number'},
            yaxis={'title': 'Time (minutes)'},
            legend=dict(title='Lineup Stints')
        )
        
        fig = go.Figure(data=traces, layout=layout)
        plot_div = pio.to_html(fig, full_html=False)
    else:
        plot_div = ""

    return render_template('lineup_dashboard.html', teams=teams, games=games, plot_div=plot_div, selected_team=selected_team, selected_game=selected_game)


@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        if user_id in users and users[user_id] == password:
            session['user_id'] = user_id
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials. Please try again."
    return render_template('login.html')




@app.route('/team_stats')
def team_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Execute the query
    cursor.execute("""
    WITH TeamResults AS (
        SELECT 
            home_id AS team_id,
            COUNT(*) AS games_played,
            SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) AS losses
        FROM game_schedule
        GROUP BY home_id
        
        UNION ALL
        
        SELECT 
            away_id AS team_id,
            COUNT(*) AS games_played,
            SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN away_score < home_score THEN 1 ELSE 0 END) AS losses
        FROM game_schedule
        GROUP BY away_id
    ),
    TeamWinLoss AS (
        SELECT 
            team_id,
            SUM(games_played) AS games_played,
            SUM(wins) AS wins,
            SUM(losses) AS losses
        FROM TeamResults
        GROUP BY team_id
    )
    SELECT 
        teamName AS team_name,
        WL.games_played,
        WL.wins,
        WL.losses,
        ROUND(CAST(WL.wins AS FLOAT) / WL.games_played, 3) AS win_percentage
    FROM TeamWinLoss WL
    JOIN Team T ON WL.team_id = T.teamId
    ORDER BY win_percentage DESC;
    """)

    if team_name:
        cursor.execute(query + " WHERE T.teamName = ?", (team_name,))
    else:
        cursor.execute(query)

    results = cursor.fetchall()
    
    return render_template('lineups.html', results=results, teams=teams, team_name=team_name)
   
 


@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        return render_template('dashboard.html', user_id=user_id)
    else:
        return redirect(url_for('login'))

@app.route('/performance_data')
def performance_data():
    # Replace this with your actual SQL query
    conn = get_db_connection()
    query = """
    SELECT player_name, SUM(points_scored) AS points_scored
    FROM player_performance
    GROUP BY player_name;
    """
    data = conn.execute(query).fetchall()
    conn.close()
    return jsonify([dict(row) for row in data])

# Route to display teams with sorting and pagination
@app.route('/teams')
def display_teams():
    # Get sorting option and page from query parameters
    sort_by = request.args.get('sort_by', 'win_percentage')  # Default sort by win percentage
    page = int(request.args.get('page', 1))  # Default page is 1
    per_page = 10  # Show 10 teams per page
    offset = (page - 1) * per_page
    
    # Validate the sort_by input to prevent SQL injection
    valid_sort_columns = ['games_played', 'wins', 'losses', 'win_percentage']
    if sort_by not in valid_sort_columns:
        sort_by = 'win_percentage'
    
    # Connect to database
    conn = sqlite3.connect('lac_fullstack_dev.db')
    cursor = conn.cursor()

    # Execute the query with sorting and pagination
    query = f"""
    WITH TeamResults AS (
        SELECT 
            home_id AS team_id,
            COUNT(*) AS games_played,
            SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) AS losses
        FROM game_schedule
        GROUP BY home_id
        
        UNION ALL
        
        SELECT 
            away_id AS team_id,
            COUNT(*) AS games_played,
            SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN away_score < home_score THEN 1 ELSE 0 END) AS losses
        FROM game_schedule
        GROUP BY away_id
    ),
    TeamWinLoss AS (
        SELECT 
            team_id,
            SUM(games_played) AS games_played,
            SUM(wins) AS wins,
            SUM(losses) AS losses
        FROM TeamResults
        GROUP BY team_id
    )
    SELECT 
        T.teamName AS team_name,
        WL.games_played,
        WL.wins,
        WL.losses,
        ROUND(CAST(WL.wins AS FLOAT) / WL.games_played, 3) AS win_percentage
    FROM TeamWinLoss WL
    JOIN Team T ON WL.team_id = T.teamId
    ORDER BY {sort_by} DESC
    LIMIT {per_page} OFFSET {offset};
    """
    
    cursor.execute(query)
    results = cursor.fetchall()

    # Get the total number of teams for pagination
    cursor.execute("SELECT COUNT(*) FROM Team")
    total_teams = cursor.fetchone()[0]
    total_pages = (total_teams // per_page) + (total_teams % per_page > 0)
    
    cursor.close()
    conn.close()

    return render_template('teams.html', teams=results, total_pages=total_pages, current_page=page, sort_by=sort_by)



# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True)
