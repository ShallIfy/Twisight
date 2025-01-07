#!/bin/bash

# Membuat subdirektori assets, public/css, public/js
mkdir -p assets/images
mkdir -p assets/sounds
mkdir -p public/css
mkdir -p public/js

# Membuat file-file utama
touch public/js/game.js
touch public/js/web3.js
touch public/css/style.css
touch public/index.php
touch leaderboard.php
touch profile.php
touch save_score.php
touch db.php
touch README.md

# Menambahkan konten default ke README.md
echo "# Flappy-SQRCAT Game Project" >> README.md
echo "Project ini adalah game seperti Flappy Bird yang terintegrasi dengan Web3, menggunakan PHP dan MySQL untuk penyimpanan data, serta memiliki fitur Leaderboard dan Profile Editor." >> README.md

echo "Struktur direktori berhasil dibuat."
