# 🎲 MTG Draft Bot

A Discord bot for running Magic: The Gathering drafts with support for both human and AI players. Specializing in Rochester Draft format, this bot makes remote drafting with your friends as engaging as sitting around a table!

## ✨ Features

### Core Functionality
- 🤖 **AI Players**: Fill empty seats with bot players
- 📊 **Rochester Draft Format**: See all picks in real-time
- 🎯 **Cube Support**: Direct integration with Cube Cobra
- 🔄 **Asynchronous Play**: Draft at your own pace
- 🤝 **Mixed Drafts**: Combine human and bot players seamlessly

### Draft Management
- 📝 **Easy Signup**: Simple commands to join drafts
- 🎮 **Intuitive Interface**: Clear pack displays and pick commands
- 📈 **Real-time Updates**: Track draft progress and player picks
- 🎨 **Color Distribution**: View cube composition and color balance

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Discord Bot Token
- Discord Server with admin privileges

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

3. Set up environment variables (see Environment Variables section)

4. Run the bot:
```bash
python src/bot.py
```

For development/testing:
```bash
python src/bot.py --test
```

## 🎮 Commands

### Draft Setup
- `/signup` - Join the current draft
- `/clear_signup` - Clear all signups (Admin only)
- `/startdraft` - Start a new draft with specified parameters

### Drafting
- `/show_pack` - View the current pack
- `/pick [card_name]` - Make a pick from the current pack

## ⚙️ Environment Variables
Create a `.env` file in the root directory with:

```env
# Discord Configuration
DISCORD_BOT_TOKEN = 'your-discord-bot-token'
TEST_GUILD_ID = 'your-test-server-id'  # Optional, for development

# Google Cloud Configuration (Future Use)
GOOGLE_APPLICATION_CREDENTIALS = "/path/to/service-account-key.json"
GOOGLE_CLOUD_PROJECT = "your-project-id"
GCS_DATA_BUCKET = 'your-gcs-bucket-name'

# API Configuration
SCRYFALL_API_URL = 'https://api.scryfall.com/bulk-data'
```

## 🏗️ Project Structure
```
mtg-draft-bot/
├── src/
│   ├── bot.py           # Main bot implementation
│   ├── cube_parser.py   # Cube Cobra integration
│   ├── draft_bots.py    # AI player implementation
│   └── requirements.txt # Project dependencies
├── llm/
│   ├── design_doc.md    # Design documentation
│   └── status_report.md # Development status
└── README.md
```

## 🎯 Draft Flow
1. Players sign up for draft using `/signup`
2. Admin starts draft with `/startdraft`
3. Bot automatically fills empty seats with AI players
4. Each player (human or bot) takes turns making picks
5. Packs are passed automatically after each pick
6. Draft continues until all packs are drafted

## 🤖 Bot Players
The bot currently supports:
- Random picking strategy
- Automatic turn handling
- Seamless integration with human players

Future bot improvements planned:
- Color preference awareness
- Card synergy recognition
- Draft strategy implementation
- Learning from human draft patterns

## 🛠️ Development Status
Check [status_report.md](llm/status_report.md) for current development status and planned features.

## 🔜 Planned Features
- Scryfall image integration
- Draft analytics and statistics
- Custom bot strategies
- Draft history tracking
- Deck builder integration
- Tournament organization tools

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments
- [Cube Cobra](https://cubecobra.com/) for cube management
- [Scryfall](https://scryfall.com/) for card data (future integration)
- Discord.py team for the amazing framework

## 📞 Support
For support, please open an issue in the GitHub repository or join our Discord server (coming soon).