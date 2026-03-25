import os
import json
import ctypes
import sys
from sys import platform
from collections import defaultdict

from PySide6.QtGui import QImage, QPixmap
from DyberPet.conf import PetData, TaskData, ActData, ItemData, DiaryData
from PySide6 import QtCore

if getattr(sys, 'frozen', False):
    # PyInstaller onefile/onedir: resources are unpacked under _MEIPASS.
    _runtime_root = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    _data_root = os.path.dirname(sys.executable)
else:
    _runtime_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    _data_root = _runtime_root

basedir = _runtime_root.replace('\\', '/')
BASEDIR = basedir

if platform == 'linux':
    configdir = os.path.dirname(os.environ['HOME']+'/.config/DyberPet/DyberPet')
    CONFIGDIR = configdir
else:
    configdir = _data_root
    CONFIGDIR = configdir

DEFAULT_THEME_COL = "#009faa"

HELP_URL = "https://github.com/ChaozhongLiu/DyberPet/issues"
PROJECT_URL = "https://github.com/ChaozhongLiu/DyberPet"
DEVDOC_URL = "https://github.com/ChaozhongLiu/DyberPet/blob/main/docs/art_dev.md"
VERSION = "v0.6.7"
AUTHOR = "https://github.com/ChaozhongLiu"
CHARCOLLECT_LINK = "https://github.com/ChaozhongLiu/DyberPet/blob/main/docs/collection.md"
ITEMCOLLECT_LINK = "https://github.com/ChaozhongLiu/DyberPet/blob/main/docs/collection.md"
PETCOLLECT_LINK = "https://github.com/ChaozhongLiu/DyberPet/blob/main/docs/collection.md"

RELEASE_API = "https://api.github.com/repos/ChaozhongLiu/DyberPet/releases/latest"
RELEASE_URL = "https://github.com/ChaozhongLiu/DyberPet/releases/latest"
UPDATE_NEEDED = False

HP_TIERS = [0,50,80,100]
TIER_NAMES = ['Starving', 'Hungry', 'Normal', 'Energetic']
HP_INTERVAL = 2
LVL_BAR_V1 = [20, 120, 300, 600, 1200, 1800, 2400, 3200]
LVL_BAR = [20] + [120]*200
PP_HEART = 0.8
PP_COIN = 0.9
COIN_MU = 10
COIN_SIGMA = 5
COIN_GAIN_MULTIPLIER = 1.0
PP_ITEM = 0.975
PP_AUDIO = 0.8
PP_BUBBLE = 0.15

# Depreciation when sell item to shop
ITEM_DEPRECIATION = 0.75

# Coin reward once a task is checked from Task Panel
SINGLETASK_REWARD = 200
# Coin reward every 5 task
FIVETASK_REWARD = 1500
# Positive FV gain multiplier
FV_GAIN_MULTIPLIER = 2.0
# Multiply HP and FV effect if item is required by bubble `feed_required`
FACTOR_FEED_REQ = 5

HUNGERSTR = "Satiety"
FAVORSTR = "Favorability"

LINK_PERMIT = {"BiliBili":"https://space.bilibili.com/",
               "微博":"https://m.weibo.cn/profile/",
               "抖音": "https://www.douyin.com/user/",
               "GitHub":"https://github.com/",
               "爱发电":"https://afdian.net/a/",
               "TikTok":"https://www.tiktok.com/",
               "YouTube":"https://www.youtube.com/"}

ITEM_BGC = {'consumable': '#EFEBDF',
            'collection': '#e1eaf4',
            'Empty': '#f0f0ef',
            'dialogue': '#e1eaf4',
            'subpet': '#f6eae9',
            'autofeed': '#e7f1e4'}
ITEM_BGC_DEFAULT = '#EFEBDF'
ITEM_BDC = '#B1C790'

# when falling met the screen boundary, 
# it will be bounced back with this speed decay factor
SPEED_DECAY = 0.5
# Scheduler HP decay speed multiplier (1.0 = default speed).
HP_DECAY_MULTIPLIER = 2.0
AUTOFEED_THRESHOLD = 60
EDGE_SNAP_ENABLED = True
EDGE_SNAP_THRESHOLD = 48
PAT_MULTI_CLICK_TALK_THRESHOLD = 12
IDLE_CHAT_INTERACTION_THRESHOLD = 2
IDLE_CHAT_MIN_GAP_SEC = 55
IDLE_CHAT_INTERVAL_MIN_SEC = 140
IDLE_CHAT_INTERVAL_MAX_SEC = 300
REPLY_UPDATE_INTERVAL_SEC = 240

LLM_CONFIG_DEFAULT = {
    "enabled": False,
    "api_type": "deepseek",
    "model": "deepseek-chat",
    "api_url": "https://api.deepseek.com",
    "api_key": "",
    "auto_talk": True
}

LLM_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "models": ["deepseek-chat"],
        "default_url": "https://api.deepseek.com"
    },
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4.1-mini", "gpt-4o-mini"],
        "default_url": "https://api.openai.com/v1"
    },
    "dashscope": {
        "name": "DashScope(Qwen)",
        "models": ["qwen-plus", "qwen-max", "qwen-turbo"],
        "default_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    },
    "custom": {
        "name": "Custom API",
        "models": [],
        "default_url": ""
    }
}

def init():
    # computer system ==================================================
    global platform
    platform = platform

    # check if data directory exists ===================================
    newpath = os.path.join(configdir, 'data')
    if not os.path.exists(newpath):
        os.makedirs(newpath)
    
    global pet_conf
    pet_conf = None

    # Image and animation related variable =============================
    global current_img, previous_img
    # Make img-to-show a global variable for multi-thread behaviors
    current_img = None #QPixmap()
    previous_img = None #Pixmap()
    global current_anchor, previous_anchor
    current_anchor = [0,0]
    previous_anchor = [0,0]

    global onfloor, draging, set_fall, playid
    global mouseposx1,mouseposx2,mouseposx3,mouseposx4,mouseposx5
    global mouseposy1,mouseposy2,mouseposy3,mouseposy4,mouseposy5
    global dragspeedx,dragspeedy,fixdragspeedx, fixdragspeedy, fall_right, gravity, prefall
    # Drag and fall related global variable
    onfloor = 1
    draging = 0
    set_fall = True # default is allow drag
    playid = 0
    mouseposx1,mouseposx2,mouseposx3,mouseposx4,mouseposx5=0,0,0,0,0
    mouseposy1,mouseposy2,mouseposy3,mouseposy4,mouseposy5=0,0,0,0,0
    dragspeedx,dragspeedy=0,0
    fixdragspeedx, fixdragspeedy = 1.0, 1.0
    fall_right = False
    gravity = 0.1
    prefall = 0

    global act_id, current_act, previous_act
    # Select animation to show
    act_id = 0
    current_act, previous_act = None, None

    global showing_dialogue_now
    showing_dialogue_now = False

    # size settings
    global size_factor, screen_scale, font_factor, status_margin, statbar_h, tunable_scale
    try:
        size_factor = 1.0 #ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
    except:
        size_factor = 1.0
    tunable_scale = 1.0

    # buff related arguments
    global HP_stop, FV_stop
    HP_stop = False
    FV_stop = False

    # sound volumn =====================================================
    global volume
    volume = 0.4

    # pet name =========================================================
    global petname
    petname = ''

    # which screen =====================================================
    global screens, current_screen
    screens = []
    current_screen = None
    global pet_hitbox
    pet_hitbox = None

    # Always on top ====================================================
    global on_top_hint, pets
    on_top_hint = True

    # Translations ====================================================
    global lang_dict
    lang_dict = json.load(open(os.path.join(basedir, 'res/language/language.json'), 'r', encoding='utf-8-sig'))

    # Settings =========================================================
    pets = get_petlist(os.path.join(basedir, 'res/role'))
    init_settings()
    global default_pet
    if default_pet not in pets:
        default_pet = pets[0]
    else:
        pets.remove(default_pet)
        pets.sort()
        pets = [default_pet] + pets
    save_settings()

    # Focus Timer
    global focus_timer_on
    focus_timer_on = False

    # Load in pet data ================================================
    global pet_data 
    pet_data = PetData(pets)

    # Load in task data ================================================
    global task_data 
    task_data = TaskData()

    # Load in diary data ================================================
    global diary_data
    diary_data = DiaryData()
    # Catch up diaries for days that passed while app/computer was offline.
    for _pet in pets:
        try:
            diary_data.finalize_pending(_pet)
        except:
            pass

    # Init animation config data ================================================
    global act_data 
    act_data = ActData(pets)

    # Load in Language Choice ==========================================
    global language_code, translator
    change_translator(language_code)

    # Load in items data ==========================================
    global items_data, required_item
    items_data = None
    required_item = None



'''
def init_pet():
    global pet_data 
    pet_data = PetData()
    init_settings()
    save_settings()
'''


def init_settings():
    global file_path, settingGood
    file_path = os.path.join(configdir, 'data/settings.json')

    global gravity, fixdragspeedx, fixdragspeedy, tunable_scale, scale_dict, volume, \
           language_code, on_top_hint, default_pet, defaultAct, themeColor, minipet_scale, \
           toaster_on, usertag_dict, auto_lock, bubble_on, auto_startup, llm_config, \
           edge_snap_enabled, edge_snap_threshold, pat_multi_click_talk_threshold, \
           idle_chat_interaction_threshold, idle_chat_min_gap_sec, \
           idle_chat_interval_min_sec, idle_chat_interval_max_sec, reply_update_interval_sec, \
           usage_guide_shown

    # check json file integrity
    try:
        json.load(open(file_path, 'r', encoding='utf-8-sig'))
        settingGood = True
    except:
        if os.path.isfile(file_path):
            settingGood = False
        else:
            settingGood = True

    if os.path.isfile(file_path) and settingGood:
        data_params = json.load(open(file_path, 'r', encoding='utf-8-sig'))

        fixdragspeedx, fixdragspeedy = data_params['fixdragspeedx'], data_params['fixdragspeedy']
        gravity = data_params['gravity']
        #tunable_scale = data_params['tunable_scale']
        volume = data_params['volume']
        language_code = data_params.get('language_code', QtCore.QLocale().name())
        on_top_hint = data_params.get('on_top_hint', True)
        default_pet = data_params.get('default_pet', pets[0])
        defaultAct = data_params.get('defaultAct', {})
        themeColor = data_params.get('themeColor', None)

        # Fix a bug version distributed to users =============
        if defaultAct is None:
            defaultAct = {}
        elif type(defaultAct) == str:
            defaultAct = {}

        for pet in pets:
            defaultAct[pet] = defaultAct.get(pet, None)
        #=====================================================

        # update for app <= v0.2.2 ===========================
        if language_code == 'CN':
            language_code = QtCore.QLocale().name()
        #=====================================================

        # v0.4.8 update ======================================
        global set_fall
        set_fall = data_params.get('set_fall', True)
        #=====================================================

        # v0.5.0 update ======================================
        # First time open v0.5.0, get the original 
        # tunable_scale as all default
        tunable_scale = data_params.get('tunable_scale', 1.0)
        # v0.5.0 tunable_scales are specified for each character
        scale_dict_tmp = data_params.get('scale_dict', {})
        scale_dict = {}
        for pet in pets:
            pet_scale = scale_dict_tmp.get(pet, tunable_scale)
            # Ensure type is int
            try:
                pet_scale = float(pet_scale)
            except:
                pet_scale = 1.0
            pet_scale = max( 0, min(5, pet_scale) )
            scale_dict[pet] = pet_scale
        tunable_scale = scale_dict[default_pet]

        # mini-pet scale settings
        minipet_scale = data_params.get('minipet_scale', defaultdict(dict))
        minipet_scale = check_dict_datatype(minipet_scale, dict, {})
        minipet_scale = defaultdict(dict, minipet_scale)
        for minipet, sdict in minipet_scale.items():
            minipet_scale[minipet] = check_dict_datatype(sdict, float, 1.0)
        #=====================================================

        # v0.5.3 Toaster can be turned off
        toaster_on = data_params.get('toaster_on', True)
        #=====================================================

        # v0.6.1 User Tag (how pet will call the user)
        usertag_dict_tmp = data_params.get('usertag_dict', {})
        usertag_dict = {}
        for pet in pets:
            usertag = usertag_dict_tmp.get(pet, '')
            usertag_dict[pet] = usertag

        # v0.6.5 stop HP & FV changes when screen locked
        auto_lock = data_params.get('auto_lock', False)
        #=====================================================

        # v0.6.7 Bubble can be turned off
        bubble_on = data_params.get('bubble_on', True)
        #=====================================================
        auto_startup = data_params.get('auto_startup', False)
        edge_snap_enabled = data_params.get('edge_snap_enabled', EDGE_SNAP_ENABLED)
        edge_snap_threshold = int(data_params.get('edge_snap_threshold', EDGE_SNAP_THRESHOLD))
        pat_multi_click_talk_threshold = int(data_params.get('pat_multi_click_talk_threshold', PAT_MULTI_CLICK_TALK_THRESHOLD))
        idle_chat_interaction_threshold = int(data_params.get('idle_chat_interaction_threshold', IDLE_CHAT_INTERACTION_THRESHOLD))
        idle_chat_min_gap_sec = int(data_params.get('idle_chat_min_gap_sec', IDLE_CHAT_MIN_GAP_SEC))
        idle_chat_interval_min_sec = int(data_params.get('idle_chat_interval_min_sec', IDLE_CHAT_INTERVAL_MIN_SEC))
        idle_chat_interval_max_sec = int(data_params.get('idle_chat_interval_max_sec', IDLE_CHAT_INTERVAL_MAX_SEC))
        reply_update_interval_sec = int(data_params.get('reply_update_interval_sec', REPLY_UPDATE_INTERVAL_SEC))
        usage_guide_shown = bool(data_params.get('usage_guide_shown', False))
        idle_chat_interval_min_sec = max(30, idle_chat_interval_min_sec)
        idle_chat_interval_max_sec = max(idle_chat_interval_min_sec, idle_chat_interval_max_sec)
        idle_chat_min_gap_sec = max(10, idle_chat_min_gap_sec)
        pat_multi_click_talk_threshold = max(3, pat_multi_click_talk_threshold)
        idle_chat_interaction_threshold = max(1, idle_chat_interaction_threshold)
        reply_update_interval_sec = max(60, reply_update_interval_sec)
        llm_config = data_params.get('llm_config', LLM_CONFIG_DEFAULT.copy())
        if type(llm_config) != dict:
            llm_config = LLM_CONFIG_DEFAULT.copy()

        # Compatibility: migrate old local schema to remote schema
        if 'api_type' not in llm_config:
            llm_config['api_type'] = llm_config.get('backend', LLM_CONFIG_DEFAULT['api_type'])
        if 'api_url' not in llm_config:
            llm_config['api_url'] = llm_config.get('endpoint', '')
        if 'api_key' not in llm_config:
            llm_config['api_key'] = ''

        for key, value in LLM_CONFIG_DEFAULT.items():
            llm_config[key] = llm_config.get(key, value)

        provider = llm_config.get('api_type', LLM_CONFIG_DEFAULT['api_type'])
        if provider not in LLM_PROVIDERS:
            llm_config['api_type'] = LLM_CONFIG_DEFAULT['api_type']
            provider = llm_config['api_type']

        if not llm_config.get('api_url'):
            llm_config['api_url'] = LLM_PROVIDERS[provider].get('default_url', '')

        models = LLM_PROVIDERS[provider].get('models', [])
        if models and llm_config.get('model') not in models:
            llm_config['model'] = models[0]


    else:
        fixdragspeedx, fixdragspeedy = 1.0, 1.0
        gravity = 0.1
        volume = 0.5
        language_code = QtCore.QLocale().name()
        on_top_hint = True
        default_pet = pets[0]
        defaultAct = {}
        themeColor = None
        for pet in pets:
            defaultAct[pet] = defaultAct.get(pet, None)
        scale_dict = {}
        for pet in pets:
            scale_dict[pet] = 1.0
        tunable_scale = 1.0
        minipet_scale = defaultdict(dict)
        toaster_on = True
        bubble_on = True
        usertag_dict = {}
        auto_lock = False
        auto_startup = False
        edge_snap_enabled = EDGE_SNAP_ENABLED
        edge_snap_threshold = EDGE_SNAP_THRESHOLD
        pat_multi_click_talk_threshold = PAT_MULTI_CLICK_TALK_THRESHOLD
        idle_chat_interaction_threshold = IDLE_CHAT_INTERACTION_THRESHOLD
        idle_chat_min_gap_sec = IDLE_CHAT_MIN_GAP_SEC
        idle_chat_interval_min_sec = IDLE_CHAT_INTERVAL_MIN_SEC
        idle_chat_interval_max_sec = IDLE_CHAT_INTERVAL_MAX_SEC
        reply_update_interval_sec = REPLY_UPDATE_INTERVAL_SEC
        usage_guide_shown = False
        llm_config = LLM_CONFIG_DEFAULT.copy()
    check_locale()
    save_settings()

def save_settings():
    global file_path, set_fall, gravity, fixdragspeedx, fixdragspeedy, scale_dict, volume, \
           language_code, on_top_hint, default_pet, defaultAct, themeColor, minipet_scale, \
           toaster_on, usertag_dict, auto_lock, bubble_on, auto_startup, llm_config, \
           edge_snap_enabled, edge_snap_threshold, pat_multi_click_talk_threshold, \
           idle_chat_interaction_threshold, idle_chat_min_gap_sec, \
           idle_chat_interval_min_sec, idle_chat_interval_max_sec, reply_update_interval_sec, \
           usage_guide_shown

    data_js = {'gravity':gravity,
               'set_fall': set_fall,
               'fixdragspeedx':fixdragspeedx,
               'fixdragspeedy':fixdragspeedy,
               'usertag_dict':usertag_dict,
               'scale_dict':scale_dict,
               'minipet_scale':minipet_scale,
               'volume':volume,
               'on_top_hint':on_top_hint,
               'toaster_on':toaster_on,
               'bubble_on':bubble_on,
               'default_pet':default_pet,
               'defaultAct':defaultAct,
               'language_code':language_code,
               'themeColor':themeColor,
               'auto_lock':auto_lock,
               'auto_startup': auto_startup,
               'edge_snap_enabled': edge_snap_enabled,
               'edge_snap_threshold': edge_snap_threshold,
               'pat_multi_click_talk_threshold': pat_multi_click_talk_threshold,
               'idle_chat_interaction_threshold': idle_chat_interaction_threshold,
               'idle_chat_min_gap_sec': idle_chat_min_gap_sec,
               'idle_chat_interval_min_sec': idle_chat_interval_min_sec,
               'idle_chat_interval_max_sec': idle_chat_interval_max_sec,
               'reply_update_interval_sec': reply_update_interval_sec,
               'usage_guide_shown': usage_guide_shown,
               'llm_config': llm_config
               }

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data_js, f, ensure_ascii=False, indent=4)

def get_petlist(dirname):
    folders = os.listdir(dirname)
    pets = []
    # subpets = []
    # v0.3.3 subpet now moved to folder: res/pet/
    for folder in folders:
        folder_path = os.path.join(dirname, folder)
        if folder != 'sys' and os.path.isdir(folder_path):
            pets.append(folder)
            #conf_path = os.path.join(folder_path, 'pet_conf.json')
            #conf = dict(json.load(open(conf_path, 'r', encoding='utf-8-sig')))
            #subpets += [i for i in conf.get('subpet',{}).keys()]
    pets = list(set(pets))
    #subpets = list(set(subpets))
    #for subpet in subpets:
    #    pets.remove(subpet)
    return pets

def change_translator(language_code):
    global translator
    if language_code == 'en_US':
        translator = None
    else:
        translator = QtCore.QTranslator()
        translator.load(QtCore.QLocale(language_code), "langs", ".", os.path.join(basedir, "res/language/"))

        global TIER_NAMES, HUNGERSTR, FAVORSTR
        TIER_NAMES = [translator.translate("others", i) for i in TIER_NAMES] #.encode('utf-8')
        HUNGER_trans = translator.translate("others", HUNGERSTR) #.encode('utf-8'))
        if HUNGER_trans:
            HUNGERSTR = HUNGER_trans
        FAVOR_trans = translator.translate("others", FAVORSTR) #.encode('utf-8'))
        if FAVOR_trans:
            FAVORSTR = FAVOR_trans

def check_locale():
    global language_code, lang_dict
    if language_code not in lang_dict.values():
        if language_code.split("_")[0] == 'zh':
            language_code = "zh_CN"
        else:
            language_code = "en_US"
            

def check_dict_datatype(raw_dict:dict, dtype, default_value):
    """
    Checks the datatype of values in a dictionary. If a value does not match the specified datatype, it is replaced with a default value.

    Parameters:
    raw_dict (dict): The dictionary to check.
    dtype (type): The expected datatype for the values.
    default_value: The value to replace if the datatype does not match.

    Returns:
    dict: A new dictionary with corrected datatypes.
    """
    return {k: (v if isinstance(v, dtype) else default_value) for k, v in raw_dict.items()}
