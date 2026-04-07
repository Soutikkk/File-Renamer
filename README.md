# 📁 Batch File Renamer

A sleek, intuitive, and modern web application built with **Python Flask** to seamlessly perform batch file renaming across your directories. It guarantees safe bulk edits, live previews, and easy undo operations, enclosed in a premium dark-themed "glassmorphism" user interface.

## 🚀 Features
- **Live Previews**: See what your files will look like exactly before confirming and applying any changes.
- **Dynamic Renaming Modes**:
  - Add automated prefixes or suffixes.
  - Search and replace specific text strings.
  - Delete exact text from filenames.
  - Apply automated sequential numbering (e.g., `_001`, `_002`).
- **One-Click Undo**: Complete history management! Made a mistake? Revert your previous bulk changes swiftly.
- **Smart Extension Filter**: Show and edit only files matching specific extensions (e.g., `.jpg`, `.mp4`).
- **Safety First**: Active existence-checking and optional file-overwrite permissions avoid accidental data loss.

## 🛠️ Built With
- **Backend**: Python 3.x, Flask framework
- **Frontend**: Custom HTML5, Vanilla CSS3 (with CSS backdrop-filters), and Vanilla ES6 JavaScript (Fetch API)
- **Design Elements**: Custom scrollbars, modal overlays, dynamic CSS toast notifications, and Google Fonts (`Outfit`).

## 📦 Getting Started Locally

### Prerequisites
Make sure you have **Python 3.8+** installed on your system.

### 1. Clone the repository
```bash
git clone https://github.com/Soutikkk/File-Renamer.git
cd File-Renamer
```

### 2. Set up a virtual environment (Recommended)
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install Flask
```

### 4. Run the application
```bash
python app.py
```
Open up your web browser and navigate to `http://127.0.0.1:5000` to start renaming your files!

---
*Created with meticulous attention to detail and modern web aesthetics.*
