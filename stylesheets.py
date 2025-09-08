# stylesheet for buttons
button_style = """
            QPushButton {
                background-color: #ce305e;  
                color: #FFFFFF;
                border-radius: 2px;
                padding: 5px;                   
            }
            QPushButton:hover {
                background-color: #e0446a;  
                color: #FFFFFF;              
            }
            QPushButton:disabled {
                background-color: #ed7f97;
                color: #FFFFFF;
            }
        """
search_button_style = """
            QPushButton {
                background-color: #ce305e;  
                color: #FFFFFF;
                border-radius: 2px;
                padding: 4px;                   
            }
            QPushButton:hover { 
                background-color: #e0446a;  
                color: #FFFFFF;    
            }
        """
everify_button_style = """
            QPushButton {
                background-color: white;  
                color: white;
                border-radius: 10px;
                padding: 0;
                transition: all 0.3s ease;
            }
            QPushButton:hover { 
                background-color: #f0e9ff; /* soft violet flash */
                border: 2px solid #372aac;
            }
            QPushButton:pressed {
                background-color: #d1c4f7;
                border: 2px solid #372aac;
            }
        """

# submenu_button_style = """
#             QPushButton:hover {
#                 background-color: #f96db1;
#                 color: #FFFFFF;
#             }
#             QPushButton:pressed {
#                 background-color: #f96db1;
#                 color: #FFFFFF;
#             }
#             QPushButton:checked {
#                 background-color: #f96db1;
#                 color: #FFFFFF;
#             }
#         """

message_box_style = """
            QMessageBox {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #212121;
                background-color: #FFFFFF;
            }
            QPushButton {
                background-color: #ce305e;
                color: #FFFFFF;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #e0446a;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #e0446a;
                color: #FFFFFF;
            }
        """

table_style = """
            QTableWidget {
                border: 1px solid #D1D0D0;
                border-radius: 4px;
                background-color: #FFFFFF;
                alternate-background-color: #F5F5F5;
                gridline-color: #D1D0D0;
            }
            QTableWidget::item {
                padding: 5px;
                color: #212121;
            }
            QTableWidget::item:hover {
                background-color: #e0446a;
                color: #FFFFFF;
            }
            QTableWidget::item:selected {
                background-color: #ce305e;
                color: #FFFFFF;
            }
            QTableWidget::item:selected:hover {
                background-color: #e0446a;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                color: #212121;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """

date_picker_style = """
            QDateEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                padding: 4px;
                border-radius: 4px;
            }
            QDateEdit:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #F5F5F5;
                background-color: #FFFFFF;
                color: #212121;
                font-weight: bold;
            }
            QCalendarWidget QToolButton {
                background-color: #F5F5F5;
                color: #212121;
                font-weight: bold;
                border: none;
                padding: 5px;
                border-radius: 4px;
            }

            QCalendarWidget QMenu {
                background-color: #F5F5F5;
                color: #FFFFFF;
            }

            QCalendarWidget QSpinBox {
                color: #000;
            }

            QCalendarWidget QAbstractItemView:enabled {
                color: #000;         /* Normal day text */
                selection-background-color: #ce305e;
                selection-color: #FFFFFF;
            }

            QCalendarWidget QAbstractItemView:disabled {
                color: #aaaaaa;         /* Disabled (greyed-out) days */
            }
            QDateEdit:disabled {
                background-color: #F0F0F0;
                color: #9E9E9E;
                border: 1px solid #CCCCCC;
            }
        """

combo_box_style = """
            QComboBox {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                border-radius: 4px;
                padding: 5px;
            }
            QComboBox:focus {
                border: 1px solid #ce305e;
                background-color: #fef2f4;
            }
            QComboBox QLineEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: none;
                padding: 2px;
            }
            QComboBox QLineEdit:focus {
                background-color: #fef2f4;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #212121;
                border: 1px solid #D1D0D0;
                selection-background-color: #ce305e;
                selection-color: #FFFFFF;
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
        """