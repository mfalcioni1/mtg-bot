# Design Document: Magic: The Gathering Draft Bot MVP

## **Overview**
The Magic: The Gathering (MTG) Draft Bot is a Discord bot designed to manage asynchronous drafts within a Discord server. The MVP focuses on implementing the Rochester Draft format with core functionality for sandbox testing, drafting mechanics, and generating recap files. The bot will be developed in Python and hosted on Google Cloud Platform (GCP).

---

## **MVP Features**
### 1. **Core Functionality**
#### **Draft Signups**
- Command: `/signup`
- Players use this command to register for the draft.
- The bot maintains a list of participants in the order they signed up.

#### **Draft Initialization**
- Command: `/startdraft`
- Parameters:
  - Cube list URL (from Cube Cobra).
  - Number of cards per pack (default: 15).
  - Number of packs (default: 24).
- Bot fetches the Cube Cobra list, shuffles it, and prepares the packs.

#### **Draft Mechanics**
- **Draft Order**:
  - Snake-order drafting sequence based on random order of signed up players.
- **Pack Posting**:
  - Bot creates a pack of cards, fetches images from the Scryfall API, and posts them in the draft channel.
- **Card Selection**:
  - Command: `/pick [card_name]`
  - Validates the pick, removes the card from the pack, and adds it to the player's card pool.
  - Notifies the next drafter and posts the updated pack if needed.

#### **Draft Results**
- Bot stores draft results, including:
  - Player picks.
  - Pack and pick numbers.
  - Cards available at each pick.
- Generates a recap file (HTML or PDF) upon completion.

### 2. **Sandbox Mode**
- Allows testing without permanent records.
- Useful for debugging and learning the bot's functionality.

### 3. **Draft Recap File**
- Generates a shareable draft recap file in HTML or PDF format.
- Includes:
  - Draft summary.
  - Player picks.
  - Pack composition at each pick.

---

## **Technical Architecture**
### **Data Management**
- **Firestore**:
  - Store draft metadata, player pools, pack contents, and pick history.
  - Real-time updates for managing asynchronous drafts.
- **Google Cloud Storage**:
  - Store generated recap files.

### **Bot Implementation**
- **Framework**: `discord.py`
- **Commands**:
  - `/signup` to register players.
  - `/startdraft` to initialize the draft.
  - `/pick [card_name]` to select a card.
  - `/viewpool [player_name]` to view player card pools.
  - `/recap` to generate and share the recap file.

### **Image Handling**
- **Scryfall API**:
  - Fetch card images for packs.
  - Cache images temporarily in GCP to reduce latency.

### **Hosting**
- **Google Cloud Run**:
  - Deploy the bot as a serverless application for scalability.
- **Cloud Scheduler**:
  - Optional for periodic health checks.

---

## **Development Workflow**
### **1. Setup**
- Initialize the Discord bot using `discord.py`.
- Create Firestore database for draft state management.
- Integrate with Cube Cobra and Scryfall APIs.

### **2. Core Features**
#### **Draft Signups**
- Implement `/signup` command to track player registrations.

#### **Draft Initialization**
- Fetch and shuffle the Cube list.
- Generate packs and store them in Firestore.

#### **Draft Mechanics**
- Implement `/pick` command with validation and notifications.
- Automate pack updates and state management.

#### **Sandbox Mode**
- Add a "sandbox" flag to drafts for testing without saving results.

### **3. Recap File Generation**
- Develop a utility to format draft results as HTML or PDF.
- Integrate Google Cloud Storage for file storage and sharing.

### **4. Testing**
- Create unit tests for commands and state transitions.
- Conduct end-to-end testing using sandbox mode.

---

## **Potential Challenges**
1. **State Consistency**
   - Ensure Firestore transactions are atomic to prevent conflicts in asynchronous drafts.
2. **Card Image Fetching**
   - Minimize latency by caching Scryfall API responses.
3. **User Experience in Discord**
   - Use rich embeds to format messages and reduce clutter.

---

## **Future Backlog**
- **Additional Draft Formats**: Standard draft, rotisserie, rarity balancing, grid draft, team draft
- **LLM Interactions**: Draft grades, draft recaps
- **Analytics**: Use databased results to provide insights
- **Smarter Bot Players**: Better bot drafters
- **Gameplay**: Game management (pairings, etc.), record tracking

---

## **Next Steps**
1. Set up Discord bot and basic commands.
2. Implement Firestore integration for draft state management.
3. Build and test the core draft mechanics.
4. Develop sandbox mode and recap file generation.
5. Test the bot extensively before deployment.

