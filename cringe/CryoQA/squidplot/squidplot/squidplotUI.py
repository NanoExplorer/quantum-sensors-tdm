# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'squidplot.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(798, 581)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.innerwidget = QtGui.QWidget(self.centralwidget)
        self.innerwidget.setObjectName(_fromUtf8("innerwidget"))
        self.horizontalLayout_4 = QtGui.QHBoxLayout(self.innerwidget)
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.controlWidget = QtGui.QWidget(self.innerwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.controlWidget.sizePolicy().hasHeightForWidth())
        self.controlWidget.setSizePolicy(sizePolicy)
        self.controlWidget.setObjectName(_fromUtf8("controlWidget"))
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.controlWidget)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.filetypeGroupBox = QtGui.QGroupBox(self.controlWidget)
        self.filetypeGroupBox.setEnabled(True)
        self.filetypeGroupBox.setObjectName(_fromUtf8("filetypeGroupBox"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.filetypeGroupBox)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.filetypeLineEdit = QtGui.QLineEdit(self.filetypeGroupBox)
        self.filetypeLineEdit.setMaximumSize(QtCore.QSize(200, 16777215))
        self.filetypeLineEdit.setReadOnly(True)
        self.filetypeLineEdit.setObjectName(_fromUtf8("filetypeLineEdit"))
        self.verticalLayout_2.addWidget(self.filetypeLineEdit)
        self.verticalLayout_3.addWidget(self.filetypeGroupBox)
        self.columnGroupBox = QtGui.QGroupBox(self.controlWidget)
        self.columnGroupBox.setEnabled(False)
        self.columnGroupBox.setObjectName(_fromUtf8("columnGroupBox"))
        self.verticalLayout_4 = QtGui.QVBoxLayout(self.columnGroupBox)
        self.verticalLayout_4.setObjectName(_fromUtf8("verticalLayout_4"))
        self.columnComboBox = QtGui.QComboBox(self.columnGroupBox)
        self.columnComboBox.setObjectName(_fromUtf8("columnComboBox"))
        self.verticalLayout_4.addWidget(self.columnComboBox)
        self.verticalLayout_3.addWidget(self.columnGroupBox)
        self.pageGroupBox = QtGui.QGroupBox(self.controlWidget)
        self.pageGroupBox.setObjectName(_fromUtf8("pageGroupBox"))
        self.verticalLayout_5 = QtGui.QVBoxLayout(self.pageGroupBox)
        self.verticalLayout_5.setObjectName(_fromUtf8("verticalLayout_5"))
        self.pageComboBox = QtGui.QComboBox(self.pageGroupBox)
        self.pageComboBox.setObjectName(_fromUtf8("pageComboBox"))
        self.verticalLayout_5.addWidget(self.pageComboBox)
        self.verticalLayout_3.addWidget(self.pageGroupBox)
        self.channelGroupBox = QtGui.QGroupBox(self.controlWidget)
        self.channelGroupBox.setEnabled(False)
        self.channelGroupBox.setObjectName(_fromUtf8("channelGroupBox"))
        self.verticalLayout_6 = QtGui.QVBoxLayout(self.channelGroupBox)
        self.verticalLayout_6.setObjectName(_fromUtf8("verticalLayout_6"))
        self.chwidget1 = QtGui.QWidget(self.channelGroupBox)
        self.chwidget1.setObjectName(_fromUtf8("chwidget1"))
        self.horizontalLayout_5 = QtGui.QHBoxLayout(self.chwidget1)
        self.horizontalLayout_5.setObjectName(_fromUtf8("horizontalLayout_5"))
        self.plotlabel = QtGui.QLabel(self.chwidget1)
        self.plotlabel.setObjectName(_fromUtf8("plotlabel"))
        self.horizontalLayout_5.addWidget(self.plotlabel)
        self.channelLineEdit = QtGui.QLineEdit(self.chwidget1)
        self.channelLineEdit.setMinimumSize(QtCore.QSize(60, 0))
        self.channelLineEdit.setMaximumSize(QtCore.QSize(60, 16777215))
        self.channelLineEdit.setReadOnly(True)
        self.channelLineEdit.setObjectName(_fromUtf8("channelLineEdit"))
        self.horizontalLayout_5.addWidget(self.channelLineEdit)
        self.verticalLayout_6.addWidget(self.chwidget1)
        self.chwidget2 = QtGui.QWidget(self.channelGroupBox)
        self.chwidget2.setObjectName(_fromUtf8("chwidget2"))
        self.verticalLayout_7 = QtGui.QVBoxLayout(self.chwidget2)
        self.verticalLayout_7.setObjectName(_fromUtf8("verticalLayout_7"))
        self.channelSlider = QtGui.QSlider(self.chwidget2)
        self.channelSlider.setMaximum(1)
        self.channelSlider.setOrientation(QtCore.Qt.Horizontal)
        self.channelSlider.setTickPosition(QtGui.QSlider.TicksBothSides)
        self.channelSlider.setTickInterval(1)
        self.channelSlider.setObjectName(_fromUtf8("channelSlider"))
        self.verticalLayout_7.addWidget(self.channelSlider)
        self.verticalLayout_6.addWidget(self.chwidget2)
        self.verticalLayout_3.addWidget(self.channelGroupBox)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem)
        self.horizontalLayout_4.addWidget(self.controlWidget)
        self.plotwidget = PlotWidget(self.innerwidget)
        self.plotwidget.setObjectName(_fromUtf8("plotwidget"))
        self.horizontalLayout_4.addWidget(self.plotwidget)
        self.verticalLayout.addWidget(self.innerwidget)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 798, 22))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setObjectName(_fromUtf8("menuFile"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.actionOpen = QtGui.QAction(MainWindow)
        self.actionOpen.setObjectName(_fromUtf8("actionOpen"))
        self.actionExit = QtGui.QAction(MainWindow)
        self.actionExit.setObjectName(_fromUtf8("actionExit"))
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionExit)
        self.menubar.addAction(self.menuFile.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "squidplot", None))
        self.filetypeGroupBox.setTitle(_translate("MainWindow", "Filetype", None))
        self.columnGroupBox.setTitle(_translate("MainWindow", "Column", None))
        self.pageGroupBox.setTitle(_translate("MainWindow", "Page", None))
        self.channelGroupBox.setTitle(_translate("MainWindow", "Channel", None))
        self.plotlabel.setText(_translate("MainWindow", "Current", None))
        self.menuFile.setTitle(_translate("MainWindow", "File", None))
        self.actionOpen.setText(_translate("MainWindow", "Open", None))
        self.actionExit.setText(_translate("MainWindow", "Exit", None))

from pyqtgraph import PlotWidget
