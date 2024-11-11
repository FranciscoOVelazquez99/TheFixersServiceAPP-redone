from app import create_app

app = create_app()

import sys
import os
import socket
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QMessageBox, 
                           QDialog, QVBoxLayout, QLabel, QProgressBar)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSharedMemory,QTimer,Qt
from threading import Thread
from waitress import serve
import webbrowser
import win32console
import win32gui
import win32con


class StartupDialog(QDialog):
    def __init__(self, host, port):
        super().__init__()
        self.setWindowTitle("The Fixers Service")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.setFixedSize(400, 150)
        
        layout = QVBoxLayout()
        
        self.status_label = QLabel(f"Iniciando The Fixers Service en\nhttp://{host}:{port}")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress = QProgressBar()
        self.progress.setMaximum(0)
        self.progress.setMinimum(0)
        layout.addWidget(self.progress)
        
        self.setLayout(layout)
        
        # Auto-cerrar después de 3 segundos
        QTimer.singleShot(3000, self.close)



def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def run_flask():
    host = get_ip()
    port = 6969
    try:
        serve(app, host=host, port=port)
    except Exception as e:
        print(f"Error al iniciar el servidor: {e}")
        sys.exit(1)

class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super().__init__(icon, parent)
        menu = QMenu(parent)
        
        open_action = menu.addAction("Abrir aplicación")
        open_action.triggered.connect(self.open_browser)
        
        exit_action = menu.addAction("Salir")
        exit_action.triggered.connect(self.exit)
        
        self.setContextMenu(menu)

    def open_browser(self):
        host = get_ip()
        webbrowser.open(f"http://{host}:6969")

    def exit(self):
        QApplication.quit()

def hide_console():
    console_window = win32console.GetConsoleWindow()
    if console_window:
        win32gui.ShowWindow(console_window, win32con.SW_HIDE)

if __name__ == "__main__":
    hide_console()

    shared_memory = QSharedMemory("FixServUniqueKey")
    if shared_memory.attach():
        app = QApplication(sys.argv)
        dialog = QDialog()
        dialog.setWindowTitle("The Fixers Service")
        dialog.setFixedSize(300, 100)
        layout = QVBoxLayout()
        label = QLabel("La aplicación ya está en ejecución.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        dialog.setLayout(layout)
        dialog.exec_()
        sys.exit(0)

    if not shared_memory.create(1):
        print("No se pudo crear la memoria compartida.")
        sys.exit(1)

    # Inicia el servidor Flask en un hilo separado
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()



    # Inicia la aplicación Qt para el icono de bandeja del sistema
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    host=get_ip()
    port = 6969
    dialog = StartupDialog(host, port)
    dialog.show()

    icon_path = os.path.join(os.path.dirname(sys.executable), "FixLogo.ico")
    icon = QIcon(icon_path)
    tray_icon = SystemTrayIcon(icon)
    tray_icon.show()

    sys.exit(qt_app.exec_())
