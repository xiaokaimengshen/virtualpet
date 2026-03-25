# coding:utf-8
import os

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QPushButton,
    QComboBox,
    QPlainTextEdit,
    QMessageBox,
)
from qfluentwidgets import ScrollArea, ExpandLayout, CardWidget, TransparentToolButton

import DyberPet.settings as settings

basedir = settings.BASEDIR


class notebookInterface(ScrollArea):
    """Notebook page for generated daily journals."""

    def __init__(self, sizeHintdb: tuple[int, int], parent=None):
        super().__init__(parent=parent)

        self.setObjectName("notebookInterface")
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        self.headerWidget = QWidget(self)
        self.headerWidget.setFixedWidth(sizeHintdb[0] - 175)
        self.panelLabel = QLabel(self.tr("日记本"), self.headerWidget)
        self.panelLabel.setSizePolicy(QSizePolicy.Maximum, self.panelLabel.sizePolicy().verticalPolicy())
        self.panelLabel.adjustSize()
        self.panelHelp = TransparentToolButton(QIcon(os.path.join(basedir, 'res/icons/question.svg')), self.headerWidget)
        self.panelHelp.setFixedSize(25, 25)
        self.panelHelp.setIconSize(QSize(25, 25))

        self.headerLayout = QHBoxLayout(self.headerWidget)
        self.headerLayout.setContentsMargins(0, 0, 0, 0)
        self.headerLayout.setSpacing(0)
        self.headerLayout.addWidget(self.panelLabel, Qt.AlignLeft | Qt.AlignVCenter)
        self.headerLayout.addItem(QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))
        self.headerLayout.addWidget(self.panelHelp, Qt.AlignLeft | Qt.AlignVCenter)
        self.headerLayout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.diaryCard = CardWidget(self.scrollWidget)
        self.diaryCard.setBorderRadius(12)

        self.diaryTitle = QLabel(self.tr("日记"), self.diaryCard)
        self.diaryTitle.setObjectName("diaryTitle")

        self.dayCombo = QComboBox(self.diaryCard)
        self.dayCombo.currentIndexChanged.connect(self._on_day_changed)

        self.prevPageBtn = QPushButton(self.tr("上一页"), self.diaryCard)
        self.nextPageBtn = QPushButton(self.tr("下一页"), self.diaryCard)
        self.pageInfo = QLabel("0/0", self.diaryCard)
        self.pageInfo.setAlignment(Qt.AlignCenter)
        self.pageInfo.setMinimumWidth(70)

        self.prevPageBtn.clicked.connect(self._prev_page)
        self.nextPageBtn.clicked.connect(self._next_page)

        self.diaryBody = QPlainTextEdit(self.diaryCard)
        self.diaryBody.setReadOnly(True)
        self.diaryBody.setObjectName("diaryBody")
        self.diaryBody.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.diaryBody.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.diaryBody.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.current_day = None
        self.current_pages = []
        self.current_page_index = 0

        self.toolbarLayout = QHBoxLayout()
        self.toolbarLayout.setContentsMargins(0, 0, 0, 0)
        self.toolbarLayout.setSpacing(8)
        self.toolbarLayout.addWidget(self.dayCombo, 1)
        self.toolbarLayout.addWidget(self.prevPageBtn)
        self.toolbarLayout.addWidget(self.pageInfo)
        self.toolbarLayout.addWidget(self.nextPageBtn)

        self.bodyLayout = QVBoxLayout(self.diaryCard)
        self.bodyLayout.setContentsMargins(28, 26, 28, 20)
        self.bodyLayout.setSpacing(12)
        self.bodyLayout.addWidget(self.diaryTitle)
        self.bodyLayout.addLayout(self.toolbarLayout)
        self.bodyLayout.addWidget(self.diaryBody, 1)

        self.refreshTimer = QTimer(self)
        self.refreshTimer.timeout.connect(self.refreshDiary)
        self.refreshTimer.start(5000)

        self.__initWidget()
        self.refreshDiary()

    def __initWidget(self):
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 125, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        self.__setQss()
        self.__initLayout()
        self.__connectSignalToSlot()

    def __connectSignalToSlot(self):
        self.panelHelp.clicked.connect(self._show_instruction)

    def __initLayout(self):
        self.headerWidget.move(60, 20)
        self.diaryCard.setMinimumHeight(460)

        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(70, 10, 70, 0)
        self.expandLayout.addWidget(self.diaryCard)

    def __setQss(self):
        self.scrollWidget.setObjectName("scrollWidget")
        self.panelLabel.setObjectName("panelLabel")
        theme = "light"
        with open(os.path.join(basedir, "res/icons/Dashboard/qss/", theme, "status_interface.qss"), encoding="utf-8") as f:
            self.setStyleSheet(
                f.read()
                + """
                QLabel#diaryTitle {
                    font-size: 18px;
                    font-weight: 600;
                }
                QPlainTextEdit#diaryBody {
                    font-size: 14px;
                    color: rgba(30, 30, 30, 0.88);
                    background: transparent;
                    border: none;
                }
            """
            )

    def _set_empty(self, message):
        self.current_day = None
        self.current_pages = []
        self.current_page_index = 0
        self.diaryTitle.setText(self.tr("日记"))
        self.diaryBody.setPlainText(message)
        self.pageInfo.setText("0/0")
        self.prevPageBtn.setEnabled(False)
        self.nextPageBtn.setEnabled(False)

    def refreshDiary(self, *_):
        if not hasattr(settings, "diary_data"):
            self._set_empty(self.tr("日记系统尚未初始化。"))
            return

        try:
            settings.diary_data.finalize_pending(settings.petname)
        except Exception:
            pass

        days = settings.diary_data.list_journal_days(settings.petname)
        last_selected = self.current_day

        self.dayCombo.blockSignals(True)
        self.dayCombo.clear()
        for d in days:
            self.dayCombo.addItem(d, userData=d)
        self.dayCombo.blockSignals(False)

        if not days:
            self._set_empty(self.tr("暂无可查看日记。"))
            self.dayCombo.setEnabled(False)
            return

        self.dayCombo.setEnabled(True)
        if last_selected in days:
            idx = days.index(last_selected)
            self.dayCombo.setCurrentIndex(idx)
        else:
            self.dayCombo.setCurrentIndex(0)
        self._on_day_changed(self.dayCombo.currentIndex())

    def _on_day_changed(self, idx):
        if idx < 0:
            self._set_empty(self.tr("暂无可查看日记。"))
            return
        day = self.dayCombo.itemData(idx)
        if not day:
            self._set_empty(self.tr("暂无可查看日记。"))
            return

        journal = settings.diary_data.get_journal(settings.petname, day)
        if not journal:
            self._set_empty(self.tr("该日期没有日记。"))
            return

        self.current_day = day
        self.current_pages = journal.get("pages") or []
        if not self.current_pages:
            content = (journal.get("content") or "").strip()
            self.current_pages = [content] if content else []
        self.current_page_index = 0
        self.diaryTitle.setText(journal.get("title", f"{day} 日记"))
        self._render_current_page()

    def _render_current_page(self):
        total = len(self.current_pages)
        if total <= 0:
            self._set_empty(self.tr("该日期没有可显示内容。"))
            return

        self.current_page_index = max(0, min(self.current_page_index, total - 1))
        self.diaryBody.setPlainText(self.current_pages[self.current_page_index])
        self.diaryBody.verticalScrollBar().setValue(0)
        self.pageInfo.setText(f"{self.current_page_index + 1}/{total}")
        self.prevPageBtn.setEnabled(self.current_page_index > 0)
        self.nextPageBtn.setEnabled(self.current_page_index < total - 1)

    def _prev_page(self):
        if self.current_page_index <= 0:
            return
        self.current_page_index -= 1
        self._render_current_page()

    def _next_page(self):
        if self.current_page_index >= len(self.current_pages) - 1:
            return
        self.current_page_index += 1
        self._render_current_page()

    def _show_instruction(self):
        QMessageBox.information(self, self.tr("日记本"), self.tr("桌宠会每天写日记哦"))
