# Gooky Bot 🤖

A feature-rich, all-purpose Discord bot built with Python and discord.py. Gooky is designed with a modular cog-based architecture and a robust manager pattern for handling business logic, making it scalable and easy to maintain.

---

## ✨ Key Features

Gooky comes packed with features to manage and engage a Discord community:

#### 🏆 Advanced Leveling System
* **XP Sources:** Earn XP for sending messages, adding reactions, participating in voice channels, and even streaming with Discord's "Go Live" feature.
* **Bonus XP:** Server admins can configure specific "engagement channels" (e.g., `#art`, `#memes`) to grant bonus XP.
* **Competitive Commands:**
    * `/level`: Check your own or another member's level and XP progress.
    * `/rank`: See your exact position on the server's leaderboard.
    * `/leaderboard`: A paginated, interactive leaderboard showing the top users.

#### 🛡️ Moderation Suite
* A full set of moderation tools for server administrators:
    * `/kick`: Kick a member from the server.
    * `/ban`: Ban a member from the server.
    * `/timeout`: Mute a member for a specified duration (e.g., `10m`, `1h`, `3d`).
    * `/clear`: Bulk delete messages from a channel.

#### 🛠️ Admin & Utility Commands
* `/setprefix`: Set a custom command prefix for your server.
* `/embed`: A powerful command for admins to create and send custom embeds for announcements.
* `/say`: Make the bot send a plain text message to a channel.
* `/wallpaper`: A fun utility that scrapes a Steam Workshop link to display its preview image in a large format.
* `/sync`: (Bot Owner Only) Manually sync application commands to Discord.

#### 👋 General Features
* **Custom Help Command:** An interactive `/help` command that lists all available commands and their usage.
* **Welcome System:** Automatically sends a welcome DM to new members when they join a server.
* **Guild Onboarding:** Sends a helpful DM to the server owner and admins when the bot is first added to their server.

---

## 💻 Tech Stack

This project leverages modern and efficient technologies to ensure reliability and performance.

* **Language:** Python
* **Core Library:** `discord.py`
* **Database:** PostgreSQL
* **ORM & Migrations:** `SQLAlchemy` (for object-relational mapping) and `Alembic` (for database schema migrations).
* **Project & Dependency Management:** `uv`
* **Web Scraping:** `aiohttp` (for async HTTP requests) and `BeautifulSoup4` (for HTML parsing).
* **Logging:** `colorlog` for development and `RotatingFileHandler` for production log files.

---

## 📂 Project Structure

The bot is organized into a clean, cog-based architecture:

* `src/gookybot/cogs/`: Contains the command definitions, listeners, and UI components, separated by functionality (e.g., `leveling.py`, `moderation.py`).
* `src/gookybot/features/`: Contains the business logic in "Manager" classes (e.g., `LevelingManager`), keeping the cogs clean and focused on Discord interactions.
* `src/gookybot/database/`: Contains all database-related code, including the connection, models, and Alembic migrations.



---

## 🚀 Getting Started

To run this bot locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/gookybot.git](https://github.com/your-username/gookybot.git)
    cd gookybot
    ```

2.  **Create a `.env` file** in the root directory and add your secrets:
    ```env
    # .env
    DISCORD_TOKEN="your_bot_token_here"
    DATABASE_URL="postgresql+asyncpg://user:password@localhost/gookybot_db"
    ```

3.  **Install dependencies and sync the environment:**
    ```bash
    uv sync
    ```

4.  **Run database migrations:**
    ```bash
    alembic upgrade head
    ```

5.  **Run the bot:**
    ```bash
    uv run bot
    ```