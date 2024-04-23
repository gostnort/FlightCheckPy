from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog
from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget, QTextEdit
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtGui import QIcon
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fight_Check_Python 0.5")
        self.setFixedSize(600, 400)  # Set fixed window size
        
        # Set window icon
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "resources/fcp0.5.ico")
        self.setWindowIcon(QIcon(icon_path))

        # Create button and QLineEdit for file path
        self.button = QPushButton("Open...")
        self.button.clicked.connect(self.open_file_dialog)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        
        # Create QTextEdit for result output
        self.result_text_edit = QTextEdit()

        # Create "Run" button
        self.run_button = QPushButton("Run")
        self.run_button.setFixedWidth(100)  # Set width to 50 pixels
        self.run_button.clicked.connect(self.run_logic)
        
        # Create a QHBoxLayout for the first row
        first_row_layout = QHBoxLayout()
        first_row_layout.addWidget(self.button)
        first_row_layout.addWidget(self.file_path_edit)
        
        # Create a QVBoxLayout for the main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(first_row_layout)
        main_layout.addWidget(self.result_text_edit)
        main_layout.addWidget(self.run_button)
        
        # Create a central widget to hold the main layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*);;Text Files (*.txt)")
        if file_path:
            self.file_path_edit.setText(file_path)

    def run_logic(self):
        # Implement your main logic here
        file_path = self.file_path_edit.text()
        # Do something with the file path, for example:
        self.result_text_edit.append(f"Running logic with file: {file_path}")

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()