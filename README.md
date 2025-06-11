# Twisight

Twisight is a Flask application that visualizes Twitter topics and helps you keep track of trending keywords. The app uses Tweepy to query the Twitter API and renders interactive charts with Chart.js. Users can connect a Phantom wallet and earn *Retro Points* each time they perform a search.

## Features

- **Tweet Search** - Fetches daily tweet counts for a keyword and stores the result as a CSV file under `data/`.
- **Interactive Charts** - Line, bar and doughnut charts built with Chart.js for visualizing keyword performance.
- **Search Suggestions** - Offers popular suggestions based on previous searches.
- **Wallet Integration** - Connect a Solana Phantom wallet to unlock search capabilities and accumulate Retro Points.
- **History and Statistics** - Keeps a log of searches in `search_history.csv` and counts the most recent searches in `recent_searches.csv`.

## Installation

1. Ensure Python 3 is installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root and define your Twitter bearer token:
   ```
   BEARER_TOKEN=<your token>
   ```
4. Run the application:
   ```bash
   python app.py
   ```
5. Open `http://localhost:5000` in your browser.

Wallet addresses and point totals are stored under `account-list/`. Search results are saved within the `data/` directory.

