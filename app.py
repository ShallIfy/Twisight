# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import tweepy
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io
import base64
import csv
import urllib.parse
import logging
import json
import math  # For pagination

# Load .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Menggunakan os.urandom(24) untuk SECRET_KEY

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get Bearer Token from .env
bearer_token = os.getenv("BEARER_TOKEN")
if not bearer_token:
    logger.error("Bearer Token tidak ditemukan di file .env.")
    raise EnvironmentError("[ERROR] Bearer Token tidak ditemukan di file .env. Silakan periksa konfigurasi Anda.")

# Authenticate Tweepy client
try:
    client = tweepy.Client(bearer_token=bearer_token)
    logger.debug("Tweepy client berhasil diautentikasi.")
except Exception as e:
    logger.error(f"Gagal mengautentikasi Tweepy client: {e}")
    raise

# File paths untuk penyimpanan CSV dan JSON
RECENT_SEARCHES_FILE = "recent_searches.csv"
HISTORY_FILE = "search_history.csv"
DATA_DIR = "data"
LAST_REFRESH_FILE = "last_refresh.json"
WALLET_FILE = "account-list/wallet.json"
POINTS_FILE = "account-list/points.json"

# Ensure CSV dan direktori data ada
def initialize_storage():
    if not os.path.exists(RECENT_SEARCHES_FILE):
        with open(RECENT_SEARCHES_FILE, "w", newline="", encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Query", "Count"])
        logger.debug(f"Created {RECENT_SEARCHES_FILE}.")

    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", newline="", encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Query", "Timestamp"])
        logger.debug(f"Created {HISTORY_FILE}.")

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logger.debug(f"Created data directory at {DATA_DIR}.")

    if not os.path.exists(LAST_REFRESH_FILE):
        with open(LAST_REFRESH_FILE, "w", encoding='utf-8') as file:
            json.dump({"last_refresh": {}}, file)
        logger.debug(f"Created {LAST_REFRESH_FILE}.")

    if not os.path.exists("account-list"):
        os.makedirs("account-list")
        logger.debug("Created account-list directory.")

    if not os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, "w", encoding='utf-8') as file:
            json.dump([], file)
        logger.debug(f"Created {WALLET_FILE}.")

    if not os.path.exists(POINTS_FILE):
        with open(POINTS_FILE, "w", encoding='utf-8') as file:
            json.dump({}, file)
        logger.debug(f"Created {POINTS_FILE}.")

initialize_storage()

# Load last refresh times
def load_last_refresh_times():
    try:
        with open(LAST_REFRESH_FILE, "r", encoding='utf-8') as file:
            data = json.load(file)
            last_refresh = data.get("last_refresh", {})
            # Convert string timestamps to datetime objects
            for query in last_refresh:
                last_refresh[query] = datetime.strptime(last_refresh[query], "%Y-%m-%dT%H:%M:%S")
            return last_refresh
    except Exception as e:
        logger.error(f"Can't Fetch Last Refresh Time: {e}")
        return {}

# Save last refresh times
def save_last_refresh_times(last_refresh):
    try:
        # Convert datetime objects to strings
        last_refresh_str = {query: dt.strftime("%Y-%m-%dT%H:%M:%S") for query, dt in last_refresh.items()}
        with open(LAST_REFRESH_FILE, "w", encoding='utf-8') as file:
            json.dump({"last_refresh": last_refresh_str}, file)
        logger.debug("Last Refresh Can't be Fetched")
    except Exception as e:
        logger.error(f"Last Refresh Failed: {e}")

# Update recent searches in CSV
def update_recent_searches(query):
    data = {}
    if os.path.exists(RECENT_SEARCHES_FILE):
        with open(RECENT_SEARCHES_FILE, "r", encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2 and row[1].isdigit():
                    data[row[0]] = int(row[1])

    data[query] = data.get(query, 0) + 1
    logger.debug(f"Updating recent searches with query: {query} (Count: {data[query]})")

    with open(RECENT_SEARCHES_FILE, "w", newline="", encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Query", "Count"])
        for key, value in data.items():
            writer.writerow([key, value])
    logger.debug("Recent searches berhasil diperbarui.")

# Append to search history CSV
def append_to_history(query):
    with open(HISTORY_FILE, "a", newline="", encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([query, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")])
    logger.debug(f"Appended to search history: {query} at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

# Function to get recent tweets count
def get_recent_tweets_count(query, granularity="day"):
    try:
        response = client.get_recent_tweets_count(query, granularity=granularity)
        logger.debug(f"Fetched tweet counts for query '{query}': {response.data}")
        return response.data if response.data else []
    except tweepy.TweepyException as e:
        flash(f"[ERROR] Failed to Fetch Twitter Data: {e}", "error")
        logger.error(f"Failed to Fetch Twitter Data: {e}")
        return []

# Save tweet counts data for a query
def save_query_data(query, data):
    # Replace characters that are problematic for filenames
    safe_query = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in query)
    filename = os.path.join(DATA_DIR, f"{safe_query}.csv")
    with open(filename, "w", newline="", encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["start", "tweet_count"])
        for record in data:
            writer.writerow([record["start"], record["tweet_count"]])
    logger.debug(f"Saved tweet counts data to {filename}.")

# Helper function to calculate human-readable time difference
def human_readable_time_diff(timestamp):
    now = datetime.utcnow()
    diff = now - timestamp
    seconds = int(diff.total_seconds())
    minutes = seconds // 60
    hours = minutes // 60
    days = diff.days
    weeks = days // 7

    if seconds < 60:
        return f"{seconds}s"
    elif minutes < 60:
        return f"{minutes}m{seconds % 60}s" if seconds % 60 else f"{minutes}m"
    elif hours < 24:
        return f"{hours}h{minutes % 60}m" if minutes % 60 else f"{hours}h"
    else:
        return f"{days}d"

# Function to retrieve last search time for each query
def get_last_search_times():
    last_search_times = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding='utf-8') as file:
            reader = csv.DictReader(file)
            # Verify if required headers are present
            if 'Query' not in reader.fieldnames or 'Timestamp' not in reader.fieldnames:
                logger.error(f"CSV headers missing in {HISTORY_FILE}. Expected 'Query' and 'Timestamp'. Found: {reader.fieldnames}")
                return last_search_times  # Return empty dict or handle sesuai kebutuhan

            for row in reader:
                query = row.get('Query')
                timestamp_str = row.get('Timestamp')

                if not query or not timestamp_str:
                    logger.warning(f"Missing 'Query' or 'Timestamp' di baris: {row}")
                    continue

                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    if query not in last_search_times or timestamp > last_search_times[query]:
                        last_search_times[query] = timestamp
                except ValueError as e:
                    logger.error(f"Invalid timestamp format for query '{query}': {timestamp_str}")
    return last_search_times

# Function to plot tweet counts with transparent background
def plot_tweet_counts(data, query):
    try:
        # Format tanggal menjadi DD-MM-YY
        dates = [datetime.strptime(record["start"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d-%m-%y") for record in data]
        tweet_counts = [int(record["tweet_count"]) for record in data]
        logger.debug(f"Plotting tweet counts for query '{query}'.")
    except (KeyError, ValueError) as e:
        flash(f"[ERROR] Data Format is not Valid: {e}", "error")
        logger.error(f"Invalid data format for plotting: {e}")
        return None

    # Generate plot
    plt.figure(figsize=(10, 6))
    plt.plot(dates, tweet_counts, marker="o", linestyle="-", linewidth=2, color="lime")
    plt.title(f"Tweet Analytics for '{query}'", fontsize=14, color="lime", fontweight="bold")
    plt.xlabel("Date", fontsize=12, color="lime")
    plt.ylabel("Tweet Count", fontsize=12, color="lime")
    plt.grid(visible=True, linestyle="--", alpha=0.6)
    plt.xticks(rotation=45, fontsize=10, color="lime")
    plt.yticks(color="lime")
    plt.tight_layout()

    # Set transparent background
    plt.gcf().set_facecolor("none")

    # Save plot to a BytesIO object dengan background transparan
    img = io.BytesIO()
    plt.savefig(img, format="png", transparent=True)
    img.seek(0)
    plt.close()
    logger.debug("Plot image saved to buffer.")

    # Encode the image to base64 string
    plot_url = base64.b64encode(img.getvalue()).decode()
    logger.debug("Plot image encoded to base64.")
    return plot_url

# Route to serve raw data for a query
@app.route("/data/<path:query>")
def data_query(query):
    decoded_query = urllib.parse.unquote(query)
    logger.debug(f"Received data request for query: {decoded_query}")

    # Replace characters that are problematic for filenames
    safe_query = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in decoded_query)
    filename = os.path.join(DATA_DIR, f"{safe_query}.csv")
    if not os.path.exists(filename):
        logger.warning(f"No data found for query '{decoded_query}'.")
        return jsonify({"error": f"No data found for query '{decoded_query}'."}), 404

    data = []
    try:
        with open(filename, "r", encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                data.append(row)
        logger.debug(f"Read {len(data)} records from {filename}.")
    except Exception as e:
        logger.error(f"Failed to read query '{decoded_query}': {e}")
        return jsonify({"error": f"Gagal membaca data untuk query '{decoded_query}': {e}"}), 500

    return jsonify({"data": data})

# Route to fetch and return plot for a given query
@app.route("/plot/<path:query>")
def plot_query(query):
    # Decode the query in case it was URL-encoded
    decoded_query = urllib.parse.unquote(query)
    logger.debug(f"Received plot request for query: {decoded_query}")

    # Replace characters that are problematic for filenames
    safe_query = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in decoded_query)
    filename = os.path.join(DATA_DIR, f"{safe_query}.csv")
    if not os.path.exists(filename):
        logger.warning(f"No data found for query '{decoded_query}'.")
        return jsonify({"error": f"No data found for query '{decoded_query}'."}), 404

    data = []
    try:
        with open(filename, "r", encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                data.append(row)
        logger.debug(f"Read {len(data)} records from {filename}.")
    except Exception as e:
        logger.error(f"Gagal membaca data untuk query '{decoded_query}': {e}")
        return jsonify({"error": f"Gagal membaca data untuk query '{decoded_query}': {e}"}), 500

    plot_url = plot_tweet_counts(data, decoded_query)
    if plot_url:
        logger.debug("Plot generated successfully.")
        return jsonify({"plot_url": plot_url})
    else:
        logger.error("Failed to generate plot.")
        return jsonify({"error": "Failed to generate plot."}), 500

# Function to get counts of queries for the last two days based on tweet_count
def get_tweet_counts_last_two_days(query):
    safe_query = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in query)
    filename = os.path.join(DATA_DIR, f"{safe_query}.csv")
    if not os.path.exists(filename):
        logger.warning(f"No data file found for query '{query}'.")
        return 0, 0

    try:
        with open(filename, "r", encoding='utf-8') as file:
            reader = csv.DictReader(file)
            data = list(reader)
    except Exception as e:
        logger.error(f"Error reading data file for query '{query}': {e}")
        return 0, 0

    # Sort data by date
    data_sorted = sorted(data, key=lambda x: x['start'])

    # Extract dates and tweet_counts
    dates = [datetime.strptime(row['start'], "%Y-%m-%dT%H:%M:%S.%fZ").date() for row in data_sorted]
    tweet_counts = [int(row['tweet_count']) for row in data_sorted]

    if not dates or not tweet_counts:
        return 0, 0

    today = datetime.utcnow().date()
    day1 = today - timedelta(days=1)
    day2 = today - timedelta(days=2)

    # Initialize counts
    count_day1 = 0
    count_day2 = 0

    # Find tweet counts for day1 and day2
    for date, count in zip(dates, tweet_counts):
        if date == day1:
            count_day1 = count
        elif date == day2:
            count_day2 = count

    return count_day1, count_day2

# Route to handle wallet connections
@app.route("/connect_wallet", methods=["POST"])
def connect_wallet():
    data = request.get_json()
    wallet_address = data.get("wallet_address")
    if not wallet_address:
        logger.error("No wallet address provided in connect_wallet request.")
        return jsonify({"error": "No wallet address provided."}), 400

    # Save to wallet.json
    if os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, "r", encoding='utf-8') as f:
            wallets = json.load(f)
    else:
        wallets = []

    # Check if wallet already exists
    if not any(w['address'] == wallet_address for w in wallets):
        wallets.append({
            "address": wallet_address,
            "connect_date": datetime.utcnow().isoformat()
        })
        with open(WALLET_FILE, "w", encoding='utf-8') as f:
            json.dump(wallets, f, indent=4)
        logger.debug(f"New wallet connected and saved: {wallet_address}")

    # Store in session
    session['wallet_address'] = wallet_address

    # Initialize points if not present
    if os.path.exists(POINTS_FILE):
        with open(POINTS_FILE, "r", encoding='utf-8') as f:
            points = json.load(f)
    else:
        points = {}

    if wallet_address not in points:
        points[wallet_address] = 0
        with open(POINTS_FILE, "w", encoding='utf-8') as f:
            json.dump(points, f, indent=4)
        logger.debug(f"Initialized points for new wallet: {wallet_address}")

    return jsonify({"message": "Wallet connected successfully.", "points": points.get(wallet_address, 0)}), 200

# Route to handle wallet disconnections
@app.route("/disconnect_wallet", methods=["POST"])
def disconnect_wallet():
    wallet_address = session.pop('wallet_address', None)
    if wallet_address:
        logger.debug(f"Wallet disconnected: {wallet_address}")
    return jsonify({"message": "Wallet disconnected."}), 200

# Route to handle search suggestions (unchanged)
@app.route("/suggest")
def suggest():
    query = request.args.get('q', '').strip()
    logger.debug(f"Received suggestion request for query: '{query}'")
    if not query:
        return jsonify({"suggestions": []})

    # Read popular searches from recent_searches.csv
    popular_searches = []
    if os.path.exists(RECENT_SEARCHES_FILE):
        with open(RECENT_SEARCHES_FILE, "r", encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2 and row[1].isdigit():
                    popular_searches.append({
                        "query": row[0],
                        "count": int(row[1])  # Total number of searches
                    })

    # Sort all searches globally by count descending
    sorted_popular_searches = sorted(popular_searches, key=lambda x: x['count'], reverse=True)

    # Filter berdasarkan input query, tapi pertahankan peringkat global
    filtered_suggestions = [
        {**search, "rank": rank + 1}  # Assign global rank
        for rank, search in enumerate(sorted_popular_searches)
        if query.lower() in search["query"].lower()
    ]

    # Limit the number of suggestions (e.g., top 10 matches)
    filtered_suggestions = filtered_suggestions[:10]

    logger.debug(f"Returning {len(filtered_suggestions)} suggestions for query '{query}': {filtered_suggestions}")
    return jsonify({"suggestions": filtered_suggestions})

# Combined Route for GET and POST
@app.route("/", methods=["GET", "POST"])
def index():
    # Pagination parameters
    per_page = 10

    if request.method == "POST":
        try:
            # Check if wallet is connected
            if 'wallet_address' not in session:
                logger.debug("Wallet not connected.")
                flash("[ERROR] Please Connect Your Wallet before use the Feature", "error")
                return redirect(url_for("index"))

            query = request.form.get("query")
            logger.debug(f"Received search query: {query}")
            if not query:
                logger.debug("No query provided.")
                flash("[ERROR] Input Queary Needed", "error")
                return redirect(url_for("index"))

            # Fetch Tweet counts
            tweet_counts = get_recent_tweets_count(query)
            if tweet_counts:
                logger.debug("Tweet counts found.")
                # Save the tweet counts data
                save_query_data(query, tweet_counts)

                # Generate plot
                plot_url = plot_tweet_counts(tweet_counts, query)
                if not plot_url:
                    logger.debug("Failed to generate plot.")
                    flash("[ERROR] Gagal menghasilkan plot.", "error")
                    return redirect(url_for("index"))

                # Update recent searches and history
                update_recent_searches(query)
                append_to_history(query)

                # Increment points
                wallet_address = session['wallet_address']
                if os.path.exists(POINTS_FILE):
                    with open(POINTS_FILE, "r", encoding='utf-8') as f:
                        points = json.load(f)
                else:
                    points = {}

                points[wallet_address] = points.get(wallet_address, 0) + 1
                with open(POINTS_FILE, "w", encoding='utf-8') as f:
                    json.dump(points, f, indent=4)
                logger.debug(f"Incremented points for wallet '{wallet_address}' to {points[wallet_address]}.")

                # Read popular searches dari recent_searches.csv
                popular_searches = []
                if os.path.exists(RECENT_SEARCHES_FILE):
                    with open(RECENT_SEARCHES_FILE, "r", encoding='utf-8') as file:
                        reader = csv.reader(file)
                        next(reader)  # Skip header
                        for row in reader:
                            if len(row) >= 2 and row[1].isdigit():
                                popular_searches.append({
                                    "query": row[0],
                                    "count": int(row[1])
                                })

                # Sort Popular Searches by count descending
                sorted_popular_searches = sorted(
                    popular_searches,
                    key=lambda x: x['count'],
                    reverse=True
                )

                # Implement Pagination for Popular Searches
                popular_page = request.args.get('popular_page', 1, type=int)
                popular_total_pages = math.ceil(len(sorted_popular_searches) / per_page) if len(sorted_popular_searches) > 0 else 1

                popular_page = max(1, min(popular_page, popular_total_pages))

                start_popular = (popular_page - 1) * per_page
                end_popular = start_popular + per_page
                paginated_popular_searches = sorted_popular_searches[start_popular:end_popular]

                # Calculate percentage_change and trend for each popular search based on tweet_count
                for search in sorted_popular_searches:
                    query_search = search['query']
                    count_day1, count_day2 = get_tweet_counts_last_two_days(query_search)

                    if count_day2 == 0:
                        percentage_change = 100 if count_day1 > 0 else 0
                    else:
                        percentage_change = ((count_day1 - count_day2) / count_day2) * 100

                    # Determine trend
                    if count_day1 > count_day2:
                        trend = "up"
                    elif count_day1 < count_day2:
                        trend = "down"
                    else:
                        trend = "no_change"

                    search['percentage_change'] = round(percentage_change)
                    search['trend'] = trend

                # Read recent searches dari search_history.csv untuk Recent Searches
                recent_searches = []
                last_search_times = get_last_search_times()
                if os.path.exists(HISTORY_FILE):
                    with open(HISTORY_FILE, "r", encoding='utf-8') as file:
                        reader = csv.DictReader(file)
                        for row in reader:
                            query_entry = row.get('Query')
                            timestamp_str = row.get('Timestamp')
                            if query_entry and timestamp_str:
                                try:
                                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                    if query_entry not in [s['query'] for s in recent_searches]:
                                        recent_searches.append({
                                            "query": query_entry,
                                            "time_since": human_readable_time_diff(timestamp)
                                        })
                                    else:
                                        # Update time_since jika timestamp lebih baru
                                        existing_entry = next((item for item in recent_searches if item["query"] == query_entry), None)
                                        if existing_entry:
                                            existing_timestamp = last_search_times.get(query_entry)
                                            if timestamp > existing_timestamp:
                                                existing_entry["time_since"] = human_readable_time_diff(timestamp)
                                except ValueError:
                                    logger.error(f"Invalid timestamp format for query '{query_entry}': {timestamp_str}")

                # Sort Recent Searches by time since (most recent first)
                sorted_recent_searches = sorted(
                    recent_searches,
                    key=lambda x: last_search_times.get(x["query"], datetime.min),
                    reverse=True
                )

                # Implement Pagination for Recent Searches
                recent_page = request.args.get('recent_page', 1, type=int)
                recent_total_pages = math.ceil(len(sorted_recent_searches) / per_page) if len(sorted_recent_searches) > 0 else 1

                recent_page = max(1, min(recent_page, recent_total_pages))

                start_recent = (recent_page - 1) * per_page
                end_recent = start_recent + per_page
                paginated_recent_searches = sorted_recent_searches[start_recent:end_recent]

                # Retrieve updated points setelah increment
                points = points.get(wallet_address, 0)

                logger.debug(f"Rendering index.html with query='{query}', points={points}")
                return render_template(
                    "index.html",
                    query=query,
                    data=tweet_counts,
                    plot_url=plot_url,
                    popular_searches=paginated_popular_searches,  # Paginated popular searches
                    popular_page=popular_page,
                    popular_total_pages=popular_total_pages,
                    points=points,  # Pass points ke template
                    is_search=True  # Flag untuk menunjukkan bahwa pencarian telah dilakukan
                )
            else:
                logger.debug("No tweet counts found.")
                flash("[ERROR] No Tweet Count for that query.", "error")
                return redirect(url_for("index"))
        except Exception as e:
            logger.error(f"Exception in index route: {e}")
            flash("[ERROR] Terjadi kesalahan saat memproses permintaan Anda.", "error")
            return redirect(url_for("index"))
    else:
        try:
            logger.debug("Handling GET request.")

            # Read popular searches dari recent_searches.csv
            popular_searches = []
            if os.path.exists(RECENT_SEARCHES_FILE):
                with open(RECENT_SEARCHES_FILE, "r", encoding='utf-8') as file:
                    reader = csv.reader(file)
                    next(reader)  # Skip header
                    for row in reader:
                        if len(row) >= 2 and row[1].isdigit():
                            popular_searches.append({
                                "query": row[0],
                                "count": int(row[1])
                            })

            # Sort Popular Searches by count descending
            sorted_popular_searches = sorted(popular_searches, key=lambda x: x['count'], reverse=True)

            # Implement Pagination for Popular Searches
            popular_page = request.args.get('popular_page', 1, type=int)
            popular_total_pages = math.ceil(len(sorted_popular_searches) / per_page) if len(sorted_popular_searches) > 0 else 1

            popular_page = max(1, min(popular_page, popular_total_pages))

            start_popular = (popular_page - 1) * per_page
            end_popular = start_popular + per_page
            paginated_popular_searches = sorted_popular_searches[start_popular:end_popular]

            # Calculate percentage_change and trend for each popular search based on tweet_count
            for search in sorted_popular_searches:
                query_search = search['query']
                count_day1, count_day2 = get_tweet_counts_last_two_days(query_search)

                if count_day2 == 0:
                    percentage_change = 100 if count_day1 > 0 else 0
                else:
                    percentage_change = ((count_day1 - count_day2) / count_day2) * 100

                # Determine trend
                if count_day1 > count_day2:
                    trend = "up"
                elif count_day1 < count_day2:
                    trend = "down"
                else:
                    trend = "no_change"

                search['percentage_change'] = round(percentage_change)
                search['trend'] = trend

            # Read recent searches dari search_history.csv untuk Recent Searches
            recent_searches = []
            last_search_times = get_last_search_times()
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        query_entry = row.get('Query')
                        timestamp_str = row.get('Timestamp')
                        if query_entry and timestamp_str:
                            try:
                                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                if query_entry not in [s['query'] for s in recent_searches]:
                                    recent_searches.append({
                                        "query": query_entry,
                                        "time_since": human_readable_time_diff(timestamp)
                                    })
                                else:
                                    # Update time_since jika timestamp lebih baru
                                    existing_entry = next((item for item in recent_searches if item["query"] == query_entry), None)
                                    if existing_entry:
                                        existing_timestamp = last_search_times.get(query_entry)
                                        if timestamp > existing_timestamp:
                                            existing_entry["time_since"] = human_readable_time_diff(timestamp)
                            except ValueError:
                                logger.error(f"Invalid timestamp format for query '{query_entry}': {timestamp_str}")

            # Sort Recent Searches by time since (most recent first)
            sorted_recent_searches = sorted(
                recent_searches,
                key=lambda x: last_search_times.get(x["query"], datetime.min),
                reverse=True
            )

            # Implement Pagination for Recent Searches
            recent_page = request.args.get('recent_page', 1, type=int)
            recent_total_pages = math.ceil(len(sorted_recent_searches) / per_page) if len(sorted_recent_searches) > 0 else 1

            recent_page = max(1, min(recent_page, recent_total_pages))

            start_recent = (recent_page - 1) * per_page
            end_recent = start_recent + per_page
            paginated_recent_searches = sorted_recent_searches[start_recent:end_recent]

            # If wallet is connected, retrieve points
            wallet_address = session.get('wallet_address', None)
            points = 0
            if wallet_address:
                if os.path.exists(POINTS_FILE):
                    with open(POINTS_FILE, "r", encoding='utf-8') as f:
                        points_data = json.load(f)
                        points = points_data.get(wallet_address, 0)

            logger.debug("Rendering index.html dengan recent dan popular searches.")
            return render_template(
                "index.html",
                popular_searches=paginated_popular_searches,  # Paginated popular searches
                popular_page=popular_page,
                popular_total_pages=popular_total_pages,
                points=points,  # Pass points ke template
                is_search=False  # Flag untuk menunjukkan initial page load
            )
        except Exception as e:
            logger.error(f"Exception in GET index route: {e}")
            flash("[ERROR] Terjadi kesalahan saat memuat halaman.", "error")
            return redirect(url_for("index"))

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
