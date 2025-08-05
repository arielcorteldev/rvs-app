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
from PySide6.QtCore import Qt, QDate, QSize, QUrl
from PySide6.QtGui import QPixmap, QImage, QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from stylesheets import button_style, date_picker_style, combo_box_style, message_box_style
from pdfviewer import PDFViewer
from audit_logger import AuditLogger
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from db_config import POSTGRES_CONFIG


class DeathTaggingWindow(QWidget):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.current_user = username
        self.connection = None
        self.setWindowTitle("Death Records Tagging")
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
        """)

        self.default_directory = r"\\server\MCR\DEATH"
        self.selected_pdf = None
        self.last_page_no = None
        self.last_book_no = None

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

        # Name and Sex and Agge
        name_sex_age_layout = QHBoxLayout()
        name_sex_age_layout.setSpacing(10)

        name_container = QVBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        self.name_input.setFixedWidth(400)
        name_container.addWidget(QLabel("Name:"))
        name_container.addWidget(self.name_input)
        name_sex_age_layout.addLayout(name_container)

        sex_container = QVBoxLayout()
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(["MALE", "FEMALE"])
        self.sex_combo.setFixedWidth(200)
        self.sex_combo.setStyleSheet(combo_box_style)
        sex_container.addWidget(QLabel("Sex:"))
        sex_container.addWidget(self.sex_combo)
        name_sex_age_layout.addLayout(sex_container)
        
        age_container = QVBoxLayout()
        self.age_input = QLineEdit()
        self.age_input.setPlaceholderText("Age")
        self.age_input.setFixedWidth(70)
        age_container.addWidget(QLabel("Age:"))
        age_container.addWidget(self.age_input)
        name_sex_age_layout.addLayout(age_container)

        form_layout.addLayout(name_sex_age_layout)

        # Civil Status and Nationality
        cs_nat_layout = QHBoxLayout()
        cs_nat_layout.setSpacing(10)

        cs_container = QVBoxLayout()
        self.civil_status_combo = QComboBox()
        self.civil_status_combo.addItems(["SINGLE", "MARRIED", "WIDOW", "WIDOWER"])
        self.civil_status_combo.setFixedWidth(300)
        self.civil_status_combo.setStyleSheet(combo_box_style)
        cs_container.addWidget(QLabel("Civil Status:"))
        cs_container.addWidget(self.civil_status_combo)
        cs_nat_layout.addLayout(cs_container)

        nat_container = QVBoxLayout()
        self.nationality_combo = QComboBox()
        self.nationality_combo.setEditable(True)
        self.nationality_combo.addItems([
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
        self.nationality_combo.setFixedWidth(350)
        self.nationality_combo.setStyleSheet(combo_box_style)
        nat_container.addWidget(QLabel("Nationality:"))
        nat_container.addWidget(self.nationality_combo)
        cs_nat_layout.addLayout(nat_container)

        form_layout.addLayout(cs_nat_layout)

        # Place of Death and Date of Death
        death_info_layout = QHBoxLayout()
        death_info_layout.setSpacing(10)

        death_place_container = QVBoxLayout()
        self.death_place_input = QComboBox()
        self.death_place_input.setEditable(True)
        self.death_place_input.addItems([
            "SALVACION OPPUS YÑIGUEZ MEMORIAL PROVINCIAL HOSPITAL",
            "MAASIN MEDCITY HOSPITAL",
            "LIVINGHOPE HOSPITAL, INC.",
            "CM MATERNITY CLINIC",
        ])
        self.death_place_input.setFixedWidth(450)
        self.death_place_input.setStyleSheet(combo_box_style)
        death_place_container.addWidget(QLabel("Place of Death:"))
        death_place_container.addWidget(self.death_place_input)
        death_info_layout.addLayout(death_place_container)

        death_date_container = QVBoxLayout()
        self.date_of_death_input = QDateEdit()
        self.date_of_death_input.setCalendarPopup(True)
        self.date_of_death_input.setDate(QDate.currentDate())
        self.date_of_death_input.setFixedWidth(220)
        self.date_of_death_input.setStyleSheet(date_picker_style)
        death_date_container.addWidget(QLabel("Date of Death:"))
        death_date_container.addWidget(self.date_of_death_input)
        death_info_layout.addLayout(death_date_container)
        form_layout.addLayout(death_info_layout)

        # Cause of Death
        cod_layout = QHBoxLayout()
        cod_layout.setSpacing(10)

        cod_container = QVBoxLayout()
        self.cause_of_death_input = QLineEdit()
        self.cause_of_death_input.setPlaceholderText("Cause of Death")
        self.cause_of_death_input.setFixedWidth(650)
        cod_container.addWidget(QLabel("Cause of Death:"))
        cod_container.addWidget(self.cause_of_death_input)
        cod_layout.addLayout(cod_container)

        form_layout.addLayout(cod_layout)

        # Corpse Disposal, Late Registration, and Date of Registration
        final_info_layout = QHBoxLayout()
        final_info_layout.setSpacing(10)

        corpse_disposal_container = QVBoxLayout()
        self.corpse_disposal_combo = QComboBox()
        self.corpse_disposal_combo.setEditable(True)
        self.corpse_disposal_combo.addItems(["BURIAL", "CREMATION"])
        self.corpse_disposal_combo.setFixedWidth(270)
        self.corpse_disposal_combo.setStyleSheet(combo_box_style)
        corpse_disposal_container.addWidget(QLabel("Corpse Disposal:"))
        corpse_disposal_container.addWidget(self.corpse_disposal_combo)
        final_info_layout.addLayout(corpse_disposal_container)

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

    def load_pdfs(self, folder_path):
        """Loads PDFs from a folder and generates thumbnails."""
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
                self.last_page_no = self.page_no_input.text()
                self.last_book_no = self.book_no_input.text()
                self.last_reg_date = self.date_of_reg_input.date().toString("yyyy-MM-dd")
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
                    name, date_of_death, sex, page_no, book_no, reg_no, 
                    date_of_reg, age, civil_status, nationality,
                    place_of_death, cause_of_death,
                    corpse_disposal, late_registration
                FROM death_index 
                WHERE file_path = %s
            """, (file_path,))

            result = cursor.fetchone()

            if result:
                (name, date_of_death, sex, page_no, book_no, reg_no, 
                 date_of_reg, age, civil_status, nationality,
                 place_of_death, cause_of_death,
                 corpse_disposal, late_registration) = result

                # Set QLineEdit values
                self.page_no_input.setText(str(page_no) if page_no else "")
                self.book_no_input.setText(str(book_no) if book_no else "")
                self.reg_no_input.setText(reg_no if reg_no else "")
                self.name_input.setText(name if name else "")
                self.age_input.setText(str(age) if age else "")
                self.cause_of_death_input.setText(cause_of_death if cause_of_death else "")

                # Set QComboBox values
                self.sex_combo.setCurrentText(sex if sex else "")
                self.civil_status_combo.setCurrentText(civil_status if civil_status else "")
                self.nationality_combo.setCurrentText(nationality if nationality else "")
                self.death_place_input.setCurrentText(place_of_death if place_of_death else "")
                self.corpse_disposal_combo.setCurrentText(corpse_disposal if corpse_disposal else "")
                self.late_reg_combo.setCurrentText("Yes" if late_registration else "No")

                # Handle dates
                if date_of_death:
                    self.date_of_death_input.setDate(QDate.fromString(date_of_death.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                else:
                    self.date_of_death_input.setDate(QDate.currentDate())

                if date_of_reg:
                    self.date_of_reg_input.setDate(QDate.fromString(date_of_reg.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                else:
                    self.date_of_reg_input.setDate(QDate.currentDate())

            else:
                # Clear all fields
                self.page_no_input.setText(self.last_page_no)
                self.book_no_input.setText(self.last_book_no)
                self.reg_no_input.clear()
                self.name_input.clear()
                self.age_input.clear()
                self.cause_of_death_input.clear()
                
                self.sex_combo.setCurrentIndex(0)
                self.civil_status_combo.setCurrentIndex(0)
                self.nationality_combo.setCurrentIndex(0)
                self.death_place_input.setCurrentIndex(0)
                self.corpse_disposal_combo.setCurrentIndex(0)
                self.late_reg_combo.setCurrentIndex(0)
                
                self.date_of_reg_input.setDate(QDate.fromString(self.last_reg_date, "yyyy-MM-dd"))
                self.date_of_death_input.setDate(QDate.currentDate())
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
                age = self.age_input.text()
                cause_of_death = self.cause_of_death_input.text()
                date_of_death = self.date_of_death_input.date().toString("yyyy-MM-dd")
                sex = self.sex_combo.currentText()
                date_of_reg = self.date_of_reg_input.date().toString("yyyy-MM-dd")
                place_of_death = self.death_place_input.currentText()
                civil_status = self.civil_status_combo.currentText()
                nationality = self.nationality_combo.currentText()
                corpse_disposal = self.corpse_disposal_combo.currentText()
                late_registration = self.late_reg_combo.currentText() == "Yes"
                

                cursor.execute("""
                    INSERT INTO death_index (
                        file_path, name, date_of_death, sex, page_no, book_no, reg_no,
                        date_of_reg, age, civil_status, nationality,
                        place_of_death, cause_of_death, corpse_disposal, late_registration
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT(file_path) DO UPDATE SET
                        name = EXCLUDED.name,
                        date_of_death = EXCLUDED.date_of_death,
                        sex = EXCLUDED.sex,
                        page_no = EXCLUDED.page_no,
                        book_no = EXCLUDED.book_no,
                        reg_no = EXCLUDED.reg_no,
                        date_of_reg = EXCLUDED.date_of_reg,
                        age = EXCLUDED.age,
                        civil_status = EXCLUDED.civil_status,
                        nationality = EXCLUDED.nationality,
                        place_of_death = EXCLUDED.place_of_death,
                        cause_of_death = EXCLUDED.cause_of_death,
                        corpse_disposal = EXCLUDED.corpse_disposal,
                        late_registration = EXCLUDED.late_registration
                """, (
                    self.selected_pdf, name, date_of_death, sex, page_no, book_no, reg_no,
                    date_of_reg, age, civil_status, nationality,
                    place_of_death, cause_of_death, corpse_disposal, late_registration
                ))

                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "TAGS_SAVED",
                    {
                        "file": self.selected_pdf,
                        "record_type": "Death"
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
                        "record_type": "Death"
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
            cursor.execute("DELETE FROM death_index WHERE file_path = %s", (self.selected_pdf,))
            conn.commit()

            AuditLogger.log_action(
                conn,
                self.current_user,
                "TAGS_DELETED",
                {"file": self.selected_pdf, "table": "death_index"}
            )
            conn.commit()

            # Clear all input fields after successful deletion
            self.page_no_input.clear()
            self.book_no_input.clear()
            self.reg_no_input.clear()
            self.name_input.clear()
            self.age_input.clear()
            self.cause_of_death_input.clear()
            
            self.sex_combo.setCurrentIndex(0)
            self.civil_status_combo.setCurrentIndex(0)
            self.nationality_combo.setCurrentIndex(0)
            self.death_place_input.setCurrentIndex(0)
            self.corpse_disposal_combo.setCurrentIndex(0)
            self.late_reg_combo.setCurrentIndex(0)
            
            self.date_of_reg_input.setDate(QDate.currentDate())
            self.date_of_death_input.setDate(QDate.currentDate())
            
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
    #             cursor.execute("DELETE FROM death_index")
    #             conn.commit()

    #             AuditLogger.log_action(
    #                 conn,
    #                 self.current_user,
    #                 "ALL_TAGS_CLEARED",
    #                 {"tables": ["death_index"]}
    #             )
    #             conn.commit()
    #             QMessageBox.information(self, "Success", "All tags have been cleared from the database.")
    #     finally:
    #         if cursor:
    #             cursor.close()
    #         self.closeConnection()

    def get_table_name(self, file_path):
        """Determine the table name based on file path or other logic."""
        return 'death_index'
    
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
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_OPENED",
                {"window": "DeathTaggingWindow"}
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
                {"window": "DeathTaggingWindow"}
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
# 	window = DeathTaggingWindow()
# 	window.show()
# 	app.exec()