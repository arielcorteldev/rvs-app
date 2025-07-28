# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'searchdeathwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QHBoxLayout,
    QLabel, QLayout, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_SearchDeathWindow(object):
    def setupUi(self, SearchDeathWindow):
        if not SearchDeathWindow.objectName():
            SearchDeathWindow.setObjectName(u"SearchDeathWindow")
        SearchDeathWindow.resize(800, 600)
        icon = QIcon()
        icon.addFile(u"icons/magnifier.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        SearchDeathWindow.setWindowIcon(icon)
        self.centralwidget = QWidget(SearchDeathWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.search_by_comboBox = QComboBox(self.centralwidget)
        self.search_by_comboBox.setObjectName(u"search_by_comboBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.search_by_comboBox.sizePolicy().hasHeightForWidth())
        self.search_by_comboBox.setSizePolicy(sizePolicy)
        self.search_by_comboBox.setMaximumSize(QSize(500, 16777215))

        self.horizontalLayout.addWidget(self.search_by_comboBox)

        self.search_textEdit = QLineEdit(self.centralwidget)
        self.search_textEdit.setObjectName(u"search_textEdit")
        sizePolicy.setHeightForWidth(self.search_textEdit.sizePolicy().hasHeightForWidth())
        self.search_textEdit.setSizePolicy(sizePolicy)
        self.search_textEdit.setMinimumSize(QSize(300, 0))
        self.search_textEdit.setMaximumSize(QSize(2000, 16777215))

        self.horizontalLayout.addWidget(self.search_textEdit)

        self.search_button = QPushButton(self.centralwidget)
        self.search_button.setObjectName(u"search_button")
        icon1 = QIcon()
        icon1.addFile(u"icons/player.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.search_button.setIcon(icon1)

        self.horizontalLayout.addWidget(self.search_button)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 1, 1, 2)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")

        self.auto_form = QPushButton(self.centralwidget)
        self.auto_form.setObjectName(u"auto_form")
        icon7 = QIcon()
        icon7.addFile(u"icons/auto.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.auto_form.setIcon(icon7)

        self.verticalLayout.addWidget(self.auto_form)
        
        self.create_form = QPushButton(self.centralwidget)
        self.create_form.setObjectName(u"create_form")
        icon2 = QIcon()
        icon2.addFile(u"icons/add.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.create_form.setIcon(icon2)

        self.verticalLayout.addWidget(self.create_form)

        # self.docstamp1 = QPushButton(self.centralwidget)
        # self.docstamp1.setObjectName(u"docstamp1")
        # icon3 = QIcon()
        # icon3.addFile(u"icons/stamp.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        # self.docstamp1.setIcon(icon3)

        # self.verticalLayout.addWidget(self.docstamp1)

        self.no_record = QPushButton(self.centralwidget)
        self.no_record.setObjectName(u"no_record")
        icon4 = QIcon()
        icon4.addFile(u"icons/norecord.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.no_record.setIcon(icon4)

        self.verticalLayout.addWidget(self.no_record)

        self.destroyed = QPushButton(self.centralwidget)
        self.destroyed.setObjectName(u"destroyed")
        icon5 = QIcon()
        icon5.addFile(u"icons/destroyed.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.destroyed.setIcon(icon5)

        self.verticalLayout.addWidget(self.destroyed)

        # self.docstamp2 = QPushButton(self.centralwidget)
        # self.docstamp2.setObjectName(u"docstamp2")
        # icon6 = QIcon()
        # icon6.addFile(u"icons/stamp2.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        # self.docstamp2.setIcon(icon6)

        # self.verticalLayout.addWidget(self.docstamp2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.horizontalLayout_2.addLayout(self.verticalLayout)

        self.results_list = QListWidget(self.centralwidget)
        self.results_list.setObjectName(u"results_list")

        self.horizontalLayout_2.addWidget(self.results_list)


        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 4)

        self.status_label = QLabel(self.centralwidget)
        self.status_label.setObjectName(u"status_label")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.status_label.sizePolicy().hasHeightForWidth())
        self.status_label.setSizePolicy(sizePolicy1)
        self.status_label.setMaximumSize(QSize(400, 16777215))
        self.status_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.status_label, 2, 3, 1, 1)

        self.regyear_textEdit = QLineEdit(self.centralwidget)
        self.regyear_textEdit.setObjectName(u"regyear_textEdit")
        sizePolicy.setHeightForWidth(self.regyear_textEdit.sizePolicy().hasHeightForWidth())
        self.regyear_textEdit.setSizePolicy(sizePolicy)
        self.regyear_textEdit.setMinimumSize(QSize(150, 0))
        self.regyear_textEdit.setMaximumSize(QSize(700, 16777215))

        self.gridLayout.addWidget(self.regyear_textEdit, 0, 0, 1, 1)

        self.everify_button = QPushButton(self.centralwidget)
        self.everify_button.setObjectName(u"everify_button")

        self.gridLayout.addWidget(self.everify_button, 0, 3, 1, 1)

        SearchDeathWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(SearchDeathWindow)

        QMetaObject.connectSlotsByName(SearchDeathWindow)
    # setupUi

    def retranslateUi(self, SearchDeathWindow):
        SearchDeathWindow.setWindowTitle(QCoreApplication.translate("SearchDeathWindow", u"MainWindow", None))
        self.search_textEdit.setPlaceholderText("")
        self.search_button.setText("")
        self.create_form.setText("")
        # self.docstamp1.setText("")
        self.no_record.setText("")
        self.destroyed.setText("")
        # self.docstamp2.setText("")
        self.status_label.setText("")
        self.regyear_textEdit.setText("")
        self.regyear_textEdit.setPlaceholderText(QCoreApplication.translate("SearchDeathWindow", u"Enter Year of Registration", None))
        self.everify_button.setText(QCoreApplication.translate("SearchDeathWindow", u"PushButton", None))
    # retranslateUi

