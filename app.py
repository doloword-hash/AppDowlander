import os
import io
import json
import uuid
import hashlib
import random
import requests
import re
import base64
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, session, send_file, jsonify
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from oauthlib.oauth2 import WebApplicationClient
from cryptography.fernet import Fernet
import google.generativeai as genai
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'burmalnod_secret_key_2026_ultra_mega_imba_6000_lines'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
IS_MAINTENANCE_MODE = False

# =====================================================================
# 🔑 НАСТРОЙКИ И КЛЮЧИ
# =====================================================================
MASTER_KEY = b'ключ'
ENCRYPTED_CONFIG = b'конфиг'
cipher = Fernet(MASTER_KEY)
_config = json.loads(cipher.decrypt(ENCRYPTED_CONFIG).decode('utf-8'))
ADMIN_PASSWORD = _config['admin_pass']
FOLDER_ID = _config['folder_id']
GOOGLE_CLIENT_ID = _config['client_id']
GOOGLE_CLIENT_SECRET = _config['client_secret']
GEMINI_API_KEY = 'AQXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
genai.configure(api_key=GEMINI_API_KEY)

SERVICE_ACCOUNT_FILE = 'credentials.json'
LOCAL_CHAT_FILE = 'messages.txt'
PROFILES_FILE = 'profiles.json'
PENDING_STICKERS_FILE = 'pending_stickers.json'
PINNED_FILE = 'pinned.json'
GROUPS_FILE = 'groups.json'
BOTS_FILE = 'bots.json'
BLACKLIST_FILE = 'blacklist.json'
STICKER_HASH_FILE = 'sticker_hashes.json'
STICKER_PACKS_FILE = 'sticker_packs.json'
POSTS_FILE = 'posts.json'
TASKS_FILE = 'tasks_progress.json'
FM_VIEWERS_FILE = 'fm_viewers.json'
REACTIONS_FILE = 'reactions.json'
DECORATIONS_FILE = 'decorations.json'
USER_DECORATIONS_FILE = 'user_decorations.json'
ACHIEVEMENTS_FILE = 'achievements.json'
USER_ACHIEVEMENTS_FILE = 'user_achievements.json'
DECORATION_UPLOADS_FILE = 'decoration_uploads.json'

STATIC_DIR = os.path.join(app.root_path, 'static')
PENDING_STICKERS_DIR = os.path.join(STATIC_DIR, 'stickers', 'pending')
APPROVED_STICKERS_DIR = os.path.join(STATIC_DIR, 'stickers', 'custom')
VOICE_DIR = os.path.join(STATIC_DIR, 'voice')
UPLOADS_DIR = os.path.join(STATIC_DIR, 'uploads')
GALLERY_DIR = os.path.join(STATIC_DIR, 'gallery')
DECORATIONS_DIR = os.path.join(STATIC_DIR, 'decorations')
DECORATION_IMAGES_DIR = os.path.join(DECORATIONS_DIR, 'images')
DECORATION_FRAMES_DIR = os.path.join(DECORATIONS_DIR, 'frames')
DECORATION_EFFECTS_DIR = os.path.join(DECORATIONS_DIR, 'effects')
DECORATION_BACKGROUNDS_DIR = os.path.join(DECORATIONS_DIR, 'backgrounds')
DECORATION_BADGES_DIR = os.path.join(DECORATIONS_DIR, 'badges')

os.makedirs(PENDING_STICKERS_DIR, exist_ok=True)
os.makedirs(APPROVED_STICKERS_DIR, exist_ok=True)
os.makedirs(VOICE_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(GALLERY_DIR, exist_ok=True)
os.makedirs(DECORATIONS_DIR, exist_ok=True)
os.makedirs(DECORATION_IMAGES_DIR, exist_ok=True)
os.makedirs(DECORATION_FRAMES_DIR, exist_ok=True)
os.makedirs(DECORATION_EFFECTS_DIR, exist_ok=True)
os.makedirs(DECORATION_BACKGROUNDS_DIR, exist_ok=True)
os.makedirs(DECORATION_BADGES_DIR, exist_ok=True)

USER_ACTIVITY = {}
FM_VIEWERS = {}
AUTO_ADMIN_EMAIL = 'doloword@gmail.com'
INITIAL_BURMALNETS = 5
SPAM_LIMIT_SECONDS = 30
SUBSCRIPTION_DURATION_DAYS = 2
SUBSCRIPTION_PRICE = 12

# =====================================================================
# 🎯 СИСТЕМА ЗАДАНИЙ
# =====================================================================
TASK_POOL = [
    {'id': 'send_messages_5', 'title': '💬 Общительный', 'description': 'Отправь 5 сообщений в любой чат', 'target': 5, 'reward': 3, 'action': 'send_message'},
    {'id': 'send_messages_15', 'title': '🗣️ Болтун', 'description': 'Отправь 15 сообщений в чатах', 'target': 15, 'reward': 7, 'action': 'send_message'},
    {'id': 'send_sticker', 'title': '🎨 Стикеровод', 'description': 'Отправь 3 стикера', 'target': 3, 'reward': 4, 'action': 'send_sticker'},
    {'id': 'create_post', 'title': '📝 Блогер', 'description': 'Опубликуй 1 пост', 'target': 1, 'reward': 5, 'action': 'create_post'},
    {'id': 'like_posts_3', 'title': '❤️ Оценщик', 'description': 'Поставь 3 лайка под постами', 'target': 3, 'reward': 2, 'action': 'like_post'},
    {'id': 'upload_file', 'title': '📎 Файлообменщик', 'description': 'Загрузи 1 файл в чат', 'target': 1, 'reward': 4, 'action': 'upload_file'},
    {'id': 'voice_message', 'title': '🎤 Голосистый', 'description': 'Запиши 2 голосовых сообщения', 'target': 2, 'reward': 5, 'action': 'send_voice'},
    {'id': 'open_private_chat', 'title': '👥 Друг', 'description': 'Открой 1 приватный чат', 'target': 1, 'reward': 3, 'action': 'open_private'},
    {'id': 'update_profile', 'title': '✨ Модник', 'description': 'Обнови свой профиль', 'target': 1, 'reward': 3, 'action': 'update_profile'},
    {'id': 'send_messages_30', 'title': '👑 Легенда чата', 'description': 'Отправь 30 сообщений за день', 'target': 30, 'reward': 12, 'action': 'send_message'},
    {'id': 'react_messages', 'title': '🔥 Реактор', 'description': 'Поставь 5 реакций на сообщения', 'target': 5, 'reward': 3, 'action': 'react'},
    {'id': 'create_group', 'title': '🏠 Организатор', 'description': 'Создай 1 группу', 'target': 1, 'reward': 6, 'action': 'create_group'},
    {'id': 'buy_decoration', 'title': '💎 Коллекционер', 'description': 'Купи 1 украшение', 'target': 1, 'reward': 5, 'action': 'buy_decoration'},
    {'id': 'create_decoration', 'title': '🎨 Дизайнер', 'description': 'Создай 1 украшение', 'target': 1, 'reward': 8, 'action': 'create_decoration'},
    {'id': 'equip_decoration', 'title': '👗 Модник PRO', 'description': 'Надень 3 украшения одновременно', 'target': 3, 'reward': 6, 'action': 'equip_decoration'},
]

ACHIEVEMENT_POOL = [
    {'id': 'first_message', 'title': '👋 Первое сообщение', 'description': 'Отправь первое сообщение', 'icon': '💬', 'reward': 5},
    {'id': 'message_master', 'title': '💬 Мастер общения', 'description': 'Отправь 100 сообщений', 'icon': '🗨️', 'reward': 20},
    {'id': 'sticker_collector', 'title': '🎨 Коллекционер стикеров', 'description': 'Собери 5 паков стикеров', 'icon': '🖼️', 'reward': 15},
    {'id': 'decoration_master', 'title': '💎 Мастер украшений', 'description': 'Купи 10 украшений', 'icon': '✨', 'reward': 25},
    {'id': 'legendary_collector', 'title': '🌟 Легендарный коллекционер', 'description': 'Купи 3 легендарных украшения', 'icon': '⭐', 'reward': 50},
    {'id': 'social_butterfly', 'title': '🦋 Социальная бабочка', 'description': 'Создай 5 групп', 'icon': '👥', 'reward': 30},
    {'id': 'content_creator', 'title': '📝 Создатель контента', 'description': 'Опубликуй 20 постов', 'icon': '📰', 'reward': 25},
    {'id': 'file_sharer', 'title': '📎 Делитель файлов', 'description': 'Загрузи 50 файлов', 'icon': '📁', 'reward': 20},
    {'id': 'voice_star', 'title': '🎤 Голосовая звезда', 'description': 'Запиши 30 голосовых', 'icon': '🎙️', 'reward': 25},
    {'id': 'reaction_king', 'title': '👑 Король реакций', 'description': 'Поставь 200 реакций', 'icon': '😍', 'reward': 30},
]

# =====================================================================
# 🎨 СИСТЕМА УКРАШЕНИЙ - РАСШИРЕННАЯ
# =====================================================================
DEFAULT_DECORATIONS = {
    # === ЗНАЧКИ (BADGES) ===
    'dec_gold_badge': {
        'id': 'dec_gold_badge', 'name': '🏆 Золотой значок', 'type': 'badge',
        'description': 'Блестящий золотой значок рядом с ником. Подчёркивает ваш статус!',
        'price': 15, 'emoji': '🏆', 'color': '#f59e0b', 'rarity': 'rare',
        'animation': 'glow', 'effect_intensity': 0.8,
        'has_custom_image': False, 'custom_image_url': '',
        'position': 'after_nick', 'size': 'small'
    },
    'dec_crown_badge': {
        'id': 'dec_crown_badge', 'name': '👑 Королевская корона', 'type': 'badge',
        'description': 'Величественная корона над вашим ником. Для настоящих королей!',
        'price': 40, 'emoji': '👑', 'color': '#f59e0b', 'rarity': 'legendary',
        'animation': 'float', 'effect_intensity': 1.0,
        'has_custom_image': False, 'custom_image_url': '',
        'position': 'above_nick', 'size': 'medium'
    },
    'dec_skull_badge': {
        'id': 'dec_skull_badge', 'name': '💀 Череп', 'type': 'badge',
        'description': 'Дерзкий значок с черепом. Для тех, кто не боится!',
        'price': 12, 'emoji': '💀', 'color': '#64748b', 'rarity': 'common',
        'animation': 'none', 'effect_intensity': 0.5,
        'has_custom_image': False, 'custom_image_url': '',
        'position': 'after_nick', 'size': 'small'
    },
    'dec_star_badge': {
        'id': 'dec_star_badge', 'name': '⭐ Яркая звезда', 'type': 'badge',
        'description': 'Яркая звезда рядом с ником. Сияй ярче всех!',
        'price': 18, 'emoji': '⭐', 'color': '#fbbf24', 'rarity': 'rare',
        'animation': 'rotate', 'effect_intensity': 0.9,
        'has_custom_image': False, 'custom_image_url': '',
        'position': 'after_nick', 'size': 'small'
    },
    'dec_diamond_badge': {
        'id': 'dec_diamond_badge', 'name': '💎 Бриллиант', 'type': 'badge',
        'description': 'Сияющий бриллиант. Драгоценный аксессуар!',
        'price': 35, 'emoji': '💎', 'color': '#38bdf8', 'rarity': 'epic',
        'animation': 'sparkle', 'effect_intensity': 1.0,
        'has_custom_image': False, 'custom_image_url': '',
        'position': 'after_nick', 'size': 'medium'
    },
    'dec_heart_badge': {
        'id': 'dec_heart_badge', 'name': '💖 Сердце', 'type': 'badge',
        'description': 'Милое пульсирующее сердце',
        'price': 14, 'emoji': '💖', 'color': '#ec4899', 'rarity': 'rare',
        'animation': 'pulse', 'effect_intensity': 0.8,
        'has_custom_image': False, 'custom_image_url': '',
        'position': 'after_nick', 'size': 'small'
    },
    'dec_fire_badge': {
        'id': 'dec_fire_badge', 'name': '🔥 Огонь', 'type': 'badge',
        'description': 'Пылающий огонь. Покажи свою страсть!',
        'price': 20, 'emoji': '🔥', 'color': '#ef4444', 'rarity': 'epic',
        'animation': 'flicker', 'effect_intensity': 0.9,
        'has_custom_image': False, 'custom_image_url': '',
        'position': 'after_nick', 'size': 'small'
    },
    'dec_lightning_badge': {
        'id': 'dec_lightning_badge', 'name': '⚡ Молния', 'type': 'badge',
        'description': 'Электрическая молния. Будь быстрым как闪电!',
        'price': 25, 'emoji': '⚡', 'color': '#fbbf24', 'rarity': 'epic',
        'animation': 'electric', 'effect_intensity': 0.95,
        'has_custom_image': False, 'custom_image_url': '',
        'position': 'after_nick', 'size': 'small'
    },
    
    # === РАМКИ (FRAMES) ===
    'dec_diamond_frame': {
        'id': 'dec_diamond_frame', 'name': '💎 Бриллиантовая рамка', 'type': 'frame',
        'description': 'Роскошная рамка вокруг аватарки с бриллиантовым блеском',
        'price': 25, 'emoji': '💎', 'color': '#38bdf8', 'rarity': 'epic',
        'animation': 'pulse', 'effect_intensity': 0.9,
        'has_custom_image': False, 'custom_image_url': '',
        'frame_style': 'diamond', 'border_width': 3
    },
    'dec_ice_frame': {
        'id': 'dec_ice_frame', 'name': '❄️ Ледяная рамка', 'type': 'frame',
        'description': 'Морозная рамка с кристаллами льда',
        'price': 18, 'emoji': '❄️', 'color': '#06b6d4', 'rarity': 'rare',
        'animation': 'shimmer', 'effect_intensity': 0.7,
        'has_custom_image': False, 'custom_image_url': '',
        'frame_style': 'ice', 'border_width': 3
    },
    'dec_fire_frame': {
        'id': 'dec_fire_frame', 'name': '🔥 Огненная рамка', 'type': 'frame',
        'description': 'Горящая рамка из пламени',
        'price': 22, 'emoji': '🔥', 'color': '#ef4444', 'rarity': 'rare',
        'animation': 'flicker', 'effect_intensity': 0.85,
        'has_custom_image': False, 'custom_image_url': '',
        'frame_style': 'fire', 'border_width': 3
    },
    'dec_rainbow_frame': {
        'id': 'dec_rainbow_frame', 'name': '🌈 Радужная рамка', 'type': 'frame',
        'description': 'Переливающаяся радужная рамка',
        'price': 30, 'emoji': '🌈', 'color': '#ec4899', 'rarity': 'legendary',
        'animation': 'rainbow', 'effect_intensity': 1.0,
        'has_custom_image': False, 'custom_image_url': '',
        'frame_style': 'rainbow', 'border_width': 4
    },
    'dec_gold_frame': {
        'id': 'dec_gold_frame', 'name': '🥇 Золотая рамка', 'type': 'frame',
        'description': 'Роскошная золотая рамка',
        'price': 28, 'emoji': '🥇', 'color': '#f59e0b', 'rarity': 'epic',
        'animation': 'glow', 'effect_intensity': 0.9,
        'has_custom_image': False, 'custom_image_url': '',
        'frame_style': 'gold', 'border_width': 4
    },
    'dec_neon_frame': {
        'id': 'dec_neon_frame', 'name': '💜 Неоновая рамка', 'type': 'frame',
        'description': 'Яркая неоновая рамка в стиле киберпанк',
        'price': 24, 'emoji': '💜', 'color': '#a855f7', 'rarity': 'epic',
        'animation': 'neon', 'effect_intensity': 0.9,
        'has_custom_image': False, 'custom_image_url': '',
        'frame_style': 'neon', 'border_width': 3
    },
    
    # === ЭФФЕКТЫ (EFFECTS) ===
    'dec_fire_effect': {
        'id': 'dec_fire_effect', 'name': '🔥 Огненный эффект', 'type': 'effect',
        'description': 'Горящее пламя вокруг аватарки',
        'price': 20, 'emoji': '🔥', 'color': '#ef4444', 'rarity': 'rare',
        'animation': 'burn', 'effect_intensity': 0.9,
        'has_custom_image': False, 'custom_image_url': '',
        'effect_type': 'fire'
    },
    'dec_rainbow_aura': {
        'id': 'dec_rainbow_aura', 'name': '🌈 Радужная аура', 'type': 'effect',
        'description': 'Переливающаяся аура вокруг аватарки',
        'price': 35, 'emoji': '🌈', 'color': '#ec4899', 'rarity': 'legendary',
        'animation': 'aura', 'effect_intensity': 1.0,
        'has_custom_image': False, 'custom_image_url': '',
        'effect_type': 'rainbow'
    },
    'dec_neon_glow': {
        'id': 'dec_neon_glow', 'name': '💚 Неон свечение', 'type': 'effect',
        'description': 'Ярко-зелёное неоновое свечение',
        'price': 22, 'emoji': '💚', 'color': '#22c55e', 'rarity': 'epic',
        'animation': 'neon', 'effect_intensity': 0.85,
        'has_custom_image': False, 'custom_image_url': '',
        'effect_type': 'neon'
    },
    'dec_electric_effect': {
        'id': 'dec_electric_effect', 'name': '⚡ Электрический эффект', 'type': 'effect',
        'description': 'Молнии вокруг аватарки',
        'price': 28, 'emoji': '⚡', 'color': '#fbbf24', 'rarity': 'epic',
        'animation': 'electric', 'effect_intensity': 0.95,
        'has_custom_image': False, 'custom_image_url': '',
        'effect_type': 'electric'
    },
    'dec_magic_effect': {
        'id': 'dec_magic_effect', 'name': '✨ Магический эффект', 'type': 'effect',
        'description': 'Магические искры и частицы',
        'price': 32, 'emoji': '✨', 'color': '#a855f7', 'rarity': 'legendary',
        'animation': 'magic', 'effect_intensity': 1.0,
        'has_custom_image': False, 'custom_image_url': '',
        'effect_type': 'magic'
    },
    'dec_snow_effect': {
        'id': 'dec_snow_effect', 'name': '❄️ Снежный эффект', 'type': 'effect',
        'description': 'Падающие снежинки вокруг профиля',
        'price': 18, 'emoji': '❄️', 'color': '#e0f2fe', 'rarity': 'rare',
        'animation': 'snow', 'effect_intensity': 0.8,
        'has_custom_image': False, 'custom_image_url': '',
        'effect_type': 'snow'
    },
    'dec_hearts_effect': {
        'id': 'dec_hearts_effect', 'name': '💕 Летающие сердечки', 'type': 'effect',
        'description': 'Милые летающие сердечки',
        'price': 20, 'emoji': '💕', 'color': '#ec4899', 'rarity': 'rare',
        'animation': 'hearts', 'effect_intensity': 0.8,
        'has_custom_image': False, 'custom_image_url': '',
        'effect_type': 'hearts'
    },
    
    # === ФОНЫ (BACKGROUNDS) ===
    'dec_space_bg': {
        'id': 'dec_space_bg', 'name': '🌌 Космический фон', 'type': 'background',
        'description': 'Галактический фон профиля',
        'price': 30, 'emoji': '🌌', 'color': '#8b5cf6', 'rarity': 'legendary',
        'animation': 'stars', 'effect_intensity': 0.9,
        'has_custom_image': False, 'custom_image_url': '',
        'bg_type': 'space'
    },
    'dec_sunset_bg': {
        'id': 'dec_sunset_bg', 'name': '🌅 Закатный фон', 'type': 'background',
        'description': 'Тёплый фон заката',
        'price': 15, 'emoji': '🌅', 'color': '#f97316', 'rarity': 'rare',
        'animation': 'gradient', 'effect_intensity': 0.7,
        'has_custom_image': False, 'custom_image_url': '',
        'bg_type': 'sunset'
    },
    'dec_ocean_bg': {
        'id': 'dec_ocean_bg', 'name': '🌊 Океанский фон', 'type': 'background',
        'description': 'Глубокий океанский фон',
        'price': 20, 'emoji': '🌊', 'color': '#0ea5e9', 'rarity': 'rare',
        'animation': 'waves', 'effect_intensity': 0.75,
        'has_custom_image': False, 'custom_image_url': '',
        'bg_type': 'ocean'
    },
    'dec_forest_bg': {
        'id': 'dec_forest_bg', 'name': '🌲 Лесной фон', 'type': 'background',
        'description': 'Таинственный лесной фон',
        'price': 18, 'emoji': '🌲', 'color': '#16a34a', 'rarity': 'rare',
        'animation': 'leaves', 'effect_intensity': 0.7,
        'has_custom_image': False, 'custom_image_url': '',
        'bg_type': 'forest'
    },
    'dec_galaxy_bg': {
        'id': 'dec_galaxy_bg', 'name': '🌠 Галактический фон', 'type': 'background',
        'description': 'Величественная галактика',
        'price': 38, 'emoji': '🌠', 'color': '#7c3aed', 'rarity': 'legendary',
        'animation': 'galaxy', 'effect_intensity': 1.0,
        'has_custom_image': False, 'custom_image_url': '',
        'bg_type': 'galaxy'
    },
    'dec_matrix_bg': {
        'id': 'dec_matrix_bg', 'name': '💻 Матричный фон', 'type': 'background',
        'description': 'Падающие зелёные символы Матрицы',
        'price': 25, 'emoji': '💻', 'color': '#22c55e', 'rarity': 'epic',
        'animation': 'matrix', 'effect_intensity': 0.85,
        'has_custom_image': False, 'custom_image_url': '',
        'bg_type': 'matrix'
    },
    
    # === НИКНЕЙМ ЭФФЕКТЫ ===
    'dec_gold_nick': {
        'id': 'dec_gold_nick', 'name': '🥇 Золотой ник', 'type': 'nickname',
        'description': 'Золотой градиентный никнейм',
        'price': 25, 'emoji': '🥇', 'color': '#f59e0b', 'rarity': 'epic',
        'animation': 'gold_gradient', 'effect_intensity': 0.9,
        'has_custom_image': False, 'custom_image_url': '',
        'nick_style': 'gold'
    },
    'dec_rainbow_nick': {
        'id': 'dec_rainbow_nick', 'name': '🌈 Радужный ник', 'type': 'nickname',
        'description': 'Переливающийся радужный ник',
        'price': 35, 'emoji': '🌈', 'color': '#ec4899', 'rarity': 'legendary',
        'animation': 'rainbow_text', 'effect_intensity': 1.0,
        'has_custom_image': False, 'custom_image_url': '',
        'nick_style': 'rainbow'
    },
    'dec_fire_nick': {
        'id': 'dec_fire_nick', 'name': '🔥 Огненный ник', 'type': 'nickname',
        'description': 'Горящий огненный никнейм',
        'price': 28, 'emoji': '🔥', 'color': '#ef4444', 'rarity': 'epic',
        'animation': 'fire_text', 'effect_intensity': 0.95,
        'has_custom_image': False, 'custom_image_url': '',
        'nick_style': 'fire'
    },
    'dec_neon_nick': {
        'id': 'dec_neon_nick', 'name': '💜 Неоновый ник', 'type': 'nickname',
        'description': 'Светящийся неоновый ник',
        'price': 24, 'emoji': '💜', 'color': '#a855f7', 'rarity': 'epic',
        'animation': 'neon_text', 'effect_intensity': 0.9,
        'has_custom_image': False, 'custom_image_url': '',
        'nick_style': 'neon'
    },
}

# =====================================================================
# 🛡️ СИСТЕМА САМОВОССТАНОВЛЕНИЯ
# =====================================================================
def safe_load_json(filename, default_data):
    if not os.path.exists(filename):
        safe_save_json(filename, default_data)
        return default_data
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Файл {filename} повреждён ({e}). Пересоздание...")
        try: os.remove(filename)
        except Exception: pass
        safe_save_json(filename, default_data)
        return default_data

def safe_save_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка записи в {filename}: {e}")

def cleanup_old_files():
    now = datetime.now()
    max_age = timedelta(days=1)
    for target_dir in [VOICE_DIR, UPLOADS_DIR]:
        if not os.path.exists(target_dir): continue
        for filename in os.listdir(target_dir):
            filepath = os.path.join(target_dir, filename)
            if os.path.isfile(filepath):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if now - file_mtime > max_age:
                    try: os.remove(filepath)
                    except Exception: pass

def load_pinned_messages(): return safe_load_json(PINNED_FILE, {})
def save_pinned_messages(data): safe_save_json(PINNED_FILE, data)
def load_groups(): return safe_load_json(GROUPS_FILE, {})
def save_groups(data): safe_save_json(GROUPS_FILE, data)
def load_bots(): return safe_load_json(BOTS_FILE, {})
def save_bots(data): safe_save_json(BOTS_FILE, data)
def load_profiles(): return safe_load_json(PROFILES_FILE, {})
def save_profiles(profiles): safe_save_json(PROFILES_FILE, profiles)
def load_pending_stickers(): return safe_load_json(PENDING_STICKERS_FILE, [])
def save_pending_stickers(data): safe_save_json(PENDING_STICKERS_FILE, data)
def load_blacklist(): return safe_load_json(BLACKLIST_FILE, {})
def save_blacklist(data): safe_save_json(BLACKLIST_FILE, data)
def load_sticker_hashes(): return safe_load_json(STICKER_HASH_FILE, {})
def save_sticker_hashes(data): safe_save_json(STICKER_HASH_FILE, data)
def load_sticker_packs(): return safe_load_json(STICKER_PACKS_FILE, {'packs': {}})
def save_sticker_packs(data): safe_save_json(STICKER_PACKS_FILE, data)
def load_posts(): return safe_load_json(POSTS_FILE, [])
def save_posts(data): safe_save_json(POSTS_FILE, data)
def load_tasks_progress(): return safe_load_json(TASKS_FILE, {})
def save_tasks_progress(data): safe_save_json(TASKS_FILE, data)
def load_fm_viewers(): return safe_load_json(FM_VIEWERS_FILE, {})
def save_fm_viewers(data): safe_save_json(FM_VIEWERS_FILE, data)
def load_reactions(): return safe_load_json(REACTIONS_FILE, {})
def save_reactions(data): safe_save_json(REACTIONS_FILE, data)
def load_decorations(): return safe_load_json(DECORATIONS_FILE, DEFAULT_DECORATIONS)
def save_decorations(data): safe_save_json(DECORATIONS_FILE, data)
def load_user_decorations(): return safe_load_json(USER_DECORATIONS_FILE, {})
def save_user_decorations(data): safe_save_json(USER_DECORATIONS_FILE, data)
def load_achievements(): return safe_load_json(ACHIEVEMENTS_FILE, ACHIEVEMENT_POOL)
def save_achievements(data): safe_save_json(ACHIEVEMENTS_FILE, data)
def load_user_achievements(): return safe_load_json(USER_ACHIEVEMENTS_FILE, {})
def save_user_achievements(data): safe_save_json(USER_ACHIEVEMENTS_FILE, data)

# =====================================================================
# 🎨 ФУНКЦИИ РАБОТЫ С УКРАШЕНИЯМИ И ИХ ИЗОБРАЖЕНИЯМИ
# =====================================================================
def get_decoration_image_path(dec_id, dec_type):
    """Получить путь к кастомному изображению украшения"""
    type_dirs = {
        'badge': DECORATION_BADGES_DIR,
        'frame': DECORATION_FRAMES_DIR,
        'effect': DECORATION_EFFECTS_DIR,
        'background': DECORATION_BACKGROUNDS_DIR,
        'nickname': DECORATION_IMAGES_DIR,
    }
    base_dir = type_dirs.get(dec_type, DECORATION_IMAGES_DIR)
    for ext in ['.png', '.gif', '.webp', '.jpg', '.jpeg']:
        path = os.path.join(base_dir, f"{dec_id}{ext}")
        if os.path.exists(path):
            return f"/static/decorations/{os.path.basename(base_dir)}/{dec_id}{ext}"
    return None

def save_decoration_image(file, dec_id, dec_type):
    """Сохранить изображение украшения и вернуть URL"""
    if not file or not file.filename:
        return None
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.png', '.gif', '.webp', '.jpg', '.jpeg']:
        return None
    
    type_dirs = {
        'badge': DECORATION_BADGES_DIR,
        'frame': DECORATION_FRAMES_DIR,
        'effect': DECORATION_EFFECTS_DIR,
        'background': DECORATION_BACKGROUNDS_DIR,
        'nickname': DECORATION_IMAGES_DIR,
    }
    base_dir = type_dirs.get(dec_type, DECORATION_IMAGES_DIR)
    filename = f"{dec_id}{ext}"
    filepath = os.path.join(base_dir, filename)
    file.save(filepath)
    return f"/static/decorations/{os.path.basename(base_dir)}/{filename}"

def delete_decoration_image(dec_id, dec_type):
    """Удалить изображение украшения"""
    type_dirs = {
        'badge': DECORATION_BADGES_DIR,
        'frame': DECORATION_FRAMES_DIR,
        'effect': DECORATION_EFFECTS_DIR,
        'background': DECORATION_BACKGROUNDS_DIR,
        'nickname': DECORATION_IMAGES_DIR,
    }
    base_dir = type_dirs.get(dec_type, DECORATION_IMAGES_DIR)
    for ext in ['.png', '.gif', '.webp', '.jpg', '.jpeg']:
        path = os.path.join(base_dir, f"{dec_id}{ext}")
        if os.path.exists(path):
            try: os.remove(path)
            except Exception: pass

# =====================================================================
# 🎯 ЗАДАНИЯ И ПОДПИСКА
# =====================================================================
def get_daily_task_ids():
    today = datetime.now().strftime('%Y-%m-%d')
    seed = sum(ord(c) for c in today)
    rng = random.Random(seed)
    indices = rng.sample(range(len(TASK_POOL)), 5)
    return [TASK_POOL[i]['id'] for i in indices]

def is_user_subscribed(user_key):
    if not user_key: return False
    prof = get_user_profile(user_key)
    until_str = prof.get('subscription_until')
    if not until_str: return False
    try:
        until = datetime.fromisoformat(until_str)
        return datetime.now() < until
    except Exception:
        return False

def process_subscription_payment(user_key):
    if not user_key: return False, None
    profiles = load_profiles()
    prof = profiles.get(user_key, {})
    if prof.get('is_admin'): return False, None
    until_str = prof.get('subscription_until')
    if not until_str: return False, None
    try:
        until = datetime.fromisoformat(until_str)
        now = datetime.now()
        if now < until:
            last_payment_str = prof.get('last_subscription_payment')
            if last_payment_str:
                last_payment = datetime.fromisoformat(last_payment_str)
                days_since_payment = (now - last_payment).days
                if days_since_payment >= SUBSCRIPTION_DURATION_DAYS:
                    balance = prof.get('burmalnets', INITIAL_BURMALNETS)
                    if balance >= SUBSCRIPTION_PRICE:
                        prof['burmalnets'] = balance - SUBSCRIPTION_PRICE
                        prof['last_subscription_payment'] = now.isoformat()
                        prof['subscription_until'] = (until + timedelta(days=SUBSCRIPTION_DURATION_DAYS)).isoformat()
                        profiles[user_key] = prof
                        save_profiles(profiles)
                        return True, f"Списано {SUBSCRIPTION_PRICE} бурмалкоинов"
                    else:
                        prof['subscription_until'] = None
                        prof['last_subscription_payment'] = None
                        profiles[user_key] = prof
                        save_profiles(profiles)
                        return False, "Недостаточно средств, подписка отключена"
            else:
                prof['last_subscription_payment'] = now.isoformat()
                profiles[user_key] = prof
                save_profiles(profiles)
    except Exception as e:
        print(f"Ошибка обработки подписки: {e}")
    return False, None

def get_user_daily_tasks(user_key):
    if not user_key: return []
    today = datetime.now().strftime('%Y-%m-%d')
    progress = load_tasks_progress()
    user_progress = progress.get(user_key, {})
    if user_progress.get('date') != today:
        user_progress = {'date': today, 'tasks': {}, 'claimed': []}
        progress[user_key] = user_progress
        save_tasks_progress(progress)
    task_ids = get_daily_task_ids()
    result = []
    subscribed = is_user_subscribed(user_key)
    for tid in task_ids:
        task_def = next((t for t in TASK_POOL if t['id'] == tid), None)
        if not task_def: continue
        task_data = user_progress['tasks'].get(tid, {'progress': 0})
        claimed = tid in user_progress.get('claimed', [])
        reward = task_def['reward'] * (2 if subscribed else 1)
        result.append({
            'id': tid, 'title': task_def['title'], 'description': task_def['description'],
            'target': task_def['target'], 'reward': reward,
            'progress': min(task_data.get('progress', 0), task_def['target']),
            'completed': claimed,
        })
    return result

def increment_task_progress(user_key, action):
    if not user_key: return
    today = datetime.now().strftime('%Y-%m-%d')
    progress = load_tasks_progress()
    user_progress = progress.get(user_key, {})
    if user_progress.get('date') != today:
        user_progress = {'date': today, 'tasks': {}, 'claimed': []}
    task_ids = get_daily_task_ids()
    for tid in task_ids:
        if tid in user_progress.get('claimed', []): continue
        task_def = next((t for t in TASK_POOL if t['id'] == tid), None)
        if task_def and task_def['action'] == action:
            if tid not in user_progress['tasks']:
                user_progress['tasks'][tid] = {'progress': 0}
            user_progress['tasks'][tid]['progress'] += 1
    progress[user_key] = user_progress
    save_tasks_progress(progress)

def claim_task_reward(user_key, task_id):
    today = datetime.now().strftime('%Y-%m-%d')
    progress = load_tasks_progress()
    user_progress = progress.get(user_key, {})
    if user_progress.get('date') != today: return None, 'Задания обновились'
    task_def = next((t for t in TASK_POOL if t['id'] == task_id), None)
    if not task_def: return None, 'Задание не найдено'
    task_data = user_progress['tasks'].get(task_id, {})
    if task_data.get('progress', 0) < task_def['target']: return None, 'Задание не выполнено'
    if task_id in user_progress.get('claimed', []): return None, 'Награда уже получена'
    subscribed = is_user_subscribed(user_key)
    reward = task_def['reward'] * (2 if subscribed else 1)
    profiles = load_profiles()
    prof = profiles.get(user_key, {})
    prof['burmalnets'] = prof.get('burmalnets', INITIAL_BURMALNETS) + reward
    profiles[user_key] = prof
    save_profiles(profiles)
    if 'claimed' not in user_progress: user_progress['claimed'] = []
    user_progress['claimed'].append(task_id)
    progress[user_key] = user_progress
    save_tasks_progress(progress)
    return reward, None

# =====================================================================
# 🏆 ДОСТИЖЕНИЯ
# =====================================================================
def check_achievements(user_key):
    if not user_key: return []
    user_achievements = load_user_achievements()
    user_data = user_achievements.get(user_key, {'unlocked': [], 'claimed': []})
    profiles = load_profiles()
    prof = profiles.get(user_key, {})
    new_achievements = []
    
    owned_packs = prof.get('owned_packs', [])
    if len(owned_packs) >= 5 and 'sticker_collector' not in user_data['unlocked']:
        user_data['unlocked'].append('sticker_collector')
        new_achievements.append('sticker_collector')
    
    user_decs = load_user_decorations()
    owned_decorations = user_decs.get(user_key, {}).get('owned', [])
    if len(owned_decorations) >= 10 and 'decoration_master' not in user_data['unlocked']:
        user_data['unlocked'].append('decoration_master')
        new_achievements.append('decoration_master')
    
    decorations = load_decorations()
    legendary_count = sum(1 for dec_id in owned_decorations if decorations.get(dec_id, {}).get('rarity') == 'legendary')
    if legendary_count >= 3 and 'legendary_collector' not in user_data['unlocked']:
        user_data['unlocked'].append('legendary_collector')
        new_achievements.append('legendary_collector')
    
    user_achievements[user_key] = user_data
    save_user_achievements(user_achievements)
    return new_achievements

# =====================================================================
# 🎨 УКРАШЕНИЯ - ЛОГИКА
# =====================================================================
def get_user_owned_decorations(user_key):
    if not user_key: return []
    user_decs = load_user_decorations()
    return user_decs.get(user_key, {}).get('owned', [])

def get_user_equipped_decorations(user_key):
    if not user_key: return []
    user_decs = load_user_decorations()
    return user_decs.get(user_key, {}).get('equipped', [])

def equip_decoration(user_key, dec_id):
    if not user_key or not dec_id: return False, 'Некорректные данные'
    user_decs = load_user_decorations()
    user_data = user_decs.get(user_key, {'owned': [], 'equipped': []})
    owned = user_data.get('owned', [])
    equipped = user_data.get('equipped', [])
    if dec_id not in owned: return False, 'Украшение не куплено'
    decorations = load_decorations()
    dec_info = decorations.get(dec_id, {})
    dec_type = dec_info.get('type')
    new_equipped = [e for e in equipped if decorations.get(e, {}).get('type') != dec_type]
    new_equipped.append(dec_id)
    user_data['equipped'] = new_equipped
    user_decs[user_key] = user_data
    save_user_decorations(user_decs)
    increment_task_progress(user_key, 'equip_decoration')
    return True, 'Украшение надето'

def unequip_decoration(user_key, dec_id):
    if not user_key or not dec_id: return False, 'Некорректные данные'
    user_decs = load_user_decorations()
    user_data = user_decs.get(user_key, {'owned': [], 'equipped': []})
    equipped = user_data.get('equipped', [])
    if dec_id in equipped: equipped.remove(dec_id)
    user_data['equipped'] = equipped
    user_decs[user_key] = user_data
    save_user_decorations(user_decs)
    return True, 'Украшение снято'

def buy_decoration(user_key, dec_id):
    if not user_key or not dec_id: return False, 'Некорректные данные'
    decorations = load_decorations()
    dec_info = decorations.get(dec_id)
    if not dec_info: return False, 'Украшение не найдено'
    user_decs = load_user_decorations()
    user_data = user_decs.get(user_key, {'owned': [], 'equipped': []})
    owned = user_data.get('owned', [])
    if dec_id in owned: return False, 'Украшение уже в вашей коллекции'
    profiles = load_profiles()
    prof = profiles.get(user_key, {})
    balance = prof.get('burmalnets', INITIAL_BURMALNETS)
    price = dec_info.get('price', 0)
    if balance < price:
        return False, f'Недостаточно бурмалкоинов (нужно {price}, у вас {int(balance)})'
    prof['burmalnets'] = balance - price
    profiles[user_key] = prof
    save_profiles(profiles)
    owned.append(dec_id)
    user_data['owned'] = owned
    user_decs[user_key] = user_data
    save_user_decorations(user_decs)
    increment_task_progress(user_key, 'buy_decoration')
    check_achievements(user_key)
    return True, 'Украшение куплено!'

def create_custom_decoration(user_key, decoration_data, image_file=None):
    """Создать пользовательское украшение с возможностью загрузки картинки"""
    if not user_key: return False, 'Не авторизован', None
    
    decorations = load_decorations()
    dec_id = f"dec_custom_{uuid.uuid4().hex[:8]}"
    dec_type = decoration_data.get('type', 'badge')
    
    # Проверяем и сохраняем изображение
    has_custom_image = False
    custom_image_url = ''
    if image_file:
        image_url = save_decoration_image(image_file, dec_id, dec_type)
        if image_url:
            has_custom_image = True
            custom_image_url = image_url
    
    new_decoration = {
        'id': dec_id,
        'name': decoration_data.get('name', 'Мое украшение'),
        'type': dec_type,
        'description': decoration_data.get('description', ''),
        'price': decoration_data.get('price', 10),
        'emoji': decoration_data.get('emoji', '✨'),
        'color': decoration_data.get('color', '#38bdf8'),
        'rarity': decoration_data.get('rarity', 'common'),
        'animation': decoration_data.get('animation', 'none'),
        'effect_intensity': decoration_data.get('effect_intensity', 0.5),
        'has_custom_image': has_custom_image,
        'custom_image_url': custom_image_url,
        'creator': user_key,
        'created_at': datetime.now().isoformat(),
        'position': decoration_data.get('position', 'after_nick'),
        'size': decoration_data.get('size', 'medium'),
    }
    
    decorations[dec_id] = new_decoration
    save_decorations(decorations)
    
    # Автоматически добавляем создателю в коллекцию
    user_decs = load_user_decorations()
    user_data = user_decs.get(user_key, {'owned': [], 'equipped': []})
    if dec_id not in user_data.get('owned', []):
        if 'owned' not in user_data: user_data['owned'] = []
        user_data['owned'].append(dec_id)
        user_decs[user_key] = user_data
        save_user_decorations(user_decs)
    
    increment_task_progress(user_key, 'create_decoration')
    check_achievements(user_key)
    return True, 'Украшение создано!', dec_id

def get_user_full_decorations(user_key):
    """Получить полную информацию о надетых украшениях пользователя (для отображения везде)"""
    if not user_key: return {'badge': None, 'frame': None, 'effect': None, 'background': None, 'nickname': None, 'all': []}
    
    user_decs = load_user_decorations()
    user_data = user_decs.get(user_key, {'equipped': []})
    equipped_ids = user_data.get('equipped', [])
    decorations = load_decorations()
    
    result = {'badge': None, 'frame': None, 'effect': None, 'background': None, 'nickname': None, 'all': []}
    
    for dec_id in equipped_ids:
        dec_info = decorations.get(dec_id)
        if not dec_info: continue
        
        # Добавляем URL картинки если есть
        if dec_info.get('has_custom_image') and dec_info.get('custom_image_url'):
            dec_info['image_url'] = dec_info['custom_image_url']
        else:
            # Проверяем наличие файла
            img_path = get_decoration_image_path(dec_id, dec_info.get('type'))
            if img_path:
                dec_info['image_url'] = img_path
                dec_info['has_custom_image'] = True
            else:
                dec_info['image_url'] = None
        
        result['all'].append(dec_info)
        dec_type = dec_info.get('type')
        if dec_type in result:
            result[dec_type] = dec_info
    
    return result

# =====================================================================
# ⚙️ GOOGLE SERVICES & UTILS
# =====================================================================
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
client = WebApplicationClient(GOOGLE_CLIENT_ID)
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Файл '{SERVICE_ACCOUNT_FILE}' не найден!")
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

def get_redirect_uri():
    host_url = request.host_url.rstrip('/')
    if host_url.startswith("http://") and not host_url.startswith("http://127.0.0.1") and not host_url.startswith("http://localhost"):
        host_url = host_url.replace("http://", "https://", 1)
    return f"{host_url}/login/callback"

def get_user_profile(user_key):
    profiles = load_profiles()
    key = user_key.lower() if user_key else ""
    return profiles.get(key, {})

def get_user_burmalnets(user_key):
    prof = get_user_profile(user_key)
    return prof.get('burmalnets', INITIAL_BURMALNETS)

def get_user_owned_packs(user_key):
    prof = get_user_profile(user_key)
    return prof.get('owned_packs', [])

def get_sticker_packs(user_key=None):
    packs = {
        'pack1': {'name': '🎨 Базовый пак', 'stickers': ['/static/stickers/pack1/1.png', '/static/stickers/pack1/2.png', '/static/stickers/pack1/3.png', '/static/stickers/pack1/4.png', '/static/stickers/pack1/5.png'], 'owner_key': None, 'price': 0, 'for_sale': False},
        'pack2': {'name': '🌟 Премиум пак', 'stickers': ['/static/stickers/pack2/1.png', '/static/stickers/pack2/2.png', '/static/stickers/pack2/3.png', '/static/stickers/pack2/4.png', '/static/stickers/pack2/5.png'], 'owner_key': None, 'price': 0, 'for_sale': False},
    }
    sticker_packs_data = load_sticker_packs()
    for pack_id, pack_info in sticker_packs_data.get('packs', {}).items():
        if pack_info.get('stickers') or (user_key and pack_info.get('owner_key') == user_key):
            sticker_urls = [f"/static/stickers/custom/{s}" for s in pack_info.get('stickers', [])]
            packs[pack_id] = {
                'name': pack_info.get('name', 'Мой пак'),
                'stickers': sticker_urls,
                'owner_key': pack_info.get('owner_key'),
                'price': pack_info.get('price', 0),
                'for_sale': pack_info.get('for_sale', False)
            }
    return packs

def make_private_chat_id(user1_id, user2_id):
    sorted_ids = sorted([str(user1_id).lower(), str(user2_id).lower()])
    return f"private_{sorted_ids[0]}_{sorted_ids[1]}"

def compute_file_hash(filepath):
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def get_last_seen(user_key):
    if not user_key: return "Не в сети"
    last = USER_ACTIVITY.get(user_key.lower())
    if not last: return "Давно"
    now = datetime.now()
    diff = now - last
    if diff < timedelta(seconds=30): return "🟢 В сети"
    if diff < timedelta(minutes=1): return "🟡 Меньше минуты назад"
    if diff < timedelta(hours=1): return f"🟡 {diff.seconds // 60} мин. назад"
    if diff < timedelta(days=1): return f"🔴 {diff.seconds // 3600} ч. назад"
    return f"⚫ {last.strftime('%d.%m.%Y в %H:%M')}"

def is_user_blocked(current_user_key, target_user_key):
    if not current_user_key or not target_user_key: return False
    profiles = load_profiles()
    target_prof = profiles.get(target_user_key.lower(), {})
    if target_prof.get('is_admin'): return False
    blacklist = load_blacklist()
    return target_user_key.lower() in blacklist.get(current_user_key.lower(), [])

def can_manage_group(user_key, group_info):
    return session.get('is_admin', False) or group_info.get('owner_key') == user_key

def can_manage_pack(user_key, pack_id):
    sticker_packs_data = load_sticker_packs()
    pack_info = sticker_packs_data.get('packs', {}).get(pack_id, {})
    if session.get('is_admin', False): return True
    if pack_id in ['pack1', 'pack2']: return False
    return pack_info.get('owner_key') == user_key

def can_manage_bot(user_key, bot_id):
    bots = load_bots()
    bot = bots.get(bot_id, {})
    if session.get('is_admin', False): return True
    return bot.get('owner_key') == user_key

# =====================================================================
# 🛡️ РАБОТА С ЧАТОМ
# =====================================================================
def load_raw_messages():
    if not os.path.exists(LOCAL_CHAT_FILE): return []
    valid_lines = []
    try:
        with open(LOCAL_CHAT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line_str = line.strip()
                if line_str: valid_lines.append(line_str)
    except Exception:
        try: os.remove(LOCAL_CHAT_FILE)
        except Exception: pass
        return []
    return valid_lines

def save_raw_messages(lines):
    with open(LOCAL_CHAT_FILE, 'w', encoding='utf-8') as f:
        for line in lines: f.write(line + '\n')

def load_chat_messages(target_chat_id='general', current_user=None):
    cleanup_old_files()
    raw_lines = load_raw_messages()
    messages = []
    now = datetime.now()
    curr_id = (current_user.get('email') or current_user.get('nickname')).lower() if current_user else None
    profiles = load_profiles()
    blacklist = load_blacklist()
    my_blocked = blacklist.get(curr_id, []) if curr_id else []
    reactions = load_reactions()
    
    for line in raw_lines:
        try:
            decrypted = cipher.decrypt(line.encode('utf-8')).decode('utf-8')
            data = json.loads(decrypted)
            chat_id = data.get('chat_id', 'general')
            if chat_id.startswith('private_') or chat_id.startswith('botchat_'):
                parts = chat_id.replace('private_', '').replace('botchat_', '').split('_')
                if not curr_id or curr_id not in parts: continue
            if chat_id.startswith('group_'):
                groups = load_groups()
                ginfo = groups.get(chat_id, {})
                if not ginfo.get('is_public', False):
                    members = ginfo.get('members', [])
                    if curr_id and curr_id not in members and ginfo.get('owner_key') != curr_id:
                        continue
            if chat_id != target_chat_id: continue
            user_key = (data.get('email') or data.get('user')).lower()
            if curr_id and user_key in my_blocked:
                sender_prof = profiles.get(user_key, {})
                if not sender_prof.get('is_admin'): continue
            prof = profiles.get(user_key, {})
            if prof.get('picture'): data['picture'] = prof['picture']
            data['main_nick'] = f"@{user_key.split('@')[0]}"
            data['custom_nick'] = prof.get('custom_nick') or data.get('user')
            data['is_subscribed'] = is_user_subscribed(user_key)
            
            # === ПОЛНАЯ ИНФОРМАЦИЯ ОБ УКРАШЕНИЯХ ===
            data['decorations'] = get_user_full_decorations(user_key)
            
            if data.get('is_bot'):
                data['is_online'] = True
            else:
                last_active = USER_ACTIVITY.get(user_key)
                data['is_online'] = bool(last_active and (now - last_active) < timedelta(seconds=30))
            msg_id = data.get('id')
            data['reactions'] = reactions.get(msg_id, {})
            messages.append(data)
        except Exception: pass
    return messages

def get_user_chat_list(current_user):
    chat_list = [{'id': 'general', 'name': '🌐 Общий чат', 'avatar': ''}]
    if not current_user: return chat_list
    curr_id = (current_user.get('email') or current_user.get('nickname')).lower()
    groups = load_groups()
    for gid, ginfo in groups.items():
        if ginfo.get('is_public', False) or ginfo.get('owner_key') == curr_id or curr_id in ginfo.get('members', []):
            chat_list.append({'id': gid, 'name': f"👥 {ginfo['name']}", 'avatar': ginfo.get('avatar', ''), 'is_group': True})
    bots = load_bots()
    for bot_id, bot_info in bots.items():
        if bot_info.get('enabled', True):
            if bot_info.get('owner_key') == curr_id or session.get('is_admin', False):
                chat_list.append({'id': f"botchat_{curr_id}_{bot_id}", 'name': f"🤖 {bot_info.get('name', 'Бот')}", 'avatar': bot_info.get('avatar', ''), 'is_bot': True, 'bot_id': bot_id})
    raw_lines = load_raw_messages()
    profiles = load_profiles()
    private_chats = {}
    for line in raw_lines:
        try:
            decrypted = cipher.decrypt(line.encode('utf-8')).decode('utf-8')
            data = json.loads(decrypted)
            cid = data.get('chat_id', '')
            if cid.startswith('private_'):
                parts = cid.replace('private_', '').split('_')
                if curr_id in parts:
                    partner_id = parts[0] if parts[1] == curr_id else parts[1]
                    if is_user_blocked(curr_id, partner_id): continue
                    partner_prof = profiles.get(partner_id, {})
                    # Добавляем украшения
                    partner_decs = get_user_full_decorations(partner_id)
                    private_chats[cid] = {
                        'name': partner_prof.get('custom_nick') or f"@{partner_id.split('@')[0]}",
                        'avatar': partner_prof.get('picture', ''),
                        'partner_id': partner_id,
                        'decorations': partner_decs
                    }
        except Exception: pass
    for cid, info in private_chats.items():
        chat_list.append({
            'id': cid, 'name': f"💬 {info['name']}",
            'avatar': info['avatar'], 'partner_id': info['partner_id'],
            'decorations': info['decorations']
        })
    return chat_list

def save_chat_message(user_dict, chat_id='general', text="", sticker_url="", voice_url="", local_file=None, reply_to=None, forwarded_from=None, recipient_name="", call_url=""):
    email = user_dict.get('email', '')
    nickname = user_dict.get('nickname', 'Аноним')
    picture = user_dict.get('picture', '')
    msg_time = (datetime.now() + timedelta(hours=3)).strftime("%H:%M")
    msg_obj = {'id': str(uuid.uuid4())[:8], 'chat_id': chat_id, 'email': email, 'user': nickname, 'recipient_name': recipient_name, 'time': msg_time, 'picture': picture, 'text': text, 'sticker': sticker_url, 'voice': voice_url, 'local_file': local_file, 'call_url': call_url, 'reply_to': reply_to, 'forwarded_from': forwarded_from, 'is_bot': user_dict.get('is_bot', False)}
    json_str = json.dumps(msg_obj, ensure_ascii=False)
    encrypted_line = cipher.encrypt(json_str.encode('utf-8')).decode('utf-8')
    with open(LOCAL_CHAT_FILE, 'a', encoding='utf-8') as f:
        f.write(encrypted_line + '\n')
    raw_lines = load_raw_messages()
    if len(raw_lines) > 500: save_raw_messages(raw_lines[-500:])
    if not user_dict.get('is_bot'):
        u_key = (user_dict.get('email') or user_dict.get('nickname')).lower()
        if sticker_url: increment_task_progress(u_key, 'send_sticker')
        elif voice_url: increment_task_progress(u_key, 'send_voice')
        elif text: increment_task_progress(u_key, 'send_message')
        if local_file: increment_task_progress(u_key, 'upload_file')
    if chat_id.startswith('botchat_') and not user_dict.get('is_bot'):
        trigger_bot_in_chat(chat_id, text, nickname)

def trigger_bot_in_chat(chat_id, user_text, user_nick):
    parts = chat_id.split('_')
    if len(parts) < 3: return
    bot_id = parts[2]
    bots = load_bots()
    bot = bots.get(bot_id)
    if not bot or not bot.get('enabled', True): return
    script = bot.get('script', '')
    if not script: return
    def reply(bot_msg):
        bot_user = {'email': f"{bot_id}@bot", 'nickname': bot.get('name', 'Бот'), 'picture': bot.get('avatar', ''), 'is_bot': True}
        save_chat_message(user_dict=bot_user, chat_id=chat_id, text=str(bot_msg))
    local_vars = {'text': user_text, 'user': user_nick, 'chat_id': chat_id, 'reply': reply, 'bot_name': bot.get('name', 'Бот')}
    try:
        import builtins
        exec(script, {"builtins": builtins}, local_vars)
    except Exception as e:
        print(f"⚠️ Ошибка скрипта бота {bot.get('name')}: {e}")

def delete_chat_message(msg_id, current_user, is_admin, chat_id=''):
    raw_lines = load_raw_messages()
    new_lines = []
    curr_email = current_user.get('email') if current_user else None
    curr_nick = current_user.get('nickname') if current_user else None
    is_private_chat = chat_id.startswith('private_')
    for line in raw_lines:
        try:
            decrypted = cipher.decrypt(line.encode('utf-8')).decode('utf-8')
            data = json.loads(decrypted)
            if data.get('id') == msg_id:
                msg_email = data.get('email', '')
                msg_user = data.get('user', '')
                is_owner = (curr_email and msg_email and curr_email.lower() == msg_email.lower()) or (curr_nick and msg_user and curr_nick == msg_user)
                if is_admin or is_owner or is_private_chat: continue
            new_lines.append(line)
        except Exception:
            new_lines.append(line)
    save_raw_messages(new_lines)

def edit_chat_message(msg_id, new_text, current_user, is_admin):
    raw_lines = load_raw_messages()
    new_lines = []
    curr_email = current_user.get('email') if current_user else None
    curr_nick = current_user.get('nickname') if current_user else None
    for line in raw_lines:
        try:
            decrypted = cipher.decrypt(line.encode('utf-8')).decode('utf-8')
            data = json.loads(decrypted)
            if data.get('id') == msg_id:
                msg_email = data.get('email', '')
                msg_user = data.get('user', '')
                is_owner = (curr_email and msg_email and curr_email.lower() == msg_email.lower()) or (curr_nick and msg_user and curr_nick == msg_user)
                if is_admin or is_owner:
                    data['text'] = new_text + " ✏️"
                    data['edited'] = True
                    json_str = json.dumps(data, ensure_ascii=False)
                    line = cipher.encrypt(json_str.encode('utf-8')).decode('utf-8')
                    new_lines.append(line)
                    continue
            new_lines.append(line)
        except Exception:
            new_lines.append(line)
    save_raw_messages(new_lines)

# =====================================================================
# 🎨 HTML ШАБЛОН - ПОЛНЫЙ С СИСТЕМОЙ УКРАШЕНИЙ ВЕЗДЕ
# =====================================================================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Бурмалдод — Мессенджер нового поколения</title>
<style>
* { box-sizing: border-box; touch-action: manipulation; }
body { 
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    color: #f8fafc; 
    margin: 0; 
    padding: 15px; 
    padding-bottom: 30px; 
    min-height: 100vh;
    background-attachment: fixed;
}
body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: 
        radial-gradient(circle at 20% 30%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
        radial-gradient(circle at 80% 70%, rgba(258, 96, 219, 0.2) 0%, transparent 50%),
        radial-gradient(circle at 40% 80%, rgba(56, 189, 248, 0.2) 0%, transparent 50%);
    pointer-events: none;
    z-index: -1;
}

/* ========================================= */
/* 🎨 СИСТЕМА АНИМАЦИЙ УКРАШЕНИЙ             */
/* ========================================= */
@keyframes dec-glow {
    0%, 100% { filter: drop-shadow(0 0 4px currentColor) drop-shadow(0 0 8px currentColor); transform: scale(1); }
    50% { filter: drop-shadow(0 0 8px currentColor) drop-shadow(0 0 16px currentColor); transform: scale(1.05); }
}
@keyframes dec-float {
    0%, 100% { transform: translateY(0px) rotate(0deg); }
    25% { transform: translateY(-3px) rotate(-2deg); }
    75% { transform: translateY(-3px) rotate(2deg); }
}
@keyframes dec-rotate {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes dec-sparkle {
    0%, 100% { opacity: 1; transform: scale(1) rotate(0deg); filter: brightness(1); }
    50% { opacity: 0.8; transform: scale(1.15) rotate(180deg); filter: brightness(1.5); }
}
@keyframes dec-pulse {
    0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 currentColor; }
    50% { transform: scale(1.03); box-shadow: 0 0 12px 4px currentColor; }
}
@keyframes dec-shimmer {
    0% { background-position: -200% center; }
    100% { background-position: 200% center; }
}
@keyframes dec-rainbow {
    0% { filter: hue-rotate(0deg) drop-shadow(0 0 6px currentColor); }
    100% { filter: hue-rotate(360deg) drop-shadow(0 0 12px currentColor); }
}
@keyframes dec-flicker {
    0%, 100% { opacity: 1; transform: scale(1) translateY(0); }
    25% { opacity: 0.9; transform: scale(1.05) translateY(-2px); }
    50% { opacity: 1; transform: scale(0.98) translateY(1px); }
    75% { opacity: 0.95; transform: scale(1.02) translateY(-1px); }
}
@keyframes dec-electric {
    0%, 100% { filter: drop-shadow(0 0 2px #fff) drop-shadow(0 0 6px currentColor); transform: translateX(0); }
    25% { filter: drop-shadow(0 0 4px #fff) drop-shadow(0 0 10px currentColor); transform: translateX(-1px); }
    50% { filter: drop-shadow(0 0 6px #fff) drop-shadow(0 0 14px currentColor); transform: translateX(1px); }
    75% { filter: drop-shadow(0 0 4px #fff) drop-shadow(0 0 10px currentColor); transform: translateX(-1px); }
}
@keyframes dec-magic {
    0%, 100% { transform: rotate(0deg) scale(1); filter: drop-shadow(0 0 4px currentColor); }
    25% { transform: rotate(90deg) scale(1.1); filter: drop-shadow(0 0 8px currentColor); }
    50% { transform: rotate(180deg) scale(1.05); filter: drop-shadow(0 0 12px currentColor); }
    75% { transform: rotate(270deg) scale(1.1); filter: drop-shadow(0 0 8px currentColor); }
}
@keyframes dec-burn {
    0%, 100% { filter: drop-shadow(0 -4px 6px #ef4444) drop-shadow(0 -8px 12px #f59e0b); transform: scaleY(1); }
    50% { filter: drop-shadow(0 -6px 10px #ef4444) drop-shadow(0 -12px 18px #f59e0b); transform: scaleY(1.08); }
}
@keyframes dec-aura {
    0%, 100% { box-shadow: 0 0 20px 8px currentColor, inset 0 0 20px currentColor; }
    50% { box-shadow: 0 0 30px 12px currentColor, inset 0 0 30px currentColor; }
}
@keyframes dec-neon {
    0%, 100% { filter: drop-shadow(0 0 2px currentColor) drop-shadow(0 0 4px currentColor) drop-shadow(0 0 8px currentColor); }
    50% { filter: drop-shadow(0 0 4px currentColor) drop-shadow(0 0 8px currentColor) drop-shadow(0 0 16px currentColor); }
}
@keyframes dec-stars {
    0%, 100% { background-position: 0 0; }
    100% { background-position: 100px 100px; }
}
@keyframes dec-gradient {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}
@keyframes dec-waves {
    0%, 100% { transform: translateX(0) translateY(0); }
    50% { transform: translateX(5px) translateY(-2px); }
}
@keyframes dec-leaves {
    0% { transform: translateY(0) rotate(0deg); }
    100% { transform: translateY(100px) rotate(360deg); }
}
@keyframes dec-galaxy {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes dec-snow {
    0% { transform: translateY(-10px) translateX(0); opacity: 0; }
    10% { opacity: 1; }
    100% { transform: translateY(100px) translateX(20px); opacity: 0; }
}
@keyframes dec-hearts {
    0% { transform: translateY(0) scale(0.5); opacity: 0; }
    20% { opacity: 1; }
    100% { transform: translateY(-80px) scale(1.2); opacity: 0; }
}
@keyframes dec-gold-gradient {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}
@keyframes dec-rainbow-text {
    0% { background-position: 0% 50%; filter: hue-rotate(0deg); }
    100% { background-position: 200% 50%; filter: hue-rotate(360deg); }
}
@keyframes dec-fire-text {
    0%, 100% { text-shadow: 0 0 4px #ef4444, 0 0 8px #f59e0b, 0 -4px 12px #ef4444; }
    50% { text-shadow: 0 0 8px #ef4444, 0 0 16px #f59e0b, 0 -8px 20px #ef4444; }
}
@keyframes dec-neon-text {
    0%, 100% { text-shadow: 0 0 2px currentColor, 0 0 4px currentColor, 0 0 8px currentColor, 0 0 12px currentColor; }
    50% { text-shadow: 0 0 4px currentColor, 0 0 8px currentColor, 0 0 16px currentColor, 0 0 24px currentColor; }
}
@keyframes dec-matrix {
    0% { background-position: 0 0; }
    100% { background-position: 0 100px; }
}

/* ========================================= */
/* 🎨 CSS КЛАССЫ УКРАШЕНИЙ                   */
/* ========================================= */
.decoration-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    margin-left: 4px;
    vertical-align: middle;
    position: relative;
}
.decoration-badge img {
    width: 20px;
    height: 20px;
    object-fit: contain;
    vertical-align: middle;
}
.decoration-badge.size-small { font-size: 14px; }
.decoration-badge.size-small img { width: 16px; height: 16px; }
.decoration-badge.size-medium { font-size: 18px; }
.decoration-badge.size-medium img { width: 22px; height: 22px; }
.decoration-badge.size-large { font-size: 22px; }
.decoration-badge.size-large img { width: 28px; height: 28px; }

.decoration-badge.position-above {
    position: absolute;
    top: -12px;
    left: 50%;
    transform: translateX(-50%);
    margin-left: 0;
    z-index: 10;
}
.decoration-badge.position-before {
    margin-left: 0;
    margin-right: 4px;
}

.decoration-frame {
    position: absolute;
    top: -4px;
    left: -4px;
    right: -4px;
    bottom: -4px;
    border-radius: 50%;
    pointer-events: none;
    z-index: 5;
}
.decoration-frame img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    border-radius: 50%;
}

.decoration-effect {
    position: absolute;
    top: -10px;
    left: -10px;
    right: -10px;
    bottom: -10px;
    border-radius: 50%;
    pointer-events: none;
    z-index: 1;
}
.decoration-effect img {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.decoration-background {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    border-radius: inherit;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
}
.decoration-background img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0.6;
}

.decoration-nickname {
    display: inline-block;
    font-weight: bold;
    position: relative;
}

/* Анимации */
.anim-glow { animation: dec-glow 2s ease-in-out infinite; }
.anim-float { animation: dec-float 3s ease-in-out infinite; }
.anim-rotate { animation: dec-rotate 4s linear infinite; }
.anim-sparkle { animation: dec-sparkle 1.5s ease-in-out infinite; }
.anim-pulse { animation: dec-pulse 2s ease-in-out infinite; }
.anim-shimmer { animation: dec-shimmer 3s linear infinite; background-size: 200% auto; }
.anim-rainbow { animation: dec-rainbow 4s linear infinite; }
.anim-flicker { animation: dec-flicker 1.2s ease-in-out infinite; }
.anim-electric { animation: dec-electric 0.8s ease-in-out infinite; }
.anim-magic { animation: dec-magic 3s ease-in-out infinite; }
.anim-burn { animation: dec-burn 1.5s ease-in-out infinite; }
.anim-aura { animation: dec-aura 3s ease-in-out infinite; }
.anim-neon { animation: dec-neon 1.5s ease-in-out infinite; }
.anim-stars { animation: dec-stars 20s linear infinite; }
.anim-gradient { animation: dec-gradient 4s ease infinite; background-size: 200% 200%; }
.anim-waves { animation: dec-waves 4s ease-in-out infinite; }
.anim-leaves { animation: dec-leaves 8s linear infinite; }
.anim-galaxy { animation: dec-galaxy 30s linear infinite; }
.anim-snow { animation: dec-snow 5s linear infinite; }
.anim-hearts { animation: dec-hearts 4s ease-out infinite; }
.anim-gold-gradient { animation: dec-gold-gradient 3s ease infinite; background-size: 200% auto; }
.anim-rainbow-text { animation: dec-rainbow-text 3s linear infinite; background-size: 200% auto; }
.anim-fire-text { animation: dec-fire-text 1.5s ease-in-out infinite; }
.anim-neon-text { animation: dec-neon-text 2s ease-in-out infinite; }
.anim-matrix { animation: dec-matrix 10s linear infinite; }

/* Стили никнеймов */
.nick-gold {
    background: linear-gradient(90deg, #fbbf24, #f59e0b, #fbbf24, #d97706, #fbbf24);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: transparent;
}
.nick-rainbow {
    background: linear-gradient(90deg, #ef4444, #f59e0b, #eab308, #22c55e, #3b82f6, #8b5cf6, #ec4899, #ef4444);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: transparent;
}
.nick-fire {
    color: #fbbf24;
}
.nick-neon {
    color: #fff;
}

/* Аватарка с украшениями */
.avatar-with-decorations {
    position: relative;
    display: inline-block;
}
.avatar-with-decorations .avatar-img {
    position: relative;
    z-index: 2;
    border-radius: 50%;
}

/* ========================================= */
/* ОСНОВНЫЕ СТИЛИ                            */
/* ========================================= */
.header { 
    display: flex; 
    justify-content: space-between; 
    align-items: center; 
    max-width: 1400px; 
    margin: 0 auto 15px auto; 
    background: rgba(15, 23, 42, 0.7); 
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    padding: 12px 20px; 
    border-radius: 16px; 
    flex-wrap: wrap; 
    gap: 10px; 
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.1);
}
.user-profile { display: flex; align-items: center; gap: 10px; cursor: pointer; transition: all 0.2s; padding: 4px 8px; border-radius: 12px; }
.user-profile:hover { background: rgba(255,255,255,0.05); }
.user-avatar { width: 44px; height: 44px; border-radius: 50%; border: 2px solid #38bdf8; object-fit: cover; box-shadow: 0 0 15px rgba(56, 189, 248, 0.5); }
.username { font-weight: 600; font-size: 15px; display: flex; flex-direction: column; }
.main-nick-tag { font-size: 11px; color: #38bdf8; }
.admin-badge { color: #f59e0b; font-weight: bold; font-size: 13px; margin-left: 5px; text-shadow: 0 0 8px rgba(245, 158, 11, 0.5); }
.balance-display { 
    background: linear-gradient(135deg, #f59e0b, #d97706); 
    color: #000; 
    padding: 8px 14px; 
    border-radius: 20px; 
    font-weight: bold; 
    font-size: 13px; 
    display: flex; 
    align-items: center; 
    gap: 5px;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
    animation: coinGlow 2s infinite alternate;
}
@keyframes coinGlow {
    from { box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4); }
    to { box-shadow: 0 4px 20px rgba(245, 158, 11, 0.7); }
}
.btn-auth { background: linear-gradient(135deg, #38bdf8, #0284c7); color: #0f172a; padding: 10px 20px; border-radius: 10px; text-decoration: none; font-weight: bold; box-shadow: 0 4px 12px rgba(56, 189, 248, 0.4); transition: all 0.2s; }
.btn-auth:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(56, 189, 248, 0.6); }
.btn-logout { background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; padding: 8px 14px; border-radius: 8px; text-decoration: none; font-size: 13px; box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3); }
.btn-settings { background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; padding: 8px 14px; border-radius: 8px; text-decoration: none; font-size: 13px; margin-right: 6px; box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3); }
.container { 
    max-width: 1400px; 
    margin: 0 auto; 
    background: rgba(15, 23, 42, 0.6); 
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    padding: 20px; 
    border-radius: 20px; 
    box-shadow: 0 8px 40px rgba(0,0,0,0.5);
    border: 1px solid rgba(255,255,255,0.08);
}
.alert { 
    background: linear-gradient(135deg, #ef4444, #dc2626); 
    color: #fff; 
    padding: 14px 18px; 
    border-radius: 12px; 
    margin-bottom: 15px;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}
.tabs { 
    display: flex; 
    gap: 8px; 
    margin-bottom: 20px; 
    padding: 6px;
    background: rgba(0,0,0,0.3);
    border-radius: 14px;
    flex-wrap: wrap;
    border: 1px solid rgba(255,255,255,0.05);
}
.tab-btn { 
    padding: 10px 18px; 
    background: transparent; 
    color: #94a3b8;  
    border: none; 
    border-radius: 10px; 
    cursor: pointer; 
    font-weight: 600; 
    font-size: 14px; 
    text-decoration: none; 
    transition: all 0.3s;
    position: relative;
}
.tab-btn:hover { background: rgba(255,255,255,0.08); color: #f8fafc; transform: translateY(-1px); }
.tab-btn.active { 
    background: linear-gradient(135deg, #38bdf8, #0284c7); 
    color: #0f172a;
    box-shadow: 0 4px 12px rgba(56, 189, 248, 0.4);
}
.chat-layout { display: flex; gap: 15px; height: 620px; }
.sidebar { 
    width: 300px; 
    background: rgba(11, 17, 32, 0.8); 
    backdrop-filter: blur(10px);
    border-radius: 16px; 
    padding: 12px; 
    display: flex; 
    flex-direction: column; 
    gap: 8px; 
    overflow-y: auto; 
    flex-shrink: 0;
    border: 1px solid rgba(255,255,255,0.05);
}
.search-input { 
    width: 100%; 
    padding: 10px 14px; 
    border-radius: 10px; 
    border: 1px solid rgba(255,255,255,0.1); 
    background: rgba(30, 41, 59, 0.8); 
    color: #fff; 
    font-size: 13px;
    transition: all 0.2s;
}
.search-input:focus { outline: none; border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2); }
.search-results { position: absolute; top: 42px; left: 0; right: 0; background: #1e293b; border: 1px solid #334155; border-radius: 10px; z-index: 100; max-height: 240px; overflow-y: auto; display: none; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
.search-item { padding: 10px 14px; font-size: 13px; cursor: pointer; border-bottom: 1px solid #334155; transition: all 0.2s; display: flex; align-items: center; gap: 8px; }
.search-item:hover { background: #0284c7; }
.search-item .search-avatar-wrap { position: relative; width: 28px; height: 28px; flex-shrink: 0; }
.search-item .search-avatar-wrap img { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; }
.btn-create-group { 
    background: linear-gradient(135deg, #22c55e, #16a34a); 
    color: #fff; 
    border: none; 
    padding: 10px; 
    border-radius: 10px; 
    font-weight: bold; 
    cursor: pointer; 
    font-size: 13px; 
    width: 100%; 
    margin-bottom: 8px;
    box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
    transition: all 0.2s;
}
.btn-create-group:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(34, 197, 94, 0.5); }
.chat-item { 
    padding: 10px 12px; 
    background: rgba(30, 41, 59, 0.6); 
    border-radius: 10px; 
    cursor: pointer; 
    font-size: 13px; 
    font-weight: 600; 
    color: #cbd5e1; 
    display: flex; 
    align-items: center; 
    gap: 10px; 
    overflow: hidden;
    transition: all 0.2s;
    border: 1px solid transparent;
}
.chat-item:hover { background: rgba(2, 132, 199, 0.3); border-color: rgba(56, 189, 248, 0.3); transform: translateX(4px); }
.chat-item.active { 
    background: linear-gradient(135deg, rgba(2, 132, 199, 0.5), rgba(3, 105, 161, 0.5)); 
    color: #fff;
    border-color: #38bdf8;
    box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
}
.chat-item-avatar { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; flex-shrink: 0; background: #334155; }
.chat-main { flex: 1; display: flex; flex-direction: column; height: 100%; position: relative; min-width: 0; }
.chat-header-bar { 
    display: flex; 
    justify-content: space-between; 
    align-items: center; 
    background: rgba(11, 17, 32, 0.8); 
    backdrop-filter: blur(10px);
    padding: 12px 18px; 
    border-radius: 14px; 
    margin-bottom: 10px; 
    flex-wrap: wrap; 
    gap: 10px;
    border: 1px solid rgba(255,255,255,0.05);
}
.btn-call, .btn-group-settings { 
    background: linear-gradient(135deg, #22c55e, #16a34a); 
    color: #fff; 
    border: none; 
    padding: 8px 16px; 
    border-radius: 10px; 
    font-weight: bold; 
    cursor: pointer; 
    font-size: 13px;
    box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3);
    transition: all 0.2s;
}
.btn-call:hover, .btn-group-settings:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(34, 197, 94, 0.5); }
.btn-mute { background: #475569; color: #fff; border: none; padding: 8px 14px; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 12px; transition: all 0.2s; }
.btn-mute.muted { background: linear-gradient(135deg, #ef4444, #dc2626); }
.pinned-bar { display: none; background: rgba(56, 189, 248, 0.1); padding: 8px 14px; border-radius: 10px; margin-bottom: 8px; font-size: 12px; justify-content: space-between; align-items: center; border-left: 3px solid #38bdf8; backdrop-filter: blur(10px); }
.chat-box { 
    flex: 1; 
    overflow-y: auto; 
    background: 
        linear-gradient(180deg, rgba(30, 58, 138, 0.4) 0%, rgba(59, 130, 246, 0.2) 50%, rgba(30, 64, 175, 0.4) 100%),
        radial-gradient(circle at 10% 20%, rgba(147, 51, 234, 0.15) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(236, 72, 153, 0.15) 0%, transparent 40%);
    border-radius: 16px; 
    padding: 20px; 
    display: flex; 
    flex-direction: column !important; 
    gap: 12px; 
    margin-bottom: 10px;
    border: 1px solid rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
}
.chat-box::-webkit-scrollbar { width: 8px; }
.chat-box::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); border-radius: 4px; }
.chat-box::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #38bdf8, #0284c7); border-radius: 4px; }
.msg-wrapper { display: flex; width: 100%; gap: 10px; align-items: flex-end; flex-shrink: 0; animation: msgAppear 0.3s ease-out; }
@keyframes msgAppear {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.msg-wrapper.own { justify-content: flex-end; }
.msg-wrapper.other { justify-content: flex-start; }
.msg-avatar-wrap { position: relative; width: 40px; height: 40px; flex-shrink: 0; margin-bottom: 2px; }
.msg-avatar { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; cursor: pointer; transition: all 0.2s; border: 2px solid transparent; position: relative; z-index: 2; }
.msg-avatar:hover { transform: scale(1.1); }
.msg { 
    padding: 10px 16px; 
    border-radius: 20px; 
    max-width: 75%; 
    position: relative; 
    user-select: none; 
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    transition: all 0.2s;
    word-wrap: break-word;
}
.msg:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
.msg-wrapper.own .msg { 
    background: linear-gradient(135deg, #10b981, #059669); 
    color: #fff; 
    border-bottom-right-radius: 4px;
    box-shadow: 0 2px 12px rgba(16, 185, 129, 0.3);
}
.msg-wrapper.other .msg { 
    background: rgba(255, 255, 255, 0.95); 
    color: #1e293b; 
    border-bottom-left-radius: 4px;
    backdrop-filter: blur(10px);
}
.msg-wrapper.other .msg .msg-header b { color: #0284c7; }
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
.status-dot.online { background-color: #22c55e; box-shadow: 0 0 8px #22c55e; animation: pulse 2s infinite; }
.status-dot.offline { background-color: #ef4444; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.msg-header { font-size: 11px; margin-bottom: 4px; display: flex; justify-content: space-between; gap: 12px; align-items: center; opacity: 0.85; }
.msg-header .nick-wrap { display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.msg-text { font-size: 14px; word-break: break-word; line-height: 1.5; }
.msg-text a { color: #38bdf8; text-decoration: underline; font-weight: 500; }
.msg-text a:hover { color: #0ea5e9; }
.msg-reactions { display: flex; gap: 4px; margin-top: 6px; flex-wrap: wrap; }
.reaction-chip { background: rgba(0,0,0,0.2); padding: 2px 8px; border-radius: 12px; font-size: 11px; cursor: pointer; transition: all 0.2s; border: 1px solid transparent; }
.reaction-chip:hover { background: rgba(56, 189, 248, 0.3); border-color: #38bdf8; }
.reaction-chip.mine { background: rgba(56, 189, 248, 0.4); border-color: #38bdf8; }
.sticker-img { width: 140px; height: 140px; object-fit: contain; display: block; margin-top: 5px; }
.file-card { background: rgba(0,0,0,0.25); border-radius: 10px; padding: 10px 14px; margin-top: 6px; display: flex; align-items: center; justify-content: space-between; gap: 12px; border: 1px solid rgba(255,255,255,0.1); }
.btn-file-dl { background: linear-gradient(135deg, #38bdf8, #0284c7); color: #fff !important; padding: 6px 12px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 11px; }
audio { max-width: 240px; height: 38px; margin-top: 6px; }
.call-card { background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; border-radius: 12px; padding: 12px; margin-top: 6px; text-align: center; }
.btn-join-call { background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff !important; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 12px; display: inline-block; margin-top: 6px; }
.reply-quote { background: rgba(0,0,0,0.25); border-left: 3px solid #f59e0b; padding: 6px 10px; border-radius: 6px; font-size: 12px; margin-bottom: 6px; }
.forwarded-tag { font-size: 11px; font-style: italic; color: #cbd5e1; margin-bottom: 4px; }
.reply-preview-bar { display: none; background: rgba(51, 65, 85, 0.9); padding: 8px 14px; border-radius: 10px; margin-bottom: 8px; font-size: 12px; justify-content: space-between; align-items: center; backdrop-filter: blur(10px); }
.chat-form { display: flex; gap: 8px; flex-wrap: wrap; }
.chat-form input[type="text"] { 
    flex: 1; 
    padding: 12px 16px; 
    border-radius: 12px; 
    border: 1px solid rgba(255,255,255,0.1); 
    background: rgba(15, 23, 42, 0.8); 
    color: #fff; 
    min-width: 120px;
    backdrop-filter: blur(10px);
    transition: all 0.2s;
}
.chat-form input[type="text"]:focus { outline: none; border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2); }
.btn-action { 
    background: rgba(51, 65, 85, 0.8); 
    color: #fff; 
    border: 1px solid rgba(255,255,255,0.1); 
    padding: 12px 14px; 
    border-radius: 12px; 
    cursor: pointer; 
    font-size: 16px;
    transition: all 0.2s;
}
.btn-action:hover { background: rgba(56, 189, 248, 0.3); border-color: #38bdf8; transform: translateY(-2px); }
.btn-action.recording { background: linear-gradient(135deg, #ef4444, #dc2626); animation: pulse 1s infinite; }
.btn-send {  
    background: linear-gradient(135deg, #38bdf8, #0284c7); 
    color: #0f172a; 
    border: none; 
    padding: 12px 20px; 
    border-radius: 12px; 
    font-weight: bold; 
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(56, 189, 248, 0.4);
    transition: all 0.2s;
}
.btn-send:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(56, 189, 248, 0.6); }
.context-menu { display: none; position: fixed; background: rgba(30, 41, 59, 0.95); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; box-shadow: 0 10px 40px rgba(0,0,0,0.8); z-index: 1000; width: 180px; overflow: hidden; }
.context-menu-item { padding: 12px 16px; font-size: 13px; color: #fff; cursor: pointer; transition: all 0.2s; }
.context-menu-item:hover { background: linear-gradient(135deg, #38bdf8, #0284c7); color: #0f172a; }
.modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); z-index: 2000; align-items: center; justify-content: center; padding: 15px; }
.modal { 
    background: rgba(30, 41, 59, 0.95); 
    backdrop-filter: blur(20px);
    width: 100%; 
    max-width: 500px; 
    padding: 24px; 
    border-radius: 20px; 
    text-align: center; 
    max-height: 90vh; 
    overflow-y: auto;
    border: 1px solid rgba(255,255,255,0.1);
    box-shadow: 0 20px 60px rgba(0,0,0,0.8);
    position: relative;
}
.modal-chat-list { display: flex; flex-direction: column; gap: 8px; margin: 15px 0; max-height: 240px; overflow-y: auto; }
.profile-avatar-large-wrap { 
    position: relative; 
    display: inline-block; 
    width: 120px; 
    height: 120px; 
    margin-bottom: 12px; 
}
.profile-avatar-large { 
    width: 120px; 
    height: 120px; 
    border-radius: 50%; 
    border: 3px solid #38bdf8; 
    object-fit: cover; 
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.5);
    position: relative;
    z-index: 2;
}
.profile-field { text-align: left; margin-bottom: 12px; }
.profile-field label { display: block; font-size: 12px; color: #94a3b8; margin-bottom: 4px; font-weight: 600; }
.profile-field input, .profile-field textarea, .profile-field select { 
    width: 100%; 
    padding: 10px 12px; 
    border-radius: 10px; 
    border: 1px solid rgba(255,255,255,0.1); 
    background: rgba(15, 23, 42, 0.8); 
    color: #fff; 
    font-size: 13px;
    transition: all 0.2s;
}
.profile-field input:focus, .profile-field textarea:focus, .profile-field select:focus { outline: none; border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2); }
.date-picker-row { display: flex; gap: 6px; }
.date-picker-row select { flex: 1; padding: 8px 4px; font-size: 12px; }
.stickers-picker { display: none; position: absolute; bottom: 60px; right: 0; width: 340px; background: rgba(30, 41, 59, 0.95); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.6); z-index: 50; }
.sticker-tabs { display: flex; gap: 5px; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px; overflow-x: auto; }
.sticker-tab-btn { background: rgba(15, 23, 42, 0.8); color: #94a3b8; border: none; padding: 6px 12px; border-radius: 8px; cursor: pointer; font-size: 12px; white-space: nowrap; transition: all 0.2s; }
.sticker-tab-btn.active { background: linear-gradient(135deg, #38bdf8, #0284c7); color: #0f172a; font-weight: bold; }
.sticker-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; max-height: 220px; overflow-y: auto; }
.sticker-item { width: 100%; height: 70px; object-fit: contain; cursor: pointer; border-radius: 8px; padding: 4px; transition: all 0.2s; }
.sticker-item:hover { background: rgba(56, 189, 248, 0.2); transform: scale(1.05); }
.btn-upload-sticker { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; border: none; padding: 8px 14px; border-radius: 8px; font-size: 12px; font-weight: bold; cursor: pointer; }
.file-item { background: rgba(51, 65, 85, 0.6); padding: 14px 18px; border-radius: 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(255,255,255,0.05); }
.btn-download { background: linear-gradient(135deg, #818cf8, #6366f1); color: #fff; padding: 8px 14px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: bold; }
.admin-section { background: rgba(11, 17, 32, 0.8); padding: 18px; border-radius: 14px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.05); }
.admin-section h4 { margin-top: 0; color: #38bdf8; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }
.bot-card { background: rgba(30, 41, 59, 0.8); padding: 14px; border-radius: 12px; margin-bottom: 12px; border: 1px solid rgba(255,255,255,0.05); }
.code-editor { width: 100%; height: 120px; background: #0f172a; color: #38bdf8; font-family: monospace; padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); margin-top: 6px; }
.profile-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 12px; }
.btn-block { background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; border: none; padding: 10px 16px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 12px; }
.btn-block.unblock { background: linear-gradient(135deg, #22c55e, #16a34a); }
.btn-msg { background: linear-gradient(135deg, #38bdf8, #0284c7); color: #0f172a; border: none; padding: 10px 16px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 12px; text-decoration: none; }
.toast { 
    position: fixed; 
    top: 20px; 
    right: 20px; 
    background: linear-gradient(135deg, #0284c7, #0369a1); 
    color: #fff; 
    padding: 14px 20px; 
    border-radius: 12px; 
    z-index: 5000; 
    box-shadow: 0 8px 24px rgba(0,0,0,0.5); 
    font-size: 13px; 
    display: none; 
    animation: slideIn 0.3s;
    border: 1px solid rgba(255,255,255,0.1);
}
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.members-panel { width: 240px; background: rgba(11, 17, 32, 0.8); backdrop-filter: blur(10px); border-radius: 16px; padding: 12px; overflow-y: auto; flex-shrink: 0; border: 1px solid rgba(255,255,255,0.05); }
.members-panel h5 { color: #38bdf8; margin: 0 0 10px 0; font-size: 13px; }
.member-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 8px; cursor: pointer; font-size: 12px; transition: all 0.2s; }
.member-item:hover { background: rgba(30, 41, 59, 0.8); }
.member-item .member-nick { display: inline-flex; align-items: center; gap: 3px; flex-wrap: wrap; }
.member-avatar-wrap { position: relative; width: 34px; height: 34px; flex-shrink: 0; }
.member-avatar { width: 30px; height: 30px; border-radius: 50%; object-fit: cover; background: #334155; position: relative; z-index: 2; }
.burmalda-container, .shop-container, .posts-container, .tasks-container { max-width: 900px; margin: 0 auto; }
.burmalda-player { background: rgba(11, 17, 32, 0.8); padding: 24px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); }
.burmalda-iframe-wrapper { position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 16px; background: #000; box-shadow: 0 8px 32px rgba(0,0,0,0.5); }
.burmalda-iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; border-radius: 16px; }
.shop-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.shop-card { 
    background: rgba(11, 17, 32, 0.8); 
    padding: 18px; 
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.05);
    transition: all 0.3s;
}
.shop-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); border-color: rgba(56, 189, 248, 0.3); }
.shop-card-title { font-weight: bold; font-size: 15px; color: #38bdf8; }
.shop-card-price { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; padding: 5px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; }
.shop-card-price.free { background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; }
.shop-card-stickers { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 12px 0; }
.shop-card-sticker { width: 100%; height: 55px; object-fit: contain; border-radius: 6px; }
.btn-buy { background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; border: none; padding: 10px 18px; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 13px; width: 100%; transition: all 0.2s; }
.btn-buy:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(34, 197, 94, 0.4); }
.btn-buy.owned { background: #475569; cursor: not-allowed; }
.post-card { background: rgba(11, 17, 32, 0.8); padding: 18px; border-radius: 16px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.05); transition: all 0.2s; }
.post-card:hover { border-color: rgba(56, 189, 248, 0.2); }
.post-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.post-avatar-wrap { position: relative; width: 48px; height: 48px; flex-shrink: 0; }
.post-avatar { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; position: relative; z-index: 2; }
.post-author-nick { display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.post-content { font-size: 14px; line-height: 1.6; margin-bottom: 12px; }
.post-actions { display: flex; gap: 16px; font-size: 13px; color: #94a3b8; }
.post-actions button { background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 13px; transition: all 0.2s; padding: 4px 8px; border-radius: 6px; }
.post-actions button:hover { color: #38bdf8; background: rgba(56, 189, 248, 0.1); }
.comments-section { margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1); }
.comment { background: rgba(30, 41, 59, 0.8); padding: 10px; border-radius: 8px; margin-bottom: 8px; font-size: 13px; }
.comment .comment-nick { display: inline-flex; align-items: center; gap: 3px; }
.group-member-row { display: flex; justify-content: space-between; align-items: center; background: rgba(30, 41, 59, 0.8); padding: 10px; border-radius: 8px; margin-bottom: 8px; font-size: 12px; }
.btn-sm { padding: 5px 10px; font-size: 11px; border-radius: 6px; border: none; cursor: pointer; margin-left: 4px; transition: all 0.2s; }
.btn-sm:hover { transform: translateY(-1px); }
.btn-sm-danger { background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; }
.btn-sm-warn { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; }
.fm-viewers { background: rgba(0,0,0,0.3); padding: 14px; border-radius: 12px; margin-top: 18px; border: 1px solid rgba(255,255,255,0.05); }
.fm-viewers h5 { margin: 0 0 12px 0; color: #38bdf8; font-size: 13px; }
.fm-viewer-item { display: flex; align-items: center; gap: 10px; padding: 6px; font-size: 13px; border-radius: 8px; transition: all 0.2s; }
.fm-viewer-item:hover { background: rgba(56, 189, 248, 0.1); }
.fm-viewer-item .fm-nick { display: inline-flex; align-items: center; gap: 3px; }
.fm-viewer-avatar-wrap { position: relative; width: 32px; height: 32px; flex-shrink: 0; }
.fm-viewer-avatar { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; position: relative; z-index: 2; }

/* Мастерская */
.workshop-container { max-width: 1000px; margin: 0 auto; }
.workshop-type-selector { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 30px 0; }
.workshop-type-card { background: rgba(11, 17, 32, 0.8); padding: 30px; border-radius: 20px; text-align: center; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; position: relative; overflow: hidden; }
.workshop-type-card:hover { transform: translateY(-6px); box-shadow: 0 12px 32px rgba(0,0,0,0.5); }
.workshop-type-card.sticker-card { border-color: #38bdf8; }
.workshop-type-card.sticker-card:hover { box-shadow: 0 12px 32px rgba(56, 189, 248, 0.4); }
.workshop-type-card.decoration-card { border-color: #a855f7; }
.workshop-type-card.decoration-card:hover { box-shadow: 0 12px 32px rgba(168, 85, 247, 0.4); }
.workshop-type-icon { font-size: 72px; margin-bottom: 16px; filter: drop-shadow(0 0 10px currentColor); }
.workshop-type-title { font-size: 22px; font-weight: bold; color: #f8fafc; margin-bottom: 10px; }
.workshop-type-desc { font-size: 14px; color: #94a3b8; line-height: 1.6; margin-bottom: 16px; }
.workshop-type-features { text-align: left; font-size: 12px; color: #cbd5e1; line-height: 1.8; }
.workshop-type-features li { margin-bottom: 4px; }
.workshop-steps { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.workshop-step { flex: 1; min-width: 120px; padding: 12px; background: rgba(30, 41, 59, 0.6); border-radius: 10px; text-align: center; font-size: 13px; color: #94a3b8; border: 2px solid transparent; transition: all 0.2s; }
.workshop-step.active { background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(2, 132, 199, 0.1)); border-color: #38bdf8; color: #38bdf8; font-weight: bold; }
.workshop-step.done { background: rgba(34, 197, 94, 0.15); border-color: #22c55e; color: #22c55e; }
.workshop-panel { background: rgba(11, 17, 32, 0.8); padding: 24px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); min-height: 300px; }
.workshop-upload-zone { border: 2px dashed #475569; border-radius: 12px; padding: 40px 20px; text-align: center; cursor: pointer; transition: all 0.2s; margin-bottom: 16px; }
.workshop-upload-zone:hover { border-color: #38bdf8; background: rgba(56, 189, 248, 0.05); }
.workshop-upload-zone.dragover { border-color: #38bdf8; background: rgba(56, 189, 248, 0.1); }
.workshop-preview-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; margin-top: 16px; }
.workshop-preview-item { position: relative; background: rgba(30, 41, 59, 0.8); border-radius: 10px; padding: 8px; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; }
.workshop-preview-item img { max-width: 100%; max-height: 100%; object-fit: contain; }
.workshop-preview-item .remove-btn { position: absolute; top: 4px; right: 4px; background: #ef4444; color: #fff; border: none; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; font-size: 12px; }

/* Украшения */
.decorations-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.decoration-card { background: rgba(11, 17, 32, 0.8); padding: 16px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.05); transition: all 0.3s; position: relative; overflow: hidden; }
.decoration-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
.decoration-card.rarity-common { border-color: #64748b; }
.decoration-card.rarity-rare { border-color: #38bdf8; box-shadow: 0 0 12px rgba(56, 189, 248, 0.2); }
.decoration-card.rarity-epic { border-color: #a855f7; box-shadow: 0 0 12px rgba(168, 85, 247, 0.3); }
.decoration-card.rarity-legendary { border-color: #f59e0b; box-shadow: 0 0 16px rgba(245, 158, 11, 0.4); animation: legendaryGlow 3s infinite alternate; }
@keyframes legendaryGlow {
    from { box-shadow: 0 0 16px rgba(245, 158, 11, 0.4); }
    to { box-shadow: 0 0 24px rgba(245, 158, 11, 0.7); }
}
.decoration-preview-wrap {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 80px;
    margin: 12px 0;
    background: rgba(0,0,0,0.2);
    border-radius: 10px;
    position: relative;
    overflow: hidden;
}
.decoration-preview-emoji {
    font-size: 48px;
    filter: drop-shadow(0 0 8px currentColor);
}
.decoration-preview-image {
    max-width: 80%;
    max-height: 80%;
    object-fit: contain;
    filter: drop-shadow(0 0 8px currentColor);
}
.decoration-name { font-weight: bold; font-size: 14px; color: #f8fafc; margin-bottom: 6px; }
.decoration-desc { font-size: 12px; color: #94a3b8; margin-bottom: 10px; min-height: 32px; }
.decoration-rarity { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: bold; margin-bottom: 8px; }
.rarity-common .decoration-rarity { background: #475569; color: #fff; }
.rarity-rare .decoration-rarity { background: #0284c7; color: #fff; }
.rarity-epic .decoration-rarity { background: #9333ea; color: #fff; }
.rarity-legendary .decoration-rarity { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; }
.decoration-type { font-size: 11px; color: #64748b; margin-bottom: 8px; }
.decoration-status { position: absolute; top: 10px; right: 10px; background: rgba(34, 197, 94, 0.2); color: #22c55e; padding: 3px 8px; border-radius: 8px; font-size: 11px; font-weight: bold; }
.btn-equip { background: linear-gradient(135deg, #38bdf8, #0284c7); color: #0f172a; border: none; padding: 8px 14px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 12px; width: 100%; transition: all 0.2s; }
.btn-equip:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(56, 189, 248, 0.4); }
.btn-equip.equipped { background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; }
.btn-unequip { background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; border: none; padding: 8px 14px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 12px; width: 100%; transition: all 0.2s; }

/* Превью украшения в редакторе */
.decoration-editor-preview {
    background: rgba(0,0,0,0.3);
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 150px;
    position: relative;
    overflow: hidden;
}
.decoration-editor-preview .preview-avatar {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: linear-gradient(135deg, #38bdf8, #0284c7);
    position: relative;
    z-index: 2;
}
.decoration-editor-preview .preview-nick {
    font-size: 22px;
    font-weight: bold;
    margin-left: 12px;
    color: #f8fafc;
    position: relative;
    z-index: 2;
}

/* Загрузка изображения */
.image-upload-area {
    border: 2px dashed #475569;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: 12px;
}
.image-upload-area:hover { border-color: #a855f7; background: rgba(168, 85, 247, 0.05); }
.image-upload-area.has-image { border-color: #22c55e; background: rgba(34, 197, 94, 0.05); }
.image-upload-area img { max-width: 100%; max-height: 200px; object-fit: contain; margin-top: 10px; border-radius: 8px; }

@media (max-width: 900px) { .members-panel { display: none; } }
@media (max-width: 700px) {
    body { padding: 8px; }
    .header { padding: 10px; }
    .container { padding: 12px; }
    .chat-layout { flex-direction: column; height: auto; }
    .sidebar { width: 100%; max-height: 180px; }
    .chat-box { height: 420px; }
    .stickers-picker { width: calc(100vw - 40px); right: 10px; }
    .msg { max-width: 85%; }
    .date-picker-row { flex-direction: column; }
    .shop-grid { grid-template-columns: 1fr; }
    .decorations-grid { grid-template-columns: repeat(2, 1fr); }
    .workshop-type-selector { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<div class="header">
{% if user %}
    <div class="user-profile" onclick="window.location.href='/settings'">
        {% if user.picture %}<img src="{{ user.picture }}" class="user-avatar">{% endif %}
        <span class="username">
            <span>{{ user_profile.custom_nick or user.nickname }} {% if is_admin %}<span class="admin-badge">[ADMIN]</span>{% endif %} {% if user_subscription_active %}<span style="color:#f59e0b;">⭐</span>{% endif %}</span>
            <span class="main-nick-tag">@{{ user.email.split('@')[0] if user.email else user.nickname }}</span>
        </span>
    </div>
    <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
        <div class="balance-display">💰 {{ user_burmalnets_display }}</div>
        <a href="/settings" class="btn-settings">⚙️ Настройки</a>
        <a href="/logout" class="btn-logout">Выйти</a>
    </div>
{% else %}
    <span style="color: #94a3b8; font-size: 14px;">Войдите через Google для доступа</span>
    <a href="/login" class="btn-auth">Войти</a>
{% endif %}
</div>
<div class="container">
{% if is_maintenance and not is_admin %}
    <div style="text-align: center; padding: 50px 20px;">
        <h2 style="color: #ef4444;">⛔ Сервер временно отключен</h2>
        <p style="color: #94a3b8;">Администратор Бурмалдод временно приостановил работу.</p>
    </div>
{% else %}
{% if action_error %}<div class="alert">⚠️ {{ action_error }}</div>{% endif %}
<div class="tabs">
    <a href="/?tab=chat" class="tab-btn {% if active_tab == 'chat' %}active{% endif %}">💬 Чаты</a>
    <a href="/?tab=posts" class="tab-btn {% if active_tab == 'posts' %}active{% endif %}">📝 Посты</a>
    <a href="/?tab=shop" class="tab-btn {% if active_tab == 'shop' %}active{% endif %}">🛒 Магазин</a>
    <a href="/?tab=decorations" class="tab-btn {% if active_tab == 'decorations' %}active{% endif %}">✨ Украшения</a>
    <a href="/?tab=workshop" class="tab-btn {% if active_tab == 'workshop' %}active{% endif %}">🎨 Мастерская</a>
    <a href="/?tab=tasks" class="tab-btn {% if active_tab == 'tasks' %}active{% endif %}">🎯 Задания</a>
    <a href="/?tab=files" class="tab-btn {% if active_tab == 'files' %}active{% endif %}">📁 Файлы</a>
    <a href="/?tab=burmalda_fm" class="tab-btn {% if active_tab == 'burmalda_fm' %}active{% endif %}">🎵 FM</a>
{% if is_admin %}
    <a href="/?tab=admin_panel" class="tab-btn {% if active_tab == 'admin_panel' %}active{% endif %}">⚙️ Управление</a>
    <a href="/?tab=pending" class="tab-btn {% if active_tab == 'pending' %}active{% endif %}">🔍 Стикеры ({{ pending_count }})</a>
{% endif %}
</div>

{% if active_tab == 'chat' %}
<div class="chat-layout">
    <div class="sidebar">
{% if user %}
        <button class="btn-create-group" onclick="document.getElementById('createGroupModal').style.display='flex'">➕ Создать группу</button>
        <div style="position:relative;">
            <input type="text" class="search-input" id="searchInput" placeholder="🔍 Поиск по @нику..." oninput="searchUsers(this.value)">
            <div class="search-results" id="searchResults"></div>
        </div>
{% endif %}
        <div style="margin-top: 5px;">
{% for c in user_chats %}
            <div class="chat-item {% if c.id == current_chat_id %}active{% endif %}" onclick="switchChat('{{ c.id }}')">
                {% if c.avatar %}<img src="{{ c.avatar }}" class="chat-item-avatar">
                {% else %}<div class="chat-item-avatar" style="display:flex; align-items:center; justify-content:center; font-size:12px;">💬</div>{% endif %}
                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ c.name }}</span>
            </div>
{% endfor %}
        </div>
    </div>
    <div class="chat-main">
        <div class="chat-header-bar">
            <span style="font-size: 15px; font-weight: bold;">💬 {{ current_chat_name }}</span>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
{% if user and current_chat_partner %}
                <button class="btn-mute {% if current_chat_muted %}muted{% endif %}" id="muteBtn" onclick="toggleMute()">
                    {% if current_chat_muted %}🔇{% else %}🔔{% endif %}
                </button>
{% endif %}
{% if user and current_chat_is_group and can_manage_curr_group %}
                <button class="btn-group-settings" onclick="openGroupSettings()">⚙️</button>
{% endif %}
{% if user %}<button class="btn-call" onclick="startCall()">📞</button>{% endif %}
            </div>
        </div>
        <div id="pinnedBar" class="pinned-bar">
            <span>📌 <b id="pinnedUser"></b>: <span id="pinnedText"></span></span>
            <button onclick="unpinMessage()" style="background:none; border:none; color:#ef4444; cursor:pointer; font-weight:bold;">✖</button>
        </div>
        <div class="chat-box" id="chatBox"></div>
{% if user %}
        <div id="replyBar" class="reply-preview-bar">
            <span id="replyTextSnippet"></span>
            <button onclick="cancelReply()" style="background:none; border:none; color:#ef4444; cursor:pointer; font-weight:bold;">✖</button>
        </div>
        <div style="position:relative;">
            <div class="stickers-picker" id="stickersPicker">
                <div class="sticker-tabs">
{% for pack_id, pack_info in sticker_packs.items() %}
{% if pack_id in user_owned_packs or pack_info.owner_key is none or pack_info.owner_key == user_key or is_admin %}
                    <button class="sticker-tab-btn {% if pack_id == 'pack1' %}active{% endif %}" onclick="switchStickerPack('{{ pack_id }}', this)">{{ pack_info.name }}</button>
{% endif %}
{% endfor %}
                </div>
{% for pack_id, pack_info in sticker_packs.items() %}
{% if pack_id in user_owned_packs or pack_info.owner_key is none or pack_info.owner_key == user_key or is_admin %}
                <div id="{{ pack_id }}" class="sticker-grid" style="display: {% if pack_id == 'pack1' %}grid{% else %}none{% endif %};">
{% for sticker in pack_info.stickers %}
                    <img src="{{ sticker }}" class="sticker-item" onclick="sendSticker('{{ sticker }}')">
{% else %}
                    <span style="color: #64748b; font-size: 12px; grid-column: span 4; text-align: center; padding: 10px;">Пусто</span>
{% endfor %}
                </div>
{% endif %}
{% endfor %}
                <div style="margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px; text-align: center;">
                    <button type="button" class="btn-upload-sticker" onclick="window.location.href='/?tab=workshop'">🎨 В мастерскую</button>
                </div>
            </div>
            <form onsubmit="sendMessage(event)" class="chat-form" id="chatForm">
                <input type="text" id="msgInput" placeholder="Написать сообщение..." autocomplete="off">
                <button type="button" class="btn-action" onclick="document.getElementById('localFileInput').click()">📎</button>
                <input type="file" id="localFileInput" style="display:none;" onchange="uploadLocalFile(this)">
                <button type="button" class="btn-action" onclick="toggleStickers()">😀</button>
                <button type="button" class="btn-action" id="recordVoiceBtn" onclick="toggleVoiceRecord()">🎤</button>
                <button type="submit" class="btn-send">Отправить</button>
            </form>
        </div>
{% else %}
        <p style="color: #f59e0b; text-align: center;">Войдите через Google, чтобы писать.</p>
{% endif %}
    </div>
{% if current_chat_is_group and group_members %}
    <div class="members-panel">
        <h5>👥 Участники ({{ group_members|length }})</h5>
{% for m in group_members %}
        <div class="member-item" onclick="showUserProfile('{{ m.key }}')">
            <div class="member-avatar-wrap">
                {% if m.avatar %}<img src="{{ m.avatar }}" class="member-avatar">
                {% else %}<div class="member-avatar" style="display:flex;align-items:center;justify-content:center;font-size:11px;">👤</div>{% endif %}
                {% if m.decorations and m.decorations.frame %}
                    {% if m.decorations.frame.has_custom_image and m.decorations.frame.image_url %}
                        <img src="{{ m.decorations.frame.image_url }}" class="decoration-frame anim-{{ m.decorations.frame.animation }}">
                    {% else %}
                        <div class="decoration-frame anim-{{ m.decorations.frame.animation }}" style="border: {{ m.decorations.frame.border_width or 3 }}px solid {{ m.decorations.frame.color }}; box-shadow: 0 0 10px {{ m.decorations.frame.color }};"></div>
                    {% endif %}
                {% endif %}
                {% if m.decorations and m.decorations.effect %}
                    {% if m.decorations.effect.has_custom_image and m.decorations.effect.image_url %}
                        <img src="{{ m.decorations.effect.image_url }}" class="decoration-effect anim-{{ m.decorations.effect.animation }}" style="color: {{ m.decorations.effect.color }};">
                    {% else %}
                        <div class="decoration-effect anim-{{ m.decorations.effect.animation }}" style="background: radial-gradient(circle, {{ m.decorations.effect.color }}40, transparent); color: {{ m.decorations.effect.color }};"></div>
                    {% endif %}
                {% endif %}
            </div>
            <span class="member-nick" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                {% if m.decorations and m.decorations.badge and m.decorations.badge.position == 'before' %}
                    {% if m.decorations.badge.has_custom_image and m.decorations.badge.image_url %}
                        <span class="decoration-badge anim-{{ m.decorations.badge.animation }} position-before size-{{ m.decorations.badge.size }}" style="color: {{ m.decorations.badge.color }};"><img src="{{ m.decorations.badge.image_url }}"></span>
                    {% else %}
                        <span class="decoration-badge anim-{{ m.decorations.badge.animation }} position-before size-{{ m.decorations.badge.size }}" style="color: {{ m.decorations.badge.color }};">{{ m.decorations.badge.emoji }}</span>
                    {% endif %}
                {% endif %}
                {{ m.name }}{% if m.is_owner %} 👑{% endif %}
                {% if m.decorations and m.decorations.badge and (not m.decorations.badge.position or m.decorations.badge.position == 'after_nick') %}
                    {% if m.decorations.badge.has_custom_image and m.decorations.badge.image_url %}
                        <span class="decoration-badge anim-{{ m.decorations.badge.animation }} size-{{ m.decorations.badge.size }}" style="color: {{ m.decorations.badge.color }};"><img src="{{ m.decorations.badge.image_url }}"></span>
                    {% else %}
                        <span class="decoration-badge anim-{{ m.decorations.badge.animation }} size-{{ m.decorations.badge.size }}" style="color: {{ m.decorations.badge.color }};">{{ m.decorations.badge.emoji }}</span>
                    {% endif %}
                {% endif %}
            </span>
        </div>
{% endfor %}
    </div>
{% endif %}
</div>

{% elif active_tab == 'posts' %}
<div class="posts-container">
    <h3 style="color: #38bdf8; margin-bottom: 20px;">📝 Лента постов</h3>
{% if user %}
    <div style="background: rgba(11, 17, 32, 0.8); padding: 18px; border-radius: 16px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.05);">
        <textarea id="newPostContent" placeholder="Что у вас нового? (макс. 1000 символов)" maxlength="1000" rows="3" style="width: 100%; padding: 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); background: rgba(30, 41, 59, 0.8); color: #fff; font-size: 14px; resize: vertical;"></textarea>
        <button onclick="createPost()" style="background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; border: none; padding: 10px 20px; border-radius: 10px; font-weight: bold; cursor: pointer; margin-top: 12px; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);">Опубликовать</button>
        <small style="color: #94a3b8; display: block; margin-top: 8px;">⏱️ Защита от спама: 30 сек между постами</small>
    </div>
{% endif %}
{% for post in posts %}
    <div class="post-card" id="post_{{ post.id }}">
        <div class="post-header">
            <div class="post-avatar-wrap">
                {% if post.author_avatar %}<img src="{{ post.author_avatar }}" class="post-avatar">
                {% else %}<div class="post-avatar" style="background:#334155; display:flex;align-items:center;justify-content:center;">👤</div>{% endif %}
                {% if post.author_decorations and post.author_decorations.frame %}
                    {% if post.author_decorations.frame.has_custom_image and post.author_decorations.frame.image_url %}
                        <img src="{{ post.author_decorations.frame.image_url }}" class="decoration-frame anim-{{ post.author_decorations.frame.animation }}">
                    {% else %}
                        <div class="decoration-frame anim-{{ post.author_decorations.frame.animation }}" style="border: {{ post.author_decorations.frame.border_width or 3 }}px solid {{ post.author_decorations.frame.color }}; box-shadow: 0 0 10px {{ post.author_decorations.frame.color }};"></div>
                    {% endif %}
                {% endif %}
                {% if post.author_decorations and post.author_decorations.effect %}
                    {% if post.author_decorations.effect.has_custom_image and post.author_decorations.effect.image_url %}
                        <img src="{{ post.author_decorations.effect.image_url }}" class="decoration-effect anim-{{ post.author_decorations.effect.animation }}" style="color: {{ post.author_decorations.effect.color }};">
                    {% else %}
                        <div class="decoration-effect anim-{{ post.author_decorations.effect.animation }}" style="background: radial-gradient(circle, {{ post.author_decorations.effect.color }}40, transparent); color: {{ post.author_decorations.effect.color }};"></div>
                    {% endif %}
                {% endif %}
            </div>
            <div>
                <div class="post-author-nick">
                    {% if post.author_decorations and post.author_decorations.badge and post.author_decorations.badge.position == 'before' %}
                        {% if post.author_decorations.badge.has_custom_image and post.author_decorations.badge.image_url %}
                            <span class="decoration-badge anim-{{ post.author_decorations.badge.animation }} position-before size-{{ post.author_decorations.badge.size }}" style="color: {{ post.author_decorations.badge.color }};"><img src="{{ post.author_decorations.badge.image_url }}"></span>
                        {% else %}
                            <span class="decoration-badge anim-{{ post.author_decorations.badge.animation }} position-before size-{{ post.author_decorations.badge.size }}" style="color: {{ post.author_decorations.badge.color }};">{{ post.author_decorations.badge.emoji }}</span>
                        {% endif %}
                    {% endif %}
                    <b style="color: #38bdf8;">{{ post.author_name }}</b>
                    {% if post.author_decorations and post.author_decorations.badge and (not post.author_decorations.badge.position or post.author_decorations.badge.position == 'after_nick') %}
                        {% if post.author_decorations.badge.has_custom_image and post.author_decorations.badge.image_url %}
                            <span class="decoration-badge anim-{{ post.author_decorations.badge.animation }} size-{{ post.author_decorations.badge.size }}" style="color: {{ post.author_decorations.badge.color }};"><img src="{{ post.author_decorations.badge.image_url }}"></span>
                        {% else %}
                            <span class="decoration-badge anim-{{ post.author_decorations.badge.animation }} size-{{ post.author_decorations.badge.size }}" style="color: {{ post.author_decorations.badge.color }};">{{ post.author_decorations.badge.emoji }}</span>
                        {% endif %}
                    {% endif %}
                </div>
                <div style="font-size: 11px; color: #64748b;">{{ post.timestamp[:16].replace('T', ' ') }}</div>
            </div>
        </div>
        <div class="post-content">{{ post.content }}</div>
        <div class="post-actions">
            <button onclick="likePost('{{ post.id }}')">❤️ <span id="likes_{{ post.id }}">{{ post.likes|length }}</span></button>
            <button onclick="toggleComments('{{ post.id }}')">💬 {{ post.comments|length }}</button>
{% if user and (user_key == post.author_key or is_admin) %}
            <button onclick="deletePost('{{ post.id }}')" style="color:#ef4444;">🗑️</button>
{% endif %}
        </div>
        <div class="comments-section" id="comments_{{ post.id }}" style="display:none;">
{% for c in post.comments %}
            <div class="comment">
                <span class="comment-nick">
                    {% if c.author_decorations and c.author_decorations.badge and c.author_decorations.badge.position == 'before' %}
                        {% if c.author_decorations.badge.has_custom_image and c.author_decorations.badge.image_url %}
                            <span class="decoration-badge anim-{{ c.author_decorations.badge.animation }} position-before size-{{ c.author_decorations.badge.size }}" style="color: {{ c.author_decorations.badge.color }};"><img src="{{ c.author_decorations.badge.image_url }}"></span>
                        {% else %}
                            <span class="decoration-badge anim-{{ c.author_decorations.badge.animation }} position-before size-{{ c.author_decorations.badge.size }}" style="color: {{ c.author_decorations.badge.color }};">{{ c.author_decorations.badge.emoji }}</span>
                        {% endif %}
                    {% endif %}
                    <b>{{ c.author_name }}</b>
                    {% if c.author_decorations and c.author_decorations.badge and (not c.author_decorations.badge.position or c.author_decorations.badge.position == 'after_nick') %}
                        {% if c.author_decorations.badge.has_custom_image and c.author_decorations.badge.image_url %}
                            <span class="decoration-badge anim-{{ c.author_decorations.badge.animation }} size-{{ c.author_decorations.badge.size }}" style="color: {{ c.author_decorations.badge.color }};"><img src="{{ c.author_decorations.badge.image_url }}"></span>
                        {% else %}
                            <span class="decoration-badge anim-{{ c.author_decorations.badge.animation }} size-{{ c.author_decorations.badge.size }}" style="color: {{ c.author_decorations.badge.color }};">{{ c.author_decorations.badge.emoji }}</span>
                        {% endif %}
                    {% endif %}
                </span>: {{ c.text }}
            </div>
{% endfor %}
{% if user %}
            <div style="display:flex; gap:8px; margin-top:10px;">
                <input type="text" id="comment_input_{{ post.id }}" placeholder="Комментарий..." style="flex:1; padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(30, 41, 59, 0.8); color:#fff; font-size:13px;">
                <button onclick="addComment('{{ post.id }}')" style="background:linear-gradient(135deg, #22c55e, #16a34a); color:#fff; border:none; padding:8px 14px; border-radius:8px; cursor:pointer; font-size:13px;">➕</button>
            </div>
{% endif %}
        </div>
    </div>
{% else %}
    <p style="color: #64748b; text-align: center;">Постов пока нет. Будьте первым!</p>
{% endfor %}
</div>

{% elif active_tab == 'shop' %}
<div class="shop-container">
    <h3 style="color: #38bdf8; margin-bottom: 20px;">🛒 Магазин</h3>
    <div style="background: linear-gradient(135deg, rgba(245,158,11,0.2), rgba(217,119,6,0.1)); border: 2px solid #f59e0b; padding: 24px; border-radius: 20px; margin-bottom: 28px; position: relative; overflow: hidden; box-shadow: 0 8px 32px rgba(245, 158, 11, 0.2);">
        <div style="position:absolute; top:-10px; right:-10px; font-size:100px; opacity:0.1;">⭐</div>
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:18px;">
            <div style="flex:1; min-width:220px;">
                <div style="font-size:22px; font-weight:bold; color:#f59e0b; margin-bottom:8px; text-shadow: 0 0 10px rgba(245, 158, 11, 0.5);">⭐ Бурмал PRO</div>
                <div style="font-size:14px; color:#f8fafc; margin-bottom:12px;">Премиум-подписка на <b>{{ subscription_duration_days }}</b> дня</div>
                <ul style="font-size:13px; color:#cbd5e1; margin:0; padding-left:20px; line-height:2;">
                    <li>✨ Золотой никнейм в чатах</li>
                    <li>💰 Награды за задания <b>x2</b></li>
                    <li>⭐ Значок PRO в профиле</li>
                    <li>🚀 Приоритетная поддержка</li>
                </ul>
                {% if user_subscription_active %}
                <div style="margin-top:12px; background:rgba(34,197,94,0.2); border:1px solid #22c55e; padding:10px; border-radius:10px; font-size:13px; color:#22c55e;">
                    ✅ Активна до {{ user_subscription_until }}
                </div>
                {% endif %}
            </div>
            <div style="text-align:center;">
                <div style="background:linear-gradient(135deg,#f59e0b,#d97706); color:#000; padding:12px 22px; border-radius:24px; font-weight:bold; font-size:18px; margin-bottom:12px; box-shadow: 0 4px 16px rgba(245, 158, 11, 0.5);">💰 12</div>
                {% if user %}
                    <button onclick="buySubscription()" style="background:linear-gradient(135deg,#f59e0b,#d97706); color:#000; border:none; padding:12px 24px; border-radius:10px; font-weight:bold; cursor:pointer; font-size:14px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);">
                        {% if user_subscription_active %}🔄 Продлить{% else %}💎 Купить{% endif %}
                    </button>
                    {% if user_subscription_active %}
                    <button onclick="cancelSubscription()" style="background:linear-gradient(135deg,#ef4444,#dc2626); color:#fff; border:none; padding:10px 18px; border-radius:8px; font-weight:bold; cursor:pointer; font-size:12px; margin-top:10px; display:block; width:100%;">
                        ❌ Отказаться
                    </button>
                    {% endif %}
                {% else %}
                    <div style="color:#f59e0b; font-size:13px;">Войдите, чтобы купить</div>
                {% endif %}
            </div>
        </div>
    </div>
    <h4 style="color:#38bdf8; margin-bottom:16px;">🎨 Паки стикеров</h4>
    <div class="shop-grid">
        {% for pack_id, pack_info in all_packs_for_shop %}
            <div class="shop-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <span class="shop-card-title">{{ pack_info.name }}</span>
                    {% if pack_info.price == 0 %}
                        <span class="shop-card-price free">Бесплатно</span>
                    {% else %}
                        <span class="shop-card-price">💰 {{ pack_info.price }}</span>
                    {% endif %}
                </div>
                <div class="shop-card-stickers">
                    {% for sticker in pack_info.stickers[:6] %}
                        <img src="{{ sticker }}" class="shop-card-sticker">
                    {% endfor %}
                </div>
                <div style="font-size: 12px; color: #94a3b8; margin-bottom: 10px;">Создатель: {{ pack_info.owner_name or 'Система' }}</div>
                {% if pack_id in user_owned_packs or is_admin %}
                    <button class="btn-buy owned" disabled>✓ В коллекции</button>
                {% elif pack_info.for_sale or pack_info.price == 0 %}
                    <button class="btn-buy" onclick="buyPack('{{ pack_id }}')">Купить</button>
                {% else %}
                    <button class="btn-buy owned" disabled>Не продаётся</button>
                {% endif %}
            </div>
        {% endfor %}
    </div>
</div>

{% elif active_tab == 'decorations' %}
<div class="shop-container">
    <h3 style="color: #38bdf8; margin-bottom: 12px;">✨ Галерея украшений</h3>
    <p style="color: #94a3b8; font-size: 14px; margin-bottom: 22px;">Покупайте уникальные украшения! Купленные украшения <b>сразу надеваются</b> и отображаются ВЕЗДЕ: в чатах, постах, профиле, списке участников!</p>
    <div style="background: rgba(11, 17, 32, 0.8); padding: 18px; border-radius: 16px; margin-bottom: 22px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; border: 1px solid rgba(255,255,255,0.05);">
        <div>
            <div style="font-size: 12px; color: #94a3b8;">Ваши украшения</div>
            <div style="font-size: 26px; font-weight: bold; color: #22c55e;">{{ user_owned_decorations|length }} / {{ all_decorations|length }}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 12px; color: #94a3b8;">Надето сейчас</div>
            <div style="font-size: 22px; font-weight: bold; color: #f59e0b;">✨ {{ user_equipped_decorations|length }}</div>
        </div>
    </div>
    <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
        <button class="tab-btn {% if dec_filter == 'all' %}active{% endif %}" onclick="filterDecorations('all')">Все</button>
        <button class="tab-btn {% if dec_filter == 'owned' %}active{% endif %}" onclick="filterDecorations('owned')">Мои</button>
        <button class="tab-btn {% if dec_filter == 'badge' %}active{% endif %}" onclick="filterDecorations('badge')">🏆 Значки</button>
        <button class="tab-btn {% if dec_filter == 'frame' %}active{% endif %}" onclick="filterDecorations('frame')">💎 Рамки</button>
        <button class="tab-btn {% if dec_filter == 'effect' %}active{% endif %}" onclick="filterDecorations('effect')">🔥 Эффекты</button>
        <button class="tab-btn {% if dec_filter == 'background' %}active{% endif %}" onclick="filterDecorations('background')">🌌 Фоны</button>
        <button class="tab-btn {% if dec_filter == 'nickname' %}active{% endif %}" onclick="filterDecorations('nickname')">📝 Ники</button>
    </div>
    <div class="decorations-grid" id="decorationsGrid">
        {% for dec_id, dec in all_decorations.items() %}
        <div class="decoration-card rarity-{{ dec.rarity }}" data-type="{{ dec.type }}" data-owned="{{ 'true' if dec_id in user_owned_decorations else 'false' }}">
            {% if dec_id in user_equipped_decorations %}
            <div class="decoration-status">✓ НАДЕТО</div>
            {% endif %}
            <div class="decoration-preview-wrap" style="color: {{ dec.color }};">
                {% if dec.has_custom_image and dec.custom_image_url %}
                    <img src="{{ dec.custom_image_url }}" class="decoration-preview-image anim-{{ dec.animation }}">
                {% else %}
                    <span class="decoration-preview-emoji anim-{{ dec.animation }}">{{ dec.emoji }}</span>
                {% endif %}
            </div>
            <div class="decoration-name">{{ dec.name }}</div>
            <div class="decoration-type">Тип: {{ dec.type }}</div>
            <div class="decoration-desc">{{ dec.description }}</div>
            <span class="decoration-rarity">{{ dec.rarity|upper }}</span>
            <div style="margin-top: 10px;">
                {% if dec_id in user_owned_decorations %}
                    {% if dec_id in user_equipped_decorations %}
                        <button class="btn-unequip" onclick="unequipDecoration('{{ dec_id }}')">Снять</button>
                    {% else %}
                        <button class="btn-equip" onclick="equipDecoration('{{ dec_id }}')">Надеть</button>
                    {% endif %}
                {% else %}
                    <button class="btn-buy" onclick="buyDecorationAndEquip('{{ dec_id }}')" style="padding: 8px 14px; font-size: 12px;">💰 Купить за {{ dec.price }} и надеть</button>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
</div>

{% elif active_tab == 'workshop' %}
<div class="workshop-container">
    <h3 style="color: #38bdf8; margin-bottom: 20px;">🎨 Мастерская</h3>
    
    {% if workshop_mode == 'choose' or not workshop_mode %}
    <p style="color: #94a3b8; font-size: 14px; margin-bottom: 22px;">Выберите, что вы хотите создать:</p>
    
    <div class="workshop-type-selector">
        <div class="workshop-type-card sticker-card" onclick="selectWorkshopMode('sticker')">
            <div class="workshop-type-icon" style="color: #38bdf8;">🎨</div>
            <div class="workshop-type-title">Создать пак стикеров</div>
            <div class="workshop-type-desc">Загрузите свои изображения и создайте уникальный пак стикеров для чата</div>
            <ul class="workshop-type-features">
                <li>✓ До 20 стикеров в паке</li>
                <li>✓ Поддержка PNG, JPG, WEBP, GIF</li>
                <li>✓ Возможность продажи</li>
                <li>✓ Проверка модератором</li>
                <li>✓ Настройка цены и названия</li>
            </ul>
        </div>
        
        <div class="workshop-type-card decoration-card" onclick="selectWorkshopMode('decoration')">
            <div class="workshop-type-icon" style="color: #a855f7;">✨</div>
            <div class="workshop-type-title">Создать украшение</div>
            <div class="workshop-type-desc">Создайте уникальное украшение с <b>кастомной картинкой</b>! Отображается ВЕЗДЕ как в Discord!</div>
            <ul class="workshop-type-features">
                <li>✓ 5 типов: значок, рамка, эффект, фон, ник</li>
                <li>✓ <b>Загрузка своих PNG/GIF картинок</b></li>
                <li>✓ 20+ анимаций: glow, float, rainbow, sparkle...</li>
                <li>✓ Выбор редкости и цены</li>
                <li>✓ Отображение в чатах, постах, профиле</li>
            </ul>
        </div>
    </div>
    
    {% elif workshop_mode == 'sticker' %}
    <p style="color: #94a3b8; font-size: 14px; margin-bottom: 22px;">Создание пака стикеров</p>
    
    <div class="workshop-steps">
        <div class="workshop-step {% if workshop_step == 1 %}active{% elif workshop_step > 1 %}done{% endif %}" onclick="goToWorkshopStep(1)">1️⃣ Выбор пака</div>
        <div class="workshop-step {% if workshop_step == 2 %}active{% elif workshop_step > 2 %}done{% endif %}" onclick="goToWorkshopStep(2)">2️⃣ Загрузка</div>
        <div class="workshop-step {% if workshop_step == 3 %}active{% elif workshop_step > 3 %}done{% endif %}" onclick="goToWorkshopStep(3)">3️⃣ Настройка</div>
        <div class="workshop-step {% if workshop_step == 4 %}active{% endif %}" onclick="goToWorkshopStep(4)">4️⃣ Проверка</div>
    </div>
    
    <div class="workshop-panel">
        {% if workshop_step == 1 %}
        <h4 style="color: #38bdf8; margin-top: 0;">Выберите или создайте пак</h4>
        <p style="color: #94a3b8; font-size: 13px;">Вы можете добавить стикеры в существующий пак или создать новый.</p>
        
        {% if my_workshop_packs %}
        <h5 style="color: #f8fafc; margin-top: 20px;">Мои паки:</h5>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-bottom: 20px;">
            {% for pack_id, pack_info in my_workshop_packs %}
            <div style="background: rgba(30, 41, 59, 0.8); padding: 14px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); cursor: pointer; transition: all 0.2s;" onclick="selectWorkshopPack('{{ pack_id }}')" onmouseover="this.style.borderColor='#38bdf8'" onmouseout="this.style.borderColor='rgba(255,255,255,0.05)'">
                <div style="font-weight: bold; color: #38bdf8; margin-bottom: 6px;">{{ pack_info.name }}</div>
                <div style="font-size: 12px; color: #94a3b8;">Стикеров: {{ pack_info.stickers|length }}</div>
                <div style="font-size: 12px; color: #94a3b8;">Цена: {{ pack_info.price }} 💰</div>
                {% if pack_info.for_sale %}<div style="font-size: 11px; color: #22c55e; margin-top: 4px;">🏷️ На продаже</div>{% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div style="background: rgba(34, 197, 94, 0.1); border: 2px dashed #22c55e; padding: 20px; border-radius: 12px; text-align: center;">
            <div style="font-size: 16px; font-weight: bold; color: #22c55e; margin-bottom: 10px;">✨ Создать новый пак</div>
            <div class="profile-field" style="margin-bottom: 12px;">
                <label>Название пака (до 30 символов):</label>
                <input type="text" id="newPackName" maxlength="30" placeholder="Например: Мои эмоции">
            </div>
            <div class="profile-field" style="margin-bottom: 12px;">
                <label>Описание (до 100 символов):</label>
                <textarea id="newPackDesc" maxlength="100" rows="2" placeholder="О чём этот пак?"></textarea>
            </div>
            <div class="profile-field" style="margin-bottom: 12px;">
                <label>Цена продажи (0 = бесплатно):</label>
                <input type="number" id="newPackPrice" min="0" value="0" placeholder="0">
            </div>
            <button onclick="createNewWorkshopPack()" style="background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; border: none; padding: 10px 22px; border-radius: 10px; font-weight: bold; cursor: pointer;">Создать пак</button>
        </div>
        
        {% elif workshop_step == 2 %}
        <h4 style="color: #38bdf8; margin-top: 0;">Загрузка стикеров в пак: <span style="color: #f59e0b;" id="currentPackName">{{ workshop_pack_name }}</span></h4>
        <p style="color: #94a3b8; font-size: 13px;">Загрузите изображения (PNG, JPG, WEBP, GIF). Максимум 20 стикеров в паке.</p>
        
        <div class="workshop-upload-zone" id="uploadZone" onclick="document.getElementById('workshopFileInput').click()">
            <div style="font-size: 48px; margin-bottom: 10px;">📤</div>
            <div style="font-size: 14px; color: #f8fafc; margin-bottom: 6px;">Нажмите или перетащите файлы сюда</div>
            <div style="font-size: 12px; color: #94a3b8;">Поддерживаются: PNG, JPG, WEBP, GIF</div>
            <input type="file" id="workshopFileInput" accept="image/png,image/jpeg,image/webp,image/gif" multiple style="display:none;" onchange="handleWorkshopUpload(this)">
        </div>
        
        <div id="uploadProgress" style="display:none; margin-bottom: 16px;">
            <div style="background: rgba(0,0,0,0.3); height: 8px; border-radius: 4px; overflow: hidden;">
                <div id="progressBar" style="background: linear-gradient(90deg, #38bdf8, #0284c7); height: 100%; width: 0%; transition: width 0.3s;"></div>
            </div>
            <div id="progressText" style="font-size: 12px; color: #94a3b8; margin-top: 6px; text-align: center;">Загрузка...</div>
        </div>
        
        <div id="previewGrid" class="workshop-preview-grid">
            {% for sticker in workshop_pending_stickers %}
            <div class="workshop-preview-item" id="preview_{{ sticker.id }}">
                <img src="/static/stickers/pending/{{ sticker.filename }}" alt="стикер">
                <button class="remove-btn" onclick="removePendingSticker('{{ sticker.id }}')">✖</button>
            </div>
            {% endfor %}
        </div>
        
        {% if workshop_pending_stickers %}
        <div style="margin-top: 20px; padding: 14px; background: rgba(56, 189, 248, 0.1); border-radius: 10px; border-left: 3px solid #38bdf8;">
            <div style="font-size: 13px; color: #38bdf8; font-weight: bold;">📦 В очереди: {{ workshop_pending_stickers|length }} стикеров</div>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">После загрузки всех стикеров перейдите к настройке</div>
        </div>
        {% endif %}
        
        <div style="display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap;">
            <button onclick="goToWorkshopStep(1)" style="background: #475569; color: #fff; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold;">← Назад</button>
            <button onclick="goToWorkshopStep(3)" style="background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold;" {% if not workshop_pending_stickers %}disabled style="opacity:0.5; cursor:not-allowed;"{% endif %}>Далее →</button>
        </div>
        
        {% elif workshop_step == 3 %}
        <h4 style="color: #38bdf8; margin-top: 0;">Настройка пака</h4>
        <p style="color: #94a3b8; font-size: 13px;">Проверьте и настройте параметры перед отправкой на модерацию.</p>
        
        <div style="background: rgba(30, 41, 59, 0.8); padding: 18px; border-radius: 12px; margin-bottom: 16px;">
            <div class="profile-field">
                <label>Название пака:</label>
                <input type="text" id="editPackName" value="{{ workshop_pack_name }}" maxlength="30">
            </div>
            <div class="profile-field">
                <label>Описание:</label>
                <textarea id="editPackDesc" maxlength="100" rows="2">{{ workshop_pack_desc }}</textarea>
            </div>
            <div class="profile-field">
                <label>Цена (0 = бесплатно):</label>
                <input type="number" id="editPackPrice" min="0" value="{{ workshop_pack_price }}">
            </div>
            <div class="profile-field">
                <label>
                    <input type="checkbox" id="editPackForSale" {% if workshop_pack_for_sale %}checked{% endif %}> 
                    Выставить на продажу в магазине
                </label>
            </div>
        </div>
        
        <h5 style="color: #f8fafc;">Стикеры в паке ({{ workshop_pending_stickers|length }}):</h5>
        <div class="workshop-preview-grid" style="margin-bottom: 16px;">
            {% for sticker in workshop_pending_stickers %}
            <div class="workshop-preview-item">
                <img src="/static/stickers/pending/{{ sticker.filename }}" alt="стикер">
            </div>
            {% endfor %}
        </div>
        
        <div style="display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap;">
            <button onclick="goToWorkshopStep(2)" style="background: #475569; color: #fff; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold;">← Назад</button>
            <button onclick="goToWorkshopStep(4)" style="background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold;">Далее →</button>
        </div>
        
        {% elif workshop_step == 4 %}
        <h4 style="color: #38bdf8; margin-top: 0;">Проверка и отправка на модерацию</h4>
        
        <div style="background: rgba(30, 41, 59, 0.8); padding: 18px; border-radius: 12px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: #94a3b8;">Название:</span>
                <span style="color: #f8fafc; font-weight: bold;">{{ workshop_pack_name }}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: #94a3b8;">Описание:</span>
                <span style="color: #f8fafc;">{{ workshop_pack_desc or '—' }}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: #94a3b8;">Количество стикеров:</span>
                <span style="color: #f8fafc; font-weight: bold;">{{ workshop_pending_stickers|length }}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="color: #94a3b8;">Цена:</span>
                <span style="color: #f59e0b; font-weight: bold;">💰 {{ workshop_pack_price }}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">Продажа:</span>
                <span style="color: {% if workshop_pack_for_sale %}#22c55e{% else %}#94a3b8{% endif %}; font-weight: bold;">{% if workshop_pack_for_sale %}✅ Да{% else %}❌ Нет{% endif %}</span>
            </div>
        </div>
        
        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid #f59e0b; padding: 14px; border-radius: 10px; margin-bottom: 16px;">
            <div style="font-size: 13px; color: #f59e0b; font-weight: bold; margin-bottom: 6px;">⚠️ Важно перед отправкой:</div>
            <ul style="font-size: 12px; color: #cbd5e1; margin: 0; padding-left: 20px; line-height: 1.8;">
                <li>Стикеры будут проверены модератором</li>
                <li>Неприемлемый контент будет отклонён</li>
                <li>После одобрения стикеры появятся в паке</li>
                <li>Вы сможете управлять паком в настройках</li>
            </ul>
        </div>
        
        <div style="display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap;">
            <button onclick="goToWorkshopStep(3)" style="background: #475569; color: #fff; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold;">← Назад</button>
            <button onclick="submitWorkshopForModeration()" style="background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 14px; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.4);">🚀 Отправить на модерацию</button>
        </div>
        {% endif %}
    </div>
    
    <div style="margin-top: 20px; text-align: center;">
        <button onclick="selectWorkshopMode('choose')" style="background: #475569; color: #fff; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold;">← Вернуться к выбору</button>
    </div>
    
    {% elif workshop_mode == 'decoration' %}
    <p style="color: #94a3b8; font-size: 14px; margin-bottom: 22px;">Создание украшения с <b>кастомной картинкой</b></p>
    
    <div class="workshop-panel">
        <h4 style="color: #a855f7; margin-top: 0;">✨ Создайте своё уникальное украшение</h4>
        <p style="color: #94a3b8; font-size: 13px;">Загрузите <b>свою PNG/GIF картинку</b> или используйте эмодзи. Украшение будет отображаться ВЕЗДЕ как в Discord: в чатах, постах, профиле, списке участников!</p>
        
        <form id="decorationForm" enctype="multipart/form-data">
            <div style="background: rgba(30, 41, 59, 0.8); padding: 18px; border-radius: 12px; margin-bottom: 16px;">
                <div class="profile-field">
                    <label>Название украшения (до 30 символов):</label>
                    <input type="text" id="decName" maxlength="30" placeholder="Например: Мой крутой значок" required>
                </div>
                <div class="profile-field">
                    <label>Тип украшения:</label>
                    <select id="decType" onchange="updateDecorationPreview()">
                        <option value="badge">🏆 Значок (рядом с ником)</option>
                        <option value="frame">💎 Рамка (вокруг аватарки)</option>
                        <option value="effect">🔥 Эффект (свечение вокруг аватарки)</option>
                        <option value="background">🌌 Фон (фон профиля)</option>
                        <option value="nickname">📝 Стиль ника (цветной никнейм)</option>
                    </select>
                </div>
                <div class="profile-field">
                    <label>Эмодзи (если нет картинки):</label>
                    <input type="text" id="decEmoji" maxlength="4" value="✨" placeholder="✨" oninput="updateDecorationPreview()">
                </div>
                <div class="profile-field">
                    <label>📸 Загрузить свою картинку (PNG, GIF, WEBP, JPG):</label>
                    <div class="image-upload-area" id="imageUploadArea" onclick="document.getElementById('decImageFile').click()">
                        <div style="font-size: 36px; margin-bottom: 8px;">📤</div>
                        <div style="font-size: 13px; color: #f8fafc;">Нажмите, чтобы загрузить картинку</div>
                        <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">Рекомендуемый размер: 128x128px, прозрачный фон</div>
                        <img id="imagePreview" style="display:none;">
                    </div>
                    <input type="file" id="decImageFile" accept="image/png,image/gif,image/webp,image/jpeg" style="display:none;" onchange="previewDecImage(this)">
                    <button type="button" id="removeImageBtn" onclick="removeDecImage()" style="display:none; background:#ef4444; color:#fff; border:none; padding:6px 12px; border-radius:6px; font-size:12px; cursor:pointer; margin-top:6px;">🗑️ Убрать картинку</button>
                </div>
                <div class="profile-field">
                    <label>Описание (до 100 символов):</label>
                    <textarea id="decDescription" maxlength="100" rows="2" placeholder="Описание украшения"></textarea>
                </div>
                <div class="profile-field">
                    <label>Цвет (для эффектов):</label>
                    <input type="color" id="decColor" value="#38bdf8" oninput="updateDecorationPreview()">
                </div>
                <div class="profile-field">
                    <label>Анимация:</label>
                    <select id="decAnimation" onchange="updateDecorationPreview()">
                        <option value="none">Без анимации</option>
                        <option value="glow">✨ Свечение</option>
                        <option value="float">🎈 Парение</option>
                        <option value="rotate">🔄 Вращение</option>
                        <option value="sparkle">💫 Мерцание</option>
                        <option value="pulse">💓 Пульсация</option>
                        <option value="shimmer">✨ Переливание</option>
                        <option value="rainbow">🌈 Радуга</option>
                        <option value="flicker">🔥 Мерцание огня</option>
                        <option value="electric">⚡ Электричество</option>
                        <option value="magic">✨ Магия</option>
                        <option value="burn">🔥 Горение</option>
                        <option value="aura">🌟 Аура</option>
                        <option value="neon">💜 Неон</option>
                        <option value="snow">❄️ Снег</option>
                        <option value="hearts">💕 Сердечки</option>
                    </select>
                </div>
                <div class="profile-field" id="positionField">
                    <label>Позиция значка:</label>
                    <select id="decPosition">
                        <option value="after_nick">После ника</option>
                        <option value="before">Перед ником</option>
                        <option value="above">Над ником</option>
                    </select>
                </div>
                <div class="profile-field" id="sizeField">
                    <label>Размер значка:</label>
                    <select id="decSize">
                        <option value="small">Маленький</option>
                        <option value="medium" selected>Средний</option>
                        <option value="large">Большой</option>
                    </select>
                </div>
                <div class="profile-field">
                    <label>Редкость:</label>
                    <select id="decRarity">
                        <option value="common">Common (обычное)</option>
                        <option value="rare">Rare (редкое)</option>
                        <option value="epic">Epic (эпическое)</option>
                        <option value="legendary">Legendary (легендарное)</option>
                    </select>
                </div>
                <div class="profile-field">
                    <label>Цена продажи (0 = бесплатно, мин. 5):</label>
                    <input type="number" id="decPrice" min="0" value="15">
                </div>
                <div class="profile-field">
                    <label>Интенсивность эффекта (0.1 - 1.0):</label>
                    <input type="number" id="decIntensity" min="0.1" max="1.0" step="0.1" value="0.8">
                </div>
            </div>
            
            <div style="background: rgba(30, 41, 59, 0.8); padding: 18px; border-radius: 12px; margin-bottom: 16px;">
                <h5 style="color: #f8fafc; margin-top: 0;">👁️ Живой предпросмотр:</h5>
                <div id="decorationPreview" class="decoration-editor-preview">
                    <div class="preview-avatar" id="previewAvatar"></div>
                    <span class="preview-nick" id="previewNick">ВашНик</span>
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <div style="display: inline-block; padding: 8px 16px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                        <span style="font-size: 12px; color: #94a3b8;">Как будет выглядеть в чате: </span>
                        <span id="previewInChat" style="font-size: 14px; font-weight: bold; color: #38bdf8;">ВашНик</span>
                    </div>
                </div>
            </div>
            
            <div style="display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap;">
                <button type="button" onclick="selectWorkshopMode('choose')" style="background: #475569; color: #fff; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold;">← Назад</button>
                <button type="button" onclick="createCustomDecoration()" style="background: linear-gradient(135deg, #a855f7, #7c3aed); color: #fff; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 14px; box-shadow: 0 4px 12px rgba(168, 85, 247, 0.4);">✨ Создать украшение</button>
            </div>
        </form>
    </div>
    {% endif %}
</div>

{% elif active_tab == 'tasks' %}
<div class="tasks-container">
    <h3 style="color: #38bdf8; margin-bottom: 12px;">🎯 Ежедневные задания</h3>
    <p style="color: #94a3b8; font-size: 14px; margin-bottom: 22px;">
        Задания обновляются каждый день в 00:00. Выполняй и получай бурмалкоины! 💰
        {% if user_subscription_active %}
        <span style="color: #f59e0b; font-weight: bold;">⭐ У вас подписка Бурмал PRO — награды x2!</span>
        {% endif %}
    </p>
    <div style="background: rgba(11, 17, 32, 0.8); padding: 18px; border-radius: 16px; margin-bottom: 22px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; border: 1px solid rgba(255,255,255,0.05);">
        <div>
            <div style="font-size: 12px; color: #94a3b8;">Выполнено сегодня</div>
            <div style="font-size: 26px; font-weight: bold; color: #22c55e;">{{ completed_tasks_count }} / {{ daily_tasks|length }}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 12px; color: #94a3b8;">Заработано сегодня</div>
            <div style="font-size: 22px; font-weight: bold; color: #f59e0b;">💰 {{ earned_today }}</div>
        </div>
    </div>
    {% for task in daily_tasks %}
    <div style="background: rgba(11, 17, 32, 0.8); padding: 18px; border-radius: 16px; margin-bottom: 12px; border-left: 4px solid {% if task.completed %}#22c55e{% else %}#38bdf8{% endif %}; transition: all 0.2s; border: 1px solid rgba(255,255,255,0.05); border-left: 4px solid {% if task.completed %}#22c55e{% else %}#38bdf8{% endif %};">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div style="flex: 1;">
                <div style="font-size: 16px; font-weight: bold; color: #f8fafc;">
                    {% if task.completed %}✅{% else %}🔹{% endif %} {{ task.title }}
                </div>
                <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">{{ task.description }}</div>
                <div style="font-size: 12px; color: #64748b; margin-top: 4px;">Прогресс: {{ task.progress }} / {{ task.target }}</div>
                <div style="background: rgba(0,0,0,0.3); height: 6px; border-radius: 3px; margin-top: 6px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #38bdf8, #0284c7); height: 100%; width: {{ (task.progress / task.target * 100) if task.target > 0 else 0 }}%; transition: width 0.3s;"></div>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; padding: 6px 14px; border-radius: 14px; font-weight: bold; font-size: 13px; display: inline-block;">
                    💰 {{ task.reward }}
                </div>
                {% if not task.completed and task.progress >= task.target %}
                <button onclick="claimTaskReward('{{ task.id }}')" style="background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 8px; display: block; width: 100%; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.4);">
                    Забрать
                </button>
                {% elif task.completed %}
                <div style="color: #22c55e; font-size: 12px; margin-top: 8px; font-weight: bold;">Выполнено ✓</div>
                {% endif %}
            </div>
        </div>
    </div>
    {% else %}
    <p style="color: #64748b; text-align: center;">Войдите, чтобы видеть задания.</p>
    {% endfor %}
    {% if user_subscription_active %}
    <div style="background: linear-gradient(135deg, rgba(245,158,11,0.2), rgba(217,119,6,0.1)); border: 1px solid #f59e0b; padding: 14px; border-radius: 12px; margin-top: 18px; font-size: 13px; color: #f59e0b;">
        ⭐ Подписка Бурмал PRO активна до {{ user_subscription_until }}. Все награды удвоены!
    </div>
    {% endif %}
</div>

{% elif active_tab == 'burmalda_fm' %}
<div class="burmalda-container">
    <h3 style="color: #38bdf8; margin-bottom: 20px;">🎵 Burmalda FM - Прямой эфир</h3>
    <div class="burmalda-player">
        <div class="burmalda-iframe-wrapper">
            <iframe class="burmalda-iframe" src="https://www.youtube-nocookie.com/embed/9PJ3LZLcR20?autoplay=0&rel=0&modestbranding=1" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>
        </div>
        <div style="margin-top: 18px; display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
            <a href="https://www.youtube.com/watch?v=9PJ3LZLcR20" target="_blank" style="background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; padding: 12px 20px; border-radius: 10px; text-decoration: none; font-weight: bold; font-size: 14px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);">▶️ Открыть на YouTube</a>
            <button onclick="copyStreamLink()" style="background: linear-gradient(135deg, #38bdf8, #0284c7); color: #0f172a; padding: 12px 20px; border-radius: 10px; border: none; font-weight: bold; font-size: 14px; cursor: pointer; box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);">📋 Скопировать</button>
        </div>
        {% if user %}
        <div class="fm-viewers">
            <h5>👥 Сейчас смотрят вместе с вами (<span id="fmViewersCount">{{ fm_viewers|length }}</span>):</h5>
            <div id="fmViewersList">
                {% for viewer_key, viewer_info in fm_viewers.items() %}
                <div class="fm-viewer-item">
                    <div class="fm-viewer-avatar-wrap">
                        {% if viewer_info.picture %}<img src="{{ viewer_info.picture }}" class="fm-viewer-avatar">
                        {% else %}<div class="fm-viewer-avatar" style="background:#334155; display:flex;align-items:center;justify-content:center;font-size:10px;">👤</div>{% endif %}
                        {% if viewer_info.decorations and viewer_info.decorations.frame %}
                            {% if viewer_info.decorations.frame.has_custom_image and viewer_info.decorations.frame.image_url %}
                                <img src="{{ viewer_info.decorations.frame.image_url }}" class="decoration-frame anim-{{ viewer_info.decorations.frame.animation }}">
                            {% else %}
                                <div class="decoration-frame anim-{{ viewer_info.decorations.frame.animation }}" style="border: {{ viewer_info.decorations.frame.border_width or 3 }}px solid {{ viewer_info.decorations.frame.color }}; box-shadow: 0 0 10px {{ viewer_info.decorations.frame.color }};"></div>
                            {% endif %}
                        {% endif %}
                    </div>
                    <span class="fm-nick">
                        {% if viewer_info.decorations and viewer_info.decorations.badge and viewer_info.decorations.badge.position == 'before' %}
                            {% if viewer_info.decorations.badge.has_custom_image and viewer_info.decorations.badge.image_url %}
                                <span class="decoration-badge anim-{{ viewer_info.decorations.badge.animation }} position-before size-{{ viewer_info.decorations.badge.size }}" style="color: {{ viewer_info.decorations.badge.color }};"><img src="{{ viewer_info.decorations.badge.image_url }}"></span>
                            {% else %}
                                <span class="decoration-badge anim-{{ viewer_info.decorations.badge.animation }} position-before size-{{ viewer_info.decorations.badge.size }}" style="color: {{ viewer_info.decorations.badge.color }};">{{ viewer_info.decorations.badge.emoji }}</span>
                            {% endif %}
                        {% endif %}
                        {{ viewer_info.name }}
                        {% if viewer_info.decorations and viewer_info.decorations.badge and (not viewer_info.decorations.badge.position or viewer_info.decorations.badge.position == 'after_nick') %}
                            {% if viewer_info.decorations.badge.has_custom_image and viewer_info.decorations.badge.image_url %}
                                <span class="decoration-badge anim-{{ viewer_info.decorations.badge.animation }} size-{{ viewer_info.decorations.badge.size }}" style="color: {{ viewer_info.decorations.badge.color }};"><img src="{{ viewer_info.decorations.badge.image_url }}"></span>
                            {% else %}
                                <span class="decoration-badge anim-{{ viewer_info.decorations.badge.animation }} size-{{ viewer_info.decorations.badge.size }}" style="color: {{ viewer_info.decorations.badge.color }};">{{ viewer_info.decorations.badge.emoji }}</span>
                            {% endif %}
                        {% endif %}
                    </span>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
</div>

{% elif active_tab == 'admin_panel' and is_admin %}
<h3>⚙️ Админ панель Бурмалдод</h3>
<div class="admin-section">
    <h4>🤖 Боты</h4>
    <button class="btn-create-group" style="width: auto; padding: 10px 18px; margin-bottom: 16px;" onclick="createBot()">🤖 Создать бота</button>
    {% for bot_id, bot in bots.items() %}
        <div class="bot-card">
            <form action="/admin/save_bot" method="post">
                <input type="hidden" name="bot_id" value="{{ bot_id }}">
                <div style="display: flex; gap: 10px; margin-bottom: 10px; flex-wrap:wrap;">
                    <input type="text" name="name" value="{{ bot.name }}" placeholder="Имя бота" style="flex:1; padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:#0f172a; color:#fff;">
                    <input type="text" name="avatar" value="{{ bot.avatar }}" placeholder="URL Аватарки" style="flex:2; padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:#0f172a; color:#fff;">
                    <label style="font-size:12px; display:flex; align-items:center; gap:4px;"><input type="checkbox" name="enabled" {% if bot.enabled %}checked{% endif %}> Вкл</label>
                </div>
                <textarea name="script" class="code-editor">{{ bot.script }}</textarea>
                <div style="display:flex; justify-content:space-between; margin-top:10px;">
                    <button type="submit" style="background:linear-gradient(135deg, #22c55e, #16a34a); color:#fff; border:none; padding:8px 14px; border-radius:8px; font-weight:bold; cursor:pointer;">Сохранить</button>
                    <a href="/admin/delete_bot/{{ bot_id }}" style="color:#ef4444; font-size:12px; text-decoration:none;" onclick="return confirm('Удалить бота?')">🗑️ Удалить</a>
                </div>
            </form>
        </div>
    {% endfor %}
</div>
<div class="admin-section">
    <h4>🎨 Паки стикеров</h4>
    {% for pack_id, pack_info in all_packs_admin %}
        <div style="background:rgba(30, 41, 59, 0.8); padding:12px; border-radius:10px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
                <b>{{ pack_info.name }}</b><br>
                <small style="color:#94a3b8;">Стикеров: {{ pack_info.stickers|length }} | Цена: {{ pack_info.price }} | Владелец: {{ pack_info.owner_name or 'Система' }}</small>
            </div>
            <a href="/admin/delete_pack/{{ pack_id }}" style="background:linear-gradient(135deg, #ef4444, #dc2626); color:#fff; padding:8px 14px; border-radius:8px; text-decoration:none; font-size:12px;" onclick="return confirm('Удалить пак?')">🗑️</a>
        </div>
    {% endfor %}
</div>
<div class="admin-section">
    <h4>✨ Украшения ({{ all_decorations|length }})</h4>
    <button class="btn-create-group" style="width: auto; padding: 10px 18px; margin-bottom: 16px;" onclick="document.getElementById('createDecorationModal').style.display='flex'">✨ Создать украшение</button>
    {% for dec_id, dec in all_decorations.items() %}
        <div style="background:rgba(30, 41, 59, 0.8); padding:12px; border-radius:10px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div style="display:flex; align-items:center; gap:10px;">
                {% if dec.has_custom_image and dec.custom_image_url %}
                    <img src="{{ dec.custom_image_url }}" style="width:40px; height:40px; object-fit:contain; border-radius:6px; background:rgba(0,0,0,0.3); padding:4px;">
                {% else %}
                    <span style="font-size: 32px;">{{ dec.emoji }}</span>
                {% endif %}
                <div>
                    <b>{{ dec.name }}</b>
                    <span style="color:#94a3b8; font-size:12px; margin-left:8px;">({{ dec.type }} | {{ dec.rarity }})</span>
                    {% if dec.has_custom_image %}<span style="color:#22c55e; font-size:11px; margin-left:8px;">📸 С картинкой</span>{% endif %}
                    <div style="font-size:12px; color:#f59e0b;">💰 {{ dec.price }}</div>
                </div>
            </div>
            <a href="/admin/delete_decoration/{{ dec_id }}" style="background:linear-gradient(135deg, #ef4444, #dc2626); color:#fff; padding:8px 14px; border-radius:8px; text-decoration:none; font-size:12px;" onclick="return confirm('Удалить украшение?')">🗑️</a>
        </div>
    {% endfor %}
</div>
<div class="admin-section">
    <h4>👥 Группы ({{ all_groups|length }})</h4>
    {% for gid, ginfo in all_groups.items() %}
        <div style="background:rgba(30, 41, 59, 0.8); padding:10px 14px; border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px;">
            <span><b>{{ ginfo.name }}</b> {% if ginfo.is_public %}<span style="color:#22c55e;">🌐</span>{% else %}<span style="color:#f59e0b;">🔒</span>{% endif %}</span>
            <span style="font-size:12px; color:#94a3b8;">ID: {{ gid }}</span>
        </div>
    {% endfor %}
</div>
<div class="admin-section">
    <h4>👤 Пользователи ({{ all_users|length }})</h4>
    {% for ukey, uprof in all_users.items() %}
        <div style="background:rgba(30, 41, 59, 0.8); padding:10px 14px; border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div><b>{{ uprof.get('custom_nick') or 'Без имени' }}</b> 💰 {{ uprof.get('burmalnets', 5) }}</div>
            <span style="font-size:12px; color:#38bdf8;">{{ ukey }}</span>
        </div>
    {% endfor %}
</div>
<div style="margin-top:22px;">
    <form action="/toggle_shutdown" method="post" style="display:inline;">
        {% if is_maintenance %}
            <button type="submit" style="background:linear-gradient(135deg, #22c55e, #16a34a); color:#fff; border:none; padding:12px 22px; border-radius:8px; font-weight:bold; cursor:pointer;">▶️ Включить сервер</button>
        {% else %}
            <button type="submit" style="background:linear-gradient(135deg, #ef4444, #dc2626); color:#fff; border:none; padding:12px 22px; border-radius:8px; font-weight:bold; cursor:pointer;">⛔ Выключить сервер</button>
        {% endif %}
    </form>
</div>

{% elif active_tab == 'pending' and is_admin %}
<h3>Запросы на добавление стикеров:</h3>
{% if pending_stickers %}
    {% for item in pending_stickers %}
        <div style="background: rgba(11, 17, 32, 0.8); padding: 18px; border-radius: 14px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap:wrap; gap:12px;">
            <img src="/static/stickers/pending/{{ item.filename }}" style="width: 90px; height: 90px; object-fit: contain;">
            <div>
                <div><b>От:</b> {{ item.user }}</div>
                <div style="font-size: 12px; color: #94a3b8;">{{ item.time }}</div>
                <div style="font-size: 11px; color: #38bdf8;">Пак: {{ item.pack_name }}</div>
            </div>
            <div style="display:flex; gap:8px;">
                <form action="/admin/approve_sticker" method="post" style="display:inline;">
                    <input type="hidden" name="sticker_id" value="{{ item.id }}">
                    <button type="submit" style="background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; border: none; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: bold;">Одобрить</button>
                </form>
                <form action="/admin/reject_sticker" method="post" style="display:inline;">
                    <input type="hidden" name="sticker_id" value="{{ item.id }}">
                    <button type="submit" style="background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; border: none; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: bold;">Отклонить</button>
                </form>
            </div>
        </div>
    {% endfor %}
{% else %}<p style="color: #64748b; text-align: center;">Нет стикеров на проверке.</p>{% endif %}

{% else %}
<h3>📁 Файлы на Диске:</h3>
{% if files %}
    {% for file in files %}
    <div class="file-item">
        <span>📄 {{ file.name }}</span>
        <a href="/download/{{ file.id }}/{{ file.name }}" class="btn-download">⬇️ Скачать</a>
    </div>
    {% endfor %}
{% else %}<p style="color: #64748b; text-align: center;">Файлов пока нет.</p>{% endif %}
{% endif %}
{% endif %}
</div>

<!-- Модальные окна -->
<div id="contextMenu" class="context-menu">
    <div class="context-menu-item" onclick="triggerPin()">📌 Закрепить</div>
    <div class="context-menu-item" onclick="triggerReply()">↩️ Ответить</div>
    <div class="context-menu-item" onclick="triggerForward()">↪️ Переслать</div>
    <div class="context-menu-item" id="ctxEdit" onclick="triggerEdit()">✏️ Изменить</div>
    <div class="context-menu-item" onclick="showReactionPicker()">😀 Реакция</div>
    <div class="context-menu-item" id="ctxDelete" onclick="triggerDelete()" style="color:#ef4444;">🗑️ Удалить</div>
</div>
<div id="reactionPicker" class="context-menu" style="width: 240px;">
    <div style="padding: 12px; display: flex; gap: 6px; flex-wrap: wrap; justify-content: center;">
{% for emoji in ['👍','❤️','😂','😮','😢','🔥','🎉','👎'] %}
    <button onclick="addReaction('{{ emoji }}')" style="background: rgba(255,255,255,0.1); border: none; padding: 8px 12px; border-radius: 8px; font-size: 20px; cursor: pointer; transition: all 0.2s;">{{ emoji }}</button>
{% endfor %}
    </div>
</div>
<div id="createGroupModal" class="modal-overlay">
    <div class="modal">
        <h3>Создание группы</h3>
        <form action="/create_group" method="post">
            <div class="profile-field"><label>Название группы:</label><input type="text" name="group_name" required placeholder="Например: Мой Канал" maxlength="30"></div>
            <div class="profile-field"><label>URL Аватарки:</label><input type="text" name="group_avatar" placeholder="https://..."></div>
{% if is_admin %}
            <div class="profile-field"><label><input type="checkbox" name="is_public" checked> 🌐 Публичная группа</label></div>
{% else %}
            <div class="profile-field"><small style="color:#f59e0b;">🔒 Приватная группа (только по приглашению)</small></div>
{% endif %}
            <div style="display:flex; gap:10px; justify-content:center; margin-top:18px;">
                <button type="submit" style="background:linear-gradient(135deg, #22c55e, #16a34a); color:#fff; border:none; padding:10px 18px; border-radius:8px; font-weight:bold; cursor:pointer;">Создать</button>
                <button type="button" onclick="closeModal('createGroupModal')" style="background:#475569; color:#fff; border:none; padding:10px 18px; border-radius:8px; cursor:pointer;">Отмена</button>
            </div>
        </form>
    </div>
</div>
<div id="groupSettingsModal" class="modal-overlay">
    <div class="modal" style="max-width: 520px;">
        <h3>⚙️ Управление группой</h3>
        <div style="text-align: left; margin-bottom: 18px;">
            <div class="profile-field">
                <label>Добавить участника (@ник или email):</label>
                <div style="display:flex; gap:8px;">
                    <input type="text" id="addMemberInput" placeholder="@username">
                    <button onclick="addGroupMember()" style="background:linear-gradient(135deg, #22c55e, #16a34a); color:#fff; border:none; padding:10px; border-radius:8px; cursor:pointer;">+</button>
                </div>
            </div>
            <div style="display:flex; gap:10px; margin-bottom: 18px;">
                <button onclick="toggleGroupPublic()" id="btnTogglePublic" style="flex:1; background:linear-gradient(135deg, #38bdf8, #0284c7); color:#0f172a; border:none; padding:10px; border-radius:8px; cursor:pointer; font-weight:bold;">Публичная/Закрытая</button>
                <button onclick="deleteCurrentGroup()" style="flex:1; background:linear-gradient(135deg, #ef4444, #dc2626); color:#fff; border:none; padding:10px; border-radius:8px; cursor:pointer; font-weight:bold;">🗑️ Удалить</button>
            </div>
            <h5 style="color:#94a3b8; margin: 12px 0;">Участники:</h5>
            <div id="groupMembersList" style="max-height: 220px; overflow-y: auto;"></div>
        </div>
        <button onclick="closeModal('groupSettingsModal')" style="background:#475569; color:#fff; border:none; padding:10px 18px; border-radius:8px; cursor:pointer; width:100%;">Закрыть</button>
    </div>
</div>
<div id="forwardModal" class="modal-overlay">
    <div class="modal">
        <h3>Переслать сообщение в:</h3>
        <div class="modal-chat-list" id="modalChatList"></div>
        <button onclick="closeModal('forwardModal')" style="background:#475569; color:#fff; border:none; padding:10px 18px; border-radius:8px; cursor:pointer;">Отмена</button>
    </div>
</div>
<div id="viewProfileModal" class="modal-overlay">
    <div class="modal">
        <div id="viewProfDecorationBg" style="position: absolute; top: 0; left: 0; right: 0; height: 150px; border-radius: 20px 20px 0 0; opacity: 0.3; pointer-events: none;"></div>
        <div style="position: relative; z-index: 1;">
            <div class="profile-avatar-large-wrap">
                <img id="viewProfAvatar" class="profile-avatar-large" src="">
                <div id="viewProfFrame"></div>
                <div id="viewProfEffect"></div>
            </div>
            <div id="viewProfBadge" style="font-size: 32px; margin-top: 6px;"></div>
            <h3 id="viewProfCustomNick" style="margin: 6px 0 0 0;"></h3>
            <div id="viewProfMainNick" style="color:#38bdf8; font-size:13px; margin-bottom:10px;"></div>
            <div id="viewProfLastSeen" style="font-size:12px; color:#94a3b8; margin-bottom:12px;"></div>
            <div style="background:rgba(11, 17, 32, 0.8); padding:14px; border-radius:10px; text-align:left; font-size:13px; margin-bottom:16px;">
                <p style="margin:5px 0;">📧 <b>Почта:</b> <span id="viewProfEmail">Не указана</span></p>
                <p style="margin:5px 0;">🛡️ <b>Статус:</b> <span id="viewProfStatus">Пользователь</span></p>
                <p style="margin:5px 0;">💰 <b>Бурмалнеты:</b> <span id="viewProfBurmalnets">0</span></p>
                <p style="margin:5px 0;">🎂 <b>Дата рождения:</b> <span id="viewProfBirth">Не указана</span></p>
                <p style="margin:5px 0;">📝 <b>О себе:</b> <span id="viewProfBio">Нет описания</span></p>
            </div>
            <div id="viewProfGallery" style="margin-bottom:16px;"></div>
            <div id="viewProfDecorationsList" style="margin-bottom:16px;"></div>
            <div class="profile-actions" id="viewProfActions"></div>
            <button onclick="closeModal('viewProfileModal')" style="background:linear-gradient(135deg, #38bdf8, #0284c7); color:#0f172a; border:none; padding:10px 22px; border-radius:8px; font-weight:bold; cursor:pointer; margin-top:12px;">Закрыть</button>
        </div>
    </div>
</div>
<div id="createDecorationModal" class="modal-overlay">
    <div class="modal">
        <h3>✨ Создать украшение (Админ)</h3>
        <form action="/admin/create_decoration" method="post" enctype="multipart/form-data">
            <div class="profile-field"><label>Название:</label><input type="text" name="name" required maxlength="30"></div>
            <div class="profile-field"><label>Тип:</label>
                <select name="type">
                    <option value="badge">🏆 Значок</option>
                    <option value="frame">💎 Рамка</option>
                    <option value="effect">🔥 Эффект</option>
                    <option value="background">🌌 Фон</option>
                    <option value="nickname">📝 Стиль ника</option>
                </select>
            </div>
            <div class="profile-field"><label>Эмодзи:</label><input type="text" name="emoji" required maxlength="4" value="✨"></div>
            <div class="profile-field"><label>📸 Картинка (PNG/GIF/WEBP):</label><input type="file" name="image_file" accept="image/png,image/gif,image/webp,image/jpeg"></div>
            <div class="profile-field"><label>Описание:</label><textarea name="description" maxlength="100" rows="2"></textarea></div>
            <div class="profile-field"><label>Цвет (hex):</label><input type="color" name="color" value="#38bdf8"></div>
            <div class="profile-field"><label>Анимация:</label>
                <select name="animation">
                    <option value="none">Без анимации</option>
                    <option value="glow">Свечение</option>
                    <option value="float">Парение</option>
                    <option value="rotate">Вращение</option>
                    <option value="sparkle">Мерцание</option>
                    <option value="pulse">Пульсация</option>
                    <option value="rainbow">Радуга</option>
                    <option value="neon">Неон</option>
                    <option value="electric">Электричество</option>
                </select>
            </div>
            <div class="profile-field"><label>Редкость:</label>
                <select name="rarity">
                    <option value="common">Common</option>
                    <option value="rare">Rare</option>
                    <option value="epic">Epic</option>
                    <option value="legendary">Legendary</option>
                </select>
            </div>
            <div class="profile-field"><label>Цена:</label><input type="number" name="price" min="0" value="15"></div>
            <div style="display:flex; gap:10px; justify-content:center; margin-top:18px;">
                <button type="submit" style="background:linear-gradient(135deg, #22c55e, #16a34a); color:#fff; border:none; padding:10px 18px; border-radius:8px; font-weight:bold; cursor:pointer;">Создать</button>
                <button type="button" onclick="closeModal('createDecorationModal')" style="background:#475569; color:#fff; border:none; padding:10px 18px; border-radius:8px; cursor:pointer;">Отмена</button>
            </div>
        </form>
    </div>
</div>
<div class="toast" id="toast"></div>

<script>
const activeTab = "{{ active_tab }}";
const currentUser = {{ user|tojson|safe }};
const isAdmin = {{ is_admin|tojson|safe }};
const isMaintenance = {{ is_maintenance|tojson|safe }};
let currentChatId = "{{ current_chat_id }}";
let currentChatPartner = "{{ current_chat_partner or '' }}";
let currentChatIsGroup = {{ 'true' if current_chat_is_group else 'false' }};
let canManageCurrGroup = {{ 'true' if can_manage_curr_group else 'false' }};
let userChats = {{ user_chats|tojson|safe }};
let lastMessagesJSON = "";
let lastMessageCount = 0;
let selectedMsg = null;
let replyMsgData = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let chatMuted = {{ 'true' if current_chat_muted else 'false' }};
let workshopStep = {{ workshop_step }};
let workshopPackId = "{{ workshop_pack_id }}";
let workshopPendingStickers = {{ workshop_pending_stickers|tojson|safe }};
let workshopMode = "{{ workshop_mode }}";
let decImageFile = null;

function showToast(text, duration=3000) {
    const t = document.getElementById("toast");
    t.innerText = text;
    t.style.display = "block";
    setTimeout(() => { t.style.display = "none"; }, duration);
}

function playNotificationSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.frequency.value = 800; osc.type = 'sine';
        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
        osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.3);
    } catch(e) {}
}

if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();

function linkify(text) {
    if (!text) return '';
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlRegex, '<a href="$1" target="_blank" onclick="event.stopPropagation()">$1</a>');
}

// === ФУНКЦИИ РЕНДЕРИНГА УКРАШЕНИЙ ===
function renderDecorationBadge(dec, extraClass='') {
    if (!dec) return '';
    const pos = dec.position || 'after_nick';
    const size = dec.size || 'medium';
    const anim = dec.animation || 'none';
    const color = dec.color || '#38bdf8';
    
    let posClass = '';
    if (pos === 'before') posClass = 'position-before';
    else if (pos === 'above') posClass = 'position-above';
    
    if (dec.has_custom_image && dec.image_url) {
        return `<span class="decoration-badge anim-${anim} ${posClass} size-${size} ${extraClass}" style="color: ${color};"><img src="${escapeHtml(dec.image_url)}"></span>`;
    } else {
        return `<span class="decoration-badge anim-${anim} ${posClass} size-${size} ${extraClass}" style="color: ${color};">${escapeHtml(dec.emoji || '✨')}</span>`;
    }
}

function renderDecorationFrame(dec) {
    if (!dec) return '';
    const anim = dec.animation || 'none';
    const color = dec.color || '#38bdf8';
    const bw = dec.border_width || 3;
    
    if (dec.has_custom_image && dec.image_url) {
        return `<img src="${escapeHtml(dec.image_url)}" class="decoration-frame anim-${anim}">`;
    } else {
        return `<div class="decoration-frame anim-${anim}" style="border: ${bw}px solid ${color}; box-shadow: 0 0 10px ${color};"></div>`;
    }
}

function renderDecorationEffect(dec) {
    if (!dec) return '';
    const anim = dec.animation || 'none';
    const color = dec.color || '#38bdf8';
    
    if (dec.has_custom_image && dec.image_url) {
        return `<img src="${escapeHtml(dec.image_url)}" class="decoration-effect anim-${anim}" style="color: ${color};">`;
    } else {
        return `<div class="decoration-effect anim-${anim}" style="background: radial-gradient(circle, ${color}40, transparent); color: ${color};"></div>`;
    }
}

function renderDecorationBackground(dec) {
    if (!dec) return '';
    const anim = dec.animation || 'none';
    const color = dec.color || '#38bdf8';
    
    if (dec.has_custom_image && dec.image_url) {
        return `<div class="decoration-background anim-${anim}"><img src="${escapeHtml(dec.image_url)}"></div>`;
    } else {
        return `<div class="decoration-background anim-${anim}" style="background: linear-gradient(135deg, ${color}60, ${color}20);"></div>`;
    }
}

function renderNickWithDecorations(nick, decorations, subBadge='') {
    if (!decorations) return `${subBadge}${escapeHtml(nick)}`;
    
    const badge = decorations.badge;
    const nickname = decorations.nickname;
    
    let nickHtml = escapeHtml(nick);
    
    // Применяем стиль ника
    if (nickname) {
        const style = nickname.nick_style || '';
        const color = nickname.color || '#38bdf8';
        if (style === 'gold') {
            nickHtml = `<span class="nick-gold anim-gold-gradient">${nickHtml}</span>`;
        } else if (style === 'rainbow') {
            nickHtml = `<span class="nick-rainbow anim-rainbow-text">${nickHtml}</span>`;
        } else if (style === 'fire') {
            nickHtml = `<span class="nick-fire anim-fire-text">${nickHtml}</span>`;
        } else if (style === 'neon') {
            nickHtml = `<span class="nick-neon anim-neon-text" style="color: ${color};">${nickHtml}</span>`;
        }
    }
    
    // Значок перед ником
    let beforeBadge = '';
    if (badge && badge.position === 'before') {
        beforeBadge = renderDecorationBadge(badge);
    }
    
    // Значок после ника
    let afterBadge = '';
    if (badge && (!badge.position || badge.position === 'after_nick')) {
        afterBadge = renderDecorationBadge(badge);
    }
    
    // Значок над ником
    let aboveBadge = '';
    if (badge && badge.position === 'above') {
        aboveBadge = renderDecorationBadge(badge);
    }
    
    return `${subBadge}${beforeBadge}${nickHtml}${afterBadge}`;
}

function renderAvatarWithDecorations(avatarUrl, decorations, avatarClass='msg-avatar', wrapClass='msg-avatar-wrap') {
    const decs = decorations || {};
    const bg = decs.background;
    const frame = decs.frame;
    const effect = decs.effect;
    
    let bgHtml = bg ? renderDecorationBackground(bg) : '';
    let frameHtml = frame ? renderDecorationFrame(frame) : '';
    let effectHtml = effect ? renderDecorationEffect(effect) : '';
    
    let avatarHtml = '';
    if (avatarUrl) {
        avatarHtml = `<img src="${escapeHtml(avatarUrl)}" class="${avatarClass} avatar-img">`;
    } else {
        avatarHtml = `<div class="${avatarClass} avatar-img" style="background:#475569; display:flex; align-items:center; justify-content:center;">👤</div>`;
    }
    
    return `<div class="${wrapClass} avatar-with-decorations">${bgHtml}${effectHtml}${avatarHtml}${frameHtml}</div>`;
}

// === ЗАГРУЗКА КАРТИНКИ ДЛЯ УКРАШЕНИЯ ===
function previewDecImage(input) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];
    decImageFile = file;
    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('imagePreview');
        preview.src = e.target.result;
        preview.style.display = 'block';
        document.getElementById('imageUploadArea').classList.add('has-image');
        document.getElementById('removeImageBtn').style.display = 'inline-block';
        updateDecorationPreview();
    };
    reader.readAsDataURL(file);
}

function removeDecImage() {
    decImageFile = null;
    document.getElementById('decImageFile').value = '';
    document.getElementById('imagePreview').style.display = 'none';
    document.getElementById('imageUploadArea').classList.remove('has-image');
    document.getElementById('removeImageBtn').style.display = 'none';
    updateDecorationPreview();
}

async function toggleVoiceRecord() {
    const btn = document.getElementById("recordVoiceBtn");
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('file', audioBlob, 'voice.webm');
                formData.append('chat_id', currentChatId);
                if (replyMsgData) formData.append('reply_to', JSON.stringify(replyMsgData));
                cancelReply();
                await fetch('/send_voice', { method: 'POST', body: formData });
                fetchMessages();
            };
            mediaRecorder.start(); isRecording = true;
            btn.classList.add("recording"); btn.innerText = "⏹️";
        } catch (err) { alert("Ошибка доступа к микрофону!"); }
    } else {
        mediaRecorder.stop(); isRecording = false;
        btn.classList.remove("recording"); btn.innerText = "🎤";
    }
}

async function uploadLocalFile(input) {
    if (!input.files || !input.files[0]) return;
    const formData = new FormData();
    formData.append('file', input.files[0]);
    try {
        const res = await fetch('/upload_local_file', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.status === 'ok') {
            const msgFormData = new FormData();
            msgFormData.append('chat_id', currentChatId);
            msgFormData.append('local_file', JSON.stringify(data.file));
            if (replyMsgData) msgFormData.append('reply_to', JSON.stringify(replyMsgData));
            cancelReply();
            await fetch('/send_message', { method: 'POST', body: msgFormData });
            fetchMessages();
        } else { alert("Ошибка загрузки"); }
    } catch (err) { alert("Не удалось загрузить файл."); }
    input.value = '';
}

async function createBot() {
    const res = await fetch('/create_bot', { method: 'POST' });
    if (res.ok) window.location.reload();
}

async function startCall() {
    const roomName = "BurmalnodCall_" + currentChatId.replace(/[^a-zA-Z0-9]/g, "");
    const jitsiUrl = `https://meet.jit.si/${roomName}`;
    const formData = new FormData();
    formData.append('chat_id', currentChatId);
    formData.append('call_url', jitsiUrl);
    await fetch('/send_message', { method: 'POST', body: formData });
    window.open(jitsiUrl, '_blank');
    fetchMessages();
}

function switchChat(chatId) { window.location.href = '/?tab=chat&chat_id=' + chatId; }
function closeModal(id) { document.getElementById(id).style.display = "none"; }

async function openGroupSettings() {
    if (!currentChatIsGroup || !canManageCurrGroup) return;
    document.getElementById('groupSettingsModal').style.display = 'flex';
    const res = await fetch('/get_group_info?chat_id=' + currentChatId);
    const ginfo = await res.json();
    document.getElementById('btnTogglePublic').innerText = ginfo.is_public ? '🔒 Сделать закрытой' : '🌐 Сделать публичной';
    const list = document.getElementById('groupMembersList');
    list.innerHTML = '';
    ginfo.members.forEach(m => {
        const row = document.createElement('div');
        row.className = 'group-member-row';
        row.innerHTML = `<span>${m.name} ${m.is_owner ? '👑' : ''}</span><div>${!m.is_owner ? `<button class="btn-sm btn-sm-warn" onclick="kickGroupMember('${m.key}')">Кик</button><button class="btn-sm btn-sm-danger" onclick="blockGroupMember('${m.key}')">Блок</button>` : ''}</div>`;
        list.appendChild(row);
    });
}

async function deleteCurrentGroup() {
    if (!confirm('Удалить группу?')) return;
    const res = await fetch('/delete_group/' + currentChatId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') { showToast('Группа удалена'); closeModal('groupSettingsModal'); window.location.href = '/?tab=chat&chat_id=general'; }
    else alert(data.message || 'Ошибка');
}

async function toggleGroupPublic() {
    const res = await fetch('/toggle_group_public/' + currentChatId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') { showToast(data.is_public ? 'Публичная' : 'Закрытая'); openGroupSettings(); }
}

async function addGroupMember() {
    const input = document.getElementById('addMemberInput');
    const target = input.value.trim();
    if (!target) return;
    const res = await fetch('/add_group_member/' + currentChatId, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({target: target}) });
    const data = await res.json();
    if (data.status === 'ok') { showToast('Добавлен'); input.value = ''; openGroupSettings(); }
    else alert(data.message || 'Ошибка');
}

async function kickGroupMember(memberKey) {
    if (!confirm('Исключить участника?')) return;
    const res = await fetch('/kick_group_member/' + currentChatId + '/' + encodeURIComponent(memberKey), { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') { showToast('Исключен'); openGroupSettings(); }
    else alert(data.message || 'Ошибка');
}

async function blockGroupMember(memberKey) {
    if (!confirm('Заблокировать участника?')) return;
    const res = await fetch('/block_group_member/' + currentChatId + '/' + encodeURIComponent(memberKey), { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') { showToast('Заблокирован'); openGroupSettings(); }
    else alert(data.message || 'Ошибка');
}

async function buyPack(packId) {
    const res = await fetch('/buy_pack/' + packId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') { showToast(data.message || 'Куплено!'); window.location.reload(); }
    else alert(data.message || 'Ошибка');
}

async function createPost() {
    const content = document.getElementById('newPostContent').value.trim();
    if (!content) return;
    const formData = new FormData();
    formData.append('content', content);
    const res = await fetch('/create_post', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.status === 'ok') { window.location.reload(); }
    else alert(data.message || 'Ошибка');
}

async function likePost(postId) {
    const res = await fetch('/like_post/' + postId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') document.getElementById('likes_' + postId).innerText = data.likes;
}

async function addComment(postId) {
    const input = document.getElementById('comment_input_' + postId);
    const text = input.value.trim();
    if (!text) return;
    const formData = new FormData();
    formData.append('comment', text);
    const res = await fetch('/add_comment/' + postId, { method: 'POST', body: formData });
    const data = await res.json();
    if (data.status === 'ok') window.location.reload();
    else alert(data.message || 'Ошибка');
}

async function deletePost(postId) {
    if (!confirm('Удалить пост?')) return;
    const res = await fetch('/delete_post/' + postId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') window.location.reload();
}

function toggleComments(postId) {
    const el = document.getElementById('comments_' + postId);
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function claimTaskReward(taskId) {
    const res = await fetch('/claim_task', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({task_id: taskId})
    });
    const data = await res.json();
    if (data.status === 'ok') {
        showToast(`💰 +${data.reward} бурмалкоинов!`);
        window.location.reload();
    } else {
        alert(data.message || 'Ошибка');
    }
}

async function buySubscription() {
    if (!confirm('Купить подписку Бурмал PRO за 12 бурмалкоинов на 2 дня?')) return;
    const res = await fetch('/buy_subscription', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
        showToast(`⭐ ${data.message} (до ${data.until})`);
        window.location.reload();
    } else {
        alert(data.message || 'Ошибка');
    }
}

async function cancelSubscription() {
    if (!confirm('Отказаться от подписки Бурмал PRO?')) return;
    const res = await fetch('/cancel_subscription', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
        showToast('❌ Подписка отменена');
        window.location.reload();
    } else {
        alert(data.message || 'Ошибка');
    }
}

async function buyDecoration(decId) {
    if (!confirm('Купить это украшение?')) return;
    const res = await fetch('/buy_decoration/' + decId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
        showToast(`✨ ${data.message}`);
        window.location.reload();
    } else {
        alert(data.message || 'Ошибка');
    }
}

async function buyDecorationAndEquip(decId) {
    if (!confirm('Купить и сразу надеть это украшение? Оно будет видно ВЕЗДЕ!')) return;
    const res = await fetch('/buy_decoration_and_equip/' + decId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
        showToast(`✨ ${data.message}`);
        window.location.reload();
    } else {
        alert(data.message || 'Ошибка');
    }
}

async function equipDecoration(decId) {
    const res = await fetch('/equip_decoration/' + decId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
        showToast(`✨ ${data.message}`);
        window.location.reload();
    } else {
        alert(data.message || 'Ошибка');
    }
}

async function unequipDecoration(decId) {
    const res = await fetch('/unequip_decoration/' + decId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') {
        showToast('Украшение снято');
        window.location.reload();
    } else {
        alert(data.message || 'Ошибка');
    }
}

function filterDecorations(filter) {
    const cards = document.querySelectorAll('.decoration-card');
    cards.forEach(card => {
        const type = card.dataset.type;
        const owned = card.dataset.owned === 'true';
        let show = true;
        if (filter === 'owned' && !owned) show = false;
        else if (filter !== 'all' && filter !== 'owned' && type !== filter) show = false;
        card.style.display = show ? 'block' : 'none';
    });
    document.querySelectorAll('.shop-container .tab-btn').forEach(b => b.classList.remove('active'));
    if (event && event.target) event.target.classList.add('active');
}

function selectWorkshopMode(mode) {
    window.location.href = '/?tab=workshop&mode=' + mode;
}

function goToWorkshopStep(step) {
    if (step === 3 && workshopPendingStickers.length === 0) {
        alert('Сначала загрузите хотя бы один стикер!');
        return;
    }
    window.location.href = '/?tab=workshop&mode=sticker&step=' + step + (workshopPackId ? '&pack_id=' + workshopPackId : '');
}

function selectWorkshopPack(packId) {
    window.location.href = '/?tab=workshop&mode=sticker&step=2&pack_id=' + packId;
}

async function createNewWorkshopPack() {
    const name = document.getElementById('newPackName').value.trim();
    const desc = document.getElementById('newPackDesc').value.trim();
    const price = parseInt(document.getElementById('newPackPrice').value) || 0;
    if (!name) { alert('Введите название пака'); return; }
    const res = await fetch('/workshop/create_pack', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name, description: desc, price: price})
    });
    const data = await res.json();
    if (data.status === 'ok') {
        showToast('✅ Пак создан!');
        window.location.href = '/?tab=workshop&mode=sticker&step=2&pack_id=' + data.pack_id;
    } else {
        alert(data.message || 'Ошибка');
    }
}

async function handleWorkshopUpload(input) {
    if (!input.files || input.files.length === 0) return;
    const files = Array.from(input.files);
    const progressDiv = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    progressDiv.style.display = 'block';
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('pack_id', workshopPackId);
        progressText.innerText = `Загрузка ${i + 1} из ${files.length}: ${file.name}`;
        progressBar.style.width = ((i / files.length) * 100) + '%';
        try {
            const res = await fetch('/workshop/upload_sticker', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.status === 'ok') {
                workshopPendingStickers.push(data.sticker);
                const grid = document.getElementById('previewGrid');
                const item = document.createElement('div');
                item.className = 'workshop-preview-item';
                item.id = 'preview_' + data.sticker.id;
                item.innerHTML = `<img src="/static/stickers/pending/${data.sticker.filename}" alt="стикер"><button class="remove-btn" onclick="removePendingSticker('${data.sticker.id}')">✖</button>`;
                grid.appendChild(item);
            } else {
                alert(`Ошибка загрузки ${file.name}: ${data.message}`);
            }
        } catch (err) {
            alert(`Не удалось загрузить ${file.name}`);
        }
    }
    progressBar.style.width = '100%';
    progressText.innerText = '✅ Загрузка завершена!';
    setTimeout(() => { progressDiv.style.display = 'none'; }, 2000);
    input.value = '';
}

async function removePendingSticker(stickerId) {
    if (!confirm('Удалить этот стикер?')) return;
    const res = await fetch('/workshop/remove_pending_sticker', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({sticker_id: stickerId, pack_id: workshopPackId})
    });
    const data = await res.json();
    if (data.status === 'ok') {
        const el = document.getElementById('preview_' + stickerId);
        if (el) el.remove();
        workshopPendingStickers = workshopPendingStickers.filter(s => s.id !== stickerId);
        showToast('Стикер удалён');
    } else {
        alert(data.message || 'Ошибка');
    }
}

async function submitWorkshopForModeration() {
    if (!confirm('Отправить пак на модерацию? После этого изменения будут заблокированы до проверки.')) return;
    const name = document.getElementById('editPackName').value.trim();
    const desc = document.getElementById('editPackDesc').value.trim();
    const price = parseInt(document.getElementById('editPackPrice').value) || 0;
    const forSale = document.getElementById('editPackForSale').checked;
    
    await fetch('/workshop/update_pack_settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pack_id: workshopPackId, name: name, description: desc, price: price, for_sale: forSale})
    });
    
    const res = await fetch('/workshop/submit_for_moderation', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pack_id: workshopPackId})
    });
    const data = await res.json();
    if (data.status === 'ok') {
        showToast('🚀 Пак отправлен на модерацию!');
        setTimeout(() => { window.location.href = '/?tab=workshop&mode=sticker&step=1'; }, 1500);
    } else {
        alert(data.message || 'Ошибка');
    }
}

// === ПРЕДПРОСМОТР УКРАШЕНИЯ В РЕДАКТОРЕ ===
function updateDecorationPreview() {
    const preview = document.getElementById('decorationPreview');
    const previewInChat = document.getElementById('previewInChat');
    if (!preview) return;
    
    const type = document.getElementById('decType').value;
    const emoji = document.getElementById('decEmoji').value || '✨';
    const color = document.getElementById('decColor').value;
    const animation = document.getElementById('decAnimation').value;
    const intensity = parseFloat(document.getElementById('decIntensity').value) || 0.5;
    const position = document.getElementById('decPosition') ? document.getElementById('decPosition').value : 'after_nick';
    const size = document.getElementById('decSize') ? document.getElementById('decSize').value : 'medium';
    
    // Показать/скрыть поля
    document.getElementById('positionField').style.display = (type === 'badge') ? 'block' : 'none';
    document.getElementById('sizeField').style.display = (type === 'badge') ? 'block' : 'none';
    
    let avatarHtml = '<div class="preview-avatar" id="previewAvatar"></div>';
    let nickHtml = '<span class="preview-nick" id="previewNick">ВашНик</span>';
    
    // Применяем стиль ника
    if (type === 'nickname') {
        const nickStyle = `color: ${color}; animation: dec-${animation} 2s infinite;`;
        nickHtml = `<span class="preview-nick" style="${nickStyle}">ВашНик</span>`;
    }
    
    // Добавляем украшения
    let beforeBadge = '';
    let afterBadge = '';
    let aboveBadge = '';
    let frameHtml = '';
    let effectHtml = '';
    let bgHtml = '';
    
    // Если есть загруженная картинка
    const previewImg = document.getElementById('imagePreview');
    const hasImg = previewImg && previewImg.src && previewImg.style.display !== 'none';
    const imgSrc = hasImg ? previewImg.src : '';
    
    if (type === 'badge') {
        let badgeHtml = '';
        if (hasImg) {
            badgeHtml = `<span class="decoration-badge anim-${animation} size-${size}" style="color: ${color};"><img src="${imgSrc}"></span>`;
        } else {
            badgeHtml = `<span class="decoration-badge anim-${animation} size-${size}" style="color: ${color};">${emoji}</span>`;
        }
        
        if (position === 'before') beforeBadge = badgeHtml;
        else if (position === 'above') aboveBadge = badgeHtml;
        else afterBadge = badgeHtml;
    } else if (type === 'frame') {
        if (hasImg) {
            frameHtml = `<img src="${imgSrc}" class="decoration-frame anim-${animation}" style="position:absolute; top:-10px; left:-10px; right:-10px; bottom:-10px;">`;
        } else {
            frameHtml = `<div class="decoration-frame anim-${animation}" style="border: 3px solid ${color}; box-shadow: 0 0 15px ${color};"></div>`;
        }
    } else if (type === 'effect') {
        if (hasImg) {
            effectHtml = `<img src="${imgSrc}" class="decoration-effect anim-${animation}" style="position:absolute; top:-15px; left:-15px; right:-15px; bottom:-15px; color: ${color};">`;
        } else {
            effectHtml = `<div class="decoration-effect anim-${animation}" style="background: radial-gradient(circle, ${color}60, transparent); color: ${color};"></div>`;
        }
    } else if (type === 'background') {
        if (hasImg) {
            bgHtml = `<div class="decoration-background anim-${animation}" style="background-image: url(${imgSrc}); background-size: cover; opacity: 0.4; position:absolute; top:0; left:0; right:0; bottom:0; border-radius:12px;"></div>`;
        } else {
            bgHtml = `<div class="decoration-background anim-${animation}" style="background: linear-gradient(135deg, ${color}80, ${color}30); position:absolute; top:0; left:0; right:0; bottom:0; border-radius:12px;"></div>`;
        }
    }
    
    preview.innerHTML = `
        <div style="position: relative; display: inline-flex; align-items: center; gap: 12px;">
            ${bgHtml}
            <div class="avatar-with-decorations" style="position: relative; width: 80px; height: 80px;">
                ${effectHtml}
                <div class="preview-avatar" style="width:80px; height:80px; border-radius:50%; background:linear-gradient(135deg, #38bdf8, #0284c7); position:relative; z-index:2;"></div>
                ${frameHtml}
            </div>
            <div style="position:relative;">
                ${aboveBadge}
                <div style="display:inline-flex; align-items:center; gap:4px;">
                    ${beforeBadge}
                    ${nickHtml}
                    ${afterBadge}
                </div>
            </div>
        </div>
    `;
    
    // Предпросмотр в чате
    if (type === 'nickname') {
        previewInChat.innerHTML = `<span style="color: ${color}; animation: dec-${animation} 2s infinite;">ВашНик</span>`;
    } else if (type === 'badge') {
        let badgePreview = hasImg ? `<img src="${imgSrc}" style="width:16px; height:16px; vertical-align:middle;">` : emoji;
        if (position === 'before') {
            previewInChat.innerHTML = `<span style="color:${color}; animation: dec-${animation} 2s infinite;">${badgePreview}</span> <span style="color:#38bdf8;">ВашНик</span>`;
        } else {
            previewInChat.innerHTML = `<span style="color:#38bdf8;">ВашНик</span> <span style="color:${color}; animation: dec-${animation} 2s infinite;">${badgePreview}</span>`;
        }
    } else {
        previewInChat.innerHTML = `<span style="color:#38bdf8;">ВашНик</span>`;
    }
}

async function createCustomDecoration() {
    const name = document.getElementById('decName').value.trim();
    const type = document.getElementById('decType').value;
    const emoji = document.getElementById('decEmoji').value.trim();
    const description = document.getElementById('decDescription').value.trim();
    const color = document.getElementById('decColor').value;
    const animation = document.getElementById('decAnimation').value;
    const rarity = document.getElementById('decRarity').value;
    const price = parseInt(document.getElementById('decPrice').value) || 0;
    const intensity = parseFloat(document.getElementById('decIntensity').value) || 0.5;
    const position = document.getElementById('decPosition') ? document.getElementById('decPosition').value : 'after_nick';
    const size = document.getElementById('decSize') ? document.getElementById('decSize').value : 'medium';
    
    if (!name) { alert('Введите название украшения'); return; }
    if (!emoji && !decImageFile) { alert('Введите эмодзи или загрузите картинку'); return; }
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('type', type);
    formData.append('emoji', emoji);
    formData.append('description', description);
    formData.append('color', color);
    formData.append('animation', animation);
    formData.append('rarity', rarity);
    formData.append('price', price);
    formData.append('effect_intensity', intensity);
    formData.append('position', position);
    formData.append('size', size);
    if (decImageFile) formData.append('image_file', decImageFile);
    
    const res = await fetch('/workshop/create_decoration', {
        method: 'POST',
        body: formData
    });
    const data = await res.json();
    if (data.status === 'ok') {
        showToast('✨ Украшение создано и добавлено в вашу коллекцию!');
        setTimeout(() => { window.location.href = '/?tab=decorations'; }, 1500);
    } else {
        alert(data.message || 'Ошибка');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (activeTab === 'workshop' && workshopMode === 'decoration') {
        updateDecorationPreview();
    }
    const zone = document.getElementById('uploadZone');
    if (zone) {
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            const input = document.getElementById('workshopFileInput');
            input.files = e.dataTransfer.files;
            handleWorkshopUpload(input);
        });
    }
});

async function showUserProfile(userKey) {
    if (!userKey) return;
    const res = await fetch('/get_user_profile?user_key=' + encodeURIComponent(userKey));
    const prof = await res.json();
    document.getElementById("viewProfAvatar").src = prof.picture || 'https://via.placeholder.com/120';
    document.getElementById("viewProfCustomNick").innerText = prof.custom_nick || prof.nickname || 'Аноним';
    document.getElementById("viewProfMainNick").innerText = prof.main_nick || ('@' + userKey.split('@')[0]);
    document.getElementById("viewProfLastSeen").innerText = "🕒 " + (prof.last_seen || "Не в сети");
    document.getElementById("viewProfEmail").innerText = prof.email || 'Не указана';
    const statusEl = document.getElementById("viewProfStatus");
    statusEl.innerText = prof.is_admin ? '🟡 Администратор' : '🟢 Пользователь';
    statusEl.style.color = prof.is_admin ? '#f59e0b' : '#22c55e';
    document.getElementById("viewProfBurmalnets").innerText = prof.burmalnets;
    let birthText = "Не указана";
    if (prof.birth_day && prof.birth_month && prof.birth_year) {
        const months = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
        birthText = `${prof.birth_day} ${months[prof.birth_month-1]} ${prof.birth_year}`;
    }
    document.getElementById("viewProfBirth").innerText = birthText;
    document.getElementById("viewProfBio").innerText = prof.bio || 'Нет описания';
    
    // === УКРАШЕНИЯ В ПРОФИЛЕ ===
    const decorations = prof.decorations || {};
    const frameEl = document.getElementById('viewProfFrame');
    const effectEl = document.getElementById('viewProfEffect');
    const badgeEl = document.getElementById('viewProfBadge');
    const bgEl = document.getElementById('viewProfDecorationBg');
    const decListEl = document.getElementById('viewProfDecorationsList');
    const nickEl = document.getElementById('viewProfCustomNick');
    
    // Фон
    if (decorations.background) {
        const bg = decorations.background;
        if (bg.has_custom_image && bg.image_url) {
            bgEl.style.backgroundImage = `url(${bg.image_url})`;
            bgEl.style.backgroundSize = 'cover';
        } else {
            bgEl.style.background = `linear-gradient(135deg, ${bg.color}40, ${bg.color}20)`;
        }
        bgEl.style.display = 'block';
    } else {
        bgEl.style.display = 'none';
    }
    
    // Рамка
    if (decorations.frame) {
        const frame = decorations.frame;
        frameEl.className = `decoration-frame anim-${frame.animation || 'none'}`;
        if (frame.has_custom_image && frame.image_url) {
            frameEl.innerHTML = `<img src="${frame.image_url}">`;
            frameEl.style.border = 'none';
            frameEl.style.boxShadow = 'none';
        } else {
            frameEl.innerHTML = '';
            frameEl.style.border = `${frame.border_width || 3}px solid ${frame.color}`;
            frameEl.style.boxShadow = `0 0 20px ${frame.color}`;
        }
    } else {
        frameEl.className = '';
        frameEl.innerHTML = '';
        frameEl.style.border = 'none';
    }
    
    // Эффект
    if (decorations.effect) {
        const effect = decorations.effect;
        effectEl.className = `decoration-effect anim-${effect.animation || 'none'}`;
        if (effect.has_custom_image && effect.image_url) {
            effectEl.innerHTML = `<img src="${effect.image_url}" style="color: ${effect.color};">`;
        } else {
            effectEl.innerHTML = '';
            effectEl.style.background = `radial-gradient(circle, ${effect.color}40, transparent)`;
            effectEl.style.color = effect.color;
        }
    } else {
        effectEl.className = '';
        effectEl.innerHTML = '';
    }
    
    // Значок
    if (decorations.badge) {
        const badge = decorations.badge;
        if (badge.has_custom_image && badge.image_url) {
            badgeEl.innerHTML = `<img src="${badge.image_url}" style="width:32px; height:32px; object-fit:contain;">`;
        } else {
            badgeEl.innerText = badge.emoji;
        }
        badgeEl.style.display = 'block';
        badgeEl.className = `decoration-badge anim-${badge.animation || 'none'} size-large`;
        badgeEl.style.color = badge.color;
    } else {
        badgeEl.innerText = '';
    }
    
    // Стиль ника
    if (decorations.nickname) {
        const nick = decorations.nickname;
        const style = nick.nick_style || '';
        const color = nick.color || '#38bdf8';
        let nickText = nickEl.innerText;
        if (style === 'gold') {
            nickEl.className = 'nick-gold anim-gold-gradient';
        } else if (style === 'rainbow') {
            nickEl.className = 'nick-rainbow anim-rainbow-text';
        } else if (style === 'fire') {
            nickEl.className = 'nick-fire anim-fire-text';
        } else if (style === 'neon') {
            nickEl.className = 'nick-neon anim-neon-text';
            nickEl.style.color = color;
        }
    }
    
    // Список всех украшений
    if (decorations.all && decorations.all.length > 0) {
        let html = '<div style="text-align:left; font-size:12px; color:#94a3b8; margin-bottom:8px;">✨ Украшения:</div><div style="display:flex; gap:8px; flex-wrap:wrap;">';
        decorations.all.forEach(dec => {
            if (dec.has_custom_image && dec.image_url) {
                html += `<div style="background:rgba(0,0,0,0.3); padding:6px 10px; border-radius:8px; display:inline-flex; align-items:center; gap:6px; font-size:12px;"><img src="${dec.image_url}" style="width:20px; height:20px; object-fit:contain;">${dec.name}</div>`;
            } else {
                html += `<div style="background:rgba(0,0,0,0.3); padding:6px 10px; border-radius:8px; display:inline-flex; align-items:center; gap:6px; font-size:12px;">${dec.emoji} ${dec.name}</div>`;
            }
        });
        html += '</div>';
        decListEl.innerHTML = html;
    } else {
        decListEl.innerHTML = '';
    }
    
    const galleryDiv = document.getElementById("viewProfGallery");
    if (prof.gallery && prof.gallery.length > 0) {
        let html = '<div style="text-align:left; font-size:12px; color:#94a3b8; margin-bottom:8px;">🖼️ Фото:</div><div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:10px;">';
        prof.gallery.forEach(url => { html += `<div style="aspect-ratio:1; background:#1e293b; border-radius:10px; overflow:hidden;"><img src="${url}" style="width:100%; height:100%; object-fit:cover;"></div>`; });
        html += '</div>';
        galleryDiv.innerHTML = html; galleryDiv.style.display = 'block';
    } else { galleryDiv.innerHTML = ''; galleryDiv.style.display = 'none'; }
    
    const actionsDiv = document.getElementById("viewProfActions");
    const myKey = currentUser ? (currentUser.email || currentUser.nickname).toLowerCase() : '';
    let actionsHtml = '';
    if (currentUser && userKey.toLowerCase() !== myKey) {
        actionsHtml += `<button class="btn-msg" onclick="startPrivateChat('${userKey}', '${prof.custom_nick || prof.nickname}')">💬 Написать</button>`;
        if (prof.is_blacklisted) actionsHtml += `<button class="btn-block unblock" onclick="toggleBlacklist('${userKey}', false)">✅ Убрать из ЧС</button>`;
        else actionsHtml += `<button class="btn-block" onclick="toggleBlacklist('${userKey}', true)">🚫 В ЧС</button>`;
    }
    actionsDiv.innerHTML = actionsHtml;
    document.getElementById("viewProfileModal").style.display = "flex";
}

async function toggleBlacklist(targetKey, block) {
    const res = await fetch('/toggle_blacklist', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({target_key: targetKey, block: block}) });
    const data = await res.json();
    if (data.status === 'ok') { showToast(block ? "В ЧС" : "Убран из ЧС"); closeModal('viewProfileModal'); fetchMessages(); }
    else alert(data.message || "Ошибка");
}

async function searchUsers(query) {
    query = query.trim().toLowerCase();
    const resBox = document.getElementById("searchResults");
    if (!query) { resBox.style.display = "none"; return; }
    const res = await fetch('/search_users?q=' + encodeURIComponent(query));
    const users = await res.json();
    if (users.length === 0) resBox.innerHTML = '<div class="search-item" style="color:#64748b;">Никого не найдено</div>';
    else {
        let html = '';
        users.forEach(u => {
            const decs = u.decorations || {};
            let avatarHtml = '';
            if (u.avatar) {
                avatarHtml = `<img src="${u.avatar}" style="width:28px; height:28px; border-radius:50%; object-fit:cover;">`;
            } else {
                avatarHtml = `<div style="width:28px; height:28px; border-radius:50%; background:#334155; display:flex; align-items:center; justify-content:center; font-size:11px;">👤</div>`;
            }
            
            let frameHtml = '';
            if (decs.frame) {
                if (decs.frame.has_custom_image && decs.frame.image_url) {
                    frameHtml = `<img src="${decs.frame.image_url}" class="decoration-frame anim-${decs.frame.animation}" style="top:-3px; left:-3px; right:-3px; bottom:-3px;">`;
                } else {
                    frameHtml = `<div class="decoration-frame anim-${decs.frame.animation}" style="border: 2px solid ${decs.frame.color}; box-shadow: 0 0 6px ${decs.frame.color}; top:-3px; left:-3px; right:-3px; bottom:-3px;"></div>`;
                }
            }
            
            let badgeHtml = '';
            if (decs.badge) {
                if (decs.badge.has_custom_image && decs.badge.image_url) {
                    badgeHtml = `<span class="decoration-badge anim-${decs.badge.animation} size-small" style="color: ${decs.badge.color};"><img src="${decs.badge.image_url}"></span>`;
                } else {
                    badgeHtml = `<span class="decoration-badge anim-${decs.badge.animation} size-small" style="color: ${decs.badge.color};">${decs.badge.emoji}</span>`;
                }
            }
            
            html += `<div class="search-item" onclick="startPrivateChat('${u.id}', '${u.name}')">
                <div class="search-avatar-wrap avatar-with-decorations">
                    ${avatarHtml}
                    ${frameHtml}
                </div>
                <span><b>${u.main_nick}</b> ${badgeHtml} (${u.name})</span>
            </div>`;
        });
        resBox.innerHTML = html;
    }
    resBox.style.display = "block";
}

async function startPrivateChat(targetId, targetName) {
    document.getElementById("searchResults").style.display = "none";
    const res = await fetch('/open_private_chat', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({target_id: targetId, target_name: targetName}) });
    const data = await res.json();
    if (data.status === 'ok') window.location.href = '/?tab=chat&chat_id=' + data.chat_id;
    else alert(data.message || "Ошибка");
}

function toggleStickers() {
    var picker = document.getElementById("stickersPicker");
    if(picker) picker.style.display = (picker.style.display === "block") ? "none" : "block";
}

function switchStickerPack(packId, btn) {
    document.querySelectorAll('.sticker-grid').forEach(g => g.style.display = 'none');
    document.getElementById(packId).style.display = 'grid';
    document.querySelectorAll(".sticker-tab-btn").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function openContextMenu(e, msg) {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    selectedMsg = msg;
    const menu = document.getElementById("contextMenu");
    const isOwn = currentUser && ((currentUser.email && msg.email && currentUser.email.toLowerCase() === msg.email.toLowerCase()) || (currentUser.nickname && msg.user && currentUser.nickname === msg.user));
    const isPrivateChat = currentChatId.startsWith('private_');
    document.getElementById("ctxEdit").style.display = (isOwn || isAdmin) && msg.text ? "flex" : "none";
    document.getElementById("ctxDelete").style.display = (isOwn || isAdmin || isPrivateChat) ? "flex" : "none";
    document.getElementById("reactionPicker").style.display = "none";
    let x = e ? (e.touches ? e.touches[0].clientX : e.clientX) : window.innerWidth / 2 - 80;
    let y = e ? (e.touches ? e.touches[0].clientY : e.clientY) : window.innerHeight / 2 - 50;
    menu.style.left = Math.min(x, window.innerWidth - 200) + "px";
    menu.style.top = Math.min(y, window.innerHeight - 200) + "px";
    menu.style.display = "block";
}

function showReactionPicker() {
    if (!selectedMsg) return;
    document.getElementById("contextMenu").style.display = "none";
    const picker = document.getElementById("reactionPicker");
    picker.style.left = document.getElementById("contextMenu").style.left;
    picker.style.top = document.getElementById("contextMenu").style.top;
    picker.style.display = "block";
}

async function addReaction(emoji) {
    if (!selectedMsg) return;
    document.getElementById("reactionPicker").style.display = "none";
    const res = await fetch('/add_reaction', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({msg_id: selectedMsg.id, emoji: emoji})
    });
    const data = await res.json();
    if (data.status === 'ok') fetchMessages();
}

document.addEventListener("click", (e) => {
    const menu = document.getElementById("contextMenu");
    const picker = document.getElementById("reactionPicker");
    if (menu && !menu.contains(e.target)) menu.style.display = "none";
    if (picker && !picker.contains(e.target)) picker.style.display = "none";
});

async function triggerPin() {
    if (!selectedMsg) return;
    const textSnippet = selectedMsg.text || (selectedMsg.voice ? '🎤' : (selectedMsg.local_file ? '📎' : 'Стикер'));
    await fetch('/pin_message', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({chat_id: currentChatId, user: selectedMsg.custom_nick || selectedMsg.user, text: textSnippet}) });
    checkPinnedMessage();
}

async function unpinMessage() {
    await fetch('/pin_message', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({chat_id: currentChatId, unpin: true}) });
    checkPinnedMessage();
}

async function checkPinnedMessage() {
    const res = await fetch('/get_pinned?chat_id=' + currentChatId);
    const data = await res.json();
    const bar = document.getElementById("pinnedBar");
    if (data && data.text) {
        document.getElementById("pinnedUser").innerText = data.user;
        document.getElementById("pinnedText").innerText = data.text.substring(0, 30);
        bar.style.display = "flex";
    } else bar.style.display = "none";
}

function triggerReply() {
    if (!selectedMsg) return;
    replyMsgData = { id: selectedMsg.id, user: selectedMsg.custom_nick || selectedMsg.user, text: selectedMsg.text || (selectedMsg.voice ? '🎤' : (selectedMsg.local_file ? '📎' : 'Стикер')) };
    document.getElementById("replyTextSnippet").innerText = `Ответ на ${replyMsgData.user}: "${replyMsgData.text.substring(0,25)}..."`;
    document.getElementById("replyBar").style.display = "flex";
}

function cancelReply() { replyMsgData = null; document.getElementById("replyBar").style.display = "none"; }

function triggerForward() {
    if (!selectedMsg) return;
    const listContainer = document.getElementById("modalChatList");
    listContainer.innerHTML = '';
    userChats.forEach(c => {
        const btn = document.createElement("button");
        btn.className = "chat-item"; btn.innerText = c.name; btn.onclick = () => executeForward(c.id);
        listContainer.appendChild(btn);
    });
    document.getElementById("forwardModal").style.display = "flex";
}

async function executeForward(targetChatId) {
    closeModal('forwardModal');
    if (!selectedMsg) return;
    const formData = new FormData();
    formData.append('chat_id', targetChatId);
    formData.append('message', selectedMsg.text || '');
    formData.append('sticker_url', selectedMsg.sticker || '');
    formData.append('voice_url', selectedMsg.voice || '');
    if (selectedMsg.local_file) formData.append('local_file', JSON.stringify(selectedMsg.local_file));
    formData.append('forwarded_from', selectedMsg.custom_nick || selectedMsg.user);
    await fetch('/send_message', { method: 'POST', body: formData });
    if (targetChatId === currentChatId) fetchMessages();
}

async function triggerEdit() {
    if (!selectedMsg) return;
    const newText = prompt("Редактировать:", selectedMsg.text);
    if (newText !== null && newText.trim() !== "") {
        const formData = new FormData();
        formData.append('msg_id', selectedMsg.id); formData.append('new_text', newText.trim());
        await fetch('/edit_message', { method: 'POST', body: formData });
        fetchMessages();
    }
}

async function triggerDelete() {
    if (!selectedMsg || !confirm('Удалить сообщение?')) return;
    const formData = new FormData();
    formData.append('msg_id', selectedMsg.id);
    formData.append('chat_id', currentChatId);
    await fetch('/delete_message', { method: 'POST', body: formData });
    fetchMessages();
}

async function fetchMessages() {
    if (activeTab !== 'chat' || (isMaintenance && !isAdmin)) return;
    try {
        const res = await fetch('/get_messages?chat_id=' + currentChatId);
        if(!res.ok) return;
        const messages = await res.json();
        const stringified = JSON.stringify(messages);
        if (stringified !== lastMessagesJSON) {
            if (lastMessagesJSON !== "" && messages.length > lastMessageCount && !chatMuted) {
                const newMsgs = messages.slice(lastMessageCount);
                const hasExternal = newMsgs.some(m => {
                    const isOwn = currentUser && ((currentUser.email && m.email && currentUser.email.toLowerCase() === m.email.toLowerCase()) || (currentUser.nickname && m.user && currentUser.nickname === m.user));
                    return !isOwn;
                });
                if (hasExternal) {
                    playNotificationSound();
                    if ("Notification" in window && Notification.permission === "granted") {
                        const last = newMsgs[newMsgs.length - 1];
                        const txt = last.text || (last.sticker ? '🖼️' : (last.voice ? '🎤' : '📎'));
                        new Notification(`${last.custom_nick || last.user}`, { body: txt.substring(0, 80), icon: last.picture || '' });
                    }
                }
            }
            lastMessagesJSON = stringified;
            lastMessageCount = messages.length;
            renderMessages(messages);
        }
    } catch (err) { console.error("Ошибка загрузки: ", err); }
}

function renderMessages(messages) {
    const chatBox = document.getElementById("chatBox");
    if (!chatBox) return;
    const isScrolledToBottom = chatBox.scrollHeight - chatBox.clientHeight <= chatBox.scrollTop + 60;
    if (messages.length === 0) { chatBox.innerHTML = '<p style="color: #64748b; text-align: center;">Сообщений пока нет.</p>'; return; }
    let html = '';
    messages.forEach(msg => {
        const isOwn = currentUser && ((currentUser.email && msg.email && currentUser.email.toLowerCase() === msg.email.toLowerCase()) || (currentUser.nickname && msg.user && currentUser.nickname === msg.user));
        const wrapperClass = isOwn ? 'own' : 'other';
        const userKey = (msg.email || msg.user).toLowerCase();
        const decorations = msg.decorations || {};
        
        // Аватарка с украшениями
        const avatarHtml = renderAvatarWithDecorations(msg.picture, decorations, 'msg-avatar', 'msg-avatar-wrap');
        const clickHandler = `onclick="showUserProfile('${escapeHtml(userKey)}')"`;
        
        const statusDot = msg.is_online ? '<span class="status-dot online"></span>' : '<span class="status-dot offline"></span>';
        let replyQuoteHtml = msg.reply_to ? `<div class="reply-quote"><b>${escapeHtml(msg.reply_to.user)}:</b> ${escapeHtml(msg.reply_to.text)}</div>` : '';
        let forwardHtml = msg.forwarded_from ? `<div class="forwarded-tag">↪️ От ${escapeHtml(msg.forwarded_from)}</div>` : '';
        let textHtml = msg.text ? `<div class="msg-text">${linkify(escapeHtml(msg.text))}</div>` : '';
        let stickerHtml = msg.sticker ? `<img src="${escapeHtml(msg.sticker)}" class="sticker-img" alt="стикер">` : '';
        let voiceHtml = msg.voice ? `<audio controls src="${escapeHtml(msg.voice)}"></audio>` : '';
        let fileHtml = msg.local_file ? `<div class="file-card"><div class="file-card-info">📄 <b>${escapeHtml(msg.local_file.name)}</b> (${escapeHtml(msg.local_file.size)})</div><a href="${escapeHtml(msg.local_file.url)}" class="btn-file-dl" onclick="event.stopPropagation()">Скачать</a></div>` : '';
        let callHtml = msg.call_url ? `<div class="call-card"><b>📞 Видеозвонок</b><br><a href="${escapeHtml(msg.call_url)}" target="_blank" class="btn-join-call" onclick="event.stopPropagation()">Войти</a></div>` : '';
        let reactionsHtml = '';
        if (msg.reactions && Object.keys(msg.reactions).length > 0) {
            reactionsHtml = '<div class="msg-reactions">';
            for (const [emoji, users] of Object.entries(msg.reactions)) {
                const count = users.length;
                const myKey = currentUser ? (currentUser.email || currentUser.nickname).toLowerCase() : '';
                const isMine = users.includes(myKey);
                reactionsHtml += `<span class="reaction-chip ${isMine ? 'mine' : ''}" onclick="event.stopPropagation(); addReactionDirect('${msg.id}', '${emoji}')">${emoji} ${count}</span>`;
            }
            reactionsHtml += '</div>';
        }
        const jsonStr = escapeHtml(JSON.stringify(msg));
        const displayName = msg.custom_nick || msg.user;
        const subBadge = msg.is_subscribed ? '<span style="color:#f59e0b;">⭐</span>' : '';
        
        // Ник с украшениями
        const nickWithDecs = renderNickWithDecorations(displayName, decorations, subBadge);
        
        // Эффект на сообщении
        let effectStyle = '';
        if (decorations.effect) {
            effectStyle = `box-shadow: 0 0 12px ${decorations.effect.color}40;`;
        }
        
        // Аватарка с кликом
        let avatarWithClick = avatarHtml.replace('<div class="msg-avatar-wrap', `<div ${clickHandler} class="msg-avatar-wrap`).replace('<img src', `<img ${clickHandler} src`).replace('<div class="msg-avatar', `<div ${clickHandler} class="msg-avatar`);
        
        html += `<div class="msg-wrapper ${wrapperClass}">${!isOwn ? avatarWithClick : ''}<div class="msg" style="${effectStyle}" oncontextmenu="openContextMenu(event, ${jsonStr})" onclick="openContextMenu(event, ${jsonStr})">${forwardHtml}${replyQuoteHtml}<div class="msg-header"><span class="nick-wrap">${statusDot}${nickWithDecs}</span><span>${escapeHtml(msg.time)}</span></div>${textHtml}${stickerHtml}${voiceHtml}${fileHtml}${callHtml}${reactionsHtml}</div>${isOwn ? avatarWithClick : ''}</div>`;
    });
    chatBox.innerHTML = html;
    if (isScrolledToBottom || chatBox.dataset.initialScrolled !== "true") { chatBox.scrollTop = chatBox.scrollHeight; chatBox.dataset.initialScrolled = "true"; }
}

async function addReactionDirect(msgId, emoji) {
    const res = await fetch('/add_reaction', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({msg_id: msgId, emoji: emoji})
    });
    const data = await res.json();
    if (data.status === 'ok') fetchMessages();
}

async function sendMessage(e) {
    if(e) e.preventDefault();
    const input = document.getElementById("msgInput");
    const text = input.value.trim();
    if (!text) return;
    const formData = new FormData();
    formData.append('chat_id', currentChatId); formData.append('message', text);
    if (replyMsgData) formData.append('reply_to', JSON.stringify(replyMsgData));
    input.value = ''; cancelReply();
    await fetch('/send_message', { method: 'POST', body: formData });
    fetchMessages();
}

async function sendSticker(url) {
    const formData = new FormData();
    formData.append('chat_id', currentChatId); formData.append('sticker_url', url);
    if (replyMsgData) formData.append('reply_to', JSON.stringify(replyMsgData));
    document.getElementById("stickersPicker").style.display = "none"; cancelReply();
    await fetch('/send_message', { method: 'POST', body: formData });
    fetchMessages();
}

async function toggleMute() {
    if (!currentChatPartner) return;
    const res = await fetch('/toggle_mute', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({target_key: currentChatPartner}) });
    const data = await res.json();
    if (data.status === 'ok') {
        chatMuted = data.muted;
        const btn = document.getElementById("muteBtn");
        if (chatMuted) { btn.classList.add("muted"); btn.innerHTML = "🔇"; }
        else { btn.classList.remove("muted"); btn.innerHTML = "🔔"; }
    }
}

function copyStreamLink() {
    const link = "https://www.youtube.com/watch?v=9PJ3LZLcR20";
    navigator.clipboard.writeText(link).then(() => showToast("✅ Ссылка скопирована!")).catch(() => {
        const input = document.createElement("input"); input.value = link; document.body.appendChild(input); input.select(); document.execCommand("copy"); document.body.removeChild(input); showToast("✅ Ссылка скопирована!");
    });
}

async function updateFMViewers() {
    if (activeTab !== 'burmalda_fm' || !currentUser) return;
    try {
        await fetch('/update_fm_viewer', { method: 'POST' });
        const res = await fetch('/get_fm_viewers');
        const viewers = await res.json();
        const countEl = document.getElementById('fmViewersCount');
        const listEl = document.getElementById('fmViewersList');
        if (countEl) countEl.innerText = Object.keys(viewers).length;
        if (listEl) {
            let html = '';
            for (const [key, info] of Object.entries(viewers)) {
                const decs = info.decorations || {};
                let avatarHtml = '';
                if (info.picture) {
                    avatarHtml = `<img src="${info.picture}" class="fm-viewer-avatar">`;
                } else {
                    avatarHtml = `<div class="fm-viewer-avatar" style="background:#334155; display:flex;align-items:center;justify-content:center;font-size:10px;">👤</div>`;
                }
                
                let frameHtml = '';
                if (decs.frame) {
                    if (decs.frame.has_custom_image && decs.frame.image_url) {
                        frameHtml = `<img src="${decs.frame.image_url}" class="decoration-frame anim-${decs.frame.animation}" style="top:-3px; left:-3px; right:-3px; bottom:-3px;">`;
                    } else {
                        frameHtml = `<div class="decoration-frame anim-${decs.frame.animation}" style="border: 2px solid ${decs.frame.color}; box-shadow: 0 0 6px ${decs.frame.color}; top:-3px; left:-3px; right:-3px; bottom:-3px;"></div>`;
                    }
                }
                
                let nickWithDecs = renderNickWithDecorations(info.name, decs);
                
                html += `<div class="fm-viewer-item">
                    <div class="fm-viewer-avatar-wrap avatar-with-decorations">
                        ${avatarHtml}
                        ${frameHtml}
                    </div>
                    <span class="fm-nick">${nickWithDecs}</span>
                </div>`;
            }
            listEl.innerHTML = html;
        }
    } catch (err) { console.error('FM viewers error:', err); }
}

if (activeTab === 'chat' && (!isMaintenance || isAdmin)) {
    fetchMessages(); checkPinnedMessage(); setInterval(fetchMessages, 3000);
}
if (activeTab === 'burmalda_fm' && currentUser) {
    updateFMViewers();
    setInterval(updateFMViewers, 5000);
    window.addEventListener('beforeunload', () => {
        navigator.sendBeacon('/remove_fm_viewer');
    });
}
</script>
</body>
</html>
'''

# =====================================================================
# 🚀 МАРШРУТЫ (ROUTES)
# =====================================================================
@app.route('/')
def index():
    active_tab = request.args.get('tab', 'chat')
    current_chat_id = request.args.get('chat_id', 'general')
    user = session.get('user', None)
    is_admin = session.get('is_admin', False)
    action_error = session.pop('action_error', None)
    user_key = (user.get('email') or user.get('nickname')).lower() if user else None
    if user_key:
        USER_ACTIVITY[user_key] = datetime.now()
        process_subscription_payment(user_key)
    files, pending_stickers, user_chats = [], [], get_user_chat_list(user)
    user_profile = get_user_profile(user_key) if user_key else {}
    all_groups, all_users, bots = {}, {}, {}
    sticker_packs = get_sticker_packs(user_key)
    user_owned_packs = get_user_owned_packs(user_key) if user_key else []
    user_burmalnets = get_user_burmalnets(user_key) if user_key else 0
    user_burmalnets_display = '∞' if is_admin else str(int(user_burmalnets))
    current_chat_name, current_chat_partner, current_chat_is_group, current_chat_muted, group_members = "💬 Чат", None, False, False, []
    can_manage_curr_group = False
    daily_tasks = []
    completed_tasks_count = 0
    earned_today = 0
    user_subscription_active = False
    user_subscription_until = ''
    if user_key:
        user_subscription_active = is_user_subscribed(user_key)
        if user_subscription_active:
            prof = get_user_profile(user_key)
            try:
                until_dt = datetime.fromisoformat(prof.get('subscription_until'))
                user_subscription_until = until_dt.strftime('%d.%m.%Y %H:%M')
            except Exception:
                user_subscription_until = ''
        if active_tab == 'tasks':
            daily_tasks = get_user_daily_tasks(user_key)
            completed_tasks_count = sum(1 for t in daily_tasks if t['completed'])
            earned_today = sum(t['reward'] for t in daily_tasks if t['completed'])
    subscription_duration_days = SUBSCRIPTION_DURATION_DAYS
    if user and current_chat_id:
        if current_chat_id.startswith('private_'):
            parts = current_chat_id.replace('private_', '').split('_')
            partner_id = parts[0] if parts[1] == user_key else parts[1]
            current_chat_partner = partner_id
            partner_prof = get_user_profile(partner_id)
            current_chat_name = f"💬 {partner_prof.get('custom_nick') or partner_id.split('@')[0]}"
            current_chat_muted = partner_id in user_profile.get('muted', [])
        elif current_chat_id.startswith('group_'):
            groups = load_groups()
            ginfo = groups.get(current_chat_id, {})
            if ginfo:
                current_chat_name = f"👥 {ginfo.get('name')}"
                current_chat_is_group = True
                can_manage_curr_group = can_manage_group(user_key, ginfo)
                profiles = load_profiles()
                members_keys = ginfo.get('members', [])
                if ginfo.get('owner_key') and ginfo.get('owner_key') not in members_keys:
                    members_keys = [ginfo.get('owner_key')] + members_keys
                for mk in members_keys:
                    mp = profiles.get(mk, {})
                    group_members.append({
                        'key': mk,
                        'name': mp.get('custom_nick') or mk.split('@')[0],
                        'avatar': mp.get('picture', ''),
                        'is_owner': mk == ginfo.get('owner_key'),
                        'decorations': get_user_full_decorations(mk)
                    })
        elif current_chat_id.startswith('botchat_'):
            parts = current_chat_id.split('_')
            if len(parts) >= 3:
                bot_id = parts[2]
                bots_all = load_bots()
                bot_info = bots_all.get(bot_id, {})
                current_chat_name = f"🤖 {bot_info.get('name', 'Бот')}"
        elif current_chat_id == 'general':
            current_chat_name = "🌐 Общий чат"
    if active_tab == 'admin_panel' and is_admin:
        all_groups, all_users, bots = load_groups(), load_profiles(), load_bots()
    if active_tab == 'files' and (not IS_MAINTENANCE_MODE or is_admin):
        try:
            drive_service = get_drive_service()
            results = drive_service.files().list(q=f"'{FOLDER_ID}' in parents and trashed=false", fields="files(id, name)").execute()
            for f in results.get('files', []):
                if is_admin or not (f['name'].startswith('hidden_') or f['name'].startswith('.')):
                    files.append(f)
        except Exception as e:
            action_error = f"Ошибка файлов: {e}"
    if is_admin:
        pending_stickers = load_pending_stickers()
    all_packs_for_shop, all_packs_admin = [], []
    profiles = load_profiles()
    for pack_id, pack_info in sticker_packs.items():
        owner_name = 'Система'
        if pack_info.get('owner_key'):
            owner_prof = profiles.get(pack_info['owner_key'], {})
            owner_name = owner_prof.get('custom_nick') or pack_info['owner_key'].split('@')[0]
        pack_data = {**pack_info, 'owner_name': owner_name}
        if pack_info.get('for_sale') or pack_info.get('price', 0) == 0 or pack_info.get('owner_key') is None:
            all_packs_for_shop.append((pack_id, pack_data))
        if is_admin:
            all_packs_admin.append((pack_id, pack_data))
    posts = []
    if active_tab == 'posts':
        posts = load_posts()
        for post in posts:
            author_prof = profiles.get(post['author_key'], {})
            post['author_name'] = author_prof.get('custom_nick') or post['author_key'].split('@')[0]
            post['author_avatar'] = author_prof.get('picture', '')
            post['author_decorations'] = get_user_full_decorations(post['author_key'])
            # Добавляем украшения в комментарии
            for comment in post.get('comments', []):
                comment_author_key = comment.get('author_key')
                comment_author_prof = profiles.get(comment_author_key, {})
                comment['author_name'] = comment_author_prof.get('custom_nick') or comment_author_key.split('@')[0]
                comment['author_decorations'] = get_user_full_decorations(comment_author_key)
        posts = sorted(posts, key=lambda p: p['timestamp'], reverse=True)
    fm_viewers = {}
    if active_tab == 'burmalda_fm':
        fm_viewers_data = load_fm_viewers()
        now = datetime.now()
        for k, v in list(fm_viewers_data.items()):
            if (now - datetime.fromisoformat(v.get('last_seen', now.isoformat()))).seconds < 60:
                v['decorations'] = get_user_full_decorations(k)
                fm_viewers[k] = v
        save_fm_viewers(fm_viewers)
    
    all_decorations = load_decorations()
    # Обновляем URL картинок для всех украшений
    for dec_id, dec in all_decorations.items():
        if not dec.get('has_custom_image') or not dec.get('custom_image_url'):
            img_path = get_decoration_image_path(dec_id, dec.get('type'))
            if img_path:
                dec['has_custom_image'] = True
                dec['custom_image_url'] = img_path
    
    user_owned_decorations = get_user_owned_decorations(user_key) if user_key else []
    user_equipped_decorations = get_user_equipped_decorations(user_key) if user_key else []
    dec_filter = request.args.get('dec_filter', 'all')
    
    workshop_mode = request.args.get('mode', 'choose')
    workshop_step = int(request.args.get('step', 1))
    workshop_pack_id = request.args.get('pack_id', '')
    workshop_pack_name = ''
    workshop_pack_desc = ''
    workshop_pack_price = 0
    workshop_pack_for_sale = False
    workshop_pending_stickers = []
    my_workshop_packs = []
    
    if active_tab == 'workshop' and user_key:
        sticker_packs_data = load_sticker_packs()
        all_packs = sticker_packs_data.get('packs', {})
        for pid, pinfo in all_packs.items():
            if pinfo.get('owner_key') == user_key:
                my_workshop_packs.append((pid, pinfo))
        
        if workshop_pack_id and workshop_pack_id in all_packs:
            pack_info = all_packs[workshop_pack_id]
            workshop_pack_name = pack_info.get('name', '')
            workshop_pack_desc = pack_info.get('description', '')
            workshop_pack_price = pack_info.get('price', 0)
            workshop_pack_for_sale = pack_info.get('for_sale', False)
            
            pending = load_pending_stickers()
            workshop_pending_stickers = [s for s in pending if s.get('pack_id') == workshop_pack_id and not s.get('approved', False)]
    
    return render_template_string(HTML_TEMPLATE, active_tab=active_tab, user=user, user_profile=user_profile,
        is_admin=is_admin, files=files, is_maintenance=IS_MAINTENANCE_MODE, action_error=action_error,
        sticker_packs=sticker_packs, pending_stickers=pending_stickers, pending_count=len(pending_stickers),
        user_chats=user_chats, current_chat_id=current_chat_id, all_groups=all_groups, all_users=all_users, bots=bots,
        current_chat_name=current_chat_name, current_chat_partner=current_chat_partner,
        current_chat_is_group=current_chat_is_group, current_chat_muted=current_chat_muted,
        group_members=group_members, can_manage_curr_group=can_manage_curr_group,
        user_owned_packs=user_owned_packs, user_burmalnets_display=user_burmalnets_display,
        all_packs_for_shop=all_packs_for_shop, all_packs_admin=all_packs_admin, user_key=user_key, posts=posts,
        daily_tasks=daily_tasks, completed_tasks_count=completed_tasks_count, earned_today=earned_today,
        user_subscription_active=user_subscription_active, user_subscription_until=user_subscription_until,
        subscription_duration_days=subscription_duration_days, fm_viewers=fm_viewers,
        all_decorations=all_decorations, user_owned_decorations=user_owned_decorations,
        user_equipped_decorations=user_equipped_decorations, dec_filter=dec_filter,
        workshop_mode=workshop_mode, workshop_step=workshop_step, workshop_pack_id=workshop_pack_id,
        workshop_pack_name=workshop_pack_name, workshop_pack_desc=workshop_pack_desc,
        workshop_pack_price=workshop_pack_price, workshop_pack_for_sale=workshop_pack_for_sale,
        workshop_pending_stickers=workshop_pending_stickers, my_workshop_packs=my_workshop_packs)

@app.route('/settings')
def settings_page():
    user = session.get('user')
    if not user: return redirect('/')
    user_key = (user.get('email') or user.get('nickname')).lower()
    USER_ACTIVITY[user_key] = datetime.now()
    user_profile = get_user_profile(user_key)
    is_admin = session.get('is_admin', False)
    blacklist = load_blacklist()
    blocked_users = []
    profiles = load_profiles()
    for bkey in blacklist.get(user_key, []):
        bp = profiles.get(bkey, {})
        blocked_users.append({'key': bkey, 'name': bp.get('custom_nick') or bkey.split('@')[0]})
    my_packs = []
    sticker_packs_data = load_sticker_packs()
    for pack_id, pack_info in sticker_packs_data.get('packs', {}).items():
        if pack_info.get('owner_key') == user_key:
            my_packs.append((pack_id, pack_info))
    user_owned_decorations = get_user_owned_decorations(user_key)
    user_equipped_decorations = get_user_equipped_decorations(user_key)
    all_decorations = load_decorations()
    my_decorations = []
    for did in user_owned_decorations:
        if did in all_decorations:
            dec = all_decorations[did].copy()
            if not dec.get('has_custom_image') or not dec.get('custom_image_url'):
                img_path = get_decoration_image_path(did, dec.get('type'))
                if img_path:
                    dec['has_custom_image'] = True
                    dec['custom_image_url'] = img_path
            my_decorations.append((did, dec))
    
    html = '''
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Настройки — Бурмалдод</title>
<style>
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); color: #f8fafc; margin: 0; padding: 15px; min-height: 100vh; }
.header { display: flex; justify-content: space-between; align-items: center; max-width: 800px; margin: 0 auto 15px auto; background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(20px); padding: 12px 20px; border-radius: 16px; flex-wrap: wrap; gap: 10px; border: 1px solid rgba(255,255,255,0.1); }
.user-profile { display: flex; align-items: center; gap: 10px; }
.user-avatar { width: 44px; height: 44px; border-radius: 50%; border: 2px solid #38bdf8; object-fit: cover; }
.username { font-weight: 600; font-size: 15px; display: flex; flex-direction: column; }
.main-nick-tag { font-size: 11px; color: #38bdf8; }
.admin-badge { color: #f59e0b; font-weight: bold; font-size: 13px; margin-left: 5px; }
.btn-logout, .btn-back { background: #475569; color: #fff; padding: 8px 14px; border-radius: 8px; text-decoration: none; font-size: 13px; }
.btn-logout { background: linear-gradient(135deg, #ef4444, #dc2626); }
.container { max-width: 800px; margin: 0 auto; }
.settings-card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(20px); padding: 22px; border-radius: 16px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.08); }
.settings-card h4 { color: #38bdf8; margin-top: 0; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }
.profile-field { text-align: left; margin-bottom: 14px; }
.profile-field label { display: block; font-size: 12px; color: #94a3b8; margin-bottom: 4px; font-weight: 600; }
.profile-field input, .profile-field textarea, .profile-field select { width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); background: rgba(15, 23, 42, 0.8); color: #fff; font-size: 13px; }
.date-picker-row { display: flex; gap: 6px; }
.date-picker-row select { flex: 1; padding: 8px 4px; font-size: 12px; }
.avatar-preview { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.avatar-preview img { width: 84px; height: 84px; border-radius: 50%; border: 3px solid #38bdf8; object-fit: cover; box-shadow: 0 0 15px rgba(56, 189, 248, 0.4); }
.gallery-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 12px; }
.gallery-slot { aspect-ratio: 1; background: rgba(11, 17, 32, 0.8); border: 2px dashed #475569; border-radius: 10px; display: flex; align-items: center; justify-content: center; cursor: pointer; position: relative; overflow: hidden; font-size: 24px; color: #475569; transition: all 0.2s; }
.gallery-slot:hover { border-color: #38bdf8; }
.gallery-slot img { width: 100%; height: 100%; object-fit: cover; }
.gallery-slot .remove-btn { position: absolute; top: 2px; right: 2px; background: #ef4444; color: #fff; border: none; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; font-size: 12px; }
.btn-save { background: linear-gradient(135deg, #22c55e, #16a34a); color: #fff; border: none; padding: 12px 22px; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 14px; width: 100%; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3); }
.info-line { background: rgba(11, 17, 32, 0.8); padding: 12px; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.btn-danger { background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 12px; }
.blocked-item, .pack-item { background: rgba(11, 17, 32, 0.8); padding: 12px; border-radius: 10px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.btn-sell { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: bold; }
.toast { position: fixed; top: 20px; right: 20px; background: linear-gradient(135deg, #0284c7, #0369a1); color: #fff; padding: 14px 20px; border-radius: 10px; z-index: 5000; display: none; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
.my-dec-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-top: 12px; }
.my-dec-item { background: rgba(30, 41, 59, 0.8); padding: 12px; border-radius: 12px; text-align: center; position: relative; border: 1px solid rgba(255,255,255,0.05); transition: all 0.2s; }
.my-dec-item:hover { transform: translateY(-2px); border-color: rgba(56, 189, 248, 0.3); }
.my-dec-item .dec-preview { display: flex; justify-content: center; align-items: center; height: 60px; margin-bottom: 8px; background: rgba(0,0,0,0.2); border-radius: 8px; }
.my-dec-item .dec-preview img { max-width: 50px; max-height: 50px; object-fit: contain; }
.my-dec-item .emoji { font-size: 36px; }
.my-dec-item .name { font-size: 12px; color: #f8fafc; margin-top: 4px; font-weight: 600; }
.my-dec-item .type { font-size: 10px; color: #94a3b8; margin-top: 2px; }
.my-dec-item .equipped-badge { position: absolute; top: 6px; right: 6px; background: #22c55e; color: #fff; font-size: 10px; padding: 2px 8px; border-radius: 6px; font-weight: bold; }
.my-dec-item button { margin-top: 8px; width: 100%; }
@media (max-width: 700px) { body { padding: 8px; } .gallery-grid { grid-template-columns: repeat(2, 1fr); } .date-picker-row { flex-direction: column; } .my-dec-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
</head>
<body>
<div class="header">
    <div class="user-profile">
        {% if user.picture %}<img src="{{ user.picture }}" class="user-avatar">{% endif %}
        <span class="username">
            <span>{{ user_profile.custom_nick or user.nickname }} {% if is_admin %}<span class="admin-badge">[ADMIN]</span>{% endif %}</span>
            <span class="main-nick-tag">@{{ user.email.split('@')[0] if user.email else user.nickname }}</span>
        </span>
    </div>
    <div style="display:flex; gap:8px;">
        <a href="/" class="btn-back">← Назад</a>
        <a href="/logout" class="btn-logout">Выйти</a>
    </div>
</div>
<div class="container">
    <div class="settings-card">
        <h4>👤 Основная информация</h4>
        <div class="avatar-preview">
            <img id="avatarPreview" src="{{ user_profile.picture or 'https://via.placeholder.com/84' }}">
            <div style="flex:1;">
                <div class="profile-field">
                    <label>URL аватарки:</label>
                    <input type="text" id="editAvatarUrl" value="{{ user_profile.picture or '' }}" placeholder="https://...">
                </div>
            </div>
        </div>
        <div class="profile-field"><label>Никнейм (до 13 символов):</label><input type="text" id="editCustomNick" value="{{ user_profile.custom_nick or user.nickname }}" maxlength="13"></div>
        <div class="profile-field"><label>🎂 Дата рождения:</label>
            <div class="date-picker-row">
                <select id="editBirthDay"><option value="">День</option>{% for d in range(1, 32) %}<option value="{{ d }}" {% if user_profile.birth_day == d %}selected{% endif %}>{{ d }}</option>{% endfor %}</select>
                <select id="editBirthMonth"><option value="">Месяц</option>{% for m in range(1, 13) %}<option value="{{ m }}" {% if user_profile.birth_month == m %}selected{% endif %}>{{ ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'][m-1] }}</option>{% endfor %}</select>
                <select id="editBirthYear"><option value="">Год</option>{% for y in range(2026, 1920, -1) %}<option value="{{ y }}" {% if user_profile.birth_year == y %}selected{% endif %}>{{ y }}</option>{% endfor %}</select>
            </div>
        </div>
        <div class="profile-field"><label>О себе (до 30 символов):</label><textarea id="editBio" maxlength="30" rows="2">{{ user_profile.bio or '' }}</textarea></div>
        <button class="btn-save" onclick="saveAll()">💾 Сохранить</button>
    </div>
    
    <div class="settings-card">
        <h4>✨ Мои украшения ({{ my_decorations|length }})</h4>
        {% if my_decorations %}
        <p style="color:#94a3b8; font-size:12px; margin-bottom:12px;">Украшения отображаются ВЕЗДЕ: в чатах, постах, профиле, списке участников. Как в Discord!</p>
        <div class="my-dec-grid">
            {% for dec_id, dec in my_decorations %}
            <div class="my-dec-item" style="border-color: {{ dec.color }}40;">
                {% if dec_id in user_equipped_decorations %}<div class="equipped-badge">✓ НАДЕТО</div>{% endif %}
                <div class="dec-preview">
                    {% if dec.has_custom_image and dec.custom_image_url %}
                        <img src="{{ dec.custom_image_url }}" style="color: {{ dec.color }};" class="anim-{{ dec.animation }}">
                    {% else %}
                        <span class="emoji anim-{{ dec.animation }}" style="color: {{ dec.color }};">{{ dec.emoji }}</span>
                    {% endif %}
                </div>
                <div class="name">{{ dec.name }}</div>
                <div class="type">{{ dec.type }} | {{ dec.rarity }}</div>
                {% if dec_id in user_equipped_decorations %}
                <button onclick="unequipDec('{{ dec_id }}')" style="background:#ef4444; color:#fff; border:none; padding:6px 10px; border-radius:6px; font-size:11px; cursor:pointer;">Снять</button>
                {% else %}
                <button onclick="equipDec('{{ dec_id }}')" style="background:#22c55e; color:#fff; border:none; padding:6px 10px; border-radius:6px; font-size:11px; cursor:pointer;">Надеть</button>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        <a href="/?tab=decorations" style="display:block; text-align:center; margin-top:16px; color:#38bdf8; font-size:13px; text-decoration:none;">🛒 Купить новые украшения →</a>
        {% else %}
        <p style="color:#64748b; font-size:13px;">У вас нет украшений. <a href="/?tab=decorations" style="color:#38bdf8;">Перейти в магазин</a></p>
        {% endif %}
    </div>
    
    <div class="settings-card">
        <h4>🖼️ Галерея (до 4 фото)</h4>
        <div class="gallery-grid" id="galleryGrid"></div>
        <input type="file" id="galleryInput" accept="image/*" style="display:none;" onchange="uploadGalleryPhoto(this)">
        <small style="color:#94a3b8; display:block; margin-top:10px;">Нажмите на пустую ячейку, чтобы добавить фото.</small>
    </div>
    <div class="settings-card">
        <h4>🎨 Мои паки стикеров</h4>
{% for pack_id, pack_info in my_packs %}
        <div class="pack-item" style="flex-direction: column; align-items: stretch; gap: 10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; width:100%; flex-wrap:wrap; gap:8px;">
                <div>
                    <b id="packName_{{ pack_id }}">{{ pack_info.name }}</b>
                    <span style="color:#94a3b8; font-size:12px;">({{ pack_info.stickers|length }} стикеров)</span>
                </div>
                <div style="display:flex; gap:6px; flex-wrap:wrap;">
                    <button class="btn-sell" onclick="renamePackPrompt('{{ pack_id }}')" style="background:#38bdf8;">✏️ Имя</button>
                    <button class="btn-sell" onclick="changePackPricePrompt('{{ pack_id }}')" style="background:#818cf8;">💰 Цена</button>
{% if pack_info.for_sale %}
                    <button class="btn-sell" onclick="unsellPack('{{ pack_id }}')" style="background:#ef4444; color:#fff;">⛔ Снять</button>
{% else %}
                    <button class="btn-sell" onclick="sellPack('{{ pack_id }}')">🏷️ Продать</button>
{% endif %}
                    <button class="btn-sell" onclick="deletePackConfirm('{{ pack_id }}')" style="background:#ef4444; color:#fff;">🗑️</button>
                </div>
            </div>
            <div style="display:flex; gap:6px; flex-wrap:wrap; padding:8px; background:rgba(30, 41, 59, 0.8); border-radius:8px;">
{% for sticker in pack_info.stickers %}
                <div style="position:relative; width:64px; height:64px; background:rgba(11, 17, 32, 0.8); border-radius:6px; overflow:hidden;">
                    <img src="/static/stickers/custom/{{ sticker }}" style="width:100%; height:100%; object-fit:contain;">
                    <button onclick="removeStickerFromPack('{{ pack_id }}', '{{ sticker }}')" style="position:absolute; top:2px; right:2px; background:#ef4444; color:#fff; border:none; width:20px; height:20px; border-radius:50%; cursor:pointer; font-size:11px; line-height:1;">✖</button>
                </div>
{% else %}
                <span style="color:#64748b; font-size:12px;">Пусто</span>
{% endfor %}
            </div>
            <div style="font-size:12px; color:#94a3b8;">
{% if pack_info.for_sale %}
                🏷️ На продаже за <b style="color:#f59e0b;">{{ pack_info.price }}</b> бурмалкоинов
{% else %}
                🔒 Не выставлен на продажу
{% endif %}
            </div>
        </div>
{% else %}<p style="color:#64748b; font-size:13px;">У вас нет своих паков.</p>{% endfor %}
    </div>
    <div class="settings-card">
        <h4>🚫 Чёрный список ({{ blocked_users|length }})</h4>
{% for b in blocked_users %}
        <div class="blocked-item"><span>{{ b.name }} (@{{ b.key.split('@')[0] }})</span><button class="btn-danger" onclick="unblockUser('{{ b.key }}')">Убрать</button></div>
{% else %}<p style="color:#64748b; font-size:13px;">Список пуст.</p>{% endfor %}
    </div>
    <div class="settings-card">
        <h4>ℹ️ Информация об аккаунте</h4>
        <div class="info-line"><span>📧 Почта:</span><span>{{ user.email }}</span></div>
        <div class="info-line"><span>🛡️ Статус:</span><span>{% if is_admin %}🟡 Администратор{% else %}🟢 Пользователь{% endif %}</span></div>
        <div class="info-line"><span>💰 Бурмалнеты:</span><span>{% if is_admin %}∞{% else %}{{ user_profile.get('burmalnets', 5) }}{% endif %}</span></div>
        <div class="info-line"><span>🆔 ID:</span><span style="font-family:monospace; font-size:11px; color:#94a3b8;">{{ user_key }}</span></div>
    </div>
</div>
<div class="toast" id="toast"></div>
<script>
const user = {{ user|tojson|safe }};
const user_profile = {{ user_profile|tojson|safe }};
const gallery = {{ user_profile.get('gallery', [])|tojson|safe }};
function showToast(text) { const t = document.getElementById("toast"); t.innerText = text; t.style.display = "block"; setTimeout(() => { t.style.display = "none"; }, 2500); }
function renderGallery() {
    const grid = document.getElementById("galleryGrid"); let html = '';
    for (let i = 0; i < 4; i++) {
        if (gallery[i]) html += `<div class="gallery-slot"><img src="${gallery[i]}"><button class="remove-btn" onclick="removeGallery(${i})">✖</button></div>`;
        else html += `<div class="gallery-slot" onclick="document.getElementById('galleryInput').click()">+</div>`;
    }
    grid.innerHTML = html;
}
async function uploadGalleryPhoto(input) {
    if (!input.files || !input.files[0]) return;
    if (gallery.length >= 4) { alert("Максимум 4 фото!"); input.value = ''; return; }
    const formData = new FormData(); formData.append('file', input.files[0]);
    const res = await fetch('/upload_gallery_photo', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.status === 'ok') { gallery.push(data.url); await saveGallery(); renderGallery(); }
    else alert(data.message || "Ошибка");
    input.value = '';
}
async function removeGallery(idx) { gallery.splice(idx, 1); await saveGallery(); renderGallery(); }
async function saveGallery() { await fetch('/update_gallery', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({gallery: gallery}) }); }
async function saveAll() {
    const avatarUrl = document.getElementById("editAvatarUrl").value.trim();
    const customNick = document.getElementById("editCustomNick").value.trim();
    const birthDay = parseInt(document.getElementById("editBirthDay").value) || null;
    const birthMonth = parseInt(document.getElementById("editBirthMonth").value) || null;
    const birthYear = parseInt(document.getElementById("editBirthYear").value) || null;
    const bio = document.getElementById("editBio").value.trim();
    if (customNick.length > 13) { alert("Никнейм должен быть до 13 символов!"); return; }
    if (bio.length > 30) { alert("Описание должно быть до 30 символов!"); return; }
    const res = await fetch('/update_profile', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ picture: avatarUrl, custom_nick: customNick, birth_day: birthDay, birth_month: birthMonth, birth_year: birthYear, bio: bio }) });
    const data = await res.json();
    if (data.status === 'ok') { showToast("✅ Сохранено!"); if (avatarUrl) document.getElementById("avatarPreview").src = avatarUrl; }
    else alert(data.message || "Ошибка");
}
async function unblockUser(key) {
    const res = await fetch('/toggle_blacklist', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({target_key: key, block: false}) });
    if ((await res.json()).status === 'ok') window.location.reload();
}
async function sellPack(packId) {
    const price = prompt("Цена в бурмалнетах (0 = бесплатно):");
    if (price === null) return;
    const res = await fetch('/sell_pack/' + packId, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({price: parseInt(price) || 0}) });
    const data = await res.json();
    if (data.status === 'ok') { showToast("Выставлен на продажу!"); window.location.reload(); }
    else alert(data.message || "Ошибка");
}
async function renamePackPrompt(packId) {
    const currentName = document.getElementById('packName_' + packId).innerText;
    const newName = prompt("Новое название пака (до 30 символов):", currentName);
    if (newName === null || !newName.trim()) return;
    const res = await fetch('/rename_pack/' + packId, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: newName.trim()}) });
    const data = await res.json();
    if (data.status === 'ok') { showToast("✅ Переименовано"); window.location.reload(); }
    else alert(data.message || "Ошибка");
}
async function changePackPricePrompt(packId) {
    const newPrice = prompt("Новая цена в бурмалкоинах (0 = бесплатно):", "0");
    if (newPrice === null) return;
    const price = parseInt(newPrice);
    if (isNaN(price) || price < 0) { alert("Некорректная цена"); return; }
    const res = await fetch('/change_pack_price/' + packId, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({price: price}) });
    const data = await res.json();
    if (data.status === 'ok') { showToast("✅ Цена изменена"); window.location.reload(); }
    else alert(data.message || "Ошибка");
}
async function unsellPack(packId) {
    if (!confirm("Снять пак с продажи?")) return;
    const res = await fetch('/unsell_pack/' + packId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') { showToast("✅ Снят с продажи"); window.location.reload(); }
    else alert(data.message || "Ошибка");
}
async function removeStickerFromPack(packId, stickerFilename) {
    if (!confirm("Удалить этот стикер из пака? Файл будет удалён.")) return;
    const res = await fetch('/remove_sticker_from_pack', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({pack_id: packId, sticker_filename: stickerFilename}) });
    const data = await res.json();
    if (data.status === 'ok') { showToast("✅ Стикер удалён"); window.location.reload(); }
    else alert(data.message || "Ошибка");
}
async function deletePackConfirm(packId) {
    if (!confirm("Удалить пак ЦЕЛИКОМ? Все стикеры будут потеряны!")) return;
    const res = await fetch('/delete_pack/' + packId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') { showToast("✅ Пак удалён"); window.location.reload(); }
    else alert(data.message || "Ошибка");
}
async function equipDec(decId) {
    const res = await fetch('/equip_decoration/' + decId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') { showToast("✅ " + data.message); window.location.reload(); }
    else alert(data.message || "Ошибка");
}
async function unequipDec(decId) {
    const res = await fetch('/unequip_decoration/' + decId, { method: 'POST' });
    const data = await res.json();
    if (data.status === 'ok') { showToast("✅ " + data.message); window.location.reload(); }
    else alert(data.message || "Ошибка");
}
renderGallery();
document.getElementById("editAvatarUrl").addEventListener('input', (e) => { document.getElementById("avatarPreview").src = e.target.value || 'https://via.placeholder.com/84'; });
</script>
</body>
</html>
'''
    return render_template_string(html, user=user, user_profile=user_profile, is_admin=is_admin, blocked_users=blocked_users, my_packs=my_packs, user_key=user_key, my_decorations=my_decorations, user_equipped_decorations=user_equipped_decorations)

# =====================================================================
# 📁 ВСЕ ОСТАЛЬНЫЕ МАРШРУТЫ (сохранены из оригинала)
# =====================================================================

@app.route('/upload_gallery_photo', methods=['POST'])
def upload_gallery_photo():
    user = session.get('user')
    if not user: return jsonify({'status': 'error', 'message': 'Не авторизован'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    profiles = load_profiles()
    prof = profiles.get(user_key, {})
    gallery = prof.get('gallery', [])
    if len(gallery) >= 4: return jsonify({'status': 'error', 'message': 'Максимум 4 фото'}), 400
    file = request.files.get('file')
    if not file or not file.filename: return jsonify({'status': 'error', 'message': 'Файл не выбран'}), 400
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.webp', '.gif']: return jsonify({'status': 'error', 'message': 'Неподдерживаемый формат'}), 400
    filename = f"{user_key}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(GALLERY_DIR, filename)
    file.save(filepath)
    url = f"/static/gallery/{filename}"
    gallery.append(url)
    prof['gallery'] = gallery
    profiles[user_key] = prof
    save_profiles(profiles)
    return jsonify({'status': 'ok', 'url': url})

@app.route('/update_gallery', methods=['POST'])
def update_gallery():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    data = request.get_json()
    gallery = data.get('gallery', [])[:4]
    profiles = load_profiles()
    prof = profiles.get(user_key, {})
    prof['gallery'] = gallery
    profiles[user_key] = prof
    save_profiles(profiles)
    return jsonify({'status': 'ok'})

@app.route('/upload_local_file', methods=['POST'])
def upload_local_file():
    user = session.get('user')
    if not user: return jsonify({'status': 'error', 'message': 'Войдите в систему'}), 401
    file = request.files.get('file')
    if not file or not file.filename: return jsonify({'status': 'error', 'message': 'Файл не выбран'}), 400
    safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = os.path.join(UPLOADS_DIR, safe_filename)
    file.save(filepath)
    size_bytes = os.path.getsize(filepath)
    size_mb = f"{size_bytes / (1024 * 1024):.1f} MB" if size_bytes > 1024*1024 else f"{size_bytes // 1024} KB"
    if user:
        user_key = (user.get('email') or user.get('nickname')).lower()
        increment_task_progress(user_key, 'upload_file')
    return jsonify({'status': 'ok', 'file': {'url': f"/download_local/{safe_filename}", 'name': file.filename, 'size': size_mb}})

@app.route('/download_local/<filename>')
def download_local(filename):
    filepath = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(filepath): return "Файл не найден", 404
    return send_file(filepath, as_attachment=True)

@app.route('/create_group', methods=['POST'])
def create_group():
    user = session.get('user')
    if not user: return redirect('/')
    user_key = (user.get('email') or user.get('nickname')).lower()
    is_admin = session.get('is_admin', False)
    groups = load_groups()
    group_name = request.form.get('group_name', '').strip()
    group_avatar = request.form.get('group_avatar', '').strip()
    is_public = bool(request.form.get('is_public')) if is_admin else False
    if group_name:
        gid = f"group_{uuid.uuid4().hex[:8]}"
        groups[gid] = {'name': group_name, 'avatar': group_avatar, 'owner': user.get('nickname'), 'owner_key': user_key, 'is_public': is_public, 'members': [user_key], 'blocked': []}
        save_groups(groups)
        increment_task_progress(user_key, 'create_group')
        return redirect(f'/?tab=chat&chat_id={gid}')
    return redirect('/')

@app.route('/get_group_info')
def get_group_info():
    user = session.get('user')
    if not user: return jsonify({}), 401
    chat_id = request.args.get('chat_id')
    groups = load_groups()
    ginfo = groups.get(chat_id, {})
    if not can_manage_group((user.get('email') or user.get('nickname')).lower(), ginfo):
        return jsonify({'error': 'Нет прав'}), 403
    profiles = load_profiles()
    members = []
    for mk in ginfo.get('members', []):
        mp = profiles.get(mk, {})
        members.append({'key': mk, 'name': mp.get('custom_nick') or mk.split('@')[0], 'is_owner': mk == ginfo.get('owner_key')})
    return jsonify({'is_public': ginfo.get('is_public', False), 'members': members})

@app.route('/delete_group/<group_id>', methods=['POST'])
def delete_group(group_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    groups = load_groups()
    ginfo = groups.get(group_id, {})
    if not can_manage_group(user_key, ginfo):
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403
    del groups[group_id]
    save_groups(groups)
    return jsonify({'status': 'ok'})

@app.route('/toggle_group_public/<group_id>', methods=['POST'])
def toggle_group_public(group_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    groups = load_groups()
    ginfo = groups.get(group_id, {})
    if not can_manage_group(user_key, ginfo):
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403
    ginfo['is_public'] = not ginfo.get('is_public', False)
    groups[group_id] = ginfo
    save_groups(groups)
    return jsonify({'status': 'ok', 'is_public': ginfo['is_public']})

@app.route('/add_group_member/<group_id>', methods=['POST'])
def add_group_member(group_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    data = request.get_json()
    target = data.get('target', '').strip().lower()
    if not target: return jsonify({'status': 'error', 'message': 'Введите ник или email'}), 400
    if target.startswith('@'): target = target[1:]
    groups = load_groups()
    ginfo = groups.get(group_id, {})
    if not can_manage_group(user_key, ginfo):
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403
    profiles = load_profiles()
    target_key = None
    for pkey, pval in profiles.items():
        p_nickname = pval.get('nickname', '').lower()
        p_custom_nick = pval.get('custom_nick', '').lower()
        p_email_local = pkey.split('@')[0].lower() if '@' in pkey else pkey.lower()
        if target == pkey or target == p_nickname or target == p_custom_nick or target == p_email_local:
            target_key = pkey
            break
    if not target_key:
        for pkey in profiles.keys():
            if target in pkey:
                target_key = pkey
                break
    if not target_key:
        return jsonify({'status': 'error', 'message': f'Пользователь не найден'}), 404
    if target_key in ginfo.get('blocked', []):
        return jsonify({'status': 'error', 'message': 'Заблокирован'}), 400
    if target_key not in ginfo.get('members', []):
        ginfo['members'].append(target_key)
        groups[group_id] = ginfo
        save_groups(groups)
    return jsonify({'status': 'ok'})

@app.route('/kick_group_member/<group_id>/<member_key>', methods=['POST'])
def kick_group_member(group_id, member_key):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    groups = load_groups()
    ginfo = groups.get(group_id, {})
    if not can_manage_group(user_key, ginfo): return jsonify({'status': 'error', 'message': 'Нет прав'}), 403
    if ginfo.get('owner_key') == member_key: return jsonify({'status': 'error', 'message': 'Нельзя исключить владельца'}), 400
    if member_key in ginfo.get('members', []):
        ginfo['members'].remove(member_key)
        groups[group_id] = ginfo
        save_groups(groups)
    return jsonify({'status': 'ok'})

@app.route('/block_group_member/<group_id>/<member_key>', methods=['POST'])
def block_group_member(group_id, member_key):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    groups = load_groups()
    ginfo = groups.get(group_id, {})
    if not can_manage_group(user_key, ginfo): return jsonify({'status': 'error', 'message': 'Нет прав'}), 403
    if ginfo.get('owner_key') == member_key: return jsonify({'status': 'error', 'message': 'Нельзя заблокировать владельца'}), 400
    if 'blocked' not in ginfo: ginfo['blocked'] = []
    if member_key in ginfo.get('members', []): ginfo['members'].remove(member_key)
    if member_key not in ginfo['blocked']: ginfo['blocked'].append(member_key)
    groups[group_id] = ginfo
    save_groups(groups)
    return jsonify({'status': 'ok'})

@app.route('/create_bot', methods=['POST'])
def create_bot():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    bots = load_bots()
    bot_id = f"bot_{uuid.uuid4().hex[:6]}"
    bots[bot_id] = {'name': f"Мой бот {len([b for b in bots.values() if b.get('owner_key') == user_key])+1}", 'avatar': 'https://via.placeholder.com/80', 'script': 'if "привет" in text.lower():\n    reply(f"Привет, {user}!")', 'enabled': True, 'owner_key': user_key}
    save_bots(bots)
    return jsonify({'status': 'ok'})

@app.route('/admin/save_bot', methods=['POST'])
def admin_save_bot():
    if not session.get('is_admin'): return "403", 403
    bot_id = request.form.get('bot_id')
    bots = load_bots()
    if bot_id in bots:
        bots[bot_id]['name'] = request.form.get('name', 'Бот').strip()
        bots[bot_id]['avatar'] = request.form.get('avatar', '').strip()
        bots[bot_id]['script'] = request.form.get('script', '')
        bots[bot_id]['enabled'] = 'enabled' in request.form
        save_bots(bots)
    return redirect('/?tab=admin_panel')

@app.route('/admin/delete_bot/<bot_id>')
def admin_delete_bot(bot_id):
    if not session.get('is_admin'): return "403", 403
    bots = load_bots()
    if bot_id in bots:
        del bots[bot_id]
        save_bots(bots)
    return redirect('/?tab=admin_panel')

@app.route('/admin/delete_pack/<pack_id>')
def admin_delete_pack(pack_id):
    if not session.get('is_admin'): return "403", 403
    sticker_packs_data = load_sticker_packs()
    if pack_id in sticker_packs_data.get('packs', {}):
        del sticker_packs_data['packs'][pack_id]
        save_sticker_packs(sticker_packs_data)
    return redirect('/?tab=admin_panel')

@app.route('/admin/create_decoration', methods=['POST'])
def admin_create_decoration():
    if not session.get('is_admin'): return "403", 403
    name = request.form.get('name', '').strip()
    dec_type = request.form.get('type', 'badge')
    emoji = request.form.get('emoji', '✨')
    description = request.form.get('description', '').strip()
    color = request.form.get('color', '#38bdf8')
    rarity = request.form.get('rarity', 'common')
    price = int(request.form.get('price', 15))
    animation = request.form.get('animation', 'none')
    image_file = request.files.get('image_file')
    if not name: return redirect('/?tab=admin_panel')
    decorations = load_decorations()
    dec_id = f"dec_{uuid.uuid4().hex[:8]}"
    
    has_custom_image = False
    custom_image_url = ''
    if image_file:
        image_url = save_decoration_image(image_file, dec_id, dec_type)
        if image_url:
            has_custom_image = True
            custom_image_url = image_url
    
    decorations[dec_id] = {
        'id': dec_id, 'name': name, 'type': dec_type, 'description': description,
        'price': price, 'emoji': emoji, 'color': color, 'rarity': rarity,
        'animation': animation, 'effect_intensity': 0.8,
        'has_custom_image': has_custom_image, 'custom_image_url': custom_image_url,
    }
    save_decorations(decorations)
    return redirect('/?tab=admin_panel')

@app.route('/admin/delete_decoration/<dec_id>')
def admin_delete_decoration(dec_id):
    if not session.get('is_admin'): return "403", 403
    decorations = load_decorations()
    if dec_id in decorations:
        dec_type = decorations[dec_id].get('type', 'badge')
        delete_decoration_image(dec_id, dec_type)
        del decorations[dec_id]
        save_decorations(decorations)
    return redirect('/?tab=admin_panel')

@app.route('/pin_message', methods=['POST'])
def pin_message():
    data = request.get_json()
    chat_id = data.get('chat_id')
    pinned_data = load_pinned_messages()
    if data.get('unpin'): pinned_data.pop(chat_id, None)
    else: pinned_data[chat_id] = {'user': data.get('user'), 'text': data.get('text')}
    save_pinned_messages(pinned_data)
    return jsonify({'status': 'ok'})

@app.route('/get_pinned')
def get_pinned():
    chat_id = request.args.get('chat_id', 'general')
    return jsonify(load_pinned_messages().get(chat_id, {}))

@app.route('/send_voice', methods=['POST'])
def send_voice():
    if IS_MAINTENANCE_MODE and not session.get('is_admin'): return jsonify({'status': 'error'}), 503
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    file = request.files.get('file')
    chat_id = request.form.get('chat_id', 'general')
    reply_to_raw = request.form.get('reply_to')
    reply_to = json.loads(reply_to_raw) if reply_to_raw else None
    if not file: return jsonify({'status': 'error'}), 400
    filename = f"{uuid.uuid4().hex}.webm"
    filepath = os.path.join(VOICE_DIR, filename)
    file.save(filepath)
    save_chat_message(user_dict=user, chat_id=chat_id, text="", voice_url=f"/static/voice/{filename}", reply_to=reply_to)
    return jsonify({'status': 'ok'})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    data = request.get_json()
    user_key = (user.get('email') or user.get('nickname')).lower()
    is_admin = session.get('is_admin', False)
    picture = data.get('picture', '').strip()
    custom_nick = data.get('custom_nick', '').strip()
    birth_day = data.get('birth_day')
    birth_month = data.get('birth_month')
    birth_year = data.get('birth_year')
    bio = data.get('bio', '').strip()
    if len(custom_nick) > 13: return jsonify({'status': 'error', 'message': 'Ник до 13 символов'}), 400
    if len(bio) > 30: return jsonify({'status': 'error', 'message': 'Описание до 30 символов'}), 400
    try:
        birth_day = int(birth_day) if birth_day != '' else None
        birth_month = int(birth_month) if birth_month != '' else None
        birth_year = int(birth_year) if birth_year != '' else None
    except ValueError: return jsonify({'status': 'error'}), 400
    profiles = load_profiles()
    prof = profiles.get(user_key, {})
    prof['picture'] = picture or user.get('picture', '')
    prof['custom_nick'] = custom_nick or user.get('nickname', '')
    prof['nickname'] = user.get('nickname', '')
    if birth_day is not None: prof['birth_day'] = birth_day
    if birth_month is not None: prof['birth_month'] = birth_month
    if birth_year is not None: prof['birth_year'] = birth_year
    prof['bio'] = bio
    prof['is_admin'] = is_admin
    prof['last_seen'] = datetime.now().strftime("%d.%m.%Y %H:%M")
    profiles[user_key] = prof
    save_profiles(profiles)
    session['user']['picture'] = prof['picture']
    increment_task_progress(user_key, 'update_profile')
    return jsonify({'status': 'ok'})

@app.route('/get_user_profile')
def get_user_profile_route():
    user_key = request.args.get('user_key', '').strip().lower()
    if not user_key: return jsonify({})
    prof = get_user_profile(user_key)
    main_nick = f"@{user_key.split('@')[0]}" if '@' in user_key else f"@{user_key}"
    current_user = session.get('user')
    is_blacklisted = False
    if current_user:
        curr_key = (current_user.get('email') or current_user.get('nickname')).lower()
        is_blacklisted = user_key in load_blacklist().get(curr_key, [])
    burmalnets = prof.get('burmalnets', INITIAL_BURMALNETS)
    
    # Полная информация об украшениях
    decorations = get_user_full_decorations(user_key)
    
    return jsonify({
        'main_nick': main_nick, 'custom_nick': prof.get('custom_nick', ''), 'nickname': prof.get('nickname', ''),
        'picture': prof.get('picture', ''), 'birth_day': prof.get('birth_day'), 'birth_month': prof.get('birth_month'),
        'birth_year': prof.get('birth_year'), 'bio': prof.get('bio', ''), 'gallery': prof.get('gallery', []),
        'last_seen': get_last_seen(user_key), 'is_admin': prof.get('is_admin', False), 'is_blacklisted': is_blacklisted,
        'email': user_key, 'burmalnets': burmalnets,
        'decorations': decorations
    })

@app.route('/search_users')
def search_users():
    q = request.args.get('q', '').strip().lower()
    if q.startswith('@'): q = q[1:]
    if not q: return jsonify([])
    raw_lines = load_raw_messages()
    profiles = load_profiles()
    users_found = {}
    for line in raw_lines:
        try:
            decrypted = cipher.decrypt(line.encode('utf-8')).decode('utf-8')
            data = json.loads(decrypted)
            user_key = (data.get('email') or data.get('user')).lower()
            main_nick = user_key.split('@')[0]
            if q in main_nick:
                prof = profiles.get(user_key, {})
                decorations = get_user_full_decorations(user_key)
                users_found[user_key] = {
                    'id': user_key, 'main_nick': f"@{main_nick}",
                    'name': prof.get('custom_nick') or data.get('user'),
                    'avatar': prof.get('picture', ''),
                    'decorations': decorations
                }
        except Exception: pass
    return jsonify(list(users_found.values()))

@app.route('/open_private_chat', methods=['POST'])
def open_private_chat():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    data = request.get_json()
    target_id = data.get('target_id')
    my_id = (user.get('email') or user.get('nickname')).lower()
    if not target_id or target_id.lower() == my_id: return jsonify({'status': 'error'}), 400
    if is_user_blocked(my_id, target_id) or is_user_blocked(target_id, my_id):
        return jsonify({'status': 'error', 'message': 'Чат заблокирован'}), 403
    increment_task_progress(my_id, 'open_private')
    return jsonify({'status': 'ok', 'chat_id': make_private_chat_id(my_id, target_id)})

@app.route('/toggle_blacklist', methods=['POST'])
def toggle_blacklist():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    data = request.get_json()
    target_key = (data.get('target_key') or '').strip().lower()
    block = bool(data.get('block'))
    my_key = (user.get('email') or user.get('nickname')).lower()
    if not target_key or target_key == my_key: return jsonify({'status': 'error'}), 400
    target_prof = get_user_profile(target_key)
    if target_prof.get('is_admin'): return jsonify({'status': 'error', 'message': 'Нельзя админа'}), 403
    blacklist = load_blacklist()
    my_list = blacklist.get(my_key, [])
    if block:
        if target_key not in my_list: my_list.append(target_key)
    else:
        if target_key in my_list: my_list.remove(target_key)
    blacklist[my_key] = my_list
    save_blacklist(blacklist)
    return jsonify({'status': 'ok'})

@app.route('/toggle_mute', methods=['POST'])
def toggle_mute():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    data = request.get_json()
    target_key = (data.get('target_key') or '').strip().lower()
    my_key = (user.get('email') or user.get('nickname')).lower()
    profiles = load_profiles()
    prof = profiles.get(my_key, {})
    muted = prof.get('muted', [])
    if target_key in muted:
        muted.remove(target_key); new_state = False
    else:
        muted.append(target_key); new_state = True
    prof['muted'] = muted
    profiles[my_key] = prof
    save_profiles(profiles)
    return jsonify({'status': 'ok', 'muted': new_state})

@app.route('/toggle_shutdown', methods=['POST'])
def toggle_shutdown():
    global IS_MAINTENANCE_MODE
    if session.get('is_admin'): IS_MAINTENANCE_MODE = not IS_MAINTENANCE_MODE
    return redirect(request.referrer or '/')

@app.route('/get_messages')
def get_messages():
    user = session.get('user')
    chat_id = request.args.get('chat_id', 'general')
    if user: USER_ACTIVITY[(user.get('email') or user.get('nickname')).lower()] = datetime.now()
    if IS_MAINTENANCE_MODE and not session.get('is_admin'): return jsonify([])
    return jsonify(load_chat_messages(target_chat_id=chat_id, current_user=user))

@app.route('/send_message', methods=['POST'])
def send_message():
    if IS_MAINTENANCE_MODE and not session.get('is_admin'): return jsonify({'status': 'error'}), 503
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    chat_id = request.form.get('chat_id', 'general')
    text = request.form.get('message', '').strip()
    sticker_url = request.form.get('sticker_url', '').strip()
    voice_url = request.form.get('voice_url', '').strip()
    call_url = request.form.get('call_url', '').strip()
    forwarded_from = request.form.get('forwarded_from', '').strip() or None
    local_file_raw = request.form.get('local_file')
    local_file = json.loads(local_file_raw) if local_file_raw else None
    reply_to_raw = request.form.get('reply_to')
    reply_to = json.loads(reply_to_raw) if reply_to_raw else None
    if chat_id.startswith('private_'):
        my_id = (user.get('email') or user.get('nickname')).lower()
        parts = chat_id.replace('private_', '').split('_')
        partner_id = parts[0] if parts[1] == my_id else parts[1]
        if is_user_blocked(my_id, partner_id) or is_user_blocked(partner_id, my_id):
            return jsonify({'status': 'error'}), 403
    if text or sticker_url or voice_url or call_url or local_file:
        try:
            save_chat_message(user_dict=user, chat_id=chat_id, text=text, sticker_url=sticker_url, voice_url=voice_url, local_file=local_file, call_url=call_url, reply_to=reply_to, forwarded_from=forwarded_from)
            return jsonify({'status': 'ok'})
        except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'empty'})

# =====================================================================
# 🎨 МАСТЕРСКАЯ СТИКЕРОВ И УКРАШЕНИЙ
# =====================================================================
@app.route('/workshop/create_pack', methods=['POST'])
def workshop_create_pack():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    data = request.get_json()
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    price = int(data.get('price', 0))
    if not name: return jsonify({'status': 'error'}), 400
    if len(name) > 30: return jsonify({'status': 'error', 'message': 'Название до 30'}), 400
    sticker_packs_data = load_sticker_packs()
    packs = sticker_packs_data.get('packs', {})
    pack_id = f"pack_{uuid.uuid4().hex[:8]}"
    packs[pack_id] = {
        'name': name, 'description': description, 'owner_key': user_key,
        'stickers': [], 'price': price, 'for_sale': False,
        'created': datetime.now().isoformat()
    }
    sticker_packs_data['packs'] = packs
    save_sticker_packs(sticker_packs_data)
    return jsonify({'status': 'ok', 'pack_id': pack_id})

@app.route('/workshop/upload_sticker', methods=['POST'])
def workshop_upload_sticker():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    file = request.files.get('file')
    pack_id = request.form.get('pack_id', '').strip()
    if not file or not file.filename: return jsonify({'status': 'error'}), 400
    if not pack_id: return jsonify({'status': 'error'}), 400
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
        return jsonify({'status': 'error', 'message': 'Формат'}), 400
    sticker_packs_data = load_sticker_packs()
    packs = sticker_packs_data.get('packs', {})
    if pack_id not in packs: return jsonify({'status': 'error'}), 404
    if packs[pack_id].get('owner_key') != user_key and not session.get('is_admin'):
        return jsonify({'status': 'error'}), 403
    current_pending = [s for s in load_pending_stickers() if s.get('pack_id') == pack_id and not s.get('approved', False)]
    current_approved = len(packs[pack_id].get('stickers', []))
    if len(current_pending) + current_approved >= 20:
        return jsonify({'status': 'error', 'message': 'Максимум 20'}), 400
    temp_path = os.path.join(PENDING_STICKERS_DIR, f"temp_{uuid.uuid4().hex}{ext}")
    file.save(temp_path)
    file_hash = compute_file_hash(temp_path)
    sticker_hashes = load_sticker_hashes()
    if file_hash in sticker_hashes:
        try: os.remove(temp_path)
        except: pass
        return jsonify({'status': 'error', 'message': 'Дубликат'}), 400
    sticker_file_id = f"{pack_id}_{uuid.uuid4().hex[:8]}{ext}"
    final_path = os.path.join(PENDING_STICKERS_DIR, sticker_file_id)
    os.rename(temp_path, final_path)
    sticker_hashes[file_hash] = {'sticker_file_id': sticker_file_id, 'pack_id': pack_id, 'added': datetime.now().isoformat()}
    save_sticker_hashes(sticker_hashes)
    pending = load_pending_stickers()
    sticker_data = {
        'id': sticker_file_id, 'filename': sticker_file_id, 'pack_id': pack_id,
        'pack_name': packs[pack_id]['name'], 'user': user.get('nickname', 'Аноним'),
        'user_key': user_key, 'time': datetime.now().strftime("%d.%m %H:%M"),
        'pending': True, 'approved': False
    }
    pending.append(sticker_data)
    save_pending_stickers(pending)
    return jsonify({'status': 'ok', 'sticker': sticker_data})

@app.route('/workshop/remove_pending_sticker', methods=['POST'])
def workshop_remove_pending_sticker():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    data = request.get_json()
    sticker_id = data.get('sticker_id')
    pack_id = data.get('pack_id')
    if not sticker_id or not pack_id: return jsonify({'status': 'error'}), 400
    sticker_packs_data = load_sticker_packs()
    packs = sticker_packs_data.get('packs', {})
    if pack_id not in packs: return jsonify({'status': 'error'}), 404
    if packs[pack_id].get('owner_key') != user_key and not session.get('is_admin'):
        return jsonify({'status': 'error'}), 403
    pending = load_pending_stickers()
    sticker = next((s for s in pending if s['id'] == sticker_id), None)
    if sticker:
        src = os.path.join(PENDING_STICKERS_DIR, sticker['filename'])
        if os.path.exists(src):
            try: os.remove(src)
            except: pass
        pending = [s for s in pending if s['id'] != sticker_id]
        save_pending_stickers(pending)
    sticker_hashes = load_sticker_hashes()
    hash_to_remove = None
    for h, info in sticker_hashes.items():
        if info.get('sticker_file_id') == sticker_id:
            hash_to_remove = h; break
    if hash_to_remove:
        sticker_hashes.pop(hash_to_remove, None)
        save_sticker_hashes(sticker_hashes)
    return jsonify({'status': 'ok'})

@app.route('/workshop/update_pack_settings', methods=['POST'])
def workshop_update_pack_settings():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    data = request.get_json()
    pack_id = data.get('pack_id')
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    price = int(data.get('price', 0))
    for_sale = bool(data.get('for_sale', False))
    if not pack_id: return jsonify({'status': 'error'}), 400
    sticker_packs_data = load_sticker_packs()
    packs = sticker_packs_data.get('packs', {})
    if pack_id not in packs: return jsonify({'status': 'error'}), 404
    if packs[pack_id].get('owner_key') != user_key and not session.get('is_admin'):
        return jsonify({'status': 'error'}), 403
    if name: packs[pack_id]['name'] = name
    packs[pack_id]['description'] = description
    packs[pack_id]['price'] = price
    packs[pack_id]['for_sale'] = for_sale
    sticker_packs_data['packs'] = packs
    save_sticker_packs(sticker_packs_data)
    return jsonify({'status': 'ok'})

@app.route('/workshop/submit_for_moderation', methods=['POST'])
def workshop_submit_for_moderation():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    data = request.get_json()
    pack_id = data.get('pack_id')
    if not pack_id: return jsonify({'status': 'error'}), 400
    sticker_packs_data = load_sticker_packs()
    packs = sticker_packs_data.get('packs', {})
    if pack_id not in packs: return jsonify({'status': 'error'}), 404
    if packs[pack_id].get('owner_key') != user_key and not session.get('is_admin'):
        return jsonify({'status': 'error'}), 403
    pending = load_pending_stickers()
    pack_pending = [s for s in pending if s.get('pack_id') == pack_id and not s.get('approved', False)]
    if not pack_pending: return jsonify({'status': 'error', 'message': 'Нет стикеров'}), 400
    for s in pack_pending:
        s['submitted_for_moderation'] = True
        s['moderation_time'] = datetime.now().isoformat()
    save_pending_stickers(pending)
    return jsonify({'status': 'ok'})

@app.route('/workshop/create_decoration', methods=['POST'])
def workshop_create_decoration():
    """Создание украшения пользователем с загрузкой картинки"""
    user = session.get('user')
    if not user: return jsonify({'status': 'error', 'message': 'Не авторизован'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    
    name = (request.form.get('name') or '').strip()
    dec_type = request.form.get('type', 'badge')
    emoji = (request.form.get('emoji') or '✨').strip()
    description = (request.form.get('description') or '').strip()
    color = request.form.get('color', '#38bdf8')
    animation = request.form.get('animation', 'none')
    rarity = request.form.get('rarity', 'common')
    price = int(request.form.get('price', 15))
    intensity = float(request.form.get('effect_intensity', 0.8))
    position = request.form.get('position', 'after_nick')
    size = request.form.get('size', 'medium')
    image_file = request.files.get('image_file')
    
    if not name: return jsonify({'status': 'error', 'message': 'Введите название'}), 400
    if not emoji and not image_file: return jsonify({'status': 'error', 'message': 'Введите эмодзи или загрузите картинку'}), 400
    if len(name) > 30: return jsonify({'status': 'error', 'message': 'Название до 30 символов'}), 400
    if len(description) > 100: return jsonify({'status': 'error', 'message': 'Описание до 100'}), 400
    if price < 0: return jsonify({'status': 'error', 'message': 'Цена не отрицательная'}), 400
    
    decoration_data = {
        'name': name, 'type': dec_type, 'emoji': emoji, 'description': description,
        'color': color, 'animation': animation, 'rarity': rarity, 'price': price,
        'effect_intensity': intensity, 'position': position, 'size': size
    }
    
    success, message, dec_id = create_custom_decoration(user_key, decoration_data, image_file)
    if success:
        return jsonify({'status': 'ok', 'message': message, 'decoration_id': dec_id})
    else:
        return jsonify({'status': 'error', 'message': message}), 400

@app.route('/request_sticker', methods=['POST'])
def request_sticker():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    file = request.files.get('file')
    pack_name = request.form.get('pack_name', '').strip()
    if not file or not file.filename: return jsonify({'status': 'error'}), 400
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
        return jsonify({'status': 'error'}), 400
    user_key = (user.get('email') or user.get('nickname')).lower()
    sticker_packs_data = load_sticker_packs()
    packs = sticker_packs_data.get('packs', {})
    pack_id = None
    for pid, pinfo in packs.items():
        if pinfo.get('owner_key') == user_key:
            pack_id = pid
            if pack_name: pinfo['name'] = pack_name
            break
    if not pack_id:
        if not pack_name: return jsonify({'status': 'error', 'message': 'Укажите название'}), 400
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        packs[pack_id] = {'name': pack_name, 'owner_key': user_key, 'stickers': [], 'price': 0, 'for_sale': False}
        sticker_packs_data['packs'] = packs
        save_sticker_packs(sticker_packs_data)
    temp_path = os.path.join(PENDING_STICKERS_DIR, f"temp_{uuid.uuid4().hex}{ext}")
    file.save(temp_path)
    file_hash = compute_file_hash(temp_path)
    sticker_hashes = load_sticker_hashes()
    if file_hash in sticker_hashes:
        try: os.remove(temp_path)
        except: pass
        return jsonify({'status': 'error', 'message': 'Дубликат'}), 400
    sticker_file_id = f"{pack_id}_{uuid.uuid4().hex[:8]}{ext}"
    final_path = os.path.join(PENDING_STICKERS_DIR, sticker_file_id)
    os.rename(temp_path, final_path)
    sticker_hashes[file_hash] = {'sticker_file_id': sticker_file_id, 'pack_id': pack_id, 'added': datetime.now().isoformat()}
    save_sticker_hashes(sticker_hashes)
    pending = load_pending_stickers()
    pending.append({'id': sticker_file_id, 'filename': sticker_file_id, 'pack_id': pack_id, 'pack_name': packs[pack_id]['name'], 'user': user.get('nickname', 'Аноним'), 'time': datetime.now().strftime("%d.%m %H:%M")})
    save_pending_stickers(pending)
    return jsonify({'status': 'ok', 'pack_name': packs[pack_id]['name']})

@app.route('/admin/approve_sticker', methods=['POST'])
def approve_sticker():
    if not session.get('is_admin'): return "403", 403
    sticker_file_id = request.form.get('sticker_id')
    pending = load_pending_stickers()
    item = next((s for s in pending if s['id'] == sticker_file_id), None)
    if item:
        src = os.path.join(PENDING_STICKERS_DIR, item['filename'])
        dst = os.path.join(APPROVED_STICKERS_DIR, item['filename'])
        if os.path.exists(src): os.rename(src, dst)
        sticker_packs_data = load_sticker_packs()
        pack_id = item.get('pack_id')
        if pack_id and pack_id in sticker_packs_data.get('packs', {}):
            if item['filename'] not in sticker_packs_data['packs'][pack_id].get('stickers', []):
                sticker_packs_data['packs'][pack_id]['stickers'].append(item['filename'])
            save_sticker_packs(sticker_packs_data)
        pending = [s for s in pending if s['id'] != sticker_file_id]
        save_pending_stickers(pending)
    return redirect('/?tab=pending')

@app.route('/admin/reject_sticker', methods=['POST'])
def reject_sticker():
    if not session.get('is_admin'): return "403", 403
    sticker_file_id = request.form.get('sticker_id')
    pending = load_pending_stickers()
    item = next((s for s in pending if s['id'] == sticker_file_id), None)
    if item:
        src = os.path.join(PENDING_STICKERS_DIR, item['filename'])
        if os.path.exists(src): os.remove(src)
        sticker_hashes = load_sticker_hashes()
        hash_to_remove = None
        for h, info in sticker_hashes.items():
            if info.get('sticker_file_id') == sticker_file_id:
                hash_to_remove = h; break
        if hash_to_remove:
            sticker_hashes.pop(hash_to_remove, None)
            save_sticker_hashes(sticker_hashes)
        pending = [s for s in pending if s['id'] != sticker_file_id]
        save_pending_stickers(pending)
    return redirect('/?tab=pending')

@app.route('/delete_message', methods=['POST'])
def delete_message():
    if IS_MAINTENANCE_MODE and not session.get('is_admin'): return jsonify({'status': 'error'}), 503
    user = session.get('user')
    is_admin = session.get('is_admin', False)
    msg_id = request.form.get('msg_id')
    chat_id = request.form.get('chat_id', '')
    if msg_id:
        is_private_chat = chat_id.startswith('private_')
        delete_chat_message(msg_id, user, is_admin or is_private_chat, chat_id)
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400

@app.route('/edit_message', methods=['POST'])
def edit_message():
    if IS_MAINTENANCE_MODE and not session.get('is_admin'): return jsonify({'status': 'error'}), 503
    user = session.get('user')
    is_admin = session.get('is_admin', False)
    msg_id = request.form.get('msg_id')
    new_text = request.form.get('new_text', '').strip()
    if msg_id and new_text:
        edit_chat_message(msg_id, new_text, user, is_admin)
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400

@app.route('/add_reaction', methods=['POST'])
def add_reaction():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    data = request.get_json()
    msg_id = data.get('msg_id')
    emoji = data.get('emoji')
    if not msg_id or not emoji: return jsonify({'status': 'error'}), 400
    reactions = load_reactions()
    if msg_id not in reactions: reactions[msg_id] = {}
    if emoji not in reactions[msg_id]: reactions[msg_id][emoji] = []
    if user_key in reactions[msg_id][emoji]:
        reactions[msg_id][emoji].remove(user_key)
        if not reactions[msg_id][emoji]: del reactions[msg_id][emoji]
        if not reactions[msg_id]: del reactions[msg_id]
    else:
        reactions[msg_id][emoji].append(user_key)
        increment_task_progress(user_key, 'react')
    save_reactions(reactions)
    return jsonify({'status': 'ok'})

@app.route('/create_post', methods=['POST'])
def create_post():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    content = request.form.get('content', '').strip()
    if not content: return jsonify({'status': 'error'}), 400
    if len(content) > 1000: return jsonify({'status': 'error'}), 400
    posts = load_posts()
    user_posts = [p for p in posts if p['author_key'] == user_key]
    if user_posts:
        last_post_time = datetime.fromisoformat(user_posts[-1]['timestamp'])
        if (datetime.now() - last_post_time).total_seconds() < SPAM_LIMIT_SECONDS:
            return jsonify({'status': 'error', 'message': 'Подождите'}), 400
    post_id = str(uuid.uuid4())[:8]
    post = {'id': post_id, 'author_key': user_key, 'content': content, 'timestamp': datetime.now().isoformat(), 'comments': [], 'likes': []}
    posts.append(post)
    save_posts(posts)
    increment_task_progress(user_key, 'create_post')
    return jsonify({'status': 'ok'})

@app.route('/add_comment/<post_id>', methods=['POST'])
def add_comment(post_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    comment_text = request.form.get('comment', '').strip()
    if not comment_text: return jsonify({'status': 'error'}), 400
    posts = load_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post: return jsonify({'status': 'error'}), 404
    comment = {'author_key': user_key, 'text': comment_text, 'timestamp': datetime.now().isoformat()}
    post['comments'].append(comment)
    save_posts(posts)
    return jsonify({'status': 'ok'})

@app.route('/like_post/<post_id>', methods=['POST'])
def like_post(post_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    posts = load_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post: return jsonify({'status': 'error'}), 404
    if user_key in post['likes']: post['likes'].remove(user_key)
    else: post['likes'].append(user_key)
    save_posts(posts)
    increment_task_progress(user_key, 'like_post')
    return jsonify({'status': 'ok', 'likes': len(post['likes'])})

@app.route('/delete_post/<post_id>', methods=['POST'])
def delete_post(post_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    is_admin = session.get('is_admin', False)
    posts = load_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post: return jsonify({'status': 'error'}), 404
    if post['author_key'] != user_key and not is_admin: return jsonify({'status': 'error'}), 403
    posts = [p for p in posts if p['id'] != post_id]
    save_posts(posts)
    return jsonify({'status': 'ok'})

@app.route('/claim_task', methods=['POST'])
def claim_task():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    data = request.get_json()
    task_id = data.get('task_id')
    reward, err = claim_task_reward(user_key, task_id)
    if err: return jsonify({'status': 'error', 'message': err}), 400
    return jsonify({'status': 'ok', 'reward': reward})

@app.route('/buy_subscription', methods=['POST'])
def buy_subscription():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    profiles = load_profiles()
    prof = profiles.get(user_key, {})
    balance = prof.get('burmalnets', INITIAL_BURMALNETS)
    if balance < SUBSCRIPTION_PRICE:
        return jsonify({'status': 'error', 'message': f'Недостаточно'}), 400
    if is_user_subscribed(user_key):
        try:
            current_until = datetime.fromisoformat(prof.get('subscription_until'))
            new_until = current_until + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
        except: new_until = datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
    else: new_until = datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
    prof['burmalnets'] = balance - SUBSCRIPTION_PRICE
    prof['subscription_until'] = new_until.isoformat()
    prof['last_subscription_payment'] = datetime.now().isoformat()
    profiles[user_key] = prof
    save_profiles(profiles)
    return jsonify({'status': 'ok', 'message': f'Подписка на {SUBSCRIPTION_DURATION_DAYS} дня!', 'until': new_until.strftime('%d.%m.%Y %H:%M')})

@app.route('/cancel_subscription', methods=['POST'])
def cancel_subscription():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    profiles = load_profiles()
    prof = profiles.get(user_key, {})
    prof['subscription_until'] = None
    prof['last_subscription_payment'] = None
    profiles[user_key] = prof
    save_profiles(profiles)
    return jsonify({'status': 'ok'})

@app.route('/buy_decoration/<dec_id>', methods=['POST'])
def buy_decoration_route(dec_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    success, message = buy_decoration(user_key, dec_id)
    if success: return jsonify({'status': 'ok', 'message': message})
    else: return jsonify({'status': 'error', 'message': message}), 400

@app.route('/buy_decoration_and_equip/<dec_id>', methods=['POST'])
def buy_decoration_and_equip_route(dec_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    success, message = buy_decoration(user_key, dec_id)
    if not success: return jsonify({'status': 'error', 'message': message}), 400
    success2, message2 = equip_decoration(user_key, dec_id)
    if success2: return jsonify({'status': 'ok', 'message': 'Украшение куплено и надето! Видно ВЕЗДЕ!'})
    else: return jsonify({'status': 'ok', 'message': 'Куплено, но не надето'})

@app.route('/equip_decoration/<dec_id>', methods=['POST'])
def equip_decoration_route(dec_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    success, message = equip_decoration(user_key, dec_id)
    if success: return jsonify({'status': 'ok', 'message': message})
    else: return jsonify({'status': 'error', 'message': message}), 400

@app.route('/unequip_decoration/<dec_id>', methods=['POST'])
def unequip_decoration_route(dec_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    success, message = unequip_decoration(user_key, dec_id)
    if success: return jsonify({'status': 'ok', 'message': message})
    else: return jsonify({'status': 'error', 'message': message}), 400

@app.route('/buy_pack/<pack_id>', methods=['POST'])
def buy_pack(pack_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    is_admin = session.get('is_admin', False)
    sticker_packs_data = load_sticker_packs()
    pack_info = sticker_packs_data.get('packs', {}).get(pack_id)
    if not pack_info: return jsonify({'status': 'error'}), 404
    profiles = load_profiles()
    user_prof = profiles.get(user_key, {})
    owned_packs = user_prof.get('owned_packs', [])
    if pack_id in owned_packs: return jsonify({'status': 'error', 'message': 'Уже есть'}), 400
    price = pack_info.get('price', 0)
    if not is_admin and price > 0:
        user_balance = user_prof.get('burmalnets', INITIAL_BURMALNETS)
        if user_balance < price: return jsonify({'status': 'error'}), 400
        user_prof['burmalnets'] = user_balance - price
        profiles[user_key] = user_prof
        owner_key = pack_info.get('owner_key')
        if owner_key and owner_key != user_key:
            owner_prof = profiles.get(owner_key, {})
            owner_prof['burmalnets'] = owner_prof.get('burmalnets', INITIAL_BURMALNETS) + price
            profiles[owner_key] = owner_prof
        save_profiles(profiles)
    owned_packs.append(pack_id)
    user_prof['owned_packs'] = owned_packs
    profiles[user_key] = user_prof
    save_profiles(profiles)
    return jsonify({'status': 'ok'})

@app.route('/sell_pack/<pack_id>', methods=['POST'])
def sell_pack(pack_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    data = request.get_json()
    price = data.get('price', 0)
    sticker_packs_data = load_sticker_packs()
    pack_info = sticker_packs_data.get('packs', {}).get(pack_id)
    if not pack_info or pack_info.get('owner_key') != user_key: return jsonify({'status': 'error'}), 403
    pack_info['price'] = price
    pack_info['for_sale'] = True
    sticker_packs_data['packs'][pack_id] = pack_info
    save_sticker_packs(sticker_packs_data)
    return jsonify({'status': 'ok'})

@app.route('/rename_pack/<pack_id>', methods=['POST'])
def rename_pack(pack_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    if not can_manage_pack(user_key, pack_id): return jsonify({'status': 'error'}), 403
    data = request.get_json()
    new_name = (data.get('name') or '').strip()
    if not new_name or len(new_name) > 30: return jsonify({'status': 'error'}), 400
    sticker_packs_data = load_sticker_packs()
    if pack_id in sticker_packs_data.get('packs', {}):
        sticker_packs_data['packs'][pack_id]['name'] = new_name
        save_sticker_packs(sticker_packs_data)
    return jsonify({'status': 'ok'})

@app.route('/remove_sticker_from_pack', methods=['POST'])
def remove_sticker_from_pack():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    data = request.get_json()
    pack_id = data.get('pack_id')
    sticker_filename = data.get('sticker_filename')
    if not pack_id or not sticker_filename: return jsonify({'status': 'error'}), 400
    if not can_manage_pack(user_key, pack_id): return jsonify({'status': 'error'}), 403
    sticker_packs_data = load_sticker_packs()
    pack_info = sticker_packs_data.get('packs', {}).get(pack_id)
    if not pack_info: return jsonify({'status': 'error'}), 404
    if sticker_filename in pack_info.get('stickers', []):
        pack_info['stickers'].remove(sticker_filename)
        try:
            filepath = os.path.join(APPROVED_STICKERS_DIR, sticker_filename)
            if os.path.exists(filepath): os.remove(filepath)
        except: pass
        save_sticker_packs(sticker_packs_data)
    return jsonify({'status': 'ok'})

@app.route('/unsell_pack/<pack_id>', methods=['POST'])
def unsell_pack(pack_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    if not can_manage_pack(user_key, pack_id): return jsonify({'status': 'error'}), 403
    sticker_packs_data = load_sticker_packs()
    if pack_id in sticker_packs_data.get('packs', {}):
        sticker_packs_data['packs'][pack_id]['for_sale'] = False
        save_sticker_packs(sticker_packs_data)
    return jsonify({'status': 'ok'})

@app.route('/change_pack_price/<pack_id>', methods=['POST'])
def change_pack_price(pack_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    if not can_manage_pack(user_key, pack_id): return jsonify({'status': 'error'}), 403
    data = request.get_json()
    try: new_price = int(data.get('price', 0))
    except: return jsonify({'status': 'error'}), 400
    if new_price < 0: return jsonify({'status': 'error'}), 400
    sticker_packs_data = load_sticker_packs()
    if pack_id in sticker_packs_data.get('packs', {}):
        sticker_packs_data['packs'][pack_id]['price'] = new_price
        save_sticker_packs(sticker_packs_data)
    return jsonify({'status': 'ok'})

@app.route('/delete_pack/<pack_id>', methods=['POST'])
def delete_pack(pack_id):
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    if not can_manage_pack(user_key, pack_id): return jsonify({'status': 'error'}), 403
    if pack_id in ['pack1', 'pack2'] and not session.get('is_admin'): return jsonify({'status': 'error'}), 403
    sticker_packs_data = load_sticker_packs()
    if pack_id in sticker_packs_data.get('packs', {}):
        del sticker_packs_data['packs'][pack_id]
        save_sticker_packs(sticker_packs_data)
    return jsonify({'status': 'ok'})

@app.route('/update_fm_viewer', methods=['POST'])
def update_fm_viewer():
    user = session.get('user')
    if not user: return jsonify({'status': 'error'}), 401
    user_key = (user.get('email') or user.get('nickname')).lower()
    fm_viewers = load_fm_viewers()
    prof = get_user_profile(user_key)
    fm_viewers[user_key] = {
        'name': prof.get('custom_nick') or user.get('nickname', 'Аноним'),
        'picture': prof.get('picture', ''),
        'last_seen': datetime.now().isoformat(),
        'decorations': get_user_full_decorations(user_key)
    }
    save_fm_viewers(fm_viewers)
    return jsonify({'status': 'ok'})

@app.route('/get_fm_viewers')
def get_fm_viewers():
    fm_viewers = load_fm_viewers()
    now = datetime.now()
    active = {}
    for k, v in fm_viewers.items():
        if (now - datetime.fromisoformat(v.get('last_seen', now.isoformat()))).seconds < 60:
            v['decorations'] = get_user_full_decorations(k)
            active[k] = v
    return jsonify(active)

@app.route('/remove_fm_viewer', methods=['POST'])
def remove_fm_viewer():
    user = session.get('user')
    if not user: return '', 204
    user_key = (user.get('email') or user.get('nickname')).lower()
    fm_viewers = load_fm_viewers()
    if user_key in fm_viewers:
        del fm_viewers[user_key]
        save_fm_viewers(fm_viewers)
    return '', 204

@app.route('/login')
def login():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    redirect_uri = get_redirect_uri()
    request_uri = client.prepare_request_uri(authorization_endpoint, redirect_uri=redirect_uri, scope=["openid", "email", "profile"])
    return redirect(request_uri)

@app.route('/login/callback')
def callback():
    code = request.args.get("code")
    if code:
        try:
            google_provider_cfg = get_google_provider_cfg()
            token_endpoint = google_provider_cfg["token_endpoint"]
            redirect_uri = get_redirect_uri()
            token_url, headers, body = client.prepare_token_request(
                token_endpoint,
                authorization_response=request.url.replace("http://", "https://", 1) if not request.url.startswith("http://127.0.0.1") and not request.url.startswith("http://localhost") else request.url,
                redirect_url=redirect_uri, code=code
            )
            token_response = requests.post(token_url, headers=headers, data=body, auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET))
            client.parse_request_body_response(json.dumps(token_response.json()))
            userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
            userinfo_response = requests.get(userinfo_endpoint, headers={'Authorization': f'Bearer {client.token["access_token"]}'}).json()
            if userinfo_response.get("email_verified"):
                email = userinfo_response["email"]
                is_admin = (email == AUTO_ADMIN_EMAIL)
                session["user"] = {"email": email, "nickname": email.split('@')[0], "picture": userinfo_response.get("picture", "")}
                session["is_admin"] = is_admin
                user_key = email.lower()
                profiles = load_profiles()
                if user_key not in profiles:
                    profiles[user_key] = {
                        'picture': userinfo_response.get("picture", ""),
                        'custom_nick': email.split('@')[0][:13],
                        'nickname': email.split('@')[0],
                        'bio': '', 'gallery': [], 'muted': [],
                        'is_admin': is_admin,
                        'burmalnets': INITIAL_BURMALNETS,
                        'owned_packs': []
                    }
                else: profiles[user_key]['is_admin'] = is_admin
                if 'burmalnets' not in profiles[user_key]: profiles[user_key]['burmalnets'] = INITIAL_BURMALNETS
                if 'owned_packs' not in profiles[user_key]: profiles[user_key]['owned_packs'] = []
                save_profiles(profiles)
        except Exception as e:
            session['action_error'] = f"Ошибка авторизации: {e}"
    return redirect('/')

@app.route('/logout')
def logout():
    user = session.get('user')
    if user:
        user_key = (user.get('email') or user.get('nickname')).lower()
        fm_viewers = load_fm_viewers()
        if user_key in fm_viewers:
            del fm_viewers[user_key]
            save_fm_viewers(fm_viewers)
        session.pop("user", None)
        session.pop("is_admin", None)
    return redirect('/')

@app.route('/download/<file_id>/<filename>')
def download(file_id, filename):
    if IS_MAINTENANCE_MODE and not session.get('is_admin'): return "Maintenance", 503
    is_hidden = filename.startswith('hidden_') or filename.startswith('.')
    if is_hidden and not session.get('is_admin'): return "Forbidden", 403
    try:
        drive_service = get_drive_service()
        request_drive = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_drive)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        return send_file(fh, download_name=filename, as_attachment=True)
    except Exception as e:
        return f"Ошибка: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)