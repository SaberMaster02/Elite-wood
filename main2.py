import asyncio
import sqlite3
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
import pytz

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
API_TOKEN = ''
ADMIN_IDS = [2061960043]
CHANNEL_USERNAME = '@elitewood_channel'
MANAGER_USERNAME = '@elitewood_manager'
MANAGER_PHONE = '+79876543210'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Классы состояний FSM
class AddProductStates(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_wood_type = State()
    waiting_for_category = State()
    waiting_for_length = State()
    waiting_for_width = State()
    waiting_for_thickness = State()
    waiting_for_price = State()
    waiting_for_description = State()
    waiting_for_photo = State()

class EditProductStates(StatesGroup):
    waiting_for_product_id = State()
    waiting_for_edit_choice = State()
    waiting_for_new_full_name = State()
    waiting_for_new_wood_type = State()
    waiting_for_new_category = State()
    waiting_for_new_length = State()
    waiting_for_new_width = State()
    waiting_for_new_thickness = State()
    waiting_for_new_price = State()
    waiting_for_new_description = State()
    waiting_for_new_photo = State()

class DeleteProductStates(StatesGroup):
    waiting_for_product_id = State()

class CartStates(StatesGroup):
    waiting_for_pickup_date = State()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()

class FilterStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_wood_type = State()
    waiting_for_length = State()
    waiting_for_width = State()
    waiting_for_thickness = State()

# Список категорий продукции
CATEGORIES = [
    "Масла, Клеи",
    "Крепеж ZIPBOLT",
    "Мебельные щиты",
    "Ступени",
    "Подступенки",
    "Площадки",
    "Балясины",
    "Столбы",
    "Заготовки под столбы и балясины",
    "Поручни",
    "Решетки декоративные",
    "Доска",
    "МДФ",
    "Шпон",
    "Столешницы",
    "Заглушки, шканты, шары",
    "Брус клееный",
    "Кромка",
    "Погонаж"
]

# Типы древесины
WOOD_TYPES = [
    "Сосна",
    "Дуб",
    "Бук",
    "Ясень",
    "Ольха",
    "Береза",
    "Лиственница",
    "Ель",
    "Клен"
]

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('elitewood.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            subscribed INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            wood_type TEXT,
            category TEXT NOT NULL,
            length TEXT,
            width TEXT,
            thickness TEXT,
            price REAL NOT NULL,
            description TEXT,
            photo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_date TIMESTAMP,
            status TEXT DEFAULT 'в работе',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (order_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Функции для работы с базой данных
def get_db_connection():
    return sqlite3.connect('elitewood.db', check_same_thread=False)

def add_user(user_id, username, full_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)',
            (user_id, username, full_name)
        )
        conn.commit()
    finally:
        conn.close()

def get_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_subscription(user_id, subscribed):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET subscribed = ? WHERE user_id = ?',
        (1 if subscribed else 0, user_id)
    )
    conn.commit()
    conn.close()

def add_product(full_name, wood_type, category, length, width, thickness, price, description, photo):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO products (full_name, wood_type, category, length, width, thickness, price, description, photo) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (full_name, wood_type, category, length, width, thickness, price, description, photo)
    )
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()
    return product_id

def get_products_by_category(category):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM products WHERE category = ? ORDER BY product_id DESC',
        (category,)
    )
    products = cursor.fetchall()
    conn.close()
    return products

def get_filtered_products(category=None, wood_type=None, length=None, width=None, thickness=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if category and category != 'не указано':
        query += ' AND category = ?'
        params.append(category)
    
    if wood_type and wood_type != 'не указано':
        query += ' AND wood_type = ?'
        params.append(wood_type)
    
    if length and length != 'не указано':
        query += ' AND length = ?'
        params.append(length)
    
    if width and width != 'не указано':
        query += ' AND width = ?'
        params.append(width)
    
    if thickness and thickness != 'не указано':
        query += ' AND thickness = ?'
        params.append(thickness)
    
    query += ' ORDER BY product_id DESC'
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    conn.close()
    return products

def get_unique_values(column_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT DISTINCT {column_name} FROM products WHERE {column_name} IS NOT NULL AND {column_name} != "не указано"')
    values = [row[0] for row in cursor.fetchall()]
    conn.close()
    return values

def get_product_by_id(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product

def update_product_field(product_id, field_name, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f'UPDATE products SET {field_name} = ? WHERE product_id = ?',
        (value, product_id)
    )
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE product_id = ?', (product_id,))
    conn.commit()
    conn.close()

def get_all_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products ORDER BY product_id DESC')
    products = cursor.fetchall()
    conn.close()
    return products

def add_to_cart(user_id, product_id, quantity=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT cart_id, quantity FROM cart WHERE user_id = ? AND product_id = ?',
        (user_id, product_id)
    )
    existing = cursor.fetchone()
    
    if existing:
        new_quantity = existing[1] + quantity
        cursor.execute(
            'UPDATE cart SET quantity = ? WHERE cart_id = ?',
            (new_quantity, existing[0])
        )
    else:
        cursor.execute(
            'INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)',
            (user_id, product_id, quantity)
        )
    
    conn.commit()
    conn.close()

def get_cart(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.cart_id, p.product_id, p.full_name, p.category, p.description, p.price, p.photo, c.quantity,
               p.wood_type, p.length, p.width, p.thickness
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = ?
    ''', (user_id,))
    cart_items = cursor.fetchall()
    conn.close()
    return cart_items

def remove_from_cart(cart_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cart WHERE cart_id = ?', (cart_id,))
    conn.commit()
    conn.close()

def clear_cart(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def create_order(user_id, order_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO orders (user_id, order_date) VALUES (?, ?)',
        (user_id, order_date)
    )
    order_id = cursor.lastrowid
    
    cart_items = get_cart(user_id)
    for item in cart_items:
        cursor.execute(
            'INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)',
            (order_id, item[1], item[7])
        )
    
    clear_cart(user_id)
    
    conn.commit()
    conn.close()
    return order_id

def get_user_orders(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.order_id, o.order_date, o.status, o.created_at,
               GROUP_CONCAT(p.full_name || ' (x' || oi.quantity || ')', ', ') as items
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE o.user_id = ?
        GROUP BY o.order_id
        ORDER BY o.created_at DESC
    ''', (user_id,))
    orders = cursor.fetchall()
    conn.close()
    return orders

def get_all_subscribers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE subscribed = 1')
    subscribers = cursor.fetchall()
    conn.close()
    return [sub[0] for sub in subscribers]

def get_today_visitors():
    conn = get_db_connection()
    cursor = conn.cursor()
    today = datetime.now().date()
    cursor.execute(
        'SELECT COUNT(DISTINCT user_id) FROM users WHERE DATE(created_at) = ?',
        (today,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_total_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def add_admin(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def is_admin(user_id):
    if user_id in ADMIN_IDS:
        return True
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admins WHERE user_id = ?', (user_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def update_order_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    
    cursor.execute('''
        UPDATE orders 
        SET status = 'просрочен' 
        WHERE order_date < ? AND status = 'в работе'
    ''', (now,))
    
    conn.commit()
    conn.close()

# Клавиатуры пользователя
def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Каталог продукции", callback_data="catalog")
    builder.button(text="🔍 Фильтр товаров", callback_data="filter_products")
    builder.button(text="🛒 Корзина", callback_data="cart")
    builder.button(text="🔔 Подписаться на уведомления", callback_data="subscription")
    builder.button(text="📞 Связаться с менеджером", callback_data="manager")
    builder.button(text="📢 Наш телеграмм канал", callback_data="channel")
    builder.button(text="📦 Мои покупки", callback_data="my_orders")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить товар", callback_data="admin_add_product")
    builder.button(text="✏️ Изменить товар", callback_data="admin_edit_product")
    builder.button(text="🗑️ Удалить товар", callback_data="admin_delete_product")
    builder.button(text="📢 Сделать рассылку", callback_data="admin_broadcast")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="👥 Посещаемость сегодня", callback_data="admin_visitors")
    builder.button(text="🔙 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_categories_keyboard(back_to="main_menu", for_filter=False):
    builder = InlineKeyboardBuilder()
    for category in CATEGORIES:
        builder.button(text=category, callback_data=f"category_{CATEGORIES.index(category)}")
    
    if for_filter:
        builder.button(text="Пропустить", callback_data="skip_filter")
        builder.button(text="Сбросить фильтры", callback_data="reset_filters")
    
    if back_to == "main_menu":
        builder.button(text="🔙 Назад", callback_data="main_menu")
    elif back_to == "admin_menu":
        builder.button(text="🔙 Назад", callback_data="admin_menu")
    elif back_to == "filter":
        builder.button(text="🔙 Назад", callback_data="filter_products")
    
    builder.adjust(2)
    return builder.as_markup()

def get_wood_types_keyboard(for_filter=False):
    builder = InlineKeyboardBuilder()
    existing_wood_types = get_unique_values('wood_type')
    
    if existing_wood_types:
        for wood_type in existing_wood_types:
            builder.button(text=wood_type, callback_data=f"wood_{wood_type}")
    else:
        for wood_type in WOOD_TYPES:
            builder.button(text=wood_type, callback_data=f"wood_{wood_type}")
    
    if for_filter:
        builder.button(text="Пропустить", callback_data="skip_filter")
        builder.button(text="Сбросить фильтры", callback_data="reset_filters")
        builder.button(text="🔙 Назад", callback_data="filter_products")
    else:
        builder.button(text="🔙 Назад", callback_data="back_wood_types")
        builder.button(text="Нет типа", callback_data="wood_не указано")
    
    builder.adjust(2)
    return builder.as_markup()

def get_products_keyboard(products, category_index, page=0, products_per_page=5):
    builder = InlineKeyboardBuilder()
    
    start_idx = page * products_per_page
    end_idx = start_idx + products_per_page
    page_products = products[start_idx:end_idx]
    
    for product in page_products:
        product_id, full_name, wood_type, category, length, width, thickness, price, description, photo, created_at = product
        display_text = f"{full_name[:30]}... - {price}₽"
        if wood_type:
            display_text = f"{wood_type}: {display_text}"
        builder.button(text=display_text, callback_data=f"product_{product_id}")
    
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"products_prev_{category_index}_{page}")
    if end_idx < len(products):
        builder.button(text="Вперед ➡️", callback_data=f"products_next_{category_index}_{page}")
    
    builder.button(text="🔙 Назад к категориям", callback_data="catalog")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    
    builder.adjust(1, 2, 2)
    return builder.as_markup()

def get_product_detail_keyboard(product_id, in_cart=False, from_admin=False):
    builder = InlineKeyboardBuilder()
    if not in_cart and not from_admin:
        builder.button(text="➕ Добавить в корзину", callback_data=f"add_to_cart_{product_id}")
    
    if from_admin:
        builder.button(text="🔙 Назад к товарам", callback_data="admin_back_to_products")
    else:
        builder.button(text="🔙 Назад к товарам", callback_data="back_to_products")
    
    if from_admin:
        builder.button(text="🏠 Админ панель", callback_data="admin_menu")
    else:
        builder.button(text="🏠 Главное меню", callback_data="main_menu")
    
    builder.adjust(1)
    return builder.as_markup()

def get_cart_keyboard(cart_items):
    builder = InlineKeyboardBuilder()
    for item in cart_items:
        cart_id, product_id, full_name, category, description, price, photo, quantity, wood_type, length, width, thickness = item
        builder.button(text=f"❌ {full_name[:20]}... x{quantity}", callback_data=f"remove_{cart_id}")
    
    if cart_items:
        builder.button(text="✅ Оформить заказ", callback_data="checkout")
    
    builder.button(text="🔄 Очистить корзину", callback_data="clear_cart")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    
    builder.adjust(1)
    return builder.as_markup()

def get_manager_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📞 Позвонить", callback_data="call_manager")
    builder.button(text="✍️ Написать", callback_data="write_manager")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def get_subscription_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подписаться", callback_data="subscribe")
    builder.button(text="❌ Отписаться", callback_data="unsubscribe")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def get_edit_product_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Изменить название", callback_data="edit_full_name")
    builder.button(text="🌳 Изменить тип древесины", callback_data="edit_wood_type")
    builder.button(text="📂 Изменить категорию", callback_data="edit_category")
    builder.button(text="📏 Изменить длину", callback_data="edit_length")
    builder.button(text="📐 Изменить ширину", callback_data="edit_width")
    builder.button(text="📏 Изменить толщину", callback_data="edit_thickness")
    builder.button(text="💰 Изменить цену", callback_data="edit_price")
    builder.button(text="📝 Изменить описание", callback_data="edit_description")
    builder.button(text="📷 Изменить фото", callback_data="edit_photo")
    builder.button(text="🔙 Назад", callback_data="admin_menu")
    builder.button(text="🏠 Админ панель", callback_data="admin_menu")
    builder.adjust(2, 2, 2, 1, 2, 1)
    return builder.as_markup()

def get_back_to_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="admin_menu")
    builder.button(text="🏠 Админ панель", callback_data="admin_menu")
    builder.adjust(2)
    return builder.as_markup()

def get_filter_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📂 По категории", callback_data="filter_by_category")
    builder.button(text="🌳 По типу древесины", callback_data="filter_by_wood_type")
    builder.button(text="📏 По длине", callback_data="filter_by_length")
    builder.button(text="📐 По ширине", callback_data="filter_by_width")
    builder.button(text="📏 По толщине", callback_data="filter_by_thickness")
    builder.button(text="🔍 Применить фильтры", callback_data="apply_filters")
    builder.button(text="🔄 Сбросить фильтры", callback_data="reset_filters")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    add_user(user_id, username, full_name)
    
    welcome_text = (
        f"👋 Здравствуйте, {full_name}!\n\n"
        "Я чат бот-ассистент Elite Wood в Оренбурге.\n\n"
        "📍 Мы находимся по адресу:\n"
        "ул. Энергетиков 7в., 2 этаж, 201 офис\n"
        "(рядом с Сакмарской ТЭЦ)\n\n"
        "🕐 График работы:\n"
        "Пн-пт 9.00-17.00 (склад 16.30)\n"
        "Сб 10.00-14.00\n"
        "Вс - выходной\n\n"
        "Выберите нужный раздел:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    
    if is_admin(user_id):
        add_admin(user_id)
        await message.answer("Панель администратора:", reply_markup=get_admin_menu_keyboard())
    else:
        # Для обычных пользователей ничего не делаем
        pass

# Обработчики инлайн-кнопок пользователя
@dp.callback_query(F.data == "main_menu")
async def main_menu_handler(callback: CallbackQuery):
    welcome_text = (
        f"👋 Здравствуйте, {callback.from_user.full_name}!\n\n"
        "Я чат бот-ассистент Elite Wood в Оренбурге.\n\n"
        "📍 Мы находимся по адресу:\n"
        "ул. Энергетиков 7в., 2 этаж, 201 офис\n"
        "(рядом с Сакмарской ТЭЦ)\n\n"
        "🕐 График работы:\n"
        "Пн-пт 9.00-17.00 (склад 16.30)\n"
        "Сб 10.00-14.00\n"
        "Вс - выходной\n\n"
        "Выберите нужный раздел:"
    )
    await callback.message.edit_text(welcome_text, reply_markup=get_main_menu_keyboard())

@dp.callback_query(F.data == "catalog")
async def catalog_handler(callback: CallbackQuery):
    await callback.message.edit_text("Выберите категорию продукции:", reply_markup=get_categories_keyboard("main_menu"))

@dp.callback_query(F.data == "filter_products")
async def filter_products_handler(callback: CallbackQuery):
    await callback.message.edit_text("🔍 Фильтр товаров. Выберите параметр для фильтрации:", 
                                   reply_markup=get_filter_keyboard())

@dp.callback_query(F.data == "filter_by_category")
async def filter_by_category_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите категорию для фильтрации:", 
                                   reply_markup=get_categories_keyboard("filter", True))
    await state.set_state(FilterStates.waiting_for_category)

@dp.callback_query(F.data == "filter_by_wood_type")
async def filter_by_wood_type_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите тип древесины для фильтрации:", 
                                   reply_markup=get_wood_types_keyboard(True))
    await state.set_state(FilterStates.waiting_for_wood_type)

@dp.callback_query(F.data == "filter_by_length")
async def filter_by_length_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📏 Введите длину для фильтрации (например: 2000, 2400). Для пропуска введите 'пропустить':")
    await state.set_state(FilterStates.waiting_for_length)

@dp.callback_query(F.data == "filter_by_width")
async def filter_by_width_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📐 Введите ширину для фильтрации (например: 100, 150). Для пропуска введите 'пропустить':")
    await state.set_state(FilterStates.waiting_for_width)

@dp.callback_query(F.data == "filter_by_thickness")
async def filter_by_thickness_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📏 Введите толщину для фильтрации (например: 20, 40). Для пропуска введите 'пропустить':")
    await state.set_state(FilterStates.waiting_for_thickness)

@dp.callback_query(F.data == "apply_filters")
async def apply_filters_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    category = data.get('filter_category', None)
    wood_type = data.get('filter_wood_type', None)
    length = data.get('filter_length', None)
    width = data.get('filter_width', None)
    thickness = data.get('filter_thickness', None)
    
    products = get_filtered_products(category, wood_type, length, width, thickness)
    
    if not products:
        await callback.message.edit_text(
            "🔍 По вашим критериям фильтрации товаров не найдено.\n\n"
            f"Категория: {category if category else 'любая'}\n"
            f"Тип древесины: {wood_type if wood_type else 'любой'}\n"
            f"Длина: {length if length else 'любая'}\n"
            f"Ширина: {width if width else 'любая'}\n"
            f"Толщина: {thickness if thickness else 'любая'}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Изменить фильтры", callback_data="filter_products")],
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
            ])
        )
        return
    
    # Показываем первые 5 товаров
    await show_filtered_products(callback, products, 0)

@dp.callback_query(F.data == "reset_filters")
async def reset_filters_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("✅ Фильтры сброшены.", 
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                       [InlineKeyboardButton(text="🔍 Фильтр товаров", callback_data="filter_products")],
                                       [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
                                   ]))

@dp.callback_query(F.data == "skip_filter")
async def skip_filter_handler(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state == FilterStates.waiting_for_category.state:
        await state.update_data(filter_category='не указано')
        await callback.message.edit_text("✅ Параметр категории пропущен.", reply_markup=get_filter_keyboard())
        await state.set_state(None)
    elif current_state == FilterStates.waiting_for_wood_type.state:
        await state.update_data(filter_wood_type='не указано')
        await callback.message.edit_text("✅ Параметр типа древесины пропущен.", reply_markup=get_filter_keyboard())
        await state.set_state(None)
    # Для остальных параметров обрабатывается в message handlers

async def show_filtered_products(callback: CallbackQuery, products, page=0, products_per_page=5):
    builder = InlineKeyboardBuilder()
    
    start_idx = page * products_per_page
    end_idx = start_idx + products_per_page
    page_products = products[start_idx:end_idx]
    
    for product in page_products:
        product_id, full_name, wood_type, category, length, width, thickness, price, description, photo, created_at = product
        display_text = f"{full_name[:30]}... - {price}₽"
        if wood_type:
            display_text = f"{wood_type}: {display_text}"
        builder.button(text=display_text, callback_data=f"product_{product_id}")
    
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"filtered_prev_{page}")
    if end_idx < len(products):
        builder.button(text="Вперед ➡️", callback_data=f"filtered_next_{page}")
    
    builder.button(text="🔍 Изменить фильтры", callback_data="filter_products")
    builder.button(text="🔙 Главное меню", callback_data="main_menu")
    
    builder.adjust(1, 2, 2)
    
    products_text = f"🔍 Найдено товаров: {len(products)}\n\n"
    products_text += f"Страница {page + 1} из {((len(products) - 1) // products_per_page) + 1}\n\n"
    
    await callback.message.edit_text(products_text, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("filtered_prev_") | F.data.startswith("filtered_next_"))
async def filtered_pagination_handler(callback: CallbackQuery, state: FSMContext):
    data_parts = callback.data.split("_")
    action = data_parts[1]
    current_page = int(data_parts[2])
    
    data = await state.get_data()
    category = data.get('filter_category', None)
    wood_type = data.get('filter_wood_type', None)
    length = data.get('filter_length', None)
    width = data.get('filter_width', None)
    thickness = data.get('filter_thickness', None)
    
    products = get_filtered_products(category, wood_type, length, width, thickness)
    
    if action == "prev":
        new_page = current_page - 1
    else:
        new_page = current_page + 1
    
    await show_filtered_products(callback, products, new_page)

@dp.message(FilterStates.waiting_for_length)
async def process_filter_length(message: types.Message, state: FSMContext):
    if message.text.lower() == 'пропустить':
        await state.update_data(filter_length='не указано')
        await message.answer("✅ Параметр длины пропущен.", reply_markup=get_filter_keyboard())
        await state.set_state(None)
    else:
        await state.update_data(filter_length=message.text.strip())
        await message.answer(f"✅ Длина для фильтрации установлена: {message.text.strip()}", 
                           reply_markup=get_filter_keyboard())
        await state.set_state(None)

@dp.message(FilterStates.waiting_for_width)
async def process_filter_width(message: types.Message, state: FSMContext):
    if message.text.lower() == 'пропустить':
        await state.update_data(filter_width='не указано')
        await message.answer("✅ Параметр ширины пропущен.", reply_markup=get_filter_keyboard())
        await state.set_state(None)
    else:
        await state.update_data(filter_width=message.text.strip())
        await message.answer(f"✅ Ширина для фильтрации установлена: {message.text.strip()}", 
                           reply_markup=get_filter_keyboard())
        await state.set_state(None)

@dp.message(FilterStates.waiting_for_thickness)
async def process_filter_thickness(message: types.Message, state: FSMContext):
    if message.text.lower() == 'пропустить':
        await state.update_data(filter_thickness='не указано')
        await message.answer("✅ Параметр толщины пропущен.", reply_markup=get_filter_keyboard())
        await state.set_state(None)
    else:
        await state.update_data(filter_thickness=message.text.strip())
        await message.answer(f"✅ Толщина для фильтрации установлена: {message.text.strip()}", 
                           reply_markup=get_filter_keyboard())
        await state.set_state(None)

@dp.callback_query(FilterStates.waiting_for_category, F.data.startswith("category_"))
async def process_filter_category(callback: CallbackQuery, state: FSMContext):
    category_index = int(callback.data.split("_")[1])
    category = CATEGORIES[category_index]
    
    await state.update_data(filter_category=category)
    await callback.message.edit_text(f"✅ Категория для фильтрации установлена: {category}", 
                                   reply_markup=get_filter_keyboard())
    await state.set_state(None)

@dp.callback_query(FilterStates.waiting_for_wood_type, F.data.startswith("wood_"))
async def process_filter_wood_type(callback: CallbackQuery, state: FSMContext):
    wood_type = callback.data.split("_")[1]
    
    await state.update_data(filter_wood_type=wood_type)
    await callback.message.edit_text(f"✅ Тип древесины для фильтрации установлен: {wood_type}", 
                                   reply_markup=get_filter_keyboard())
    await state.set_state(None)

@dp.callback_query(F.data == "cart")
async def cart_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    cart_items = get_cart(user_id)
    
    if not cart_items:
        await callback.message.edit_text("🛒 Ваша корзина пуста.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        ))
        return
    
    cart_text = "🛒 Ваша корзина:\n\n"
    total = 0
    
    for item in cart_items:
        cart_id, product_id, full_name, category, description, price, photo, quantity, wood_type, length, width, thickness = item
        item_total = price * quantity
        total += item_total
        cart_text += f"• {full_name}\n"
        if wood_type and wood_type != 'не указано':
            cart_text += f"  Тип: {wood_type}\n"
        if length and length != 'не указано':
            cart_text += f"  Длина: {length}\n"
        if width and width != 'не указано':
            cart_text += f"  Ширина: {width}\n"
        if thickness and thickness != 'не указано':
            cart_text += f"  Толщина: {thickness}\n"
        cart_text += f"  Цена: {price}₽ x {quantity} = {item_total}₽\n\n"
    
    cart_text += f"💰 Итого: {total}₽"
    
    await callback.message.edit_text(cart_text, reply_markup=get_cart_keyboard(cart_items))

@dp.callback_query(F.data == "subscription")
async def subscription_handler(callback: CallbackQuery):
    await callback.message.edit_text("🔔 Управление подпиской на уведомления:", reply_markup=get_subscription_keyboard())

@dp.callback_query(F.data == "manager")
async def manager_handler(callback: CallbackQuery):
    await callback.message.edit_text("📞 Связь с менеджером:", reply_markup=get_manager_keyboard())

@dp.callback_query(F.data == "channel")
async def channel_handler(callback: CallbackQuery):
    await callback.message.edit_text(f"📢 Подписывайтесь на наш Telegram канал:\n{CHANNEL_USERNAME}", 
                                   reply_markup=InlineKeyboardMarkup(
                                       inline_keyboard=[
                                           [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
                                           [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                                       ]
                                   ))

@dp.callback_query(F.data == "my_orders")
async def my_orders_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    orders = get_user_orders(user_id)
    
    if not orders:
        await callback.message.edit_text("📦 У вас еще нет покупок.", 
                                       reply_markup=InlineKeyboardMarkup(
                                           inline_keyboard=[
                                               [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
                                               [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                                           ]
                                       ))
        return
    
    orders_text = "📦 Ваши покупки:\n\n"
    
    for order in orders:
        order_id, order_date, status, created_at, items = order
        order_date_str = datetime.fromisoformat(order_date).strftime("%d.%m.%Y %H:%M") if order_date else "Не указана"
        created_at_str = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
        
        orders_text += f"Заказ #{order_id}\n"
        orders_text += f"Дата создания: {created_at_str}\n"
        orders_text += f"Дата получения: {order_date_str}\n"
        orders_text += f"Статус: {status}\n"
        orders_text += f"Товары: {items}\n"
        orders_text += "─" * 30 + "\n\n"
    
    await callback.message.edit_text(orders_text, 
                                   reply_markup=InlineKeyboardMarkup(
                                       inline_keyboard=[
                                           [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
                                           [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                                       ]
                                   ))

# Обработчики категорий и товаров
@dp.callback_query(F.data.startswith("category_"))
async def category_handler(callback: CallbackQuery, state: FSMContext):
    # Получаем текущее состояние
    current_state = await state.get_state()
    
    # Если админ находится в состоянии добавления товара
    if current_state == AddProductStates.waiting_for_category.state:
        await process_category_selection(callback, state)
        return
    
    # Если пользователь фильтрует товары
    if current_state == FilterStates.waiting_for_category.state:
        await process_filter_category(callback, state)
        return
    
    category_index = int(callback.data.split("_")[1])
    category = CATEGORIES[category_index]
    
    products = get_products_by_category(category)
    
    if not products:
        await callback.message.edit_text(
            f"В категории '{category}' пока нет товаров.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="catalog")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        )
        return
    
    await callback.message.edit_text(
        f"Категория: {category}\nВыберите товар:",
        reply_markup=get_products_keyboard(products, category_index)
    )

@dp.callback_query(F.data.startswith("products_prev_") | F.data.startswith("products_next_"))
async def pagination_handler(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    action = data_parts[1]
    category_index = int(data_parts[2])
    current_page = int(data_parts[3])
    
    category = CATEGORIES[category_index]
    products = get_products_by_category(category)
    
    if action == "prev":
        new_page = current_page - 1
    else:
        new_page = current_page + 1
    
    await callback.message.edit_text(
        f"Категория: {category}\nВыберите товар:",
        reply_markup=get_products_keyboard(products, category_index, new_page)
    )

@dp.callback_query(F.data.startswith("product_"))
async def product_detail_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = get_product_by_id(product_id)
    
    if not product:
        await callback.answer("Товар не найден!")
        return
    
    product_id, full_name, wood_type, category, length, width, thickness, price, description, photo, created_at = product
    
    product_text = f"🏷️ {full_name}\n\n"
    product_text += f"📂 Категория: {category}\n"
    if wood_type and wood_type != 'не указано':
        product_text += f"🌳 Тип древесины: {wood_type}\n"
    if length and length != 'не указано':
        product_text += f"📏 Длина: {length}\n"
    if width and width != 'не указано':
        product_text += f"📐 Ширина: {width}\n"
    if thickness and thickness != 'не указано':
        product_text += f"📏 Толщина: {thickness}\n"
    product_text += f"💰 Цена: {price}₽\n"
    product_text += f"📝 Описание: {description}"
    
    user_id = callback.from_user.id
    cart_items = get_cart(user_id)
    in_cart = any(item[1] == product_id for item in cart_items)
    
    if in_cart:
        product_text += "\n\n✅ Уже в корзине"
    
    try:
        await callback.message.delete()
        if photo:
            await callback.message.answer_photo(
                photo,
                caption=product_text,
                reply_markup=get_product_detail_keyboard(product_id, in_cart, False)
            )
        else:
            await callback.message.answer(
                product_text,
                reply_markup=get_product_detail_keyboard(product_id, in_cart, False)
            )
    except:
        await callback.message.edit_text(
            product_text,
            reply_markup=get_product_detail_keyboard(product_id, in_cart, False)
        )

@dp.callback_query(F.data == "back_to_products")
async def back_to_products_handler(callback: CallbackQuery):
    await callback.message.edit_text("Выберите категорию продукции:", reply_markup=get_categories_keyboard("main_menu"))

# Обработчики корзины
@dp.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    add_to_cart(user_id, product_id)
    
    await callback.answer("✅ Товар добавлен в корзину!")
    
    product = get_product_by_id(product_id)
    if product:
        product_id, full_name, wood_type, category, length, width, thickness, price, description, photo, created_at = product
        product_text = f"🏷️ {full_name}\n\n"
        product_text += f"📂 Категория: {category}\n"
        if wood_type and wood_type != 'не указано':
            product_text += f"🌳 Тип древесины: {wood_type}\n"
        if length and length != 'не указано':
            product_text += f"📏 Длина: {length}\n"
        if width and width != 'не указано':
            product_text += f"📐 Ширина: {width}\n"
        if thickness and thickness != 'не указано':
            product_text += f"📏 Толщина: {thickness}\n"
        product_text += f"💰 Цена: {price}₽\n"
        product_text += f"📝 Описание: {description}\n\n✅ В корзине"
        
        try:
            await callback.message.edit_caption(
                caption=product_text,
                reply_markup=get_product_detail_keyboard(product_id, True, False)
            )
        except:
            await callback.message.edit_text(
                product_text,
                reply_markup=get_product_detail_keyboard(product_id, True, False)
            )

@dp.callback_query(F.data.startswith("remove_"))
async def remove_from_cart_handler(callback: CallbackQuery):
    cart_id = int(callback.data.split("_")[1])
    remove_from_cart(cart_id)
    
    user_id = callback.from_user.id
    cart_items = get_cart(user_id)
    
    if not cart_items:
        await callback.message.edit_text("🛒 Ваша корзина пуста.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        ))
        return
    
    cart_text = "🛒 Ваша корзина:\n\n"
    total = 0
    
    for item in cart_items:
        cart_id, product_id, full_name, category, description, price, photo, quantity, wood_type, length, width, thickness = item
        item_total = price * quantity
        total += item_total
        cart_text += f"• {full_name}\n"
        if wood_type and wood_type != 'не указано':
            cart_text += f"  Тип: {wood_type}\n"
        if length and length != 'не указано':
            cart_text += f"  Длина: {length}\n"
        if width and width != 'не указано':
            cart_text += f"  Ширина: {width}\n"
        if thickness and thickness != 'не указано':
            cart_text += f"  Толщина: {thickness}\n"
        cart_text += f"  Цена: {price}₽ x {quantity} = {item_total}₽\n\n"
    
    cart_text += f"💰 Итого: {total}₽"
    
    await callback.message.edit_text(cart_text, reply_markup=get_cart_keyboard(cart_items))

@dp.callback_query(F.data == "clear_cart")
async def clear_cart_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_cart(user_id)
    
    await callback.message.edit_text("🛒 Ваша корзина очищена.", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    ))

@dp.callback_query(F.data == "checkout")
async def checkout_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📅 Введите дату и время, когда планируете забрать товар.\n"
        "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Например: 25.12.2024 14:30",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="cart")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        )
    )
    await state.set_state(CartStates.waiting_for_pickup_date)

@dp.message(CartStates.waiting_for_pickup_date)
async def process_pickup_date(message: types.Message, state: FSMContext):
    try:
        pickup_datetime = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        
        if pickup_datetime < datetime.now():
            await message.answer("Дата не может быть в прошлом. Пожалуйста, введите будущую дату:")
            return
        
        user_id = message.from_user.id
        
        order_id = create_order(user_id, pickup_datetime.isoformat())
        
        await message.answer(
            f"✅ Заказ #{order_id} успешно оформлен!\n\n"
            f"📅 Дата получения: {pickup_datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"📋 Статус: в работе\n\n"
            f"Вы можете отслеживать статус заказа в разделе 'Мои покупки'.",
            reply_markup=get_main_menu_keyboard()
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.12.2024 14:30",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="cart")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                ]
            )
        )

# Обработчики менеджера
@dp.callback_query(F.data == "call_manager")
async def call_manager_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        f"📞 Телефон менеджера:\n{MANAGER_PHONE}\n\n"
        "Нажмите на номер для звонка или скопируйте его.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="manager")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        )
    )

@dp.callback_query(F.data == "write_manager")
async def write_manager_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        f"✍️ Написать менеджеру:\n{MANAGER_USERNAME}\n\n"
        "Нажмите на ссылку, чтобы перейти в Telegram.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="manager")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        )
    )

# Обработчики подписки
@dp.callback_query(F.data == "subscribe")
async def subscribe_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    update_subscription(user_id, True)
    
    await callback.message.edit_text(
        "✅ Вы успешно подписались на уведомления!\n"
        "Теперь вы будете получать важные сообщения от бота.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="subscription")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        )
    )

@dp.callback_query(F.data == "unsubscribe")
async def unsubscribe_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    update_subscription(user_id, False)
    
    await callback.message.edit_text(
        "❌ Вы отписались от уведомления.\n"
        "Чтобы снова получать сообщения, нажмите 'Подписаться'.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="subscription")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        )
    )

# Обработчики админ-панели
@dp.callback_query(F.data == "admin_menu")
async def admin_menu_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text("Панель администратора:", reply_markup=get_admin_menu_keyboard())

@dp.callback_query(F.data == "admin_add_product")
async def admin_add_product_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "📝 Введите полное название товара:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(AddProductStates.waiting_for_full_name)

@dp.message(AddProductStates.waiting_for_full_name)
async def process_product_full_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    full_name = message.text.strip()
    if len(full_name) < 3:
        await message.answer(
            "❌ Название должно содержать минимум 3 символа. Введите полное название товара:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                    [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
                ]
            )
        )
        return
    
    await state.update_data(full_name=full_name)
    
    await message.answer(
        "🌳 Выберите тип древесины (или 'Нет типа' если не применимо):",
        reply_markup=get_wood_types_keyboard()
    )
    await state.set_state(AddProductStates.waiting_for_wood_type)

@dp.callback_query(AddProductStates.waiting_for_wood_type, F.data.startswith("wood_"))
async def process_wood_type_selection(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    wood_type = callback.data.split("_")[1]
    await state.update_data(wood_type=wood_type)
    
    await callback.message.edit_text(
        f"✅ Тип древесины: {wood_type if wood_type != 'не указано' else 'не указан'}\n\n"
        "📂 Выберите категорию товара:",
        reply_markup=get_categories_keyboard("admin_menu")
    )
    await state.set_state(AddProductStates.waiting_for_category)

@dp.callback_query(AddProductStates.waiting_for_category, F.data.startswith("category_"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    category_index = int(callback.data.split("_")[1])
    category = CATEGORIES[category_index]
    
    await state.update_data(category=category)
    
    await callback.message.edit_text(
        f"✅ Категория: {category}\n\n"
        "📏 Введите длину товара (например: 2000, 2400). Если не применимо, введите 'нет':",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(AddProductStates.waiting_for_length)

@dp.message(AddProductStates.waiting_for_length)
async def process_product_length(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    length = message.text.strip().lower()
    if length == 'нет':
        length = 'не указано'
    
    await state.update_data(length=length)
    
    await message.answer(
        f"✅ Длина: {length if length != 'не указано' else 'не указана'}\n\n"
        "📐 Введите ширину товара (например: 100, 150). Если не применимо, введите 'нет':",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(AddProductStates.waiting_for_width)

@dp.message(AddProductStates.waiting_for_width)
async def process_product_width(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    width = message.text.strip().lower()
    if width == 'нет':
        width = 'не указано'
    
    await state.update_data(width=width)
    
    await message.answer(
        f"✅ Ширина: {width if width != 'не указано' else 'не указана'}\n\n"
        "📏 Введите толщину товара (например: 20, 40). Если не применимо, введите 'нет':",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(AddProductStates.waiting_for_thickness)

@dp.message(AddProductStates.waiting_for_thickness)
async def process_product_thickness(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    thickness = message.text.strip().lower()
    if thickness == 'нет':
        thickness = 'не указано'
    
    await state.update_data(thickness=thickness)
    
    await message.answer(
        f"✅ Толщина: {thickness if thickness != 'не указано' else 'не указана'}\n\n"
        "💰 Введите цену товара (только число, например: 1500 или 2450.50):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(AddProductStates.waiting_for_price)

@dp.message(AddProductStates.waiting_for_price)
async def process_product_price(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    try:
        # Убираем возможные пробелы и заменяем запятую на точку
        price_text = message.text.strip().replace(",", ".")
        price = float(price_text)
        
        # Проверяем, что цена положительная
        if price <= 0:
            await message.answer(
                "❌ Цена должна быть больше нуля. Введите корректную цену:",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                        [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
                    ]
                )
            )
            return
            
        await state.update_data(price=price)
        
        await message.answer(
            "✅ Цена установлена!\n\n📝 Введите описание товара:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                    [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
                ]
            )
        )
        await state.set_state(AddProductStates.waiting_for_description)
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректную цену (только число):\n\nНапример: 1500 или 2450.50",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                    [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
                ]
            )
        )

@dp.message(AddProductStates.waiting_for_description)
async def process_product_description(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    description = message.text.strip()
    
    if not description or len(description) < 5:
        await message.answer(
            "❌ Описание должно содержать минимум 5 символов. Введите описание товара:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                    [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
                ]
            )
        )
        return
    
    await state.update_data(description=description)
    
    await message.answer(
        "✅ Описание добавлено!\n\n📷 Отправьте фото товара (или отправьте 'нет' если фото нет):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(AddProductStates.waiting_for_photo)

@dp.message(AddProductStates.waiting_for_photo, F.photo)
async def process_product_photo_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    photo_id = message.photo[-1].file_id
    
    data = await state.get_data()
    full_name = data.get('full_name', '')
    wood_type = data.get('wood_type', 'не указано')
    category = data.get('category', '')
    length = data.get('length', 'не указано')
    width = data.get('width', 'не указано')
    thickness = data.get('thickness', 'не указано')
    price = data.get('price', 0)
    description = data.get('description', '')
    
    product_id = add_product(full_name, wood_type, category, length, width, thickness, price, description, photo_id)
    
    await message.answer(
        f"✅ Товар успешно добавлен!\n\n"
        f"🏷️ Название: {full_name}\n"
        f"🌳 Тип древесины: {wood_type if wood_type != 'не указано' else 'не указан'}\n"
        f"📂 Категория: {category}\n"
        f"📏 Длина: {length if length != 'не указано' else 'не указана'}\n"
        f"📐 Ширина: {width if width != 'не указано' else 'не указана'}\n"
        f"📏 Толщина: {thickness if thickness != 'не указано' else 'не указана'}\n"
        f"💰 Цена: {price}₽\n"
        f"📝 Описание: {description}\n\n"
        f"ID товара: {product_id}",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()

@dp.message(AddProductStates.waiting_for_photo)
async def process_product_photo_text(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    if message.text.strip().lower() == 'нет':
        photo = None
    else:
        await message.answer(
            "❌ Пожалуйста, отправьте фото или введите 'нет' если фото нет:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                    [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
                ]
            )
        )
        return
    
    data = await state.get_data()
    full_name = data.get('full_name', '')
    wood_type = data.get('wood_type', 'не указано')
    category = data.get('category', '')
    length = data.get('length', 'не указано')
    width = data.get('width', 'не указано')
    thickness = data.get('thickness', 'не указано')
    price = data.get('price', 0)
    description = data.get('description', '')
    
    product_id = add_product(full_name, wood_type, category, length, width, thickness, price, description, photo)
    
    await message.answer(
        f"✅ Товар успешно добавлен!\n\n"
        f"🏷️ Название: {full_name}\n"
        f"🌳 Тип древесины: {wood_type if wood_type != 'не указано' else 'не указан'}\n"
        f"📂 Категория: {category}\n"
        f"📏 Длина: {length if length != 'не указано' else 'не указана'}\n"
        f"📐 Ширина: {width if width != 'не указано' else 'не указана'}\n"
        f"📏 Толщина: {thickness if thickness != 'не указано' else 'не указана'}\n"
        f"💰 Цена: {price}₽\n"
        f"📝 Описание: {description}\n\n"
        f"ID товара: {product_id}",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()

@dp.callback_query(F.data == "back_wood_types")
async def back_wood_types_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "📝 Введите полное название товара:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(AddProductStates.waiting_for_full_name)

@dp.callback_query(F.data == "admin_edit_product")
async def admin_edit_product_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    products = get_all_products()
    
    if not products:
        await callback.message.edit_text(
            "Товаров пока нет.",
            reply_markup=get_back_to_admin_keyboard()
        )
        return
    
    products_text = "Список товаров (ID - Название):\n\n"
    for product in products:
        product_id, full_name, wood_type, category, length, width, thickness, price, description, photo, created_at = product
        products_text += f"ID: {product_id} - {full_name[:50]}... - {price}₽\n"
        if wood_type and wood_type != 'не указано':
            products_text += f"  Тип древесины: {wood_type}\n"
    
    products_text += "\nВведите ID товара для редактирования:"
    
    await callback.message.edit_text(
        products_text,
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(EditProductStates.waiting_for_product_id)

@dp.callback_query(F.data == "admin_delete_product")
async def admin_delete_product_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    products = get_all_products()
    
    if not products:
        await callback.message.edit_text(
            "Товаров пока нет.",
            reply_markup=get_back_to_admin_keyboard()
        )
        return
    
    products_text = "Список товаров (ID - Название):\n\n"
    for product in products:
        product_id, full_name, wood_type, category, length, width, thickness, price, description, photo, created_at = product
        products_text += f"ID: {product_id} - {full_name[:50]}... - {price}₽\n"
    
    products_text += "\nВведите ID товара для удаления:"
    
    await callback.message.edit_text(
        products_text,
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(DeleteProductStates.waiting_for_product_id)

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_handler(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "Введите сообщение для рассылки всем подписчикам:",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_message)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    total_users = get_total_users()
    subscribers = len(get_all_subscribers())
    
    stats_text = (
        f"📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🔔 Подписчиков на уведомления: {subscribers}\n"
    )
    
    if total_users > 0:
        stats_text += f"📈 Охват подписок: {subscribers/total_users*100:.1f}%"
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_back_to_admin_keyboard()
    )

@dp.callback_query(F.data == "admin_visitors")
async def admin_visitors_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    visitors = get_today_visitors()
    
    await callback.message.edit_text(
        f"👥 Посещаемость сегодня: {visitors} пользователей",
        reply_markup=get_back_to_admin_keyboard()
    )

# Обработчики FSM для редактирования товара
@dp.message(EditProductStates.waiting_for_product_id)
async def process_edit_product_id(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    try:
        product_id = int(message.text)
        product = get_product_by_id(product_id)
        
        if not product:
            await message.answer(
                "Товар с таким ID не найден. Попробуйте снова:",
                reply_markup=get_back_to_admin_keyboard()
            )
            return
        
        await state.update_data(product_id=product_id)
        
        product_id, full_name, wood_type, category, length, width, thickness, price, description, photo, created_at = product
        
        product_info = (
            f"Товар ID: {product_id}\n"
            f"🏷️ Название: {full_name}\n"
            f"🌳 Тип древесины: {wood_type if wood_type and wood_type != 'не указано' else 'не указан'}\n"
            f"📂 Категория: {category}\n"
            f"📏 Длина: {length if length and length != 'не указано' else 'не указана'}\n"
            f"📐 Ширина: {width if width and width != 'не указано' else 'не указана'}\n"
            f"📏 Толщина: {thickness if thickness and thickness != 'не указано' else 'не указана'}\n"
            f"💰 Цена: {price}₽\n"
            f"📝 Описание: {description}\n"
        )
        
        await message.answer(
            f"{product_info}\nЧто вы хотите изменить?",
            reply_markup=get_edit_product_keyboard()
        )
        await state.set_state(EditProductStates.waiting_for_edit_choice)
        
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректный ID товара (число):",
            reply_markup=get_back_to_admin_keyboard()
        )

@dp.callback_query(EditProductStates.waiting_for_edit_choice, F.data == "edit_full_name")
async def process_edit_full_name(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "Введите новое полное название товара:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_product")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(EditProductStates.waiting_for_new_full_name)

@dp.message(EditProductStates.waiting_for_new_full_name)
async def process_new_full_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    full_name = message.text.strip()
    if len(full_name) < 3:
        await message.answer(
            "❌ Название должно содержать минимум 3 символа. Введите новое название товара:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_product")],
                    [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
                ]
            )
        )
        return
    
    data = await state.get_data()
    product_id = data.get('product_id')
    
    update_product_field(product_id, 'full_name', full_name)
    
    await message.answer(
        "✅ Название товара обновлено!",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()

@dp.callback_query(EditProductStates.waiting_for_edit_choice, F.data == "edit_wood_type")
async def process_edit_wood_type_choice(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "Выберите новый тип древесины (или 'Нет типа' если не применимо):",
        reply_markup=get_wood_types_keyboard()
    )
    await state.set_state(EditProductStates.waiting_for_new_wood_type)

@dp.callback_query(EditProductStates.waiting_for_new_wood_type, F.data.startswith("wood_"))
async def process_new_wood_type(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    wood_type = callback.data.split("_")[1]
    data = await state.get_data()
    product_id = data.get('product_id')
    
    update_product_field(product_id, 'wood_type', wood_type)
    
    await callback.message.edit_text(f"✅ Тип древесины обновлен: {wood_type if wood_type != 'не указано' else 'не указан'}")
    await callback.message.answer("Панель администратора:", reply_markup=get_admin_menu_keyboard())
    await state.clear()

@dp.callback_query(EditProductStates.waiting_for_edit_choice, F.data == "edit_category")
async def process_edit_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "Выберите новую категорию товара:",
        reply_markup=get_categories_keyboard("admin_menu")
    )
    await state.set_state(EditProductStates.waiting_for_new_category)

@dp.callback_query(EditProductStates.waiting_for_new_category, F.data.startswith("category_"))
async def process_new_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    category_index = int(callback.data.split("_")[1])
    category = CATEGORIES[category_index]
    data = await state.get_data()
    product_id = data.get('product_id')
    
    update_product_field(product_id, 'category', category)
    
    await callback.message.edit_text(f"✅ Категория обновлена: {category}")
    await callback.message.answer("Панель администратора:", reply_markup=get_admin_menu_keyboard())
    await state.clear()

@dp.callback_query(EditProductStates.waiting_for_edit_choice, F.data == "edit_length")
async def process_edit_length(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "Введите новую длину товара (например: 2000, 2400). Если не применимо, введите 'нет':",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_product")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(EditProductStates.waiting_for_new_length)

@dp.message(EditProductStates.waiting_for_new_length)
async def process_new_length(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    length = message.text.strip().lower()
    if length == 'нет':
        length = 'не указано'
    
    data = await state.get_data()
    product_id = data.get('product_id')
    
    update_product_field(product_id, 'length', length)
    
    await message.answer(
        f"✅ Длина обновлена: {length if length != 'не указано' else 'не указана'}",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()

@dp.callback_query(EditProductStates.waiting_for_edit_choice, F.data == "edit_width")
async def process_edit_width(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "Введите новую ширину товара (например: 100, 150). Если не применимо, введите 'нет':",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_product")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(EditProductStates.waiting_for_new_width)

@dp.message(EditProductStates.waiting_for_new_width)
async def process_new_width(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    width = message.text.strip().lower()
    if width == 'нет':
        width = 'не указано'
    
    data = await state.get_data()
    product_id = data.get('product_id')
    
    update_product_field(product_id, 'width', width)
    
    await message.answer(
        f"✅ Ширина обновлена: {width if width != 'не указано' else 'не указана'}",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()

@dp.callback_query(EditProductStates.waiting_for_edit_choice, F.data == "edit_thickness")
async def process_edit_thickness(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "Введите новую толщину товара (например: 20, 40). Если не применимо, введите 'нет':",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_product")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(EditProductStates.waiting_for_new_thickness)

@dp.message(EditProductStates.waiting_for_new_thickness)
async def process_new_thickness(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    thickness = message.text.strip().lower()
    if thickness == 'нет':
        thickness = 'не указано'
    
    data = await state.get_data()
    product_id = data.get('product_id')
    
    update_product_field(product_id, 'thickness', thickness)
    
    await message.answer(
        f"✅ Толщина обновлена: {thickness if thickness != 'не указано' else 'не указана'}",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()

@dp.callback_query(EditProductStates.waiting_for_edit_choice, F.data == "edit_price")
async def process_edit_price(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "Введите новую цену товара (только число):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_product")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(EditProductStates.waiting_for_new_price)

@dp.message(EditProductStates.waiting_for_new_price)
async def process_new_price(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    try:
        price = float(message.text.replace(",", "."))
        data = await state.get_data()
        product_id = data.get('product_id')
        
        update_product_field(product_id, 'price', price)
        
        await message.answer(
            "✅ Цена товара обновлена!",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректную цену (число):",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_product")],
                    [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
                ]
            )
        )

@dp.callback_query(EditProductStates.waiting_for_edit_choice, F.data == "edit_description")
async def process_edit_description(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "Введите новое описание товара:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_product")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(EditProductStates.waiting_for_new_description)

@dp.message(EditProductStates.waiting_for_new_description)
async def process_new_description(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    description = message.text
    data = await state.get_data()
    product_id = data.get('product_id')
    
    update_product_field(product_id, 'description', description)
    
    await message.answer(
        "✅ Описание товара обновлено!",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()

@dp.callback_query(EditProductStates.waiting_for_edit_choice, F.data == "edit_photo")
async def process_edit_photo(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text(
        "Отправьте новое фото товара (или отправьте 'нет' если фото нужно удалить):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_product")],
                [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
            ]
        )
    )
    await state.set_state(EditProductStates.waiting_for_new_photo)

@dp.message(EditProductStates.waiting_for_new_photo, F.photo)
async def process_new_photo_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    product_id = data.get('product_id')
    
    update_product_field(product_id, 'photo', photo_id)
    
    await message.answer(
        "✅ Фото товара обновлено!",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()

@dp.message(EditProductStates.waiting_for_new_photo)
async def process_new_photo_text(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    if message.text.strip().lower() == 'нет':
        photo = None
        data = await state.get_data()
        product_id = data.get('product_id')
        
        update_product_field(product_id, 'photo', photo)
        
        await message.answer(
            "✅ Фото товара удалено!",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            "❌ Пожалуйста, отправьте фото или введите 'нет' если фото нужно удалить:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_product")],
                    [InlineKeyboardButton(text="🏠 Админ панель", callback_data="admin_menu")]
                ]
            )
        )

# Обработчики FSM для удаления товара
@dp.message(DeleteProductStates.waiting_for_product_id)
async def process_delete_product_id(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    try:
        product_id = int(message.text)
        product = get_product_by_id(product_id)
        
        if not product:
            await message.answer(
                "Товар с таким ID не найден. Попробуйте снова:",
                reply_markup=get_back_to_admin_keyboard()
            )
            return
        
        delete_product(product_id)
        
        await message.answer(
            f"✅ Товар ID: {product_id} успешно удален!",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
        
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректный ID товара (число):",
            reply_markup=get_back_to_admin_keyboard()
        )

# Обработчики FSM для рассылки
@dp.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    subscribers = get_all_subscribers()
    
    if not subscribers:
        await message.answer(
            "Нет подписчиков для рассылки.",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
        return
    
    broadcast_text = message.text
    success_count = 0
    
    for user_id in subscribers:
        try:
            await bot.send_message(user_id, f"📢 Рассылка от Elite Wood:\n\n{broadcast_text}")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
    
    await message.answer(
        f"✅ Рассылка завершена!\n"
        f"Отправлено {success_count} из {len(subscribers)} подписчиков.",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()

@dp.callback_query(F.data == "admin_back_to_products")
async def admin_back_to_products_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора.")
        return
    
    await callback.message.edit_text("Выберите категорию:", reply_markup=get_categories_keyboard("admin_menu"))

# Функция для периодического обновления статусов заказов
async def update_orders_status():
    while True:
        update_order_status()
        await asyncio.sleep(3600)

# Основная функция
async def main():
    init_db()
    
    for admin_id in ADMIN_IDS:
        add_user(admin_id, None, "Администратор")
        add_admin(admin_id)
    
    asyncio.create_task(update_orders_status())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
