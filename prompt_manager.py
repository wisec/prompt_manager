#!/bin/env python3
import sys
import json
import os
import shutil
import pathlib
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QLayout,
    QScrollArea, QMessageBox, QWidget,
    QStatusBar, QTableView, QHeaderView, # Added QTableView, QHeaderView
    QSystemTrayIcon, QMenu,
    QSplitter # ADDED: QSplitter
)
from PyQt6.QtGui import QClipboard, QIcon ,QAction
from PyQt6.QtCore import (
    Qt, QRect, QPoint, QSize,
    QAbstractTableModel, QSortFilterProxyModel # Added QAbstractTableModel, QSortFilterProxyModel
)
from functools import partial

# --- Configuration for Prompt Database ---
# Determine the directory of the currently running script
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

# Define the hidden directory in the user's home for application data
APP_DATA_DIR = pathlib.Path.home() / ".prompt_manager"
# Define the full path for the prompt database file
PROMPT_DB_FILE = APP_DATA_DIR / "prompts.json"

APP_ICON_FILE_NAME = "app_icon_32.png" # Name of the icon file
# The full path to the icon file, expected alongside the script
APP_ICON_PATH = SCRIPT_DIR / APP_ICON_FILE_NAME # Now explicitly points to script directory

# --- FlowLayout Class Definition ---
# (No longer used for prompt display, but kept in case it's used elsewhere or for future plans)
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

# --- Custom Table Model for Prompts ---
class PromptTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self.headers = ["Title", "Created", "Modified"]
        # Store original data for sorting (if needed, QSortFilterProxyModel can do this too)

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            prompt = self._data[index.row()]
            column = index.column()
            if column == 0: return prompt['title']
            if column == 1: return prompt['created_at'] # Display as string
            if column == 2: return prompt['modified_at'] # Display as string
            return None
        if role == Qt.ItemDataRole.UserRole: # For retrieving full prompt data
            return self._data[index.row()]
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None
    
    # Method to update data
    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    # Method to get original index from proxy (needed for deletion logic)
    def get_prompt_by_row(self, row):
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

# --- Main Application Class ---
class PromptManagerApp(QMainWindow): # Now inherits from QMainWindow
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt Prompt Manager")
        self.setGeometry(100, 100, 800, 600)
        # Ensure the application data directory exists
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True) # Create the directory if it doesn't exist

        self.prompts = self.load_prompts()
        self.init_ui()
        self.populate_prompt_list() # Initial population of the table view

        # Initialize the status bar
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Application started. Load or create a prompt.")
        # --- System Tray Setup ---
        self.tray_icon = QSystemTrayIcon(self)
        # It's recommended to provide a custom icon for your application.
        # Ensure 'app_icon_32.png' is in the same directory as your script, or provide its full path.
        # Fallback to a standard icon if custom icon is not found.
        # icon_path = os.path.join(SCRIPT_DIR, "app_icon_32.png") # SCRIPT_DIR is already defined
        
        if APP_ICON_PATH.exists(): # Use the pathlib Path object
            self.tray_icon.setIcon(QIcon(str(APP_ICON_PATH)))
            self.setWindowIcon(QIcon(str(APP_ICON_PATH))) # Set window icon as well
        else:
            # Fallback to a standard system icon
            default_icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
            self.tray_icon.setIcon(default_icon)
            self.setWindowIcon(default_icon) # Set window icon as well
            self.statusBar().showMessage("Warning: 'app_icon_32.png' not found. Using a default icon.", 5000)

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
        # Connect the tray_menu's aboutToShow signal to update the prompt list
        # This ensures the prompt list is refreshed every time the tray menu is opened.
        self.tray_menu.aboutToShow.connect(self.update_tray_menu)
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
        self.prompts = self.load_prompts() #
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
        # self.setCentralWidget(central_widget) # Not needed here, as splitter will be central widget

        # REPLACED main_layout (QHBoxLayout) with QSplitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal) # ADDED: QSplitter
        self.setCentralWidget(self.main_splitter) # Set splitter as the central widget

        # --- Prompt Creation/Editing Panel ---
        edit_panel_widget = QWidget() # Wrapper widget for the layout
        edit_panel_layout = QVBoxLayout(edit_panel_widget) # Pass edit_panel_widget to the layout
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
        
        # Add the edit panel to the splitter
        self.main_splitter.addWidget(edit_panel_widget) # ADDED to splitter

        # --- Saved Prompts List Panel ---
        saved_prompts_panel_widget = QWidget() # Wrapper widget for the layout
        saved_prompts_panel_layout = QVBoxLayout(saved_prompts_panel_widget) # Pass saved_prompts_panel_widget to the layout
        saved_prompts_panel_layout.addWidget(QLabel("Search Prompts:")) # New label for search
        self.search_input = QLineEdit() # NEW: Search input box
        self.search_input.setPlaceholderText("Type to search prompts...")
        self.search_input.textChanged.connect(self.filter_prompt_list) # Connect signal
        saved_prompts_panel_layout.addWidget(self.search_input) # Add search input

        saved_prompts_panel_layout.addWidget(QLabel("Saved Prompts:"))

        # REPLACED QScrollArea and FlowLayout with QTableView
        self.prompt_table_view = QTableView() # NEW: QTableView
        
        self.prompt_table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.prompt_table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        self.source_model = PromptTableModel(self.prompts) # Our custom model
        self.proxy_model = QSortFilterProxyModel(self) # For sorting and filtering
        self.proxy_model.setSourceModel(self.source_model)
        
        self.prompt_table_view.setModel(self.proxy_model)
        
        # Configure the header for sorting
        self.prompt_table_view.setSortingEnabled(True) # Enable sorting by clicking headers
        self.prompt_table_view.horizontalHeader().setSortIndicatorShown(True) # Show the sort indicator
        # Ensure only Title column is stretched, others adjust to content
        self.prompt_table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # Title column
        self.prompt_table_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Created
        self.prompt_table_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Modified
        
        # Connect selection change for editing/deletion
        self.prompt_table_view.selectionModel().selectionChanged.connect(self.on_prompt_table_selection_changed)

        saved_prompts_panel_layout.addWidget(self.prompt_table_view)
        
        # Add the saved prompts panel to the splitter
        self.main_splitter.addWidget(saved_prompts_panel_widget) # ADDED to splitter

        # Set initial sizes for the splitter (e.g., 2/3 for edit, 1/3 for list)
        self.main_splitter.setSizes([self.width() * 2 // 3, self.width() * 1 // 3]) # ADDED: Initial sizes

    def load_prompts(self):
        if PROMPT_DB_FILE.exists():
            try:
                with open(PROMPT_DB_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Ensure 'created_at' and 'modified_at' exist for older prompts
                    for prompt in data:
                        if 'created_at' not in prompt:
                            prompt['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        if 'modified_at' not in prompt:
                            prompt['modified_at'] = prompt['created_at'] # Initially same as created_at
                    return data
            except json.JSONDecodeError:
                QMessageBox.warning(self, "DB Error", "The prompt file is corrupted. Creating a new database.")
                return []
        return []

    def save_prompts(self):
        try:
            # Create a backup of the existing prompts.json before overwriting
            backup_file = PROMPT_DB_FILE.with_suffix(".json.old.bak") # Correctly forms .prompt_manager/prompts.json.old.bak
            if PROMPT_DB_FILE.exists():
                try:
                    shutil.copyfile(PROMPT_DB_FILE, backup_file)
                    self.statusBar().showMessage(f"Backup created: '{backup_file.name}'.", 2000)
                except Exception as e:
                    QMessageBox.warning(self, "Backup Error", f"Failed to create backup file '{backup_file.name}': {e}. Proceeding with save.")
                    self.statusBar().showMessage(f"Warning: Backup failed ({e}).", 3000)

            # Now save the current prompts to the main file
            with open(PROMPT_DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.prompts, f, indent=4, ensure_ascii=False)
        except IOError as e:
            QMessageBox.critical(self, "Save Error", f"Unable to save the prompt file: {e}")

    def filter_prompt_list(self, search_text): # RENAMED from filter_prompt_buttons
        search_text = search_text.strip().lower() # Get search text, clean it, and make lowercase

        if not search_text:
            self.proxy_model.setFilterRegularExpression("") # Clear filter on proxy model
            self.source_model.update_data(self.prompts) # Ensure source model has all data
            self.statusBar().showMessage(f"{len(self.prompts)} prompts loaded.")
        else:
            filtered_data = [
                p for p in self.prompts
                if search_text in p['title'].lower() or search_text in p['content'].lower()
            ]
            self.source_model.update_data(filtered_data) # Update source model with filtered data
            self.statusBar().showMessage(f"{len(filtered_data)} prompts found.")

    def populate_prompt_list(self): # Modified for QTableView
        self.source_model.update_data(self.prompts) # Update the source model with current prompts
        self.filter_prompt_list(self.search_input.text() if hasattr(self, 'search_input') else "") # Apply filter if any
        # The status bar message is handled by filter_prompt_list now


    def save_prompt(self):
        title = self.title_input.text().strip()
        content = self.prompt_content_editor.toPlainText().strip()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
                self.prompts[i]['modified_at'] = now # Update modified date
                message = f"Prompt '{title}' modified successfully!"
                found = True
                break

        if not found:
            # Add a new prompt
            self.prompts.append({"title": title, "content": content, "created_at": now, "modified_at": now}) # Add dates
            message = f"Prompt '{title}' saved successfully!"

        self.save_prompts()
        self.prompts = self.load_prompts() # Reload all prompts after saving
        self.populate_prompt_list() # Re-populate and apply filter
        self.statusBar().showMessage(message) # Use the status bar
        self.clear_input_fields()
        self.delete_button.setEnabled(False) # Disable delete button

    def delete_selected_prompt(self):
        # Get selected rows from the proxy model
        selected_indexes = self.prompt_table_view.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.warning(self, "Error", "No prompt selected for deletion. Please select one by clicking its title in the list.") # UPDATED text
            return

        # Map proxy index to source index to get actual prompt data
        # Assuming single selection for deletion, otherwise need to iterate
        proxy_index = selected_indexes[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        prompt_to_delete = self.source_model.get_prompt_by_row(source_index.row())

        if not prompt_to_delete:
            QMessageBox.warning(self, "Error", "Could not retrieve selected prompt for deletion.")
            return

        title_to_delete = prompt_to_delete['title']

        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete the prompt '{title_to_delete}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            initial_len = len(self.prompts)
            self.prompts = [p for p in self.prompts if p['title'] != title_to_delete]
            if len(self.prompts) < initial_len:
                self.save_prompts()
                self.prompts = self.load_prompts() # Reload all prompts after deletion
                self.populate_prompt_list() # Re-populate and apply filter
                self.clear_input_fields()
                self.delete_button.setEnabled(False)
                self.statusBar().showMessage(f"Prompt '{title_to_delete}' deleted successfully!") # Use the status bar
            else:
                QMessageBox.warning(self, "Error", f"Prompt '{title_to_delete}' not found.")

    def on_prompt_table_selection_changed(self, selected, deselected): # NEW Slot for QTableView selection
        
        # Get the selected item from the proxy model
        selected_indexes = selected.indexes()
        
        if selected_indexes:
            proxy_index = selected_indexes[0] # Get the first selected row
            # Map the proxy index back to the source model to get the original data
            source_index = self.proxy_model.mapToSource(proxy_index)
            prompt_data = self.source_model.get_prompt_by_row(source_index.row())

            if prompt_data:
                clipboard = QApplication.clipboard()
                clipboard.setText(prompt_data['content'])
                self.statusBar().showMessage(f"Prompt '{prompt_data['title']}' copied to clipboard for editing.")

                self.title_input.setText(prompt_data['title'])
                self.prompt_content_editor.setPlainText(prompt_data['content'])
                self.delete_button.setEnabled(True)
            else:
                self.clear_input_fields()
        else:
            self.clear_input_fields()

    def on_prompt_button_clicked(self, prompt_data): # This method is now entirely unused
        pass

    def clear_input_fields(self):
        self.title_input.clear()
        self.prompt_content_editor.clear()
        self.delete_button.setEnabled(False)
        self.statusBar().showMessage("Input fields cleared. Ready for a new prompt.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "System Tray Error", "I couldn't detect any system tray on this system.")
        sys.exit(1)

    window = PromptManagerApp()
    window.show()
    sys.exit(app.exec())