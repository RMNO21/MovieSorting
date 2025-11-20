# 🎬 MORT - movie sorting app — Media Manager

**MORT** is a Python Tkinter‑based media management tool that helps you organize your personal media library. It scans folders for images, videos, and audio files, stores metadata in a local SQLite database, generates thumbnails, and provides a simple UI for browsing and managing your collection.

---

## ✨ Features

- **Scan and catalog** media files from one or more folders  
- **Quick search and filtering** by Movies or TV Shows  
- **Organizing tools**: move or copy files into a structured library  
- **Lightweight SQLite database** with minimal local footprint  
- **Cross‑platform support**: Linux, Windows, macOS  

---

## 📦 Prerequisites

- **Python 3.8+**  
- **Tkinter** (bundled with most Python distributions, may need manual install on some systems)  
- **Pillow (PIL)** for image handling  
- **ttkthemes** for improved UI aesthetics  
- **SQLite** (built into Python)  
- **Git** for cloning the repository  

---

## ⚙️ Installation

### Quick One‑Liner Setup

**Linux/macOS**

```bash
git clone https://github.com/RMNO21/Mort.git && cd Mort && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python3 src/movies.py
```

**Windows PowerShell**

```powershell
git clone https://github.com/RMNO21/Mort.git; cd Mort; python -m venv venv; .\venv\Scripts\activate; pip install -r requirements.txt; python src\movies.py
```

---

### Linux

```bash
# Install required system packages
sudo apt-get update
sudo apt-get install python3 python3-full python3-venv python3-tk python3-pip git

# Clone the repository
git clone https://github.com/RMNO21/Mort.git
cd Mort

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run the application
python src/movies.py
```

---

### Windows

```cmd
git clone https://github.com/RMNO21/Mort.git
cd Mort
pip install -r requirements.txt
python src\movies.py
```

---

### macOS

```bash
brew install python3 git
git clone https://github.com/RMNO21/Mort.git
cd Mort
pip3 install -r requirements.txt
python3 src/movies.py
```

---

## 🚀 Usage

- Launch the app and use **Add Folder** to select media sources  
- Click **Refresh** to scan and populate the library  
- Filter by **Movies** or **TV Shows**  
- Switch to **Thumbnail View** for a visual library  
- Right‑click items to **Open**, **Reveal in Finder/Explorer**, or **Delete**  

---

## ⚙️ Configuration

- Settings are stored in **`mm_settings.json`** in the project root  
- Thumbnails are cached under **`.thumbs_revamp`**  
- Database is lightweight and stored locally  

---

## 🛠️ Troubleshooting

- **Tkinter not found** → Install `python3-tk` (Linux) or ensure Tkinter is included in your Python distribution  
- **Dependencies missing** → Run `pip install -r requirements.txt` again  
- **Permission errors** → Run with elevated privileges or adjust folder permissions  
- **Thumbnail issues** → Delete `.thumbs_revamp` and refresh  

---

## 🤝 Contributing

Contributions are welcome!  
- Fork the repo  
- Create a feature branch  
- Submit a pull request with a clear description  

---

## 📜 License

This project is licensed under the **GNU General Public License v3.0 or later**.  
See the LICENSE file for details.  
