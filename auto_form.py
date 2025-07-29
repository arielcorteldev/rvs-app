import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


# IMPORT PYSIDE6 MODULES
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog


from audit_logger import AuditLogger
from db_config import POSTGRES_CONFIG

from stylesheets import search_button_style, everify_button_style, button_style, message_box_style

# New Custom Form Preview Window
class FormPreviewWindow(QMainWindow):
    def __init__(self, pdf_path, record_data, form_type, connection=None, username=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Preview - {form_type} Form")
        self.setFixedSize(QSize(494, 700))  # Reduced from 850x1100 to 700x900
        self.pdf_path = pdf_path
        self.record_data = record_data
        self.form_type = form_type
        self.connection = connection
        self.username = username
        self.user_full_name = self._get_user_full_name()
        self.remarks_field = None  # Will hold the QTextEdit for remarks

        # Log form preview window opened
        if self.connection:
            try:
                AuditLogger.log_action(
                    self.connection,
                    self.username or "SYSTEM",  # Use username if available
                    "FORM_PREVIEW_OPENED",
                    {
                        "form_type": form_type,
                        "record_data": record_data
                    }
                )
                self.connection.commit()
            except Exception as e:
                print(f"Error logging form preview: {str(e)}")

        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Print and Save Buttons in a horizontal layout
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)
        self.print_button = QPushButton("Print Form")
        self.print_button.setStyleSheet(button_style)
        self.print_button.clicked.connect(self.print_form)
        button_row.addWidget(self.print_button)

        self.save_button = QPushButton("Save")
        self.save_button.setStyleSheet(button_style)
        self.save_button.clicked.connect(self.save_remarks)
        button_row.addWidget(self.save_button)

        self.layout.addLayout(button_row)

        self.form_area = QWidget()
        self.form_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.form_area_layout = QAbsoluteLayout(self.form_area)
        self.layout.addWidget(self.form_area)

        # Map form types to background image paths
        self.background_images = {
            "Birth": "forms_img/form_1a_background.png",
            "Death": "forms_img/form_2a_background.png",
            "Marriage": "forms_img/form_3a_background.png",
        }

        # Load background image
        background_image_path = self.background_images.get(self.form_type)
        if background_image_path and os.path.exists(background_image_path):
            self.form_area.setStyleSheet(f"""
                QWidget#form_area {{
                    background-image: url({background_image_path});
                    background-repeat: no-repeat;
                    background-position: center;
                    background-size: contain;
                }}
            """)
            self.form_area.setObjectName("form_area")
        else:
            # QMessageBox.warning(self, "Image Not Found", f"Background image not found for {self.form_type}: {background_image_path}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Image Not Found")
            box.setText(f"Background image not found for {self.form_type}: {background_image_path}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
            self.form_area.setStyleSheet("background-color: white;")

        self.populate_form_fields()

        

    def populate_form_fields(self):
        # Clear existing fields to prevent duplicates on subsequent calls (if any)
        for item in self.form_area_layout._items:
            item[0].deleteLater() # Delete the QWidget
        self.form_area_layout._items.clear()

        # Helper for adding QLineEdits. Adjust font and style as needed.
        font = QFont("Arial", 9) # Smaller font for form fields
        font_small = QFont("Arial", 8)
        font_big = QFont("Arial", 10)
        font_smallest = QFont("Arial", 6)
        style = "background-color: rgba(0,0,255,0.2); border: none; color: black; font-weight: bold" # Transparent background, no border
        text_edit_style = "background-color: rgba(0,0,255,0.2); border: none; color: black; font-weight: bold"

        # Load saved remarks from the database if available
        saved_remarks = ""
        if self.connection and self.pdf_path:
            table_map = {
                "Birth": "birth_index",
                "Death": "death_index",
                "Marriage": "marriage_index",
            }
            table = table_map.get(self.form_type)
            if table:
                try:
                    cursor = self.connection.cursor()
                    cursor.execute(f"SELECT remarks FROM {table} WHERE normalize_path(file_path) = %s", (self.pdf_path.replace('\\\\', '/').replace('\\', '/'),))
                    result = cursor.fetchone()
                    if result and result[0]:
                        saved_remarks = result[0]
                    cursor.close()
                except Exception as e:
                    print(f"Error loading saved remarks: {str(e)}")

        def adjust_text_edit_font(text_edit):
            text = text_edit.toPlainText()
            if not text:
                text_edit.setFont(font_small)
                return
                
            # Start with original font size
            current_size = font_small.pointSize()
            test_font = QFont(font_small)
            test_font.setPointSize(current_size)
            
            # Get text metrics
            metrics = QFontMetrics(test_font)
            text_width = metrics.horizontalAdvance(text)
            
            # If text is too wide, reduce font size until it fits
            while text_width > text_edit.width() - 10 and current_size > 6:  # 6pt minimum font size
                current_size -= 1
                test_font.setPointSize(current_size)
                metrics = QFontMetrics(test_font)
                text_width = metrics.horizontalAdvance(text)
            
            # Apply the adjusted font
            adjusted_font = QFont(font_small)
            adjusted_font.setPointSize(current_size)
            text_edit.setFont(adjusted_font)

        if self.form_type == "Birth":
            # Birth Form (FORM 1-A.pdf) - COORDINATES ARE ESTIMATES, ADJUST AS NEEDED
            self.add_field(self.record_data.get('page_no', ''), 182, 170, 40, 18, font_big, style)
            self.add_field(self.record_data.get('book_no', ''), 290, 170, 40, 18, font_big, style)
            
            self.add_field(self.record_data.get('reg_no', ''), 235, 196, 200, 18, font, style)
            
            # Format date_of_reg to "January 1 2025"
            date_of_reg = self.record_data.get('date_of_reg', '')
            if date_of_reg:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_of_reg, '%Y-%m-%d')
                    date_of_reg = date_obj.strftime('%B %d, %Y')
                except:
                    pass
            self.add_field(date_of_reg, 235, 213, 200, 18, font, style)

            self.add_field(self.record_data.get('name', ''), 235, 230, 200, 18, font, style)
            self.add_field(self.record_data.get('sex', ''), 235, 247, 200, 18, font, style)
            
            # Format date_of_birth to "January 1 2025"
            date_of_birth = self.record_data.get('date_of_birth', '')
            if date_of_birth:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_of_birth, '%Y-%m-%d')
                    date_of_birth = date_obj.strftime('%B %d, %Y')
                except:
                    pass
            self.add_field(date_of_birth, 235, 264, 200, 18, font, style)
            
            # Handle place of birth abbreviations
            place_of_birth = self.record_data.get('place_of_birth', '')
            if place_of_birth == 'SALVACION OPPUS YÑIGUEZ MEMORIAL PROVINCIAL HOSPITAL':
                place_of_birth = 'SOYMPH, Maasin City, So. Leyte'
            elif place_of_birth == 'MAASIN MEDCITY HOSPITAL':
                place_of_birth = 'MMCH, Maasin City, So. Leyte'
            elif place_of_birth == 'LIVINGHOPE HOSPITAL, INC.':
                place_of_birth = 'LHH, Maasin City, So. Leyte'
            self.add_field(place_of_birth, 235, 281, 200, 18, font, style)

            self.add_field(self.record_data.get('name_of_mother', ''), 235, 296, 200, 18, font, style)
            self.add_field(self.record_data.get('nationality_mother', ''), 235, 312, 200, 18, font, style)
            self.add_field(self.record_data.get('name_of_father', ''), 235, 329, 200, 18, font, style)
            self.add_field(self.record_data.get('nationality_father', ''), 235, 346, 200, 18, font, style)
            
            # Format parents_marriage_date to "January 1 2025"
            parents_marriage_date = self.record_data.get('parents_marriage_date', '')
            if parents_marriage_date:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(parents_marriage_date, '%Y-%m-%d')
                    parents_marriage_date = date_obj.strftime('%B %d, %Y')
                except:
                    pass
            self.add_field(parents_marriage_date, 235, 362, 200, 18, font, style)

            self.add_field(self.record_data.get('parents_marriage_place', ''), 235, 378, 200, 18, font, style)

            # Issued to and Date (current date)
            self.add_field(self.record_data.get('name', ''), 253, 400, 160, 18, font, style)
            from datetime import date
            self.add_field(date.today().strftime('%B %d, %Y'), 347, 94, 100, 18, font_small, style)

            # New User Input Fields for Form 1-A (Estimated Coordinates)
            self.add_field(self.user_full_name or '', 115, 550, 160, 18, font_small, style) # Verifier Name
            self.add_field('', 115, 561, 160, 18, font_smallest, style) # Verifier Position
            self.add_field('', 110, 582, 70, 18, font_smallest, style) # Amount Paid
            self.add_field('', 110, 595, 70, 18, font_smallest, style) # O.R. Number
            self.add_field(date.today().strftime('%m/%d/%Y'), 110, 606, 70, 18, font_smallest, style) # Date Paid
            self.add_field('', 280, 560, 170, 18, font_small, style) # OIC Field 1
            self.add_field('', 305, 588, 125, 18, font_small, style) # OIC Field 2
            self.add_field('', 305, 603, 125, 18, font_smallest, style) # OIC Field 3
            self.add_field('', 275, 618, 190, 18, font_smallest, style) # OIC Field 4
            
            # Add Remarks field for Birth form
            self.remarks_field = QTextEdit(self.form_area)
            self.remarks_field.setFont(font_small)
            self.remarks_field.setStyleSheet(text_edit_style)
            self.remarks_field.textChanged.connect(lambda: adjust_text_edit_font(self.remarks_field))
            self.remarks_field.setPlainText(saved_remarks)
            self.form_area_layout.addWidget(self.remarks_field, 110, 435, 355, 90)

        elif self.form_type == "Death":
            # Death Form (FORM 2-A.pdf) - COORDINATES ARE ESTIMATES, ADJUST AS NEEDED
            self.add_field(self.record_data.get('page_no', ''), 190, 180, 40, 18, font_big, style)
            self.add_field(self.record_data.get('book_no', ''), 300, 180, 40, 18, font_big, style)

            self.add_field(self.record_data.get('reg_no', ''), 243, 210, 200, 18, font, style)
            
            # Format date_of_reg to "January 1 2025"
            date_of_reg = self.record_data.get('date_of_reg', '')
            if date_of_reg:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_of_reg, '%Y-%m-%d')
                    date_of_reg = date_obj.strftime('%B %d, %Y')
                except:
                    pass
            self.add_field(date_of_reg, 243, 227, 200, 18, font, style)

            self.add_field(self.record_data.get('name', ''), 243, 243, 200, 18, font, style)
            self.add_field(self.record_data.get('sex', ''), 243, 260, 200, 18, font, style)
            self.add_field(self.record_data.get('age', ''), 243, 277, 200, 18, font, style)
            self.add_field(self.record_data.get('civil_status', ''), 243, 293, 200, 18, font, style)
            self.add_field(self.record_data.get('nationality', ''), 243, 309, 200, 18, font, style)
            
            # Format date_of_reg to "January 1 2025"
            date_of_death = self.record_data.get('date_of_death', '')
            if date_of_death:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_of_death, '%Y-%m-%d')
                    date_of_death = date_obj.strftime('%B %d, %Y')
                except:
                    pass
            self.add_field(date_of_death, 243, 325, 200, 18, font, style)

            self.add_field(self.record_data.get('place_of_death', ''), 243, 342, 200, 18, font, style)
            
            # Replace QLineEdit with QTextEdit for cause of death
            cause_of_death = QTextEdit(self.form_area)
            cause_of_death.setFont(font)
            cause_of_death.setStyleSheet(text_edit_style)
            cause_of_death.setPlaceholderText("")
            cause_of_death.setFixedHeight(36)  # Height for 2 lines
            cause_of_death.textChanged.connect(lambda: adjust_text_edit_font(cause_of_death))
            cause_of_death.setText(self.record_data.get('cause_of_death', ''))
            self.form_area_layout.addWidget(cause_of_death, 243, 360, 200, 38)

            # Issued to and Date (current date)
            self.add_field(self.record_data.get('name', ''), 265, 403, 160, 18, font, style)
            from datetime import date
            self.add_field(date.today().strftime('%B %d, %Y'), 355, 101, 100, 18, font_small, style)

            # New User Input Fields for Form 2-A (Estimated Coordinates)
            self.add_field(self.user_full_name or '', 115, 539, 160, 18, font_small, style) # Verifier Name
            self.add_field('', 115, 550, 160, 18, font_smallest, style) # Verifier Position
            self.add_field('', 110, 569, 70, 18, font_smallest, style) # Amount Paid
            self.add_field('', 110, 579, 70, 18, font_smallest, style) # O.R. Number
            self.add_field(date.today().strftime('%m/%d/%Y'), 110, 588, 70, 18, font_smallest, style) # Date Paid
            self.add_field('', 280, 540, 170, 18, font_small, style) # OIC Field 1
            self.add_field('', 305, 568, 125, 18, font_small, style) # OIC Field 2
            self.add_field('', 305, 583, 125, 18, font_smallest, style) # OIC Field 3
            self.add_field('', 275, 598, 190, 18, font_smallest, style) # OIC Field 4

            # Add Remarks field for Death form
            self.remarks_field = QTextEdit(self.form_area)
            self.remarks_field.setFont(font_small)
            self.remarks_field.setStyleSheet(text_edit_style)
            self.remarks_field.textChanged.connect(lambda: adjust_text_edit_font(self.remarks_field))
            self.remarks_field.setPlainText(saved_remarks)
            self.form_area_layout.addWidget(self.remarks_field, 107, 438, 355, 60)

        elif self.form_type == "Marriage":
            # Marriage Form (FORM 3-A.pdf) - COORDINATES ARE ESTIMATES, ADJUST AS NEEDED
            self.add_field(self.record_data.get('page_no', ''), 195, 170, 40, 18, font_big, style)
            self.add_field(self.record_data.get('book_no', ''), 298, 170, 40, 18, font_big, style)
            
            # Husband's Details
            self.add_field(self.record_data.get('husband_name', ''), 148, 225, 145, 18, font, style)
            self.add_field(self.record_data.get('husband_age', ''), 148, 242, 145, 18, font, style)
            self.add_field(self.record_data.get('husb_nationality', ''), 148, 259, 145, 18, font, style)
            self.add_field(self.record_data.get('husb_civil_status', ''), 148, 276, 145, 18, font, style)
            self.add_field(self.record_data.get('husb_mother', ''), 148, 294, 145, 18, font, style)
            self.add_field(self.record_data.get('husb_father', ''), 148, 310, 145, 18, font, style)

            # Wife's Details
            self.add_field(self.record_data.get('wife_name', ''), 295, 225, 145, 18, font, style)
            self.add_field(self.record_data.get('wife_age', ''), 295, 242, 145, 18, font, style)
            self.add_field(self.record_data.get('wife_nationality', ''), 295, 259, 145, 18, font, style)
            self.add_field(self.record_data.get('wife_civil_status', ''), 295, 276, 145, 18, font, style)
            self.add_field(self.record_data.get('wife_mother', ''), 295, 294, 145, 18, font, style)
            self.add_field(self.record_data.get('wife_father', ''), 295, 310, 145, 18, font, style)

            # Common Details
            self.add_field(self.record_data.get('reg_no', ''), 148, 326, 300, 18, font, style)
            # Format date_of_reg to "January 1 2025"
            date_of_reg = self.record_data.get('date_of_reg', '')
            if date_of_reg:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_of_reg, '%Y-%m-%d')
                    date_of_reg = date_obj.strftime('%B %d, %Y')
                except:
                    pass
            self.add_field(date_of_reg, 148, 342, 300, 18, font, style)
            
            # Format date_of_marriage to "January 1 2025"
            date_of_marriage = self.record_data.get('date_of_marriage', '')
            if date_of_marriage:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_of_marriage, '%Y-%m-%d')
                    date_of_marriage = date_obj.strftime('%B %d, %Y')
                except:
                    pass
            self.add_field(date_of_marriage, 148, 358, 300, 18, font, style)
            
            self.add_field(self.record_data.get('place_of_marriage', ''), 148, 374, 300, 18, font, style)

            # Issued to and Date (current date)
            self.add_field(self.record_data.get('husband_name', ''), 245, 398, 160, 18, font, style)
            from datetime import date
            self.add_field(date.today().strftime('%B %d, %Y'), 353, 95, 100, 18, font_small, style)

            # New User Input Fields for Form 2-A (Estimated Coordinates)
            self.add_field(self.user_full_name or '', 105, 545, 160, 18, font_small, style) # Verifier Name
            self.add_field('', 105, 555, 160, 18, font_smallest, style) # Verifier Position

            self.add_field('', 95, 574, 70, 18, font_smallest, style) # Amount Paid
            self.add_field('', 95, 583, 70, 18, font_smallest, style) # O.R. Number
            self.add_field(date.today().strftime('%m/%d/%Y'), 95, 593, 70, 18, font_smallest, style) # Date Paid

            self.add_field('', 280, 540, 170, 18, font_small, style) # OIC Field 1
            self.add_field('', 305, 568, 125, 18, font_small, style) # OIC Field 2
            self.add_field('', 305, 583, 125, 18, font_smallest, style) # OIC Field 3
            self.add_field('', 275, 598, 190, 18, font_smallest, style) # OIC Field 4

            # Add Remarks field for Marriage form
            self.remarks_field = QTextEdit(self.form_area)
            self.remarks_field.setFont(font_small)
            self.remarks_field.setStyleSheet(text_edit_style)
            self.remarks_field.textChanged.connect(lambda: adjust_text_edit_font(self.remarks_field))
            self.remarks_field.setPlainText(saved_remarks)
            self.form_area_layout.addWidget(self.remarks_field, 95, 430, 365, 70)

    def add_field(self, value_text, x, y, width, height, font, style):
        line_edit = QLineEdit(value_text, self.form_area)
        line_edit.setFont(font)
        line_edit.setStyleSheet(style)
        
        
        def adjust_font_size():
            text = line_edit.text()
            if not text:
                line_edit.setFont(font)
                return
                
            # Start with original font size
            current_size = font.pointSize()
            test_font = QFont(font)
            test_font.setPointSize(current_size)
            
            # Get text metrics
            metrics = QFontMetrics(test_font)
            text_width = metrics.horizontalAdvance(text)
            
            # If text is too wide, reduce font size until it fits
            while text_width > line_edit.width() - 10 and current_size > 6:  # 8pt minimum font size
                current_size -= 1
                test_font.setPointSize(current_size)
                metrics = QFontMetrics(test_font)
                text_width = metrics.horizontalAdvance(text)
            
            # Apply the adjusted font
            adjusted_font = QFont(font)
            adjusted_font.setPointSize(current_size)
            line_edit.setFont(adjusted_font)
        
        # Connect the textChanged signal to our adjust_font_size function
        line_edit.textChanged.connect(adjust_font_size)
        
        # Initial font size adjustment
        adjust_font_size()
        
        self.form_area_layout.addWidget(line_edit, x, y, width, height)

    def print_form(self):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize.A4)  # Set to A4 size
        print_dialog = QPrintDialog(printer, self)
        if print_dialog.exec() == QPrintDialog.Accepted:
            try:
                # Log print action
                if self.connection:
                    try:
                        AuditLogger.log_action(
                            self.connection,
                            "SYSTEM",  # Default to SYSTEM if no user context
                            "FORM_PRINTED",
                            {
                                "form_type": self.form_type,
                                "record_data": self.record_data
                            }
                        )
                        self.connection.commit()
                    except Exception as e:
                        print(f"Error logging form print: {str(e)}")

                # Store original styles
                original_form_style = self.form_area.styleSheet()
                original_field_styles = {}
                
                # Remove background image and field backgrounds
                self.form_area.setStyleSheet("background-color: white;")
                
                # Remove backgrounds from all fields
                for item in self.form_area_layout._items:
                    widget = item[0]
                    if isinstance(widget, (QLineEdit, QTextEdit)):
                        original_field_styles[widget] = widget.styleSheet()
                        widget.setStyleSheet("background-color: transparent; border: none; color: black; font-weight: bold")
                
                # Create a painter for the printer
                painter = QPainter()
                painter.begin(printer)
                
                # Get the page rect
                page_rect = printer.pageRect(QPrinter.DevicePixel)
                
                # Calculate the scale to fit the form to the page while maintaining aspect ratio
                form_scale = min(
                    page_rect.width() / self.form_area.width(),
                    page_rect.height() / self.form_area.height()
                )
                
                # Center the form on the page
                x_offset = (page_rect.width() - (self.form_area.width() * form_scale)) / 2
                y_offset = (page_rect.height() - (self.form_area.height() * form_scale)) / 2
                
                # Apply the transformation
                painter.translate(x_offset, y_offset)
                painter.scale(form_scale, form_scale)
                
                # Render the form
                self.form_area.render(painter, QPoint(0, 0))
                
                # End painting
                painter.end()
                
                # Restore original styles
                self.form_area.setStyleSheet(original_form_style)
                for widget, style in original_field_styles.items():
                    widget.setStyleSheet(style)
                
                # QMessageBox.information(self, "Print Status", "Form sent to printer.")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Information)
                box.setWindowTitle("Print Status")
                box.setText("Form sent to printer")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
            except Exception as e:
                # Restore original styles even if there's an error
                self.form_area.setStyleSheet(original_form_style)
                for widget, style in original_field_styles.items():
                    widget.setStyleSheet(style)
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Critical)
                box.setWindowTitle("Print Error")
                box.setText(f"An error occurred while printing: {str(e)}")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()

    def closeEvent(self, event):
        """Handle window close event"""
        if self.connection:
            try:
                AuditLogger.log_action(
                    self.connection,
                    "SYSTEM",  # Default to SYSTEM if no user context
                    "FORM_PREVIEW_CLOSED",
                    {
                        "form_type": self.form_type,
                        "record_data": self.record_data
                    }
                )
                self.connection.commit()
            except Exception as e:
                print(f"Error logging form preview close: {str(e)}")
        event.accept()

    def _get_user_full_name(self):
        """Get the user's full name from the database by concatenating firstname and lastname"""
        if not self.connection or not self.username:
            return ""
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT firstname, lastname 
                FROM users_list 
                WHERE username = %s
            """, (self.username,))
            result = cursor.fetchone()
            cursor.close()
            if result:
                firstname, lastname = result
                return f"{firstname} {lastname}".strip().upper()
            return ""
        except Exception as e:
            print(f"Error fetching user full name: {str(e)}")
            return ""

    def save_remarks(self):
        """Save the remarks to the appropriate index table based on form type."""
        if self.connection.closed:
            # Reconnect using your db config
            import psycopg2
            self.connection = psycopg2.connect(**POSTGRES_CONFIG)
        if not self.connection:
            # QMessageBox.critical(self, "Database Error", "No database connection available.")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Database Error")
            box.setText("No database connection available.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
            return
        if not self.remarks_field:
            # QMessageBox.critical(self, "Error", "Remarks field not found.")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText("Remarks field not found.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
            return
        remarks_text = self.remarks_field.toPlainText()
        table_map = {
            "Birth": "birth_index",
            "Death": "death_index",
            "Marriage": "marriage_index",
        }
        table = table_map.get(self.form_type)
        if not table:
            # QMessageBox.critical(self, "Error", f"Unknown form type: {self.form_type}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Error")
            box.setText(f"Unknown form type: {self.form_type}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
            return
        try:
            cursor = self.connection.cursor()
            # Check if the row exists for the given file_path
            cursor.execute(f"SELECT 1 FROM {table} WHERE normalize_path(file_path) = %s", (self.pdf_path.replace('\\\\', '/').replace('\\', '/'),))
            if not cursor.fetchone():
                # QMessageBox.critical(self, "Error", f"No record found for file_path:\n{self.pdf_path}\nRemarks not saved.")
                box = QMessageBox(self)
                box.setIcon(QMessageBox.Critical)
                box.setWindowTitle("Error")
                box.setText(f"No record found for file_path:\n{self.pdf_path}\nRemarks not saved.")
                box.setStandardButtons(QMessageBox.Ok)
                box.setStyleSheet(message_box_style)
                box.exec()
                cursor.close()
                return
            cursor.execute(f"""
                UPDATE {table}
                SET remarks = %s
                WHERE normalize_path(file_path) = %s
            """, (remarks_text, self.pdf_path.replace('\\\\', '/').replace('\\', '/')))
            self.connection.commit()
            cursor.close()
            # QMessageBox.information(self, "Success", "Form saved successfully.")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Success")
            box.setText("Form saved successfully.")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()
        except Exception as e:
            # QMessageBox.critical(self, "Database Error", f"Failed to save remarks: {str(e)}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Database Error")
            box.setText(f"Failed to save remarks: {str(e)}")
            box.setStandardButtons(QMessageBox.Ok)
            box.setStyleSheet(message_box_style)
            box.exec()

    def normalize_path(path):
        return path.replace('\\\\', '/').replace('\\', '/')

# A custom layout manager for absolute positioning. This is a common pattern for overlays.
class QAbsoluteLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = [] # Stores (widget, QRect) tuples

    def __del__(self):
        while self._items:
            item = self._items.pop()
            if item[0].parent() == self.parent():
                item[0].setParent(None) # Detach widget from layout parent

    def addItem(self, item):
        # This absolute layout is designed for addWidget, not generic QLayoutItems.
        # If other QLayoutItem types were supported, their geometry would need management here.
        # For now, we will not support adding generic QLayoutItem directly via addItem for simplicity.
        raise NotImplementedError("This layout only supports adding widgets via addWidget.")

    def addWidget(self, widget, x, y, width=None, height=None):
        target_width = width if width is not None else widget.sizeHint().width()
        target_height = height if height is not None else widget.sizeHint().height()
        geometry = QRect(x, y, target_width, target_height)
        self._items.append((widget, geometry))
        widget.setParent(self.parent()) # Ensure the widget has the correct parent
        widget.setGeometry(geometry) # Set initial geometry

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        # For a custom layout, you might wrap the widget in a QWidgetItem if needed.
        # For this absolute layout, direct access to widget and geometry is typical.
        if 0 <= index < len(self._items):
            return QWidgetItem(self._items[index][0]) # Return QWidgetItem wrapping the widget
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            widget, _ = self._items.pop(index)
            if widget.parent() == self.parent():
                widget.setParent(None) # Detach widget from parent when taken
            return QWidgetItem(widget) # Return QWidgetItem wrapping the widget
        return None

    def setGeometry(self, rect):
        # This method is called when the layout itself changes size or position.
        # We need to reposition our widgets relative to the new layout origin.
        # The stored geometries are relative to the layout's top-left (0,0).
        for widget, original_geometry in self._items:
            # New position is original_geometry.topLeft() + rect.topLeft()
            new_pos = original_geometry.topLeft() + rect.topLeft()
            widget.setGeometry(new_pos.x(), new_pos.y(), original_geometry.width(), original_geometry.height())

    def sizeHint(self):
        # Return the minimum size required by the layout based on its children.
        if not self._items:
            return QSize(0, 0)
        
        max_x = 0
        max_y = 0
        for _, geometry in self._items:
            max_x = max(max_x, geometry.right())
            max_y = max(max_y, geometry.bottom())
        return QSize(max_x, max_y)

    def minimumSize(self):
        return self.sizeHint()