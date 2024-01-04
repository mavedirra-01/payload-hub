import sys
import os
from PyQt5.QtWidgets import (QApplication, QPlainTextEdit, QMainWindow, QGridLayout, QHBoxLayout, QTabWidget, QTextEdit, QPushButton, QVBoxLayout, QWidget, QFileDialog, QLabel, QDialog, QLineEdit, QFormLayout, QMessageBox, QComboBox)
from PyQt5.QtCore import QThread, pyqtSignal, QUrl, QRegExp
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
import paramiko
import json
import re
# TODO 
"""
allow for arguments in modules

make ui more clean and readable
"""

DRACULA_STYLESHEET = """
    QMainWindow {
        background-color: #282a36;
    }
    QLabel, QPushButton, QComboBox, QLineEdit {
        font-size: 11pt;
        color: #f8f8f2;
        font-family: 'Arial';
    }
    QPushButton {
        min-height: 30px;
        background-color: #44475a;
        border: none;
        border-radius: 5px;
        padding: 5px 10px;
    }
    QPushButton#CardButton {
        font-size: 12pt;  /* Larger font size */
        color: #f8f8f2;  /* Light text */
        background-color: #6272a4;  /* Card background */
        border-radius: 8px;  /* Rounded corners */
        padding: 15px;  /* Inner padding */
        text-align: left;
        border: none;
    }
    
    QPlainTextEdit {
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 11pt;
        color: #f8f8f2;
        background-color: #282a36;
        border: 1px solid #6272a4;
    }

    QPushButton#CardButton:hover {
        background-color: #50fa7b;  /* Change color on hover */
    }
    QPushButton:hover {
        background-color: #6272a4;
    }
    QPushButton:pressed {
        background-color: #50fa7b;
    }
    QTextEdit {
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 12pt;
        color: #f8f8f2;
        background-color: #44475a;
        padding: 5px;
        border: 1px solid #6272a4;
    }
    QTabWidget::pane {
        border-top: 2px solid #44475a;
    }
    QTabWidget::tab-bar {
        alignment: center;
    }
    QTabBar::tab {
        background: #6272a4;
        color: #f8f8f2;
        padding: 5px;
        margin: 1px;
        border-radius: 3px;
    }
    QTabBar::tab:selected {
        background: #50fa7b;
        color: #282a36;
    }
    QTabBar::tab:!selected:hover {
        background: #bd93f9;
    }
    QLineEdit {
        background-color: #44475a;
        border-radius: 5px;
        padding: 5px;
        border: 1px solid #6272a4;
    }
    QComboBox {
        min-height: 25px;
        background-color: #44475a;
        border-radius: 5px;
        padding: 5px;
        border: 1px solid #6272a4;
    }
    QComboBox::drop-down {
        border: none;
    }
    QComboBox::down-arrow {
        image: url(dropdown-arrow.png); /* Replace with your arrow image */
    }
    QDialog {
        background-color: #282a36;
    }
    QScrollBar:vertical {
        border: 1px solid #44475a;
        background: #282a36;
        width: 12px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #6272a4;
        min-height: 20px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: 0px solid grey;
        background: #44475a;
        height: 0px;
        subcontrol-position: top;
        subcontrol-origin: margin;
    }
    QStatusBar {
        font-size: 10pt;
        color: #f8f8f2;
        background-color: #44475a;
        padding: 3px;
    }
"""


CONFIG_DIR = ".config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "drones.json")

def save_config(drones):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as file:
        json.dump(drones, file, indent=4)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    return {}

def strip_ansi_codes(text):
    # This pattern is designed to catch common ANSI escape sequences
    ansi_escape = re.compile(r'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-_] |
            \[ [0-?]* [ -/]* [@-~]  # CSI ... Cmd
        )
    ''', re.VERBOSE)
    return ansi_escape.sub('', text)

class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#ff79c6"))  # Pink color for keywords
        keywords = ["def", "class", "import", "from", "as", "if", "elif", "else", "while", "for", "try", "except", "with"]

        self.highlighting_rules = [(r'\b' + keyword + r'\b', keyword_format) for keyword in keywords]

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
                
class JsonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#f1fa8c"))

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#bd93f9"))

        boolean_format = QTextCharFormat()
        boolean_format.setForeground(QColor("#ffb86c"))

        self.highlighting_rules = [
            (r'"[^"\\]*(\\.[^"\\]*)*"', string_format),
            (r'\b-?\d+(\.\d+)?([eE][+-]?\d+)?\b', number_format),
            (r'\b(true|false)\b', boolean_format)
        ]

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)


class BashSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#ff79c6"))
        keywords = ["if", "then", "else", "fi", "for", "while", "do", "done", "echo", "exit"]

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6272a4"))
        comment_format.setFontItalic(True)

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#f1fa8c"))

        self.highlighting_rules = [(r'\b' + keyword + r'\b', keyword_format) for keyword in keywords]
        self.highlighting_rules += [
            (r'#.*', comment_format),
            (r'".*?"', string_format),
            (r"'.*?'", string_format)
        ]

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)

class CommandLineArgsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Enter Command-Line Arguments')

        layout = QVBoxLayout(self)

        self.args_input = QLineEdit(self)
        layout.addWidget(self.args_input)

        self.submit_button = QPushButton('Submit', self)
        self.submit_button.clicked.connect(self.accept)
        layout.addWidget(self.submit_button)

    def get_arguments(self):
        return self.args_input.text().strip()


class DroneConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Configure Drone')

        self.layout = QFormLayout(self)

        self.host_input = QLineEdit(self)
        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)

        self.layout.addRow('Host:', self.host_input)
        self.layout.addRow('Username:', self.username_input)
        self.layout.addRow('Password:', self.password_input)

        self.submit_button = QPushButton('Save', self)
        self.submit_button.clicked.connect(self.accept)
        self.layout.addRow(self.submit_button)

    def get_details(self):
        return self.host_input.text(), self.username_input.text(), self.password_input.text()

class SSHThread(QThread):
    update_output = pyqtSignal(str)

    def __init__(self, host, username, password, full_command, is_script_path=True):
        super().__init__()
        self.host = host
        self.username = username
        self.password = password
        self.full_command = full_command
        self.is_script_path = is_script_path
        self.ssh = None
        self.running = False

    
            
    def convert_line_endings(self, local_path):
        """Convert Windows line endings to Unix/Linux line endings."""
        with open(local_path, 'r') as file:
            content = file.read()
        return content.replace('\r\n', '\n')
    
    def transfer_script(self, local_path):
        """Transfers the script to the remote machine after converting line endings."""
        script_content = self.convert_line_endings(local_path)
        filename = os.path.basename(local_path)
        remote_path = f"/tmp/{filename}"

        with self.ssh.open_sftp() as sftp:
            with sftp.file(remote_path, 'w') as remote_file:
                remote_file.write(script_content)
        
        self.ssh.exec_command(f"chmod +x {remote_path}")
        return remote_path

    def run(self):
        self.running = True
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(self.host, username=self.username, password=self.password)

            if self.is_script_path:
                remote_script_path = self.transfer_script(self.full_command.split()[0])
                # Use the absolute path for executing the script
                command_to_run = f"echo $$; exec {remote_script_path} {' '.join(self.full_command.split()[1:])}"
            else:
                command_to_run = f"echo $$; exec {self.full_command}"

            stdin, stdout, stderr = self.ssh.exec_command(command_to_run, get_pty=True)

            # Correctly parsing the PID
            try:
                self.pid = int(stdout.readline().strip())
            except ValueError:
                self.update_output.emit("Error: Unable to parse PID.")
                return

            while self.running and not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    aline = stdout.channel.recv(1024).decode('utf-8')
                    clean_line = strip_ansi_codes(aline)
                    self.update_output.emit(clean_line)
                if stderr.channel.recv_stderr_ready():
                    aline = stderr.channel.recv_stderr(1024)
                    self.update_output.emit(aline.decode('utf-8'))

        except Exception as e:
            self.update_output.emit(f"SSH Connection Error: {str(e)}")
        finally:
            if self.ssh:
                self.ssh.close()

    def stop(self):
        self.running = False
        if self.ssh:
            try:
                # Safely attempt to send a kill command
                if self.pid:
                    kill_command = f"kill {self.pid}"
                    self.ssh.exec_command(kill_command)
            except Exception as e:
                # Log or print the exception if needed
                pass
            finally:
                self.ssh.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_module_path = None
        self.setWindowTitle("BSTG Payload Hub")
        self.setGeometry(100, 100, 800, 600)

        self.layout = QVBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        self.tab_widget = QTabWidget(self)
        self.layout.addWidget(self.tab_widget)

        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        self.moduleSelectionLayout = QHBoxLayout()  # Horizontal layout for module selection

        self.module_label = QLabel("Choose a module to run:")
        self.moduleSelectionLayout.addWidget(self.module_label)

        self.moduleComboBox = QComboBox(self)
        self.populate_module_combobox()  # Call the method to populate the combo box
        self.moduleSelectionLayout.addWidget(self.moduleComboBox)
        self.moduleComboBox.currentIndexChanged.connect(self.module_selected)


        self.module_button = QPushButton("Execute Module", self)
        self.module_button.clicked.connect(self.execute_module)
        self.moduleSelectionLayout.addWidget(self.module_button)

        self.layout.addLayout(self.moduleSelectionLayout)

        self.selected_module = None
        self.threads = []
        
        # module editor
        self.module_editor_tab = QWidget()
        self.module_editor_layout = QVBoxLayout(self.module_editor_tab)

        self.module_editor = QPlainTextEdit()

        self.module_editor_layout.addWidget(self.module_editor)

        self.save_button = QPushButton("Save Module")
        self.save_button.clicked.connect(self.save_module)
        self.module_editor_layout.addWidget(self.save_button)

        # Add the module editor tab to the tab widget
        self.tab_widget.addTab(self.module_editor_tab, "Module Editor")
        
        # Create Home Tab
        self.home_tab = QWidget()
        self.home_layout = QGridLayout(self.home_tab)

        # Add cards to the home tab
        self.add_home_cards()

        # Add the home tab to the tab widget
        self.tab_widget.insertTab(0, self.home_tab, "Home")


        # Initialize drone_selector before calling populate_drones
        self.drone_selector = QComboBox(self)
        self.layout.addWidget(self.drone_selector)

        self.configure_drone_button = QPushButton("Configure Drone", self)
        self.configure_drone_button.clicked.connect(self.configure_drone)
        self.layout.addWidget(self.configure_drone_button)

        # Load and populate drones after drone_selector is created
        self.drones = load_config()
        self.populate_drones()
        
        # Actice connections
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.statusBar = self.statusBar()
        self.update_status_bar()
        
    def add_home_cards(self):
        # Example of adding a card with a URL
        card1 = QPushButton("Visit Google")
        card1.setObjectName("CardButton")
        card1.setCursor(Qt.PointingHandCursor)  # Set cursor to pointing hand
        card1.clicked.connect(lambda: self.on_card_click("https://google.com"))
        self.home_layout.addWidget(card1, 0, 0)

        # Adding another card
        card2 = QPushButton("Visit Example")
        card2.setObjectName("CardButton")
        card2.setCursor(Qt.PointingHandCursor)  # Set cursor to pointing hand
        card2.clicked.connect(lambda: self.on_card_click("https://example.com"))
        self.home_layout.addWidget(card2, 0, 1)

    def on_card_click(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def save_module(self):
        if not self.current_module_path:
            QMessageBox.warning(self, "Error", "No module loaded.")
            return

        module_content = self.module_editor.toPlainText()
        try:
            with open(self.current_module_path, 'w') as file:
                file.write(module_content)
            QMessageBox.information(self, "Success", "Module saved successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save module: {e}")

    
    def load_module_into_editor(self, module_path):
        self.current_module_path = module_path
        try:
            with open(module_path, 'r') as file:
                content = file.read()
                self.module_editor.setPlainText(content)
                self.set_syntax_highlighter(module_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load module: {e}")

            
    def set_syntax_highlighter(self, module_path):
        if module_path.endswith('.sh'):
            self.syntax_highlighter = BashSyntaxHighlighter(self.module_editor.document())
        elif module_path.endswith('.json'):
            self.syntax_highlighter = JsonSyntaxHighlighter(self.module_editor.document())
        elif module_path.endswith('.py'):
            self.syntax_highlighter = PythonSyntaxHighlighter(self.module_editor.document())


    
    def populate_module_combobox(self):
        modules_dir = "modules"
        if not os.path.exists(modules_dir):
            print("Modules directory not found")
            return

        for filename in os.listdir(modules_dir):
            if filename.endswith(('.sh', '.py', '.json')):
                self.moduleComboBox.addItem(filename)
        
    def on_tab_changed(self, index):
        if index != -1:
            tab_info = self.tab_widget.tabText(index)
            self.update_status_bar(f"Active connection: {tab_info}")
        else:
            self.update_status_bar()
        
        
    def update_status_bar(self, text="No active connection"):
        self.statusBar.showMessage(text)    
    
    def populate_drones(self):
        for drone_id in self.drones:
            self.drone_selector.addItem(drone_id)

    def configure_drone(self):
        dialog = DroneConfigDialog(self)
        if dialog.exec_():
            host, username, password = dialog.get_details()
            if host and username and password:
                drone_id = f"{username}@{host}"
                self.drones[drone_id] = (host, username, password)
                self.drone_selector.addItem(drone_id)
                save_config(self.drones)

    def close_tab(self, index):
        tab = self.tab_widget.widget(index)
        if tab and hasattr(tab, 'ssh_thread'):
            tab.ssh_thread.stop()
        self.tab_widget.removeTab(index)


    def add_ssh_tab(self, host, username, password, command, is_script_path=True, group_name="", group_color=None):
        tab = QTextEdit()
        tab.setReadOnly(True)
        if group_color:
            tab.setStyleSheet(f"background-color: {group_color};")
  
        tab.ssh_thread = SSHThread(host, username, password, command, is_script_path)
        self.update_status_bar(f"Connected to: {username}@{host}")
        tab.ssh_thread.update_output.connect(lambda line: tab.append(line))
        tab.ssh_thread.start()
        self.threads.append(tab.ssh_thread)

        tab_name = f"{group_name} ({username}@{host})" if group_name else f"{username}@{host}"
        index = self.tab_widget.addTab(tab, tab_name)
        self.tab_widget.setTabsClosable(True)
        return tab


    def remove_thread(self, thread):
        self.threads.remove(thread)
        
    def module_selected(self, index):
        if index >= 0:
            selected_module = self.moduleComboBox.itemText(index)
            if selected_module:
                module_path = os.path.join("modules", selected_module)
                self.load_module_into_editor(module_path)


    def execute_module(self):
        if not self.drone_selector.currentText():
            QMessageBox.warning(self, "No Drone Selected", "Please configure and select a drone first.")
            return

        selected_module = self.moduleComboBox.currentText()
        if not selected_module:
            QMessageBox.warning(self, "No Module Selected", "Please select a module first.")
            return

        module_path = os.path.join("modules", selected_module)
        drone_id = self.drone_selector.currentText()
        host, username, password = self.drones[drone_id]

        # If the module is a JSON file, execute it as before
        if selected_module.endswith('.json'):
            with open(module_path, 'r') as file:
                module_data = json.load(file)
                group_color = module_data.get("color", None)
                if module_data.get("grouped", False):
                    for tab_info in module_data.get("tabs", []):
                        group_name = tab_info.get("name", "")
                        self.open_tab_group(tab_info["command"], False, group_name, group_color)
            return

        # For .py or .sh scripts, prompt for command-line arguments
        args_dialog = CommandLineArgsDialog(self)
        if args_dialog.exec_() == QDialog.Accepted:
            args = args_dialog.get_arguments()
            full_command = f"{module_path} {args}"
            self.add_ssh_tab(host, username, password, full_command, is_script_path=True)



    def open_tab_group(self, command, is_script_path=True, group_name=None, group_color=None):
        drone_id = self.drone_selector.currentText()
        host, username, password = self.drones[drone_id]
        self.add_ssh_tab(host, username, password, command, is_script_path, group_name, group_color)

            
    def closeEvent(self, event):
        for thread in self.threads:
            if thread.isRunning():
                thread.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DRACULA_STYLESHEET)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
