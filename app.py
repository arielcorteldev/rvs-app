import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import subprocess

# IMPORT PYSIDE6 MODULES
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *

# IMPORT UI 
from MainWindow import Ui_MainWindow
from Login_Dialog import Ui_Login_Dialog
from db_config import POSTGRES_CONFIG

from stylesheets import message_box_style

from search import SearchBirthWindow, SearchDeathWindow, SearchMarriageWindow
from verify import VerifyBirthWindow, VerifyDeathWindow, VerifyMarriageWindow
from manage_users import ManageUserForm

# from indexing import *
from stats import StatisticsWindow
from tagging_main import TaggingMainWindow
from everify_form import eVerifyForm
from audit_logger import AuditLogger
from audit_log_viewer import AuditLogViewer
from releasing_docs import ReleaseDocumentWindow
from releasing_log_viewer import ReleasingLogViewer
from book_viewer import BookViewerWindow

from flask_server.app import start_server
import threading


flask_thread = threading.Thread(target=start_server, daemon=True)
flask_thread.start()

basedir = os.path.dirname(__file__)


# Login Dialog
class Login(QDialog, Ui_Login_Dialog):
    # Add a custom signal to emit the user info (username and full name) on success
    login_success = Signal(str, str)  # username, full_name

    def __init__(self):
        super().__init__()

        # set up UI for window
        self.setupUi(self)

        # set window title
        self.setWindowTitle('Log in')

        # hide password input
        self.password_input.setEchoMode(QLineEdit.Password)

        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
                color: #212121;
            }
            QLineEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
            QPushButton {
                background-color: #ce305e;
                color: #FFFFFF;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0446a;
                color: #FFFFFF;
            }
        """)

        # connect login button to login method
        self.login_button.clicked.connect(self.login)

    def create_connection(self):
        try:
            conn = psycopg2.connect(**POSTGRES_CONFIG)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except psycopg2.Error as e:
            print(f"Error connecting to database: {str(e)}")
            return None

    def closeConnection(self, conn):
        if conn:
            try:
                conn.close()
            except:
                pass  # Ignore close errors

    def login(self):
        try:
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()

            if not username or not password:
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Information)
                box.setWindowTitle("Information")
                box.setText("Please enter both username and password.")
                box.setStandardButtons(QMessageBox.Ok)

                box.setStyleSheet(message_box_style)

                box.exec()
                return

            conn = self.create_connection()
            if not conn:
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Critical)
                box.setWindowTitle("Error")
                box.setText("Could not connect to database.")
                box.setStandardButtons(QMessageBox.Ok)

                box.setStyleSheet(message_box_style)

                box.exec()
                return
                
            cursor = conn.cursor()
            
            # Check credentials and fetch user info
            cursor.execute(
                "SELECT username, firstname, lastname FROM users_list WHERE username = %s AND password = %s",
                (username, password)
            )
            
            user = cursor.fetchone()
            
            if user:
                username, firstname, lastname = user
                full_name = f"{firstname} {lastname}".strip()
                
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Information)
                box.setWindowTitle("Success")
                box.setText("Login successful!")
                box.setStandardButtons(QMessageBox.Ok)

                box.setStyleSheet(message_box_style)
                box.exec()
                self.login_success.emit(username, full_name)
                AuditLogger.log_action(
                    conn,
                    username,
                    "LOGIN",
                    {"client": "DesktopApp"}
                )
                mainwindow.showMaximized()
                self.hide()
            else:
                AuditLogger.log_action(
                    conn,
                    "SYSTEM",
                    "LOGIN_FAILED",
                    {"username": username, "reason": "invalid_credentials"}
                )
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Invalid username or password.")
                box.setStandardButtons(QMessageBox.Ok)

                box.setStyleSheet(message_box_style)
                box.exec()
        except psycopg2.Error as e:
            AuditLogger.log_action(
                conn,
                "SYSTEM",
                "LOGIN_ERROR",
                {"error": str(e)}
            )
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Warning")
            box.setText(f"Login failed due to database error: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)

            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            if cursor:
                cursor.close()
            self.closeConnection(conn)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.windows = {}
        self.connection = None

        # Create Login window instance
        self.login_window = Login()

        # Connect login signal
        self.login_window.login_success.connect(self.set_current_user)

        
        # Initialize window properties
        self.setWindowTitle("OCCR Records Verification System")
        self.setMinimumSize(1000, 600)

        # Set window icon
        self.setWindowIcon(QIcon("icons/RVS-icon.png"))

        # Initialize UI state
        self.is_sidebar_expanded = False
        self.sidebar_width = 200
        self.sidebar_minimum = 50
        
        
        # Create and set the central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create main layout
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create and setup sidebar
        self.setup_sidebar()
        
        # Create and setup main content
        self.setup_main_content()
        
        # Set the default page
        self.content_stack.setCurrentIndex(0)
        
    def setup_sidebar(self):
        # Create sidebar frame
        self.sidebar = QFrame()
        self.sidebar.setMaximumWidth(self.sidebar_minimum)  # Start with minimum width
        self.sidebar.setMinimumWidth(self.sidebar_minimum)  # Start with minimum width
        self.sidebar.setStyleSheet("""
            QFrame {
                background-color: #F2F2F2;
                border: none;
            }
            QPushButton {
                color: #212121;
                border: none;
                text-align: left;
                padding: 10px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #ce305e;
                color: #FFFFFF;
            }
            QPushButton:clicked {
                background-color: #ce305e;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #ce305e;
                color: #FFFFFF;
            }
            #logout_button {
                border-top: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton#sub_menu_btn {
                padding-left: 30px;
                font-size: 13px;
                background-color: rgba(0, 0, 0, 0.1);
            }
            QPushButton#sub_menu_btn:hover {
                background-color: #ce305e;
                color: #FFFFFF;
            }
        """)
        
        # Create sidebar layout
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)

        # City Seal and Office Logo
        
        # Create toggle button
        self.toggle_button = QPushButton("≡")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                padding: 10px 15px;
                background-color: #F2F2F2;
                color: #212121;
            }
            QPushButton:hover {
                background-color: #ce305e;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle_sidebar)
        self.sidebar_layout.addWidget(self.toggle_button)
        

        # Create Verify Menu Container
        self.verify_container = QFrame()
        self.verify_layout = QVBoxLayout(self.verify_container)
        self.verify_layout.setContentsMargins(0, 0, 0, 0)
        self.verify_layout.setSpacing(0)
        
        # Add Verify main button
        self.verify_button = QPushButton()
        verify_icon = QIcon("icons/verify.png")
        self.verify_button.setIcon(verify_icon)
        self.verify_button.setIconSize(QSize(24, 24))
        self.verify_button.setText("")  # Start with no text
        
        # Add dropdown indicator
        self.verify_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
            }
        """)
        self.verify_layout.addWidget(self.verify_button)
        
        # Create sub-menu container
        self.verify_sub_menu = QFrame()
        self.verify_sub_menu.setHidden(True)  # Hidden by default
        self.sub_menu_layout = QVBoxLayout(self.verify_sub_menu)
        self.sub_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.sub_menu_layout.setSpacing(0)
        
        # Add sub-menu buttons
        self.verify_livebirth_btn = QPushButton("Live Birth")
        self.verify_death_btn = QPushButton("Death")
        self.verify_marriage_btn = QPushButton("Marriage")
        
        # Set object names for sub-menu styling
        for btn in [self.verify_livebirth_btn, self.verify_death_btn, self.verify_marriage_btn]:
            btn.setObjectName("sub_menu_btn")
        
        # Add buttons to sub-menu layout
        self.sub_menu_layout.addWidget(self.verify_livebirth_btn)
        self.sub_menu_layout.addWidget(self.verify_death_btn)
        self.sub_menu_layout.addWidget(self.verify_marriage_btn)
        
        # Add sub-menu to verify container
        self.verify_layout.addWidget(self.verify_sub_menu)
        
        # Add verify container to sidebar
        self.sidebar_layout.addWidget(self.verify_container)
        
        # Connect verify button to toggle sub-menu
        self.verify_button.clicked.connect(self.toggle_verify_menu)
        
        # Connect sub-menu buttons to their respective pages
        self.verify_livebirth_btn.clicked.connect(self.open_search_birth_dialog)
        self.verify_death_btn.clicked.connect(self.open_search_death_dialog)
        self.verify_marriage_btn.clicked.connect(self.open_search_marriage_dialog)

        # Create Filename Search Menu Container
        self.filename_search_container = QFrame()
        self.filename_search_layout = QVBoxLayout(self.filename_search_container)
        self.filename_search_layout.setContentsMargins(0, 0, 0, 0)
        self.filename_search_layout.setSpacing(0)
        
        # Add Filename Search main button
        self.filename_search_button = QPushButton()
        verify_icon = QIcon("icons/magnifier.png")
        self.filename_search_button.setIcon(verify_icon)
        self.filename_search_button.setIconSize(QSize(24, 24))
        self.filename_search_button.setText("")  # Start with no text
        
        # Add dropdown indicator
        self.filename_search_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
            }
        """)
        self.filename_search_layout.addWidget(self.filename_search_button)
        
        # Create sub-menu container
        self.filename_search_sub_menu = QFrame()
        self.filename_search_sub_menu.setHidden(True)  # Hidden by default
        self.sub_menu_layout = QVBoxLayout(self.filename_search_sub_menu)
        self.sub_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.sub_menu_layout.setSpacing(0)
        
        # Add sub-menu buttons
        self.fname_search_birth_btn = QPushButton("Live Birth")
        self.fname_search_death_btn = QPushButton("Death")
        self.fname_search_marriage_btn = QPushButton("Marriage")
        
        # Set object names for sub-menu styling
        for btn in [self.fname_search_birth_btn, self.fname_search_death_btn, self.fname_search_marriage_btn]:
            btn.setObjectName("sub_menu_btn")
        
        # Add buttons to sub-menu layout
        self.sub_menu_layout.addWidget(self.fname_search_birth_btn)
        self.sub_menu_layout.addWidget(self.fname_search_death_btn)
        self.sub_menu_layout.addWidget(self.fname_search_marriage_btn)
        
        # Add sub-menu to Filename Search container
        self.filename_search_layout.addWidget(self.filename_search_sub_menu)
        
        # Add Filename Search container to sidebar
        self.sidebar_layout.addWidget(self.filename_search_container)
        
        # Connect verify button to toggle sub-menu
        self.filename_search_button.clicked.connect(self.toggle_filename_search_menu)
        
        # Connect sub-menu buttons to their respective pages
        self.fname_search_birth_btn.clicked.connect(self.open_fsearch_birth_dialog)
        self.fname_search_death_btn.clicked.connect(self.open_fsearch_death_dialog)
        self.fname_search_marriage_btn.clicked.connect(self.open_fsearch_marriage_dialog)

        # Add eVerify button
        self.everify_button = QPushButton()
        everify_icon = QIcon("icons/check.png")
        self.everify_button.setIcon(everify_icon)
        self.everify_button.setIconSize(QSize(24, 24))
        self.everify_button.setText("")  # Start with no text
        self.everify_button.clicked.connect(self.open_everify)
        self.sidebar_layout.addWidget(self.everify_button)

        # Create Release Menu Container
        self.release_container = QFrame()
        self.release_layout = QVBoxLayout(self.release_container)
        self.release_layout.setContentsMargins(0, 0, 0, 0)
        self.release_layout.setSpacing(0)
        
        # Add Release main button
        self.release_button = QPushButton()
        release_icon = QIcon("icons/handover.png")
        self.release_button.setIcon(release_icon)
        self.release_button.setIconSize(QSize(24, 24))
        self.release_button.setText("")  # Start with no text
        
        # Add dropdown indicator
        self.release_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
            }
        """)
        self.release_layout.addWidget(self.release_button)
        
        # Create sub-menu container
        self.release_sub_menu = QFrame()
        self.release_sub_menu.setHidden(True)  # Hidden by default
        self.sub_menu_layout = QVBoxLayout(self.release_sub_menu)
        self.sub_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.sub_menu_layout.setSpacing(0)
        
        # Add sub-menu buttons
        self.release_form_btn = QPushButton("Release Document")
        self.release_log_btn = QPushButton("Releasing Logbook")
        
        # Set object names for sub-menu styling
        for btn in [self.release_form_btn, self.release_log_btn]:
            btn.setObjectName("sub_menu_btn")
        
        # Add buttons to sub-menu layout
        self.sub_menu_layout.addWidget(self.release_form_btn)
        self.sub_menu_layout.addWidget(self.release_log_btn)
        
        # Add sub-menu to release container
        self.release_layout.addWidget(self.release_sub_menu)
        
        # Add release container to sidebar
        self.sidebar_layout.addWidget(self.release_container)
        
        # Connect release button to toggle sub-menu
        self.release_button.clicked.connect(self.toggle_release_menu)
        
        # Connect sub-menu buttons to their respective pages
        self.release_form_btn.clicked.connect(self.open_release_form)
        self.release_log_btn.clicked.connect(self.open_release_log)

        # Create Other Features Menu Container
        self.other_features_container = QFrame()
        self.other_features_layout = QVBoxLayout(self.other_features_container)
        self.other_features_layout.setContentsMargins(0, 0, 0, 0)
        self.other_features_layout.setSpacing(0)
        
        # Add Other Features main button
        self.other_features_button = QPushButton()
        other_features_icon = QIcon("icons/application.png")
        self.other_features_button.setIcon(other_features_icon)
        self.other_features_button.setIconSize(QSize(24, 24))
        self.other_features_button.setText("")  # Start with no text
        
        # Add dropdown indicator
        self.other_features_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
            }
        """)
        self.other_features_layout.addWidget(self.other_features_button)
        
        # Create sub-menu container
        self.other_features_sub_menu = QFrame()
        self.other_features_sub_menu.setHidden(True)  # Hidden by default
        self.sub_menu_layout = QVBoxLayout(self.other_features_sub_menu)
        self.sub_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.sub_menu_layout.setSpacing(0)
        
        # Add sub-menu buttons
        self.statistics_btn = QPushButton("Statistics")
        self.tagging_btn = QPushButton("Tagging")
        self.book_viewer_btn = QPushButton("Book Viewer")
        
        # Set object names for sub-menu styling
        for btn in [self.statistics_btn, self.tagging_btn, self.book_viewer_btn]:
            btn.setObjectName("sub_menu_btn")
        
        # Add buttons to sub-menu layout
        self.sub_menu_layout.addWidget(self.statistics_btn)
        self.sub_menu_layout.addWidget(self.tagging_btn)
        self.sub_menu_layout.addWidget(self.book_viewer_btn)

        # Add sub-menu to other features container
        self.other_features_layout.addWidget(self.other_features_sub_menu)
        
        # Add other features container to sidebar
        self.sidebar_layout.addWidget(self.other_features_container)
        
        # Connect other features button to toggle sub-menu
        self.other_features_button.clicked.connect(self.toggle_other_features_menu)
        
        # Connect sub-menu buttons to their respective pages
        self.statistics_btn.clicked.connect(self.open_statistics_tools)
        self.tagging_btn.clicked.connect(self.open_tagging_tools)
        self.book_viewer_btn.clicked.connect(self.open_book_viewer)
        # Create User Management Menu Container
        self.user_management_container = QFrame()
        self.user_management_layout = QVBoxLayout(self.user_management_container)
        self.user_management_layout.setContentsMargins(0, 0, 0, 0)
        self.user_management_layout.setSpacing(0)

        # Add User Management main button
        self.user_management_button = QPushButton()
        user_management_icon = QIcon("icons/profile.png")
        self.user_management_button.setIcon(user_management_icon)
        self.user_management_button.setIconSize(QSize(24, 24))
        self.user_management_button.setText("")  # Start with no text
        
        # Add dropdown indicator
        self.user_management_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
            }
        """)
        self.user_management_layout.addWidget(self.user_management_button)
        
        # Create sub-menu container
        self.user_management_sub_menu = QFrame()
        self.user_management_sub_menu.setHidden(True)  # Hidden by default
        self.sub_menu_layout = QVBoxLayout(self.user_management_sub_menu)
        self.sub_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.sub_menu_layout.setSpacing(0)
        
        # Add sub-menu buttons
        self.manage_user_btn = QPushButton("Manage User")
        self.audit_log_btn = QPushButton("Audit Logbook")
        
        # Set object names for sub-menu styling
        for btn in [self.manage_user_btn, self.audit_log_btn]:
            btn.setObjectName("sub_menu_btn")
        
        # Add buttons to sub-menu layout
        self.sub_menu_layout.addWidget(self.manage_user_btn)
        self.sub_menu_layout.addWidget(self.audit_log_btn)
        
        # Add sub-menu to user management container
        self.user_management_layout.addWidget(self.user_management_sub_menu)
        
        # Add user management container to sidebar
        self.sidebar_layout.addWidget(self.user_management_container)
        
        # Connect user management button to toggle sub-menu
        self.user_management_button.clicked.connect(self.toggle_user_management_menu)
        
        # Connect sub-menu buttons to their respective pages
        self.manage_user_btn.clicked.connect(self.open_manage_user)
        self.audit_log_btn.clicked.connect(self.open_audit_log_viewer)
        
        # Add stretch to push buttons to the top
        self.sidebar_layout.addStretch()
        
        # Add logout button at the bottom
        self.logout_button = QPushButton()
        logout_icon = QIcon("icons/logout.png")
        self.logout_button.setIcon(logout_icon)
        self.logout_button.setIconSize(QSize(24, 24))
        self.logout_button.setText("")  # Start with no text
        self.logout_button.setObjectName("logout_button")
        self.logout_button.clicked.connect(self.logout)
        self.sidebar_layout.addWidget(self.logout_button)
        
        # Add sidebar to main layout
        self.main_layout.addWidget(self.sidebar)
        
    def setup_main_content(self):
        # Create main content area
        self.content_area = QFrame()
        self.content_area.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
            }
        """)
        
        # Create content layout
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Create stacked widget for different pages
        self.content_stack = QStackedWidget()
        
        # Create home page
        self.home_page = QWidget()
        self.home_layout = QVBoxLayout(self.home_page)
        
        # Add logo to home page
        logo_label = QLabel()
        logo_pixmap = QPixmap("icons/RVS-logo.png")
        # Scale the pixmap while maintaining aspect ratio
        scaled_pixmap = logo_pixmap.scaled(1000, 1000, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        self.home_layout.addWidget(logo_label)
        
        # Add spacer to center the logo vertically
        self.home_layout.addStretch(1)
        self.home_layout.insertStretch(0, 1)
        
        # Add pages to stack
        self.content_stack.addWidget(self.home_page)
        
        
        # Add stack to content layout
        self.content_layout.addWidget(self.content_stack)

        # ──────── FOOTER ──────── #
        footer = QFrame()
        footer.setFixedHeight(80)
        footer.setStyleSheet("background-color: #fef2f4;")

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 10, 20, 10)
        footer_layout.setSpacing(20)
        footer_layout.setAlignment(Qt.AlignCenter)  # Center horizontally

        # Left: Text and City Seal
        left_container = QHBoxLayout()
        left_label = QLabel("City Government of Maasin")
        left_font = QFont()
        left_font.setBold(True)
        left_font.setPointSize(12)
        left_label.setFont(left_font)
        left_label.setStyleSheet("color: #333;")

        city_seal_label = QLabel()
        city_seal_pixmap = QPixmap("icons/city_seal.png").scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        city_seal_label.setPixmap(city_seal_pixmap)

        left_container.addWidget(left_label)
        left_container.addWidget(city_seal_label)

        left_widget = QWidget()
        left_widget.setLayout(left_container)

        # Right: Office Logo and Text
        right_container = QHBoxLayout()
        office_logo_label = QLabel()
        office_logo_pixmap = QPixmap("icons/office_logo.png").scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        office_logo_label.setPixmap(office_logo_pixmap)

        right_label = QLabel("Office of the City Civil Registrar")
        right_font = QFont()
        right_font.setBold(True)
        right_font.setPointSize(12)
        right_label.setFont(right_font)
        right_label.setStyleSheet("color: #333;")

        right_container.addWidget(office_logo_label)
        right_container.addWidget(right_label)

        right_widget = QWidget()
        right_widget.setLayout(right_container)

        # Add both containers to footer layout
        footer_layout.addWidget(left_widget)
        footer_layout.addStretch(1)
        footer_layout.addWidget(right_widget)

        # Add footer to main content layout
        self.content_layout.addWidget(footer)
        
        # Add content area to main layout
        self.main_layout.addWidget(self.content_area)
        
    def toggle_sidebar(self):
        if self.is_sidebar_expanded:
            self.contract_sidebar()
        else:
            self.expand_sidebar()
            
    def contract_sidebar(self):
        # Create animation group for synchronized animations
        self.animation_group = QParallelAnimationGroup()
        
        # Animate maximum width
        self.animation_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.animation_max.setDuration(300)
        self.animation_max.setStartValue(self.sidebar_width)
        self.animation_max.setEndValue(self.sidebar_minimum)
        self.animation_max.setEasingCurve(QEasingCurve.InOutQuart)
        
        # Animate minimum width
        self.animation_min = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.animation_min.setDuration(300)
        self.animation_min.setStartValue(self.sidebar_width)
        self.animation_min.setEndValue(self.sidebar_minimum)
        self.animation_min.setEasingCurve(QEasingCurve.InOutQuart)
        
        # Add both animations to the group
        self.animation_group.addAnimation(self.animation_max)
        self.animation_group.addAnimation(self.animation_min)
        
        # Start the animation group
        self.animation_group.start()
        
        self.is_sidebar_expanded = False
        self.verify_button.setText("")
        self.verify_button.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2;
            }
            QPushButton:hover {
                background-color: #ce305e;
            }
        """)
        self.filename_search_button.setText("")
        self.filename_search_button.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2;
            }
            QPushButton:hover {
                background-color: #ce305e;
            }
        """)
        self.logout_button.setText("")
        self.logout_button.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2;
            }
            QPushButton:hover {
                background-color: #ce305e;
            }
        """)
        self.everify_button.setText("")
        self.release_button.setText("")
        self.release_button.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2;
            }
            QPushButton:hover {
                background-color: #ce305e;
            }
        """)
        self.other_features_button.setText("")
        self.other_features_button.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2;
            }
            QPushButton:hover {
                background-color: #ce305e;
            }
        """)
        self.user_management_button.setText("")
        self.user_management_button.setStyleSheet("""
            QPushButton {
                background-color: #F2F2F2;
            }
            QPushButton:hover {
                background-color: #ce305e;
            }
        """)

        # Hide sub-menu when sidebar is contracted
        self.verify_sub_menu.hide()
        self.filename_search_sub_menu.hide()
        self.other_features_sub_menu.hide()
        self.release_sub_menu.hide()
        self.user_management_sub_menu.hide()
        
    def expand_sidebar(self):
        # Create animation group for synchronized animations
        self.animation_group = QParallelAnimationGroup()
        
        # Animate maximum width
        self.animation_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.animation_max.setDuration(300)
        self.animation_max.setStartValue(self.sidebar_minimum)
        self.animation_max.setEndValue(self.sidebar_width)
        self.animation_max.setEasingCurve(QEasingCurve.InOutQuart)
        
        # Animate minimum width
        self.animation_min = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.animation_min.setDuration(300)
        self.animation_min.setStartValue(self.sidebar_minimum)
        self.animation_min.setEndValue(self.sidebar_width)
        self.animation_min.setEasingCurve(QEasingCurve.InOutQuart)
        
        # Add both animations to the group
        self.animation_group.addAnimation(self.animation_max)
        self.animation_group.addAnimation(self.animation_min)
        
        # Start the animation group
        self.animation_group.start()
        
        self.is_sidebar_expanded = True
        self.verify_button.setText("  Verify")
        self.filename_search_button.setText("  Search")
        self.everify_button.setText("  eVerify")
        self.release_button.setText("  Release")
        self.other_features_button.setText("  Other Features")
        self.user_management_button.setText("  User Management")
        self.logout_button.setText("  Logout")

    def create_connection(self):
        try:
            if self.connection is None:
                self.connection = psycopg2.connect(**POSTGRES_CONFIG)
                self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            return self.connection
        except psycopg2.Error as e:
            print(f"Error connecting to database: {str(e)}")
            return None

    def closeConnection(self):
        if self.connection:
            try:
                self.connection.close()
            except:
                pass  # Ignore close errors
            self.connection = None

    # log current user
    def set_current_user(self, username, full_name):
        conn = self.create_connection()
        try:
            print(f"Logging action: user={username}, full_name={full_name}")
            self.current_user = username
            self.current_user_full_name = full_name  # Store full name
            AuditLogger.log_action(
                conn,
                username,
                "SESSION_START",
                {"username": username}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def logout(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()

        # message = QMessageBox.question(self, "Confirmation", "Are you sure you want to log out?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        # QMessageBox.question returns the selected button, so instead:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Confirmation")
        box.setText("Are you sure you want to log out?")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        box.setStyleSheet(message_box_style)

        if box.exec() == QMessageBox.Yes:
            conn = self.create_connection()
            try:
                # Log window closures first
                for window_name, window in self.windows.items():
                    if window.isVisible():
                        AuditLogger.log_action(
                            conn,
                            self.current_user,
                            "WINDOW_CLOSED",
                            {"window": window_name, "reason": "logout"}
                        )
                    window.close()

                if self.current_user:
                    AuditLogger.log_action(
                        conn,
                        self.current_user,
                        "LOGOUT",
                        {"reason": "user_initiated"}
                    )
                conn.commit()
            finally:
                self.closeConnection()

            # Clear all window references
            self.windows.clear()


            self.login_window.show()
            self.hide()

    def closeEvent(self, event):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Confirmation")
        box.setText("Are you sure you want to log out?")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        box.setStyleSheet(message_box_style)
        reply = box.exec()
        
        if reply == QMessageBox.Yes:
            conn = self.create_connection()
            try:
                # Log window closures
                for window_name, window in self.windows.items():
                    if window.isVisible():
                        AuditLogger.log_action(
                            conn,
                            self.current_user,
                            "WINDOW_CLOSED", 
                            {"window": window_name, "reason": "app_exit"}
                        )
                    window.close()
                
                # Log application exit
                if self.current_user:
                    AuditLogger.log_action(
                        conn,
                        self.current_user,
                        "APP_EXIT",
                        {"reason": "user_initiated"}
                    )
                conn.commit()
            finally:
                self.closeConnection()
            
            # Clean up
            self.windows.clear()
            # if self.recordstatus:
            #     self.recordstatus.close()
            event.accept()
        else:
            event.ignore()

    def toggle_verify_menu(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
        # Toggle sub-menu visibility with animation
        self.verify_sub_menu.setVisible(not self.verify_sub_menu.isVisible())
        
        # Update button style to indicate state
        if self.verify_sub_menu.isVisible():
            self.verify_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    background-color: rgba(0, 0, 0, 0.1);
                    color: #212121;
                }
                QPushButton:hover {
                    background-color: #ce305e;
                    color: #FFFFFF;
                }
            """)
        else:
            self.verify_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    color: #212121;
                }
                QPushButton:hover {
                    background-color: #ce305e;
                    color: #FFFFFF;
                }
            """)
    
    def toggle_filename_search_menu(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
        # Toggle sub-menu visibility with animation
        self.filename_search_sub_menu.setVisible(not self.filename_search_sub_menu.isVisible())
        
        # Update button style to indicate state
        if self.filename_search_sub_menu.isVisible():
            self.filename_search_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    background-color: rgba(0, 0, 0, 0.1);
                    color: #212121;
                }
                QPushButton:hover {
                    background-color: #ce305e;
                    color: #FFFFFF;
                }
            """)
        else:
            self.filename_search_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    color: #212121;
                }
                QPushButton:hover {
                    background-color: #ce305e;
                    color: #FFFFFF;
                }
            """)

    def toggle_release_menu(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
        # Toggle sub-menu visibility with animation
        self.release_sub_menu.setVisible(not self.release_sub_menu.isVisible())

        # Update button style to indicate state
        if self.release_sub_menu.isVisible():
            self.release_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    background-color: rgba(0, 0, 0, 0.1);
                    color: #212121;
                }
                QPushButton:hover {
                    background-color: #ce305e;
                    color: #FFFFFF;
                }
            """)
        else:
            self.release_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    color: #212121;
                }
                QPushButton:hover {
                    background-color: #ce305e;
                    color: #FFFFFF;
                }
            """)

    def toggle_other_features_menu(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
        # Toggle sub-menu visibility with animation
        self.other_features_sub_menu.setVisible(not self.other_features_sub_menu.isVisible())

        # Update button style to indicate state
        if self.other_features_sub_menu.isVisible():
            self.other_features_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    background-color: rgba(0, 0, 0, 0.1);
                    color: #212121;
                }
                QPushButton:hover {
                    background-color: #ce305e;
                    color: #FFFFFF;
                }
            """)
        else:
            self.other_features_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    color: #212121;
                }
                QPushButton:hover {
                    background-color: #ce305e;
                    color: #FFFFFF;
                }
            """)
    
    def toggle_user_management_menu(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
        # Toggle sub-menu visibility with animation
        self.user_management_sub_menu.setVisible(not self.user_management_sub_menu.isVisible())

        # Update button style to indicate state
        if self.user_management_sub_menu.isVisible():
            self.user_management_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    background-color: rgba(0, 0, 0, 0.1);
                    color: #212121;
                }
                QPushButton:hover {
                    background-color: #ce305e;
                    color: #FFFFFF;
                }
            """)
        else:
            self.user_management_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    color: #212121;
                }
                QPushButton:hover {
                    background-color: #ce305e;
                    color: #FFFFFF;
                }
            """)

    # open search live birth window
    def open_fsearch_birth_dialog(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
            
        conn = self.create_connection()
        try:
            birth = self.windows.get('birth')
            if birth is None or not birth.isVisible():
                birth = SearchBirthWindow(self.current_user, parent=self, main_window=self)
                # Apply customizations when first creating
                birth.setWindowTitle('Search Live Birth')
                birth.setParent(self)
                birth.setWindowFlag(Qt.Window)
                self.windows['birth'] = birth

            birth.show()
            birth.raise_()
            birth.activateWindow()
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "SearchBirthWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    # open search death window
    def open_fsearch_death_dialog(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
            
        conn = self.create_connection()
        try:
            death = self.windows.get('death')
            if death is None or not death.isVisible():
                death = SearchDeathWindow(self.current_user, parent=self, main_window=self)
                death.setWindowTitle('Search Death')
                # death.setStyleSheet("""
                #     QMainWindow {
                #         background-color: #FFFFFF;
                #     }
                #     QListWidget {
                #         background-color: #cedbef;
                #     }
                # """)
                death.setParent(self)
                death.setWindowFlag(Qt.Window)
                self.windows['death'] = death
                
            death.show()
            death.raise_()
            death.activateWindow()
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "SearchDeathWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    # open search marriage window
    def open_fsearch_marriage_dialog(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
            
        conn = self.create_connection()
        try:
            marriage = self.windows.get('marriage')
            if marriage is None or not marriage.isVisible():
                marriage = SearchMarriageWindow(self.current_user, parent=self, main_window=self)
                marriage.setWindowTitle('Search Marriage')
                marriage.setParent(self)
                marriage.setWindowFlag(Qt.Window)
                self.windows['marriage'] = marriage
                
            marriage.show()
            marriage.raise_()
            marriage.activateWindow()
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "SearchMarriageWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def open_search_birth_dialog(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
            
        conn = self.create_connection()
        try:
            birth_book = self.windows.get('birth_book')
            if birth_book is None or not birth_book.isVisible():
                birth_book = VerifyBirthWindow(self.current_user, parent=self, main_window=self)
                birth_book.setWindowTitle('Verify Live Birth')
                birth_book.setParent(self)
                birth_book.setWindowFlag(Qt.Window)
                self.windows['birth_book'] = birth_book
                
            birth_book.show()
            birth_book.raise_()
            birth_book.activateWindow()
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "SearchBirthBookWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def open_search_death_dialog(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
            
        conn = self.create_connection()
        try:
            death_book = self.windows.get('death_book')
            if death_book is None or not death_book.isVisible():
                death_book = VerifyDeathWindow(self.current_user, parent=self, main_window=self)
                death_book.setWindowTitle('Verify Death')
                death_book.setParent(self)
                death_book.setWindowFlag(Qt.Window)
                self.windows['birth_book'] = death_book
                
            death_book.show()
            death_book.raise_()
            death_book.activateWindow()
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "SearchDeathBookWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def open_search_marriage_dialog(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()
            
        conn = self.create_connection()
        try:
            marriage_book = self.windows.get('marriage_book')
            if marriage_book is None or not marriage_book.isVisible():
                marriage_book = VerifyMarriageWindow(self.current_user, parent=self, main_window=self)
                marriage_book.setWindowTitle('Verify Marriage')
                marriage_book.setParent(self)
                marriage_book.setWindowFlag(Qt.Window)
                self.windows['birth_book'] = marriage_book
                
            marriage_book.show()
            marriage_book.raise_()
            marriage_book.activateWindow()
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "SearchMarriageBookWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()
    
    # open eVERIFY window
    def open_everify(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()

        conn = self.create_connection()
        try:
            everify = self.windows.get('everify')
            if everify is None or not everify.isVisible():
                everify = eVerifyForm(self.current_user, parent=self)
                everify.setParent(self)
                everify.setWindowFlag(Qt.Window)
                self.windows['everify'] = everify
                
            everify.show()
            everify.raise_()
            everify.activateWindow()
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "eVerifyForm"}
            )
            conn.commit()
        finally:
            self.closeConnection()
    
    def get_everify_form(self):
        everify_form = self.windows.get('everify_form')
        if everify_form is None or not everify_form.isVisible():
            everify_form = eVerifyForm(self.current_user, parent=self)
            everify_form.setParent(self)
            everify_form.setWindowFlag(Qt.Window)
            self.windows['everify_form'] = everify_form
        return everify_form

    # open release form
    def open_release_form(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()

        conn = self.create_connection()
        try:
            release_form = self.windows.get('release_form')
            if release_form is None or not release_form.isVisible():
                release_form = ReleaseDocumentWindow(self.current_user, parent=self, main_window=self)
                release_form.setParent(self)
                release_form.setWindowFlag(Qt.Window)
                self.windows['release_form'] = release_form
                
            release_form.show()
            release_form.raise_()
            release_form.activateWindow()
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "ReleaseForm"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    # open release log
    def open_release_log(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()

        conn = self.create_connection()
        try:
            release_log = self.windows.get('release_log')
            if release_log is None or not release_log.isVisible():
                release_log = ReleasingLogViewer(self.current_user, parent=self)
                release_log.setParent(self)
                release_log.setWindowFlag(Qt.Window)
                self.windows['release_log'] = release_log

            release_log.show()
            release_log.raise_()
            release_log.activateWindow()

            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "ReleasingLogViewer"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    # open statistics tools window
    def open_statistics_tools(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()

        conn = self.create_connection()
        try:
            statistics = self.windows.get('statistics')
            if statistics is None or not statistics.isVisible():
                statistics = StatisticsWindow(self.current_user, parent=self)
                statistics.setParent(self)
                statistics.setWindowFlag(Qt.Window)
                self.windows['statistics'] = statistics
                
            statistics.showMaximized()
            statistics.raise_()
            statistics.activateWindow()
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "StatisticsWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()
    
    # open tagging tools window
    def open_tagging_tools(self):
        # Expand sidebar first if it's contracted
        if not self.is_sidebar_expanded:
            self.expand_sidebar()

        conn = self.create_connection()
        try:
            tagging = self.windows.get('tagging')
            if tagging is None or not tagging.isVisible():
                tagging = TaggingMainWindow(self.current_user, parent=self)
                tagging.setParent(self)
                tagging.setWindowFlag(Qt.Window)
                self.windows['tagging'] = tagging
                
            tagging.show()
            tagging.raise_()
            tagging.activateWindow()
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "TaggingWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()
    
    # open book viewer window
    def open_book_viewer(self):
        conn = self.create_connection()
        try:
            book_viewer = self.windows.get('book_viewer')
            if book_viewer is None or not book_viewer.isVisible():
                book_viewer = BookViewerWindow(self.current_user, parent=self)
                book_viewer.setParent(self)
                book_viewer.setWindowFlag(Qt.Window)
                self.windows['book_viewer'] = book_viewer
                
            book_viewer.showMaximized()
            book_viewer.raise_()
            book_viewer.activateWindow()

            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "BookViewerWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    # open manage user window
    def open_manage_user(self):
        conn = self.create_connection()
        try:
            manage_user = self.windows.get('manage_user')
            if manage_user is None or not manage_user.isVisible():
                manage_user = ManageUserForm(self.current_user, parent=self)
                manage_user.setParent(self)
                manage_user.setWindowFlag(Qt.Window)
                self.windows['manage_user'] = manage_user
                
            manage_user.show()
            manage_user.raise_()
            manage_user.activateWindow()

            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "ManageUserForm"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    # open audit log viewer window
    def open_audit_log_viewer(self):
        conn = self.create_connection()
        try:
            audit_log_viewer = self.windows.get('audit_log_viewer')
            if audit_log_viewer is None or not audit_log_viewer.isVisible():
                audit_log_viewer = AuditLogViewer(self.current_user, parent=self)
                audit_log_viewer.setParent(self)
                audit_log_viewer.setWindowFlag(Qt.Window)
                self.windows['audit_log_viewer'] = audit_log_viewer
                
            audit_log_viewer.show()
            audit_log_viewer.raise_()
            audit_log_viewer.activateWindow()
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "OPEN_WINDOW",
                {"window": "AuditLogViewer"}
            )
            conn.commit()
        finally:
            self.closeConnection()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set application style
    app.setStyle("Fusion")
    app.setStyleSheet("""
            QToolTip {
                background-color: #ce305e;  /* Green background */
                color: #000000;             /* White text */
                border: 1px solid #ce305e;  /* Beige border */
                font-size: 12px;
            }
        """)
    mainwindow = MainWindow()
    loginwindow = Login()
    loginwindow.login_success.connect(mainwindow.set_current_user)
    loginwindow.show()
    # mainwindow.show()
    sys.exit(app.exec()) 