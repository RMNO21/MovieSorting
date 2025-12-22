# 🎬 MORT - movie sorting app — Media Manager

**MORT** is a Python Tkinter‑based media management tool that helps you organize your personal media library. It scans folders for images, videos, and audio files, stores metadata in a local SQLite database, generates thumbnails, and provides a simple UI for browsing and managing your collection.

---

<img width="1202" height="834" alt="MORT Application Interface" src="[https://github.com/user-attachments/assets/aa60e979-c415-4b0e-a60b-b1d7f523cd6b](https://github.com/user-attachments/assets/aa60e979-c415-4b0e-a60b-b1d7f523cd6b)" />

---

## ✨ Features

* **Scan and catalog** media files from one or more folders.
* **Quick search and filtering** by Movies or TV Shows.
* **Organizing tools**: move or copy files into a structured library.
* **Lightweight SQLite database** with minimal local footprint.
* **Cross‑platform support**: Linux, Windows, macOS.

---

## 📦 Prerequisites

To run MORT, you need the following environment set up:

* **Python 3.8+**
* **Tkinter** (Bundled with most Python distributions; Linux users may need a manual install)
* **Pillow (PIL)** (For image handling)
* **ttkthemes** (For improved UI aesthetics)
* **SQLite** (Built into Python)
* **Git** (For cloning the repository)

---

## ⚙️ Installation

### Quick One‑Liner Setup

**Linux/macOS**

```bash
git clone https://github.com/RMNO21/MovieSorting.git && cd MovieSorting && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python3 src/movies.py

```

**Windows PowerShell**

```powershell
git clone https://github.com/RMNO21/MovieSorting.git ; cd MovieSorting; python -m venv venv; .\venv\Scripts\activate; pip install -r requirements.txt; python src\movies.py

```

---

### Detailed Installation by OS

#### 🐧 Linux

```bash
# Install required system packages
sudo apt-get update
sudo apt-get install python3 python3-full python3-venv python3-tk python3-pip git

# Clone the repository
git clone https://github.com/RMNO21/MovieSorting.git
cd MovieSorting

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run the application
python src/movies.py

```

#### 🪟 Windows

```cmd
git clone https://github.com/RMNO21/MovieSorting.git
cd MovieSorting
pip install -r requirements.txt
python src\movies.py

```

#### 🍎 macOS

```bash
brew install python3 git
git clone https://github.com/RMNO21/MovieSorting.git
cd MovieSorting
pip3 install -r requirements.txt
python3 src/movies.py

```

---

## 🚀 Usage

1. Launch the app and use **Add Folder** to select media sources.
2. Click **Refresh** to scan and populate the library.
3. Filter by **Movies** or **TV Shows**.
4. Switch to **Thumbnail View** for a visual library experience.
5. Right‑click items to **Open**, **Reveal in Finder/Explorer**, or **Delete**.

---

## ⚙️ Configuration

* **Settings File:** Stored in `mm_settings.json` in the project root.
* **Thumbnails:** Cached under the `.thumbs_revamp` directory.
* **Database:** A lightweight SQLite file stored locally within the project folder.

---

## 🛠️ Troubleshooting

* **Tkinter not found:**
* *Linux:* Run `sudo apt-get install python3-tk`.
* *Windows/macOS:* Ensure Tkinter was included during your Python installation (usually checked by default).


* **Dependencies missing:**
* Run `pip install -r requirements.txt` again inside your virtual environment.


* **Permission errors:**
* Run with elevated privileges (Admin/Sudo) or adjust folder permissions for the target directories.


* **Thumbnail issues:**
* Delete the `.thumbs_revamp` folder and click **Refresh** to regenerate them.



---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repo.
2. Create a feature branch.
3. Submit a pull request with a clear description.

---

## 📜 License

This project is licensed under the **GNU General Public License v3.0 or later**.
See the LICENSE file for details.

