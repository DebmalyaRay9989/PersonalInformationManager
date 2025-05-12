

import sys
import json
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import os
import shutil
import bcrypt
import secrets
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox,
                             QComboBox, QDateEdit, QFormLayout, QTabWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QAction, QFileDialog,
                             QStackedWidget, QGroupBox, QTextEdit, QScrollArea, QFrame,
                             QDialog, QDialogButtonBox, QCheckBox, QSizePolicy, QListWidgetItem, QInputDialog)
from PyQt5.QtCore import QDate, Qt, QSize, QSettings, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QDoubleValidator, QPalette, QLinearGradient
from PyQt5.QtWidgets import QMenuBar, QStatusBar
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import csv

class UserManager:

    def __init__(self):
        self.users_file = 'data/users.json'
        self.load_users()
        # Create icons directory if it doesn't exist
        os.makedirs('icons', exist_ok=True)

    def load_users(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as file:
                self.users = json.load(file)
        else:
            self.users = {}

    def save_users(self):
        with open(self.users_file, 'w') as file:
            json.dump(self.users, file, indent=4)

    def add_user(self, username, email, password):
        if username in self.users:
            return False, "Username already exists."
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        self.users[username] = {
            "email": email,
            "password": hashed_password.decode(),
            "reset_token": None,
            "token_expiry": None
        }
        self.save_users()
        return True, "User registered successfully."

    def verify_user(self, username, password):
        if username not in self.users:
            return False, "Username does not exist."
        user_data = self.users[username]
        if 'password' not in user_data:
            return False, "User data is corrupted."
        hashed_password = user_data["password"].encode()
        if bcrypt.checkpw(password.encode(), hashed_password):
            return True, "Login successful."
        return False, "Incorrect password."

    def request_reset(self, username_or_email):
        for username, details in self.users.items():
            if username == username_or_email or details["email"] == username_or_email:
                token = secrets.token_urlsafe(32)
                expiry = (datetime.now() + timedelta(hours=1)).isoformat()
                self.users[username]["reset_token"] = token
                self.users[username]["token_expiry"] = expiry
                self.save_users()
                self.send_reset_email(details["email"], token)
                return True, "Reset token sent to your email."
        return False, "Username or email not found."

    def reset_password(self, token, new_password):
        for username, details in self.users.items():
            if details["reset_token"] == token and details["token_expiry"] > datetime.now().isoformat():
                hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
                self.users[username]["password"] = hashed_password.decode()
                self.users[username]["reset_token"] = None
                self.users[username]["token_expiry"] = None
                self.save_users()
                return True, "Password reset successfully."
        return False, "Invalid or expired token."

    def send_reset_email(self, email, token):
        try:
            # Directly set the SendGrid API key here or use another secure method
            sendgrid_api_key = 'YOUR_SENDGRID_API_KEY'
            if not sendgrid_api_key:
                raise ValueError("SendGrid API key is not set.")

            sg = SendGridAPIClient(sendgrid_api_key)
            from_email = "noreply@financedocmanager.com"
            to_email = email
            subject = "Password Reset Request"
            body = (
                f"Hello,\n\n"
                f"We received a request to reset your password. Use the following token to reset your password:\n\n"
                f"Token: {token}\n\n"
                f"If you did not request a password reset, please ignore this email.\n\n"
                f"Best regards,\n"
                f"FinanceDocManager Team"
            )

            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=body)

            response = sg.send(message)
            print(f"Email sent successfully: {response.status_code}")
        except ValueError as ve:
            print(f"Configuration error: {ve}")
        except Exception as e:
            print(f"Failed to send email: {e}")

class DocumentManagerApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal Information & Document Manager")
        self.setGeometry(100, 100, 1600, 1000)  # Set a fixed height of 980
        self.setFixedHeight(1000)  # Ensure the height is fixed

        # Modern color palette
        self.primary_color = "#2c3e50"
        self.secondary_color = "#3498db"
        self.accent_color = "#e74c3c"
        self.light_color = "#ecf0f1"
        self.dark_color = "#34495e"

        # Set application-wide style
        self.setStyleSheet(self.get_stylesheet())

        # Set application icon
        self.set_application_icon()

        # Initialize data
        self.transactions = []
        self.documents = {
            "aadhar": [],
            "pan": [],
            "bank_accounts": [],
            "driving_license": [],
            "certificates": []
        }
        self.categories = {
            "Income": ["Salary", "Bonus", "Gift", "Investment", "Other"],
            "Expense": ["Food", "Transport", "Housing", "Entertainment", "Healthcare", "Education", "Shopping", "Other"]
        }

        # Create data directories if they don't exist
        self.data_dir = "data"
        self.documents_dir = os.path.join(self.data_dir, "documents")
        os.makedirs(self.documents_dir, exist_ok=True)

        self.load_data()
        self.init_ui()
        self.update_balance()

        # Add some visual polish
        self.setWindowOpacity(0.0)
        self.fade_in()

    def get_stylesheet(self):
        return f"""
            /* Main Window */
            QMainWindow {{
                background-color: {self.light_color};
                border: 1px solid {self.primary_color};
                border-radius: 8px;
            }}

            /* General Widgets */
            QWidget {{
                font-family: 'Segoe UI', Arial, sans-serif;
                color: {self.dark_color};
            }}

            /* Group Boxes */
            QGroupBox {{
                border: 2px solid {self.primary_color};
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 20px;
                font-weight: bold;
                background-color: white;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {self.primary_color};
                font-size: 16px;
            }}

            /* Buttons */
            QPushButton {{
                background-color: {self.secondary_color};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
                min-width: 80px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #2980b9;
            }}
            QPushButton:pressed {{
                background-color: {self.primary_color};
                padding: 9px 19px 7px 21px; /* Gives a pressed effect */
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
                color: #7f8c8d;
            }}

            /* Input Fields */
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QListWidget, QTableWidget {{
                padding: 10px;
                border: 1px solid #d6d6d6;
                border-radius: 6px;
                background-color: white;
                selection-background-color: {self.secondary_color};
                selection-color: white;
                min-width: 200px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {{
                border: 2px solid {self.secondary_color};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #d6d6d6;
                selection-background-color: {self.secondary_color};
                selection-color: white;
            }}

            /* Tables */
            QTableWidget {{
                border: 1px solid #d6d6d6;
                border-radius: 6px;
                gridline-color: #e0e0e0;
                alternate-background-color: #f8f9fa;
            }}
            QHeaderView::section {{
                background-color: {self.primary_color};
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                border-radius: 4px;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}

            /* Tabs */
            QTabWidget::pane {{
                border: 1px solid #d6d6d6;
                border-radius: 6px;
                padding: 5px;
                background: white;
                margin-top: 5px;
            }}
            QTabBar::tab {{
                background: #ecf0f1;
                padding: 15px 30px;
                border: 1px solid #d6d6d6;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                color: {self.dark_color};
                min-width: 150px;
            }}
            QTabBar::tab:selected {{
                background: white;
                border-bottom: 1px solid white;
                color: {self.primary_color};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background: #d6eaf8;
            }}

            /* Menu Bar */
            QMenuBar {{
                background-color: {self.primary_color};
                color: white;
                padding: 5px;
                border-radius: 6px;
            }}
            QMenuBar::item {{
                padding: 5px 15px;
                background: transparent;
                border-radius: 4px;
                color: white;
            }}
            QMenuBar::item:selected {{
                background: {self.secondary_color};
            }}
            QMenuBar::item:pressed {{
                background: #1a5276;
            }}
            QMenuBar::item:disabled {{
                color: #bdc3c7;
            }}
            QMenu {{
                background-color: white;
                border: 1px solid #d6d6d6;
                padding: 5px;
                border-radius: 6px;
            }}
            QMenu::item {{
                padding: 5px 25px 5px 20px;
            }}
            QMenu::item:selected {{
                background-color: {self.secondary_color};
                color: white;
            }}
            QMenu::separator {{
                height: 1px;
                background: #d6d6d6;
                margin: 5px 0;
            }}

            /* Status Bar */
            QStatusBar {{
                background-color: {self.primary_color};
                color: white;
                padding: 3px;
                border-radius: 6px;
            }}
            QStatusBar::item {{
                border: none;
            }}

            /* Scroll Bars */
            QScrollBar:vertical {{
                width: 12px;
                margin: 0;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {self.secondary_color};
                min-height: 20px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QScrollBar:horizontal {{
                height: 12px;
                margin: 0;
                background: transparent;
            }}
            QScrollBar::handle:horizontal {{
                background: {self.secondary_color};
                min-width: 20px;
                border-radius: 6px;
            }}

            /* Tool Tips */
            QToolTip {{
                background-color: #2c3e50;
                color: white;
                border: 1px solid #2c3e50;
                padding: 3px;
                border-radius: 3px;
                opacity: 230;
            }}

            /* Dialogs */
            QDialog {{
                background-color: white;
            }}
            QDialogButtonBox {{
                button-layout: 0; /* WinLayout */
            }}

            /* Checkboxes and Radio Buttons */
            QCheckBox, QRadioButton {{
                spacing: 8px;
            }}
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 16px;
                height: 16px;
            }}
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                background-color: {self.secondary_color};
                border: 1px solid {self.secondary_color};
            }}

            /* Progress Bars */
            QProgressBar {{
                border: 1px solid #d6d6d6;
                border-radius: 3px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {self.secondary_color};
                width: 10px;
            }}

            /* Special Styles for Login Form */
            QGroupBox#login_group {{
                border: 2px solid {self.secondary_color};
                background-color: white;
            }}
            QGroupBox#login_group::title {{
                color: {self.secondary_color};
                font-size: 16px;
            }}
            #login_button, #register_button {{
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }}

            /* Header Styles */
            #header QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: white;
            }}
            #balance_label {{
                font-size: 18px;
                font-weight: bold;
                color: white;
                padding: 10px 15px;
                background-color: {self.secondary_color};
                border-radius: 6px;
            }}
        """

    def set_application_icon(self):
        if os.path.exists('icons/app_icon.png'):
            self.setWindowIcon(QIcon('icons/app_icon.png'))
        else:
            # Create a simple default icon if none exists
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(self.secondary_color))
            self.setWindowIcon(QIcon(pixmap))

    def load_icon(self, icon_name, default_color=None):
        """Load an icon with fallback to a colored circle if not found"""
        icon_path = f'icons/{icon_name}'
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        else:
            # Create a simple colored circle as fallback
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            if default_color:
                painter.setBrush(QColor(default_color))
            else:
                painter.setBrush(QColor(self.secondary_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, 28, 28)
            painter.end()
            return QIcon(pixmap)

    def fade_in(self):
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.increase_opacity)
        self.fade_timer.start(30)  # 30ms interval for smooth fade

    def increase_opacity(self):
        current_opacity = self.windowOpacity()
        if current_opacity < 1.0:
            self.setWindowOpacity(current_opacity + 0.05)
        else:
            self.fade_timer.stop()

    def init_ui(self):
        # Initialize filter_category to avoid AttributeError
        self.filter_category = QComboBox()

        # Create main tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)  # Modern tab look
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)

        # Finance Section
        self.init_finance_tab()

        # Document Management Section
        self.init_documents_tab()

        # Main layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins
        main_layout.setSpacing(10)  # Reduced spacing

        # Header with balance
        header = self.create_header()
        main_layout.addWidget(header)

        # Login Form
        self.login_group = self.create_login_form()
        main_layout.addWidget(self.login_group)

        # User info display (shown after login)
        self.user_info_widget = self.create_user_info_widget()
        main_layout.addWidget(self.user_info_widget)
        self.user_info_widget.setVisible(False)

        # Add tabs to the layout
        main_layout.addWidget(self.tabs, 1)

        self.setCentralWidget(main_widget)

        # Create menu bar
        self.create_menu_bar()

        # Status bar
        self.statusBar().setStyleSheet(f"background-color: {self.primary_color}; color: white;")
        self.statusBar().showMessage("Ready")

        # Initially hide the tabs
        self.tabs.setVisible(False)

        # Initialize UserManager
        self.user_manager = UserManager()

        # Check for remembered user
        self.check_remembered_user()

    def create_header(self):
        header = QWidget()
        header.setStyleSheet(f"background-color: {self.primary_color}; border-radius: 8px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 5, 15, 5)  # Reduced margins
        header_layout.setSpacing(15)  # Reduced spacing

        title = QLabel("Personal Information & Document Manager")
        title.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: white;
        """)

        self.balance_label = QLabel()
        self.balance_label.setStyleSheet("""
            font-size: 16px;  # Reduced font size
            font-weight: bold;
            color: white;
            padding: 8px 12px;  # Reduced padding
            background-color: {self.secondary_color};
            border-radius: 6px;
        """)
        self.update_balance()

        # Advanced Search Bar
        search_bar_layout = QHBoxLayout()
        search_bar_layout.setSpacing(8)  # Reduced spacing

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search transactions and documents...")
        self.search_bar.textChanged.connect(self.perform_search)
        search_bar_layout.addWidget(self.search_bar)

        self.advanced_search_button = QPushButton("Advanced Search")
        self.advanced_search_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: 1px solid white;
                padding: 4px 8px;  # Reduced padding
                border-radius: 3px;
                font-size: 11px;  # Reduced font size
            }
            QPushButton:hover {
                background-color: white;
                color: {self.primary_color};
            }
        """)
        self.advanced_search_button.clicked.connect(self.show_advanced_search_dialog)
        search_bar_layout.addWidget(self.advanced_search_button)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.balance_label)
        header_layout.addLayout(search_bar_layout)

        return header

    def show_advanced_search_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Advanced Search")
        dialog.setModal(True)
        dialog.setMinimumWidth(350)  # Reduced width
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #2c3e50;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(15, 15, 15, 15)  # Reduced margins
        layout.setSpacing(12)  # Reduced spacing

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setVerticalSpacing(12)  # Reduced spacing
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.search_keyword = QLineEdit()
        self.search_keyword.setPlaceholderText("Enter keywords...")
        form_layout.addRow("Keywords:", self.search_keyword)

        self.search_date_from = QDateEdit()
        self.search_date_from.setCalendarPopup(True)
        self.search_date_from.setDate(QDate.currentDate().addMonths(-1))
        form_layout.addRow("Date From:", self.search_date_from)

        self.search_date_to = QDateEdit()
        self.search_date_to.setCalendarPopup(True)
        self.search_date_to.setDate(QDate.currentDate())
        form_layout.addRow("Date To:", self.search_date_to)

        self.search_amount_from = QLineEdit()
        self.search_amount_from.setPlaceholderText("Minimum amount")
        self.search_amount_from.setValidator(QDoubleValidator())
        form_layout.addRow("Amount From:", self.search_amount_from)

        self.search_amount_to = QLineEdit()
        self.search_amount_to.setPlaceholderText("Maximum amount")
        self.search_amount_to.setValidator(QDoubleValidator())
        form_layout.addRow("Amount To:", self.search_amount_to)

        self.search_sort_by = QComboBox()
        self.search_sort_by.addItems(["Date", "Amount", "Category"])
        form_layout.addRow("Sort By:", self.search_sort_by)

        self.search_sort_order = QComboBox()
        self.search_sort_order.addItems(["Ascending", "Descending"])
        form_layout.addRow("Sort Order:", self.search_sort_order)

        btn_search = QPushButton("Search")
        btn_search.setIcon(QIcon('icons/search.png'))
        btn_search.clicked.connect(lambda: self.perform_advanced_search(dialog))
        form_layout.addRow(btn_search)

        layout.addLayout(form_layout)
        dialog.setLayout(layout)
        dialog.exec_()

    def perform_advanced_search(self, dialog):
        keyword = self.search_keyword.text().lower()
        date_from = self.search_date_from.date().toString(Qt.ISODate)
        date_to = self.search_date_to.date().toString(Qt.ISODate)
        amount_from = self.search_amount_from.text()
        amount_to = self.search_amount_to.text()
        sort_by = self.search_sort_by.currentText()
        sort_order = self.search_sort_order.currentText()

        filtered_transactions = []
        for trans in self.transactions:
            if (keyword in trans["description"].lower() or not keyword) and \
               (date_from <= trans["date"] <= date_to) and \
               (not amount_from or float(amount_from) <= trans["amount"]) and \
               (not amount_to or float(amount_to) >= trans["amount"]):
                filtered_transactions.append(trans)

        if sort_by == "Date":
            filtered_transactions.sort(key=lambda x: x["date"], reverse=(sort_order == "Descending"))
        elif sort_by == "Amount":
            filtered_transactions.sort(key=lambda x: x["amount"], reverse=(sort_order == "Descending"))
        elif sort_by == "Category":
            filtered_transactions.sort(key=lambda x: x["category"], reverse=(sort_order == "Descending"))

        self.load_transactions(filtered_transactions)

        dialog.accept()

    def show_search_results_popup(self, query, results):
        # Create a frame to act as a popup
        popup = QFrame(self)
        popup.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #d6d6d6;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: #2c3e50;
                font-size: 16px;
                font-weight: bold;
            }
            QListWidget {
                border: none;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
        """)
        popup.setWindowFlags(Qt.Popup)

        # Calculate the position of the popup
        search_bar_global_pos = self.search_bar.mapToGlobal(QPoint(0, 0))
        popup_x = search_bar_global_pos.x()
        popup_y = search_bar_global_pos.y() + self.search_bar.height()
        popup.setGeometry(popup_x, popup_y, 550, 350)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create a list widget for search results
        results_list = QListWidget()
        results_list.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
            }
        """)

        # Populate the list with search results
        for category, items in results.items():
            if items:  # Only add categories that have results
                category_item = QListWidgetItem(category)
                category_item.setFlags(Qt.NoItemFlags)  # Make category non-selectable
                category_item.setBackground(QColor("#f0f0f0"))
                category_item.setForeground(QColor("#3498db"))
                font = category_item.font()
                font.setBold(True)
                category_item.setFont(font)
                results_list.addItem(category_item)
                
                for item in items:
                    # Store the original data reference in the item
                    list_item = QListWidgetItem(f"  • {item}")
                    list_item.setData(Qt.UserRole, (category, item))  # Store category and item data
                    results_list.addItem(list_item)

        # Connect item click to navigation function
        results_list.itemClicked.connect(lambda item: self.navigate_to_search_result(item))

        layout.addWidget(results_list)
        popup.setLayout(layout)
        popup.show()

    def navigate_to_search_result(self, item):
        # Get the stored data from the clicked item
        data = item.data(Qt.UserRole)
        if not data:
            return  # This was a category header
        
        category, item_text = data
        
        # Close the popup
        self.sender().parent().close()
        
        # Navigate to the appropriate tab and select the item
        if category == "Transactions":
            self.tabs.setCurrentIndex(0)  # Finance tab
            finance_tab = self.tabs.widget(0)
            finance_sub_tabs = finance_tab.findChild(QTabWidget)
            finance_sub_tabs.setCurrentIndex(1)  # Transactions sub-tab
            
            # Find and select the matching transaction
            for row in range(self.trans_table.rowCount()):
                table_item = self.trans_table.item(row, 4)  # Description column
                if table_item and item_text in table_item.text():
                    self.trans_table.selectRow(row)
                    break
        
        elif category == "Aadhar Cards":
            self.tabs.setCurrentIndex(1)  # Documents tab
            doc_sub_tabs = self.tabs.widget(1).findChild(QTabWidget)
            doc_sub_tabs.setCurrentIndex(0)  # Aadhar sub-tab
            
            # Find and select the matching Aadhar card
            for i in range(self.aadhar_list.count()):
                list_item = self.aadhar_list.item(i)
                if list_item and item_text in list_item.text():
                    self.aadhar_list.setCurrentItem(list_item)
                    self.display_aadhar_details(list_item)
                    break
        
        elif category == "PAN Cards":
            self.tabs.setCurrentIndex(1)  # Documents tab
            doc_sub_tabs = self.tabs.widget(1).findChild(QTabWidget)
            doc_sub_tabs.setCurrentIndex(1)  # PAN sub-tab
            
            # Find and select the matching PAN card
            for i in range(self.pan_list.count()):
                list_item = self.pan_list.item(i)
                if list_item and item_text in list_item.text():
                    self.pan_list.setCurrentItem(list_item)
                    self.display_pan_details(list_item)
                    break
        
        elif category == "Bank Accounts":
            self.tabs.setCurrentIndex(1)  # Documents tab
            doc_sub_tabs = self.tabs.widget(1).findChild(QTabWidget)
            doc_sub_tabs.setCurrentIndex(2)  # Bank sub-tab
            
            # Find and select the matching bank account
            for i in range(self.bank_list.count()):
                list_item = self.bank_list.item(i)
                if list_item and item_text in list_item.text():
                    self.bank_list.setCurrentItem(list_item)
                    self.display_bank_details(list_item)
                    break
        
        elif category == "Driving Licenses":
            self.tabs.setCurrentIndex(1)  # Documents tab
            doc_sub_tabs = self.tabs.widget(1).findChild(QTabWidget)
            doc_sub_tabs.setCurrentIndex(3)  # License sub-tab
            
            # Find and select the matching driving license
            for i in range(self.dl_list.count()):
                list_item = self.dl_list.item(i)
                if list_item and item_text in list_item.text():
                    self.dl_list.setCurrentItem(list_item)
                    self.display_dl_details(list_item)
                    break
        
        elif category == "Certificates":
            self.tabs.setCurrentIndex(1)  # Documents tab
            doc_sub_tabs = self.tabs.widget(1).findChild(QTabWidget)
            doc_sub_tabs.setCurrentIndex(4)  # Certificates sub-tab
            
            # Find and select the matching certificate
            for i in range(self.cert_list.count()):
                list_item = self.cert_list.item(i)
                if list_item and item_text in list_item.text():
                    self.cert_list.setCurrentItem(list_item)
                    self.display_cert_details(list_item)
                    break

    def highlight_search_query(self, query, results):
        highlighted_results = ""
        for category, items in results.items():
            highlighted_results += f"<h3>{category.capitalize()}</h3>"
            for item in items:
                highlighted_item = item.replace(query, f"<span style='background-color: yellow;'>{query}</span>")
                highlighted_results += f"<p>{highlighted_item}</p>"
        return highlighted_results

    def perform_search(self, query):
        if not query:
            self.load_transactions()
            self.update_aadhar_list()
            self.update_pan_list()
            self.update_bank_list()
            self.update_dl_list()
            self.update_cert_list()
            return

        query = query.lower()
        results = {
            "Transactions": [],
            "Aadhar Cards": [],
            "PAN Cards": [],
            "Bank Accounts": [],
            "Driving Licenses": [],
            "Certificates": []
        }

        # Search transactions
        for trans in self.transactions:
            if (query in trans["description"].lower() or
                query in trans["category"].lower() or
                query in trans["date"].lower() or
                query in str(trans["amount"])):
                results["Transactions"].append(
                    f"{trans['date']} - {trans['category']}: {trans['description']} (₹{trans['amount']})"
                )

        # Search Aadhar cards
        for aadhar in self.documents["aadhar"]:
            if (query in aadhar["name"].lower() or
                query in aadhar["number"].lower() or
                query in aadhar["dob"].lower() or
                query in aadhar["address"].lower()):
                results["Aadhar Cards"].append(
                    f"{aadhar['name']} ({aadhar['number']}) - {aadhar['dob']}"
                )

        # Search PAN cards
        for pan in self.documents["pan"]:
            if (query in pan["name"].lower() or
                query in pan["number"].lower() or
                query in pan["dob"].lower() or
                query in pan["address"].lower()):
                results["PAN Cards"].append(
                    f"{pan['name']} ({pan['number']}) - {pan['dob']}"
                )

        # Search Bank accounts
        for bank in self.documents["bank_accounts"]:
            if (query in bank["name"].lower() or
                query in bank["account_number"].lower() or
                query in bank["ifsc"].lower() or
                query in bank["branch"].lower() or
                query in bank["address"].lower()):
                results["Bank Accounts"].append(
                    f"{bank['name']} ({bank['account_number']}) - {bank['ifsc']}"
                )

        # Search Driving licenses
        for dl in self.documents["driving_license"]:
            if (query in dl["name"].lower() or
                query in dl["number"].lower() or
                query in dl["dob"].lower() or
                query in dl["address"].lower()):
                results["Driving Licenses"].append(
                    f"{dl['name']} ({dl['number']}) - {dl['dob']}"
                )

        # Search Certificates
        for cert in self.documents["certificates"]:
            if (query in cert["name"].lower() or
                query in cert["issuer"].lower() or
                query in cert["date"].lower() or
                query in cert["description"].lower()):
                results["Certificates"].append(
                    f"{cert['name']} ({cert['issuer']}) - {cert['date']}"
                )

        # Show search results popup
        self.show_search_results_popup(query, results)

    def create_login_form(self):
        login_group = QGroupBox("Login / Register")
        login_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3498db;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 25px;
                font-weight: bold;
                background-color: white;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #3498db;
            }
        """)

        login_layout = QVBoxLayout(login_group)
        login_layout.setContentsMargins(20, 20, 20, 20)
        login_layout.setSpacing(15)

        # Header with icon
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel()
        pixmap = QPixmap('icons/login.png').scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(pixmap)

        title_label = QLabel("Welcome to FinanceDocManager")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
        """)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        login_layout.addWidget(header)

        # Toggle button for Login/Register
        self.toggle_button = QPushButton("Switch to Register")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #3498db;
                border: 1px solid #3498db;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #3498db;
                color: white;
            }
            QPushButton:pressed {
                background-color: #3498db;
                border-color: #3498db;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle_login_register)
        login_layout.addWidget(self.toggle_button, alignment=Qt.AlignRight)

        # Create stacked widget to hold both forms
        self.login_stack = QStackedWidget()
        self.login_stack.setStyleSheet("background: transparent;")

        # Create login form
        self.login_form = self.create_login_widget()
        self.login_stack.addWidget(self.login_form)

        self.balance_label.setVisible(False)

        # Create register form
        self.register_form = self.create_register_widget()
        self.login_stack.addWidget(self.register_form)

        # Start with login form visible
        self.login_stack.setCurrentIndex(0)

        login_layout.addWidget(self.login_stack)

        # Footer with version info
        footer = QLabel("Version 1.0 | © 2025 FinanceDocManager")
        footer.setStyleSheet("""
            color: #7f8c8d;
            font-size: 10px;
            qproperty-alignment: AlignCenter;
        """)
        login_layout.addWidget(footer)

        return login_group

    def create_login_widget(self):
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QFormLayout(widget)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        layout.setVerticalSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Style for input fields
        input_style = """
            QLineEdit {
                padding: 10px;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """

        # Username field
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet(input_style)

        # Password field
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(input_style)

        # Remember me checkbox
        self.remember_me_checkbox = QCheckBox("Remember Me")
        self.remember_me_checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 8px;
                color: #34495e;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)

        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.login_button.clicked.connect(self.login)

        # Forgot password button
        self.forgot_password_button = QPushButton("Forgot Password?")
        self.forgot_password_button.setStyleSheet("""
            QPushButton {
                text-decoration: underline;
                color: #3498db;
                border: none;
                background: transparent;
                padding: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #2980b9;
            }
        """)
        self.forgot_password_button.setFlat(True)
        self.forgot_password_button.clicked.connect(self.show_forgot_password_dialog)

        # Add rows to form
        layout.addRow(QLabel("Username:"), self.username_input)
        layout.addRow(QLabel("Password:"), self.password_input)

        # Add checkbox and forgot password in same row
        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.remember_me_checkbox)
        bottom_row.addStretch()
        bottom_row.addWidget(self.forgot_password_button)
        layout.addRow(bottom_row)

        # Add login button centered
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.login_button)
        button_row.addStretch()
        layout.addRow(button_row)

        return widget

    def create_register_widget(self):
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QFormLayout(widget)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        layout.setVerticalSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Style for input fields
        input_style = """
            QLineEdit {
                padding: 10px;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
            QTextEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QTextEdit:focus {
                border: 1px solid #3498db;
            }
        """

        # Registration fields
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Choose a username")
        self.reg_username.setStyleSheet(input_style)

        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Your email address")
        self.reg_email.setStyleSheet(input_style)

        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Create a password")
        self.reg_password.setEchoMode(QLineEdit.Password)
        self.reg_password.setStyleSheet(input_style)

        self.reg_confirm_password = QLineEdit()
        self.reg_confirm_password.setPlaceholderText("Confirm your password")
        self.reg_confirm_password.setEchoMode(QLineEdit.Password)
        self.reg_confirm_password.setStyleSheet(input_style)

        # Password strength indicator
        self.password_strength = QLabel("Password Strength: ")
        self.password_strength.setStyleSheet("""
            font-size: 12px;
            color: #7f8c8d;
            font-style: italic;
        """)
        self.reg_password.textChanged.connect(self.update_password_strength)

        # Register button
        self.register_button = QPushButton("Register")
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #16a085;
            }
        """)
        self.register_button.clicked.connect(self.register_user)

        # Add rows to form
        layout.addRow("Username:", self.reg_username)
        layout.addRow("Email:", self.reg_email)
        layout.addRow("Password:", self.reg_password)
        layout.addRow("", self.password_strength)
        layout.addRow("Confirm Password:", self.reg_confirm_password)

        # Add register button centered
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.register_button)
        button_row.addStretch()
        layout.addRow(button_row)

        return widget

    def toggle_login_register(self):
        if self.login_stack.currentIndex() == 0:  # Currently showing login
            self.login_stack.setCurrentIndex(1)  # Show register
            self.toggle_button.setText("Switch to Login")
        else:
            self.login_stack.setCurrentIndex(0)  # Show login
            self.toggle_button.setText("Switch to Register")

    def create_user_info_widget(self):
        user_info_widget = QWidget()
        user_info_layout = QHBoxLayout(user_info_widget)
        user_info_layout.setContentsMargins(0, 0, 0, 0)

        self.username_display = QLabel()
        self.username_display.setStyleSheet(f"font-size: 16px; color: {self.dark_color};")

        self.logout_button = QPushButton("Logout")
        self.logout_button.setStyleSheet(f"""
            background-color: {self.accent_color};
            color: white;
            padding: 6px 12px;
        """)
        self.logout_button.clicked.connect(self.logout)

        user_info_layout.addWidget(self.username_display)
        user_info_layout.addStretch()
        user_info_layout.addWidget(self.logout_button)

        return user_info_widget

    def create_menu_bar(self):
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)  # For better cross-platform consistency

        # File menu
        file_menu = menubar.addMenu('File')

        backup_action = QAction('Backup Data', self)
        backup_action.setShortcut("Ctrl+B")
        backup_action.triggered.connect(self.backup_data)
        file_menu.addAction(backup_action)

        restore_action = QAction('Restore Data', self)
        restore_action.setShortcut("Ctrl+R")
        restore_action.triggered.connect(self.restore_data)
        file_menu.addAction(restore_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Profile menu
        profile_menu = menubar.addMenu('Profile')

        edit_profile_action = QAction('Edit Profile', self)
        edit_profile_action.triggered.connect(self.show_edit_profile_dialog)
        profile_menu.addAction(edit_profile_action)

        # Tools menu
        tools_menu = menubar.addMenu('Tools')

        calc_action = QAction('Calculator', self)
        calc_action.setShortcut("Ctrl+C")
        calc_action.triggered.connect(self.show_calculator)
        tools_menu.addAction(calc_action)

        add_tab_action = QAction('Add Custom Tab', self)
        add_tab_action.setShortcut("Ctrl+T")
        add_tab_action.triggered.connect(self.show_add_tab_dialog)
        tools_menu.addAction(add_tab_action)

        close_tab_action = QAction('Close Tab', self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(self.close_current_tab)
        tools_menu.addAction(close_tab_action)

        # Help menu
        help_menu = menubar.addMenu('Help')

        about_action = QAction('About', self)
        about_action.setShortcut("F1")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def init_finance_tab(self):
        """Initialize the finance management tab"""
        finance_tab = QWidget()
        finance_layout = QVBoxLayout(finance_tab)
        finance_layout.setContentsMargins(5, 5, 5, 5)
        finance_layout.setSpacing(10)

        # Add a close button to the tab header
        close_button = QPushButton("Close Tab")
        close_button.setStyleSheet("color: white;")
        close_button.clicked.connect(lambda: self.close_tab(self.tabs.indexOf(finance_tab)))
        finance_layout.addWidget(close_button, alignment=Qt.AlignRight)

        # Create sub-tabs for finance section
        finance_sub_tabs = QTabWidget()
        finance_sub_tabs.setDocumentMode(True)
        finance_sub_tabs.setTabPosition(QTabWidget.North)

        # Add Transaction Tab
        add_trans_tab = QWidget()
        self.init_add_transaction_tab(add_trans_tab)

        # View Transactions Tab
        view_trans_tab = QWidget()
        self.init_view_transactions_tab(view_trans_tab)

        # Statistics Tab
        stats_tab = QWidget()
        self.init_stats_tab(stats_tab)

        finance_sub_tabs.addTab(add_trans_tab, "Add Transaction")
        finance_sub_tabs.addTab(view_trans_tab, "Transactions")
        finance_sub_tabs.addTab(stats_tab, "Statistics")

        finance_layout.addWidget(finance_sub_tabs)
        self.tabs.addTab(finance_tab, QIcon('icons/finance.png'), "Finance")

    def init_documents_tab(self):
        """Initialize the document management tab"""
        documents_tab = QWidget()
        documents_layout = QVBoxLayout(documents_tab)
        documents_layout.setContentsMargins(5, 5, 5, 5)
        documents_layout.setSpacing(5)

        # Add a close button to the tab header
        close_button = QPushButton("Close Tab")
        close_button.setStyleSheet("color: white;")
        close_button.clicked.connect(lambda: self.close_tab(self.tabs.indexOf(documents_tab)))
        documents_layout.addWidget(close_button, alignment=Qt.AlignRight)

        # Create sub-tabs for document types
        doc_sub_tabs = QTabWidget()
        doc_sub_tabs.setDocumentMode(True)
        doc_sub_tabs.setTabPosition(QTabWidget.North)

        # Aadhar Card Tab
        aadhar_tab = QWidget()
        self.init_aadhar_tab(aadhar_tab)

        # PAN Card Tab
        pan_tab = QWidget()
        self.init_pan_tab(pan_tab)

        # Bank Accounts Tab
        bank_tab = QWidget()
        self.init_bank_tab(bank_tab)

        # Driving License Tab
        dl_tab = QWidget()
        self.init_dl_tab(dl_tab)

        # Certificates Tab
        cert_tab = QWidget()
        self.init_certificates_tab(cert_tab)

        doc_sub_tabs.addTab(aadhar_tab, QIcon('icons/aadhar.png'), "Aadhar")
        doc_sub_tabs.addTab(pan_tab, QIcon('icons/pan.png'), "PAN")
        doc_sub_tabs.addTab(bank_tab, QIcon('icons/bank.png'), "Bank")
        doc_sub_tabs.addTab(dl_tab, QIcon('icons/license.png'), "License")
        doc_sub_tabs.addTab(cert_tab, QIcon('icons/certificate.png'), "Certificates")

        documents_layout.addWidget(doc_sub_tabs)
        self.tabs.addTab(documents_tab, QIcon('icons/documents.png'), "Documents")

    def init_aadhar_tab(self, tab):
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Left side - Form for new Aadhar entry
        form_group = QGroupBox("Add Aadhar Card Details")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setVerticalSpacing(10)

        self.aadhar_name = QLineEdit()
        self.aadhar_name.setPlaceholderText("Full name as on Aadhar")
        self.aadhar_number = QLineEdit()
        self.aadhar_number.setInputMask("9999 9999 9999")
        self.aadhar_number.setPlaceholderText("12-digit Aadhar number")
        self.aadhar_dob = QDateEdit()
        self.aadhar_dob.setCalendarPopup(True)
        self.aadhar_dob.setDate(QDate.currentDate().addYears(-30))

        self.aadhar_front_img = QLabel("Front Image: Not selected")
        self.aadhar_back_img = QLabel("Back Image: Not selected")

        btn_front = QPushButton("Select Front Image")
        btn_front.setIcon(QIcon('icons/image.png'))
        btn_front.clicked.connect(lambda: self.select_document_image("aadhar_front"))

        btn_back = QPushButton("Select Back Image")
        btn_back.setIcon(QIcon('icons/image.png'))
        btn_back.clicked.connect(lambda: self.select_document_image("aadhar_back"))

        btn_save = QPushButton("Save Aadhar Details")
        btn_save.setIcon(self.load_icon('save.png', '#2ecc71'))
        btn_save.clicked.connect(self.save_aadhar_details)

        form_layout.addRow("Full Name:", self.aadhar_name)
        form_layout.addRow("Aadhar Number:", self.aadhar_number)
        form_layout.addRow("Date of Birth:", self.aadhar_dob)
        form_layout.addRow(btn_front, self.aadhar_front_img)
        form_layout.addRow(btn_back, self.aadhar_back_img)
        form_layout.addRow(btn_save)

        form_group.setLayout(form_layout)

        # Right side - List of saved Aadhar cards
        list_group = QGroupBox("Saved Aadhar Cards")
        list_layout = QVBoxLayout()
        list_layout.setSpacing(8)

        self.aadhar_list = QListWidget()
        self.aadhar_list.setIconSize(QSize(32, 32))
        self.aadhar_list.itemClicked.connect(self.display_aadhar_details)
        self.aadhar_list.setStyleSheet("QListWidget::item { padding: 5px; }")

        self.aadhar_details_display = QTextEdit()
        self.aadhar_details_display.setReadOnly(True)
        self.aadhar_details_display.setStyleSheet("""
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
        """)

        # Search bar for Aadhar cards
        self.aadhar_search_bar = QLineEdit()
        self.aadhar_search_bar.setPlaceholderText("Search Aadhar cards...")
        self.aadhar_search_bar.textChanged.connect(self.filter_aadhar_list)

        list_layout.addWidget(self.aadhar_search_bar)
        list_layout.addWidget(self.aadhar_list)
        list_layout.addWidget(QLabel("Details:"))
        list_layout.addWidget(self.aadhar_details_display)

        list_group.setLayout(list_layout)

        # Add both groups to main layout
        layout.addWidget(form_group, 40)
        layout.addWidget(list_group, 60)

        self.update_aadhar_list()

    def filter_aadhar_list(self, query):
        query = query.lower()
        filtered_aadhar = [
            aadhar for aadhar in self.documents["aadhar"]
            if query in aadhar["name"].lower() or
            query in aadhar["number"].lower() or
            query in aadhar["dob"].lower() or
            query in aadhar["address"].lower()
        ]
        self.update_aadhar_list(filtered_aadhar)

    def init_pan_tab(self, tab):
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Left side - Form for new PAN entry
        form_group = QGroupBox("Add PAN Card Details")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setVerticalSpacing(10)

        self.pan_name = QLineEdit()
        self.pan_name.setPlaceholderText("Full name as on PAN")
        self.pan_number = QLineEdit()
        self.pan_number.setInputMask("AAAAA9999A")
        self.pan_number.setPlaceholderText("10-character PAN number")
        self.pan_dob = QDateEdit()
        self.pan_dob.setCalendarPopup(True)
        self.pan_dob.setDate(QDate.currentDate().addYears(-30))
        self.pan_address = QTextEdit()
        self.pan_address.setMaximumHeight(150)  # Increased height for address field
        self.pan_address.setPlaceholderText("Full address as on PAN")

        self.pan_front_img = QLabel("Front Image: Not selected")

        btn_front = QPushButton("Select Front Image")
        btn_front.setIcon(QIcon('icons/image.png'))
        btn_front.clicked.connect(lambda: self.select_document_image("pan_front"))

        btn_save = QPushButton("Save PAN Details")
        btn_save.setIcon(QIcon('icons/save.png'))
        btn_save.clicked.connect(self.save_pan_details)

        form_layout.addRow("Full Name:", self.pan_name)
        form_layout.addRow("PAN Number:", self.pan_number)
        form_layout.addRow("Date of Birth:", self.pan_dob)
        form_layout.addRow("Address:", self.pan_address)
        form_layout.addRow(btn_front, self.pan_front_img)
        form_layout.addRow(btn_save)

        form_group.setLayout(form_layout)

        # Right side - List of saved PAN cards
        list_group = QGroupBox("Saved PAN Cards")
        list_layout = QVBoxLayout()
        list_layout.setSpacing(8)

        self.pan_list = QListWidget()
        self.pan_list.setIconSize(QSize(32, 32))
        self.pan_list.itemClicked.connect(self.display_pan_details)
        self.pan_list.setStyleSheet("QListWidget::item { padding: 5px; }")

        self.pan_details_display = QTextEdit()
        self.pan_details_display.setReadOnly(True)
        self.pan_details_display.setStyleSheet("""
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
        """)

        # Search bar for PAN cards
        self.pan_search_bar = QLineEdit()
        self.pan_search_bar.setPlaceholderText("Search PAN cards...")
        self.pan_search_bar.textChanged.connect(self.filter_pan_list)

        list_layout.addWidget(self.pan_search_bar)
        list_layout.addWidget(self.pan_list)
        list_layout.addWidget(QLabel("Details:"))
        list_layout.addWidget(self.pan_details_display)

        list_group.setLayout(list_layout)

        # Add both groups to main layout
        layout.addWidget(form_group, 40)
        layout.addWidget(list_group, 60)

        self.update_pan_list()

    def filter_pan_list(self, query):
        query = query.lower()
        filtered_pan = [
            pan for pan in self.documents["pan"]
            if query in pan["name"].lower() or
            query in pan["number"].lower() or
            query in pan["dob"].lower() or
            query in pan["address"].lower()
        ]
        self.update_pan_list(filtered_pan)

    def init_bank_tab(self, tab):
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Left side - Form for new Bank Account entry
        form_group = QGroupBox("Add Bank Account Details")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setVerticalSpacing(10)

        self.bank_name = QLineEdit()
        self.bank_name.setPlaceholderText("Bank name")
        self.bank_account_number = QLineEdit()
        self.bank_account_number.setPlaceholderText("Bank account number")
        self.bank_ifsc = QLineEdit()
        self.bank_ifsc.setPlaceholderText("IFSC code")
        self.bank_branch = QLineEdit()
        self.bank_branch.setPlaceholderText("Branch name")

        self.bank_passbook_img = QLabel("Passbook Image: Not selected")

        btn_passbook = QPushButton("Select Passbook Image")
        btn_passbook.setIcon(QIcon('icons/image.png'))
        btn_passbook.clicked.connect(lambda: self.select_document_image("bank_passbook"))

        btn_save = QPushButton("Save Bank Account Details")
        btn_save.setIcon(QIcon('icons/save.png'))
        btn_save.clicked.connect(self.save_bank_details)

        form_layout.addRow("Bank Name:", self.bank_name)
        form_layout.addRow("Account Number:", self.bank_account_number)
        form_layout.addRow("IFSC Code:", self.bank_ifsc)
        form_layout.addRow("Branch Name:", self.bank_branch)
        form_layout.addRow(btn_passbook, self.bank_passbook_img)
        form_layout.addRow(btn_save)

        form_group.setLayout(form_layout)

        # Right side - List of saved Bank Accounts
        list_group = QGroupBox("Saved Bank Accounts")
        list_layout = QVBoxLayout()
        list_layout.setSpacing(8)

        self.bank_list = QListWidget()
        self.bank_list.setIconSize(QSize(32, 32))
        self.bank_list.itemClicked.connect(self.display_bank_details)
        self.bank_list.setStyleSheet("QListWidget::item { padding: 5px; }")

        self.bank_details_display = QTextEdit()
        self.bank_details_display.setReadOnly(True)
        self.bank_details_display.setStyleSheet("""
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
        """)

        # Search bar for Bank Accounts
        self.bank_search_bar = QLineEdit()
        self.bank_search_bar.setPlaceholderText("Search Bank Accounts...")
        self.bank_search_bar.textChanged.connect(self.filter_bank_list)

        list_layout.addWidget(self.bank_search_bar)
        list_layout.addWidget(self.bank_list)
        list_layout.addWidget(QLabel("Details:"))
        list_layout.addWidget(self.bank_details_display)

        list_group.setLayout(list_layout)

        # Add both groups to main layout
        layout.addWidget(form_group, 40)
        layout.addWidget(list_group, 60)

        self.update_bank_list()

    def filter_bank_list(self, query):
        query = query.lower()
        filtered_bank = [
            bank for bank in self.documents["bank_accounts"]
            if query in bank["name"].lower() or
            query in bank["account_number"].lower() or
            query in bank["ifsc"].lower() or
            query in bank["branch"].lower() or
            query in bank["address"].lower()
        ]
        self.update_bank_list(filtered_bank)

    def init_dl_tab(self, tab):
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Left side - Form for new Driving License entry
        form_group = QGroupBox("Add Driving License Details")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setVerticalSpacing(10)

        self.dl_name = QLineEdit()
        self.dl_name.setPlaceholderText("Full name as on Driving License")
        self.dl_number = QLineEdit()
        self.dl_number.setPlaceholderText("Driving License number")
        self.dl_dob = QDateEdit()
        self.dl_dob.setCalendarPopup(True)
        self.dl_dob.setDate(QDate.currentDate().addYears(-30))

        self.dl_front_img = QLabel("Front Image: Not selected")
        self.dl_back_img = QLabel("Back Image: Not selected")

        btn_front = QPushButton("Select Front Image")
        btn_front.setIcon(QIcon('icons/image.png'))
        btn_front.clicked.connect(lambda: self.select_document_image("dl_front"))

        btn_back = QPushButton("Select Back Image")
        btn_back.setIcon(QIcon('icons/image.png'))
        btn_back.clicked.connect(lambda: self.select_document_image("dl_back"))

        btn_save = QPushButton("Save Driving License Details")
        btn_save.setIcon(QIcon('icons/save.png'))
        btn_save.clicked.connect(self.save_dl_details)

        form_layout.addRow("Full Name:", self.dl_name)
        form_layout.addRow("License Number:", self.dl_number)
        form_layout.addRow("Date of Birth:", self.dl_dob)
        form_layout.addRow(btn_front, self.dl_front_img)
        form_layout.addRow(btn_back, self.dl_back_img)
        form_layout.addRow(btn_save)

        form_group.setLayout(form_layout)

        # Right side - List of saved Driving Licenses
        list_group = QGroupBox("Saved Driving Licenses")
        list_layout = QVBoxLayout()
        list_layout.setSpacing(8)

        self.dl_list = QListWidget()
        self.dl_list.setIconSize(QSize(32, 32))
        self.dl_list.itemClicked.connect(self.display_dl_details)
        self.dl_list.setStyleSheet("QListWidget::item { padding: 5px; }")

        self.dl_details_display = QTextEdit()
        self.dl_details_display.setReadOnly(True)
        self.dl_details_display.setStyleSheet("""
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
        """)

        # Search bar for Driving Licenses
        self.dl_search_bar = QLineEdit()
        self.dl_search_bar.setPlaceholderText("Search Driving Licenses...")
        self.dl_search_bar.textChanged.connect(self.filter_dl_list)

        list_layout.addWidget(self.dl_search_bar)
        list_layout.addWidget(self.dl_list)
        list_layout.addWidget(QLabel("Details:"))
        list_layout.addWidget(self.dl_details_display)

        list_group.setLayout(list_layout)

        # Add both groups to main layout
        layout.addWidget(form_group, 40)
        layout.addWidget(list_group, 60)

        self.update_dl_list()

    def filter_dl_list(self, query):
        query = query.lower()
        filtered_dl = [
            dl for dl in self.documents["driving_license"]
            if query in dl["name"].lower() or
            query in dl["number"].lower() or
            query in dl["dob"].lower() or
            query in dl["address"].lower()
        ]
        self.update_dl_list(filtered_dl)

    def init_certificates_tab(self, tab):
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Left side - Form for new Certificate entry
        form_group = QGroupBox("Add Certificate Details")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setVerticalSpacing(10)

        self.cert_name = QLineEdit()
        self.cert_name.setPlaceholderText("Certificate name")
        self.cert_issuer = QLineEdit()
        self.cert_issuer.setPlaceholderText("Issuing authority")
        self.cert_date = QDateEdit()
        self.cert_date.setCalendarPopup(True)
        self.cert_date.setDate(QDate.currentDate())
        self.cert_description = QTextEdit()
        self.cert_description.setMaximumHeight(150)  # Increased height for description field
        self.cert_description.setPlaceholderText("Description of the certificate")

        self.cert_image = QLabel("Certificate Image: Not selected")

        btn_image = QPushButton("Select Certificate Image")
        btn_image.setIcon(QIcon('icons/image.png'))
        btn_image.clicked.connect(lambda: self.select_document_image("cert_image"))

        btn_save = QPushButton("Save Certificate Details")
        btn_save.setIcon(QIcon('icons/save.png'))
        btn_save.clicked.connect(self.save_cert_details)

        form_layout.addRow("Certificate Name:", self.cert_name)
        form_layout.addRow("Issuing Authority:", self.cert_issuer)
        form_layout.addRow("Issue Date:", self.cert_date)
        form_layout.addRow("Description:", self.cert_description)
        form_layout.addRow(btn_image, self.cert_image)
        form_layout.addRow(btn_save)

        form_group.setLayout(form_layout)

        # Right side - List of saved Certificates
        list_group = QGroupBox("Saved Certificates")
        list_layout = QVBoxLayout()
        list_layout.setSpacing(8)

        self.cert_list = QListWidget()
        self.cert_list.setIconSize(QSize(32, 32))
        self.cert_list.itemClicked.connect(self.display_cert_details)
        self.cert_list.setStyleSheet("QListWidget::item { padding: 5px; }")

        self.cert_details_display = QTextEdit()
        self.cert_details_display.setReadOnly(True)
        self.cert_details_display.setStyleSheet("""
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
        """)

        # Search bar for Certificates
        self.cert_search_bar = QLineEdit()
        self.cert_search_bar.setPlaceholderText("Search Certificates...")
        self.cert_search_bar.textChanged.connect(self.filter_cert_list)

        list_layout.addWidget(self.cert_search_bar)
        list_layout.addWidget(self.cert_list)
        list_layout.addWidget(QLabel("Details:"))
        list_layout.addWidget(self.cert_details_display)

        list_group.setLayout(list_layout)

        # Add both groups to main layout
        layout.addWidget(form_group, 40)
        layout.addWidget(list_group, 60)

        self.update_cert_list()

    def filter_cert_list(self, query):
        query = query.lower()
        filtered_cert = [
            cert for cert in self.documents["certificates"]
            if query in cert["name"].lower() or
            query in cert["issuer"].lower() or
            query in cert["date"].lower() or
            query in cert["description"].lower()
        ]
        self.update_cert_list(filtered_cert)

    def init_add_transaction_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        form_group = QGroupBox("Add Transaction")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setVerticalSpacing(8)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.trans_type = QComboBox()
        self.trans_type.addItems(["Income", "Expense"])
        self.trans_category = QComboBox()
        self.trans_date = QDateEdit()
        self.trans_date.setCalendarPopup(True)
        self.trans_date.setDate(QDate.currentDate())
        self.trans_amount = QLineEdit()
        self.trans_amount.setValidator(QDoubleValidator())
        self.trans_amount.setPlaceholderText("0.00")
        self.trans_description = QTextEdit()
        self.trans_description.setMaximumHeight(100)
        self.trans_description.setPlaceholderText("Optional description")

        form_layout.addRow("Type:", self.trans_type)
        form_layout.addRow("Category:", self.trans_category)
        form_layout.addRow("Date:", self.trans_date)
        form_layout.addRow("Amount (₹):", self.trans_amount)
        form_layout.addRow("Description:", self.trans_description)

        btn_save_trans = QPushButton("Save Transaction")
        btn_save_trans.setIcon(QIcon('icons/save.png'))
        btn_save_trans.clicked.connect(self.save_transaction)
        form_layout.addRow(btn_save_trans)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        self.trans_type.currentIndexChanged.connect(self.update_categories)
        self.update_categories()

    def init_view_transactions_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Filter controls
        filter_group = QGroupBox("Filter Transactions")
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        self.filter_type = QComboBox()
        self.filter_type.addItems(["All", "Income", "Expense"])

        self.filter_category = QComboBox()
        self.filter_category.addItem("All Categories")

        self.filter_from_date = QDateEdit()
        self.filter_from_date.setCalendarPopup(True)
        self.filter_from_date.setDate(QDate.currentDate().addMonths(-1))

        self.filter_to_date = QDateEdit()
        self.filter_to_date.setCalendarPopup(True)
        self.filter_to_date.setDate(QDate.currentDate())

        btn_filter = QPushButton("Apply Filter")
        btn_filter.setIcon(QIcon('icons/filter.png'))
        btn_filter.clicked.connect(self.apply_transaction_filter)

        btn_reset = QPushButton("Reset")
        btn_reset.setIcon(QIcon('icons/reset.png'))
        btn_reset.clicked.connect(self.reset_transaction_filter)

        filter_layout.addWidget(QLabel("Type:"))
        filter_layout.addWidget(self.filter_type)
        filter_layout.addWidget(QLabel("Category:"))
        filter_layout.addWidget(self.filter_category)
        filter_layout.addWidget(QLabel("From:"))
        filter_layout.addWidget(self.filter_from_date)
        filter_layout.addWidget(QLabel("To:"))
        filter_layout.addWidget(self.filter_to_date)
        filter_layout.addWidget(btn_filter)
        filter_layout.addWidget(btn_reset)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Transactions table
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(7)
        self.trans_table.setHorizontalHeaderLabels(["Date", "Type", "Category", "Amount", "Description", "Actions", "Edit"])
        self.trans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trans_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.trans_table.verticalHeader().setVisible(False)
        self.trans_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.trans_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.trans_table.setAlternatingRowColors(True)

        # Set row height to make rows wider
        self.trans_table.verticalHeader().setDefaultSectionSize(50)  # Adjust the value as needed

        self.trans_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)

        self.load_transactions()

        layout.addWidget(self.trans_table, 1)

    def init_stats_tab(self, tab):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # Summary cards
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(8)

        # Income card
        income_card = QGroupBox("Income")
        income_card.setStyleSheet("""
            QGroupBox {
                border: 2px solid #2ecc71;
            }
        """)
        income_layout = QVBoxLayout()
        income_layout.setAlignment(Qt.AlignCenter)
        self.income_label = QLabel("₹0.00")
        self.income_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2ecc71;
            qproperty-alignment: AlignCenter;
        """)
        income_layout.addWidget(self.income_label)
        income_card.setLayout(income_layout)

        # Expense card
        expense_card = QGroupBox("Expense")
        expense_card.setStyleSheet("""
            QGroupBox {
                border: 2px solid #e74c3c;
            }
        """)
        expense_layout = QVBoxLayout()
        expense_layout.setAlignment(Qt.AlignCenter)
        self.expense_label = QLabel("₹0.00")
        self.expense_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #e74c3c;
            qproperty-alignment: AlignCenter;
        """)
        expense_layout.addWidget(self.expense_label)
        expense_card.setLayout(expense_layout)

        # Balance card
        balance_card = QGroupBox("Balance")
        balance_card.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3498db;
            }
        """)
        balance_layout = QVBoxLayout()
        balance_layout.setAlignment(Qt.AlignCenter)
        self.balance_stats_label = QLabel("₹0.00")
        self.balance_stats_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
            qproperty-alignment: AlignCenter;
        """)
        balance_layout.addWidget(self.balance_stats_label)
        balance_card.setLayout(balance_layout)

        summary_layout.addWidget(income_card, 1)
        summary_layout.addWidget(expense_card, 1)
        summary_layout.addWidget(balance_card, 1)
        layout.addLayout(summary_layout)

        # Charts area
        charts_group = QGroupBox("Statistics")
        charts_layout = QVBoxLayout()

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setStyleSheet("""
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
            font-family: monospace;
        """)

        # Add a button to generate detailed report
        report_button = QPushButton("Generate Detailed Report")
        report_button.clicked.connect(self.generate_detailed_report)
        charts_layout.addWidget(report_button)

        # Add a button to show charts
        charts_button = QPushButton("Show Charts")
        charts_button.clicked.connect(self.show_charts)
        charts_layout.addWidget(charts_button)

        charts_layout.addWidget(self.stats_text)
        charts_group.setLayout(charts_layout)
        layout.addWidget(charts_group, 1)

        self.update_stats()

    def showEvent(self, event):
        super().showEvent(event)
        # Disable the maximize button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        self.show()

    def login(self):
        try:
            username = self.username_input.text()
            password = self.password_input.text()
            remember_me = self.remember_me_checkbox.isChecked()

            if not username or not password:
                QMessageBox.warning(self, "Error", "Please enter both username and password")
                return

            # Show loading state
            self.login_button.setEnabled(False)
            self.login_button.setText("Logging in...")
            QApplication.processEvents()  # Force UI update

            success, message = self.user_manager.verify_user(username, password)

            if success:
                # Successful login
                self.current_user = username

                # Hide the entire login group
                self.login_group.setVisible(False)

                # Display the username
                self.username_display.setText(f"Welcome, {username}")
                self.user_info_widget.setVisible(True)

                # Show the main tabs
                self.tabs.setVisible(True)

                # Update the balance display
                self.update_balance()

                # If remember me is checked, store username (but never password)
                if remember_me:
                    settings = QSettings("FinanceDocManager", "AppSettings")
                    settings.setValue("remembered_user", username)
                else:
                    settings = QSettings("FinanceDocManager", "AppSettings")
                    settings.remove("remembered_user")

                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.warning(self, "Error", message)

            # Reset login button
            self.login_button.setEnabled(True)
            self.login_button.setText("Login")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def register_user(self):
        try:
            username = self.reg_username.text()
            email = self.reg_email.text()
            password = self.reg_password.text()
            confirm_password = self.reg_confirm_password.text()

            if not username or not email or not password or not confirm_password:
                QMessageBox.warning(self, "Error", "Please fill in all fields.")
                return

            if password != confirm_password:
                QMessageBox.warning(self, "Error", "Passwords do not match.")
                return

            success, message = self.user_manager.add_user(username, email, password)
            if success:
                QMessageBox.information(self, "Success", message)
                self.toggle_login_register()  # Switch back to login mode
            else:
                QMessageBox.warning(self, "Error", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def update_password_strength(self):
        try:
            password = self.reg_password.text()
            strength = "Weak"
            if len(password) >= 8:
                strength = "Medium"
            if len(password) >= 12 and any(char.isupper() for char in password) and any(char.islower() for char in password) and any(char.isdigit() for char in password):
                strength = "Strong"

            strength_color = {
                "Weak": "red",
                "Medium": "orange",
                "Strong": "green"
            }

            self.password_strength.setText(f"Password Strength: <font color='{strength_color[strength]}'>{strength}</font>")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def show_forgot_password_dialog(self):
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Password Reset")
            dialog.setModal(True)
            dialog.setMinimumWidth(400)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                }
                QLabel {
                    color: #2c3e50;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(8)

            # Step 1: Request reset
            step1 = QWidget()
            step1_layout = QVBoxLayout(step1)
            step1_layout.setSpacing(8)

            step1_layout.addWidget(QLabel("Enter your username or email:"))

            self.reset_username_input = QLineEdit()
            self.reset_username_input.setPlaceholderText("username or email")
            step1_layout.addWidget(self.reset_username_input)

            btn_request_reset = QPushButton("Request Reset")
            btn_request_reset.clicked.connect(lambda: self.handle_reset_request(dialog))
            step1_layout.addWidget(btn_request_reset)

            step1.setLayout(step1_layout)

            # Step 2: Enter token and new password
            step2 = QWidget()
            step2_layout = QVBoxLayout(step2)
            step2_layout.setSpacing(8)

            step2_layout.addWidget(QLabel("Check your email for the reset token"))

            self.reset_token_input = QLineEdit()
            self.reset_token_input.setPlaceholderText("paste token here")
            step2_layout.addWidget(self.reset_token_input)

            step2_layout.addWidget(QLabel("New Password:"))
            self.new_password_input = QLineEdit()
            self.new_password_input.setPlaceholderText("minimum 8 characters")
            self.new_password_input.setEchoMode(QLineEdit.Password)
            step2_layout.addWidget(self.new_password_input)

            step2_layout.addWidget(QLabel("Confirm New Password:"))
            self.confirm_new_password_input = QLineEdit()
            self.confirm_new_password_input.setPlaceholderText("must match above")
            self.confirm_new_password_input.setEchoMode(QLineEdit.Password)
            step2_layout.addWidget(self.confirm_new_password_input)

            btn_complete_reset = QPushButton("Reset Password")
            btn_complete_reset.clicked.connect(lambda: self.handle_password_reset(dialog))
            step2_layout.addWidget(btn_complete_reset)

            step2.setLayout(step2_layout)
            step2.setVisible(False)

            # Stacked widget to switch between steps
            self.reset_stack = QStackedWidget()
            self.reset_stack.addWidget(step1)
            self.reset_stack.addWidget(step2)

            layout.addWidget(self.reset_stack)
            dialog.setLayout(layout)

            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def handle_reset_request(self, dialog):
        try:
            username_or_email = self.reset_username_input.text()
            if not username_or_email:
                QMessageBox.warning(self, "Error", "Please enter your username or email.")
                return

            success, message = self.user_manager.request_reset(username_or_email)
            if success:
                QMessageBox.information(self, "Success", message)
                self.reset_stack.setCurrentIndex(1)
            else:
                QMessageBox.warning(self, "Error", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def handle_password_reset(self, dialog):
        try:
            token = self.reset_token_input.text()
            new_password = self.new_password_input.text()
            confirm_password = self.confirm_new_password_input.text()

            if not token or not new_password or not confirm_password:
                QMessageBox.warning(self, "Error", "Please fill in all fields.")
                return

            if new_password != confirm_password:
                QMessageBox.warning(self, "Error", "Passwords do not match.")
                return

            success, message = self.user_manager.reset_password(token, new_password)
            if success:
                QMessageBox.information(self, "Success", message)
                dialog.accept()
            else:
                QMessageBox.warning(self, "Error", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def logout(self):
        # Hide the tabs and show the login form
        self.tabs.setVisible(False)
        self.user_info_widget.setVisible(False)

        # Show login group
        self.login_group.setVisible(True)

        # Clear the inputs
        self.username_input.clear()
        self.password_input.clear()

        # Reset current user
        self.current_user = None

    def save_transaction(self):
        try:
            trans_type = self.trans_type.currentText()
            category = self.trans_category.currentText()
            date = self.trans_date.date().toString(Qt.ISODate)
            amount = self.trans_amount.text()
            description = self.trans_description.toPlainText()

            if not amount:
                QMessageBox.warning(self, "Error", "Amount cannot be empty.")
                return

            try:
                amount = float(amount)
            except ValueError:
                QMessageBox.warning(self, "Error", "Invalid amount format.")
                return

            transaction = {
                "type": trans_type,
                "category": category,
                "date": date,
                "amount": amount,
                "description": description
            }

            self.transactions.append(transaction)
            self.save_data()
            self.load_transactions()
            self.update_balance()
            self.update_stats()
            QMessageBox.information(self, "Success", "Transaction saved successfully.")

            # Clear the form
            self.trans_amount.clear()
            self.trans_description.clear()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def load_transactions(self, filtered_transactions=None):
        try:
            self.trans_table.setRowCount(0)
            transactions = filtered_transactions if filtered_transactions else self.transactions

            for row, transaction in enumerate(transactions):
                self.trans_table.insertRow(row)
                self.trans_table.setItem(row, 0, QTableWidgetItem(transaction["date"]))
                self.trans_table.setItem(row, 1, QTableWidgetItem(transaction["type"]))
                self.trans_table.setItem(row, 2, QTableWidgetItem(transaction["category"]))
                self.trans_table.setItem(row, 3, QTableWidgetItem(f"₹{transaction['amount']:.2f}"))
                self.trans_table.setItem(row, 4, QTableWidgetItem(transaction["description"]))

                delete_button = QPushButton("Delete")
                delete_button.setStyleSheet("color: red;")
                delete_button.clicked.connect(lambda _, r=row: self.delete_transaction(r))
                self.trans_table.setCellWidget(row, 5, delete_button)

                edit_button = QPushButton("Edit")
                edit_button.setStyleSheet("color: blue;")
                edit_button.clicked.connect(lambda _, r=row: self.edit_transaction(r))
                self.trans_table.setCellWidget(row, 6, edit_button)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def edit_transaction(self, row):
        try:
            transaction = self.transactions[row]
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Transaction")
            dialog.setModal(True)
            dialog.setMinimumWidth(400)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                }
                QLabel {
                    color: #2c3e50;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(8)

            form_layout = QFormLayout()
            form_layout.setLabelAlignment(Qt.AlignRight)
            form_layout.setVerticalSpacing(15)
            form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

            trans_type = QComboBox()
            trans_type.addItems(["Income", "Expense"])
            trans_type.setCurrentText(transaction["type"])
            trans_category = QComboBox()
            trans_category.addItems(self.categories[transaction["type"]])
            trans_category.setCurrentText(transaction["category"])
            trans_date = QDateEdit()
            trans_date.setCalendarPopup(True)
            trans_date.setDate(QDate.fromString(transaction["date"], Qt.ISODate))
            trans_amount = QLineEdit()
            trans_amount.setValidator(QDoubleValidator())
            trans_amount.setText(str(transaction["amount"]))
            trans_description = QTextEdit()
            trans_description.setMaximumHeight(100)
            trans_description.setText(transaction["description"])

            form_layout.addRow("Type:", trans_type)
            form_layout.addRow("Category:", trans_category)
            form_layout.addRow("Date:", trans_date)
            form_layout.addRow("Amount (₹):", trans_amount)
            form_layout.addRow("Description:", trans_description)

            btn_save_trans = QPushButton("Save Changes")
            btn_save_trans.setIcon(QIcon('icons/save.png'))
            btn_save_trans.clicked.connect(lambda: self.save_edited_transaction(dialog, row, trans_type, trans_category, trans_date, trans_amount, trans_description))
            form_layout.addRow(btn_save_trans)

            layout.addLayout(form_layout)
            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_edited_transaction(self, dialog, row, trans_type, trans_category, trans_date, trans_amount, trans_description):
        try:
            type = trans_type.currentText()
            category = trans_category.currentText()
            date = trans_date.date().toString(Qt.ISODate)
            amount = trans_amount.text()
            description = trans_description.toPlainText()

            if not amount:
                QMessageBox.warning(self, "Error", "Amount cannot be empty.")
                return

            try:
                amount = float(amount)
            except ValueError:
                QMessageBox.warning(self, "Error", "Invalid amount format.")
                return

            self.transactions[row] = {
                "type": type,
                "category": category,
                "date": date,
                "amount": amount,
                "description": description
            }

            self.save_data()
            self.load_transactions()
            self.update_balance()
            self.update_stats()
            QMessageBox.information(self, "Success", "Transaction updated successfully.")
            dialog.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def delete_transaction(self, row):
        try:
            # Show confirmation dialog
            confirm = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this transaction?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if confirm == QMessageBox.Yes:
                self.trans_table.removeRow(row)
                del self.transactions[row]
                self.save_data()
                self.update_balance()
                self.update_stats()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def apply_transaction_filter(self):
        try:
            trans_type = self.filter_type.currentText()
            category = self.filter_category.currentText()
            from_date = self.filter_from_date.date().toString(Qt.ISODate)
            to_date = self.filter_to_date.date().toString(Qt.ISODate)

            filtered_transactions = [
                trans for trans in self.transactions
                if (trans_type == "All" or trans["type"] == trans_type) and
                (category == "All Categories" or trans["category"] == category) and
                (from_date <= trans["date"] <= to_date)
            ]

            self.load_transactions(filtered_transactions)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def reset_transaction_filter(self):
        try:
            self.filter_type.setCurrentIndex(0)
            self.filter_category.setCurrentIndex(0)
            self.filter_from_date.setDate(QDate.currentDate().addMonths(-1))
            self.filter_to_date.setDate(QDate.currentDate())
            self.load_transactions()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def update_categories(self):
        try:
            trans_type = self.trans_type.currentText()
            self.trans_category.clear()
            self.trans_category.addItems(self.categories[trans_type])
            self.filter_category.clear()
            self.filter_category.addItem("All Categories")
            self.filter_category.addItems(self.categories[trans_type])

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def update_balance(self):
        try:
            total_income = sum(trans["amount"] for trans in self.transactions if trans["type"] == "Income")
            total_expense = sum(trans["amount"] for trans in self.transactions if trans["type"] == "Expense")
            balance = total_income - total_expense
            self.balance_label.setText(f"Balance: ₹{balance:.2f}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def update_stats(self):
        try:
            total_income = sum(trans["amount"] for trans in self.transactions if trans["type"] == "Income")
            total_expense = sum(trans["amount"] for trans in self.transactions if trans["type"] == "Expense")
            balance = total_income - total_expense

            self.income_label.setText(f"₹{total_income:.2f}")
            self.expense_label.setText(f"₹{total_expense:.2f}")
            self.balance_stats_label.setText(f"₹{balance:.2f}")

            stats_text = f"""
            Total Income: ₹{total_income:.2f}
            Total Expense: ₹{total_expense:.2f}
            Balance: ₹{balance:.2f}
            """
            self.stats_text.setText(stats_text)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def select_document_image(self, doc_type):
        try:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)", options=options)
            if file_name:
                # Copy the selected image to the documents directory
                doc_path = os.path.join(self.documents_dir, os.path.basename(file_name))
                shutil.copy(file_name, doc_path)

                if doc_type == "aadhar_front":
                    self.aadhar_front_img.setText(f"Front Image: {doc_path}")
                    self.aadhar_front_img.setStyleSheet("color: green;")
                elif doc_type == "aadhar_back":
                    self.aadhar_back_img.setText(f"Back Image: {doc_path}")
                    self.aadhar_back_img.setStyleSheet("color: green;")
                elif doc_type == "pan_front":
                    self.pan_front_img.setText(f"Front Image: {doc_path}")
                    self.pan_front_img.setStyleSheet("color: green;")
                elif doc_type == "bank_passbook":
                    self.bank_passbook_img.setText(f"Passbook Image: {doc_path}")
                    self.bank_passbook_img.setStyleSheet("color: green;")
                elif doc_type == "dl_front":
                    self.dl_front_img.setText(f"Front Image: {doc_path}")
                    self.dl_front_img.setStyleSheet("color: green;")
                elif doc_type == "dl_back":
                    self.dl_back_img.setText(f"Back Image: {doc_path}")
                    self.dl_back_img.setStyleSheet("color: green;")
                elif doc_type == "cert_image":
                    self.cert_image.setText(f"Certificate Image: {doc_path}")
                    self.cert_image.setStyleSheet("color: green;")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_aadhar_details(self):
        try:
            name = self.aadhar_name.text()
            number = self.aadhar_number.text()
            dob = self.aadhar_dob.date().toString(Qt.ISODate)
            address = self.aadhar_address.toPlainText()
            front_image = self.aadhar_front_img.text().split(": ")[1]
            back_image = self.aadhar_back_img.text().split(": ")[1]

            if not name or not number or not dob or not address or not front_image or not back_image:
                QMessageBox.warning(self, "Error", "Please fill in all fields and select images.")
                return

            if not self.validate_aadhar_number(number):
                QMessageBox.warning(self, "Error", "Invalid Aadhar number format.")
                return

            aadhar_details = {
                "name": name,
                "number": number,
                "dob": dob,
                "address": address,
                "front_image": os.path.basename(front_image),
                "back_image": os.path.basename(back_image)
            }

            self.documents["aadhar"].append(aadhar_details)
            self.save_data()
            self.update_aadhar_list()
            QMessageBox.information(self, "Success", "Aadhar details saved successfully.")

            # Clear the form
            self.aadhar_name.clear()
            self.aadhar_number.clear()
            self.aadhar_address.clear()
            self.aadhar_front_img.setText("Front Image: Not selected")
            self.aadhar_back_img.setText("Back Image: Not selected")
            self.aadhar_front_img.setStyleSheet("")
            self.aadhar_back_img.setStyleSheet("")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def validate_aadhar_number(self, number):
        # Aadhar number should be 12 digits
        return len(number) == 12 and number.isdigit()

    def update_aadhar_list(self, filtered_aadhar=None):
        try:
            self.aadhar_list.clear()
            aadhar_list = filtered_aadhar if filtered_aadhar else self.documents["aadhar"]
            for aadhar in aadhar_list:
                item = QListWidgetItem(f"{aadhar['name']} ({aadhar['number']})")
                item.setIcon(QIcon('icons/aadhar.png'))
                self.aadhar_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def display_aadhar_details(self, item):
        try:
            aadhar = self.documents["aadhar"][self.aadhar_list.row(item)]
            details = f"""
            Name: {aadhar['name']}
            Aadhar Number: {aadhar['number']}
            Date of Birth: {aadhar['dob']}
            Address: {aadhar['address']}
            Front Image: {aadhar['front_image']}
            Back Image: {aadhar['back_image']}
            """
            self.aadhar_details_display.setText(details)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_pan_details(self):
        try:
            name = self.pan_name.text()
            number = self.pan_number.text()
            dob = self.pan_dob.date().toString(Qt.ISODate)
            address = self.pan_address.toPlainText()
            front_image = self.pan_front_img.text().split(": ")[1]

            if not name or not number or not dob or not address or not front_image:
                QMessageBox.warning(self, "Error", "Please fill in all fields and select images.")
                return

            if not self.validate_pan_number(number):
                QMessageBox.warning(self, "Error", "Invalid PAN number format.")
                return

            pan_details = {
                "name": name,
                "number": number,
                "dob": dob,
                "address": address,
                "front_image": os.path.basename(front_image)
            }

            self.documents["pan"].append(pan_details)
            self.save_data()
            self.update_pan_list()
            QMessageBox.information(self, "Success", "PAN details saved successfully.")

            # Clear the form
            self.pan_name.clear()
            self.pan_number.clear()
            self.pan_address.clear()
            self.pan_front_img.setText("Front Image: Not selected")
            self.pan_front_img.setStyleSheet("")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def validate_pan_number(self, number):
        # PAN number should be 10 characters long with the format AAAAA9999A
        return bool(re.match(r'^[A-Z]{5}\d{4}[A-Z]\$', number))

    def update_pan_list(self, filtered_pan=None):
        try:
            self.pan_list.clear()
            pan_list = filtered_pan if filtered_pan else self.documents["pan"]
            for pan in pan_list:
                item = QListWidgetItem(f"{pan['name']} ({pan['number']})")
                item.setIcon(QIcon('icons/pan.png'))
                self.pan_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def display_pan_details(self, item):
        try:
            pan = self.documents["pan"][self.pan_list.row(item)]
            details = f"""
            Name: {pan['name']}
            PAN Number: {pan['number']}
            Date of Birth: {pan['dob']}
            Address: {pan['address']}
            Front Image: {pan['front_image']}
            """
            self.pan_details_display.setText(details)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_bank_details(self):
        try:
            name = self.bank_name.text()
            account_number = self.bank_account_number.text()
            ifsc = self.bank_ifsc.text()
            branch = self.bank_branch.text()
            address = self.bank_address.toPlainText()
            passbook_image = self.bank_passbook_img.text().split(": ")[1]

            if not name or not account_number or not ifsc or not branch or not address or not passbook_image:
                QMessageBox.warning(self, "Error", "Please fill in all fields and select images.")
                return

            if not self.validate_ifsc_code(ifsc):
                QMessageBox.warning(self, "Error", "Invalid IFSC code format.")
                return

            bank_details = {
                "name": name,
                "account_number": account_number,
                "ifsc": ifsc,
                "branch": branch,
                "address": address,
                "passbook_image": os.path.basename(passbook_image)
            }

            self.documents["bank_accounts"].append(bank_details)
            self.save_data()
            self.update_bank_list()
            QMessageBox.information(self, "Success", "Bank account details saved successfully.")

            # Clear the form
            self.bank_name.clear()
            self.bank_account_number.clear()
            self.bank_ifsc.clear()
            self.bank_branch.clear()
            self.bank_address.clear()
            self.bank_passbook_img.setText("Passbook Image: Not selected")
            self.bank_passbook_img.setStyleSheet("")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def validate_ifsc_code(self, ifsc):
        # IFSC code should be 11 characters long and alphanumeric
        return bool(re.match(r'^[A-Za-z]{4}0[A-Z0-9]{6}\$', ifsc))

    def update_bank_list(self, filtered_bank=None):
        try:
            self.bank_list.clear()
            bank_list = filtered_bank if filtered_bank else self.documents["bank_accounts"]
            for bank in bank_list:
                item = QListWidgetItem(f"{bank['name']} ({bank['account_number']})")
                item.setIcon(QIcon('icons/bank.png'))
                self.bank_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def display_bank_details(self, item):
        try:
            bank = self.documents["bank_accounts"][self.bank_list.row(item)]
            details = f"""
            Bank Name: {bank['name']}
            Account Number: {bank['account_number']}
            IFSC Code: {bank['ifsc']}
            Branch Name: {bank['branch']}
            Address: {bank['address']}
            Passbook Image: {bank['passbook_image']}
            """
            self.bank_details_display.setText(details)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_dl_details(self):
        try:
            name = self.dl_name.text()
            number = self.dl_number.text()
            dob = self.dl_dob.date().toString(Qt.ISODate)
            address = self.dl_address.toPlainText()
            front_image = self.dl_front_img.text().split(": ")[1]
            back_image = self.dl_back_img.text().split(": ")[1]

            if not name or not number or not dob or not address or not front_image or not back_image:
                QMessageBox.warning(self, "Error", "Please fill in all fields and select images.")
                return

            dl_details = {
                "name": name,
                "number": number,
                "dob": dob,
                "address": address,
                "front_image": os.path.basename(front_image),
                "back_image": os.path.basename(back_image)
            }

            self.documents["driving_license"].append(dl_details)
            self.save_data()
            self.update_dl_list()
            QMessageBox.information(self, "Success", "Driving license details saved successfully.")

            # Clear the form
            self.dl_name.clear()
            self.dl_number.clear()
            self.dl_address.clear()
            self.dl_front_img.setText("Front Image: Not selected")
            self.dl_back_img.setText("Back Image: Not selected")
            self.dl_front_img.setStyleSheet("")
            self.dl_back_img.setStyleSheet("")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def update_dl_list(self, filtered_dl=None):
        try:
            self.dl_list.clear()
            dl_list = filtered_dl if filtered_dl else self.documents["driving_license"]
            for dl in dl_list:
                item = QListWidgetItem(f"{dl['name']} ({dl['number']})")
                item.setIcon(QIcon('icons/license.png'))
                self.dl_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def display_dl_details(self, item):
        try:
            dl = self.documents["driving_license"][self.dl_list.row(item)]
            details = f"""
            Name: {dl['name']}
            License Number: {dl['number']}
            Date of Birth: {dl['dob']}
            Address: {dl['address']}
            Front Image: {dl['front_image']}
            Back Image: {dl['back_image']}
            """
            self.dl_details_display.setText(details)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_cert_details(self):
        try:
            name = self.cert_name.text()
            issuer = self.cert_issuer.text()
            date = self.cert_date.date().toString(Qt.ISODate)
            description = self.cert_description.toPlainText()
            image = self.cert_image.text().split(": ")[1]

            if not name or not issuer or not date or not description or not image:
                QMessageBox.warning(self, "Error", "Please fill in all fields and select images.")
                return

            cert_details = {
                "name": name,
                "issuer": issuer,
                "date": date,
                "description": description,
                "image": os.path.basename(image)
            }

            self.documents["certificates"].append(cert_details)
            self.save_data()
            self.update_cert_list()
            QMessageBox.information(self, "Success", "Certificate details saved successfully.")

            # Clear the form
            self.cert_name.clear()
            self.cert_issuer.clear()
            self.cert_description.clear()
            self.cert_image.setText("Certificate Image: Not selected")
            self.cert_image.setStyleSheet("")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def update_cert_list(self, filtered_cert=None):
        try:
            self.cert_list.clear()
            cert_list = filtered_cert if filtered_cert else self.documents["certificates"]
            for cert in cert_list:
                item = QListWidgetItem(f"{cert['name']} ({cert['issuer']})")
                item.setIcon(QIcon('icons/certificate.png'))
                self.cert_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def display_cert_details(self, item):
        try:
            cert = self.documents["certificates"][self.cert_list.row(item)]
            details = f"""
            Certificate Name: {cert['name']}
            Issuing Authority: {cert['issuer']}
            Issue Date: {cert['date']}
            Description: {cert['description']}
            Certificate Image: {cert['image']}
            """
            self.cert_details_display.setText(details)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_data(self):
        try:
            data = {
                "transactions": self.transactions,
                "documents": self.documents
            }
            with open(os.path.join(self.data_dir, 'data.json'), 'w') as file:
                json.dump(data, file, indent=4)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def load_data(self):
        try:
            data_file = os.path.join(self.data_dir, 'data.json')
            if os.path.exists(data_file):
                with open(data_file, 'r') as file:
                    data = json.load(file)
                    self.transactions = data.get("transactions", [])
                    self.documents = data.get("documents", {
                        "aadhar": [],
                        "pan": [],
                        "bank_accounts": [],
                        "driving_license": [],
                        "certificates": []
                    })

                    # Load document images
                    for doc_type, docs in self.documents.items():
                        for doc in docs:
                            for key in ["front_image", "back_image", "passbook_image", "image"]:
                                if key in doc:
                                    doc[key] = os.path.join(self.documents_dir, doc[key])

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def backup_data(self):
        try:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "Backup Data", "", "CSV Files (*.csv);;JSON Files (*.json);;XML Files (*.xml)", options=options)
            if file_name:
                if file_name.endswith('.csv'):
                    self.save_data_as_csv(file_name)
                elif file_name.endswith('.json'):
                    self.save_data_as_json(file_name)
                elif file_name.endswith('.xml'):
                    self.save_data_as_xml(file_name)
                QMessageBox.information(self, "Success", "Data backed up successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")


    def save_data_as_csv(self, file_name):
        try:
            with open(file_name, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Type", "Category", "Date", "Amount", "Description"])
                for transaction in self.transactions:
                    writer.writerow([transaction["type"], transaction["category"], transaction["date"], transaction["amount"], transaction["description"]])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_data_as_json(self, file_name):
        try:
            data = {
                "transactions": self.transactions,
                "documents": self.documents
            }
            with open(file_name, 'w') as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_data_as_xml(self, file_name):
        try:
            root = ET.Element("data")

            transactions = ET.SubElement(root, "transactions")
            for trans in self.transactions:
                trans_elem = ET.SubElement(transactions, "transaction")
                for key, value in trans.items():
                    ET.SubElement(trans_elem, key).text = str(value)

            documents = ET.SubElement(root, "documents")
            for doc_type, docs in self.documents.items():
                doc_type_elem = ET.SubElement(documents, doc_type)
                for doc in docs:
                    doc_elem = ET.SubElement(doc_type_elem, "document")
                    for key, value in doc.items():
                        ET.SubElement(doc_elem, key).text = str(value)

            tree = ET.ElementTree(root)
            tree.write(file_name, encoding='utf-8', xml_declaration=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def restore_data(self):
        try:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getOpenFileName(self, "Restore Data", "", "JSON Files (*.json);;CSV Files (*.csv);;XML Files (*.xml)", options=options)
            if file_name:
                if file_name.endswith('.json'):
                    self.load_data_from_json(file_name)
                elif file_name.endswith('.csv'):
                    self.load_data_from_csv(file_name)
                elif file_name.endswith('.xml'):
                    self.load_data_from_xml(file_name)
                else:
                    QMessageBox.warning(self, "Error", "Unsupported file format.")
                    return

                self.load_transactions()
                self.update_balance()
                self.update_stats()
                self.update_aadhar_list()
                self.update_pan_list()
                self.update_bank_list()
                self.update_dl_list()
                self.update_cert_list()
                QMessageBox.information(self, "Success", "Data restored successfully.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def load_data_from_json(self, file_name):
        try:
            with open(file_name, 'r') as file:
                data = json.load(file)
                self.transactions = data.get("transactions", [])
                self.documents = data.get("documents", {
                    "aadhar": [],
                    "pan": [],
                    "bank_accounts": [],
                    "driving_license": [],
                    "certificates": []
                })

                # Load document images
                for doc_type, docs in self.documents.items():
                    for doc in docs:
                        for key in ["front_image", "back_image", "passbook_image", "image"]:
                            if key in doc:
                                doc[key] = os.path.join(self.documents_dir, doc[key])

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def load_data_from_csv(self, file_name):
        try:
            self.transactions = []
            self.documents = {
                "aadhar": [],
                "pan": [],
                "bank_accounts": [],
                "driving_license": [],
                "certificates": []
            }

            with open(file_name, mode='r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    transaction = {
                        "type": row["Type"],
                        "category": row["Category"],
                        "date": row["Date"],
                        "amount": float(row["Amount"]),
                        "description": row["Description"]
                    }
                    self.transactions.append(transaction)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def load_data_from_xml(self, file_name):
        try:
            self.transactions = []
            self.documents = {
                "aadhar": [],
                "pan": [],
                "bank_accounts": [],
                "driving_license": [],
                "certificates": []
            }

            tree = ET.parse(file_name)
            root = tree.getroot()

            for trans_elem in root.findall(".//transaction"):
                transaction = {
                    "type": trans_elem.find("type").text,
                    "category": trans_elem.find("category").text,
                    "date": trans_elem.find("date").text,
                    "amount": float(trans_elem.find("amount").text),
                    "description": trans_elem.find("description").text
                }
                self.transactions.append(transaction)

            for doc_type in self.documents.keys():
                for doc_elem in root.findall(f".//{doc_type}/document"):
                    doc = {}
                    for key in doc_elem:
                        doc[key.tag] = key.text
                    self.documents[doc_type].append(doc)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def show_calculator(self):
        try:
            os.system("calc.exe")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def show_about(self):
        QMessageBox.about(self, "About", "Personal Information & Document Manager\nVersion 1.0\nDeveloped by Debmalya Ray")

    def check_remembered_user(self):
        try:
            settings = QSettings("FinanceDocManager", "AppSettings")
            remembered_user = settings.value("remembered_user")
            if remembered_user:
                self.username_input.setText(remembered_user)
                self.remember_me_checkbox.setChecked(True)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def show_add_tab_dialog(self):
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Add Custom Tab")
            dialog.setModal(True)
            dialog.setMinimumWidth(400)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                }
                QLabel {
                    color: #2c3e50;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(8)

            # Tab name input
            tab_name_label = QLabel("Tab Name:")
            self.tab_name_input = QLineEdit()
            self.tab_name_input.setPlaceholderText("Enter the name of the new tab")
            layout.addWidget(tab_name_label)
            layout.addWidget(self.tab_name_input)

            # Fields input
            fields_label = QLabel("Fields (comma-separated):")
            self.fields_input = QLineEdit()
            self.fields_input.setPlaceholderText("Enter the fields for the new tab")
            layout.addWidget(fields_label)
            layout.addWidget(self.fields_input)

            # Add button
            add_button = QPushButton("Add Tab")
            add_button.setIcon(QIcon('icons/add.png'))
            add_button.clicked.connect(lambda: self.add_custom_tab(dialog))
            layout.addWidget(add_button)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def add_custom_tab(self, dialog):
        try:
            tab_name = self.tab_name_input.text()
            fields = self.fields_input.text()

            if not tab_name or not fields:
                QMessageBox.warning(self, "Error", "Please enter both the tab name and fields.")
                return

            # Create a new tab with the specified name and fields
            new_tab = QWidget()
            self.init_custom_tab(new_tab, tab_name, fields.split(','))

            # Add the new tab to the main tab widget
            self.tabs.addTab(new_tab, QIcon('icons/custom.png'), tab_name)

            # Close the dialog
            dialog.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def init_custom_tab(self, tab, tab_name, fields):
        try:
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(8)

            # Add a close button to the tab header
            close_button = QPushButton("Close Tab")
            close_button.setStyleSheet("color: white;")
            close_button.clicked.connect(lambda: self.close_tab(self.tabs.indexOf(tab)))
            layout.addWidget(close_button, alignment=Qt.AlignRight)

            # Create a form group for adding new entries
            form_group = QGroupBox(f"Add {tab_name} Details")
            form_layout = QFormLayout()
            form_layout.setLabelAlignment(Qt.AlignRight)
            form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
            form_layout.setVerticalSpacing(10)

            # Create input fields dynamically based on the provided fields
            self.custom_inputs = {}
            for field in fields:
                field = field.strip()
                label = QLabel(field.capitalize())
                input_field = QLineEdit()
                input_field.setPlaceholderText(f"Enter {field}")
                form_layout.addRow(label, input_field)
                self.custom_inputs[field] = input_field

            # Add a save button
            save_button = QPushButton("Save Details")
            save_button.setIcon(QIcon('icons/save.png'))
            save_button.clicked.connect(lambda: self.save_custom_details(tab_name))
            form_layout.addRow(save_button)

            form_group.setLayout(form_layout)
            layout.addWidget(form_group)

            # Create a list group for displaying saved entries
            list_group = QGroupBox(f"Saved {tab_name} Details")
            list_layout = QVBoxLayout()
            list_layout.setSpacing(8)

            self.custom_list = QListWidget()
            self.custom_list.setIconSize(QSize(32, 32))
            self.custom_list.itemClicked.connect(lambda item: self.display_custom_details(item, tab_name))
            self.custom_list.setStyleSheet("QListWidget::item { padding: 5px; }")

            self.custom_details_display = QTextEdit()
            self.custom_details_display.setReadOnly(True)
            self.custom_details_display.setStyleSheet("""
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            """)

            # Search bar for custom entries
            self.custom_search_bar = QLineEdit()
            self.custom_search_bar.setPlaceholderText(f"Search {tab_name} entries...")
            self.custom_search_bar.textChanged.connect(lambda query: self.filter_custom_list(query, tab_name))

            list_layout.addWidget(self.custom_search_bar)
            list_layout.addWidget(self.custom_list)
            list_layout.addWidget(QLabel("Details:"))
            list_layout.addWidget(self.custom_details_display)

            list_group.setLayout(list_layout)
            layout.addWidget(list_group)

            # Initialize the documents dictionary for the new tab
            if tab_name not in self.documents:
                self.documents[tab_name] = []

            # Update the list of saved entries
            self.update_custom_list(tab_name)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_custom_details(self, tab_name):
        try:
            details = {}
            for field, input_field in self.custom_inputs.items():
                details[field] = input_field.text()

            if any(value == "" for value in details.values()):
                QMessageBox.warning(self, "Error", "Please fill in all fields.")
                return

            self.documents[tab_name].append(details)
            self.save_data()
            self.update_custom_list(tab_name)
            QMessageBox.information(self, "Success", f"{tab_name} details saved successfully.")

            # Clear the form
            for input_field in self.custom_inputs.values():
                input_field.clear()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def update_custom_list(self, tab_name, filtered_custom=None):
        try:
            self.custom_list.clear()
            custom_list = filtered_custom if filtered_custom else self.documents[tab_name]
            for details in custom_list:
                item_text = ", ".join(f"{key}: {value}" for key, value in details.items())
                item = QListWidgetItem(item_text)
                item.setIcon(QIcon('icons/custom.png'))
                self.custom_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def display_custom_details(self, item, tab_name):
        try:
            details = self.documents[tab_name][self.custom_list.row(item)]
            details_text = "\n".join(f"{key}: {value}" for key, value in details.items())
            self.custom_details_display.setText(details_text)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def filter_custom_list(self, query, tab_name):
        query = query.lower()
        filtered_custom = [
            details for details in self.documents[tab_name]
            if any(query in value.lower() for value in details.values())
        ]
        self.update_custom_list(tab_name, filtered_custom)

    def close_tab(self, index):
        try:
            if index >= 0:
                # Show confirmation dialog
                confirm = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this tab?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

                if confirm == QMessageBox.Yes:
                    self.tabs.removeTab(index)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def close_current_tab(self):
        try:
            current_index = self.tabs.currentIndex()
            if current_index >= 0:
                # Show confirmation dialog
                confirm = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this tab?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

                if confirm == QMessageBox.Yes:
                    self.close_tab(current_index)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def show_edit_profile_dialog(self):
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Profile")
            dialog.setModal(True)
            dialog.setMinimumWidth(400)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                }
                QLabel {
                    color: #2c3e50;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(8)

            form_layout = QFormLayout()
            form_layout.setLabelAlignment(Qt.AlignRight)
            form_layout.setVerticalSpacing(15)
            form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

            username_label = QLabel("Username:")
            username_input = QLineEdit()
            username_input.setText(self.current_user)
            username_input.setReadOnly(True)

            email_label = QLabel("Email:")
            email_input = QLineEdit()
            email_input.setText(self.user_manager.users[self.current_user]["email"])

            password_label = QLabel("New Password:")
            password_input = QLineEdit()
            password_input.setEchoMode(QLineEdit.Password)
            password_input.setPlaceholderText("Leave blank if no change")

            confirm_password_label = QLabel("Confirm New Password:")
            confirm_password_input = QLineEdit()
            confirm_password_input.setEchoMode(QLineEdit.Password)
            confirm_password_input.setPlaceholderText("Leave blank if no change")

            form_layout.addRow(username_label, username_input)
            form_layout.addRow(email_label, email_input)
            form_layout.addRow(password_label, password_input)
            form_layout.addRow(confirm_password_label, confirm_password_input)

            btn_save_profile = QPushButton("Save Changes")
            btn_save_profile.setIcon(QIcon('icons/save.png'))
            btn_save_profile.clicked.connect(lambda: self.save_profile_changes(dialog, email_input, password_input, confirm_password_input))
            form_layout.addRow(btn_save_profile)

            layout.addLayout(form_layout)
            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def save_profile_changes(self, dialog, email_input, password_input, confirm_password_input):
        try:
            email = email_input.text()
            new_password = password_input.text()
            confirm_password = confirm_password_input.text()

            if new_password and new_password != confirm_password:
                QMessageBox.warning(self, "Error", "Passwords do not match.")
                return

            if new_password:
                hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
                self.user_manager.users[self.current_user]["password"] = hashed_password.decode()

            self.user_manager.users[self.current_user]["email"] = email
            self.user_manager.save_users()

            QMessageBox.information(self, "Success", "Profile updated successfully.")
            dialog.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def perform_search(self, query):
        if not query:
            self.load_transactions()
            self.update_aadhar_list()
            self.update_pan_list()
            self.update_bank_list()
            self.update_dl_list()
            self.update_cert_list()
            return

        query = query.lower()
        results = {
            "Transactions": [],
            "Aadhar Cards": [],
            "PAN Cards": [],
            "Bank Accounts": [],
            "Driving Licenses": [],
            "Certificates": []
        }

        # Search transactions
        filtered_transactions = [
            trans for trans in self.transactions
            if query in trans["description"].lower() or
            query in trans["category"].lower() or
            query in trans["date"].lower() or
            query in str(trans["amount"])
        ]
        for trans in filtered_transactions:
            results["Transactions"].append(f"{trans['date']} - {trans['category']}: {trans['description']} (₹{trans['amount']})")

        # Search Aadhar cards
        filtered_aadhar = [
            aadhar for aadhar in self.documents["aadhar"]
            if query in aadhar["name"].lower() or
            query in aadhar["number"].lower() or
            query in aadhar["dob"].lower() or
            query in aadhar["address"].lower()
        ]
        for aadhar in filtered_aadhar:
            results["Aadhar Cards"].append(f"{aadhar['name']} ({aadhar['number']}) - {aadhar['dob']}")

        # Search PAN cards
        filtered_pan = [
            pan for pan in self.documents["pan"]
            if query in pan["name"].lower() or
            query in pan["number"].lower() or
            query in pan["dob"].lower() or
            query in pan["address"].lower()
        ]
        for pan in filtered_pan:
            results["PAN Cards"].append(f"{pan['name']} ({pan['number']}) - {pan['dob']}")

        # Search Bank accounts
        filtered_bank = [
            bank for bank in self.documents["bank_accounts"]
            if query in bank["name"].lower() or
            query in bank["account_number"].lower() or
            query in bank["ifsc"].lower() or
            query in bank["branch"].lower() or
            query in bank["address"].lower()
        ]
        for bank in filtered_bank:
            results["Bank Accounts"].append(f"{bank['name']} ({bank['account_number']}) - {bank['ifsc']}")

        # Search Driving licenses
        filtered_dl = [
            dl for dl in self.documents["driving_license"]
            if query in dl["name"].lower() or
            query in dl["number"].lower() or
            query in dl["dob"].lower() or
            query in dl["address"].lower()
        ]
        for dl in filtered_dl:
            results["Driving Licenses"].append(f"{dl['name']} ({dl['number']}) - {dl['dob']}")

        # Search Certificates
        filtered_cert = [
            cert for cert in self.documents["certificates"]
            if query in cert["name"].lower() or
            query in cert["issuer"].lower() or
            query in cert["date"].lower() or
            query in cert["description"].lower()
        ]
        for cert in filtered_cert:
            results["Certificates"].append(f"{cert['name']} ({cert['issuer']}) - {cert['date']}")

        # Show search results popup
        self.show_search_results_popup(query, results)

    def export_data(self):
        try:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "Export Data", "", "CSV Files (*.csv)", options=options)
            if file_name:
                with open(file_name, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Type", "Category", "Date", "Amount", "Description"])
                    for transaction in self.transactions:
                        writer.writerow([transaction["type"], transaction["category"], transaction["date"], transaction["amount"], transaction["description"]])
                QMessageBox.information(self, "Success", "Data exported successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def generate_detailed_report(self):
        try:
            report_text = self.generate_report_text()
            self.stats_text.setText(report_text)
            QMessageBox.information(self, "Success", "Detailed report generated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def generate_report_text(self):
        try:
            total_income = sum(trans["amount"] for trans in self.transactions if trans["type"] == "Income")
            total_expense = sum(trans["amount"] for trans in self.transactions if trans["type"] == "Expense")
            balance = total_income - total_expense

            income_by_category = {}
            expense_by_category = {}

            for trans in self.transactions:
                if trans["type"] == "Income":
                    if trans["category"] not in income_by_category:
                        income_by_category[trans["category"]] = 0
                    income_by_category[trans["category"]] += trans["amount"]
                elif trans["type"] == "Expense":
                    if trans["category"] not in expense_by_category:
                        expense_by_category[trans["category"]] = 0
                    expense_by_category[trans["category"]] += trans["amount"]

            report_text = f"""
            Total Income: ₹{total_income:.2f}
            Total Expense: ₹{total_expense:.2f}
            Balance: ₹{balance:.2f}

            Income by Category:
            """
            for category, amount in income_by_category.items():
                report_text += f"{category}: ₹{amount:.2f}\n"

            report_text += "\nExpense by Category:\n"
            for category, amount in expense_by_category.items():
                report_text += f"{category}: ₹{amount:.2f}\n"

            return report_text
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
            return ""

    def show_notifications(self, event):
        try:
            notifications = self.get_notifications()
            if not notifications:
                QMessageBox.information(self, "Notifications", "No new notifications.")
                return

            notification_text = "\n".join(notifications)
            QMessageBox.information(self, "Notifications", notification_text)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def get_notifications(self):
        try:
            today = QDate.currentDate()
            upcoming_bills = [trans for trans in self.transactions if trans["type"] == "Expense" and QDate.fromString(trans["date"], Qt.ISODate) <= today.addDays(7)]
            notifications = [f"Upcoming bill: {trans['description']} on {trans['date']}" for trans in upcoming_bills]
            return notifications
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
            return []

    def show_charts(self):
        try:
            # Create a dialog to display the charts
            dialog = QDialog(self)
            dialog.setWindowTitle("Financial Charts")
            dialog.setModal(True)
            dialog.setMinimumWidth(800)
            dialog.setMinimumHeight(600)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(8)

            # Create tabs for different charts
            chart_tabs = QTabWidget()
            layout.addWidget(chart_tabs)

            # Income vs Expense Pie Chart
            pie_chart_tab = QWidget()
            pie_chart_layout = QVBoxLayout(pie_chart_tab)
            pie_chart = self.create_pie_chart()
            pie_chart_layout.addWidget(pie_chart)
            chart_tabs.addTab(pie_chart_tab, "Income vs Expense")

            # Income by Category Bar Chart
            income_bar_chart_tab = QWidget()
            income_bar_chart_layout = QVBoxLayout(income_bar_chart_tab)
            income_bar_chart = self.create_income_bar_chart()
            income_bar_chart_layout.addWidget(income_bar_chart)
            chart_tabs.addTab(income_bar_chart_tab, "Income by Category")

            # Expense by Category Bar Chart
            expense_bar_chart_tab = QWidget()
            expense_bar_chart_layout = QVBoxLayout(expense_bar_chart_tab)
            expense_bar_chart = self.create_expense_bar_chart()
            expense_bar_chart_layout.addWidget(expense_bar_chart)
            chart_tabs.addTab(expense_bar_chart_tab, "Expense by Category")

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def create_pie_chart(self):
        try:
            total_income = sum(trans["amount"] for trans in self.transactions if trans["type"] == "Income")
            total_expense = sum(trans["amount"] for trans in self.transactions if trans["type"] == "Expense")

            labels = ['Income', 'Expense']
            sizes = [total_income, total_expense]
            colors = ['#2ecc71', '#e74c3c']
            fig, ax = plt.subplots()
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

            canvas = FigureCanvas(fig)
            return canvas

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def create_income_bar_chart(self):
        try:
            income_by_category = {}
            for trans in self.transactions:
                if trans["type"] == "Income":
                    if trans["category"] not in income_by_category:
                        income_by_category[trans["category"]] = 0
                    income_by_category[trans["category"]] += trans["amount"]

            categories = list(income_by_category.keys())
            amounts = list(income_by_category.values())

            fig, ax = plt.subplots()
            ax.bar(categories, amounts, color='#2ecc71')
            ax.set_xlabel('Categories')
            ax.set_ylabel('Amount')
            ax.set_title('Income by Category')

            canvas = FigureCanvas(fig)
            return canvas

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def create_expense_bar_chart(self):
        try:
            expense_by_category = {}
            for trans in self.transactions:
                if trans["type"] == "Expense":
                    if trans["category"] not in expense_by_category:
                        expense_by_category[trans["category"]] = 0
                    expense_by_category[trans["category"]] += trans["amount"]

            categories = list(expense_by_category.keys())
            amounts = list(expense_by_category.values())

            fig, ax = plt.subplots()
            ax.bar(categories, amounts, color='#e74c3c')
            ax.set_xlabel('Categories')
            ax.set_ylabel('Amount')
            ax.set_title('Expense by Category')

            canvas = FigureCanvas(fig)
            return canvas

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set application font
    font = QFont()
    font.setFamily("Segoe UI")  # Windows
    font.setPointSize(10)
    app.setFont(font)

    window = DocumentManagerApp()
    window.show()
    sys.exit(app.exec_())







