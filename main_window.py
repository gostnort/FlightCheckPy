from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog
from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget, QTextEdit
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtGui import QIcon
import os
import argparse
import run_button

class MainWindow(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.setWindowTitle("Fight_Check_Python 0.5")
        self.resize(600, 400)  # Set initial window size to 600x400 pixels
        self.setMinimumSize(200, 200)  # Set minimum window size to 200x200 pixels
        
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
        self.run_button.setFixedWidth(100)  # Set width to 100 pixels
        self.run_button.clicked.connect(lambda: self.run_logic(args))
        
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

    def run_logic(self,args):
        self.result_text_edit.clear()

        # Check if debug mode is enabled and append debug message
        if args.debug:
            self.result_text_edit.append("Debug mode enabled")

        # Implement your main logic here
        file_path = self.file_path_edit.text()
        pr_list=run_button.separate_pr(file_path)
        messages=run_button.loop_obtain_info(pr_list)
        
        if args.debug:
            for line in pr_list:
                self.result_text_edit.append(line)
                self.result_text_edit.append("+++++++++")

        for line in messages[0]:
            self.result_text_edit.append(line)

        if args.debug:
            for line in messages[1]:
                self.result_text_edit.append(line)

def main():
    parser = argparse.ArgumentParser(description="Fight_Check_Python 0.5")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # Create the application
    app = QApplication([])
    window = MainWindow(args)
    window.show()
    app.exec()

if __name__ == "__main__":
    main()