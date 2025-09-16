# Prompt Manager

A simple, yet powerful, desktop application built with PyQt6 for Linux to manage and quickly access frequently used text prompts. This application allows users to create, modify, and delete prompt templates, associating each with a button for one-click copying to the clipboard. It also features system tray integration for easy access and background operation.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Features

*   **Prompt Management:** Create, edit, and delete text prompts directly within the application.
*   **Dynamic Buttons:** Each saved prompt is represented by a dynamically created button.
*   **Clipboard Integration:** Click a prompt button to instantly copy its content to the clipboard.
*   **Persistent Storage:** Prompts are saved locally in a `prompts.json` file within a dedicated hidden directory in the user's home folder.
*   **Backup Mechanism:** Automatic backup (`prompts.json.old.bak`) is created before each save to prevent data loss.
*   **System Tray Integration:**
    *   Minimize the application to the system tray instead of closing it.
    *   Restore the window with a double-click on the tray icon.
    *   Access saved prompts directly from the tray icon's context menu to copy their content to the clipboard.
    *   Option to quit the application completely from the tray menu.
*   **Dynamic Layout:** Prompt buttons in the "Saved Prompts" area automatically wrap to the next line based on window width, without horizontal scrollbars.
*   **User Feedback:** Status bar messages for non-critical information and `QMessageBox` for errors and critical warnings.
*   **Customizable Icon:** Supports a custom `app_icon_32.png` for the application window and system tray.

## Installation

### Prerequisites

*   Python 3.x
*   pip (Python package installer)

### Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/wisec/Prompt_Manager.git
    cd Prompt_Manager
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate # On Windows, use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install PyQt6
    ```
    *   `PyQt6`: The GUI toolkit.
    or debian/ubuntu
    ```bash 
    sudo apt install python3-pyqt6
    ```
## Usage

1.  **Run the application:**
    ```bash
    python3 prompt_manager.py
    ```

2.  **Create or Edit a Prompt:**
    *   Enter a **Prompt Title** in the input box on the left. This will be the label for the button.
    *   Type or paste the **Prompt Content** into the larger text area.
    *   Click **"Save Prompt"**. If a prompt with the same title already exists, its content will be updated. Otherwise, a new prompt will be saved, and a new button will appear in the "Saved Prompts" area.

3.  **Use Saved Prompts:**
    *   Click any button in the "Saved Prompts" area (on the right).
    *   The prompt's content will be **copied to your clipboard**.
    *   The prompt's title and content will also be loaded into the input fields on the left for quick editing.

4.  **Delete a Prompt:**
    *   Click a prompt button in the "Saved Prompts" area to load its details into the input fields.
    *   Click **"Delete Selected Prompt"**. You will be asked for confirmation.

5.  **System Tray Functions:**
    *   When you close the main window, the application will minimize to the system tray.
    *   **Double-click** the tray icon to restore the main window.
    *   **Right-click** the tray icon to open a context menu:
        *   **"Restore Window"**: Restores the main application window.
        *   **"Saved Prompts"**: A sub-menu listing all your saved prompts. Clicking any prompt here will copy its content to the clipboard without opening the main window.
        *   **"Quit Application"**: Exits the application completely.

## Configuration

*   **Prompt Data Location:** All prompt data is stored in a hidden directory within your user's home folder:
    *   `~/.prompt_manager/` (e.g., `/home/your_username/.prompt_manager/` on Linux)
*   **`prompts.json`**: This file is automatically created inside the `.prompt_manager/` directory. It stores all your prompt data in JSON format.
*   **`prompts.json.old.bak`**: A backup copy of `prompts.json` created automatically inside the `.prompt_manager/` directory before each save operation.
*   **`app_icon.png` (or `.ico`)**: For a custom application and tray icon, place an image file named `app_icon.png` (or `app_icon.ico`) in the same directory as ``prompt_manager.py`. If not found, a default system icon will be used.

## Project Structure

```
.
├── prompt_manager.py # The main application script
├── prompts.json # Local database for saved prompts (auto-generated)
├── prompts.json.old.bak # Backup of the prompts database (auto-generated)
└── app_icon.png # (Optional) Custom application icon file
```

## Disclaimer 
This project was entirely created using Gemini with some AI promptings.
Thanks to the simplicity of the project, it was not necessary to modify the 
code created by Gemini, but only to adjust it with additional prompts.

## Contributing

Feel free to fork the repository, open issues, or submit pull requests with improvements, bug fixes, or new features.

## License

This project is open source and available under the [MIT License](LICENSE).

