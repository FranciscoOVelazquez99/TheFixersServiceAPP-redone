from app import create_app

app = create_app()

import sys
import os
import socket
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QMessageBox, 
                           QDialog, QVBoxLayout, QLabel, QProgressBar, QFrame)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSharedMemory, QTimer, Qt, QSize
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
        self.setFixedSize(400, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel#title {
                color: #2c3e50;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#status {
                color: #34495e;
                font-size: 14px;
            }
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(sys.executable), "FixLogo.ico")
        pixmap = QIcon(logo_path).pixmap(QSize(100, 100))
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        # Título
        title_label = QLabel("The Fixers Service")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Línea separadora
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #bdc3c7;")
        layout.addWidget(line)
        
        # Estado
        self.status_label = QLabel(f"Iniciando servicio en\nhttp://{host}:{port}")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Barra de progreso
        self.progress = QProgressBar()
        self.progress.setMaximum(0)
        self.progress.setMinimum(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        
        self.setLayout(layout)
        
        # Efecto de fade out al cerrar
        self.opacity = 1.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fade_out)
        QTimer.singleShot(2500, self.start_fade_out)

    def start_fade_out(self):
        self.timer.start(50)  # Actualizar cada 50ms

    def fade_out(self):
        self.opacity -= 0.1
        if self.opacity <= 0:
            self.timer.stop()
            self.close()
        else:
            self.setWindowOpacity(self.opacity)

# También mejorar el diálogo de "ya está en ejecución"
def show_already_running_dialog():
    dialog = QDialog()
    dialog.setWindowTitle("The Fixers Service")
    dialog.setFixedSize(300, 150)
    dialog.setStyleSheet("""
        QDialog {
            background-color: white;
        }
        QLabel {
            color: #2c3e50;
            font-size: 14px;
        }
    """)
    
    layout = QVBoxLayout()
    layout.setSpacing(15)
    layout.setContentsMargins(20, 20, 20, 20)
    
    icon_label = QLabel()
    icon_path = os.path.join(os.path.dirname(sys.executable), "FixLogo.ico")
    pixmap = QIcon(icon_path).pixmap(QSize(50, 50))
    icon_label.setPixmap(pixmap)
    icon_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(icon_label)
    
    label = QLabel("La aplicación ya está en ejecución.")
    label.setAlignment(Qt.AlignCenter)
    layout.addWidget(label)
    
    dialog.setLayout(layout)
    return dialog


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
        dialog = show_already_running_dialog()
        dialog.exec_()
        sys.exit(0)
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
