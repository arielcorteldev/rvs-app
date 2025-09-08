import os
import re
import subprocess
import sys
import pymupdf  
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QDate, QSize, QUrl, QSettings
from PySide6.QtGui import QPixmap, QImage, QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from stylesheets import button_style, date_picker_style, combo_box_style, message_box_style
from pdfviewer import PDFViewer
from audit_logger import AuditLogger
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from db_config import POSTGRES_CONFIG


class MarriageTaggingWindow(QWidget):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.current_user = username
        self.connection = None
        self.setWindowTitle("Marriage Records Tagging")
        self.setGeometry(100, 100, 1000, 600)
        # self.showMaximized()
        
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setWindowIcon(QIcon("icons/application.png"))

        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #212121;
            }
            QLineEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
            QComboBox {
                font-weight: bold;
            }
            QComboBox QLineEdit {
                font-weight: bold;
            }
            QDateEdit {
                font-weight: bold;
            }
        """)

        self.default_directory = r"\\server\MCR\MARRIAGE"
        self.selected_pdf = None
        self.last_page_no = None
        self.last_book_no = None
        self.last_reg_date = None
        self.last_place_of_marriage = None
        self.last_date_of_marriage = None
        self.settings = QSettings("OCCR", "RVS")
        self.pending_select_pdf = None

        self.init_ui()
    
    def create_connection(self):
        if self.connection is None:
            self.connection = psycopg2.connect(**POSTGRES_CONFIG)
            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return self.connection

    def closeConnection(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignTop)
        
        # Select Folder Button
        self.folder_button = QPushButton("Select Folder")
        self.folder_button.setStyleSheet(button_style)
        self.folder_button.setFixedWidth(130)
        self.folder_button.clicked.connect(self.select_folder)
        main_layout.addWidget(self.folder_button)

        # Create a scroll area for the form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedWidth(750)
        
        # Create a widget to hold the form
        form_widget = QWidget()
        form_layout = QVBoxLayout()
        form_layout.setAlignment(Qt.AlignTop)
        form_widget.setLayout(form_layout)

        # Create horizontal layouts for grouped fields
        # Page No, Book No, Registry No
        reg_info_layout = QHBoxLayout()
        reg_info_layout.setSpacing(10)
        
        page_no_container = QVBoxLayout()
        self.page_no_input = QLineEdit()
        self.page_no_input.setPlaceholderText("Page No.")
        self.page_no_input.setFixedWidth(220)
        page_no_container.addWidget(QLabel("Page No.:"))
        page_no_container.addWidget(self.page_no_input)
        reg_info_layout.addLayout(page_no_container)

        book_no_container = QVBoxLayout()
        self.book_no_input = QLineEdit()
        self.book_no_input.setPlaceholderText("Book No.")
        self.book_no_input.setFixedWidth(220)
        book_no_container.addWidget(QLabel("Book No.:"))
        book_no_container.addWidget(self.book_no_input)
        reg_info_layout.addLayout(book_no_container)

        reg_no_container = QVBoxLayout()
        self.reg_no_input = QLineEdit()
        self.reg_no_input.setPlaceholderText("Registry No.")
        self.reg_no_input.setFixedWidth(220)
        reg_no_container.addWidget(QLabel("Registry No.:"))
        reg_no_container.addWidget(self.reg_no_input)
        reg_info_layout.addLayout(reg_no_container)
        form_layout.addLayout(reg_info_layout)

        # HUSBAND SECTION
        # Husband Name and Age
        husband_name_age_layout = QHBoxLayout()
        husband_name_age_layout.setSpacing(10)

        husband_name_container = QVBoxLayout()
        self.husband_name_input = QLineEdit()
        self.husband_name_input.setPlaceholderText("Husband Name")
        self.husband_name_input.setFixedWidth(500)
        husband_name_container.addWidget(QLabel("Husband Name:"))
        husband_name_container.addWidget(self.husband_name_input)
        husband_name_age_layout.addLayout(husband_name_container)

        husband_age_container = QVBoxLayout()
        self.husband_age_input = QLineEdit()
        self.husband_age_input.setPlaceholderText("Age")
        self.husband_age_input.setFixedWidth(150)
        husband_age_container.addWidget(QLabel("Age:"))
        husband_age_container.addWidget(self.husband_age_input)
        husband_name_age_layout.addLayout(husband_age_container)

        form_layout.addLayout(husband_name_age_layout)

        # Husband Civil Status and Nationality
        husband_cs_nat_layout = QHBoxLayout()
        husband_cs_nat_layout.setSpacing(10)

        husband_nat_container = QVBoxLayout()
        self.husband_nationality_combo = QComboBox()
        self.husband_nationality_combo.setEditable(True)
        self.husband_nationality_combo.addItems([
            "FILIPINO",
            "CHINESE",
            "INDIAN",
            "AMERICAN",
            "JAPANESE",
            "SOUTH KOREAN",
            "GERMAN",
            "AUSTRALIAN",
            "TAIWANESE",
            "INDONESIAN",
            "VIETNAMESE",
        ])
        self.husband_nationality_combo.setFixedWidth(350)
        self.husband_nationality_combo.setStyleSheet(combo_box_style)
        husband_nat_container.addWidget(QLabel("Nationality:"))
        husband_nat_container.addWidget(self.husband_nationality_combo)
        husband_cs_nat_layout.addLayout(husband_nat_container)

        husband_cs_container = QVBoxLayout()
        self.husband_civil_status_combo = QComboBox()
        self.husband_civil_status_combo.addItems(["SINGLE", "WIDOW", "WIDOWER"])
        self.husband_civil_status_combo.setFixedWidth(300)
        self.husband_civil_status_combo.setStyleSheet(combo_box_style)
        husband_cs_container.addWidget(QLabel("Civil Status:"))
        husband_cs_container.addWidget(self.husband_civil_status_combo)
        husband_cs_nat_layout.addLayout(husband_cs_container)

        form_layout.addLayout(husband_cs_nat_layout)

        # Husband Parents Name
        husband_parents_layout = QHBoxLayout()
        husband_parents_layout.setSpacing(10)

        husband_father_container = QVBoxLayout()
        self.husband_father_name_input = QLineEdit()
        self.husband_father_name_input.setPlaceholderText("Name of Father")
        self.husband_father_name_input.setFixedWidth(325)
        husband_father_container.addWidget(QLabel("Name of Father:"))
        husband_father_container.addWidget(self.husband_father_name_input)
        husband_parents_layout.addLayout(husband_father_container)

        husband_mother_container = QVBoxLayout()
        self.husband_mother_name_input = QLineEdit()
        self.husband_mother_name_input.setPlaceholderText("Name of Mother")
        self.husband_mother_name_input.setFixedWidth(325)
        husband_mother_container.addWidget(QLabel("Name of Mother:"))
        husband_mother_container.addWidget(self.husband_mother_name_input)
        husband_parents_layout.addLayout(husband_mother_container)

        form_layout.addLayout(husband_parents_layout)

        # WIFE SECTION
        # Wife Name and Age
        wife_name_age_layout = QHBoxLayout()
        wife_name_age_layout.setSpacing(10)

        wife_name_container = QVBoxLayout()
        self.wife_name_input = QLineEdit()
        self.wife_name_input.setPlaceholderText("Wife Name")
        self.wife_name_input.setFixedWidth(500)
        wife_name_container.addWidget(QLabel("Wife Name:"))
        wife_name_container.addWidget(self.wife_name_input)
        wife_name_age_layout.addLayout(wife_name_container)

        wife_age_container = QVBoxLayout()
        self.wife_age_input = QLineEdit()
        self.wife_age_input.setPlaceholderText("Age")
        self.wife_age_input.setFixedWidth(150)
        wife_age_container.addWidget(QLabel("Age:"))
        wife_age_container.addWidget(self.wife_age_input)
        wife_name_age_layout.addLayout(wife_age_container)

        form_layout.addLayout(wife_name_age_layout)

        # Wife Civil Status and Nationality
        wife_cs_nat_layout = QHBoxLayout()
        wife_cs_nat_layout.setSpacing(10)

        wife_nat_container = QVBoxLayout()
        self.wife_nationality_combo = QComboBox()
        self.wife_nationality_combo.setEditable(True)
        self.wife_nationality_combo.addItems([
            "FILIPINO",
            "CHINESE",
            "INDIAN",
            "AMERICAN",
            "JAPANESE",
            "SOUTH KOREAN",
            "GERMAN",
            "AUSTRALIAN",
            "TAIWANESE",
            "INDONESIAN",
            "VIETNAMESE",
        ])
        self.wife_nationality_combo.setFixedWidth(350)
        self.wife_nationality_combo.setStyleSheet(combo_box_style)
        wife_nat_container.addWidget(QLabel("Nationality:"))
        wife_nat_container.addWidget(self.wife_nationality_combo)
        wife_cs_nat_layout.addLayout(wife_nat_container)

        wife_cs_container = QVBoxLayout()
        self.wife_civil_status_combo = QComboBox()
        self.wife_civil_status_combo.addItems(["SINGLE", "WIDOW", "WIDOWER"])
        self.wife_civil_status_combo.setFixedWidth(300)
        self.wife_civil_status_combo.setStyleSheet(combo_box_style)
        wife_cs_container.addWidget(QLabel("Civil Status:"))
        wife_cs_container.addWidget(self.wife_civil_status_combo)
        wife_cs_nat_layout.addLayout(wife_cs_container)

        form_layout.addLayout(wife_cs_nat_layout)

        # Wife Parents Name
        wife_parents_layout = QHBoxLayout()
        wife_parents_layout.setSpacing(10)

        wife_father_container = QVBoxLayout()
        self.wife_father_name_input = QLineEdit()
        self.wife_father_name_input.setPlaceholderText("Name of Father")
        self.wife_father_name_input.setFixedWidth(325)
        wife_father_container.addWidget(QLabel("Name of Father:"))
        wife_father_container.addWidget(self.wife_father_name_input)
        wife_parents_layout.addLayout(wife_father_container)

        wife_mother_container = QVBoxLayout()
        self.wife_mother_name_input = QLineEdit()
        self.wife_mother_name_input.setPlaceholderText("Name of Mother")
        self.wife_mother_name_input.setFixedWidth(325)
        wife_mother_container.addWidget(QLabel("Name of Mother:"))
        wife_mother_container.addWidget(self.wife_mother_name_input)
        wife_parents_layout.addLayout(wife_mother_container)

        form_layout.addLayout(wife_parents_layout)

        # Date of Marriage and Place of Marriage
        marriage_info_layout = QHBoxLayout()
        marriage_info_layout.setSpacing(10)

        dom_container = QVBoxLayout()
        self.date_of_marriage_input = QDateEdit()
        self.date_of_marriage_input.setCalendarPopup(True)
        self.date_of_marriage_input.setDate(QDate.currentDate())
        self.date_of_marriage_input.setFixedWidth(220)
        self.date_of_marriage_input.setStyleSheet(date_picker_style)
        dom_container.addWidget(QLabel("Date of Marriage:"))
        dom_container.addWidget(self.date_of_marriage_input)
        marriage_info_layout.addLayout(dom_container)

        pom_container = QVBoxLayout()
        self.place_of_marriage_combo = QComboBox()
        self.place_of_marriage_combo.setEditable(True)
        self.place_of_marriage_combo.addItems([
            "NATIONAL SHRINE AND PARISH OF OUR LADY OF THE ASSUMPTION",
            "ASSUMPTION IN THE HILLS PARISH",
            "STO. NIÑO DE IBARRA PARISH",
            "MUNICIPAL TRIAL COURT IN CITIES",
        ])
        self.place_of_marriage_combo.setFixedWidth(450)
        self.place_of_marriage_combo.setStyleSheet(combo_box_style)
        pom_container.addWidget(QLabel("Place of Marriage:"))
        pom_container.addWidget(self.place_of_marriage_combo)
        marriage_info_layout.addLayout(pom_container)

        form_layout.addLayout(marriage_info_layout)

        # Ceremony Type, Late Registration, and Date of Registration
        final_info_layout = QHBoxLayout()
        final_info_layout.setSpacing(10)

        ceremony_type_container = QVBoxLayout()
        self.ceremony_type_combo = QComboBox()
        self.ceremony_type_combo.setEditable(True)
        self.ceremony_type_combo.addItems([
            "ROMAN CATHOLIC WEDDING",
            "CIVIL WEDDING",
            "OTHER RELIGIOUS WEDDING",
        ])
        self.ceremony_type_combo.setFixedWidth(270)
        self.ceremony_type_combo.setStyleSheet(combo_box_style)
        ceremony_type_container.addWidget(QLabel("Ceremony Type:"))
        ceremony_type_container.addWidget(self.ceremony_type_combo)
        final_info_layout.addLayout(ceremony_type_container)

        late_reg_container = QVBoxLayout()
        self.late_reg_combo = QComboBox()
        self.late_reg_combo.addItems(["NO", "YES"])
        self.late_reg_combo.setFixedWidth(200)
        self.late_reg_combo.setStyleSheet(combo_box_style)
        late_reg_container.addWidget(QLabel("Late Registration:"))
        late_reg_container.addWidget(self.late_reg_combo)
        final_info_layout.addLayout(late_reg_container)

        reg_date_container = QVBoxLayout()
        self.date_of_reg_input = QDateEdit()
        self.date_of_reg_input.setCalendarPopup(True)
        self.date_of_reg_input.setDate(QDate.currentDate())
        self.date_of_reg_input.setFixedWidth(200)
        self.date_of_reg_input.setStyleSheet(date_picker_style)
        reg_date_container.addWidget(QLabel("Date of Registration:"))
        reg_date_container.addWidget(self.date_of_reg_input)
        final_info_layout.addLayout(reg_date_container)
        form_layout.addLayout(final_info_layout)

        # Add the form widget to the scroll area
        scroll_area.setWidget(form_widget)
        main_layout.addWidget(scroll_area)

        # Action Buttons
        button_layout = QHBoxLayout()

        save_btn = QPushButton("Save Tags")
        save_btn.clicked.connect(self.save_tags)
        save_btn.setFixedWidth(130)
        button_layout.addWidget(save_btn)

        delete_btn = QPushButton("Delete Tags")
        delete_btn.clicked.connect(self.delete_tags)
        delete_btn.setFixedWidth(130)
        button_layout.addWidget(delete_btn)

        # clear_btn = QPushButton("Clear All Tags")
        # clear_btn.clicked.connect(self.clear_all_tags)
        # clear_btn.setFixedWidth(130)
        # button_layout.addWidget(clear_btn)

        save_btn.setStyleSheet(button_style)
        delete_btn.setStyleSheet(button_style)
        # clear_btn.setStyleSheet(button_style)

        button_layout.setSpacing(5)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(Qt.AlignLeft)

        main_layout.addLayout(button_layout)

        # PDF List Preview
        self.pdf_list = QListWidget()
        self.pdf_list.setFixedWidth(750)
        self.pdf_list.setIconSize(QSize(100, 140))
        self.pdf_list.itemClicked.connect(self.show_preview)
        self.pdf_list.setStyleSheet("""
            QListWidget {
                background-color: #FFFFFF;
                color: #212121;
            }
            QListWidget::item {
                background-color: #FFFFFF;
                color: #212121;
            }
            QListWidget::item:hover {
                background-color: #e0446a;
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                background-color: #ce305e;
                color: #FFFFFF;
            }
        """)

        self.pdf_list.currentItemChanged.connect(self.show_preview)
        main_layout.addWidget(self.pdf_list)

        # PDF Viewer Section
        pdf_layout = QVBoxLayout()
        pdf_controls = QHBoxLayout()

        self.pdf_viewer = PDFViewer()
        pdf_layout.addWidget(self.pdf_viewer)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.clicked.connect(self.zoom_in_pdf)
        zoom_in_btn.setStyleSheet(button_style)
        pdf_controls.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("-")
        zoom_out_btn.clicked.connect(self.zoom_out_pdf)
        zoom_out_btn.setStyleSheet(button_style)
        pdf_controls.addWidget(zoom_out_btn)

        pdf_layout.addLayout(pdf_controls)

        # Split Layout: Inputs Left, PDF Right
        split_layout = QHBoxLayout()
        split_layout.addLayout(main_layout, stretch=2)
        split_layout.addLayout(pdf_layout, stretch=5)

        self.setLayout(split_layout)

        # self.load_pdfs(self.default_directory)

    def select_folder(self):
        """Opens a folder selection dialog and loads PDFs."""
        conn = self.create_connection()
        try:
            folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", self.default_directory)
            if folder_path:
                # persist last selected folder
                self.settings.setValue("marriage/last_folder", folder_path)
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "FOLDER_SELECTED",
                    {"path": folder_path}
                )
                conn.commit()
                self.load_pdfs(folder_path)
        finally:
            self.closeConnection()

    def load_pdfs(self, folder_path, selected_file_path=None):
        """Loads PDFs from a folder and generates thumbnails. Optionally selects a file."""
        conn = self.create_connection()
        progress = None
        try:
            self.pdf_list.clear()
            if not os.path.exists(folder_path):
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "PDF_LOAD_ERROR",
                    {"error": "Folder not found", "path": folder_path}
                )
                conn.commit()
                QMessageBox.warning(self, "Error", f"Folder not found: {folder_path}")
                return
            
            # Show loading progress
            progress = QProgressDialog("Loading PDFs...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("Loading")
            progress.setCancelButton(None)  # Remove cancel button
            progress.show()
            QApplication.processEvents()
            
            pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
            pdf_files.sort(key=self.natural_sort_key)
            
            failed_files = []
            for filename in pdf_files:
                try:
                    file_path = os.path.join(folder_path, filename)
                    thumbnail = self.generate_thumbnail(file_path)
                    
                    item = QListWidgetItem(QIcon(thumbnail), filename)
                    item.setSizeHint(QSize(0, 40))
                    item.setData(Qt.UserRole, file_path)
                    self.pdf_list.addItem(item)
                except Exception as e:
                    failed_files.append((filename, str(e)))
                    continue
            
            if failed_files:
                error_msg = "Failed to load some PDFs:\n\n"
                for filename, error in failed_files:
                    error_msg += f"{filename}: {error}\n"
                QMessageBox.warning(self, "Warning", error_msg)
            
            AuditLogger.log_action(
                conn,
                self.current_user,
                "PDFS_LOADED",
                {"folder": folder_path, "count": len(pdf_files), "failed": len(failed_files)}
            )
            conn.commit()
            # auto-select previously selected file if provided
            target = selected_file_path or self.pending_select_pdf
            if target:
                for i in range(self.pdf_list.count()):
                    item = self.pdf_list.item(i)
                    if item.data(Qt.UserRole) == target:
                        self.pdf_list.setCurrentItem(item)
                        self.show_preview(item)
                        break
                self.pending_select_pdf = None
            
        except Exception as e:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "PDF_LOAD_ERROR",
                {"error": str(e), "path": folder_path}
            )
            conn.commit()
            QMessageBox.critical(self, "Error", f"Failed to load PDFs: {str(e)}")
        finally:
            if progress:
                progress.close()
                progress.deleteLater()  # Ensure the dialog is properly destroyed
            self.closeConnection()

    def natural_sort_key(self, text):
        """Sort filenames naturally, treating numbers correctly."""
        def convert(text):
            return int(text) if text.isdigit() else text.lower()
        
        alphanum_key = [convert(c) for c in re.split('([0-9]+)', text)]
        return alphanum_key

    
    def generate_thumbnail(self, pdf_path):
        """Extracts the first page of a PDF and converts it to a QPixmap."""
        try:
            doc = pymupdf.open(pdf_path)
            if doc.page_count == 0:
                raise Exception("PDF has no pages")
            
            page = doc[0]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5))  # Scale down image
            
            # Convert raw image data to QImage
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGBA8888)
            
            # Clean up resources
            doc.close()
            
            return QPixmap.fromImage(img)
        except Exception as e:
            raise Exception(f"Failed to generate thumbnail: {str(e)}")

    def show_preview(self, item):
        """Loads the selected PDF and stores its file path."""
        conn = self.create_connection()
        try:
            self.selected_pdf = item.data(Qt.UserRole)
            if self.selected_pdf:
                # persist last selected PDF
                self.settings.setValue("marriage/last_pdf", self.selected_pdf)
                self.last_page_no = self.page_no_input.text()
                self.last_book_no = self.book_no_input.text()
                self.last_reg_date = self.date_of_reg_input.date().toString("yyyy-MM-dd")
                self.last_place_of_marriage = self.place_of_marriage_combo.currentText()
                self.last_date_of_marriage = self.date_of_marriage_input.date().toString("yyyy-MM-dd")
                self.pdf_viewer.load_pdf(self.selected_pdf)
                self.load_existing_tags(self.selected_pdf)

                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "PDF_PREVIEWED",
                    {"file": self.selected_pdf}
                )
        finally:
            self.closeConnection()

    def get_selected_pdf(self):
        """Returns the currently selected PDF file path."""
        return self.selected_pdf


    def load_existing_tags(self, file_path):
        conn = self.create_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    husband_name, wife_name, date_of_marriage, page_no, book_no, reg_no, 
                    husband_age, wife_age, husb_nationality, wife_nationality,
                    husb_civil_status, wife_civil_status, husb_mother, wife_mother,
                    husb_father, wife_father, date_of_reg, place_of_marriage,
                    ceremony_type, late_registration
                FROM marriage_index 
                WHERE file_path = %s
            """, (file_path,))

            result = cursor.fetchone()

            if result:
                (husband_name, wife_name, date_of_marriage, page_no, book_no, reg_no, 
                husband_age, wife_age, husb_nationality, wife_nationality,
                husb_civil_status, wife_civil_status, husb_mother, wife_mother,
                husb_father, wife_father, date_of_reg, place_of_marriage,
                ceremony_type, late_registration) = result

                # Set QLineEdit values
                self.page_no_input.setText(str(page_no) if page_no else "")
                self.book_no_input.setText(str(book_no) if book_no else "")
                self.reg_no_input.setText(reg_no if reg_no else "")
                self.husband_name_input.setText(husband_name if husband_name else "")
                self.wife_name_input.setText(wife_name if wife_name else "")
                self.husband_age_input.setText(str(husband_age) if husband_age else "")
                self.wife_age_input.setText(str(wife_age) if wife_age else "")
                self.husband_mother_name_input.setText(husb_mother if husb_mother else "")
                self.husband_father_name_input.setText(husb_father if husb_father else "")
                self.wife_mother_name_input.setText(wife_mother if wife_mother else "")
                self.wife_father_name_input.setText(wife_father if wife_father else "")

                # Set QComboBox values
                self.place_of_marriage_combo.setCurrentText(place_of_marriage if place_of_marriage else "")
                self.husband_nationality_combo.setCurrentText(husb_nationality if husb_nationality else "")
                self.wife_nationality_combo.setCurrentText(wife_nationality if wife_nationality else "")
                self.husband_civil_status_combo.setCurrentText(husb_civil_status if husb_civil_status else "")
                self.wife_civil_status_combo.setCurrentText(wife_civil_status if wife_civil_status else "")
                self.ceremony_type_combo.setCurrentText(ceremony_type if ceremony_type else "")
                self.late_reg_combo.setCurrentText("Yes" if late_registration else "No")

                # Handle dates
                if date_of_marriage:
                    self.date_of_marriage_input.setDate(QDate.fromString(date_of_marriage.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                else:
                    self.date_of_marriage_input.setDate(QDate.currentDate())

                if date_of_reg:
                    self.date_of_reg_input.setDate(QDate.fromString(date_of_reg.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                else:
                    self.date_of_reg_input.setDate(QDate.currentDate())

            else:
                # Clear all fields
                self.page_no_input.setText(self.last_page_no)
                self.book_no_input.setText(self.last_book_no)
                self.reg_no_input.clear()
                self.husband_name_input.clear()
                self.wife_name_input.clear()
                self.husband_age_input.clear()
                self.wife_age_input.clear()
                self.husband_mother_name_input.clear()
                self.husband_father_name_input.clear()
                self.wife_mother_name_input.clear()
                self.wife_father_name_input.clear()
                
                self.place_of_marriage_combo.setCurrentText(self.last_place_of_marriage)
                self.husband_nationality_combo.setCurrentIndex(0)
                self.wife_nationality_combo.setCurrentIndex(0)
                self.husband_civil_status_combo.setCurrentIndex(0)
                self.wife_civil_status_combo.setCurrentIndex(0)
                self.ceremony_type_combo.setCurrentIndex(0)
                self.late_reg_combo.setCurrentIndex(0)
                
                self.date_of_reg_input.setDate(QDate.fromString(self.last_reg_date, "yyyy-MM-dd"))
                self.date_of_marriage_input.setDate(QDate.fromString(self.last_date_of_marriage, "yyyy-MM-dd"))
        finally:
            if cursor:
                cursor.close()
            self.closeConnection()

    def save_tags(self):
        conn = self.create_connection()
        try:
            if not self.selected_pdf:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAG_SAVE_FAILED",
                    {"reason": "no_pdf_selected"}
                )
                # QMessageBox.warning(self, "Error", "Please select a PDF file before saving tags!")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Warning")
                box.setText("Please select a PDF file before saving tags.")
                box.setStandardButtons(QMessageBox.Ok)

                box.setStyleSheet(message_box_style)

                box.exec()
                return

            cursor = conn.cursor()

            try:
                # Get values from input fields
                page_no = int(self.page_no_input.text()) if self.page_no_input.text() else None
                book_no = int(self.book_no_input.text()) if self.book_no_input.text() else None
                reg_no = self.reg_no_input.text()
                husband_name = self.husband_name_input.text()
                wife_name = self.wife_name_input.text()
                husband_age = self.husband_age_input.text()
                wife_age = self.wife_age_input.text()
                husb_mother = self.husband_mother_name_input.text()
                wife_mother = self.wife_mother_name_input.text()
                husb_father = self.husband_father_name_input.text()
                wife_father = self.wife_father_name_input.text()
                date_of_marriage = self.date_of_marriage_input.date().toString("yyyy-MM-dd")
                date_of_reg = self.date_of_reg_input.date().toString("yyyy-MM-dd")
                place_of_marriage = self.place_of_marriage_combo.currentText()
                husb_nationality = self.husband_nationality_combo.currentText()
                wife_nationality = self.wife_nationality_combo.currentText()
                husb_civil_status = self.husband_civil_status_combo.currentText()
                wife_civil_status = self.wife_civil_status_combo.currentText()
                ceremony_type = self.ceremony_type_combo.currentText()
                late_registration = self.late_reg_combo.currentText() == "Yes"

                cursor.execute("""
                    INSERT INTO marriage_index (
                        file_path, husband_name, wife_name, date_of_marriage, page_no, book_no, reg_no,
                        husband_age, wife_age, husb_nationality, wife_nationality,
                        husb_civil_status, wife_civil_status, husb_mother, wife_mother,
                        husb_father, wife_father, date_of_reg, place_of_marriage,
                        ceremony_type, late_registration
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT(file_path) DO UPDATE SET
                        husband_name = EXCLUDED.husband_name,
                        wife_name = EXCLUDED.wife_name,
                        date_of_marriage = EXCLUDED.date_of_marriage,
                        page_no = EXCLUDED.page_no,
                        book_no = EXCLUDED.book_no,
                        reg_no = EXCLUDED.reg_no,
                        husband_age = EXCLUDED.husband_age,
                        wife_age = EXCLUDED.wife_age,
                        husb_nationality = EXCLUDED.husb_nationality,
                        wife_nationality = EXCLUDED.wife_nationality,
                        husb_civil_status = EXCLUDED.husb_civil_status,
                        wife_civil_status = EXCLUDED.wife_civil_status,
                        husb_mother = EXCLUDED.husb_mother,
                        wife_mother = EXCLUDED.wife_mother,
                        husb_father = EXCLUDED.husb_father,
                        wife_father = EXCLUDED.wife_father,
                        date_of_reg = EXCLUDED.date_of_reg,
                        place_of_marriage = EXCLUDED.place_of_marriage,
                        ceremony_type = EXCLUDED.ceremony_type,
                        late_registration = EXCLUDED.late_registration
                """, (
                    self.selected_pdf, husband_name, wife_name, date_of_marriage, page_no, book_no, reg_no,
                    husband_age, wife_age, husb_nationality, wife_nationality,
                    husb_civil_status, wife_civil_status, husb_mother, wife_mother,
                    husb_father, wife_father, date_of_reg,
                    place_of_marriage, ceremony_type, late_registration
                ))

                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAGS_SAVED",
                    {
                        "file": self.selected_pdf,
                        "record_type": "Marriage"
                    }
                )
                # QMessageBox.information(self, "Success", "Tags saved successfully.")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Information)
                box.setWindowTitle("Success")
                box.setText("Tags saved successfully.")
                box.setStandardButtons(QMessageBox.Ok)

                box.setStyleSheet(message_box_style)
                box.exec()

            except Exception as e:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAG_SAVE_ERROR",
                    {
                        "error": str(e),
                        "file": self.selected_pdf,
                        "record_type": "Marriage"
                    }
                )
                # QMessageBox.critical(self, "Error", f"Failed to save tags: {str(e)}")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Critical)
                box.setWindowTitle("Error")
                box.setText(f"Failed to save tags: {str(e)}")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
        finally:
            if cursor:
                cursor.close()
            self.closeConnection()

    def delete_tags(self):
        conn = self.create_connection()
        try:
            if not self.selected_pdf:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAG_DELETE_FAILED",
                    {"reason": "no_pdf_selected"}
                )
                conn.commit()
                # QMessageBox.warning(self, "Error", "Please select a PDF file to delete its tags!")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Warning)
                box.setWindowTitle("Error")
                box.setText("Please select a PDF file to delete its tags.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                return

            cursor = conn.cursor()
            cursor.execute("DELETE FROM marriage_index WHERE file_path = %s", (self.selected_pdf,))
            conn.commit()

            AuditLogger.log_action(
                conn,
                self.current_user,
                "TAGS_DELETED",
                {"file": self.selected_pdf, "table": "marriage_index"}
            )
            conn.commit()

            # Clear all input fields after successful deletion
            self.page_no_input.clear()
            self.book_no_input.clear()
            self.reg_no_input.clear()
            self.husband_name_input.clear()
            self.wife_name_input.clear()
            self.husband_age_input.clear()
            self.wife_age_input.clear()
            self.husband_mother_name_input.clear()
            self.husband_father_name_input.clear()
            self.wife_mother_name_input.clear()
            self.wife_father_name_input.clear()
            
            self.place_of_marriage_combo.setCurrentIndex(0)
            self.husband_nationality_combo.setCurrentIndex(0)
            self.wife_nationality_combo.setCurrentIndex(0)
            self.husband_civil_status_combo.setCurrentIndex(0)
            self.wife_civil_status_combo.setCurrentIndex(0)
            self.ceremony_type_combo.setCurrentIndex(0)
            self.late_reg_combo.setCurrentIndex(0)
            
            self.date_of_reg_input.setDate(QDate.currentDate())
            self.date_of_marriage_input.setDate(QDate.currentDate())
            
            # QMessageBox.information(self, "Success", "Tags deleted successfully!")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Success")
            box.setText("Tags deleted successfully.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        finally:
            if cursor:
                cursor.close()
            self.closeConnection()

    # def clear_all_tags(self):
    #     conn = self.create_connection()
    #     try:
    #         reply = QMessageBox.question(
    #             self, 
    #             "Clear All Tags", 
    #             "Are you sure you want to clear all tags from the database?",
    #             QMessageBox.Yes | QMessageBox.No, 
    #             QMessageBox.No
    #         )
            
    #         if reply == QMessageBox.Yes:
    #             cursor = conn.cursor()
    #             cursor.execute("DELETE FROM birth_index")
    #             conn.commit()

    #             AuditLogger.log_action(
    #                 conn,
    #                 self.current_user,
    #                 "ALL_TAGS_CLEARED",
    #                 {"tables": ["birth_index"]}
    #             )
    #             conn.commit()
    #             # QMessageBox.information(self, "Success", "All tags have been cleared from the database.")
    #             box = QMessageBox(self)
    #             box.setIcon(QMessageBox.Information)
    #             box.setWindowTitle("Success")
    #             box.setText("All tags have been cleared from the database.")
    #             box.setStandardButtons(QMessageBox.Ok)
    #             box.setStyleSheet(message_box_style)
    #             box.exec()
    #     finally:
    #         if cursor:
    #             cursor.close()
    #         self.closeConnection()

    def get_table_name(self, file_path):
        """Determine the table name based on file path or other logic."""
        return 'marriage_index'
    
    def zoom_in_pdf(self):
        """Increase the zoom level of the PDF Viewer."""
        self.pdf_viewer.set_zoom(self.pdf_viewer.zoom_factor + 0.1)

    def zoom_out_pdf(self):
        """Decrease the zoom level of the PDF Viewer."""
        self.pdf_viewer.set_zoom(max(0.1, self.pdf_viewer.zoom_factor - 0.1))

    def showEvent(self, event):
        super().showEvent(event)
        conn = self.create_connection()
        try:
            # attempt to restore last session state
            last_folder = self.settings.value("marriage/last_folder", type=str)
            last_pdf = self.settings.value("marriage/last_pdf", type=str)
            if last_folder and os.path.isdir(last_folder):
                if last_pdf and os.path.isfile(last_pdf):
                    self.pending_select_pdf = last_pdf
                self.load_pdfs(last_folder)
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_OPENED",
                {"window": "MarriageTaggingWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()

    def closeEvent(self, event):
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_CLOSED",
                {"window": "MarriageTaggingWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()
            event.ignore()
            self.hide()

    # def handle_marriage_place_change(self, value):
    #     """Handle changes in marriage place combo box."""
    #     null_triggers = ["Not Married", "Forgotten", "Don't Know"]

    #     if value in null_triggers:
    #         # Set to null date and disable
    #         self.date_of_marriage_input.setDate(QDate())  # Clears the date
    #         self.date_of_marriage_input.setSpecialValueText("")  # Optional: show blank
    #         self.date_of_marriage_input.setEnabled(False)
    #     else:
    #         # Re-enable and set to current date if empty
    #         self.date_of_marriage_input.setEnabled(True)
    #         if not self.date_of_marriage_input.date().isValid() or self.date_of_marriage_input.date() == QDate():
    #             self.date_of_marriage_input.setDate(QDate.currentDate())


# if __name__ == "__main__":
# 	app = QApplication([])
# 	window = BirthTaggingWindow()
# 	window.show()
# 	app.exec()