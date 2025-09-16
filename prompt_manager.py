import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel,QLayout,
    QScrollArea, QGridLayout, QMessageBox, QWidget,
    QStatusBar,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtGui import QClipboard, QIcon ,QAction
from PyQt6.QtCore import (
    Qt, QRect, QPoint, QSize 
)
 

# Import for functools.partial for dynamic menu actions
from functools import partial

PROMPT_DB_FILE = 'prompts.json'

# --- FlowLayout Class Definition ---
# This class enables dynamic button wrapping based on available width
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, spacing=-1):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins()
        size += QSize(margin.left() + margin.right(), margin.top() + margin.bottom())
        return size

    def _doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        spacing = self.spacing()

        for item in self.itemList:
            nextX = x + item.sizeHint().width() + spacing
            if nextX - spacing > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spacing
                nextX = x + item.sizeHint().width() + spacing
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()
# --- End FlowLayout Class Definition ---


class PromptManagerApp(QMainWindow): # Now inherits from QMainWindow
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt Prompt Manager")
        self.setGeometry(100, 100, 800, 600)

        self.prompts = self.load_prompts()
        self.init_ui()
        self.populate_prompt_buttons()

        # Initialize the status bar
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Application started. Load or create a prompt.")
        # --- System Tray Setup ---
        self.tray_icon = QSystemTrayIcon(self)
        # It's recommended to provide a custom icon for your application.
        # Ensure 'app_icon.png' is in the same directory as your script, or provide its full path.
        # Fallback to a standard icon if custom icon is not found.
        icon_path = os.path.join(os.path.dirname(__file__), "app_icon_32.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Fallback to a standard system icon
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
            self.statusBar().showMessage("Warning: 'app_icon.png' not found. Using a default icon.", 5000)

        self.tray_menu = QMenu()

        self.restore_action = QAction("Restore Window", self)
        self.restore_action.triggered.connect(self.showNormal) # Or self.show()
        self.tray_menu.addAction(self.restore_action)

        self.tray_menu.addSeparator()

        # Sub-menu for saved prompts
        self.prompts_sub_menu = self.tray_menu.addMenu("Saved Prompts")

        self.tray_menu.addSeparator()

        self.quit_action = QAction("Quit Application", self)
        self.quit_action.triggered.connect(QApplication.quit)
        self.tray_menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

        # Update tray menu immediately after initial load
        self.update_tray_menu()


    def closeEvent(self, event):
        # Intercept close event to minimize to tray
        if self.isVisible(): # Check if the window is currently visible
            self.hide()
            self.statusBar().showMessage("Application minimized to tray.", 2000)
            event.ignore() # Do not actually close the window
        else:
            # If the window is already hidden (e.g., quitting from tray menu), allow it to close.
            event.accept()

    def on_tray_icon_activated(self, reason):
        # Handle single and double clicks on the tray icon
        if reason == QSystemTrayIcon.ActivationReason.Trigger: # Single click (usually shows context menu by default)
            # You can add custom behavior here for single click if needed
            pass
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick: # Double click
            self.showNormal() # Restore the window to its normal state
            self.activateWindow() # Bring window to front
            self.statusBar().showMessage("Application restored from tray.")

    def update_tray_menu(self):
        # Clear existing prompt actions from the sub-menu before repopulating
        self.prompts_sub_menu.clear()

        if not self.prompts:
            no_prompts_action = QAction("No Prompts Saved", self)
            no_prompts_action.setEnabled(False) # Make it non-clickable
            self.prompts_sub_menu.addAction(no_prompts_action)
            return

        for prompt_data in self.prompts:
            action = QAction(prompt_data['title'], self)
            # Use functools.partial to pass arguments to the slot
            action.triggered.connect(partial(self.copy_prompt_to_clipboard_from_tray,
                                              prompt_data['content'],
                                              prompt_data['title']))
            self.prompts_sub_menu.addAction(action)

    def copy_prompt_to_clipboard_from_tray(self, content, title):
        clipboard = QApplication.clipboard()
        clipboard.setText(content)
        self.statusBar().showMessage(f"Prompt '{title}' copied to clipboard from tray.")



    def init_ui(self):
        # QMainWindow requires a central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget) # Pass central_widget to the layout

        # --- Prompt Creation/Editing Panel ---
        edit_panel_layout = QVBoxLayout()
        edit_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        edit_panel_layout.addWidget(QLabel("Prompt Title:"))
        self.title_input = QLineEdit()
        edit_panel_layout.addWidget(self.title_input)

        edit_panel_layout.addWidget(QLabel("Prompt Content:"))
        self.prompt_content_editor = QTextEdit()
        edit_panel_layout.addWidget(self.prompt_content_editor)

        # Save/Delete Buttons
        action_buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Prompt")
        self.save_button.clicked.connect(self.save_prompt)
        action_buttons_layout.addWidget(self.save_button)

        self.delete_button = QPushButton("Delete Selected Prompt")
        self.delete_button.clicked.connect(self.delete_selected_prompt)
        self.delete_button.setEnabled(False) # Disabled on startup
        action_buttons_layout.addWidget(self.delete_button)
        edit_panel_layout.addLayout(action_buttons_layout)

        main_layout.addLayout(edit_panel_layout, 2) # Takes 2/3 of the space

        # --- Saved Prompts Buttons Panel ---
        saved_prompts_panel_layout = QVBoxLayout()
        saved_prompts_panel_layout.addWidget(QLabel("Saved Prompts:"))

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # This is the main addition

        self.scroll_area_content = QWidget()
        self.prompt_buttons_layout = FlowLayout() # Changed from QGridLayout to FlowLayout 
        #self.prompt_buttons_layout = QGridLayout() # Grid for buttons
        #self.prompt_buttons_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft) # Ensure top-left alignment
        self.scroll_area_content.setLayout(self.prompt_buttons_layout)
        self.scroll_area.setWidget(self.scroll_area_content)

        saved_prompts_panel_layout.addWidget(self.scroll_area)
        main_layout.addLayout(saved_prompts_panel_layout, 1) # Takes 1/3 of the space

        # Note: self.setLayout(main_layout) is no longer needed when using QMainWindow with central_widget


    def load_prompts(self):
        if os.path.exists(PROMPT_DB_FILE):
            try:
                with open(PROMPT_DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "DB Error", "The prompt file is corrupted. Creating a new database.")
                return []
        return []

    def save_prompts(self):
        try:
            # Create a backup of the existing prompts.json before overwriting
            backup_file = PROMPT_DB_FILE + ".old.bak"
            if os.path.exists(PROMPT_DB_FILE):
                try:
                    import shutil
                    shutil.copyfile(PROMPT_DB_FILE, backup_file)
                    self.statusBar().showMessage(f"Backup created: '{backup_file}'.", 2000)
                except Exception as e:
                    # Log or show a warning if backup fails, but don't stop the main save operation
                    QMessageBox.warning(self, "Backup Error", f"Failed to create backup file '{backup_file}': {e}. Proceeding with save.")
                    self.statusBar().showMessage(f"Warning: Backup failed ({e}).", 3000)

            with open(PROMPT_DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.prompts, f, indent=4, ensure_ascii=False)
        except IOError as e:
            QMessageBox.critical(self, "Save Error", f"Unable to save the prompt file: {e}")

    def populate_prompt_buttons_old(self):
        # Clear existing buttons to avoid duplicates
        while self.prompt_buttons_layout.count():
            item = self.prompt_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Recreate all buttons
        row, col = 0, 0
        for prompt_data in self.prompts:
            button = QPushButton(prompt_data['title'])
            # Pass a copy of prompt_data to avoid closure issues with the loop
            button.clicked.connect(lambda checked, p=prompt_data: self.on_prompt_button_clicked(p))
            self.prompt_buttons_layout.addWidget(button, row, col)
            col += 1
            if col > 2: # 3 columns per row
                col = 0
                row += 1
        self.statusBar().showMessage(f"{len(self.prompts)} prompts loaded.")
        
    def populate_prompt_buttons(self):
        # Clear existing buttons to avoid duplicates
        # FlowLayout requires taking items one by one
        while self.prompt_buttons_layout.count():
            item = self.prompt_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Recreate all buttons
        # FlowLayout will handle dynamic wrapping
        for prompt_data in self.prompts:
            button = QPushButton(prompt_data['title'])
            # Pass a copy of prompt_data to avoid closure issues with the loop
            button.clicked.connect(lambda checked, p=prompt_data: self.on_prompt_button_clicked(p))
            self.prompt_buttons_layout.addWidget(button) # Changed from addWidget(button, row, col)

        self.statusBar().showMessage(f"{len(self.prompts)} prompts loaded.")

    def save_prompt(self):
        title = self.title_input.text().strip()
        content = self.prompt_content_editor.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, "Error", "Prompt title cannot be empty.")
            return
        if not content:
            QMessageBox.warning(self, "Error", "Prompt content cannot be empty.")
            return

        message = ""
        # Check if the prompt already exists to modify it
        found = False
        for i, p in enumerate(self.prompts):
            if p['title'] == title:
                self.prompts[i]['content'] = content
                message = f"Prompt '{title}' modified successfully!"
                found = True
                break

        if not found:
            # Add a new prompt
            self.prompts.append({"title": title, "content": content})
            message = f"Prompt '{title}' saved successfully!"

        self.save_prompts()
        self.populate_prompt_buttons() # Update buttons
        self.statusBar().showMessage(message) # Use the status bar
        self.clear_input_fields()
        self.delete_button.setEnabled(False) # Disable delete button

    def delete_selected_prompt(self):
        title_to_delete = self.title_input.text().strip()
        if not title_to_delete:
            QMessageBox.warning(self, "Error", "No prompt selected for deletion. Please select one by clicking its button.")
            return

        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete the prompt '{title_to_delete}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            initial_len = len(self.prompts)
            self.prompts = [p for p in self.prompts if p['title'] != title_to_delete]
            if len(self.prompts) < initial_len:
                self.save_prompts()
                self.populate_prompt_buttons()
                self.clear_input_fields()
                self.delete_button.setEnabled(False)
                self.statusBar().showMessage(f"Prompt '{title_to_delete}' deleted successfully!") # Use the status bar
            else:
                QMessageBox.warning(self, "Error", f"Prompt '{title_to_delete}' not found.")


    def on_prompt_button_clicked(self, prompt_data):
        # Copy content to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(prompt_data['content'])
        self.statusBar().showMessage(f"Prompt '{prompt_data['title']}' copied to clipboard for editing.") # Use the status bar

        # Display content in the text area for modifications
        self.title_input.setText(prompt_data['title'])
        self.prompt_content_editor.setPlainText(prompt_data['content'])
        self.delete_button.setEnabled(True) # Enable delete button when a prompt is selected

    def clear_input_fields(self):
        self.title_input.clear()
        self.prompt_content_editor.clear()
        self.delete_button.setEnabled(False)
        self.statusBar().showMessage("Input fields cleared. Ready for a new prompt.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PromptManagerApp()
    window.show()
    sys.exit(app.exec())
