import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import requests
import webbrowser
import subprocess
from flask_server.app import get_access_token
from everify_form import eVerifyForm

# IMPORT PYSIDE6 MODULES
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *

# IMPORT UI 
from Search_Birth_Window import Ui_SearchBirthWindow
from Search_Death_Window import Ui_SearchDeathWindow
from Search_Marriage_Window import Ui_SearchMarriageWindow
from audit_logger import AuditLogger
from db_config import POSTGRES_CONFIG

from stylesheets import search_button_style, everify_button_style, button_style, message_box_style

# Base class for searching PDF records
class SearchWindowBase(QMainWindow):
    def __init__(self, ui_class, search_path, form_file, no_record_file, destroyed_file, username, parent=None, main_window=None):
        super().__init__(parent)
        self.ui = ui_class()
        self.ui.setupUi(self)
        
        # print(f"DEBUG - SearchWindowBase received username: {username}")
        self.current_user = username
        self.main_window = main_window

        # Add database connection method
        self.connection = None

        self.setFixedSize(QSize(800, 600))
        self.search_path = search_path
        self.form_file = form_file
        self.no_record_file = no_record_file
        self.destroyed_file = destroyed_file

        # Set styles
        for button in [
            self.ui.search_button, self.ui.create_form, self.ui.no_record,
            self.ui.destroyed, self.ui.auto_form
        ]:
            button.setStyleSheet(search_button_style)
        
        

        self.ui.centralwidget.setStyleSheet("background-color: #FFFFFF;")
        
        self.ui.results_list.setStyleSheet("""
            QListWidget {
                background-color: #F2F2F2;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                color: #212121;  
                padding: 5px;
            }

            QListWidget::item:selected {
                background-color: #ce305e;  
                color: #FFFFFF;
            }

            QListWidget::item:hover {
                background-color: #e0446a;  
                color: #212121;
            }
        """)

        self.ui.search_textEdit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
        """)
        self.ui.regyear_textEdit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
        """)
        self.ui.search_by_comboBox.setFixedWidth(100)
        self.ui.search_by_comboBox.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox::item {
                background-color: #FFFFFF;
                color: #212121;
            }
            QComboBox::item:hover {
                background-color: #ce305e;
                color: #FFFFFF;
            }
            QComboBox::item:selected {
                background-color: #ce305e;
                color: #FFFFFF;
            }
            QComboBox:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
        """)
        
        # Set tooltips
        self.ui.auto_form.setToolTip("Auto-generate Form")
        self.ui.create_form.setToolTip("Create Form")
        self.ui.no_record.setToolTip("Create No Record Form")
        self.ui.destroyed.setToolTip("Create Record Destroyed Form")
        
        # Connect buttons
        # self.ui.auto_form.clicked.connect(self.open_auto_form)
        self.ui.search_button.clicked.connect(self.search_pdfs)
        self.ui.create_form.clicked.connect(self.open_form_file)
        self.ui.no_record.clicked.connect(self.open_no_record)
        self.ui.destroyed.clicked.connect(self.open_destroyed_record)
        
        # Setup combo box
        self.ui.search_by_comboBox.addItems(["Name", "Date", "Reg No."])
        
        # List for found PDFs
        self.found_pdfs = []
        
        # Open file on double-click
        self.ui.results_list.itemDoubleClicked.connect(self.open_selected_file)

        # Add eVerify button
        self.ui.everify_button.setIcon(QIcon("icons/everify-icon.png"))
        self.ui.everify_button.setIconSize(QSize(130, 40))
        self.ui.everify_button.setFixedWidth(130)
        self.ui.everify_button.setText("")
        self.ui.everify_button.setStyleSheet(everify_button_style)
        self.ui.everify_button.setToolTip("Launch eVerify Authentication")
        self.ui.everify_button.clicked.connect(self.start_everify_flow)

        self.ui.horizontalLayout.insertWidget(3, self.ui.everify_button)

        self.ui.horizontalLayout.update()
        self.updateGeometry()

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
    
    def open_form_file(self):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPENED",
                {"form_type": "1A/2A/3A", "path": self.form_file}
            )
            conn.commit()
            self.open_file(self.form_file)
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPEN_ERROR",
                {"form_type": "1A/2A/3A", "error": str(e)}
            )
            conn.commit()
            # QMessageBox.critical(self, "Error", f"Failed to open form: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to open form: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()
    
    def open_no_record(self):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPENED",
                {"form_type": "No Record", "path": self.no_record_file}
            )
            conn.commit()
            self.open_file(self.no_record_file)
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPEN_ERROR",
                {"form_type": "No Record", "error": str(e)}
            )
            conn.commit()
            # QMessageBox.critical(self, "Error", f"Failed to open form: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to open form: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()
    
    def open_destroyed_record(self):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPENED",
                {"form_type": "Destroyed", "path": self.destroyed_file}
            )
            conn.commit()
            self.open_file(self.destroyed_file)
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FORM_OPEN_ERROR",
                {"form_type": "Destroyed", "error": str(e)}
            )
            conn.commit()
            # QMessageBox.critical(self, "Error", f"Failed to open form: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to open form: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()
    
    def open_selected_file(self, item):
        regyear = self.ui.regyear_textEdit.text().strip()
        if not regyear:
            # QMessageBox.warning(self, "Error", "Please enter a registration year before opening a file.")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Error")
            box.setText("Please enter a registration year before opening a file.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
            return
        file_path = os.path.join(self.search_path, regyear, item.text())
        conn = self.create_connection()
        try:
            os.startfile(file_path)
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FILE_OPENED",
                {"file": item.text(), "path": file_path}
            )
            conn.commit()
        except FileNotFoundError:
            # QMessageBox.critical(self, "Error", f"File not found:\n{file_path}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"File not found:\n{file_path}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        except Exception as e:
            # QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"An error occurred:\n{str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FILE_OPEN_ERROR",
                {"error": str(e), "file": item.text()}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def open_file(self, file_path):
        conn = self.create_connection()
        try:
            os.startfile(file_path)
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FILE_OPENED",
                {"path": file_path}
            )
            conn.commit()
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "FILE_OPEN_ERROR",
                {"path": file_path, "error": str(e)}
            )
            conn.commit()
            # QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Failed to open file: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()
    def search_pdfs(self):
        print(f"DEBUG - Current user during search: {self.current_user}")
        self.ui.results_list.clear()
        query = self.ui.search_textEdit.text().strip()
        folder = os.path.join(self.search_path, self.ui.regyear_textEdit.text().strip())
        self.found_pdfs.clear()

        conn = self.create_connection()
        try:
            search_type = self.ui.search_by_comboBox.currentText()
            search_year = self.ui.regyear_textEdit.text().strip()
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "SEARCH_STARTED",
                {
                    "type": search_type,
                    "query": query,
                    "year": search_year,
                    "path": folder
                }
            )
            conn.commit()

            if not folder or not os.path.exists(folder):
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "SEARCH_ERROR",
                    {"error": "Invalid folder path", "year": search_year}
                )
                conn.commit()
                # QMessageBox.warning(self, "Warning", "Cannot find location. Please check the year.")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Cannot find location. Please check the year.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return
            if not query:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "SEARCH_ERROR",
                    {"error": "Empty search query"}
                )
                conn.commit()
                # QMessageBox.warning(self, "Warning", "Please enter a name or date to search.")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Please enter a name or date to search.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return
            search_method = self.find_pdfs_name if search_type in ["Name", "Reg No."] else self.find_pdfs_date
            pdf_files = search_method(folder, query)

            if pdf_files:
                self.ui.results_list.addItems(pdf_files)
                self.found_pdfs.extend(pdf_files)
                self.ui.status_label.setText(f"Found {len(self.found_pdfs)} files.")
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "SEARCH_COMPLETED",
                    {
                        "result_count": len(pdf_files),
                        "type": search_type,
                        "year": search_year
                    }
                )
            else:
                # QMessageBox.information(self, "No Results", "No PDF files found.")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Information)
                box.setWindowTitle("No Results")
                box.setText("No PDF files found.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "SEARCH_NO_RESULTS",
                    {
                        "type": search_type,
                        "query": query,
                        "year": search_year
                    }
                )
            conn.commit()
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "SEARCH_ERROR",
                {
                    "error": str(e),
                    "type": self.ui.search_by_comboBox.currentText(),
                    "query": query,
                    "year": self.ui.regyear_textEdit.text().strip()
                }
            )
            conn.commit()
            # QMessageBox.critical(self, "Error", f"An error occurred during search: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"An error occurred during search: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            self.closeConnection()
    
    def find_pdfs_name(self, folder, query):
        pdf_files = []
        search_terms = [term.strip().lower() for term in query.split(" ")]
        try:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.pdf') and all(term in file.lower() for term in search_terms):
                        pdf_files.append(file)
        except Exception as e:
            conn = self.create_connection()
            try:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "SEARCH_ERROR",
                    {
                        "method": "name_search",
                        "error": str(e),
                        "folder": folder,
                        "query": query
                    }
                )
                conn.commit()
            finally:
                self.closeConnection()
            # QMessageBox.critical(self, "Error", f"An error occurred while searching: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"An error occurred while searching: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        return pdf_files

    def find_pdfs_date(self, folder, query):
        pdf_files = []
        try:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.pdf') and query.lower() in file.lower():
                        pdf_files.append(file)
        except Exception as e:
            conn = self.create_connection()
            try:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "SEARCH_ERROR",
                    {
                        "method": "date_search",
                        "error": str(e),
                        "folder": folder,
                        "query": query
                    }
                )
                conn.commit()
            finally:
                self.closeConnection()
            # QMessageBox.critical(self, "Error", f"An error occurred while searching: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"An error occurred while searching: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        return pdf_files
    
    
    def start_everify_flow(self):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(conn, self.current_user, "EVERIFY_INITIATED")
            conn.commit()
            # Get the access token using backend function
            access_token = get_access_token()  # This handles refresh and token logic

            if access_token:
                print("✅ Token successfully acquired and valid.")
                everify = self.main_window.get_everify_form()
                everify.fullNameVerified.connect(self.populate_search_field)
                everify.show()
                everify.raise_()
                everify.activateWindow()

            else:
                print("❌ Failed to acquire a token.")
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "EVERIFY_TOKEN_ERROR",
                    {"error": "Failed to acquire token"}
                )
                conn.commit()
        finally:
            self.closeConnection()
    
    # def open_everify_form(self):
    #     conn = self.create_connection()
    #     try:
    #         self.everify_form.start_everify_flow()

    #         AuditLogger.log_action(
    #             conn,
    #             self.current_user,
    #             "OPEN_WINDOW",
    #             {"window": "eVerifyForm"}
    #         )
    #         conn.commit()
    #     finally:
    #         self.closeConnection()

    def show_search_window(self):
        """Bring this window to front and activate it."""
        # If it's minimized, restore it
        if self.isMinimized():
            self.showNormal()
        # Show it (if it was hidden)
        self.show()
        # Raise it above other windows
        self.raise_()
        # Give it focus
        self.activateWindow()
    
    def populate_search_field(self, full_name):
        
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "SEARCH_FIELD_POPULATED",
                {"full_name": full_name}
            )
            conn.commit()

            self.show_search_window()

            # Set AlwaysOnTop flag to keep the window on top
            # flags = self.windowFlags()
            # self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            # self.show()           # re-show with the new flag
            # self.raise_()         # bring it to the top of the stacking order
            # self.activateWindow() # give it keyboard/mouse focus
            
            self.ui.search_textEdit.setText(full_name)
            self.ui.search_button.click()
            print(f"🔍 Auto-filled search_textEdit with: {full_name}")
        finally:
            self.closeConnection()

    def closeEvent(self, event):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_CLOSED",
                {"window": self.__class__.__name__}
            )
            conn.commit()

            # Clear all inputs
            self.ui.regyear_textEdit.clear()
            self.ui.search_textEdit.clear()
            self.ui.search_by_comboBox.setCurrentText("Name")
            self.ui.results_list.clear()
            self.ui.status_label.clear()

        finally:
            self.closeConnection()
            event.ignore()
            self.hide()

# Subclasses for each document type
class SearchBirthWindow(SearchWindowBase):
    def __init__(self, username, parent=None, main_window=None):
        super().__init__(Ui_SearchBirthWindow, r"\\server\MCR\LIVE BIRTH", r'forms\FORM 1-A.pdf', r'forms\NO RECORD OF LIVE BIRTH.pdf', r'forms\DESTROYED - LIVE BIRTH.pdf', username, parent, main_window)

class SearchDeathWindow(SearchWindowBase):
    def __init__(self, username, parent=None, main_window=None):
        super().__init__(Ui_SearchDeathWindow, r"\\server\MCR\DEATH", r'forms\FORM 2-A.pdf', r'forms\NO RECORD OF DEATH.pdf', r'forms\DESTROYED - DEATH.pdf', username, parent, main_window)

class SearchMarriageWindow(SearchWindowBase):
    def __init__(self, username, parent=None, main_window=None):
        super().__init__(Ui_SearchMarriageWindow, r"\\server\MCR\MARRIAGE", r'forms\FORM 3-A.pdf', r'forms\NO RECORD OF MARRIAGE.pdf', r'forms\DESTROYED - MARRIAGE.pdf', username, parent, main_window)
