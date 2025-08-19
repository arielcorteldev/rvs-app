import psycopg2
import os
import pymupdf  
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QDate, QSize
from PySide6.QtGui import QPixmap, QImage, QIcon
from stylesheets import button_style, date_picker_style
from audit_logger import AuditLogger
from db_config import POSTGRES_CONFIG




class StatisticsWindow(QWidget):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.current_user = username
        self.connection = None
        self.setWindowTitle("Statistics Tool")
        self.setGeometry(200, 200, 800, 600)
        # self.showMaximized()

        self.setWindowIcon(QIcon("icons/application.png"))

        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
        """)

        self.init_ui()

    def create_connection(self):
        if self.connection is None:
            self.connection = psycopg2.connect(**POSTGRES_CONFIG)
            self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        return self.connection

    def closeConnection(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

    def init_ui(self):
        main_layout = QHBoxLayout()

        # Left-side layout for filters
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)

        # Record type selection dropdown
        self.record_type_dropdown = QComboBox(self)
        self.record_type_dropdown.addItems(["Live Birth", "Death", "Marriage"])
        self.record_type_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                color: #212121;
                border-radius: 4px;
                padding: 4px;
                border: 1px solid #D1D0D0;
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
        self.record_type_dropdown.currentIndexChanged.connect(self.update_keys_for_record_type)
        left_layout.addWidget(self.record_type_dropdown)

        # Key selection dropdown
        self.key_dropdown = QComboBox(self)
        self.key_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                color: #212121;
                border-radius: 4px;
                padding: 4px;
                border: 1px solid #D1D0D0;
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
        left_layout.addWidget(self.key_dropdown)

        # Date range label
        self.date_label = QLabel("Date of Birth Range:", self)
        left_layout.addWidget(self.date_label)

        self.start_date_input = QDateEdit(self)
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_input.setStyleSheet(date_picker_style)
        left_layout.addWidget(self.start_date_input)

        self.end_date_input = QDateEdit(self)
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDate(QDate.currentDate())
        self.end_date_input.setStyleSheet(date_picker_style)
        left_layout.addWidget(self.end_date_input)

        generate_btn = QPushButton("Generate Statistics", self)
        generate_btn.clicked.connect(self.generate_statistics)
        generate_btn.setStyleSheet(button_style)
        left_layout.addWidget(generate_btn)

        export_pdf_btn = QPushButton("Export Report as PDF", self)
        export_pdf_btn.clicked.connect(self.export_pdf_report)
        export_pdf_btn.setStyleSheet(button_style)
        left_layout.addWidget(export_pdf_btn)

        # Right-side layout for charts
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.canvas)

        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=2)
        self.setLayout(main_layout)

        self.update_keys_for_record_type()  # Set initial keys

    def update_keys_for_record_type(self):
        record_type = self.record_type_dropdown.currentText()
        self.key_dropdown.clear()
        if record_type == "Live Birth":
            self.key_dropdown.addItems([
                "Name", "Sex", "Place of Birth", "Name of Mother", "Name of Father", "Nationality of Mother", "Nationality of Father", "Attendant", "Late Registration", "Twin"
            ])
            self.date_label.setText("Date of Birth Range:")
        elif record_type == "Death":
            self.key_dropdown.addItems([
                "Name", "Sex", "Age", "Civil Status", "Nationality", "Place of Death", "Cause of Death", "Corpse Disposal", "Late Registration"
            ])
            self.date_label.setText("Date of Death Range:")
        elif record_type == "Marriage":
            self.key_dropdown.addItems([
                "Husband Name", "Husband Age", "Husband Civil Status", "Husband Nationality", "Wife Name", "Wife Age", "Wife Civil Status", "Wife Nationality", "Place of Marriage", "Ceremony Type", "Late Registration"
            ])
            self.date_label.setText("Date of Marriage Range:")

    def generate_statistics(self):
        record_type = self.record_type_dropdown.currentText()
        selected_key = self.key_dropdown.currentText().strip()
        start_date = self.start_date_input.date().toString("yyyy-MM-dd")
        end_date = self.end_date_input.date().toString("yyyy-MM-dd")

        conn = self.create_connection()
        try:
            if not selected_key:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "STATISTICS_GENERATION_FAILED",
                    {"reason": "no_key_selected"}
                )
                conn.commit()
                QMessageBox.warning(self, "Error", "Please select a valid key!")
                return

            AuditLogger.log_action(
                conn,
                self.current_user,
                "STATISTICS_GENERATION_STARTED",
                {
                    "record_type": record_type,
                    "key": selected_key,
                    "start_date": start_date,
                    "end_date": end_date
                }
            )
            conn.commit()

            cursor = conn.cursor()

            # Table and date field selection
            if record_type == "Live Birth":
                table = "birth_index"
                date_field = "date_of_birth"
            elif record_type == "Death":
                table = "death_index"
                date_field = "date_of_death"
            elif record_type == "Marriage":
                table = "marriage_index"
                date_field = "date_of_marriage"
            else:
                table = "birth_index"
                date_field = "date_of_birth"

            # Key to column mapping
            key_column_map = {
                # Live Birth
                "Name": "name",
                "Sex": "sex",
                "Place of Birth": "place_of_birth",
                "Name of Mother": "name_of_mother",
                "Name of Father": "name_of_father",
                "Nationality of Mother": "nationality_mother",
                "Nationality of Father": "nationality_father",
                "Attendant": "attendant",
                "Late Registration": "late_registration",
                "Twin": "twin",
                # Death
                "Age": "age_years",
                "Civil Status": "civil_status",
                "Nationality": "nationality",
                "Place of Death": "place_of_death",
                "Cause of Death": "cause_of_death",
                "Corpse Disposal": "corpse_disposal",
                # Marriage
                "Husband Name": "husband_name",
                "Husband Age": "husband_age",
                "Husband Civil Status": "husb_civil_status",
                "Husband Nationality": "husb_nationality",
                "Wife Name": "wife_name",
                "Wife Age": "wife_age",
                "Wife Civil Status": "wife_civil_status",
                "Wife Nationality": "wife_nationality",
                "Place of Marriage": "place_of_marriage",
                "Ceremony Type": "ceremony_type",
            }

            column = key_column_map.get(selected_key)
            if not column:
                QMessageBox.warning(self, "Error", f"No column mapping for key: {selected_key}")
                return

            try:
                cursor.execute(f"SELECT {column} FROM {table} WHERE {date_field} BETWEEN %s AND %s", (start_date, end_date))
                all_tags = cursor.fetchall()
                value_counts = self.process_statistics_data(all_tags, selected_key)

                if not value_counts:
                    AuditLogger.log_action(
                        conn,
                        self.current_user,
                        "STATISTICS_NO_DATA",
                        {
                            "record_type": record_type,
                            "key": selected_key,
                            "start_date": start_date,
                            "end_date": end_date
                        }
                    )
                    conn.commit()
                    QMessageBox.information(self, "No Data", f"No records found for '{selected_key}' in the selected date range.")
                else:
                    AuditLogger.log_action(
                        conn,
                        self.current_user,
                        "STATISTICS_GENERATED",
                        {
                            "record_type": record_type,
                            "key": selected_key,
                            "record_count": len(all_tags),
                            "unique_values": len(value_counts)
                        }
                    )
                    conn.commit()
                    self.plot_statistics(selected_key, value_counts)

            except psycopg2.Error as e:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "DATABASE_ERROR",
                    {
                        "operation": "generate_statistics",
                        "error": str(e),
                        "key": selected_key
                    }
                )
                conn.commit()
                QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")

        finally:
            self.closeConnection()

    def process_statistics_data(self, all_tags, selected_key):
        value_counts = {}
        for row in all_tags:
            if selected_key.lower() == "twin":
                value = "Twin" if row[0] == 1 else "Not Twin"
            elif selected_key.lower() == "legitimate":
                value = "Legitimate" if row[0] == 1 else "Illegitimate"
            elif selected_key.lower() == "religious":
                value = "Religious" if row[0] == 1 else "Not Religious"
            elif selected_key.lower() in ["age of mother", "age of husband", "age of wife"]:
                value = self.get_age_range(row[0])
            else:
                value = row[0]
            value_counts[value] = value_counts.get(value, 0) + 1
        return value_counts

    def get_age_range(self, age):
        if age < 18:
            return "Under 18"
        elif 18 <= age <= 25:
            return "18-25"
        elif 26 <= age <= 35:
            return "26-35"
        elif 36 <= age <= 45:
            return "36-45"
        else:
            return "Above 45"

    def plot_statistics(self, key, value_counts):
        self.ax.clear()
        if value_counts:
            values, counts = zip(*sorted(value_counts.items()))
            self.ax.bar(values, counts, color='blue')
            self.ax.set_title(f"{key} Distribution")
            self.ax.set_xlabel(f"{key} Values")
            self.ax.set_ylabel("Count")
            self.ax.set_xticks(range(len(values)))
            self.ax.set_xticklabels(values, rotation=45, ha='right')
        else:
            self.ax.text(0.5, 0.5, "No data available", ha='center', va='center', fontsize=12)
        self.canvas.draw()

    def export_pdf_report(self):
        record_type = self.record_type_dropdown.currentText()
        selected_key = self.key_dropdown.currentText().strip()
        start_date = self.start_date_input.date().toString("yyyy-MM-dd")
        end_date = self.end_date_input.date().toString("yyyy-MM-dd")

        conn = self.create_connection()
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "", "PDF Files (*.pdf)")
            if not file_path:
                return

            if not selected_key:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "PDF_EXPORT_FAILED",
                    {"reason": "no_key_selected"}
                )
                conn.commit()
                return

            # Table and date field selection
            if record_type == "Live Birth":
                table = "birth_index"
                date_field = "date_of_birth"
            elif record_type == "Death":
                table = "death_index"
                date_field = "date_of_death"
            elif record_type == "Marriage":
                table = "marriage_index"
                date_field = "date_of_marriage"
            else:
                table = "birth_index"
                date_field = "date_of_birth"

            # Key to column mapping (same as in generate_statistics)
            key_column_map = {
                "Name": "name",
                "Sex": "sex",
                "Place of Birth": "place_of_birth",
                "Name of Mother": "name_of_mother",
                "Name of Father": "name_of_father",
                "Nationality of Mother": "nationality_mother",
                "Nationality of Father": "nationality_father",
                "Attendant": "attendant",
                "Late Registration": "late_registration",
                "Twin": "twin",
                "Age": "age_years",
                "Civil Status": "civil_status",
                "Nationality": "nationality",
                "Place of Death": "place_of_death",
                "Cause of Death": "cause_of_death",
                "Corpse Disposal": "corpse_disposal",
                "Husband Name": "husband_name",
                "Husband Age": "husband_age",
                "Husband Civil Status": "husb_civil_status",
                "Husband Nationality": "husb_nationality",
                "Wife Name": "wife_name",
                "Wife Age": "wife_age",
                "Wife Civil Status": "wife_civil_status",
                "Wife Nationality": "wife_nationality",
                "Place of Marriage": "place_of_marriage",
                "Ceremony Type": "ceremony_type",
            }

            column = key_column_map.get(selected_key)
            if not column:
                QMessageBox.warning(self, "Error", f"No column mapping for key: {selected_key}")
                return

            try:
                cursor = conn.cursor()
                cursor.execute(f"SELECT {column} FROM {table} WHERE {date_field} BETWEEN %s AND %s", (start_date, end_date))
                all_tags = cursor.fetchall()
                value_counts = self.process_statistics_data(all_tags, selected_key)

                # Generate PDF with statistics
                with PdfPages(file_path) as pdf:
                    self.figure.clear()
                    self.ax = self.figure.add_subplot(111)

                    if value_counts:
                        values, counts = zip(*sorted(value_counts.items()))
                        self.ax.bar(values, counts, color='blue')
                        self.ax.set_title(f"{selected_key} Distribution")
                        self.ax.set_xlabel(f"{selected_key} Values")
                        self.ax.set_ylabel("Count")
                        self.ax.set_xticklabels(values, rotation=45, ha='right')
                    else:
                        self.ax.text(0.5, 0.5, "No data available", ha='center', va='center', fontsize=12)

                    pdf.savefig(self.figure)
                    self.figure.clear()

                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "PDF_EXPORT_SUCCESS",
                    {
                        "record_type": record_type,
                        "key": selected_key,
                        "file_path": file_path,
                        "start_date": start_date,
                        "end_date": end_date
                    }
                )
                conn.commit()

            except Exception as e:
                AuditLogger.log_action(
                    conn,
                    self.current_user,
                    "PDF_EXPORT_ERROR",
                    {
                        "error": str(e),
                        "record_type": record_type,
                        "key": selected_key,
                        "file_path": file_path
                    }
                )
                conn.commit()
                QMessageBox.critical(self, "Export Error", f"Failed to export PDF: {str(e)}")

        finally:
            self.closeConnection()

    def showEvent(self, event):
        super().showEvent(event)
        conn = self.create_connection()
        try:
            AuditLogger.log_action(
                conn,
                self.current_user,
                "WINDOW_OPENED",
                {"window": "StatisticsWindow"}
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
                {"window": "StatisticsWindow"}
            )
            conn.commit()
        finally:
            self.closeConnection()
            event.ignore()
            self.hide()