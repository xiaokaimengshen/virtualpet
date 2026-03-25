import sys
from sys import platform
import time
import math
import types
import random
import json
import inspect
import threading
import webbrowser
from typing import List
from pathlib import Path
import pynput.mouse as mouse

from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QTimer, QObject, QPoint, QEvent, QElapsedTimer
from PySide6.QtCore import QThread, Signal, QRectF, QRect, QSize, QPropertyAnimation, QAbstractAnimation
from PySide6.QtGui import QImage, QPixmap, QIcon, QCursor, QPainter, QFont, QFontMetrics, QAction, QBrush, QPen, QColor, QFontDatabase, QPainterPath, QRegion, QIntValidator, QDoubleValidator

from qfluentwidgets import CaptionLabel, setFont, Action #,RoundMenu
from qfluentwidgets import FluentIcon as FIF
from DyberPet.custom_widgets import SystemTray
from .custom_roundmenu import RoundMenu

from DyberPet.conf import *
from DyberPet.utils import *
from DyberPet.modules import *
from DyberPet.Accessory import MouseMoveManager
from DyberPet.custom_widgets import RoundBarBase, LevelBadge
from DyberPet.bubbleManager import BubbleManager
from DyberPet.local_llm import LocalLLMService
from DyberPet.local_chat import LocalChatWindow

# initialize settings
import DyberPet.settings as settings
settings.init()

basedir = settings.BASEDIR
configdir = settings.CONFIGDIR


# version
dyberpet_version = settings.VERSION
vf = open(os.path.join(configdir,'data/version'), 'w')
vf.write(dyberpet_version)
vf.close()

# some UI size parameters
status_margin = int(3)
statbar_h = int(20)
icons_wh = 20

# system config
sys_hp_tiers = settings.HP_TIERS 
sys_hp_interval = settings.HP_INTERVAL
sys_lvl_bar = settings.LVL_BAR
sys_pp_heart = settings.PP_HEART
sys_pp_item = settings.PP_ITEM
sys_pp_audio = settings.PP_AUDIO


# Pet HP progress bar
class DP_HpBar(QProgressBar):
    hptier_changed = Signal(int, str, name='hptier_changed')
    hp_updated = Signal(int, name='hp_updated')

    def __init__(self, *args, **kwargs):

        super(DP_HpBar, self).__init__(*args, **kwargs)

        self.setFormat('0/100')
        self.setValue(0)
        self.setAlignment(Qt.AlignCenter)
        self.hp_tiers = sys_hp_tiers #[0,50,80,100]

        self.hp_max = 100
        self.interval = 1
        self.hp_inner = 0
        self.hp_perct = 0

        # Custom colors and sizes
        self.bar_color = QColor("#FAC486")  # Fill color
        self.border_color = QColor(0, 0, 0) # Border color
        self.border_width = 1               # Border width in pixels
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Full widget rect minus border width to avoid overlap
        full_rect = QRectF(self.border_width / 2.0, self.border_width / 2.0,
                           self.width() - self.border_width, self.height() - self.border_width)
        radius = (self.height() - self.border_width) / 2.0

        # Draw the background rounded rectangle
        painter.setBrush(QBrush(QColor(240, 240, 240)))  # Light gray background
        painter.setPen(QPen(self.border_color, self.border_width))
        painter.drawRoundedRect(full_rect, radius, radius)

        # Create a clipping path for the filled progress that is inset by the border width
        clip_path = QPainterPath()
        inner_rect = full_rect.adjusted(self.border_width, self.border_width, -self.border_width, -self.border_width)
        clip_path.addRoundedRect(inner_rect, radius - self.border_width, radius - self.border_width)
        painter.setClipPath(clip_path)

        # Calculate progress rect and draw it within the clipping region
        progress_width = (self.width() - 2 * self.border_width) * self.value() / self.maximum()
        progress_rect = QRectF(self.border_width, self.border_width,
                               progress_width, self.height() - 2 * self.border_width)

        painter.setBrush(QBrush(self.bar_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(progress_rect)
        
        # Text drawing
        painter.setClipping(False)  # Disable clipping to draw text over entire bar
        text = self.format()  # Use the format string directly
        painter.setPen(QColor(0, 0, 0))  # Set text color
        font = QFont("Segoe UI", 9, QFont.Normal)
        painter.setFont(font)
        #painter.drawText(full_rect, Qt.AlignCenter, text)
        font_metrics = QFontMetrics(font)
        text_height = font_metrics.height()
        # Draw text in the calculated position
        painter.drawText(full_rect.adjusted(0, -font_metrics.descent()//2, 0, 0), Qt.AlignCenter, text)

    def init_HP(self, change_value, interval_time):
        self.hp_max = int(100*interval_time)
        self.interval = interval_time
        if change_value == -1:
            self.hp_inner = self.hp_max
            settings.pet_data.change_hp(self.hp_inner)
        else:
            self.hp_inner = change_value
        self.hp_perct = math.ceil(round(self.hp_inner/self.interval, 1))
        self.setFormat('%i/100'%self.hp_perct)
        self.setValue(self.hp_perct)
        self._onTierChanged()
        self.hp_updated.emit(self.hp_perct)

    def updateValue(self, change_value, from_mod):

        before_value = self.value()

        if from_mod == 'Scheduler':
            if settings.HP_stop:
                return
            new_hp_inner = max(self.hp_inner + change_value, 0)

        else:

            if change_value > 0:
                new_hp_inner = min(self.hp_inner + change_value*self.interval, self.hp_max)

            elif change_value < 0:
                new_hp_inner = max(self.hp_inner + change_value*self.interval, 0)

            else:
                return 0


        if new_hp_inner == self.hp_inner:
            return 0
        else:
            self.hp_inner = new_hp_inner

        new_hp_perct = math.ceil(round(self.hp_inner/self.interval, 1))
            
        if new_hp_perct == self.hp_perct:
            settings.pet_data.change_hp(self.hp_inner)
            return 0
        else:
            self.hp_perct = new_hp_perct
            self.setFormat('%i/100'%self.hp_perct)
            self.setValue(self.hp_perct)
        
        after_value = self.value()

        hp_tier = sum([int(after_value>i) for i in self.hp_tiers])

        #鍛婄煡鍔ㄧ敾妯″潡銆侀€氱煡妯″潡
        if hp_tier > settings.pet_data.hp_tier:
            self.hptier_changed.emit(hp_tier,'up')
            settings.pet_data.change_hp(self.hp_inner, hp_tier)
            self._onTierChanged()

        elif hp_tier < settings.pet_data.hp_tier:
            self.hptier_changed.emit(hp_tier,'down')
            settings.pet_data.change_hp(self.hp_inner, hp_tier)
            self._onTierChanged()
            
        else:
            settings.pet_data.change_hp(self.hp_inner) #.hp = current_value

        self.hp_updated.emit(self.hp_perct)
        return int(after_value - before_value)

    def _onTierChanged(self):
        colors = ["#f8595f", "#f8595f", "#FAC486", "#abf1b7"]
        self.bar_color = QColor(colors[settings.pet_data.hp_tier])  # Fill color
        self.update()
        



# Favorability Progress Bar
class DP_FvBar(QProgressBar):
    fvlvl_changed = Signal(int, name='fvlvl_changed')
    fv_updated = Signal(int, int, name='fv_updated')

    def __init__(self, *args, **kwargs):

        super(DP_FvBar, self).__init__(*args, **kwargs)

        # Custom colors and sizes
        self.bar_color = QColor("#F4665C")  # Fill color
        self.border_color = QColor(0, 0, 0) # Border color
        self.border_width = 1               # Border width in pixels

        self.fvlvl = 0
        self.lvl_bar = sys_lvl_bar #[20, 120, 300, 600, 1200]
        self.points_to_lvlup = self.lvl_bar[self.fvlvl]
        self.setMinimum(0)
        self.setMaximum(self.points_to_lvlup)
        self.setFormat('lv%s: 0/%s'%(int(self.fvlvl), self.points_to_lvlup))
        self.setValue(0)
        self.setAlignment(Qt.AlignCenter)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Full widget rect minus border width to avoid overlap
        full_rect = QRectF(self.border_width / 2.0, self.border_width / 2.0,
                           self.width() - self.border_width, self.height() - self.border_width)
        radius = (self.height() - self.border_width) / 2.0

        # Draw the background rounded rectangle
        painter.setBrush(QBrush(QColor(240, 240, 240)))  # Light gray background
        painter.setPen(QPen(self.border_color, self.border_width))
        painter.drawRoundedRect(full_rect, radius, radius)

        # Create a clipping path for the filled progress that is inset by the border width
        clip_path = QPainterPath()
        inner_rect = full_rect.adjusted(self.border_width, self.border_width, -self.border_width, -self.border_width)
        clip_path.addRoundedRect(inner_rect, radius - self.border_width, radius - self.border_width)
        painter.setClipPath(clip_path)

        # Calculate progress rect and draw it within the clipping region
        progress_width = (self.width() - 2 * self.border_width) * self.value() / self.maximum()
        progress_rect = QRectF(self.border_width, self.border_width,
                               progress_width, self.height() - 2 * self.border_width)

        painter.setBrush(QBrush(self.bar_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(progress_rect)
        
        # Text drawing
        painter.setClipping(False)  # Disable clipping to draw text over entire bar
        text = self.format()  # Use the format string directly
        painter.setPen(QColor(0, 0, 0))  # Set text color
        font = QFont("Segoe UI", 9, QFont.Normal)
        painter.setFont(font)
        #painter.drawText(full_rect, Qt.AlignCenter, text)
        font_metrics = QFontMetrics(font)
        text_height = font_metrics.height()
        # Draw text in the calculated position
        painter.drawText(full_rect.adjusted(0, -font_metrics.descent()//2, 0, 0), Qt.AlignCenter, text)

    def init_FV(self, fv_value, fv_lvl):
        self.fvlvl = fv_lvl
        self.points_to_lvlup = self.lvl_bar[self.fvlvl]
        self.setMinimum(0)
        self.setMaximum(self.points_to_lvlup)
        self.setFormat('lv%s: %i/%s'%(int(self.fvlvl), fv_value, self.points_to_lvlup))
        self.setValue(fv_value)
        self.fv_updated.emit(self.value(), self.fvlvl)

    def updateValue(self, change_value, from_mod):

        before_value = self.value()

        if from_mod == 'Scheduler':
            if settings.pet_data.hp_tier > 1:
                prev_value = self.value()
                current_value = self.value() + change_value #, self.maximum())
            elif settings.pet_data.hp_tier == 0 and not settings.FV_stop:
                prev_value = self.value()
                current_value = self.value() - 1
            else:
                return 0

        elif change_value != 0:
            prev_value = self.value()
            current_value = self.value() + change_value

        else:
            return 0


        if current_value < self.maximum():
            self.setValue(current_value)

            current_value = self.value()
            if current_value == prev_value:
                return 0
            else:
                self.setFormat('lv%s: %s/%s'%(int(self.fvlvl), int(current_value), int(self.maximum())))
                settings.pet_data.change_fv(current_value)
            after_value = self.value()

            self.fv_updated.emit(self.value(), self.fvlvl)
            return int(after_value - before_value)

        else:  # 好感度升级
            addedValue = self._level_up(current_value, prev_value)
            self.fv_updated.emit(self.value(), self.fvlvl)
            return addedValue

    def _level_up(self, newValue, oldValue, added=0):
        if self.fvlvl == (len(self.lvl_bar)-1):
            current_value = self.maximum()
            if current_value == oldValue:
                return 0
            self.setFormat('lv%s: %s/%s'%(int(self.fvlvl),int(current_value),self.points_to_lvlup))
            self.setValue(current_value)
            settings.pet_data.change_fv(current_value, self.fvlvl)
            #鍛婄煡鍔ㄧ敾妯″潡銆侀€氱煡妯″潡
            self.fvlvl_changed.emit(-1)
            return current_value - oldValue + added

        else:
            #after_value = newValue
            added_tmp = self.maximum() - oldValue
            newValue -= self.maximum()
            self.fvlvl += 1
            self.points_to_lvlup = self.lvl_bar[self.fvlvl]
            self.setMinimum(0)
            self.setMaximum(self.points_to_lvlup)
            self.setFormat('lv%s: %s/%s'%(int(self.fvlvl),int(newValue),self.points_to_lvlup))
            self.setValue(newValue)
            settings.pet_data.change_fv(newValue, self.fvlvl)
            #鍛婄煡鍔ㄧ敾妯″潡銆侀€氱煡妯″潡
            self.fvlvl_changed.emit(self.fvlvl)

            if newValue < self.maximum():
                return newValue + added_tmp + added
            else:
                return self._level_up(newValue, 0, added_tmp)




# Pet Object
class PetWidget(QWidget):
    setup_notification = Signal(str, str, name='setup_notification')
    setup_bubbleText = Signal(dict, int, int, name="setup_bubbleText")
    close_bubble = Signal(str, name="close_bubble")
    addItem_toInven = Signal(int, list, name='addItem_toInven')
    fvlvl_changed_main_note = Signal(int, name='fvlvl_changed_main_note')
    fvlvl_changed_main_inve = Signal(int, name='fvlvl_changed_main_inve')
    hptier_changed_main_note = Signal(int, str, name='hptier_changed_main_note')

    setup_acc = Signal(dict, int, int, name='setup_acc')
    change_note = Signal(name='change_note')
    close_all_accs = Signal(name='close_all_accs')

    move_sig = Signal(int, int, name='move_sig')
    #acc_withdrawed = Signal(str, name='acc_withdrawed')
    send_positions = Signal(list, list, name='send_positions')

    lang_changed = Signal(name='lang_changed')
    show_controlPanel = Signal(name='show_controlPanel')

    show_dashboard = Signal(name='show_dashboard')
    hp_updated = Signal(int, name='hp_updated')
    fv_updated = Signal(int, int, name='fv_updated')

    compensate_rewards = Signal(name="compensate_rewards")
    refresh_bag = Signal(name="refresh_bag")
    addCoins = Signal(int, name='addCoins')
    autofeed = Signal(name='autofeed')

    stopAllThread = Signal(name='stopAllThread')

    taskUI_Timer_update = Signal(name="taskUI_Timer_update")
    taskUI_task_end = Signal(name="taskUI_task_end")
    single_pomo_done = Signal(name="single_pomo_done")

    refresh_acts = Signal(name='refresh_acts')
    llm_reply_ready = Signal(str, name='llm_reply_ready')

    def __init__(self, parent=None, curr_pet_name=None, pets=(), screens=[]):
        """
        瀹犵墿缁勪欢
        :param parent: 鐖剁獥鍙?        :param curr_pet_name: 褰撳墠瀹犵墿鍚嶇О
        :param pets: 鍏ㄩ儴瀹犵墿鍒楄〃
        """
        super(PetWidget, self).__init__(parent) #, flags=Qt.WindowFlags())
        self.pets = settings.pets
        if curr_pet_name is None:
            self.curr_pet_name = settings.default_pet
        else:
            self.curr_pet_name = curr_pet_name
        #self.pet_conf = PetConfig()

        self.image = None
        self.tray = None

        # 榧犳爣鎷栨嫿鍒濆灞炴€?        self.is_follow_mouse = False
        self.mouse_moving = False
        self.mouse_drag_pos = self.pos()
        self.mouse_pos = [0, 0]
        self.hiding_edge = None
        self.is_hiding_mode = False
        self._hiding_frame_update = False
        # Hide mode overall scale (+10% from current value)
        self.hide_scale_ratio = 0.856548
        # Unified hide distance controls
        self.hide_visible_ratio = 0.62
        self.hide_edge_out_left_px = 12
        self.hide_edge_out_right_px = 31
        self.hide_frames = []
        self.hide_frame_bounds = []
        self.hide_bounds_global = (0, 0, 0)
        self.current_hide_frame_idx = 0
        self.hide_frame_idx = 0
        self.hide_anim_timer = QTimer(self)
        self.hide_anim_timer.setTimerType(Qt.PreciseTimer)
        self.hide_anim_timer.timeout.connect(self._tick_hiding_animation)
        self._llm_busy = False
        self._llm_prefetch_cache = {}
        self._llm_prefetch_inflight = set()
        self._llm_prefetch_order = ['idle_chat']
        self._llm_prefetch_idx = 0
        self._llm_update_busy = False
        self._reply_update_order = ['patpat', 'feed', 'pat_multi_click', 'throw_land', 'edge_hide_left', 'edge_hide_right', 'idle_chat']
        self._reply_update_idx = 0
        self.reply_update_interval_ms = int(max(60, int(getattr(settings, 'reply_update_interval_sec', 240))) * 1000)
        self.reply_preset_file = os.path.join(configdir, 'data', 'llm_reply_presets.json')
        self.reply_library = self._load_reply_library()
        self._save_reply_library()
        self.local_llm = LocalLLMService()
        self.chat_window = None
        self._interaction_since_llm = 0
        self._last_llm_reply_ts = 0.0
        self._last_user_context_text = ""
        self._last_user_context_key = ""
        self._last_user_context_log_ts = 0.0
        self._last_user_observe_speak_ts = 0.0
        self.pat_multi_click_talk_threshold = int(getattr(settings, 'pat_multi_click_talk_threshold', 12))
        self.idle_chat_interaction_threshold = int(getattr(settings, 'idle_chat_interaction_threshold', 2))
        self.idle_chat_min_gap_sec = int(getattr(settings, 'idle_chat_min_gap_sec', 55))
        idle_min = int(getattr(settings, 'idle_chat_interval_min_sec', 140))
        idle_max = int(getattr(settings, 'idle_chat_interval_max_sec', 300))
        if idle_max < idle_min:
            idle_max = idle_min
        self.idle_chat_interval_range = (idle_min, idle_max)
        self._next_idle_llm_ts = time.time() + random.randint(*self.idle_chat_interval_range)
        self._death_handled = False
        # Safe cursor defaults before _init_ui loads custom cursor assets.
        self.cursor_user = self.cursor()
        self.cursor_default = self.cursor_user
        self.cursor_clicked = self.cursor_user
        self.cursor_dragged = self.cursor_user
        self.idle_llm_timer = QTimer(self)
        self.idle_llm_timer.setTimerType(Qt.PreciseTimer)
        self.idle_llm_timer.timeout.connect(self._tick_idle_llm)
        self.llm_prefetch_timer = QTimer(self)
        self.llm_prefetch_timer.setTimerType(Qt.PreciseTimer)
        self.llm_prefetch_timer.timeout.connect(self._prefetch_llm_cache)
        self.reply_update_timer = QTimer(self)
        self.reply_update_timer.setTimerType(Qt.PreciseTimer)
        self.reply_update_timer.timeout.connect(self._update_reply_library_tick)
        self.user_observe_timer = QTimer(self)
        self.user_observe_timer.setTimerType(Qt.PreciseTimer)
        self.user_observe_timer.timeout.connect(self._observe_user_context)
        self.diary_rollover_timer = QTimer(self)
        self.diary_rollover_timer.setTimerType(Qt.PreciseTimer)
        self.diary_rollover_timer.timeout.connect(self._tick_diary_rollover)
        self.llm_reply_ready.connect(self._handle_llm_reply)

        # Record too frequent mouse clicking
        self.click_timer = QElapsedTimer()
        self.click_interval = 1000  # Max interval in ms to consider consecutive clicks
        self.click_count = 0

        # Screen info
        settings.screens = screens #[i.geometry() for i in screens]
        self.current_screen = settings.screens[0].availableGeometry() #geometry()
        settings.current_screen = settings.screens[0]
        #self.screen_geo = QDesktopWidget().availableGeometry() #screenGeometry()
        self.screen_width = self.current_screen.width() #self.screen_geo.width()
        self.screen_height = self.current_screen.height() #self.screen_geo.height()

        self._init_ui()
        self._init_widget()
        self._init_hide_frames()
        self.init_conf(self.curr_pet_name) # if curr_pet_name else self.pets[0])

        #self._set_menu(pets)
        #self._set_tray()
        self.show()

        self._setup_ui()

        # 寮€濮嬪姩鐢绘ā鍧楀拰浜や簰妯″潡
        self.threads = {}
        self.workers = {}
        self.runAnimation()
        self.runInteraction()
        self.runScheduler()
        

        # 鍒濆鍖栭噸澶嶆彁閱掍换鍔?- feature deleted
        #self.remind_window.initial_task()

        # 鍚姩瀹屾瘯10s鍚庢鏌ュソ鎰熷害绛夌骇濂栧姳琛ュ伩
        self.compensate_timer = None
        self._setup_compensate()
        self.idle_llm_timer.start(60000)
        self.llm_prefetch_timer.start(15000)
        self.reply_update_timer.start(self.reply_update_interval_ms)
        self.user_observe_timer.start(45000)
        self.diary_rollover_timer.start(120000)
        QTimer.singleShot(1200, self._warmup_llm)
        QTimer.singleShot(5000, self._observe_user_context)
        QTimer.singleShot(1500, self._auto_show_usage_guide_if_needed)

    def _setup_compensate(self):
        self._stop_compensate()
        self.compensate_timer = QTimer(singleShot=True, timeout=self._compensate_rewards)
        self.compensate_timer.start(10000)

    def _sync_dynamic_chat_settings(self):
        self.pat_multi_click_talk_threshold = int(getattr(settings, 'pat_multi_click_talk_threshold', self.pat_multi_click_talk_threshold))
        self.idle_chat_interaction_threshold = int(getattr(settings, 'idle_chat_interaction_threshold', self.idle_chat_interaction_threshold))
        self.idle_chat_min_gap_sec = int(getattr(settings, 'idle_chat_min_gap_sec', self.idle_chat_min_gap_sec))
        idle_min = int(getattr(settings, 'idle_chat_interval_min_sec', self.idle_chat_interval_range[0]))
        idle_max = int(getattr(settings, 'idle_chat_interval_max_sec', self.idle_chat_interval_range[1]))
        if idle_max < idle_min:
            idle_max = idle_min
        self.idle_chat_interval_range = (idle_min, idle_max)

        target_ms = int(max(60, int(getattr(settings, 'reply_update_interval_sec', 240))) * 1000)
        if target_ms != self.reply_update_interval_ms:
            self.reply_update_interval_ms = target_ms
            if hasattr(self, 'reply_update_timer'):
                self.reply_update_timer.start(self.reply_update_interval_ms)

    def _stop_compensate(self):
        if self.compensate_timer:
            self.compensate_timer.stop()

    def _mark_interaction(self, category=None, message=None):
        self._interaction_since_llm += 1
        if category and message:
            self._append_diary(category, message)

    def _classify_user_scene(self, app_name, win_title):
        txt = f"{app_name} {win_title}".lower()
        if any(k in txt for k in ['code', 'pycharm', 'vscode', 'studio', '开发', '.py', 'github']):
            return "写代码"
        if any(k in txt for k in ['word', 'doc', 'pdf', '文档', '论文', 'excel', 'ppt']):
            return "看文档"
        if any(k in txt for k in ['bilibili', 'youtube', '视频', 'movie', 'player']):
            return "看视频"
        if any(k in txt for k in ['wechat', 'qq', 'discord', 'telegram', '聊天', 'message']):
            return "聊天沟通"
        if any(k in txt for k in ['game', 'steam', 'unity', 'ue', '原神', '游戏']):
            return "玩游戏"
        return "忙自己的事情"

    def _observe_user_context(self):
        # Lightweight foreground sampler: only track app + title changes.
        info = get_active_window_brief()
        if not info:
            return
        app_name = (info.get('app') or '').strip()
        win_title = (info.get('title') or '').strip()
        if not win_title:
            return
        if len(win_title) > 70:
            win_title = win_title[:70] + "..."

        scene = self._classify_user_scene(app_name, win_title)
        key = f"{app_name}|{win_title}"
        if key == self._last_user_context_key:
            return
        self._last_user_context_key = key
        self._last_user_context_text = f"你大概在{scene}（{win_title}）"

        now_ts = time.time()
        if now_ts - self._last_user_context_log_ts >= 120:
            self._append_diary('user_context', self._last_user_context_text)
            self._last_user_context_log_ts = now_ts

        # Occasional caring line (low frequency, non-intrusive).
        if (not self.is_hiding_mode) and (now_ts - self._last_user_observe_speak_ts >= 420):
            if random.random() < 0.2:
                self._speak_line(f"我看到你在{scene}，我在这陪你。", from_category='chat_pet_auto')
                self._last_user_observe_speak_ts = now_ts

    def moveEvent(self, event):
        self.move_sig.emit(self.pos().x()+self.width()//2, self.pos().y()+self.height())
        self._update_pet_hitbox()

    def enterEvent(self, event):
        # Change the cursor when it enters the window
        self.setCursor(self.cursor_default)
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Restore the original cursor when it leaves the window
        self.setCursor(self.cursor_user)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """
        榧犳爣鐐瑰嚮浜嬩欢
        :param event: 浜嬩欢
        :return:
        """
        
        if event.button() == Qt.RightButton:
            # 鎵撳紑鍙抽敭鑿滃崟
            if settings.draging:
                return
            #self.setContextMenuPolicy(Qt.CustomContextMenu)
            #self.customContextMenuRequested.connect(self._show_status_menu)
            self._show_status_menu()
            
        if event.button() == Qt.LeftButton:
            if self.is_hiding_mode:
                # Exit hide mode only when user actually grabs the pet.
                self._exit_hiding_mode()
            # 宸﹂敭缁戝畾鎷栨嫿
            self.is_follow_mouse = True
            self.mouse_drag_pos = event.globalPos() - self.pos()
            
            if settings.onfloor == 0:
            # Left press activates Drag interaction
                if settings.set_fall:              
                    settings.onfloor=0
                settings.draging=1
                self.workers['Animation'].pause()
                self.workers['Interaction'].start_interact('mousedrag')
            
            # Record click
            if self.click_timer.isValid() and self.click_timer.elapsed() <= self.click_interval:
                self.click_count += 1
            else:
                self.click_count = 1
                self.click_timer.restart()
                
            event.accept()
            #self.setCursor(QCursor(Qt.ArrowCursor))
            self.setCursor(self.cursor_clicked)

    def mouseMoveEvent(self, event):
        """
        榧犳爣绉诲姩浜嬩欢, 宸﹂敭涓旂粦瀹氳窡闅? 绉诲姩绐椾綋
        :param event:
        :return:
        """
        
        if Qt.LeftButton and self.is_follow_mouse:
            self.move(event.globalPos() - self.mouse_drag_pos)

            self.mouse_moving = True
            self.setCursor(self.cursor_dragged)

            if settings.mouseposx3 == 0:
                
                settings.mouseposx1=QCursor.pos().x()
                settings.mouseposx2=settings.mouseposx1
                settings.mouseposx3=settings.mouseposx2
                settings.mouseposx4=settings.mouseposx3

                settings.mouseposy1=QCursor.pos().y()
                settings.mouseposy2=settings.mouseposy1
                settings.mouseposy3=settings.mouseposy2
                settings.mouseposy4=settings.mouseposy3
            else:
                #mouseposx5=mouseposx4
                settings.mouseposx4=settings.mouseposx3
                settings.mouseposx3=settings.mouseposx2
                settings.mouseposx2=settings.mouseposx1
                settings.mouseposx1=QCursor.pos().x()
                #mouseposy5=mouseposy4
                settings.mouseposy4=settings.mouseposy3
                settings.mouseposy3=settings.mouseposy2
                settings.mouseposy2=settings.mouseposy1
                settings.mouseposy1=QCursor.pos().y()

            if settings.onfloor == 1:
                if settings.set_fall:
                    settings.onfloor=0
                settings.draging=1
                self.workers['Animation'].pause()
                self.workers['Interaction'].start_interact('mousedrag')
            

            event.accept()
            #print(self.pos().x(), self.pos().y())

    def mouseReleaseEvent(self, event):
        """
        鏉惧紑榧犳爣鎿嶄綔
        :param event:
        :return:
        """
        if event.button()==Qt.LeftButton:

            self.is_follow_mouse = False
            #self.setCursor(QCursor(Qt.ArrowCursor))
            self.setCursor(self.cursor_default)

            #print(self.mouse_moving, settings.onfloor)
            if settings.onfloor == 1 and not self.mouse_moving:
                self.patpat()

            else:

                anim_area = QRect(self.pos() + QPoint(self.width()//2-self.label.width()//2, 
                                                      self.height()-self.label.height()), 
                                  QSize(self.label.width(), self.label.height()))
                intersected = self.current_screen.intersected(anim_area)
                area = intersected.width() * intersected.height() / self.label.width() / self.label.height()
                if area > 0.5:
                    pass
                else:
                    for screen in settings.screens:
                        if screen.geometry() == self.current_screen:
                            continue
                        intersected = screen.geometry().intersected(anim_area)
                        area_tmp = intersected.width() * intersected.height() / self.label.width() / self.label.height()
                        if area_tmp > 0.5:
                            self.switch_screen(screen)
                    

                if settings.set_fall:
                    if self._apply_edge_snap():
                        hiding_edge = self._check_hiding_edge_on_release()
                        settings.onfloor = 1
                        settings.draging = 0
                        settings.prefall = 0
                        settings.dragspeedx = 0
                        settings.dragspeedy = 0
                        settings.mouseposx1 = settings.mouseposx3 = 0
                        settings.mouseposy1 = settings.mouseposy3 = 0
                        self.workers['Interaction'].stop_interact()
                        if hiding_edge:
                            self._execute_hiding_mode(hiding_edge)
                        else:
                            self.workers['Animation'].resume()
                    else:
                        settings.onfloor=0
                        settings.draging=0
                        settings.prefall=1

                        settings.dragspeedx=(settings.mouseposx1-settings.mouseposx3)/2*settings.fixdragspeedx
                        settings.dragspeedy=(settings.mouseposy1-settings.mouseposy3)/2*settings.fixdragspeedy
                        settings.mouseposx1=settings.mouseposx3=0
                        settings.mouseposy1=settings.mouseposy3=0

                        if settings.dragspeedx > 0:
                            settings.fall_right = True
                        else:
                            settings.fall_right = False

                else:
                    settings.draging=0
                    self._move_customized(0,0)
                    settings.current_img = self.pet_conf.default.images[0]
                    self.set_img()
                    self.workers['Animation'].resume()
            self.mouse_moving = False

    def _apply_edge_snap(self):
        if not getattr(settings, 'edge_snap_enabled', settings.EDGE_SNAP_ENABLED):
            return False
        if settings.screens is None or len(settings.screens) == 0:
            return False

        threshold = max(8, int(getattr(settings, 'edge_snap_threshold', settings.EDGE_SNAP_THRESHOLD)))
        screen_left = self.current_screen.topLeft().x()
        screen_right = self.current_screen.topLeft().x() + self.screen_width
        center_x = self.pos().x() + self.width() // 2

        dist_left = abs(center_x - screen_left)
        dist_right = abs(screen_right - center_x)
        if min(dist_left, dist_right) > threshold:
            return False

        if dist_left <= dist_right:
            new_x = screen_left - self.width() // 2
        else:
            new_x = screen_right - self.width() // 2

        new_y = self.pos().y()
        new_x, new_y = self.limit_in_screen(new_x, new_y, on_action=True)
        self.move(new_x, new_y)
        return True

    def _check_hiding_edge_on_release(self):
        """Return 'left'/'right' when pet should enter edge hiding mode."""
        if not settings.set_fall:
            return None
        threshold = max(8, int(getattr(settings, 'edge_snap_threshold', settings.EDGE_SNAP_THRESHOLD)))
        center_x = self.pos().x() + self.width() // 2
        screen_left = self.current_screen.topLeft().x()
        screen_right = self.current_screen.topLeft().x() + self.screen_width
        if abs(center_x - screen_left) <= threshold:
            return 'left'
        if abs(center_x - screen_right) <= threshold:
            return 'right'
        return None

    def _init_hide_frames(self):
        self.hide_frames = []
        self.hide_frame_bounds = []
        self.hide_bounds_global = (0, 0, 0)
        kkk_dir = os.path.join(basedir, 'res', 'role', self.curr_pet_name, 'KKK')
        if not os.path.isdir(kkk_dir):
            kkk_dir = os.path.join(basedir, 'res', 'role', self.curr_pet_name, 'action')
        frame_files = sorted(
            [f for f in os.listdir(kkk_dir) if f.startswith('edge_') and f.endswith('.png')]
        )
        for fn in frame_files:
            p = os.path.join(kkk_dir, fn)
            pm = QPixmap()
            if pm.load(p):
                self.hide_frames.append(pm)
                self.hide_frame_bounds.append(self._calc_opaque_bounds(pm))

        if self.hide_frame_bounds and self.hide_frames:
            global_min = min(b[0] for b in self.hide_frame_bounds)
            global_max = max(b[1] for b in self.hide_frame_bounds)
            # frame widths are consistent for a sequence, use max as safe value
            frame_w = max(pm.width() for pm in self.hide_frames)
            opaque_w = max(1, global_max - global_min + 1)
            self.hide_bounds_global = (global_min, global_max, opaque_w, frame_w)

    def _calc_opaque_bounds(self, pm: QPixmap):
        """Return (min_x, max_x, opaque_w) for alpha>0 pixels in source frame."""
        img = pm.toImage().convertToFormat(QImage.Format_RGBA8888)
        w = img.width()
        h = img.height()
        min_x = w
        max_x = -1
        for x in range(w):
            opaque_col = False
            for y in range(h):
                if img.pixelColor(x, y).alpha() > 0:
                    opaque_col = True
                    break
            if opaque_col:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
        if max_x < min_x:
            return (0, w - 1, w)
        return (min_x, max_x, max_x - min_x + 1)

    def _start_hiding_animation(self):
        if not self.hide_frames:
            self._init_hide_frames()
        self.hide_frame_idx = 0
        self.current_hide_frame_idx = 0
        if self.hide_frames:
            settings.previous_img = settings.current_img
            settings.current_img = self.hide_frames[0]
            self._hiding_frame_update = True
            self.set_img()
            self._hiding_frame_update = False
            self.hide_frame_idx = 1 % len(self.hide_frames)
        if self.hide_anim_timer.isActive():
            self.hide_anim_timer.stop()
        self.hide_anim_timer.start(80)

    def _stop_hiding_animation(self):
        if self.hide_anim_timer.isActive():
            self.hide_anim_timer.stop()

    def _tick_hiding_animation(self):
        if not self.is_hiding_mode or not self.hide_frames:
            return
        settings.previous_img = settings.current_img
        settings.current_img = self.hide_frames[self.hide_frame_idx]
        self.current_hide_frame_idx = self.hide_frame_idx
        self.hide_frame_idx = (self.hide_frame_idx + 1) % len(self.hide_frames)
        self._hiding_frame_update = True
        self.set_img()
        self._hiding_frame_update = False
        self._reposition_hiding_to_edge()

    def _calc_hide_visible_width(self, opaque_width_scaled):
        # Adaptive visible width based on rendered opaque width.
        visible_width = int(opaque_width_scaled * self.hide_visible_ratio)
        visible_width = max(24, visible_width)
        visible_width = min(max(24, int(opaque_width_scaled) - 2), visible_width)
        return visible_width

    def _reposition_hiding_to_edge(self):
        if not self.is_hiding_mode or self.hiding_edge not in ('left', 'right'):
            return

        screen_left = self.current_screen.topLeft().x()
        screen_right = self.current_screen.topLeft().x() + self.screen_width
        if not self.hide_frames:
            return

        # Use global bounds for the whole hide sequence.
        if len(self.hide_bounds_global) != 4:
            return
        min_x, max_x, opaque_w, frame_w = self.hide_bounds_global
        scale_factor = settings.tunable_scale * self.hide_scale_ratio

        label_w = self.label.width()
        # Label is centered in main widget, compute horizontal margin dynamically.
        margin_x = (self.width() - label_w) / 2.0

        pad_left = min_x * scale_factor
        pad_right = (frame_w - (max_x + 1)) * scale_factor
        opaque_w_scaled = opaque_w * scale_factor
        visible_width = self._calc_hide_visible_width(opaque_w_scaled)

        if self.hiding_edge == 'left':
            # Mirror uses original right pad as the visual left pad.
            img_left = screen_left - (opaque_w_scaled - visible_width) - pad_right + self.hide_edge_out_left_px
        else:
            img_left = screen_right - visible_width - pad_left - self.hide_edge_out_right_px

        new_x = int(round(img_left - margin_x))
        new_y = max(
            self.current_screen.topLeft().y() + self.label.height() // 2 - self.height(),
            min(self.pos().y(), self.floor_pos + settings.current_anchor[1])
        )
        self.move(new_x, new_y)

    def _execute_hiding_mode(self, hiding_edge):
        settings.fall_right = (hiding_edge == 'right')
        self.hiding_edge = hiding_edge
        self.is_hiding_mode = True
        # Lock to dedicated edge animation so normal random/fall actions cannot override.
        self.workers['Interaction'].stop_interact()
        self.workers['Animation'].pause()
        self._start_hiding_animation()
        self._reposition_hiding_to_edge()
        # Side-edge special chat, e.g. "I'll stay quiet here."
        self._trigger_llm_interaction_reply('edge_hide', hiding_edge)

    def _exit_hiding_mode(self):
        if not self.is_hiding_mode:
            return
        self._stop_hiding_animation()
        screen_left = self.current_screen.topLeft().x()
        screen_right = self.current_screen.topLeft().x() + self.screen_width
        if self.hiding_edge == 'left':
            new_x = screen_left - self.width() // 2
        else:
            new_x = screen_right - self.width() // 2
        new_y = max(
            self.current_screen.topLeft().y() + self.label.height() // 2 - self.height(),
            min(self.pos().y(), self.floor_pos + settings.current_anchor[1])
        )
        self.move(new_x, new_y)
        self.hiding_edge = None
        self.is_hiding_mode = False
        self.workers['Animation'].resume()
        self.workers['Interaction'].start_interact('animat', 'onfloor')


    def _init_widget(self) -> None:
        """
        鍒濆鍖栫獥浣? 鏃犺竟妗嗗崐閫忔槑绐楀彛
        :return:
        """
        if settings.on_top_hint:
            if platform == 'win32':
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow | Qt.NoDropShadowWindowHint)
            else:
                # SubWindow not work in MacOS
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        else:
            if platform == 'win32':
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow | Qt.NoDropShadowWindowHint)
            else:
                # SubWindow not work in MacOS
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)

        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.repaint()
        # 鏄惁璺熼殢榧犳爣
        self.is_follow_mouse = False
        self.mouse_drag_pos = self.pos()

    def ontop_update(self):
        if settings.on_top_hint:
            if platform == 'win32':
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow | Qt.NoDropShadowWindowHint)
            else:
                # SubWindow not work in MacOS
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        else:
            if platform == 'win32':
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow | Qt.NoDropShadowWindowHint)
            else:
                # SubWindow not work in MacOS
                self.setWindowFlags(Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
                
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.show()


    def _init_ui(self):
        # The Character ----------------------------------------------------------------------------
        self.label = QLabel(self)
        self.label.setScaledContents(True)
        self.label.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.label.installEventFilter(self)
        #self.label.setStyleSheet("border : 2px solid blue")

        # system animations
        self.sys_src = _load_all_pic('sys')
        self.sys_conf = PetConfig.init_sys(self.sys_src) 
        # ------------------------------------------------------------------------------------------

        # Hover Timer --------------------------------------------------------
        self.status_frame = QFrame()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0,0,0,0)
        vbox.setSpacing(0)

        # 鐣寗鏃堕挓
        h_box3 = QHBoxLayout()
        h_box3.setContentsMargins(0,0,0,0)
        h_box3.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.tomatoicon = QLabel(self)
        self.tomatoicon.setFixedSize(statbar_h,statbar_h)
        image = QPixmap()
        image.load(os.path.join(basedir, 'res/icons/Tomato_icon.png'))
        self.tomatoicon.setScaledContents(True)
        self.tomatoicon.setPixmap(image)
        self.tomatoicon.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        h_box3.addWidget(self.tomatoicon)
        self.tomato_time = RoundBarBase(fill_color="#ef4e50", parent=self) #QProgressBar(self, minimum=0, maximum=25, objectName='PetTM')
        self.tomato_time.setFormat('')
        self.tomato_time.setValue(25)
        self.tomato_time.setAlignment(Qt.AlignCenter)
        self.tomato_time.hide()
        self.tomatoicon.hide()
        h_box3.addWidget(self.tomato_time)

        # 涓撴敞鏃堕棿
        h_box4 = QHBoxLayout()
        h_box4.setContentsMargins(0,status_margin,0,0)
        h_box4.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.focusicon = QLabel(self)
        self.focusicon.setFixedSize(statbar_h,statbar_h)
        image = QPixmap()
        image.load(os.path.join(basedir, 'res/icons/Timer_icon.png'))
        self.focusicon.setScaledContents(True)
        self.focusicon.setPixmap(image)
        self.focusicon.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        h_box4.addWidget(self.focusicon)
        self.focus_time = RoundBarBase(fill_color="#47c0d2", parent=self) #QProgressBar(self, minimum=0, maximum=0, objectName='PetFC')
        self.focus_time.setFormat('')
        self.focus_time.setValue(0)
        self.focus_time.setAlignment(Qt.AlignCenter)
        self.focus_time.hide()
        self.focusicon.hide()
        h_box4.addWidget(self.focus_time)

        vbox.addStretch()
        vbox.addLayout(h_box3)
        vbox.addLayout(h_box4)

        self.status_frame.setLayout(vbox)
        #self.status_frame.setStyleSheet("border : 2px solid blue")
        self.status_frame.setContentsMargins(0,0,0,0)
        #self.status_box.addWidget(self.status_frame)
        #self.status_frame.hide()
        # ------------------------------------------------------------

        #Layout_1 ----------------------------------------------------
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)

        self.petlayout = QVBoxLayout()
        self.petlayout.addWidget(self.status_frame)

        image_hbox = QHBoxLayout()
        image_hbox.setContentsMargins(0,0,0,0)
        image_hbox.addStretch()
        image_hbox.addWidget(self.label, Qt.AlignBottom | Qt.AlignHCenter)
        image_hbox.addStretch()

        self.petlayout.addLayout(image_hbox, Qt.AlignBottom | Qt.AlignHCenter)
        self.petlayout.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.petlayout.setContentsMargins(0,0,0,0)
        self.layout.addLayout(self.petlayout, Qt.AlignBottom | Qt.AlignHCenter)
        # ------------------------------------------------------------

        self.setLayout(self.layout)
        # ------------------------------------------------------------


        # 鍒濆鍖栬儗鍖?        #self.items_data = ItemData(HUNGERSTR=settings.HUNGERSTR, FAVORSTR=settings.FAVORSTR)
        settings.items_data = ItemData(HUNGERSTR=settings.HUNGERSTR, FAVORSTR=settings.FAVORSTR)
        #self._init_Inventory()
        #self.showing_comp = 0

        # Custom cursor setup
        self.cursor_user = self.cursor()
        system_cursor_size = 32
        if os.path.exists(os.path.join(basedir, 'res/icons/cursor_default.png')):
            self.cursor_default = QCursor(QPixmap("res/icons/cursor_default.png").scaled(system_cursor_size, system_cursor_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.cursor_default = self.cursor_user
        if os.path.exists(os.path.join(basedir, 'res/icons/cursor_clicked.png')):
            self.cursor_clicked = QCursor(QPixmap("res/icons/cursor_clicked.png").scaled(system_cursor_size, system_cursor_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.cursor_clicked = self.cursor_user
        if os.path.exists(os.path.join(basedir, 'res/icons/cursor_dragged.png')):
            self.cursor_dragged = QCursor(QPixmap("res/icons/cursor_dragged.png").scaled(system_cursor_size, system_cursor_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.cursor_dragged = self.cursor_user

    '''
    def _init_Inventory(self):
        self.items_data = ItemData(HUNGERSTR=settings.HUNGERSTR, FAVORSTR=settings.FAVORSTR)
        self.inventory_window = Inventory(self.items_data)
        self.inventory_window.close_inventory.connect(self.show_inventory)
        self.inventory_window.use_item_inven.connect(self.use_item)
        self.inventory_window.item_note.connect(self.register_notification)
        self.inventory_window.item_anim.connect(self.item_drop_anim)
        self.addItem_toInven.connect(self.inventory_window.add_items)
        self.acc_withdrawed.connect(self.inventory_window.acc_withdrawed)
        self.fvlvl_changed_main_inve.connect(self.inventory_window.fvchange)
    '''


    def _set_menu(self, pets=()):
        """
        Option Menu
        """
        #menu = RoundMenu(self.tr("More Options"), self)
        #menu.setIcon(FIF.MENU)

        # Select action
        self.act_menu = RoundMenu(self.tr("选择动作"))
        self.act_menu.setIcon(QIcon(os.path.join(basedir,'res/icons/jump.svg')))

        if platform == 'win32':
            self.start_follow_mouse = Action(QIcon(os.path.join(basedir,'res/icons/cursor.svg')),
                                            self.tr('跟随鼠标'),
                                            triggered = self.follow_mouse_act)
            self.act_menu.addAction(self.start_follow_mouse)
            self.act_menu.addSeparator()

        acts_config = settings.act_data.allAct_params[settings.petname]
        self.select_acts = [ _build_act(k, self.act_menu, self._show_act) for k,v in acts_config.items() if v['unlocked']]
        if self.select_acts:
            self.act_menu.addActions(self.select_acts)

        #menu.addMenu(self.act_menu)


        # Launch pet/partner
        self.companion_menu = RoundMenu(self.tr("召唤伙伴"))
        self.companion_menu.setIcon(QIcon(os.path.join(basedir,'res/icons/partner.svg')))

        add_acts = [_build_act(name, self.companion_menu, self._add_pet) for name in pets]
        self.companion_menu.addActions(add_acts)

        #menu.addMenu(self.companion_menu)
        #menu.addSeparator()

        # Change Character
        self.change_menu = RoundMenu(self.tr("更换角色"))
        self.change_menu.setIcon(QIcon(os.path.join(basedir,'res/icons/system/character.svg')))
        change_acts = [_build_act(name, self.change_menu, self._change_pet) for name in pets]
        self.change_menu.addActions(change_acts)
        #menu.addMenu(self.change_menu)

        # Drop on/off
        '''
        if settings.set_fall == 1:
            self.switch_fall = Action(QIcon(os.path.join(basedir,'res/icons/on.svg')),
                                      self.tr('鍏佽涓嬭惤'), menu)
        else:
            self.switch_fall = Action(QIcon(os.path.join(basedir,'res/icons/off.svg')),
                                      self.tr("Don't Drop"), menu)
        self.switch_fall.triggered.connect(self.fall_onoff)
        '''
        #menu.addAction(self.switch_fall)

        
        # Visit website - feature deprecated
        '''
        web_file = os.path.join(basedir, 'res/role/sys/webs.json')
        if os.path.isfile(web_file):
            web_dict = json.load(open(web_file, 'r', encoding='utf-8-sig'))

            self.web_menu = RoundMenu(self.tr("Website"), menu)
            self.web_menu.setIcon(QIcon(os.path.join(basedir,'res/icons/website.svg')))

            web_acts = [_build_act_param(name, web_dict[name], self.web_menu, self.open_web) for name in web_dict]
            self.web_menu.addActions(web_acts)
            menu.addMenu(self.web_menu)
        '''
            
        #menu.addSeparator()
        #self.menu = menu
        #self.menu.addAction(Action(FIF.POWER_BUTTON, self.tr('Exit'), triggered=self.quit))


    def _update_fvlock(self):

        # Update selectable animations
        acts_config = settings.act_data.allAct_params[settings.petname]
        for act_name, act_conf in acts_config.items():
            if act_conf['unlocked']:
                if act_name not in [acti.text() for acti in self.select_acts]:
                    new_act = _build_act(act_name, self.act_menu, self._show_act)
                    self.act_menu.addAction(new_act)
                    self.select_acts.append(new_act)
            else:
                if act_name in [acti.text() for acti in self.select_acts]:
                    act_index = [acti.text() for acti in self.select_acts].index(act_name)
                    self.act_menu.removeAction(self.select_acts[act_index])
                    self.select_acts.remove(self.select_acts[act_index])


    def _set_Statusmenu(self):

        # Character Name
        self.statusTitle = QWidget()
        hboxTitle = QHBoxLayout(self.statusTitle)
        hboxTitle.setContentsMargins(0,0,0,0)
        self.nameLabel = CaptionLabel(self.curr_pet_name, self)
        setFont(self.nameLabel, 14, QFont.DemiBold)
        #self.nameLabel.setFixedWidth(75)

        daysText = self.tr("（已陪伴 ") + str(settings.pet_data.days) + \
                   self.tr(" 天）")
        self.daysLabel = CaptionLabel(daysText, self)
        setFont(self.daysLabel, 14, QFont.Normal)

        hboxTitle.addStretch(1)
        hboxTitle.addWidget(self.nameLabel, Qt.AlignLeft | Qt.AlignVCenter)
        hboxTitle.addStretch(1)
        hboxTitle.addWidget(self.daysLabel, Qt.AlignRight | Qt.AlignVCenter)
        #hboxTitle.addStretch(1)
        self.statusTitle.setFixedSize(225, 25)

        # # Status Title
        # hp_tier = settings.pet_data.hp_tier
        # statusText = self.tr("Status: ") + f"{settings.TIER_NAMES[hp_tier]}"
        # self.statLabel = CaptionLabel(statusText, self)
        # setFont(self.statLabel, 14, QFont.Normal)

        # Level Badge
        lvlWidget = QWidget()
        h_box0 = QHBoxLayout(lvlWidget)
        h_box0.setContentsMargins(0,0,0,0)
        h_box0.setSpacing(5)
        h_box0.setAlignment(Qt.AlignCenter)
        lvlLable = CaptionLabel(self.tr("等级"))
        setFont(lvlLable, 13, QFont.Normal)
        lvlLable.adjustSize()
        lvlLable.setFixedSize(43, lvlLable.height())
        self.lvl_badge = LevelBadge(settings.pet_data.fv_lvl)
        h_box0.addWidget(lvlLable)
        #h_box0.addStretch(1)
        h_box0.addWidget(self.lvl_badge)
        h_box0.addStretch(1)
        lvlWidget.setFixedSize(250, 25)

        # Hunger status
        hpWidget = QWidget()
        h_box1 = QHBoxLayout(hpWidget)
        h_box1.setContentsMargins(0,0,0,0) #status_margin,0,0)
        h_box1.setSpacing(5)
        h_box1.setAlignment(Qt.AlignCenter) #AlignBottom | Qt.AlignHCenter)
        hpLable = CaptionLabel(self.tr("饱食度"))
        setFont(hpLable, 13, QFont.Normal)
        hpLable.adjustSize()
        hpLable.setFixedSize(43, hpLable.height())
        self.hpicon = QLabel(self)
        self.hpicon.setFixedSize(icons_wh,icons_wh)
        image = QPixmap()
        image.load(os.path.join(basedir, 'res/icons/HP_icon.png'))
        self.hpicon.setScaledContents(True)
        self.hpicon.setPixmap(image)
        self.hpicon.setAlignment(Qt.AlignCenter) #AlignBottom | Qt.AlignRight)
        h_box1.addWidget(hpLable)
        h_box1.addStretch(1)
        h_box1.addWidget(self.hpicon)
        #h_box1.addStretch(1)
        self.pet_hp = DP_HpBar(self, minimum=0, maximum=100, objectName='PetHP')
        self.pet_hp.hp_updated.connect(self._hp_updated)
        h_box1.addWidget(self.pet_hp)
        h_box1.addStretch(1)

        # favor status
        fvWidget = QWidget()
        h_box2 = QHBoxLayout(fvWidget)
        h_box2.setContentsMargins(0,0,0,0) #status_margin,0,0)
        h_box2.setSpacing(5)
        h_box2.setAlignment(Qt.AlignCenter) #Qt.AlignBottom | Qt.AlignHCenter)
        fvLable = CaptionLabel(self.tr("好感度"))
        setFont(fvLable, 13, QFont.Normal)
        fvLable.adjustSize()
        fvLable.setFixedSize(43, fvLable.height())
        self.emicon = QLabel(self)
        self.emicon.setFixedSize(icons_wh,icons_wh)
        image = QPixmap()
        image.load(os.path.join(basedir, 'res/icons/Fv_icon.png'))
        self.emicon.setScaledContents(True)
        self.emicon.setPixmap(image)
        #self.emicon.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        h_box2.addWidget(fvLable, Qt.AlignHCenter | Qt.AlignTop)
        h_box2.addStretch(1)
        h_box2.addWidget(self.emicon)
        self.pet_fv = DP_FvBar(self, minimum=0, maximum=100, objectName='PetEM')
        self.pet_fv.fv_updated.connect(self._fv_updated)

        self.pet_hp.hptier_changed.connect(self.hpchange)
        self.pet_fv.fvlvl_changed.connect(self.fvchange)
        h_box2.addWidget(self.pet_fv)
        h_box2.addStretch(1)

        self.pet_hp.init_HP(settings.pet_data.hp, sys_hp_interval) #2)
        self.pet_fv.init_FV(settings.pet_data.fv, settings.pet_data.fv_lvl)
        self.pet_hp.setFixedSize(145, 15)
        self.pet_fv.setFixedSize(145, 15)

        # Status Widget
        self.statusWidget = QWidget()
        StatVbox = QVBoxLayout(self.statusWidget)
        StatVbox.setContentsMargins(0,5,30,10)
        StatVbox.setSpacing(5)
        
        #StatVbox.addWidget(self.statusTitle, Qt.AlignVCenter)
        StatVbox.addStretch(1)
        #StatVbox.addWidget(self.daysLabel)
        StatVbox.addWidget(hpWidget, Qt.AlignLeft | Qt.AlignVCenter)
        StatVbox.addWidget(fvWidget, Qt.AlignLeft | Qt.AlignVCenter)
        StatVbox.addStretch(1)
        #statusWidget.setLayout(StatVbox)
        #statusWidget.setContentsMargins(0,0,0,0)
        self.statusWidget.setFixedSize(250, 70)
        
        self.StatMenu = RoundMenu(parent=self)
        self.StatMenu.addWidget(self.statusTitle, selectable=False)
        self.StatMenu.addSeparator()
        #self.StatMenu.addWidget(self.statLabel, selectable=False)
        self.StatMenu.addWidget(lvlWidget, selectable=False)
        self.StatMenu.addWidget(self.statusWidget, selectable=False)
        #self.StatMenu.addWidget(fvbar, selectable=False)
        self.StatMenu.addSeparator()

        #self.StatMenu.addMenu(self.menu)
        self.StatMenu.addActions([
            #Action(FIF.MENU, self.tr('More Options'), triggered=self._show_right_menu),
            Action(QIcon(os.path.join(basedir,'res/icons/dashboard.svg')), self.tr('角色面板'), triggered=self._show_dashboard),
            Action(QIcon(os.path.join(basedir,'res/icons/SystemPanel.png')), self.tr('系统'), triggered=self._show_controlPanel),
        ])
        self.chat_menu = RoundMenu(self.tr("互动"))
        self.chat_menu.setIcon(QIcon(os.path.join(basedir, 'res/icons/system/ai.svg')))
        self.chat_menu.addActions([
            Action(QIcon(os.path.join(basedir, 'res/icons/system/ai.svg')), self.tr('聊天'), triggered=self._show_chat_window),
            Action(QIcon(os.path.join(basedir, 'res/icons/task.svg')), self.tr('游戏'), triggered=self._show_game_dev_tip),
        ])
        self.StatMenu.addSeparator()

        self.StatMenu.addMenu(self.chat_menu)
        self.StatMenu.addMenu(self.act_menu)
        self.StatMenu.addMenu(self.companion_menu)
        self.StatMenu.addMenu(self.change_menu)
        self.StatMenu.addAction(
            Action(QIcon(os.path.join(basedir, 'res/icons/question.svg')), self.tr('使用说明'), triggered=self._show_usage_guide)
        )
        self.StatMenu.addSeparator()
        
        self.StatMenu.addActions([
            Action(FIF.POWER_BUTTON, self.tr('退出'), triggered=self.quit),
        ])


    # def _update_statusTitle(self, hp_tier):
    #     statusText = self.tr("Status: ") + f"{settings.TIER_NAMES[hp_tier]}"
    #     self.statLabel.setText(statusText)


    def _show_status_menu(self):
        """
        灞曠ず鍙抽敭鑿滃崟
        :return:
        """
        # 鍏夋爣浣嶇疆寮瑰嚭鑿滃崟
        self.StatMenu.popup(QCursor.pos()-QPoint(0, self.StatMenu.height()-20))

    # Backward-compatible alias for old typo method name.
    def _show_Staus_menu(self):
        self._show_status_menu()

    def _add_pet(self, pet_name: str):
        pet_acc = {'name':'pet', 'pet_name':pet_name}
        #self.setup_acc.emit(pet_acc, int(self.current_screen.topLeft().x() + random.uniform(0.4,0.7)*self.screen_width), self.pos().y())
        # To accomodate any subpet that always follows main, change the position to top middle pos of pet
        self.setup_acc.emit(pet_acc, int( self.pos().x() + self.width()/2 ), self.pos().y())

    def open_web(self, web_address):
        try:
            webbrowser.open(web_address)
        except:
            return
    '''
    def freeze_pet(self):
        """stop all thread, function for save import"""
        self.stop_thread('Animation')
        self.stop_thread('Interaction')
        self.stop_thread('Scheduler')
        #del self.threads, self.workers
    '''
    
    def refresh_pet(self):
        # stop animation thread and start again
        self.stop_thread('Animation')
        self.stop_thread('Interaction')

        # Change status
        self.pet_hp.init_HP(settings.pet_data.hp, sys_hp_interval) #2)
        self.pet_fv.init_FV(settings.pet_data.fv, settings.pet_data.fv_lvl)

        # Change status related behavior
        #self.workers['Animation'].hpchange(settings.pet_data.hp_tier, None)
        #self.workers['Animation'].fvchange(settings.pet_data.fv_lvl)

        # Animation config data update
        settings.act_data._pet_refreshed(settings.pet_data.fv_lvl)
        self.refresh_acts.emit()

        # cancel default animation if any
        '''
        defaul_act = settings.defaultAct[self.curr_pet_name]
        if defaul_act is not None:
            self._set_defaultAct(self, defaul_act)
        self._update_fvlock()
        # add default animation back
        if defaul_act in [acti.text() for acti in self.defaultAct_menu.actions()]:
            self._set_defaultAct(self, defaul_act)
        '''

        # Update BackPack
        #self._init_Inventory()
        self.refresh_bag.emit()
        self._set_menu(self.pets)
        self._set_Statusmenu()
        self._set_tray()

        # restart animation and interaction
        self.runAnimation()
        self.runInteraction()
        
        # restore data system
        settings.pet_data.frozen_data = False

        # Compensate items if any
        self._setup_compensate()
    

    def _change_pet(self, pet_name: str) -> None:
        """
        鏀瑰彉瀹犵墿
        :param pet_name: 瀹犵墿鍚嶇О
        :return:
        """
        if self.curr_pet_name == pet_name:
            return
        if self.is_hiding_mode:
            self._stop_hiding_animation()
            self.is_hiding_mode = False
            self.hiding_edge = None
        
        # close all accessory widgets (subpet, accessory animation, etc.)
        self.close_all_accs.emit()

        # stop animation thread and start again
        self.stop_thread('Animation')
        self.stop_thread('Interaction')

        # reload pet data
        settings.pet_data._change_pet(pet_name)

        # reload new pet
        self.init_conf(pet_name)

        # Change status
        self.pet_hp.init_HP(settings.pet_data.hp, sys_hp_interval) #2)
        self.pet_fv.init_FV(settings.pet_data.fv, settings.pet_data.fv_lvl)

        # Change status related behavior
        #self.workers['Animation'].hpchange(settings.pet_data.hp_tier, None)
        #self.workers['Animation'].fvchange(settings.pet_data.fv_lvl)

        # Update Backpack
        #self._init_Inventory()
        self.refresh_bag.emit()
        self.refresh_acts.emit()

        self.change_note.emit()
        self.repaint()
        self._setup_ui()

        self.runAnimation()
        self.runInteraction()

        self.workers['Scheduler'].send_greeting()
        # Compensate items if any
        self._setup_compensate()
        # Due to Qt internal behavior, sometimes has to manually correct the position back
        pos_x, pos_y = self.pos().x(), self.pos().y()
        QTimer.singleShot(10, lambda: self.move(pos_x, pos_y))

    def init_conf(self, pet_name: str) -> None:
        """
        鍒濆鍖栧疇鐗╃獥鍙ｉ厤缃?        :param pet_name: 瀹犵墿鍚嶇О
        :return:
        """
        self.curr_pet_name = pet_name
        settings.petname = pet_name
        settings.tunable_scale = settings.scale_dict.get(pet_name, 1.0)
        pic_dict = _load_all_pic(pet_name)
        self.pet_conf = PetConfig.init_config(self.curr_pet_name, pic_dict) #settings.size_factor)
        
        self.margin_value = 0 #0.1 * max(self.pet_conf.width, self.pet_conf.height) # 鐢ㄤ簬灏唚idgets璋冩暣鍒板悎閫傜殑澶у皬
        # Add customized animation
        settings.act_data.init_actData(pet_name, settings.pet_data.hp_tier, settings.pet_data.fv_lvl)
        self._load_custom_anim()
        settings.pet_conf = self.pet_conf

        # Update coin name and image according to the pet config
        if self.pet_conf.coin_config:
            coin_config = self.pet_conf.coin_config.copy()
            if not coin_config['image']:
                coin_config['image'] = settings.items_data.default_coin['image']
            settings.items_data.coin = coin_config
        else:
            settings.items_data.coin = settings.items_data.default_coin.copy()

        # Init bubble behavior manager
        self.bubble_manager = BubbleManager()
        self.bubble_manager.register_bubble.connect(self.register_bubbleText)
        self._init_hide_frames()

        self._set_menu(self.pets)
        self._set_Statusmenu()
        self._set_tray()


    def _load_custom_anim(self):
        acts_conf = settings.act_data.allAct_params[settings.petname]
        for act_name, act_conf in acts_conf.items():
            if act_conf['act_type'] == 'customized' and act_name not in self.pet_conf.custom_act:
                # generate new Act objects for cutomized animation
                acts = []
                for act in act_conf.get('act_list', []):
                    acts.append(self._prepare_act_obj(act))
                accs = []
                for act in act_conf.get('acc_list', []):
                    accs.append(self._prepare_act_obj(act))
                # save the new animation config with same format as self.pet_conf.accessory_act
                self.pet_conf.custom_act[act_name] = {"act_list": acts,
                                                      "acc_list": accs,
                                                      "anchor": act_conf.get('anchor_list',[]),
                                                      "act_type": act_conf['status_type']}

    def _prepare_act_obj(self, actobj):
        
        # if this act is a skipping act e.g. [60, 20]
        if len(actobj) == 2:
            return actobj
        else:
            act_conf_name = actobj[0]
            act_idx_start = actobj[1]
            act_idx_end = actobj[2]+1
            act_repeat_num = actobj[3]
            new_actobj = self.pet_conf.act_dict[act_conf_name].customized_copy(act_idx_start, act_idx_end, act_repeat_num)
            return new_actobj

    def updateList(self):
        self.workers['Animation'].update_prob()

    def _addNewAct(self, act_name):
        acts_config = settings.act_data.allAct_params[settings.petname]
        act_conf = acts_config[act_name]

        # Add to pet_conf
        acts = []
        for act in act_conf.get('act_list', []):
            acts.append(self._prepare_act_obj(act))
        accs = []
        for act in act_conf.get('acc_list', []):
            accs.append(self._prepare_act_obj(act))
        self.pet_conf.custom_act[act_name] = {"act_list": acts,
                                                "acc_list": accs,
                                                "anchor": act_conf.get('anchor_list',[]),
                                                "act_type": act_conf['status_type']}
        # update random action prob
        self.updateList()
        # Add to menu
        if act_conf['unlocked']:
            select_act = _build_act(act_name, self.act_menu, self._show_act)
            self.select_acts.append(select_act)
            self.act_menu.addAction(select_act)
    
    def _deleteAct(self, act_name):
        # delete from self.pet_config
        self.pet_conf.custom_act.pop(act_name)
        # update random action prob
        self.updateList()

        # delete from menu
        act_index = [acti.text() for acti in self.select_acts].index(act_name)
        self.act_menu.removeAction(self.select_acts[act_index])
        self.select_acts.remove(self.select_acts[act_index])


    def _setup_ui(self):

        #bar_width = int(max(100*settings.size_factor, 0.5*self.pet_conf.width))
        bar_width = int(max(100, 0.5*self.pet_conf.width))
        bar_width = int(min(200, bar_width))
        self.tomato_time.setFixedSize(bar_width, statbar_h-5)
        self.focus_time.setFixedSize(bar_width, statbar_h-5)

        self.reset_size(setImg=False)

        settings.previous_img = settings.current_img
        settings.current_img = self.pet_conf.default.images[0] #list(pic_dict.values())[0]
        settings.previous_anchor = [0, 0] #settings.current_anchor
        settings.current_anchor = [int(i*settings.tunable_scale) for i in self.pet_conf.default.anchor]
        self.set_img()
        self.border = self.pet_conf.width/2

        
        # 鍒濆浣嶇疆
        #screen_geo = QDesktopWidget().availableGeometry() #QDesktopWidget().screenGeometry()
        screen_width = self.screen_width #screen_geo.width()
        work_height = self.screen_height #screen_geo.height()
        x = self.current_screen.topLeft().x() + int(screen_width*0.8) - self.width()//2
        y = self.current_screen.topLeft().y() + work_height - self.height()
        self.move(x,y)
        if settings.previous_anchor != settings.current_anchor:
            self.move(self.pos().x() - settings.previous_anchor[0] + settings.current_anchor[0],
                      self.pos().y() - settings.previous_anchor[1] + settings.current_anchor[1])
            #self.move(self.pos().x()-settings.previous_anchor[0]*settings.tunable_scale+settings.current_anchor[0]*settings.tunable_scale,
            #          self.pos().y()-settings.previous_anchor[1]*settings.tunable_scale+settings.current_anchor[1]*settings.tunable_scale)

    '''
    def eventFilter(self, object, event):
        return
    
        if event.type() == QEvent.Enter:
            self.status_frame.show()
            return True
        elif event.type() == QEvent.Leave:
            self.status_frame.hide()
        return False
    '''

    def _set_tray(self) -> None:
        """
        璁剧疆鏈€灏忓寲鎵樼洏
        :return:
        """
        if self.tray is None:
            self.tray = SystemTray(self.StatMenu, self) #QSystemTrayIcon(self)
            self.tray.setIcon(QIcon(os.path.join(basedir, 'res/icons/icon.png')))
            self.tray.show()
        else:
            self.tray.setMenu(self.StatMenu)
            self.tray.show()

    def reset_size(self, setImg=True):
        #self.setFixedSize((max(self.pet_hp.width()+statbar_h,self.pet_conf.width)+self.margin_value)*max(1.0,settings.tunable_scale),
        #                  (self.margin_value+4*statbar_h+self.pet_conf.height)*max(1.0, settings.tunable_scale))
        self.setFixedSize( int(max(self.tomato_time.width()+statbar_h,self.pet_conf.width*settings.tunable_scale)),
                           int(2*statbar_h+self.pet_conf.height*settings.tunable_scale)
                         )

        #self.label.setFixedWidth(self.width())

        # 鍒濆浣嶇疆
        #screen_geo = QDesktopWidget().availableGeometry() #QDesktopWidget().screenGeometry()
        screen_width = self.screen_width #screen_geo.width()
        work_height = self.screen_height #screen_geo.height()
        x = self.pos().x() + settings.current_anchor[0]
        if settings.set_fall:
            y = self.current_screen.topLeft().y() + work_height-self.height()+settings.current_anchor[1]
        else:
            y = self.pos().y() + settings.current_anchor[1]
        # make sure that for all stand png, png bottom is the ground
        #self.floor_pos = work_height-self.height()
        self.floor_pos = self.current_screen.topLeft().y() + work_height - self.height()
        self.move(x,y)
        self.move_sig.emit(self.pos().x()+self.width()//2, self.pos().y()+self.height())

        if setImg:
            self.set_img()

    def set_img(self): #, img: QImage) -> None:
        """
        涓虹獥浣撹缃浘鐗?        :param img: 鍥剧墖
        :return:
        """
        # In hide mode, ignore frame updates from normal animation/interaction threads.
        if self.is_hiding_mode and not self._hiding_frame_update:
            return

        #print(settings.previous_anchor, settings.current_anchor)
        if settings.previous_anchor != settings.current_anchor:
            self.move(self.pos().x()-settings.previous_anchor[0]+settings.current_anchor[0],
                      self.pos().y()-settings.previous_anchor[1]+settings.current_anchor[1])

        scale_factor = settings.tunable_scale
        if self.is_hiding_mode:
            # Hide-mode sprites are slightly larger visually; reduce around 10%.
            scale_factor *= self.hide_scale_ratio
        width_tmp = int(settings.current_img.width()*scale_factor)
        height_tmp = int(settings.current_img.height()*scale_factor)

        # HighDPI-compatible scaling solution
        # self.label.setScaledContents(True)
        self.label.setFixedSize(width_tmp, height_tmp)
        pix = settings.current_img
        # Edge hide animation source is right-edge peeking style; mirror for left edge.
        if self.is_hiding_mode and self.hiding_edge == 'left':
            transform = QTransform()
            transform.scale(-1, 1)
            pix = pix.transformed(transform)
        self.label.setPixmap(pix) #QPixmap.fromImage(settings.current_img))
        # previous scaling soluton
        #self.label.resize(width_tmp, height_tmp)
        #self.label.setPixmap(QPixmap.fromImage(settings.current_img.scaled(width_tmp, height_tmp,
        #                                                                 aspectMode=Qt.KeepAspectRatio,
        #                                                                 mode=Qt.SmoothTransformation)))
        self.image = settings.current_img
        self._update_pet_hitbox()

    def _update_pet_hitbox(self):
        # Keep a lightweight global hitbox so other modules can check drag-drop feed.
        img_x = self.pos().x() + self.width() // 2 - self.label.width() // 2
        img_y = self.pos().y() + self.height() - self.label.height()
        settings.pet_hitbox = (img_x, img_y, self.label.width(), self.label.height())

    def _append_diary(self, category, message):
        if not hasattr(settings, 'diary_data'):
            return

        msg = message if message else self.tr("Triggered: ") + str(category)
        try:
            settings.diary_data.add_entry(settings.petname, category, msg)
        except:
            pass

    def _compensate_rewards(self):
        self.compensate_rewards.emit()
        # Note user if App updates available
        if settings.UPDATE_NEEDED:
            self.register_notification("system",
                                       self.tr("发现新版本，请到 系统-设置-检查更新 查看详情。"))

    def register_notification(self, note_type, message):
        self.setup_notification.emit(note_type, message)
        self._append_diary(note_type, message)


    def register_bubbleText(self, bubble_dict:dict):
        bubble_payload = dict(bubble_dict) if bubble_dict else {}
        if self.is_hiding_mode and self.hiding_edge in ('left', 'right'):
            bubble_payload['_side_mode'] = self.hiding_edge
        else:
            bubble_payload['_side_mode'] = None
        self.setup_bubbleText.emit(bubble_payload, self.pos().x()+self.width()//2, self.pos().y()+self.height())

    def _process_greeting_mssg(self, bubble_dict:dict):
        self.bubble_manager.add_usertag(bubble_dict, 'end', send=True)

    def register_accessory(self, accs):
        self.setup_acc.emit(accs, self.pos().x()+self.width()//2, self.pos().y()+self.height())

    def dev_add_coins(self, value=1000):
        try:
            n = int(value)
        except Exception:
            n = 1000
        if n <= 0:
            return
        self.addCoins.emit(n)
        self.register_notification('status_coin', self.tr("开发者模式金币增加：") + f"+{n}")

    def dev_set_hp_zero(self):
        # Keep one unified status path so hp tier/death flow and UI all sync.
        self.pet_hp.init_HP(0, sys_hp_interval)
        self.register_notification('status_hp', self.tr("开发者模式：饱食度归零"))

    def dev_generate_today_diary(self):
        if not hasattr(settings, 'diary_data'):
            self.register_notification('system', self.tr("日记系统不可用"))
            return
        try:
            created = settings.diary_data.generate_today_journal(settings.petname, overwrite=True)
            if created:
                self.register_notification('system', self.tr("已总结并生成当日日记"))
            else:
                self.register_notification('system', self.tr("今天暂无可总结内容"))
        except Exception:
            self.register_notification('system', self.tr("生成当日日记失败"))


    def _change_status(self, status, change_value, from_mod='Scheduler', send_note=False):
        # Check system status
        if from_mod == 'Scheduler' and is_system_locked() and settings.auto_lock:
            print("System locked, skip HP and FV changes")
            return
        if status == 'hp' and from_mod == 'Scheduler' and change_value < 0:
            change_value = change_value * settings.HP_DECAY_MULTIPLIER
        if status == 'fv' and change_value > 0:
            change_value = int(round(change_value * settings.FV_GAIN_MULTIPLIER))
        if status not in ['hp','fv']:
            return
        elif status == 'hp':
            
            diff = self.pet_hp.updateValue(change_value, from_mod)

        elif status == 'fv':
            
            diff = self.pet_fv.updateValue(change_value, from_mod)

        if send_note:

            if diff > 0:
                diff = '+%s'%diff
            elif diff < 0:
                diff = str(diff)
            else:
                return
            if status == 'hp':
                message = self.tr('饱食度') + " " f'{diff}'
            else:
                message = self.tr('好感度') + " " f'{diff}'
            self.register_notification('status_%s'%status, message)
        
        # Periodically triggered events
        if status == 'hp' and from_mod == 'Scheduler': # avoid being called in both hp and fv
            # Random Bubble
            if random.uniform(0, 1) < settings.PP_BUBBLE:
                self.bubble_manager.trigger_scheduled()

            # Auto-Feed
            if settings.pet_data.hp <= settings.AUTOFEED_THRESHOLD*settings.HP_INTERVAL:
                self.autofeed.emit()

    def _hp_updated(self, hp):
        self.hp_updated.emit(hp)
        if hp <= 0 and not self._death_handled:
            self._death_handled = True
            self._handle_pet_death()

    def _fv_updated(self, fv, fv_lvl):
        self.fv_updated.emit(fv, fv_lvl)


    def _change_time(self, status, timeleft):
        if status not in ['tomato','tomato_start','tomato_rest','tomato_end',
                          'focus_start','focus','focus_end','tomato_cencel','focus_cancel']:
            return

        if status in ['tomato','tomato_rest','tomato_end','focus','focus_end']:
            self.taskUI_Timer_update.emit()

        if status == 'tomato_start':
            self.tomato_time.setMaximum(25)
            self.tomato_time.setValue(timeleft)
            self.tomato_time.setFormat('%s min'%(int(timeleft)))
            #self.tomato_window.newTomato()
        elif status == 'tomato_rest':
            self.tomato_time.setMaximum(5)
            self.tomato_time.setValue(timeleft)
            self.tomato_time.setFormat('%s min'%(int(timeleft)))
            self.single_pomo_done.emit()
        elif status == 'tomato':
            self.tomato_time.setValue(timeleft)
            self.tomato_time.setFormat('%s min'%(int(timeleft)))
        elif status == 'tomato_end':
            self.tomato_time.setValue(0)
            self.tomato_time.setFormat('')
            #self.tomato_window.endTomato()
            self.taskUI_task_end.emit()
        elif status == 'tomato_cencel':
            self.tomato_time.setValue(0)
            self.tomato_time.setFormat('')

        elif status == 'focus_start':
            if timeleft == 0:
                self.focus_time.setMaximum(1)
                self.focus_time.setValue(0)
                self.focus_time.setFormat('%s min'%(int(timeleft)))
            else:
                self.focus_time.setMaximum(timeleft)
                self.focus_time.setValue(timeleft)
                self.focus_time.setFormat('%s min'%(int(timeleft)))
        elif status == 'focus':
            self.focus_time.setValue(timeleft)
            self.focus_time.setFormat('%s min'%(int(timeleft)))
        elif status == 'focus_end':
            self.focus_time.setValue(0)
            self.focus_time.setMaximum(0)
            self.focus_time.setFormat('')
            #self.focus_window.endFocus()
            self.taskUI_task_end.emit()
        elif status == 'focus_cancel':
            self.focus_time.setValue(0)
            self.focus_time.setMaximum(0)
            self.focus_time.setFormat('')

    def use_item(self, item_name):
        self._mark_interaction('feed', f'fed {item_name}')
        # Check if it's pet-required item
        if item_name == settings.required_item:
            reward_factor = settings.FACTOR_FEED_REQ
            self.close_bubble.emit('feed_required')
        else:
            reward_factor = 1

        # 椋熺墿
        if settings.items_data.item_dict[item_name]['item_type']=='consumable':
            self.workers['Animation'].pause()
            self.workers['Interaction'].start_interact('use_item', item_name)
            self.bubble_manager.trigger_bubble('feed_done')

        # 闄勪欢鐗╁搧
        elif item_name in self.pet_conf.act_name or item_name in self.pet_conf.acc_name:
            self.workers['Animation'].pause()
            self.workers['Interaction'].start_interact('use_clct', item_name)

        # 瀵硅瘽鐗╁搧
        elif settings.items_data.item_dict[item_name]['item_type']=='dialogue':
            if item_name in self.pet_conf.msg_dict:
                accs = {'name':'dialogue', 'msg_dict':self.pet_conf.msg_dict[item_name]}
                x = self.pos().x() #+self.width()//2
                y = self.pos().y() #+self.height()
                self.setup_acc.emit(accs, x, y)
                return

        # 绯荤粺闄勪欢鐗╁搧
        elif item_name in self.sys_conf.acc_name:
            accs = self.sys_conf.accessory_act[item_name]
            x = self.pos().x()+self.width()//2
            y = self.pos().y()+self.height()
            self.setup_acc.emit(accs, x, y)
        
        # Subpet
        elif settings.items_data.item_dict[item_name]['item_type']=='subpet':
            pet_acc = {'name':'subpet', 'pet_name':item_name}
            x = self.pos().x()+self.width()//2
            y = self.pos().y()+self.height()
            self.setup_acc.emit(pet_acc, x, y)
            return

        else:
            pass

        # 榧犳爣鎸備欢 - currently gave up :(
        '''
        elif item_name in self.sys_conf.mouseDecor:
            accs = {'name':'mouseDecor', 'config':self.sys_conf.mouseDecor[item_name]}
            x = self.pos().x()+self.width()//2
            y = self.pos().y()+self.height()
            self.setup_acc.emit(accs, x, y)
        '''
        
        # Apply item effects.
        self._change_status(
            'hp',
            int(settings.items_data.item_dict[item_name]['effect_HP'] * reward_factor),
            from_mod='inventory',
            send_note=True
        )
        
        if item_name in self.pet_conf.item_favorite:
            self._change_status('fv',
                                int(settings.items_data.item_dict[item_name]['effect_FV']*self.pet_conf.item_favorite[item_name]*reward_factor),
                                from_mod='inventory', send_note=True)

        elif item_name in self.pet_conf.item_dislike:
            self._change_status('fv', 
                                int(settings.items_data.item_dict[item_name]['effect_FV']*self.pet_conf.item_dislike[item_name]*reward_factor),
                                from_mod='inventory', send_note=True)

        else:
            self._change_status('fv', 
                                int(settings.items_data.item_dict[item_name]['effect_FV']*reward_factor),
                                from_mod='inventory', send_note=True)
        self._trigger_llm_interaction_reply('feed', item_name)

    def add_item(self, n_items, item_names=[]):
        self.addItem_toInven.emit(n_items, item_names)

    def patpat(self):
        self._sync_dynamic_chat_settings()
        self._mark_interaction('interaction', 'patpat interaction')
        # 鎽告懜鍔ㄧ敾
        if self.click_count >= self.pat_multi_click_talk_threshold:
            self.bubble_manager.trigger_bubble("pat_frequent")
            self._trigger_llm_interaction_reply('pat_multi_click', f'count={self.click_count}')
        elif self.workers['Interaction'].interact != 'patpat':
            if settings.focus_timer_on:
                self.bubble_manager.trigger_bubble("pat_focus")
            else:
                self.workers['Animation'].pause()
                self.workers['Interaction'].start_interact('patpat')
        # Probability trigger for floating rewards
        prob_num_0 = random.uniform(0, 1)
        if prob_num_0 < sys_pp_heart:
            try:
                accs = self.sys_conf.accessory_act['heart']
            except:
                return
            x = QCursor.pos().x() #self.pos().x()+self.width()//2 + random.uniform(-0.25, 0.25) * self.label.width()
            y = QCursor.pos().y() #self.pos().y()+self.height()-0.8*self.label.height() + random.uniform(0, 1) * 10
            self.setup_acc.emit(accs, x, y)

        elif prob_num_0 < settings.PP_COIN:
            # Drop random amount of coins
            self.addCoins.emit(0)

        elif prob_num_0 > sys_pp_item:
            self.addItem_toInven.emit(1, [])
            #print('鐗╁搧鎺夎惤锛?)

        if prob_num_0 > sys_pp_audio:
            #闅忔満璇煶
            if random.uniform(0, 1) > 0.5:
                # This will be deprecated soon
                self.register_notification('random', '')
            else:
                self.bubble_manager.trigger_patpat_random()
        self._trigger_llm_interaction_reply('patpat', '')

    def item_drop_anim(self, item_payload):
        if isinstance(item_payload, dict):
            item_name = item_payload.get('item_name', '')
            draggable = bool(item_payload.get('draggable', False))
            timeout_ms = int(item_payload.get('timeout_ms', 1500))
            return_on_close = bool(item_payload.get('return_on_close', False))
        else:
            item_name = str(item_payload)
            draggable = False
            timeout_ms = 1500
            return_on_close = False

        if (not draggable) and (not return_on_close):
            timeout_ms = int(round(timeout_ms * 1.5))

        if item_name == 'coin':
            accs = {
                "name": "item_drop",
                "item_image": [settings.items_data.coin['image']],
                "draggable": draggable,
                "timeout_ms": timeout_ms,
                "return_on_close": False,
            }
        else:
            item = settings.items_data.item_dict[item_name]
            accs = {
                "name": "item_drop",
                "item_image": [item['image']],
                "draggable": draggable,
                "timeout_ms": timeout_ms,
                "return_on_close": return_on_close,
                "return_item_name": item_name,
                "return_item_count": 1,
            }
        x = self.pos().x()+self.width()//2 + random.uniform(-0.25, 0.25) * self.label.width()
        y = self.pos().y()+self.height()-self.label.height()
        self.setup_acc.emit(accs, x, y)



    def quit(self) -> None:
        """
        鍏抽棴绐楀彛, 绯荤粺閫€鍑?        :return:
        """
        if self.idle_llm_timer.isActive():
            self.idle_llm_timer.stop()
        if self.llm_prefetch_timer.isActive():
            self.llm_prefetch_timer.stop()
        if self.user_observe_timer.isActive():
            self.user_observe_timer.stop()
        if self.reply_update_timer.isActive():
            self.reply_update_timer.stop()
        if self.diary_rollover_timer.isActive():
            self.diary_rollover_timer.stop()
        settings.pet_data.save_data()
        settings.pet_data.frozen()
        self.stop_thread('Animation')
        self.stop_thread('Interaction')
        self.stop_thread("Scheduler")
        self.stopAllThread.emit()
        self.close()
        sys.exit()

    def stop_thread(self, module_name):
        self.workers[module_name].kill()
        self.threads[module_name].terminate()
        self.threads[module_name].wait()
        #self.threads[module_name].wait()

    def follow_mouse_act(self):
        sender = self.sender()
        if settings.onfloor == 0:
            return
        if sender.text()==self.tr("跟随鼠标"):
            sender.setText(self.tr("停止跟随"))
            self.MouseTracker = MouseMoveManager()
            self.MouseTracker.moved.connect(self.update_mouse_position)
            self.get_positions('mouse')
            self.workers['Animation'].pause()
            self.workers['Interaction'].start_interact('followTarget', 'mouse')
        else:
            sender.setText(self.tr("跟随鼠标"))
            self.MouseTracker._listener.stop()
            self.workers['Interaction'].stop_interact()

    def get_positions(self, object_name):

        main_pos = [int(self.pos().x() + self.width()//2), int(self.pos().y() + self.height() - self.label.height())]

        if object_name == 'mouse':
            self.send_positions.emit(main_pos, self.mouse_pos)

    def update_mouse_position(self, x, y):
        self.mouse_pos = [x, y]

    def stop_trackMouse(self):
        self.start_follow_mouse.setText(self.tr("跟随鼠标"))
        self.MouseTracker._listener.stop()

    '''
    def fall_onoff(self):
        #global set_fall
        sender = self.sender()
        if settings.set_fall==1:
            sender.setText(self.tr("Don't Drop"))
            sender.setIcon(QIcon(os.path.join(basedir,'res/icons/off.svg')))
            settings.set_fall=0
        else:
            sender.setText(self.tr("鍏佽涓嬭惤"))
            sender.setIcon(QIcon(os.path.join(basedir,'res/icons/on.svg')))
            settings.set_fall=1
    '''

    def _show_controlPanel(self):
        self.show_controlPanel.emit()

    def _show_chat_window(self):
        side_reason = self._chat_availability_reason()
        if side_reason:
            QMessageBox.warning(self, self.tr("不可用"), side_reason)
            return
        self._mark_interaction('chat_open', 'opened chat window')
        reason = self.local_llm.unavailable_reason()
        if reason:
            QMessageBox.warning(self, self.tr("不可用"), reason)
            return
        if self.chat_window is None:
            self.chat_window = LocalChatWindow(
                pet_name=self.curr_pet_name,
                availability_checker=self._chat_availability_reason
            )
        self.chat_window.set_pet_name(self.curr_pet_name)
        self.chat_window.show()
        self.chat_window.raise_()
        self.chat_window.activateWindow()

    def _show_dashboard(self):
        self.show_dashboard.emit()

    def _show_game_dev_tip(self):
        QMessageBox.information(self, self.tr("游戏"), self.tr("正在开发中"))

    def _usage_guide_text(self):
        return (
            "猫猫桌宠使用说明\n"
            "使用说明查看：右键桌宠>使用说明\n"
            "桌宠第一次启动后建议先启用联网大模型，配置API密钥\n"
            "【配置方法：右键桌宠>系统>设置>AI大模型】API不懂的，网上查下，很简单的\n"
            "1、互动方式：点击、拖拽桌宠\n"
            "【点击桌宠有概率获得啵币或触发特殊事件】\n"
            "2、属性值：\n"
            "等级：每过一段时间自动变化\n"
            "饱食度：不断缓慢消耗，桌宠饿的时候概率自己吃饭，最好手动喂食！\n"
            "        饱食度为零时，桌宠死亡，没办法恢复数据！！！养好她！\n"
            "好感度：互动、吃饭等可增加好感度，能解锁更多动作与玩法\n"
            "3、右键后的操作：\n"
            "角色面板：状态、背包、商店、任务、动画、日记\n"
            "系统：开机自启、语音、大模型、关于\n"
            "【其它的慢慢探索吧！照顾好桌宠哦QAQ~】"
        )

    def _show_usage_guide(self):
        QMessageBox.information(self, self.tr("使用说明"), self._usage_guide_text())

    def _auto_show_usage_guide_if_needed(self):
        if getattr(settings, 'usage_guide_shown', False):
            return
        self._show_usage_guide()
        settings.usage_guide_shown = True
        settings.save_settings()

    def _default_reply_library(self):
        return {
            'feed': ["好耶，吃饱啦！", "这口真香，谢谢你。", "我又有力气陪你啦。"],
            'patpat': ["被摸摸好开心。", "再摸一下嘛。", "嘿嘿，我在呢。"],
            'pat_multi_click': ["哇，连点我这么多下。", "你今天手速好快呀。", "收到收到，我在认真回应你。"],
            'throw_land': ["呼，安全落地。", "被你扔得有点晕乎。", "我落地啦，下次轻一点嘛。"],
            'edge_hide_left': ["我在左边安安静静待着。", "先在这边偷看你。"],
            'edge_hide_right': ["我在右边安安静静待着。", "先在这边悄悄陪你。"],
            'idle_chat': ["我在悄悄看你忙什么。", "今天也想和你多待一会。", "你认真时也很可爱。", "我有点饿了，记得喂我呀。"],
        }

    def _load_reply_library(self):
        defaults = self._default_reply_library()
        path = Path(self.reply_preset_file)
        if not path.exists():
            return defaults
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(raw, dict):
                return defaults
            for key, fallback_values in defaults.items():
                values = raw.get(key, fallback_values)
                if not isinstance(values, list):
                    values = fallback_values
                cleaned = [str(i).strip() for i in values if str(i).strip()]
                raw[key] = cleaned[:12] if cleaned else fallback_values
            return raw
        except Exception:
            return defaults

    def _save_reply_library(self):
        try:
            Path(self.reply_preset_file).write_text(
                json.dumps(self.reply_library, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception:
            pass

    def _get_local_reply(self, event_name, context_text=''):
        key = event_name
        if event_name == 'edge_hide':
            key = 'edge_hide_left' if str(context_text) == 'left' else 'edge_hide_right'
        pool = self.reply_library.get(key, [])
        if not pool:
            pool = self._default_reply_library().get(key, [])
        if not pool:
            return ''
        return random.choice(pool)

    def _parse_generated_reply_lines(self, raw_text):
        lines = []
        for line in (raw_text or '').splitlines():
            line = line.strip()
            if not line:
                continue
            line = line.lstrip('-').lstrip('*').strip()
            if line and line[0].isdigit() and '.' in line[:3]:
                line = line.split('.', 1)[1].strip()
            if line:
                lines.append(line[:28])
        deduped = []
        seen = set()
        for line in lines:
            if line in seen:
                continue
            seen.add(line)
            deduped.append(line)
        return deduped[:8]

    def _update_reply_library_tick(self):
        self._sync_dynamic_chat_settings()
        llm_enabled = bool(settings.llm_config.get('enabled', False))
        auto_talk = bool(settings.llm_config.get('auto_talk', True))
        if (not llm_enabled) or (not auto_talk):
            return
        if self.local_llm.unavailable_reason():
            return
        if self._llm_update_busy:
            return

        event_key = self._reply_update_order[self._reply_update_idx]
        self._reply_update_idx = (self._reply_update_idx + 1) % len(self._reply_update_order)
        self._llm_update_busy = True

        def _worker():
            try:
                prompt = (
                    f"你是桌宠{self.curr_pet_name}。"
                    f"请针对事件 {event_key} 生成 6 句中文短句，每句 6-16 字，口吻可爱自然，不要 emoji，不要解释。"
                    "每行一句。"
                )
                raw = self.local_llm.chat(
                    messages=[{'role': 'user', 'content': prompt}],
                    system_prompt='你是桌宠语料生成器，只输出多行短句。',
                    max_tokens=180,
                    temperature=0.9,
                    timeout=16,
                )
                new_lines = self._parse_generated_reply_lines(raw)
                if new_lines:
                    self.reply_library[event_key] = new_lines
                    self._save_reply_library()
            except Exception:
                pass
            finally:
                self._llm_update_busy = False

        threading.Thread(target=_worker, daemon=True).start()

    def _trigger_llm_interaction_reply(self, event_name, context_text=''):
        # Interaction events always speak from local preset library.
        if event_name in ('pat_multi_click', 'throw_land', 'edge_hide', 'patpat', 'feed'):
            local_msg = self._get_local_reply(event_name, context_text)
            if local_msg:
                self._speak_line(local_msg, from_category='chat_pet_auto')
                return True

        cached = self._llm_prefetch_cache.pop(event_name, None)
        if cached:
            self._speak_line(cached, from_category='chat_pet_auto')
            self._prefetch_event_reply(event_name)
            return True

        if self._llm_busy:
            # For strong interaction events, still give immediate visible response.
            if event_name in ('pat_multi_click', 'throw_land', 'edge_hide', 'patpat', 'feed'):
                fallback = self._fallback_interaction_reply(event_name, context_text)
                if fallback:
                    self._speak_line(fallback, from_category='chat_pet_auto')
                    return True
            return False
        llm_enabled = bool(settings.llm_config.get('enabled', False))
        auto_talk = bool(settings.llm_config.get('auto_talk', True))
        if (not llm_enabled) or (not auto_talk):
            fallback = self._fallback_interaction_reply(event_name, context_text)
            if fallback:
                self._speak_line(fallback, from_category='chat_pet_auto')
                return True
            return False
        if self.local_llm.unavailable_reason():
            fallback = self._fallback_interaction_reply(event_name, context_text)
            if fallback:
                self._speak_line(fallback, from_category='chat_pet_auto')
                return True
            return False
        self._llm_busy = True

        def _worker():
            try:
                msg = self.local_llm.pet_interaction_reply(event_name, context_text, pet_name=self.curr_pet_name)
                if msg:
                    self.llm_reply_ready.emit(msg)
            except Exception:
                fb = self._fallback_interaction_reply(event_name, context_text)
                if fb:
                    self.llm_reply_ready.emit(fb)
            finally:
                self._llm_busy = False

        threading.Thread(target=_worker, daemon=True).start()
        return True

    def _warmup_llm(self):
        llm_enabled = bool(settings.llm_config.get('enabled', False))
        auto_talk = bool(settings.llm_config.get('auto_talk', True))
        if (not llm_enabled) or (not auto_talk):
            return
        if self.local_llm.unavailable_reason():
            return

        def _worker():
            try:
                self.local_llm.quick_check()
            except Exception:
                pass
            self._prefetch_llm_cache()

        threading.Thread(target=_worker, daemon=True).start()

    def _prefetch_context_for_event(self, event_name):
        if event_name == 'edge_hide':
            return random.choice(['left', 'right'])
        if event_name == 'idle_chat':
            hp = int(self.pet_hp.value()) if hasattr(self, 'pet_hp') else 0
            fv = int(self.pet_fv.value()) if hasattr(self, 'pet_fv') else 0
            mood_hint = "正常"
            if hp <= 30:
                mood_hint = "有点饿"
            elif fv >= 70:
                mood_hint = "很开心"
            user_ctx = f" 最近我观察到：{self._last_user_context_text}。" if self._last_user_context_text else ""
            return f"状态: 饱食度{hp}/100, 好感度{fv}, 心情{mood_hint}。{user_ctx}"
        return ''

    def _prefetch_event_reply(self, event_name):
        if self._llm_busy:
            return
        if event_name in self._llm_prefetch_cache:
            return
        if event_name in self._llm_prefetch_inflight:
            return

        llm_enabled = bool(settings.llm_config.get('enabled', False))
        auto_talk = bool(settings.llm_config.get('auto_talk', True))
        if (not llm_enabled) or (not auto_talk):
            return
        if self.local_llm.unavailable_reason():
            return

        self._llm_prefetch_inflight.add(event_name)
        context_text = self._prefetch_context_for_event(event_name)

        def _worker():
            try:
                msg = self.local_llm.pet_interaction_reply(
                    event_name, context_text, pet_name=self.curr_pet_name
                )
                if msg:
                    self._llm_prefetch_cache[event_name] = msg.strip()
            except Exception:
                pass
            finally:
                self._llm_prefetch_inflight.discard(event_name)

        threading.Thread(target=_worker, daemon=True).start()

    def _prefetch_llm_cache(self):
        llm_enabled = bool(settings.llm_config.get('enabled', False))
        auto_talk = bool(settings.llm_config.get('auto_talk', True))
        if (not llm_enabled) or (not auto_talk):
            self._llm_prefetch_cache.clear()
            self._llm_prefetch_inflight.clear()
            return
        if self.local_llm.unavailable_reason():
            return
        if self._llm_busy:
            return

        length = len(self._llm_prefetch_order)
        if length <= 0:
            return
        for _ in range(length):
            event_name = self._llm_prefetch_order[self._llm_prefetch_idx]
            self._llm_prefetch_idx = (self._llm_prefetch_idx + 1) % length
            if event_name in self._llm_prefetch_cache or event_name in self._llm_prefetch_inflight:
                continue
            self._prefetch_event_reply(event_name)
            break

    def _handle_llm_reply(self, message):
        if message:
            self._speak_line(message, from_category='chat_pet_auto')

    def _chat_availability_reason(self):
        # 0.77-like behavior: side mode can still produce interaction-related chat.
        return None

    def _tick_idle_llm(self):
        self._sync_dynamic_chat_settings()
        now_ts = time.time()
        if now_ts - self._last_llm_reply_ts < self.idle_chat_min_gap_sec:
            return

        enough_interactions = self._interaction_since_llm >= self.idle_chat_interaction_threshold
        enough_idle_time = now_ts >= self._next_idle_llm_ts
        if not (enough_interactions or enough_idle_time):
            return

        hp = int(self.pet_hp.value()) if hasattr(self, 'pet_hp') else 0
        fv = int(self.pet_fv.value()) if hasattr(self, 'pet_fv') else 0
        mood_hint = "正常"
        if hp <= 30:
            mood_hint = "有点饿"
        elif fv >= 70:
            mood_hint = "很开心"

        launched = self._trigger_llm_interaction_reply(
            'idle_chat',
            f"状态: 饱食度{hp}/100, 好感度{fv}, 心情{mood_hint}。"
            f"{(' 最近我观察到你：' + self._last_user_context_text + '。') if self._last_user_context_text else ''}"
            "请随机说一句短中文，可以调侃、关心我在做什么、提及你饿不饿或开不开心。"
        )
        if launched:
            self._interaction_since_llm = 0
            self._next_idle_llm_ts = now_ts + random.randint(*self.idle_chat_interval_range)

    def _tick_diary_rollover(self):
        if not hasattr(settings, 'diary_data'):
            return
        for pet_name in getattr(settings, 'pets', [settings.petname]):
            try:
                settings.diary_data.finalize_pending(pet_name)
            except:
                pass

    def _speak_line(self, text, from_category='chat_pet_auto'):
        msg = (text or '').strip()
        if not msg:
            return
        bubble_dict = {
            "message": msg,
            "icon": None,
            "start_audio": None,
            "end_audio": None,
            "timeout": 4,
            # Use None so interaction chats are not deduplicated away.
            "bubble_type": None,
        }
        self.register_bubbleText(bubble_dict)
        self._append_diary(from_category, msg)
        self._last_llm_reply_ts = time.time()

    def _fallback_interaction_reply(self, event_name, context_text=''):
        hp_now = int(self.pet_hp.value()) if hasattr(self, 'pet_hp') else 0
        if event_name == 'feed':
            return random.choice(["好耶，吃饱啦！", "这口真香，谢谢你。", "我又有力气陪你啦。"])
        if event_name == 'patpat':
            return random.choice(["被摸摸好开心。", "再摸一下嘛。", "嘿嘿，我在呢。"])
        if event_name == 'pat_multi_click':
            return random.choice(["哇，连点我这么多下。", "你今天手速好快呀。", "收到收到，我在认真回应你。"])
        if event_name == 'throw_land':
            return random.choice(["呼，安全落地。", "被你扔得有点晕乎。", "我落地啦，下次轻一点嘛。"])
        if event_name == 'edge_hide':
            if str(context_text) == 'left':
                return random.choice(["我在左边安安静静待着。", "先在这边偷看你。"])
            return random.choice(["我在右边安安静静待着。", "先在这边悄悄陪你。"])
        if event_name == 'idle_chat':
            if hp_now <= 25:
                return random.choice(["我有点饿了，想吃点东西。", "肚子咕咕叫了。"])
            return random.choice(["我在悄悄看你忙什么。", "今天也想和你多待一会。", "你认真时也很可爱。"])
        return ""

    def _collect_all_journals_text(self):
        blocks = []
        if not hasattr(settings, 'diary_data'):
            return ""
        try:
            settings.diary_data.finalize_pending(settings.petname)
            days = settings.diary_data.list_journal_days(settings.petname)
            for day in reversed(days):
                journal = settings.diary_data.get_journal(settings.petname, day)
                if not journal:
                    continue
                content = (journal.get('content') or '').strip()
                if not content:
                    continue
                blocks.append(f"[{day}]\n{content}")
        except Exception:
            return ""
        return "\n\n".join(blocks).strip()

    def _generate_llm_death_summary(self, journals_text):
        reason = self.local_llm.unavailable_reason()
        if reason:
            return "我因为长期饥饿离开了。虽然很舍不得你，但还是想谢谢你一直以来的陪伴。"

        try:
            prompt = (
                f"你是桌宠{settings.petname}。"
                "请写一段死亡说明与告别信，中文，120字以内，语气真诚克制，包含："
                "1) 死亡原因是饥饿归零；2) 对用户的不舍与感谢；3) 不要使用emoji。"
            )
            if journals_text:
                prompt += "\n以下是已整理日记摘要，请参考后再写：\n" + journals_text[:3000]
            text = self.local_llm.chat(
                messages=[{'role': 'user', 'content': prompt}],
                system_prompt='你是桌宠临终遗书助手，只输出正文。',
                max_tokens=220,
                temperature=0.6,
                timeout=20,
            )
            text = (text or '').strip()
            if text:
                return text
        except Exception:
            pass
        return "我因为长期饥饿离开了。虽然很舍不得你，但还是想谢谢你一直以来的陪伴。"

    def _build_death_note_text(self):
        journals_text = self._collect_all_journals_text()
        llm_summary = self._generate_llm_death_summary(journals_text)
        lines = []
        lines.append(f"{settings.petname} 的遗书")
        lines.append(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("【死亡原因与告别】")
        lines.append(llm_summary)
        lines.append("")
        lines.append("【全部已整理日记】")
        if journals_text:
            lines.append(journals_text)
        else:
            lines.append("暂无可整理日记。")
        return "\n".join(lines).strip() + "\n"

    def _reset_data_after_death(self):
        # Reset pet save data to fresh start (full HP, zero FV/coins/items).
        full_hp_inner = int(100 * sys_hp_interval)
        try:
            settings.pet_data.reset_all_progress(full_hp_inner=full_hp_inner)
        except Exception:
            pass

        # Clear diary data for a full restart experience after death note exported.
        try:
            if hasattr(settings, 'diary_data'):
                settings.diary_data.reset_all()
        except Exception:
            pass

        # Refresh UI state immediately.
        try:
            self.pet_hp.init_HP(full_hp_inner, sys_hp_interval)
            self.pet_fv.init_FV(0, 0)
            self._death_handled = False
            self._interaction_since_llm = 0
            self._last_llm_reply_ts = 0.0
            self._next_idle_llm_ts = time.time() + random.randint(*self.idle_chat_interval_range)
        except Exception:
            pass

    def _handle_pet_death(self):
        note_text = self._build_death_note_text()
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        note_file = os.path.join(
            desktop_dir,
            f"{settings.petname}_最后日记_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        )
        try:
            with open(note_file, 'w', encoding='utf-8') as f:
                f.write(note_text)
            try:
                os.startfile(note_file)
            except Exception:
                pass
        except Exception:
            pass

        QMessageBox.information(
            self,
            self.tr("告别"),
            self.tr("桌宠已因饥饿死亡，遗书已生成。数据已重置为全新开始。")
        )
        self._reset_data_after_death()
    '''
    def show_compday(self):
        sender = self.sender()
        if sender.text()=="鏄剧ず闄即澶╂暟":
            acc = {'name':'compdays', 
                   'height':self.label.height(),
                   'message': "杩欐槸%s闄即浣犵殑绗?%i 澶?%(settings.petname,settings.pet_data.days)}
            sender.setText("鍏抽棴闄即澶╂暟")
            x = self.pos().x() + self.width()//2
            y = self.pos().y() + self.height() - self.label.height() - 20 #*settings.size_factor
            self.setup_acc.emit(acc, x, y)
            self.showing_comp = 1
        else:
            sender.setText("鏄剧ず闄即澶╂暟")
            self.setup_acc.emit({'name':'compdays'}, 0, 0)
            self.showing_comp = 0
    '''

    def show_tomato(self):
        if self.tomato_window.isVisible():
            self.tomato_window.hide()

        else:
            self.tomato_window.move(max(self.current_screen.topLeft().y(),self.pos().x()-self.tomato_window.width()//2),
                                    max(self.current_screen.topLeft().y(),self.pos().y()-self.tomato_window.height()))
            self.tomato_window.show()

        '''
        elif self.tomato_clock.text()=="鍙栨秷鐣寗鏃堕挓":
            self.tomato_clock.setText("鐣寗鏃堕挓")
            self.workers['Scheduler'].cancel_tomato()
            self.tomatoicon.hide()
            self.tomato_time.hide()
        '''

    def run_tomato(self, nt):
        self.workers['Scheduler'].add_tomato(n_tomato=int(nt))
        self.tomatoicon.show()
        self.tomato_time.show()
        settings.focus_timer_on = True

    def cancel_tomato(self):
        self.workers['Scheduler'].cancel_tomato()

    def change_tomato_menu(self):
        self.tomatoicon.hide()
        self.tomato_time.hide()
        settings.focus_timer_on = False

    
    def show_focus(self):
        if self.focus_window.isVisible():
            self.focus_window.hide()
        
        else:
            self.focus_window.move(max(self.current_screen.topLeft().y(),self.pos().x()-self.focus_window.width()//2),
                                   max(self.current_screen.topLeft().y(),self.pos().y()-self.focus_window.height()))
            self.focus_window.show()


    def run_focus(self, task, hs, ms):
        if task == 'range':
            if hs<=0 and ms<=0:
                return
            self.workers['Scheduler'].add_focus(time_range=[hs,ms])
        elif task == 'point':
            self.workers['Scheduler'].add_focus(time_point=[hs,ms])
        self.focusicon.show()
        self.focus_time.show()
        settings.focus_timer_on = True

    def pause_focus(self, state):
        if state: # 鏆傚仠
            self.workers['Scheduler'].pause_focus()
        else: # 缁х画
            self.workers['Scheduler'].resume_focus(int(self.focus_time.value()), int(self.focus_time.maximum()))


    def cancel_focus(self):
        self.workers['Scheduler'].cancel_focus(int(self.focus_time.maximum()-self.focus_time.value()))

    def change_focus_menu(self):
        self.focusicon.hide()
        self.focus_time.hide()
        settings.focus_timer_on = False


    def show_remind(self):
        if self.remind_window.isVisible():
            self.remind_window.hide()
        else:
            self.remind_window.move(max(self.current_screen.topLeft().y(),self.pos().x()-self.remind_window.width()//2),
                                    max(self.current_screen.topLeft().y(),self.pos().y()-self.remind_window.height()))
            self.remind_window.show()

    ''' Reminder function deleted from v0.3.7
    def run_remind(self, task_type, hs=0, ms=0, texts=''):
        if task_type == 'range':
            self.workers['Scheduler'].add_remind(texts=texts, time_range=[hs,ms])
        elif task_type == 'point':
            self.workers['Scheduler'].add_remind(texts=texts, time_point=[hs,ms])
        elif task_type == 'repeat_interval':
            self.workers['Scheduler'].add_remind(texts=texts, time_range=[hs,ms], repeat=True)
        elif task_type == 'repeat_point':
            self.workers['Scheduler'].add_remind(texts=texts, time_point=[hs,ms], repeat=True)
    '''

    def show_inventory(self):
        if self.inventory_window.isVisible():
            self.inventory_window.hide()
        else:
            self.inventory_window.move(max(self.current_screen.topLeft().y(), self.pos().x()-self.inventory_window.width()//2),
                                    max(self.current_screen.topLeft().y(), self.pos().y()-self.inventory_window.height()))
            self.inventory_window.show()
            #print(self.inventory_window.size())

    '''
    def show_settings(self):
        if self.setting_window.isVisible():
            self.setting_window.hide()
        else:
            #self.setting_window.move(max(self.current_screen.topLeft().y(), self.pos().x()-self.setting_window.width()//2),
            #                        max(self.current_screen.topLeft().y(), self.pos().y()-self.setting_window.height()))
            #self.setting_window.resize(800,800)
            self.setting_window.show()
    '''

    '''
    def show_settingstest(self):
        self.settingUI = SettingMainWindow()
        
        if sys.platform == 'win32':
            self.settingUI.setWindowFlags(
                Qt.FramelessWindowHint | Qt.SubWindow | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        else:
            self.settingUI.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        self.settingUI.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        cardShadowSE = QtWidgets.QGraphicsDropShadowEffect(self.settingUI)
        cardShadowSE.setColor(QColor(189, 167, 165))
        cardShadowSE.setOffset(0, 0)
        cardShadowSE.setBlurRadius(20)
        self.settingUI.setGraphicsEffect(cardShadowSE)
        
        self.settingUI.show()
    '''

    def runAnimation(self):
        # Create thread for Animation Module
        self.threads['Animation'] = QThread()
        self.workers['Animation'] = Animation_worker(self.pet_conf)
        self.workers['Animation'].moveToThread(self.threads['Animation'])

        # Connect signals and slots
        self.threads['Animation'].started.connect(self.workers['Animation'].run)
        self.workers['Animation'].sig_setimg_anim.connect(self.set_img)
        self.workers['Animation'].sig_move_anim.connect(self._move_customized)
        self.workers['Animation'].sig_repaint_anim.connect(self.repaint)
        self.workers['Animation'].acc_regist.connect(self.register_accessory)

        # Start the thread
        self.threads['Animation'].start()
        self.threads['Animation'].setTerminationEnabled()


    def hpchange(self, hp_tier, direction):
        self.workers['Animation'].hpchange(hp_tier, direction)
        self.hptier_changed_main_note.emit(hp_tier, direction)
        #self._update_statusTitle(hp_tier)

    def fvchange(self, fv_lvl):
        if fv_lvl == -1:
            self.fvlvl_changed_main_note.emit(fv_lvl)
        else:
            self.workers['Animation'].fvchange(fv_lvl)
            self.fvlvl_changed_main_note.emit(fv_lvl)
            self.fvlvl_changed_main_inve.emit(fv_lvl)
            self._update_fvlock()
            self.lvl_badge.set_level(fv_lvl)
        self.refresh_acts.emit()
        self.bubble_manager.trigger_bubble(bb_type="fv_lvlup")

    def runInteraction(self):
        # Create thread for Interaction Module
        self.threads['Interaction'] = QThread()
        self.workers['Interaction'] = Interaction_worker(self.pet_conf)
        self.workers['Interaction'].moveToThread(self.threads['Interaction'])

        # Connect signals and slots
        self.workers['Interaction'].sig_setimg_inter.connect(self.set_img)
        self.workers['Interaction'].sig_move_inter.connect(self._move_customized)
        self.workers['Interaction'].sig_act_finished.connect(self.resume_animation)
        self.workers['Interaction'].sig_interact_note.connect(self.register_notification)
        self.workers['Interaction'].acc_regist.connect(self.register_accessory)
        self.workers['Interaction'].query_position.connect(self.get_positions)
        self.workers['Interaction'].stop_trackMouse.connect(self.stop_trackMouse)
        self.send_positions.connect(self.workers['Interaction'].receive_pos)

        # Start the thread
        self.threads['Interaction'].start()
        self.threads['Interaction'].setTerminationEnabled()

    def runScheduler(self):
        # Create thread for Scheduler Module
        self.threads['Scheduler'] = QThread()
        self.workers['Scheduler'] = Scheduler_worker()
        self.workers['Scheduler'].moveToThread(self.threads['Interaction'])

        # Connect signals and slots
        self.threads['Scheduler'].started.connect(self.workers['Scheduler'].run)
        self.workers['Scheduler'].sig_settext_sche.connect(self.register_notification) #_set_dialogue_dp)
        self.workers['Scheduler'].sig_setact_sche.connect(self._show_act)
        self.workers['Scheduler'].sig_setstat_sche.connect(self._change_status)
        self.workers['Scheduler'].sig_focus_end.connect(self.change_focus_menu)
        self.workers['Scheduler'].sig_tomato_end.connect(self.change_tomato_menu)
        self.workers['Scheduler'].sig_settime_sche.connect(self._change_time)
        self.workers['Scheduler'].sig_addItem_sche.connect(self.add_item)
        self.workers['Scheduler'].sig_setup_bubble.connect(self._process_greeting_mssg)

        # Start the thread
        self.threads['Scheduler'].start()
        self.threads['Scheduler'].setTerminationEnabled()



    def _move_customized(self, plus_x, plus_y):

        #print(act_list)
        #direction, frame_move = str(act_list[0]), float(act_list[1])
        pos = self.pos()
        new_x = pos.x() + plus_x
        new_y = pos.y() + plus_y

        # 姝ｅ湪涓嬭惤鐨勬儏鍐碉紝鍙互鍒囨崲灞忓箷
        if settings.onfloor == 0:
            # 钀藉湴鎯呭喌
            if new_y > self.floor_pos+settings.current_anchor[1]:
                settings.onfloor = 1
                new_x, new_y = self.limit_in_screen(new_x, new_y)
                # Throw-and-land interaction chat trigger.
                self._trigger_llm_interaction_reply('throw_land', '')
            # In air
            else:
                anim_area = QRect(self.pos() + QPoint(self.width()//2-self.label.width()//2, 
                                                      self.height()-self.label.height()), 
                                  QSize(self.label.width(), self.label.height()))
                intersected = self.current_screen.intersected(anim_area)
                area = intersected.width() * intersected.height() / self.label.width() / self.label.height()
                if area > 0.5:
                    # Keep bouncing/clamping at edge while still on the same screen.
                    new_x, new_y = self.limit_in_screen(new_x, new_y)
                else:
                    switched = False
                    for screen in settings.screens:
                        if screen.geometry() == self.current_screen:
                            continue
                        intersected = screen.geometry().intersected(anim_area)
                        area_tmp = intersected.width() * intersected.height() / self.label.width() / self.label.height()
                        if area_tmp > 0.5:
                            self.switch_screen(screen)
                            switched = True
                    if not switched:
                        new_x, new_y = self.limit_in_screen(new_x, new_y)

        # 姝ｅ湪鍋氬姩浣滅殑鎯呭喌锛屽眬闄愬湪褰撳墠灞忓箷鍐?        else:
            new_x, new_y = self.limit_in_screen(new_x, new_y, on_action=True)

        self.move(new_x, new_y)


    def switch_screen(self, screen):
        self.current_screen = screen.geometry()
        settings.current_screen = screen
        self.screen_geo = screen.availableGeometry() #screenGeometry()
        self.screen_width = self.screen_geo.width()
        self.screen_height = self.screen_geo.height()
        self.floor_pos = self.current_screen.topLeft().y() + self.screen_height -self.height()


    def limit_in_screen(self, new_x, new_y, on_action=False):
        if new_x + self.width() // 2 < self.current_screen.topLeft().x():
            #surpass_x = 'Left'
            new_x = self.current_screen.topLeft().x() - self.width() // 2
            if not on_action:
                settings.dragspeedx = -settings.dragspeedx * settings.SPEED_DECAY
                settings.fall_right = not settings.fall_right

        elif new_x + self.width() // 2 > self.current_screen.topLeft().x() + self.screen_width:
            #surpass_x = 'Right'
            new_x = self.current_screen.topLeft().x() + self.screen_width - self.width() // 2
            if not on_action:
                settings.dragspeedx = -settings.dragspeedx * settings.SPEED_DECAY
                settings.fall_right = not settings.fall_right

        if new_y + self.height() - self.label.height() // 2 < self.current_screen.topLeft().y():
            #surpass_y = 'Top'
            new_y = self.current_screen.topLeft().y() + self.label.height() // 2 - self.height()
            if not on_action:
                settings.dragspeedy = abs(settings.dragspeedy) * settings.SPEED_DECAY

        elif new_y > self.floor_pos + settings.current_anchor[1]:
            #surpass_y = 'Bottom'
            new_y = self.floor_pos + settings.current_anchor[1]

        return new_x, new_y


    def _show_act(self, act_name):
        self.workers['Animation'].pause()
        self.workers['Interaction'].start_interact('actlist', act_name)
    '''
    def _show_acc(self, acc_name):
        self.workers['Animation'].pause()
        self.workers['Interaction'].start_interact('anim_acc', acc_name)
    '''
    def _set_defaultAct(self, act_name):

        if act_name == settings.defaultAct[self.curr_pet_name]:
            settings.defaultAct[self.curr_pet_name] = None
            settings.save_settings()
            for action in self.defaultAct_menu.menuActions():
                if action.text() == act_name:
                    action.setIcon(QIcon(os.path.join(basedir, 'res/icons/dot.png')))
        else:
            for action in self.defaultAct_menu.menuActions():
                if action.text() == settings.defaultAct[self.curr_pet_name]:
                    action.setIcon(QIcon(os.path.join(basedir, 'res/icons/dot.png')))
                elif action.text() == act_name:
                    action.setIcon(QIcon(os.path.join(basedir, 'res/icons/dotfill.png'))) #os.path.join(basedir, 'res/icons/check_icon.png')))

            settings.defaultAct[self.curr_pet_name] = act_name
            settings.save_settings()


    def resume_animation(self):
        self.workers['Animation'].resume()
    
    def _mightEventTrigger(self):
        # Update date
        settings.pet_data.update_date()
        # Update companion days
        daysText = self.tr("（已陪伴 ") + str(settings.pet_data.days) + \
                   self.tr(" 天）")
        self.daysLabel.setText(daysText)




def _load_all_pic(pet_name: str) -> dict:
    """
    鍔犺浇瀹犵墿鎵€鏈夊姩浣滃浘鐗?    :param pet_name: 瀹犵墿鍚嶇О
    :return: {鍔ㄤ綔缂栫爜: 鍔ㄤ綔鍥剧墖}
    """
    img_dir = os.path.join(basedir, 'res/role/{}/action/'.format(pet_name))
    images = os.listdir(img_dir)
    return {image.split('.')[0]: _get_q_img(img_dir + image) for image in images}

def _get_q_img(img_path: str) -> QPixmap:
    """
    灏嗗浘鐗囪矾寰勫姞杞戒负 QPixmap
    :param img_path: 鍥剧墖璺緞
    :return: QPixmap
    """
    #image = QImage()
    image = QPixmap()
    image.load(img_path)
    return image

def _build_act(name: str, parent: QObject, act_func, icon=None) -> Action:
    """
    鏋勫缓鏀瑰彉鑿滃崟鍔ㄤ綔
    :param pet_name: 鑿滃崟鍔ㄤ綔鍚嶇О
    :param parent 鐖剁骇鑿滃崟
    :param act_func: 鑿滃崟鍔ㄤ綔鍑芥暟
    :return:
    """
    if icon:
        act = Action(icon, name, parent)
    else:
        act = Action(name, parent)
    act.triggered.connect(lambda: act_func(name))
    return act

def _build_act_param(name: str, param: str, parent: QObject, act_func) -> Action:
    """
    鏋勫缓鏀瑰彉鑿滃崟鍔ㄤ綔
    :param pet_name: 鑿滃崟鍔ㄤ綔鍚嶇О
    :param parent 鐖剁骇鑿滃崟
    :param act_func: 鑿滃崟鍔ㄤ綔鍑芥暟
    :return:
    """
    act = Action(name, parent)
    act.triggered.connect(lambda: act_func(param))
    return act




