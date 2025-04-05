# 🎲 MTG Draft Bot

A Discord bot for running Magic: The Gathering drafts with support for both human and AI players. Specializing in Rochester Draft format and V4CB game mode, this bot makes remote drafting and playing with your friends as engaging as sitting around a table!

## ✨ Features

### Core Functionality
- 🤖 **AI Players**: Fill empty seats with bot players using random picking strategy
- 📊 **Rochester Draft Format**: See all picks in real-time with proper snake draft ordering
- 🎯 **Cube Support**: Direct integration with Cube Cobra's CSV endpoint
- 🔄 **Asynchronous Play**: Draft at your own pace
- 🤝 **Mixed Drafts**: Combine human and bot players seamlessly
- 🎮 **V4CB Game Mode**: Full support for V4CB games with banned list management and scoring

### Draft Management
- 📝 **Easy Signup**: Simple commands to join drafts
- 🎮 **Intuitive Interface**: Clear pack displays with pick history
- 📈 **Real-time Updates**: Track draft progress and player picks
- 🎨 **Color Distribution**: View cube composition and color balance
- 🔍 **Card Autocomplete**: Smart card name suggestions when making picks

### V4CB Game Features
- 📋 **Banned List Management**: Add, remove, and view banned cards with pagination
- 🎯 **Card Submission**: Submit and validate 4-card combinations
- 📊 **Score Tracking**: Track and manage player scores
- 🏆 **Winner Management**: Support for multiple winners per round
- 💾 **Persistent Storage**: Game state saved and recovered using Google Cloud Storage

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Discord Bot Token
- Discord Server with admin privileges
- Google Cloud Project with Storage enabled
- Google Cloud Service Account credentials

### Installation
1. Clone the repository:
```bash
git clone https://github.com/yourusername/mtg-draft-bot.git
cd mtg-draft-bot
```

2. Install dependencies:
```bash
pip install -r src/requirements.txt
```

3. Set up environment variables:
```env
# Discord Configuration
DISCORD_BOT_TOKEN = 'your-discord-bot-token'
TEST_GUILD_ID = 'your-test-server-id'  # Optional, for development

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS = "/path/to/service-account-key.json"
GOOGLE_CLOUD_PROJECT = "your-project-id"
```

4. Run the bot:
```bash
python src/bot.py
```

For development/testing:
```bash
python src/bot.py --test
```

## 🎮 Commands

### Draft Commands
- `/signup` - Join the current draft
- `/clear_signup` - Clear all signups (Admin only)
- `/start_draft` - Start a new draft with specified parameters
- `/show_pack` - View the current pack
- `/pick [card_name]` - Make a pick from the current pack
- `/view_pool` - View your drafted cards
- `/quit_draft` - End the current draft (Admin only)

### V4CB Commands
- `/v4cb_start` - Start a new V4CB game
- `/v4cb_submit` - Submit cards for the current round
- `/v4cb_banned` - View the banned list
- `/v4cb_update_banned` - Add cards to the banned list
- `/v4cb_remove_banned_card` - Remove a card from the banned list
- `/v4cb_clear_banned` - Clear the entire banned list
- `/v4cb_reveal` - Reveal all submissions for the current round
- `/v4cb_submit_winner` - Submit winner(s) for the current round
- `/v4cb_score` - View current scores
- `/v4cb_end` - End the current game

## 🏗️ Project Structure
```
mtg-draft-bot/
├── src/
│   ├── bot.py           # Main bot implementation
│   ├── cube_parser.py   # Cube Cobra integration
│   ├── draft_bots.py    # AI player implementation
│   ├── draft.py         # Rochester draft logic
│   ├── pack_display.py  # Pack display system
│   ├── v4cb.py         # V4CB game implementation
│   ├── storage_manager.py # Cloud storage integration
│   └── requirements.txt # Project dependencies
├── llm/
│   ├── design_doc.md    # Design documentation
│   └── status_report.md # Development status
└── README.md
```

## 🛠️ Development Status
- ✅ Core draft functionality complete
- ✅ V4CB game implementation complete
- ✅ Cloud storage integration complete
- ✅ Proper deployment infrastructure
- ✅ Command management system
- ✅ Pack display system
- 🚧 Planned improvements for analytics and statistics
- 🚧 Deck history tracking for V4CB games

For detailed development status, see [status_report.md](llm/status_report.md).

## 📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments
- [Cube Cobra](https://cubecobra.com/) for cube management
- [Discord.py](https://discordpy.readthedocs.io/) for the Discord API wrapper

## 📞 Support
For support, please open an issue in the GitHub repository or join our Discord server (coming soon).