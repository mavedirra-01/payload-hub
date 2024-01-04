import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QTextEdit, QPushButton, QVBoxLayout, QWidget, QFileDialog, QLabel, QDialog, QLineEdit, QFormLayout, QMessageBox, QComboBox)
from PyQt5.QtCore import QThread, pyqtSignal
import paramiko
import json
# TODO 
"""
Fix fomatting on output
make ui more clean and readable
clearly show what ssh connection is currently active 
"""

DRACULA_STYLESHEET = """
    QMainWindow {
        background-color: #282a36;
    }
    QLabel, QPushButton, QComboBox, QLineEdit {
        color: #f8f8f2;
        font-family: 'Arial';
    }
    QPushButton {
        background-color: #44475a;
        border: none;
        border-radius: 5px;
        padding: 5px 10px;
    }
    QPushButton:hover {
        background-color: #6272a4;
    }
    QPushButton:pressed {
        background-color: #50fa7b;
    }
    QTextEdit {
        background-color: #44475a;
        color: #f8f8f2;
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

    def __init__(self, host, username, password, command, is_script_path=True):
        super().__init__()
        self.host = host
        self.username = username
        self.password = password
        self.command = command
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
        
        return remote_path
    
    def get_command(self, script_path):
        if script_path.endswith('.py'):
            return f"python3 {script_path}"
        else:
            return f"bash {script_path}"

    def run(self):
        self.running = True
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(self.host, username=self.username, password=self.password)

            if self.is_script_path:
                remote_script_path = self.transfer_script(self.command)
                command_to_run = f"echo $$; exec {self.get_command(remote_script_path)}"
            else:
                command_to_run = f"echo $$; exec {self.command}"

            stdin, stdout, stderr = self.ssh.exec_command(command_to_run, get_pty=True)

            # Correctly parsing the PID
            try:
                self.pid = int(stdout.readline().strip())
            except ValueError:
                self.update_output.emit("Error: Unable to parse PID.")
                return

            while self.running and not stdout.channel.exit_status_ready():
                # Read stdout and stderr and emit signals
                if stdout.channel.recv_ready():
                    aline = stdout.channel.recv(1024)
                    self.update_output.emit(aline.decode('utf-8'))
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
        self.setWindowTitle("SSH Drone Controller")
        self.setGeometry(100, 100, 800, 600)

        self.layout = QVBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        self.tab_widget = QTabWidget(self)
        self.layout.addWidget(self.tab_widget)

        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        self.module_label = QLabel("Choose a module to run:", self)
        self.layout.addWidget(self.module_label)

        self.module_button = QPushButton("Select Module", self)
        self.module_button.clicked.connect(self.select_module)
        self.layout.addWidget(self.module_button)

        self.selected_module = None
        self.threads = []

        # Initialize drone_selector before calling populate_drones
        self.drone_selector = QComboBox(self)
        self.layout.addWidget(self.drone_selector)

        self.configure_drone_button = QPushButton("Configure Drone", self)
        self.configure_drone_button.clicked.connect(self.configure_drone)
        self.layout.addWidget(self.configure_drone_button)

        # Load and populate drones after drone_selector is created
        self.drones = load_config()
        self.populate_drones()
        
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
        tab.ssh_thread.update_output.connect(lambda line: tab.append(line))
        tab.ssh_thread.start()
        self.threads.append(tab.ssh_thread)

        tab_name = f"{group_name} - {host}" if group_name else host
        index = self.tab_widget.addTab(tab, tab_name)
        self.tab_widget.setTabsClosable(True)
        return tab


    def remove_thread(self, thread):
        self.threads.remove(thread)

    def select_module(self):
        if not self.drone_selector.currentText():
            QMessageBox.warning(self, "No Drone Selected", "Please configure and select a drone first.")
            return

        options = QFileDialog.Options()
        file_filter = "All Files (*);;JSON Files (*.json);;Python Scripts (*.py);;Bash Scripts (*.sh)"
        module_file, selected_filter = QFileDialog.getOpenFileName(self, "Select Module or Script", "modules", file_filter, options=options)

        if module_file:
            if module_file.endswith('.json'):
                with open(module_file, 'r') as file:
                    module_data = json.load(file)
                    group_color = module_data.get("color", None)
                    if module_data.get("grouped", False):
                        for tab_info in module_data.get("tabs", []):
                            group_name = tab_info.get("name", "")
                            self.open_tab_group(tab_info["command"], False, group_name, group_color)
            else:
                # Handle script file
                drone_id = self.drone_selector.currentText()
                host, username, password = self.drones[drone_id]
                self.add_ssh_tab(host, username, password, module_file, True)

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
