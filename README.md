🧠 Overview

CTF-AI is a Python-based capture-the-flag (CTF) style game that uses adversarial search techniques to power its AI. Designed both as an educational project and a simple interactive game, it demonstrates basic AI decision making in a turn-based or strategic environment.

🚀 Features

Python implementation of an adversarial search agent.

Simple Pygame-powered interface (via pygame_view.py).

Modular design separating game logic and AI behavior.

Easily extensible for adding more intelligent agents or game modes.

🧩 Tech Stack

Language: Python

UI: Pygame

AI Logic: Custom adversarial search modules

Platform-agnostic (runs anywhere Python & Pygame are supported)

📦 Installation

1. Clone the repo

git clone https://github.com/shishir-kuet/CTF-AI.git
cd CTF-AI

2. Create & activate a virtual environment (recommended)

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

3. Install dependencies

pip install -r requirements.txt

4. Run the game

python main.py

🧠 How It Works

Core Modules
File	          Purpose
main.py	        Game launcher & entry point
game_state.py	  Logic for the game state transitions
ai.py	          Main AI decision system using adversarial search
fuzzy_ai.py	    Alternate AI logic with fuzzy or heuristic behavior
pygame_view.py	User interface and rendering
config.py	      Game configuration options

The adversarial search engine evaluates possible moves and selects optimal decisions based on game outcomes. This is foundational for turn-based strategy AI.

🕹 Running the Game

Once launched with python main.py:

1.Controls appear following game start.

2.The AI and player alternate actions based on current game logic.

3.Win/loss conditions depend on your specific game scenario.


📁 Recommended Directory Structure
CTF-AI/
├─ ai.py
├─ config.py
├─ fuzzy_ai.py
├─ game_state.py
├─ main.py
├─ pygame_view.py
├─ requirements.txt
├─ README.md
├─ /__pycache__/

🛠 Development
Add a New AI Strategy

1. Create a new file for your agent logic:
my_agent.py

2. Follow the interface in ai.py for move evaluation.

3. Plug into the main loop by importing and choosing it in config.

Contribute

1. Fork the repository

2. Create your feature branch (git checkout -b feature/...)

3. Commit your changes

4. Open a pull request
