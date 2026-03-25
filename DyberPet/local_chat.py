import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QMessageBox

from DyberPet.local_llm import LocalLLMService
import DyberPet.settings as settings


class LocalChatWindow(QWidget):
    response_ready = Signal(str, name='response_ready')
    error_ready = Signal(str, name='error_ready')

    def __init__(self, parent=None, pet_name='桌宠', availability_checker=None):
        super().__init__(parent)
        self.pet_name = pet_name
        self.llm = LocalLLMService()
        self.history = []
        self._busy = False
        self.availability_checker = availability_checker

        self.setWindowTitle('桌宠聊天')
        self.setMinimumSize(460, 520)

        self.chat_view = QTextEdit(self)
        self.chat_view.setReadOnly(True)

        self.input_edit = QLineEdit(self)
        self.input_edit.setPlaceholderText('输入消息，按回车发送...')
        self.send_btn = QPushButton('发送', self)
        self.clear_btn = QPushButton('清空', self)

        row = QHBoxLayout()
        row.addWidget(self.input_edit)
        row.addWidget(self.send_btn)
        row.addWidget(self.clear_btn)

        root = QVBoxLayout(self)
        root.addWidget(self.chat_view)
        root.addLayout(row)

        self.send_btn.clicked.connect(self._send_message)
        self.input_edit.returnPressed.connect(self._send_message)
        self.clear_btn.clicked.connect(self._clear)
        self.response_ready.connect(self._on_response)
        self.error_ready.connect(self._on_error)

    def set_pet_name(self, pet_name):
        self.pet_name = pet_name

    def _append_line(self, who, text):
        self.chat_view.append(f'[{who}] {text}')
        self.chat_view.verticalScrollBar().setValue(self.chat_view.verticalScrollBar().maximum())

    def _clear(self):
        self.history = []
        self.chat_view.clear()

    def _send_message(self):
        text = self.input_edit.text().strip()
        if not text or self._busy:
            return

        if callable(self.availability_checker):
            extra_reason = self.availability_checker()
            if extra_reason:
                QMessageBox.warning(self, '不可用', extra_reason)
                return

        reason = self.llm.unavailable_reason()
        if reason:
            QMessageBox.warning(self, '不可用', reason)
            return

        self.input_edit.clear()
        self._append_line('你', text)
        self.history.append({'role': 'user', 'content': text})
        if hasattr(settings, 'diary_data'):
            settings.diary_data.add_entry(settings.petname, 'chat_user', text)
        self._busy = True
        self.send_btn.setEnabled(False)

        threading.Thread(target=self._worker_chat, daemon=True).start()

    def _worker_chat(self):
        try:
            reply = self.llm.chat(
                messages=self.history[-8:],
                system_prompt=f'你是桌宠{self.pet_name}，回答自然、简短、友好。',
                max_tokens=256,
                temperature=0.7,
                timeout=20,
            )
            if not reply:
                reply = '我有点卡壳了，再说一次嘛。'
            self.response_ready.emit(reply)
        except Exception as e:
            self.error_ready.emit(str(e))

    def _on_response(self, text):
        self.history.append({'role': 'assistant', 'content': text})
        self._append_line(self.pet_name, text)
        if hasattr(settings, 'diary_data'):
            settings.diary_data.add_entry(settings.petname, 'chat_pet', text)
        self._busy = False
        self.send_btn.setEnabled(True)

    def _on_error(self, err):
        self._append_line('系统', f'联网模型调用失败: {err}')
        self._busy = False
        self.send_btn.setEnabled(True)
