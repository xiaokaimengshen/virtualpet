# coding:utf-8
import sys
import os
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import QApplication
from qfluentwidgets import (NavigationItemPosition, MessageBox, setTheme, Theme, FluentWindow,
                            NavigationAvatarWidget,  SplitFluentWindow, FluentTranslator)
from qfluentwidgets import FluentIcon as FIF

from .BasicSettingUI import SettingInterface
from .GameSaveUI import SaveInterface
from .CharCardUI import CharInterface
from .ItemCardUI import ItemInterface
from .PetCardUI import PetInterface
from sys import platform
import DyberPet.settings as settings
basedir = settings.BASEDIR

module_path = os.path.join(basedir, 'DyberPet/DyberSettings/')


class ControlMainWindow(FluentWindow):

    def __init__(self, minWidth=800, minHeight=800):
        super().__init__()

        # create sub interface
        self.settingInterface = SettingInterface(self)
        self.gamesaveInterface = SaveInterface(sizeHintDyber=(minWidth, minHeight), parent=self)
        self.charCardInterface = CharInterface(sizeHintDyber=(minWidth, minHeight), parent=self)
        self.itemCardInterface = ItemInterface(sizeHintDyber=(minWidth, minHeight), parent=self)
        self.petCardInterface = PetInterface(sizeHintDyber=(minWidth, minHeight), parent=self)

        self.initNavigation()
        self.setMinimumSize(minWidth, minHeight)
        self.initWindow()

    def initNavigation(self):
        # add sub interface
        self.addSubInterface(self.settingInterface, FIF.SETTING, self.tr('设置'))
        self.addSubInterface(self.gamesaveInterface,
                             FIF.SAVE,
                             self.tr('存档'))
        self.addSubInterface(self.charCardInterface,
                             QIcon(os.path.join(basedir, "res/icons/system/character.svg")),
                             self.tr('角色'))
        self.addSubInterface(self.itemCardInterface,
                             QIcon(os.path.join(basedir, "res/icons/system/itemMod.svg")),
                             self.tr('物品模块'))
        self.addSubInterface(self.petCardInterface,
                             QIcon(os.path.join(basedir, "res/icons/system/minipet.svg")),
                             self.tr('小宠物'))

        self.navigationInterface.setExpandWidth(200)

    def initWindow(self):
        self.setWindowIcon(QIcon(os.path.join(basedir, "res/icons/SystemPanel.png")))
        self.setWindowTitle(self.tr('系统'))

        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

    def show_window(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)

    translator = FluentTranslator()
    app.installTranslator(translator)

    w = ControlMainWindow()
    w.show()
    app.exec_()
