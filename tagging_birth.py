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
from PySide6.QtGui import QPixmap, QImage, QIcon, QShortcut, QKeySequence
from PySide6.QtWebEngineWidgets import QWebEngineView
from stylesheets import button_style, date_picker_style, combo_box_style, message_box_style
from pdfviewer import PDFViewer
from audit_logger import AuditLogger
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from db_config import POSTGRES_CONFIG


class BirthTaggingWindow(QWidget):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.current_user = username
        self.connection = None
        self.setWindowTitle("Live Birth Records Tagging")
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
            QWidget#form_area[saved="true"] {
                background-color: #dff9e5; /* light green form background */
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

        self.default_directory = r"\\server\MCR\LIVE BIRTH"
        self.selected_pdf = None
        self.last_page_no = None
        self.last_book_no = None
        self.last_reg_date = None
        self.last_place_of_birth = None

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
        form_widget.setObjectName("form_area")
        self.form_area = form_widget
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

        # Name and Sex
        name_sex_layout = QHBoxLayout()
        name_sex_layout.setSpacing(10)

        name_container = QVBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        self.name_input.setFixedWidth(450)
        name_container.addWidget(QLabel("Name:"))
        name_container.addWidget(self.name_input)
        name_sex_layout.addLayout(name_container)

        sex_container = QVBoxLayout()
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(["MALE", "FEMALE"])
        self.sex_combo.setFixedWidth(220)
        self.sex_combo.setStyleSheet(combo_box_style)
        sex_container.addWidget(QLabel("Sex:"))
        sex_container.addWidget(self.sex_combo)
        name_sex_layout.addLayout(sex_container)
        form_layout.addLayout(name_sex_layout)

        # Date of Birth and Place of Birth
        birth_info_layout = QHBoxLayout()
        birth_info_layout.setSpacing(10)

        dob_container = QVBoxLayout()
        self.date_of_birth_input = QDateEdit()
        self.date_of_birth_input.setCalendarPopup(True)
        self.date_of_birth_input.setDate(QDate.currentDate())
        self.date_of_birth_input.setFixedWidth(150)
        self.date_of_birth_input.setStyleSheet(date_picker_style)
        dob_container.addWidget(QLabel("Date of Birth:"))
        dob_container.addWidget(self.date_of_birth_input)
        birth_info_layout.addLayout(dob_container)

        pob_container = QVBoxLayout()
        self.place_of_birth_combo = QComboBox()
        self.place_of_birth_combo.setEditable(True)
        self.place_of_birth_combo.addItems([
            "SALVACION OPPUS YÑIGUEZ MEMORIAL PROVINCIAL HOSPITAL",
            "MAASIN MEDCITY HOSPITAL",
            "LIVINGHOPE HOSPITAL, INC.",
            "CM MATERNITY CLINIC",
        ])
        self.place_of_birth_combo.setFixedWidth(400)
        self.place_of_birth_combo.setStyleSheet(combo_box_style)
        pob_container.addWidget(QLabel("Place of Birth:"))
        pob_container.addWidget(self.place_of_birth_combo)
        birth_info_layout.addLayout(pob_container)

        type_of_birth_container = QVBoxLayout()
        self.type_of_birth_combo = QComboBox()
        self.type_of_birth_combo.addItems([
            "SINGLE", "TWIN", "TRIPLET", "QUADRUPLET", "QUINTUPLET", 
            "SEXTUPLET", "SEPTUPLET", "OCTUPLET", "NONUPLET", "DECAPLET"
        ])
        self.type_of_birth_combo.setFixedWidth(100)
        self.type_of_birth_combo.setStyleSheet(combo_box_style)
        type_of_birth_container.addWidget(QLabel("Type of Birth:"))
        type_of_birth_container.addWidget(self.type_of_birth_combo)
        birth_info_layout.addLayout(type_of_birth_container)
        form_layout.addLayout(birth_info_layout)

        # Name of Mother and Nationality
        mother_info_layout = QHBoxLayout()
        mother_info_layout.setSpacing(10)

        mother_name_container = QVBoxLayout()
        self.mother_name_input = QLineEdit()
        self.mother_name_input.setPlaceholderText("Name of Mother")
        self.mother_name_input.setFixedWidth(450)
        mother_name_container.addWidget(QLabel("Name of Mother:"))
        mother_name_container.addWidget(self.mother_name_input)
        mother_info_layout.addLayout(mother_name_container)

        mother_nat_container = QVBoxLayout()
        self.mother_nationality_combo = QComboBox()
        self.mother_nationality_combo.setEditable(True)
        self.mother_nationality_combo.addItems([
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
        self.mother_nationality_combo.setFixedWidth(220)
        self.mother_nationality_combo.setStyleSheet(combo_box_style)
        mother_nat_container.addWidget(QLabel("Nationality of Mother:"))
        mother_nat_container.addWidget(self.mother_nationality_combo)
        mother_info_layout.addLayout(mother_nat_container)
        form_layout.addLayout(mother_info_layout)

        # Name of Father and Nationality
        father_info_layout = QHBoxLayout()
        father_info_layout.setSpacing(10)

        father_name_container = QVBoxLayout()
        self.father_name_input = QLineEdit()
        self.father_name_input.setPlaceholderText("Name of Father")
        self.father_name_input.setFixedWidth(450)
        father_name_container.addWidget(QLabel("Name of Father:"))
        father_name_container.addWidget(self.father_name_input)
        father_info_layout.addLayout(father_name_container)

        father_nat_container = QVBoxLayout()
        self.father_nationality_combo = QComboBox()
        self.father_nationality_combo.setEditable(True)
        self.father_nationality_combo.addItems([
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
        self.father_nationality_combo.setFixedWidth(220)
        self.father_nationality_combo.setStyleSheet(combo_box_style)
        father_nat_container.addWidget(QLabel("Nationality of Father:"))
        father_nat_container.addWidget(self.father_nationality_combo)
        father_info_layout.addLayout(father_nat_container)
        form_layout.addLayout(father_info_layout)

        # Place of Marriage and Date of Marriage
        marriage_info_layout = QHBoxLayout()
        marriage_info_layout.setSpacing(10)

        marriage_place_container = QVBoxLayout()
        self.marriage_place_input = QComboBox()
        self.marriage_place_input.setEditable(True)
        self.marriage_place_input.addItems([
            "NOT MARRIED",
            "FORGOTTEN",
            "DON'T KNOW",
            "NOT APPLICABLE"
        ])
        self.marriage_place_input.setFixedWidth(450)
        self.marriage_place_input.setStyleSheet(combo_box_style)
        self.marriage_place_input.currentTextChanged.connect(self.handle_marriage_place_change)
        marriage_place_container.addWidget(QLabel("Place of Marriage:"))
        marriage_place_container.addWidget(self.marriage_place_input)
        marriage_info_layout.addLayout(marriage_place_container)

        marriage_date_container = QVBoxLayout()
        self.date_of_marriage_input = QDateEdit()
        self.date_of_marriage_input.setCalendarPopup(True)
        self.date_of_marriage_input.setDate(QDate.currentDate())
        self.date_of_marriage_input.setEnabled(False)
        self.date_of_marriage_input.setFixedWidth(220)
        self.date_of_marriage_input.setStyleSheet(date_picker_style)
        marriage_date_container.addWidget(QLabel("Date of Marriage:"))
        marriage_date_container.addWidget(self.date_of_marriage_input)
        marriage_info_layout.addLayout(marriage_date_container)
        form_layout.addLayout(marriage_info_layout)

        # Attendant, Late Registration, Twin, and Date of Registration
        final_info_layout = QHBoxLayout()
        final_info_layout.setSpacing(10)

        attendant_container = QVBoxLayout()
        self.attendant_combo = QComboBox()
        self.attendant_combo.setEditable(True)
        self.attendant_combo.addItems([
            "PHYSICIAN",
            "MIDWIFE",
            "NURSE",
            "HILOT",
            "OTHERS",
            "NOT APPLICABLE",
            "DON'T KNOW"
        ])
        self.attendant_combo.setFixedWidth(220)
        self.attendant_combo.setStyleSheet(combo_box_style)
        attendant_container.addWidget(QLabel("Attendant:"))
        attendant_container.addWidget(self.attendant_combo)
        final_info_layout.addLayout(attendant_container)

        late_reg_container = QVBoxLayout()
        self.late_reg_combo = QComboBox()
        self.late_reg_combo.addItems(["NO", "YES"])
        self.late_reg_combo.setFixedWidth(150)
        self.late_reg_combo.setStyleSheet(combo_box_style)
        late_reg_container.addWidget(QLabel("Late Registration:"))
        late_reg_container.addWidget(self.late_reg_combo)
        final_info_layout.addLayout(late_reg_container)

        reg_date_container = QVBoxLayout()
        self.date_of_reg_input = QDateEdit()
        self.date_of_reg_input.setCalendarPopup(True)
        self.date_of_reg_input.setDate(QDate.currentDate())
        self.date_of_reg_input.setFixedWidth(150)
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

        # Add keyboard shortcut for save button (Ctrl+S)
        save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        save_shortcut.activated.connect(self.save_tags)

        delete_btn = QPushButton("Delete Tags")
        delete_btn.clicked.connect(self.delete_tags)
        delete_btn.setFixedWidth(130)
        button_layout.addWidget(delete_btn)

        save_btn.setStyleSheet(button_style)
        delete_btn.setStyleSheet(button_style)

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
                self.settings.setValue("birth/last_folder", folder_path)
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
                self.settings.setValue("birth/last_pdf", self.selected_pdf)
                self.last_page_no = self.page_no_input.text()
                self.last_book_no = self.book_no_input.text()
                self.last_reg_date = self.date_of_reg_input.date().toString("yyyy-MM-dd")
                self.last_place_of_birth = self.place_of_birth_combo.currentText()
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
                    name, date_of_birth, sex, page_no, book_no, reg_no, 
                    date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                    name_of_father, nationality_father, parents_marriage_date,
                    parents_marriage_place, attendant, type_of_birth, late_registration
                FROM birth_index 
                WHERE file_path = %s
            """, (file_path,))

            result = cursor.fetchone()

            if result:
                (name, date_of_birth, sex, page_no, book_no, reg_no, 
                 date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                 name_of_father, nationality_father, parents_marriage_date,
                 parents_marriage_place, attendant, type_of_birth, late_registration) = result

                # Set QLineEdit values
                self.page_no_input.setText(str(page_no) if page_no else "")
                self.book_no_input.setText(str(book_no) if book_no else "")
                self.reg_no_input.setText(reg_no if reg_no else "")
                self.name_input.setText(name if name else "")
                self.mother_name_input.setText(name_of_mother if name_of_mother else "")
                self.father_name_input.setText(name_of_father if name_of_father else "")

                # Set QComboBox values
                self.sex_combo.setCurrentText(sex if sex else "")
                self.place_of_birth_combo.setCurrentText(place_of_birth if place_of_birth else "")
                self.mother_nationality_combo.setCurrentText(nationality_mother if nationality_mother else "")
                self.father_nationality_combo.setCurrentText(nationality_father if nationality_father else "")
                self.attendant_combo.setCurrentText(attendant if attendant else "")
                # self.late_reg_combo.setCurrentText("Yes" if late_registration else "No")
                # self.twin_combo.setCurrentText("Yes" if twin else "No")
                # Force reset before setting
                self.late_reg_combo.setCurrentIndex(-1)  # This clears the selection
                self.late_reg_combo.setCurrentText("YES" if late_registration is True else "NO")


                # Handle type_of_birth
                if type_of_birth:
                    self.type_of_birth_combo.setCurrentText(type_of_birth)
                else:
                    self.type_of_birth_combo.setCurrentIndex(0)  # Set to "N/A"

                # Handle dates
                if date_of_birth:
                    self.date_of_birth_input.setDate(QDate.fromString(date_of_birth.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                else:
                    self.date_of_birth_input.setDate(QDate.currentDate())

                if date_of_reg:
                    self.date_of_reg_input.setDate(QDate.fromString(date_of_reg.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                else:
                    self.date_of_reg_input.setDate(QDate.currentDate())

                # Handle marriage place and date
                if parents_marriage_place:
                    self.marriage_place_input.setCurrentText(parents_marriage_place)
                else:
                    self.marriage_place_input.clearEditText()
                    self.marriage_place_input.setCurrentIndex(0)
                    self.marriage_place_input.setEditText(self.marriage_place_input.itemText(0))
                
                if parents_marriage_date:
                    self.date_of_marriage_input.setDate(QDate.fromString(parents_marriage_date.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                    self.date_of_marriage_input.setEnabled(True)
                else:
                    self.date_of_marriage_input.setEnabled(False)

                self.set_saved_cue(True)
            
            else:
                # Clear all fields
                self.page_no_input.setText(self.last_page_no)
                self.book_no_input.setText(self.last_book_no)
                self.reg_no_input.clear()
                self.name_input.clear()
                self.mother_name_input.clear()
                self.father_name_input.clear()
                
                self.sex_combo.setCurrentIndex(0)
                self.place_of_birth_combo.setCurrentText(self.last_place_of_birth)
                self.mother_nationality_combo.setCurrentIndex(0)
                self.father_nationality_combo.setCurrentIndex(0)
                self.attendant_combo.setCurrentIndex(0)
                self.late_reg_combo.setCurrentIndex(0)
                self.type_of_birth_combo.setCurrentIndex(0)
                
                self.date_of_reg_input.setDate(QDate.fromString(self.last_reg_date, "yyyy-MM-dd"))
                self.date_of_birth_input.setDate(QDate.currentDate())
                self.date_of_marriage_input.setDate(QDate.currentDate())
                self.date_of_marriage_input.setEnabled(False)
                
                self.set_saved_cue(False)
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
                name = self.name_input.text()
                date_of_birth = self.date_of_birth_input.date().toString("yyyy-MM-dd")
                sex = self.sex_combo.currentText()
                date_of_reg = self.date_of_reg_input.date().toString("yyyy-MM-dd")
                place_of_birth = self.place_of_birth_combo.currentText()
                name_of_mother = self.mother_name_input.text()
                nationality_mother = self.mother_nationality_combo.currentText()
                name_of_father = self.father_name_input.text() if self.father_name_input.text() != "" else None
                nationality_father = self.father_nationality_combo.currentText() if self.father_name_input.text() != "" else None
                type_of_birth = self.type_of_birth_combo.currentText()
                
                # Handle marriage date based on marriage place
                if self.marriage_place_input.currentText() in ["NOT MARRIED", "FORGOTTEN", "DON'T KNOW", "NOT APPLICABLE"]:
                    parents_marriage_date = None
                    parents_marriage_place = None
                else:
                    parents_marriage_date = self.date_of_marriage_input.date().toString("yyyy-MM-dd")
                    parents_marriage_place = self.marriage_place_input.currentText()

                attendant = self.attendant_combo.currentText()
                late_registration = self.late_reg_combo.currentText().strip().lower() == "yes"
                
                cursor.execute("""
                    INSERT INTO birth_index (
                        file_path, name, date_of_birth, sex, page_no, book_no, reg_no,
                        date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                        name_of_father, nationality_father, parents_marriage_date,
                        parents_marriage_place, attendant, type_of_birth, late_registration
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT(file_path) DO UPDATE SET
                        name = EXCLUDED.name,
                        date_of_birth = EXCLUDED.date_of_birth,
                        sex = EXCLUDED.sex,
                        page_no = EXCLUDED.page_no,
                        book_no = EXCLUDED.book_no,
                        reg_no = EXCLUDED.reg_no,
                        date_of_reg = EXCLUDED.date_of_reg,
                        place_of_birth = EXCLUDED.place_of_birth,
                        name_of_mother = EXCLUDED.name_of_mother,
                        nationality_mother = EXCLUDED.nationality_mother,
                        name_of_father = EXCLUDED.name_of_father,
                        nationality_father = EXCLUDED.nationality_father,
                        parents_marriage_date = EXCLUDED.parents_marriage_date,
                        parents_marriage_place = EXCLUDED.parents_marriage_place,
                        attendant = EXCLUDED.attendant,
                        late_registration = EXCLUDED.late_registration,
                        type_of_birth = EXCLUDED.type_of_birth
                """, (
                    self.selected_pdf, name, date_of_birth, sex, page_no, book_no, reg_no,
                    date_of_reg, place_of_birth, name_of_mother, nationality_mother,
                    name_of_father, nationality_father, parents_marriage_date,
                    parents_marriage_place, attendant, type_of_birth, late_registration
                ))

                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAGS_SAVED",
                    {
                        "file": self.selected_pdf,
                        "record_type": "Birth"
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

                self.set_saved_cue(True)
                
            except Exception as e:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAG_SAVE_ERROR",
                    {
                        "error": str(e),
                        "file": self.selected_pdf,
                        "record_type": "Birth"
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
            cursor.execute("DELETE FROM birth_index WHERE file_path = %s", (self.selected_pdf,))
            conn.commit()

            AuditLogger.log_action(
                conn,
                self.current_user,
                "TAGS_DELETED",
                {"file": self.selected_pdf, "table": "birth_index"}
            )
            conn.commit()

            # Clear all input fields after successful deletion
            self.page_no_input.clear()
            self.book_no_input.clear()
            self.reg_no_input.clear()
            self.name_input.clear()
            self.mother_name_input.clear()
            self.father_name_input.clear()
            
            self.sex_combo.setCurrentIndex(0)
            self.place_of_birth_combo.setCurrentIndex(0)
            self.mother_nationality_combo.setCurrentIndex(0)
            self.father_nationality_combo.setCurrentIndex(0)
            self.attendant_combo.setCurrentIndex(0)
            self.late_reg_combo.setCurrentIndex(0)
            self.type_of_birth_combo.setCurrentIndex(0)
            
            self.date_of_reg_input.setDate(QDate.currentDate())
            self.date_of_birth_input.setDate(QDate.currentDate())
            self.date_of_marriage_input.setDate(QDate.currentDate())
            self.date_of_marriage_input.setEnabled(False)
            
            self.set_saved_cue(False)

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
        return 'birth_index'
    
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
            last_folder = self.settings.value("birth/last_folder", type=str)
            last_pdf = self.settings.value("birth/last_pdf", type=str)
            if last_folder and os.path.isdir(last_folder):
                # keep for selection after load if file exists
                if last_pdf and os.path.isfile(last_pdf):
                    self.pending_select_pdf = last_pdf
                self.load_pdfs(last_folder)
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_OPENED",
                {"window": "BirthTaggingWindow"}
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
                {"window": "BirthTaggingWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()
            event.ignore()
            self.hide()

    def handle_marriage_place_change(self, value):
        """Handle changes in marriage place combo box."""
        null_triggers = ["NOT MARRIED", "FORGOTTEN", "DON'T KNOW", "NOT APPLICABLE"]

        if value in null_triggers:
            # Set to null date and disable
            self.date_of_marriage_input.setDate(QDate())  # Clears the date
            self.date_of_marriage_input.setSpecialValueText("")  # Optional: show blank
            self.date_of_marriage_input.setEnabled(False)
        else:
            # Re-enable and set to current date if empty
            self.date_of_marriage_input.setEnabled(True)
            if not self.date_of_marriage_input.date().isValid() or self.date_of_marriage_input.date() == QDate():
                self.date_of_marriage_input.setDate(QDate.currentDate())



    # def get_form_fields(self):
    #     """Return all form field widgets for styling updates."""
    #     return [
    #         # Line edits
    #         self.page_no_input, self.book_no_input, self.reg_no_input, self.name_input,
    #         self.mother_name_input, self.father_name_input,
    #         # Combo boxes
    #         self.sex_combo, self.place_of_birth_combo, self.mother_nationality_combo,
    #         self.father_nationality_combo, self.attendant_combo, self.late_reg_combo,
    #         self.type_of_birth_combo, self.marriage_place_input,
    #         # Dates
    #         self.date_of_birth_input, self.date_of_reg_input, self.date_of_marriage_input,
    #     ]

    def set_saved_cue(self, enabled):
        """Toggle green saved border on all fields."""
        # for widget in self.get_form_fields():
        #     widget.setProperty("saved", True if enabled else False)
        #     # Re-polish to apply dynamic property stylesheet
        #     widget.style().unpolish(widget)
        #     widget.style().polish(widget)
        #     widget.update()
        if hasattr(self, 'form_area') and self.form_area is not None:
            self.form_area.setProperty("saved", True if enabled else False)
            self.form_area.style().unpolish(self.form_area)
            self.form_area.style().polish(self.form_area)
            self.form_area.update()



