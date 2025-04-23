# -*- coding: utf-8 -*-

import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog
import qfluentwidgets
from qfluentwidgets import InfoBar, InfoBarPosition
from src.transform import ZhihuDownloader
from qfluentwidgets import BodyLabel, LineEdit, TextEdit, TitleLabel

class Ui_Form(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.bindSignals()
        
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(628, 528)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(Form)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.TitleLabel = TitleLabel(Form)
        self.TitleLabel.setObjectName("TitleLabel")
        self.verticalLayout.addWidget(self.TitleLabel)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.BodyLabel = BodyLabel(Form)
        self.BodyLabel.setObjectName("BodyLabel")
        self.horizontalLayout.addWidget(self.BodyLabel)
        self.LineEdit = LineEdit(Form)
        self.LineEdit.setObjectName("LineEdit")
        self.horizontalLayout.addWidget(self.LineEdit)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.BodyLabel_2 = BodyLabel(Form)
        self.BodyLabel_2.setObjectName("BodyLabel_2")
        self.horizontalLayout_2.addWidget(self.BodyLabel_2)
        self.TextEdit = TextEdit(Form)
        self.TextEdit.setObjectName("TextEdit")
        self.horizontalLayout_2.addWidget(self.TextEdit)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.BodyLabel_3 = BodyLabel(Form)
        self.BodyLabel_3.setObjectName("BodyLabel_3")
        self.horizontalLayout_3.addWidget(self.BodyLabel_3)
        self.LineEdit_3 = LineEdit(Form)
        self.LineEdit_3.setText("")
        self.LineEdit_3.setObjectName("LineEdit_3")
        self.horizontalLayout_3.addWidget(self.LineEdit_3)
        self.PushButton = qfluentwidgets.PushButton(Form)
        self.PushButton.setObjectName("PushButton")
        self.horizontalLayout_3.addWidget(self.PushButton)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.PrimaryPushButton = qfluentwidgets.PrimaryPushButton(Form)
        self.PrimaryPushButton.setObjectName("PrimaryPushButton")
        self.verticalLayout.addWidget(self.PrimaryPushButton)
        self.horizontalLayout_4.addLayout(self.verticalLayout)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)
        
    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.TitleLabel.setText(_translate("Form", "Zhihu Grab"))
        self.BodyLabel.setText(_translate("Form", "知乎链接："))
        self.BodyLabel_2.setText(_translate("Form", "Cookie :"))
        self.BodyLabel_3.setText(_translate("Form", "保存地址："))
        self.PushButton.setText(_translate("Form", "浏览"))
        self.PrimaryPushButton.setText(_translate("Form", "保存为markdown文档"))
        
    def bindSignals(self):
        """绑定信号槽"""
        self.PushButton.clicked.connect(self.selectSaveDir)
        self.PrimaryPushButton.clicked.connect(self.saveToMarkdown)
        
    def selectSaveDir(self):
        """选择保存目录"""
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录", os.path.expanduser("~"))
        if save_dir:
            self.LineEdit_3.setText(save_dir)
            
    def saveToMarkdown(self):
        """保存为markdown文档"""
        try:
            # 获取输入值
            url = self.LineEdit.text().strip()
            cookie = self.TextEdit.toPlainText().strip()
            save_dir = self.LineEdit_3.text().strip()
            
            # 验证输入
            if not url:
                InfoBar.warning(
                    title='警告',
                    content='请输入知乎链接',
                    orient=QtCore.Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            if not cookie:
                InfoBar.warning(
                    title='警告',
                    content='请输入Cookie',
                    orient=QtCore.Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            if not save_dir:
                InfoBar.warning(
                    title='警告',
                    content='请选择保存目录',
                    orient=QtCore.Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
                
            # 创建保存目录
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            # 切换到保存目录
            current_dir = os.getcwd()
            os.chdir(save_dir)
            
            try:
                # 下载并转换内容
                downloader = ZhihuDownloader(cookie)
                output_name = downloader.check_url(url)
                InfoBar.success(
                    title='成功',
                    content=f'文章已保存到：\n{os.path.join(save_dir, output_name)}',
                    orient=QtCore.Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            finally:
                # 恢复原来的工作目录
                os.chdir(current_dir)
                
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=str(e),
                orient=QtCore.Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
