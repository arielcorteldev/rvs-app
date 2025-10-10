import os
import pymupdf  
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QDate, QSize, QTimer
from PySide6.QtGui import QPixmap, QImage, QIcon
from stylesheets import button_style

class PDFViewer(QScrollArea):
    """PDF Viewer with zoom support optimized for landscape files."""
    def __init__(self, parent=None):
        super().__init__(parent)      
        self.setWidgetResizable(True)
        self.pdf_widget = QWidget()
        self.pdf_layout = QVBoxLayout(self.pdf_widget)
        self.setWidget(self.pdf_widget)

        self.pdf_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
        """)

        self.zoom_factor = 1.0
        self.current_file = None
        self.target_width = 1000  # Target width for landscape pages
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.delayed_resize_render)
        self.last_width = self.width()
        self.manual_zoom = False  # Flag to track if zoom was set manually

    def load_pdf(self, file_path):
        """Loads and displays the PDF with optimized scaling for landscape."""
        self.current_file = file_path
        self.manual_zoom = False  # Reset manual zoom flag
        self.render_pdf()

    def render_pdf(self):
        """Renders the PDF with optimized scaling for landscape orientation."""
        try:
            if not self.current_file:
                return

            # Open the PDF file
            doc = pymupdf.open(self.current_file)
            self.clear_pdf()
            
            # Calculate optimal zoom factor for landscape pages (only if not manual zoom)
            if not self.manual_zoom and len(doc) > 0:
                first_page = doc[0]
                page_width = first_page.rect.width
                page_height = first_page.rect.height
                
                # Calculate zoom factor to fit width
                if page_width > page_height:  # Landscape
                    # Scale to fit width with some padding
                    available_width = self.target_width - 40  # 20px padding on each side
                    self.zoom_factor = available_width / page_width
                else:  # Portrait
                    # Scale to fit width but maintain aspect ratio
                    available_width = self.target_width - 40
                    self.zoom_factor = available_width / page_width

            dpi = 72 * self.zoom_factor

            for page_number in range(len(doc)):
                page = doc[page_number]
                matrix = pymupdf.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=matrix)
                image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(image)

                label = QLabel()
                label.setPixmap(pixmap)
                label.setAlignment(Qt.AlignCenter)
                label.setMinimumWidth(pixmap.width())
                label.setMinimumHeight(pixmap.height())
                self.pdf_layout.addWidget(label)
                
        except Exception as e:
            print(f"Error rendering PDF: {e}")
            label = QLabel("Unable to load PDF.")
            label.setAlignment(Qt.AlignCenter)
            self.pdf_layout.addWidget(label)

        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(0))

    def clear_pdf(self):
        """Clears the current PDF view."""
        while self.pdf_layout.count():
            widget = self.pdf_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()

    def set_zoom(self, zoom_factor):
        """Updates the zoom factor and re-renders the PDF."""
        self.zoom_factor = zoom_factor
        self.manual_zoom = True  # Mark as manual zoom
        self.render_pdf()  # Re-render the PDF with the updated zoom factor
        
    def resizeEvent(self, event):
        """Handle window resize to recalculate zoom factor with debouncing."""
        super().resizeEvent(event)
        
        # Only trigger resize if width actually changed significantly
        current_width = self.width()
        if abs(current_width - self.last_width) > 10:  # Only if width changed by more than 10px
            self.last_width = current_width
            self.target_width = current_width - 40  # Account for scrollbar and padding
            
            # Stop any existing timer and start a new one
            self.resize_timer.stop()
            self.resize_timer.start(200)  # 200ms delay to prevent rapid re-renders
            
    def delayed_resize_render(self):
        """Delayed render after resize to prevent shaking."""
        if self.current_file:
            self.manual_zoom = False  # Reset to auto-zoom on resize
            self.render_pdf()