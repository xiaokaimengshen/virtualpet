# coding:utf-8
import os
import json
import urllib.request
from sys import platform

from qfluentwidgets import (SettingCardGroup, SwitchSettingCard, HyperlinkCard, SettingCard, InfoBar,
                            ComboBoxSettingCard, ScrollArea, ExpandLayout, InfoBarPosition, PushSettingCard,
                            setThemeColor)

from qfluentwidgets import FluentIcon as FIF
from PySide6.QtCore import Qt, Signal, QUrl, QStandardPaths, QLocale
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QWidget, QLabel, QApplication, QInputDialog, QLineEdit, QMessageBox
#from qframelesswindow import FramelessWindow

from .custom_utils import Dyber_RangeSettingCard, Dyber_ComboBoxSettingCard, CustomColorSettingCard, LineEditDialog
import DyberPet.settings as settings
from DyberPet.local_llm import LocalLLMService
from DyberPet.SelfStartup.windows_startup import is_enabled as startup_is_enabled, set_enabled as startup_set_enabled

basedir = settings.BASEDIR
module_path = os.path.join(basedir, 'DyberPet/DyberSettings/')
'''
if platform == 'win32':
    basedir = ''
    module_path = 'DyberPet/DyberSettings/'
else:
    #from pathlib import Path
    basedir = os.path.dirname(__file__) #Path(os.path.dirname(__file__))
    #basedir = basedir.parent
    basedir = basedir.replace('\\','/')
    basedir = '/'.join(basedir.split('/')[:-2])

    module_path = os.path.join(basedir, 'DyberPet/DyberSettings/')
'''


class SettingInterface(ScrollArea):
    """ Setting interface """

    ontop_changed = Signal(name='ontop_changed')
    scale_changed = Signal(name='scale_changed')
    lang_changed = Signal(name='lang_changed')
    dev_add_coins = Signal(int, name='dev_add_coins')
    dev_set_hp_zero = Signal(name='dev_set_hp_zero')
    dev_generate_today_diary = Signal(name='dev_generate_today_diary')

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingInterface")
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # setting label
        self.settingLabel = QLabel(self.tr("设置"), self)
        
        # Mode =========================================================================================
        self.ModeGroup = SettingCardGroup(self.tr('模式'), self.scrollWidget)
        # Always on top
        self.AlwaysOnTopCard = SwitchSettingCard(
            FIF.PIN,
            self.tr("窗口置顶"),
            self.tr("桌宠会显示在其它应用上方"),
            parent=self.ModeGroup #DisplayModeGroup
        )
        if settings.on_top_hint:
            self.AlwaysOnTopCard.setChecked(True)
        else:
            self.AlwaysOnTopCard.setChecked(False)
        self.AlwaysOnTopCard.switchButton.checkedChanged.connect(self._AlwaysOnTopChanged)

        # Allow drop
        self.AllowDropCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/falldown.svg')),
            self.tr("允许掉落"),
            self.tr("鼠标松开后：开启时会落地，关闭时停在当前位置"),
            parent=self.ModeGroup #DisplayModeGroup
        )
        if settings.set_fall:
            self.AllowDropCard.setChecked(True)
        else:
            self.AllowDropCard.setChecked(False)
        self.AllowDropCard.switchButton.checkedChanged.connect(self._AllowDropChanged)

        # Auto-Lock
        self.AutoLockCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/lock.svg')),
            self.tr("自动锁定"),
            self.tr("锁屏时同时锁定饱食度和好感度（目前仅 Windows 生效）"),
            parent=self.ModeGroup #DisplayModeGroup
        )
        if settings.auto_lock:
            self.AutoLockCard.setChecked(True)
        else:
            self.AutoLockCard.setChecked(False)
        self.AutoLockCard.switchButton.checkedChanged.connect(self._AutoLockChanged)
        if platform != 'win32':
            self.AutoLockCard.switchButton.indicator.setEnabled(False)

        # Auto-Start
        self.AutoStartCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/software.svg')),
            self.tr("开机自启动"),
            self.tr("登录系统后自动启动 猫猫桌宠"),
            parent=self.ModeGroup
        )
        startup_checked = settings.auto_startup or startup_is_enabled()
        self.AutoStartCard.setChecked(startup_checked)
        self.AutoStartCard.switchButton.checkedChanged.connect(self._AutoStartChanged)
        if platform != 'win32':
            self.AutoStartCard.switchButton.indicator.setEnabled(False)


        # Interaction parameters =======================================================================
        self.InteractionGroup = SettingCardGroup(self.tr('交互'), self.scrollWidget)
        self.GravityCard = Dyber_RangeSettingCard(
            1, 200, 0.01,
            QIcon(os.path.join(basedir, 'res/icons/system/gravity.svg')),
            self.tr("重力"),
            self.tr("桌宠下落加速度"),
            parent=self.InteractionGroup
        )

        self.GravityCard.setValue(int(settings.gravity*100))
        self.GravityCard.slider.valueChanged.connect(self._GravityChanged)

        self.DragCard = Dyber_RangeSettingCard(
            0, 200, 0.01,
            QIcon(os.path.join(basedir, 'res/icons/system/mousedrag.svg')),
            self.tr("拖拽速度"),
            self.tr("鼠标拖拽速度系数"),
            parent=self.InteractionGroup
        )
        self.DragCard.setValue(int(settings.fixdragspeedx*100))
        self.DragCard.slider.valueChanged.connect(self._DragChanged)

        # Notification parameters ======================================================================
        self.VolumnGroup = SettingCardGroup(self.tr('通知'), self.scrollWidget)
        self.VolumnCard = Dyber_RangeSettingCard(
            0, 10, 0.1,
            QIcon(os.path.join(basedir, 'res/icons/system/speaker.svg')),
            self.tr("音量"),
            self.tr("通知与桌宠音量"),
            parent=self.VolumnGroup
        )
        self.VolumnCard.setValue(int(settings.volume*10))
        self.VolumnCard.slider.valueChanged.connect(self._VolumnChanged)

        self.AllowToasterCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/popup.svg')),
            self.tr("弹窗通知"),
            self.tr("开启后通知会在右下角弹出"),
            parent=self.VolumnGroup
        )
        if settings.toaster_on:
            self.AllowToasterCard.setChecked(True)
        else:
            self.AllowToasterCard.setChecked(False)
        self.AllowToasterCard.switchButton.checkedChanged.connect(self._AllowToasterChanged)

        self.AllowBubbleCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/bubble.svg')),
            self.tr("对话气泡"),
            self.tr("开启后桌宠上方会弹出各类气泡"),
            parent=self.VolumnGroup
        )
        if settings.bubble_on:
            self.AllowBubbleCard.setChecked(True)
        else:
            self.AllowBubbleCard.setChecked(False)
        self.AllowBubbleCard.switchButton.checkedChanged.connect(self._AllowBubbleChanged)

        # Personalization ==============================================================================
        self.PersonalGroup = SettingCardGroup(self.tr('个性化'), self.scrollWidget)
        self.ScaleCard = Dyber_RangeSettingCard(
            1, 50, 0.1,
            QIcon(os.path.join(basedir, 'res/icons/system/resize.svg')),
            self.tr("桌宠缩放"),
            self.tr("调整桌宠大小"),
            parent=self.PersonalGroup
        )
        self.ScaleCard.setValue(int(settings.tunable_scale*10))
        self.ScaleCard.slider.valueChanged.connect(self._ScaleChanged)

        pet_list = settings.pets
        self.DefaultPetCard = Dyber_ComboBoxSettingCard(
            pet_list,
            pet_list,
            QIcon(os.path.join(basedir, 'res/icons/system/homestar.svg')),
            self.tr('默认桌宠'),
            self.tr('每次启动应用时显示的桌宠'),
            parent=self.PersonalGroup
        )
        self.DefaultPetCard.comboBox.currentTextChanged.connect(self._DefaultPetChanged)

        lang_choices = list(settings.lang_dict.keys())
        lang_now = lang_choices[list(settings.lang_dict.values()).index(settings.language_code)]
        lang_choices.remove(lang_now)
        lang_choices = [lang_now] + lang_choices
        self.languageCard = Dyber_ComboBoxSettingCard(
            lang_choices,
            lang_choices,
            FIF.LANGUAGE,
            self.tr('语言'),
            self.tr('设置界面显示语言'),
            parent=self.PersonalGroup
        )
        self.languageCard.comboBox.currentTextChanged.connect(self._LanguageChanged)

        self.themeColorCard = CustomColorSettingCard(
            FIF.PALETTE,
            self.tr('主题色'),
            self.tr('修改应用主题颜色'),
            self.PersonalGroup
        )
        self.themeColorCard.colorChanged.connect(self.colorChanged)

        # LLM settings ==============================================================================
        self.LLMGroup = SettingCardGroup(self.tr('AI大模型'), self.scrollWidget)

        self.LLMEnableCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/ai.svg')),
            self.tr("启用联网大模型"),
            self.tr("启用云端模型聊天与互动自动回复"),
            parent=self.LLMGroup
        )
        self.LLMEnableCard.setChecked(bool(settings.llm_config.get('enabled', False)))
        self.LLMEnableCard.switchButton.checkedChanged.connect(self._LLMEnableChanged)

        provider_keys = list(settings.LLM_PROVIDERS.keys())
        self.llm_provider_name2key = {settings.LLM_PROVIDERS[k]['name']: k for k in provider_keys}
        provider_texts = [settings.LLM_PROVIDERS[k]['name'] for k in provider_keys]
        current_provider = settings.llm_config.get('api_type', provider_keys[0])
        if current_provider not in settings.LLM_PROVIDERS:
            current_provider = provider_keys[0]
            settings.llm_config['api_type'] = current_provider
        provider_texts = [settings.LLM_PROVIDERS[current_provider]['name']] + [t for t in provider_texts if t != settings.LLM_PROVIDERS[current_provider]['name']]
        provider_opts = [self.llm_provider_name2key[t] for t in provider_texts]

        self.LLMProviderCard = Dyber_ComboBoxSettingCard(
            provider_opts,
            provider_texts,
            QIcon(os.path.join(basedir, 'res/icons/system/link.svg')),
            self.tr('模型服务商'),
            self.tr('选择联网模型服务商'),
            parent=self.LLMGroup
        )
        self.LLMProviderCard.comboBox.currentTextChanged.connect(self._LLMProviderChanged)

        model_options = settings.LLM_PROVIDERS[current_provider].get('models', [])
        current_model = settings.llm_config.get('model', '')
        if model_options:
            if current_model not in model_options:
                current_model = model_options[0]
                settings.llm_config['model'] = current_model
            model_texts = [current_model] + [m for m in model_options if m != current_model]
        else:
            model_texts = [current_model or "Qwen2.5-0.5B-Instruct"]

        self.LLMModelCard = Dyber_ComboBoxSettingCard(
            model_texts,
            model_texts,
            QIcon(os.path.join(basedir, 'res/icons/system/document.svg')),
            self.tr('模型名称'),
            self.tr('选择要调用的模型名称'),
            parent=self.LLMGroup
        )
        self.LLMModelCard.comboBox.currentTextChanged.connect(self._LLMModelChanged)

        self.LLMApiKeyCard = PushSettingCard(
            self.tr('编辑'),
            QIcon(os.path.join(basedir, 'res/icons/system/key.svg')),
            self.tr('API 密钥'),
            self.tr('配置服务商 API 密钥'),
            parent=self.LLMGroup
        )
        self.LLMApiKeyCard.clicked.connect(self._edit_llm_api_key)

        self.LLMApiUrlCard = PushSettingCard(
            self.tr('编辑'),
            QIcon(os.path.join(basedir, 'res/icons/system/link.svg')),
            self.tr('API 地址'),
            self.tr('配置联网接口地址（OpenAI 兼容）'),
            parent=self.LLMGroup
        )
        self.LLMApiUrlCard.clicked.connect(self._edit_llm_api_url)

        self.LLMAutoTalkCard = SwitchSettingCard(
            QIcon(os.path.join(basedir, 'res/icons/system/bubble.svg')),
            self.tr("互动自动回复"),
            self.tr("与桌宠互动时自动调用联网模型说话"),
            parent=self.LLMGroup
        )
        self.LLMAutoTalkCard.setChecked(bool(settings.llm_config.get('auto_talk', True)))
        self.LLMAutoTalkCard.switchButton.checkedChanged.connect(self._LLMAutoTalkChanged)

        self.LLMTestCard = PushSettingCard(
            self.tr('测试'),
            QIcon(os.path.join(basedir, 'res/icons/system/debug.svg')),
            self.tr('测试联网服务'),
            self.tr('检查联网大模型是否可用'),
            parent=self.LLMGroup
        )
        self.LLMTestCard.clicked.connect(self._test_llm_connection)

        # About ==============================================================================
        self.aboutGroup = SettingCardGroup(self.tr('关于'), self.scrollWidget)
        # Do not check updates during app startup.
        settings.UPDATE_NEEDED = False
        self.aboutCard = PushSettingCard(
            self.tr('查看'),
            QIcon(os.path.join(basedir, 'res/icons/system/update.svg')),
            self.tr('检查更新'),
            '',
            self.aboutGroup
        )
        self.aboutCard.clicked.connect(self._show_update_info)
        self.helpCard = PushSettingCard(
            self.tr('查看'),
            FIF.HELP,
            self.tr('帮助问题'),
            '',
            self.aboutGroup
        )
        self.helpCard.clicked.connect(self._show_help_info)
        self.devModeCard = PushSettingCard(
            self.tr('进入'),
            QIcon(os.path.join(basedir, 'res/icons/system/debug.svg')),
            self.tr('开发者模式'),
            self.tr('输入密码后可执行测试功能'),
            self.aboutGroup
        )
        self.devModeCard.clicked.connect(self._open_developer_mode)
        self.thanksCard = PushSettingCard(
            self.tr('查看'),
            QIcon(os.path.join(basedir, 'res/icons/system/document.svg')),
            self.tr('致谢'),
            '',
            self.aboutGroup
        )
        self.thanksCard.clicked.connect(self._show_acknowledgement)
        self.__initWidget()

    def __initWidget(self):
        #self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 75, 0, 20)
        self.setWidget(self.scrollWidget)
        #self.scrollWidget.resize(1000, 800)
        self.setWidgetResizable(True)

        # initialize style sheet
        self.__setQss()

        # initialize layout
        self.__initLayout()
        #self.__connectSignalToSlot()

    def __initLayout(self):
        self.settingLabel.move(50, 20)

        # add cards to group
        self.ModeGroup.addSettingCard(self.AlwaysOnTopCard)
        self.ModeGroup.addSettingCard(self.AllowDropCard)
        self.ModeGroup.addSettingCard(self.AutoLockCard)
        self.ModeGroup.addSettingCard(self.AutoStartCard)

        self.InteractionGroup.addSettingCard(self.GravityCard)
        self.InteractionGroup.addSettingCard(self.DragCard)

        self.VolumnGroup.addSettingCard(self.VolumnCard)
        self.VolumnGroup.addSettingCard(self.AllowToasterCard)
        self.VolumnGroup.addSettingCard(self.AllowBubbleCard)

        self.PersonalGroup.addSettingCard(self.ScaleCard)
        self.PersonalGroup.addSettingCard(self.DefaultPetCard)
        self.PersonalGroup.addSettingCard(self.languageCard)
        self.PersonalGroup.addSettingCard(self.themeColorCard)

        self.LLMGroup.addSettingCard(self.LLMEnableCard)
        self.LLMGroup.addSettingCard(self.LLMProviderCard)
        self.LLMGroup.addSettingCard(self.LLMModelCard)
        self.LLMGroup.addSettingCard(self.LLMApiKeyCard)
        self.LLMGroup.addSettingCard(self.LLMApiUrlCard)
        self.LLMGroup.addSettingCard(self.LLMAutoTalkCard)
        self.LLMGroup.addSettingCard(self.LLMTestCard)

        self.aboutGroup.addSettingCard(self.aboutCard)
        self.aboutGroup.addSettingCard(self.helpCard)
        self.aboutGroup.addSettingCard(self.devModeCard)
        self.aboutGroup.addSettingCard(self.thanksCard)

        # add setting card group to layout
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(60, 10, 60, 0)

        self.expandLayout.addWidget(self.ModeGroup)
        self.expandLayout.addWidget(self.InteractionGroup)
        self.expandLayout.addWidget(self.VolumnGroup)
        self.expandLayout.addWidget(self.PersonalGroup)
        self.expandLayout.addWidget(self.LLMGroup)
        self.expandLayout.addWidget(self.aboutGroup)

    def __setQss(self):
        """ set style sheet """
        self.scrollWidget.setObjectName('scrollWidget')
        self.settingLabel.setObjectName('settingLabel')

        theme = 'light' #if isDarkTheme() else 'light'
        with open(os.path.join(basedir, 'res/icons/system/qss/', theme, 'setting_interface.qss'), encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def _AlwaysOnTopChanged(self, isChecked):
        if isChecked:
            settings.on_top_hint = True
            settings.save_settings()
            self.ontop_changed.emit()
        else:
            settings.on_top_hint = False
            settings.save_settings()
            self.ontop_changed.emit()

    def _AllowDropChanged(self, isChecked):
        if isChecked:
            settings.set_fall = True
        else:
            settings.set_fall = False
        settings.save_settings()

    def _AutoLockChanged(self, isChecked):
        if isChecked:
            settings.auto_lock = True
        else:
            settings.auto_lock = False
        settings.save_settings()

    def _AutoStartChanged(self, isChecked):
        settings.auto_startup = bool(isChecked)
        if platform == 'win32':
            ok = startup_set_enabled(bool(isChecked))
            if not ok:
                settings.auto_startup = startup_is_enabled()
        settings.save_settings()

    def _GravityChanged(self, value):
        settings.gravity = value*0.01
        settings.save_settings()

    def _DragChanged(self, value):
        settings.fixdragspeedx, settings.fixdragspeedy = value*0.01, value*0.01
        settings.save_settings()

    def _VolumnChanged(self, value):
        settings.volume = round(value*0.1, 3)
        settings.save_settings()

    def _ScaleChanged(self, value):
        settings.tunable_scale = value*0.1
        settings.scale_dict[settings.petname] = settings.tunable_scale
        settings.save_settings()
        self.scale_changed.emit()

    def _update_scale(self):
        self.ScaleCard.setValue(int(settings.tunable_scale*10))

    def _DefaultPetChanged(self, value):
        settings.default_pet = value
        settings.save_settings()

    def _LanguageChanged(self, value):
        settings.language_code = settings.lang_dict[value]
        settings.save_settings()
        settings.change_translator(settings.lang_dict[value])
        #self.retranslateUi()
        self.__showRestartTooltip()
        self.lang_changed.emit()
    
    def __showRestartTooltip(self):
        """ show restart tooltip """
        InfoBar.warning(
            '',
            self.tr('此设置在重启后生效'),
            duration=3000,
            position=InfoBarPosition.BOTTOM,
            parent=self.window()
        )

    def colorChanged(self, color_str):
        setThemeColor(color_str)
        settings.themeColor = color_str
        settings.save_settings()

    def _checkUpdate(self):
        local_version = settings.VERSION
        success, github_version = get_latest_version()
        if success:
            update_needed = compare_versions(local_version, github_version)
            if update_needed:
                return True, local_version + "  " + self.tr("发现新版本")
            else:
                return False, local_version + "  " + self.tr("已是最新版本")
        else:
            return False, self.tr("检查更新失败，请稍后重试。")
        
    def _AllowToasterChanged(self, isChecked):
        if isChecked:
            settings.toaster_on = True
        else:
            settings.toaster_on = False
        settings.save_settings()

    def _AllowBubbleChanged(self, isChecked):
        if isChecked:
            settings.bubble_on = True
        else:
            settings.bubble_on = False
        settings.save_settings()

    def _LLMEnableChanged(self, isChecked):
        settings.llm_config['enabled'] = bool(isChecked)
        settings.save_settings()

    def _LLMProviderChanged(self, provider_name):
        provider_key = self.llm_provider_name2key.get(provider_name, 'deepseek')
        settings.llm_config['api_type'] = provider_key
        provider_conf = settings.LLM_PROVIDERS.get(provider_key, settings.LLM_PROVIDERS['deepseek'])
        model_list = provider_conf.get('models', [])

        if model_list:
            settings.llm_config['model'] = model_list[0]
            self._reset_model_combo(model_list, model_list[0])
        else:
            current_model = settings.llm_config.get('model', 'custom-model') or 'custom-model'
            settings.llm_config['model'] = current_model
            self._reset_model_combo([current_model], current_model)

        if not settings.llm_config.get('api_url'):
            settings.llm_config['api_url'] = provider_conf.get('default_url', '')
        settings.save_settings()

    def _LLMModelChanged(self, model_name):
        if model_name:
            settings.llm_config['model'] = model_name
            settings.save_settings()

    def _LLMAutoTalkChanged(self, isChecked):
        settings.llm_config['auto_talk'] = bool(isChecked)
        settings.save_settings()

    def _reset_model_combo(self, options, current_value):
        self.LLMModelCard.comboBox.clear()
        display_list = [current_value] + [m for m in options if m != current_value]
        for item in display_list:
            self.LLMModelCard.comboBox.addItem(item, userData=item)
        self.LLMModelCard.comboBox.setCurrentText(current_value)

    def _edit_llm_api_key(self):
        current = settings.llm_config.get('api_key') or ''
        title = self.tr("编辑 API 密钥")
        w = LineEditDialog(title, current, self.window())
        if w.exec():
            settings.llm_config['api_key'] = w.nameLineEdit.text().strip()
            settings.save_settings()

    def _edit_llm_api_url(self):
        current = settings.llm_config.get('api_url') or ''
        title = self.tr("编辑 API 地址")
        w = LineEditDialog(title, current, self.window())
        if w.exec():
            settings.llm_config['api_url'] = w.nameLineEdit.text().strip()
            settings.save_settings()

    def _test_llm_connection(self):
        ok, message = LocalLLMService().quick_check()
        self.__showInfo(self.tr(message), is_error=not ok)

    def _open_developer_mode(self):
        password, ok = QInputDialog.getText(
            self.window(),
            self.tr("开发者模式"),
            self.tr("请输入密码"),
            QLineEdit.Password
        )
        if not ok:
            return
        if password != "root":
            self.__showInfo(self.tr("密码错误"), is_error=True)
            return

        msg_box = QMessageBox(self.window())
        msg_box.setWindowTitle(self.tr("开发者模式"))
        msg_box.setText(self.tr("请选择要执行的功能"))
        btn_death = msg_box.addButton(self.tr("宠物死亡测试（饱食度归零）"), QMessageBox.ActionRole)
        btn_coin = msg_box.addButton(self.tr("立即加1000金币"), QMessageBox.ActionRole)
        btn_diary = msg_box.addButton(self.tr("总结并生成当日日记"), QMessageBox.ActionRole)
        msg_box.addButton(self.tr("取消"), QMessageBox.RejectRole)
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == btn_death:
            self.dev_set_hp_zero.emit()
            self.__showInfo(self.tr("已触发：饱食度归零"))
        elif clicked == btn_coin:
            self.dev_add_coins.emit(1000)
            self.__showInfo(self.tr("已增加 1000 金币"))
        elif clicked == btn_diary:
            self.dev_generate_today_diary.emit()
            self.__showInfo(self.tr("已触发：总结并生成当日日记"))

    def _show_acknowledgement(self):
        QMessageBox.information(
            self.window(),
            self.tr("致谢"),
            self.tr("本项目使用了 DyberPet 框架，特此感谢作者 ChaozhongLiu 的贡献。代码重构基于 Fluent-Widgets，感谢作者 zhiyiYo 的指导和帮助")
        )

    def _show_update_info(self):
        QMessageBox.information(
            self.window(),
            self.tr("检查更新"),
            self.tr("当前软件已是最新版本- v.0.8.0\n本软件由猫猫桌宠基于DyberPet 开源框架开发，未经允许不得转载，二创源码、合作商用请点击帮助问题")
        )

    def _show_help_info(self):
        QMessageBox.information(
            self.window(),
            self.tr("帮助问题"),
            self.tr("问题反馈及创作合作请加微信xiaokonglong088，备注来意")
        )

    def __showInfo(self, content, is_error=False):
        if is_error:
            InfoBar.error(
                '',
                content,
                duration=4500,
                position=InfoBarPosition.BOTTOM,
                parent=self.window()
            )
        else:
            InfoBar.success(
                '',
                content,
                duration=3000,
                position=InfoBarPosition.BOTTOM,
                parent=self.window()
            )





def get_latest_version():
    url = settings.RELEASE_API
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            return True, data['tag_name']
    except Exception as e:
        return False, None

def compare_versions(local_version, github_version):
    # Remove 'v' prefix from version strings
    local_version = local_version.lstrip('v')
    github_version = github_version.lstrip('v')

    # Split version strings into their components
    local_parts = local_version.split('.')
    github_parts = github_version.split('.')

    # Convert version components to integers
    local_numbers = [int(part) for part in local_parts]
    github_numbers = [int(part) for part in github_parts]

    # Compare each component
    for local, github in zip(local_numbers, github_numbers):
        if local < github:
            return True  # User should update
        elif local > github:
            return False  # Local version is ahead

    # If all components are equal, check for additional components
    if len(local_numbers) < len(github_numbers):
        return True  # User should update
    else:
        return False  # Local version is up to date or ahead

