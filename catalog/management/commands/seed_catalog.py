"""
پر کردن دیتابیس فروشگاه با ۵۸ محصول نمونه (دسته‌بندی چند سطحی + برند + تنوع + تصویر)

اجرا:
    python manage.py seed_catalog
    python manage.py seed_catalog --reset
    python manage.py seed_catalog --no-images
"""

import random
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductVariant,
)

try:
    from PIL import Image as PILImage
    from PIL import ImageDraw
except ImportError:  # در صورت نصب نبودن Pillow تصویر ساخته نمی‌شود
    PILImage = None
    ImageDraw = None


# ------------------------------------------------------------------
# دسته‌بندی‌ها : (نام, slug, slug والد)
# ------------------------------------------------------------------
CATEGORIES = [
    # ریشه‌ها
    ("آرایشی", "makeup", None),
    ("مراقبت پوست", "skincare", None),
    ("مراقبت مو", "haircare", None),
    ("عطر و ادکلن", "fragrance", None),

    # زیرشاخه‌های آرایشی
    ("رژ لب", "lipstick", "makeup"),
    ("کرم پودر", "foundation", "makeup"),
    ("ریمل", "mascara", "makeup"),
    ("سایه چشم", "eyeshadow", "makeup"),
    ("رژ گونه", "blush", "makeup"),
    ("خط چشم", "eyeliner", "makeup"),

    # زیرشاخه‌های مراقبت پوست
    ("پاک‌کننده", "cleanser", "skincare"),
    ("مرطوب‌کننده", "moisturizer", "skincare"),
    ("سرم", "serum", "skincare"),
    ("ضد آفتاب", "sunscreen", "skincare"),

    # زیرشاخه‌های مراقبت مو
    ("شامپو", "shampoo", "haircare"),
    ("نرم‌کننده مو", "conditioner", "haircare"),

    # زیرشاخه عطر
    ("ادکلن", "perfume", "fragrance"),
]


# ------------------------------------------------------------------
# برندها
# ------------------------------------------------------------------
BRANDS = [
    ("میبلین", "maybelline"),
    ("لورآل", "loreal"),
    ("نیوآ", "nivea"),
    ("مک", "mac"),
    ("کلینیک", "clinique"),
    ("د اوردینری", "the-ordinary"),
    ("سراوی", "cerave"),
    ("گارنیه", "garnier"),
    ("اسنس", "essence"),
    ("نیکس", "nyx"),
    ("بورژوآ", "bourjois"),
    ("ریمل لندن", "rimmel"),
    ("هودا بیوتی", "huda-beauty"),
    ("فنی بیوتی", "fenty-beauty"),
    ("لانکوم", "lancome"),
    ("استی لودر", "estee-lauder"),
    ("سینره", "cinere"),
    ("سریتا", "seirita"),
]


# ------------------------------------------------------------------
# توضیحات و ویژگی‌ها به تفکیک زیردسته (برای متن واقعی‌تر)
# ------------------------------------------------------------------
CATEGORY_DESCRIPTIONS = {
    "lipstick": "رژ لبی با بافت مخملی و پوشش‌دهی کامل که رنگدانه‌های آن ماندگاری بالایی روی لب دارند و از خشکی لب جلوگیری می‌کنند.",
    "foundation": "کرم پودری با پوشش متوسط تا بالا که بافت پوست را یکدست می‌کند، منافذ را کم‌رنگ می‌سازد و در طول روز بدون اکسید شدن روی پوست می‌ماند.",
    "mascara": "ریملی با فرمول حجم‌دهنده که مژه‌ها را از ریشه بلند و پرپشت نشان می‌دهد و بدون ایجاد گلوله، مژه‌ها را از هم جدا نگه می‌دارد.",
    "eyeshadow": "سایه‌ای با پیگمنت بالا و پخش‌پذیری نرم که به‌راحتی محو می‌شود و ماندگاری خوبی روی پلک دارد.",
    "blush": "رژ گونه‌ای با رنگدانه‌های نرم که به پوست حالت طبیعی و شاداب می‌بخشد و روی انواع تناژ پوستی زیبا می‌نشیند.",
    "eyeliner": "خط چشمی با نوک دقیق و رنگ عمیق که خطی یکدست و ماندگار می‌کشد و در طول روز پخش نمی‌شود.",
    "cleanser": "شوینده‌ای ملایم با pH متعادل که آلودگی، چربی اضافه و باقی‌مانده آرایش را پاک می‌کند، بدون آن‌که سد دفاعی پوست را تخریب کند.",
    "moisturizer": "مرطوب‌کننده‌ای با ترکیبات آبرسان که رطوبت را در لایه‌های پوست حفظ می‌کند و بافت پوست را نرم و صاف نشان می‌دهد.",
    "serum": "سرمی با غلظت بالای مواد مؤثره که به‌سرعت جذب پوست می‌شود و برای رفع مشکلات خاص پوستی طراحی شده است.",
    "sunscreen": "ضد آفتابی با فیلترهای وسیع‌الطیف UVA/UVB که از پوست در برابر لک، پیری زودرس و آفتاب‌سوختگی محافظت می‌کند.",
    "shampoo": "شامپویی با فرمول ملایم که مو را از آلودگی پاک می‌کند، چربی سر را متعادل نگه می‌دارد و حجم طبیعی مو را حفظ می‌کند.",
    "conditioner": "نرم‌کننده‌ای که مو را باز می‌کند، درخشندگی می‌بخشد و از موخوره و شکنندگی ساقه مو جلوگیری می‌کند.",
    "perfume": "عطری با رایحه‌ای ماندگار و ترکیبات اصیل که در طول روز روی پوست و لباس حفظ می‌شود.",
}

FEATURES = {
    "lipstick": ["پوشش‌دهی بالا فقط با یک لایه", "بافت مات و مخملی", "حاوی ویتامین E و روغن‌های مغذی"],
    "foundation": ["ماندگاری طولانی بدون اکسید شدن", "بافت سبک و قابل لایه‌بندی", "مناسب انواع پوست"],
    "mascara": ["افکت حجم‌دهی و بلندکنندگی", "فرمول ضدآب و ضد ریزش", "براش جداکننده مژه"],
    "eyeshadow": ["پیگمنت بالا و پخش‌پذیری آسان", "قابل استفاده خشک و مرطوب", "بدون ریزش پودر"],
    "blush": ["رنگ‌دهی طبیعی و قابل لایه‌بندی", "بافت پودری نرم", "ماندگاری طولانی"],
    "eyeliner": ["نوک ماژیکی دقیق", "رنگ مشکی عمیق", "خشک شدن سریع و ضدآب"],
    "cleanser": ["بدون صابون و بدون سولفات", "مناسب پوست حساس", "حفظ رطوبت طبیعی پوست"],
    "moisturizer": ["جذب سریع و بدون چربی", "آبرسانی ۲۴ ساعته", "مناسب استفاده صبح و شب"],
    "serum": ["غلظت بالای ماده مؤثره", "بافت سبک و بدون چربی", "قابل استفاده زیر مرطوب‌کننده"],
    "sunscreen": ["SPF بالا و طیف وسیع", "بدون آثار سفیدی", "مناسب زیر آرایش"],
    "shampoo": ["بدون سولفات قوی", "مناسب استفاده روزانه", "کنترل چربی و شوره"],
    "conditioner": ["نرم‌کنندگی فوری", "کاهش موخوره", "افزایش درخشندگی مو"],
    "perfume": ["رایحه ماندگار و پخش‌شوندگی خوب", "مناسب استفاده روزانه و مجلسی", "بسته‌بندی اصیل"],
}


# ------------------------------------------------------------------
# محصولات
#   - برای محصولات آرایشی از کلید "shades" (لیست نام تنوع) + "price" استفاده شده
#   - برای محصولات پوست/مو/عطر از کلید "variants" (نام، قیمت) استفاده شده
# ------------------------------------------------------------------
PRODUCTS = [
    # ==================== رژ لب ====================
    {
        "name": "رژ لب مایع مات میبلین سوپراستی ماتی اینک",
        "slug": "maybelline-superstay-matte-ink",
        "category": "lipstick", "brand": "maybelline", "price": 520000,
        "shades": ["01 نود صورتی", "02 رز کلاسیک", "03 قرمز آتشین", "04 شرابی", "05 کورال"],
    },
    {
        "name": "رژ لب جامد مات مک",
        "slug": "mac-matte-lipstick",
        "category": "lipstick", "brand": "mac", "price": 1450000,
        "shades": ["Russian Red", "Velvet Teddy", "Ruby Woo", "Chili"],
    },
    {
        "name": "رژ لب کرمی لورآل کلر ریش",
        "slug": "loreal-color-riche-lipstick",
        "category": "lipstick", "brand": "loreal", "price": 780000,
        "shades": ["نود 01", "رز 02", "قرمز 03"],
    },
    {
        "name": "رژ لب مایع مات هودا بیوتی",
        "slug": "huda-beauty-liquid-matte",
        "category": "lipstick", "brand": "huda-beauty", "price": 1650000,
        "shades": ["Bombshell", "Icon", "Trendsetter", "Material Girl"],
    },
    {
        "name": "رژ لب مایع فنی بیوتی استانا لیپ پینت",
        "slug": "fenty-beauty-stunna-lip-paint",
        "category": "lipstick", "brand": "fenty-beauty", "price": 1900000,
        "shades": ["Uncensored", "Unbutton", "Unveil"],
    },
    {
        "name": "مداد رژ لب نیکس اسلیم لیپ پنسیل",
        "slug": "nyx-slim-lip-pencil",
        "category": "lipstick", "brand": "nyx", "price": 380000,
        "shades": ["Nude", "Rose", "Red"],
    },
    {
        "name": "رژ لب مات ریمل لندن لستینگ فینیش",
        "slug": "rimmel-lasting-finish-lipstick",
        "category": "lipstick", "brand": "rimmel", "price": 420000,
        "shades": ["Kate 01", "Kate 03", "Kate 08"],
    },
    {
        "name": "بالم رژ لب بورژوآ",
        "slug": "bourjois-lip-balm",
        "category": "lipstick", "brand": "bourjois", "price": 350000,
        "shades": ["صورتی", "کورال"],
    },

    # ==================== کرم پودر ====================
    {
        "name": "کرم پودر میبلین فیت می",
        "slug": "maybelline-fit-me-foundation",
        "category": "foundation", "brand": "maybelline", "price": 690000,
        "shades": ["110 Ivory", "120 Classic Ivory", "128 Warm Nude", "220 Natural Beige"],
    },
    {
        "name": "کرم پودر لورآل ترو مچ",
        "slug": "loreal-true-match-foundation",
        "category": "foundation", "brand": "loreal", "price": 1150000,
        "shades": ["1.N Ivory", "2.N Vanilla", "3.N Creamy Beige", "4.D Golden"],
    },
    {
        "name": "کرم پودر مک استودیو فیکس فلوید",
        "slug": "mac-studio-fix-fluid",
        "category": "foundation", "brand": "mac", "price": 2100000,
        "shades": ["NC15", "NC25", "NC35", "NW20"],
    },
    {
        "name": "کرم پودر لانکوم تینت آیدول اولترا ور",
        "slug": "lancome-teint-idole-ultra-wear",
        "category": "foundation", "brand": "lancome", "price": 2800000,
        "shades": ["005 Beige", "010 Beige", "025 Beige"],
    },
    {
        "name": "کرم پودر فنی بیوتی پرو فیلتر",
        "slug": "fenty-beauty-pro-filt-r",
        "category": "foundation", "brand": "fenty-beauty", "price": 2450000,
        "shades": ["110", "150", "220", "300"],
    },
    {
        "name": "کرم پودر مدادی اسنس کاور استیک",
        "slug": "essence-cover-stick",
        "category": "foundation", "brand": "essence", "price": 320000,
        "shades": ["Light", "Medium", "Deep"],
    },

    # ==================== ریمل ====================
    {
        "name": "ریمل میبلین لش سنسیشنال",
        "slug": "maybelline-lash-sensational",
        "category": "mascara", "brand": "maybelline", "price": 480000,
        "shades": ["مشکی", "مشکی ضدآب"],
    },
    {
        "name": "ریمل لورآل لش پارادایز",
        "slug": "loreal-lash-paradise",
        "category": "mascara", "brand": "loreal", "price": 720000,
        "shades": ["مشکی", "قهوه‌ای"],
    },
    {
        "name": "ریمل اسنس لش پرینسس",
        "slug": "essence-lash-princess",
        "category": "mascara", "brand": "essence", "price": 240000,
        "shades": ["مشکی"],
    },
    {
        "name": "ریمل ریمل لندن اسکاندال آیز",
        "slug": "rimmel-scandaleyes-mascara",
        "category": "mascara", "brand": "rimmel", "price": 390000,
        "shades": ["مشکی", "مشکی ضدآب"],
    },
    {
        "name": "ریمل لانکوم مسیو بیگ",
        "slug": "lancome-monsieur-big-mascara",
        "category": "mascara", "brand": "lancome", "price": 1900000,
        "shades": ["مشکی"],
    },

    # ==================== سایه چشم ====================
    {
        "name": "پالت سایه چشم نیکس اولتیمیت",
        "slug": "nyx-ultimate-shadow-palette",
        "category": "eyeshadow", "brand": "nyx", "price": 1250000,
        "shades": ["Warm Neutrals", "Cool Neutrals", "Brights"],
    },
    {
        "name": "پالت سایه چشم هودا بیوتی رز گلد",
        "slug": "huda-beauty-rose-gold-palette",
        "category": "eyeshadow", "brand": "huda-beauty", "price": 2650000,
        "shades": ["Rose Gold", "New Nude"],
    },
    {
        "name": "سایه چشم تک مک",
        "slug": "mac-single-eyeshadow",
        "category": "eyeshadow", "brand": "mac", "price": 890000,
        "shades": ["All That Glitters", "Satin Taupe", "Woodwinked"],
    },
    {
        "name": "پالت سایه چشم اسنس",
        "slug": "essence-eyeshadow-palette",
        "category": "eyeshadow", "brand": "essence", "price": 280000,
        "shades": ["Nude", "Rose"],
    },
    {
        "name": "سایه چشم کرمی بورژوآ",
        "slug": "bourjois-cream-eyeshadow",
        "category": "eyeshadow", "brand": "bourjois", "price": 340000,
        "shades": ["طلایی", "نقره‌ای"],
    },

    # ==================== رژ گونه ====================
    {
        "name": "رژ گونه میبلین فیت می بلاش",
        "slug": "maybelline-fit-me-blush",
        "category": "blush", "brand": "maybelline", "price": 450000,
        "shades": ["Rose", "Peach", "Coral"],
    },
    {
        "name": "رژ گونه پودری مک",
        "slug": "mac-powder-blush",
        "category": "blush", "brand": "mac", "price": 1350000,
        "shades": ["Melba", "Peaches", "Fleur Power"],
    },
    {
        "name": "رژ گونه مایع فنی بیوتی چیکس اوت",
        "slug": "fenty-beauty-cheeks-out",
        "category": "blush", "brand": "fenty-beauty", "price": 1750000,
        "shades": ["Rosé", "Daiquiri Dip", "Bikini Martini"],
    },
    {
        "name": "رژ گونه اسنس سیلک تاچ",
        "slug": "essence-silk-touch-blush",
        "category": "blush", "brand": "essence", "price": 210000,
        "shades": ["10 Satin Peach", "20 Satin Coral"],
    },

    # ==================== خط چشم ====================
    {
        "name": "خط چشم ماژیکی نیکس اپیک اینک",
        "slug": "nyx-epic-ink-liner",
        "category": "eyeliner", "brand": "nyx", "price": 460000,
        "shades": ["مشکی", "قهوه‌ای"],
    },
    {
        "name": "خط چشم ریمل لندن اسکاندال آیز",
        "slug": "rimmel-scandaleyes-liner",
        "category": "eyeliner", "brand": "rimmel", "price": 350000,
        "shades": ["مشکی", "مشکی ضدآب"],
    },
    {
        "name": "مداد چشم مک آی کوهل",
        "slug": "mac-eye-kohl",
        "category": "eyeliner", "brand": "mac", "price": 780000,
        "shades": ["Teddy", "Smolder"],
    },

    # ==================== پاک‌کننده ====================
    {
        "name": "فوم شوینده صورت سینره",
        "slug": "cinere-foam-cleanser",
        "category": "cleanser", "brand": "cinere",
        "variants": [("۱۵۰ میلی‌لیتر", 320000), ("۲۰۰ میلی‌لیتر", 420000)],
    },
    {
        "name": "ژل شوینده کف‌ساز سراوی",
        "slug": "cerave-foaming-cleanser",
        "category": "cleanser", "brand": "cerave",
        "variants": [("۲۳۶ میلی‌لیتر", 890000), ("۴۷۳ میلی‌لیتر", 1450000)],
    },
    {
        "name": "میسلار واتر گارنیه",
        "slug": "garnier-micellar-water",
        "category": "cleanser", "brand": "garnier",
        "variants": [("۴۰۰ میلی‌لیتر", 480000), ("۷۰۰ میلی‌لیتر", 690000)],
    },
    {
        "name": "پاک‌کننده آرایش چشم لورآل",
        "slug": "loreal-eye-makeup-remover",
        "category": "cleanser", "brand": "loreal",
        "variants": [("۱۲۵ میلی‌لیتر", 540000)],
    },

    # ==================== مرطوب‌کننده ====================
    {
        "name": "کرم مرطوب‌کننده سراوی مویسچرایزینگ کرم",
        "slug": "cerave-moisturizing-cream",
        "category": "moisturizer", "brand": "cerave",
        "variants": [("۳۴۰ گرم", 980000), ("۴۵۴ گرم", 1250000)],
    },
    {
        "name": "کرم مرطوب‌کننده نیوآ سافت",
        "slug": "nivea-soft-cream",
        "category": "moisturizer", "brand": "nivea",
        "variants": [("۷۵ میلی‌لیتر", 250000), ("۱۵۰ میلی‌لیتر", 390000)],
    },
    {
        "name": "کرم آبرسان کلینیک مویسچر سورج",
        "slug": "clinique-moisture-surge",
        "category": "moisturizer", "brand": "clinique",
        "variants": [("۵۰ میلی‌لیتر", 1850000)],
    },
    {
        "name": "کرم پانتنول سینره",
        "slug": "cinere-panthenol-cream",
        "category": "moisturizer", "brand": "cinere",
        "variants": [("۵۰ میلی‌لیتر", 290000)],
    },
    {
        "name": "لوسیون مرطوب‌کننده سریتا",
        "slug": "seirita-moisturizing-lotion",
        "category": "moisturizer", "brand": "seirita",
        "variants": [("۱۰۰ میلی‌لیتر", 360000)],
    },

    # ==================== سرم ====================
    {
        "name": "سرم ویتامین C د اوردینری",
        "slug": "the-ordinary-vitamin-c-serum",
        "category": "serum", "brand": "the-ordinary",
        "variants": [("۳۰ میلی‌لیتر", 780000)],
    },
    {
        "name": "سرم نیاسینامید ۱۰٪ د اوردینری",
        "slug": "the-ordinary-niacinamide-serum",
        "category": "serum", "brand": "the-ordinary",
        "variants": [("۳۰ میلی‌لیتر", 620000)],
    },
    {
        "name": "سرم هیالورونیک اسید د اوردینری",
        "slug": "the-ordinary-hyaluronic-serum",
        "category": "serum", "brand": "the-ordinary",
        "variants": [("۳۰ میلی‌لیتر", 690000)],
    },
    {
        "name": "سرم شب کلینیک",
        "slug": "clinique-night-serum",
        "category": "serum", "brand": "clinique",
        "variants": [("۳۰ میلی‌لیتر", 2200000)],
    },
    {
        "name": "سرم ضد لک سریتا",
        "slug": "seirita-anti-spot-serum",
        "category": "serum", "brand": "seirita",
        "variants": [("۳۰ میلی‌لیتر", 420000)],
    },

    # ==================== ضد آفتاب ====================
    {
        "name": "ضد آفتاب سینره SPF50",
        "slug": "cinere-sunscreen-spf50",
        "category": "sunscreen", "brand": "cinere",
        "variants": [("۵۰ میلی‌لیتر", 480000)],
    },
    {
        "name": "ضد آفتاب لورآل SPF50",
        "slug": "loreal-sunscreen-spf50",
        "category": "sunscreen", "brand": "loreal",
        "variants": [("۵۰ میلی‌لیتر", 850000)],
    },
    {
        "name": "ضد آفتاب سراوی SPF30",
        "slug": "cerave-sunscreen-spf30",
        "category": "sunscreen", "brand": "cerave",
        "variants": [("۵۲ میلی‌لیتر", 1150000)],
    },
    {
        "name": "ضد آفتاب نیوآ SPF50",
        "slug": "nivea-sun-spf50",
        "category": "sunscreen", "brand": "nivea",
        "variants": [("۷۵ میلی‌لیتر", 390000)],
    },

    # ==================== شامپو ====================
    {
        "name": "شامپو ضد ریزش سریتا",
        "slug": "seirita-anti-hairloss-shampoo",
        "category": "shampoo", "brand": "seirita",
        "variants": [("۲۵۰ میلی‌لیتر", 340000), ("۴۰۰ میلی‌لیتر", 490000)],
    },
    {
        "name": "شامپو گارنیه",
        "slug": "garnier-shampoo",
        "category": "shampoo", "brand": "garnier",
        "variants": [("۴۰۰ میلی‌لیتر", 280000)],
    },
    {
        "name": "شامپو نیوآ",
        "slug": "nivea-shampoo",
        "category": "shampoo", "brand": "nivea",
        "variants": [("۲۵۰ میلی‌لیتر", 260000)],
    },

    # ==================== نرم‌کننده مو ====================
    {
        "name": "نرم‌کننده مو گارنیه",
        "slug": "garnier-conditioner",
        "category": "conditioner", "brand": "garnier",
        "variants": [("۴۰۰ میلی‌لیتر", 290000)],
    },
    {
        "name": "ماسک مو سینره",
        "slug": "cinere-hair-mask",
        "category": "conditioner", "brand": "cinere",
        "variants": [("۵۰۰ گرم", 410000)],
    },

    # ==================== ادکلن ====================
    {
        "name": "ادکلن لانکوم لا وی بوت",
        "slug": "lancome-la-vie-est-belle",
        "category": "perfume", "brand": "lancome",
        "variants": [("۵۰ میلی‌لیتر", 5800000), ("۱۰۰ میلی‌لیتر", 8900000)],
    },
    {
        "name": "عطر استی لودر پلژرز",
        "slug": "estee-lauder-pleasures",
        "category": "perfume", "brand": "estee-lauder",
        "variants": [("۵۰ میلی‌لیتر", 4200000)],
    },
    {
        "name": "عطر فنی بیوتی",
        "slug": "fenty-beauty-perfume",
        "category": "perfume", "brand": "fenty-beauty",
        "variants": [("۵۰ میلی‌لیتر", 3600000)],
    },
    {
        "name": "عطر نیوآ",
        "slug": "nivea-perfume",
        "category": "perfume", "brand": "nivea",
        "variants": [("۳۰ میلی‌لیتر", 950000)],
    },
]


# رنگ تصویر پیش‌فرض هر زیردسته
CATEGORY_COLORS = {
    "lipstick": (196, 62, 90),
    "foundation": (214, 176, 143),
    "mascara": (48, 48, 56),
    "eyeshadow": (146, 108, 156),
    "blush": (232, 141, 150),
    "eyeliner": (60, 60, 70),
    "cleanser": (150, 200, 190),
    "moisturizer": (170, 210, 220),
    "serum": (200, 190, 230),
    "sunscreen": (240, 200, 120),
    "shampoo": (200, 160, 120),
    "conditioner": (190, 170, 140),
    "perfume": (170, 130, 190),
}


class Command(BaseCommand):
    help = "پر کردن دیتابیس کاتالوگ با داده‌های نمونه (بیش از ۵۰ محصول)"

    # ------------------------------------------------------------------
    # آرگومان‌های خط فرمان
    # ------------------------------------------------------------------
    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="پاک کردن کامل داده‌های کاتالوگ قبل از درج مجدد",
        )
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="ساخت تصاویر نمونه را غیرفعال کن",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        random.seed(2024)  # خروجی تکرارپذیر

        if options["reset"]:
            self.reset_catalog()
            self.stdout.write(self.style.WARNING("داده‌های قبلی کاتالوگ پاک شد."))

        categories = self.seed_categories()
        brands = self.seed_brands()
        product_count, variant_count, image_count = self.seed_products(
            categories, brands, with_images=not options["no_images"]
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ پایان موفق!\n"
                f"   دسته‌بندی‌ها : {len(categories)}\n"
                f"   برندها       : {len(brands)}\n"
                f"   محصولات      : {product_count}\n"
                f"   تنوع‌ها (Variant): {variant_count}\n"
                f"   تصاویر       : {image_count}\n"
            )
        )

    # ------------------------------------------------------------------
    # پاک‌سازی (ترتیب مهم است چون FKها PROTECT هستند)
    # ------------------------------------------------------------------
    def reset_catalog(self):
        for image in ProductImage.objects.all():
            image.image.delete(save=False)
        ProductImage.objects.all().delete()
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.filter(parent__isnull=False).delete()
        Category.objects.filter(parent__isnull=True).delete()
        Brand.objects.all().delete()

    # ------------------------------------------------------------------
    # دسته‌بندی‌ها
    # ------------------------------------------------------------------
    def seed_categories(self):
        categories = {}
        for name, slug, parent_slug in CATEGORIES:
            parent = categories.get(parent_slug)
            obj, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "parent": parent, "is_active": True},
            )
            categories[slug] = obj
        return categories

    # ------------------------------------------------------------------
    # برندها
    # ------------------------------------------------------------------
    def seed_brands(self):
        brands = {}
        for name, slug in BRANDS:
            obj, _ = Brand.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "is_active": True},
            )
            brands[slug] = obj
        return brands

    # ------------------------------------------------------------------
    # محصولات + تنوع‌ها + تصاویر
    # ------------------------------------------------------------------
    def seed_products(self, categories, brands, with_images=True):
        products = variants = images = 0

        for data in PRODUCTS:
            product, _ = Product.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "description": self.build_description(data),
                    "category": categories[data["category"]],
                    "brand": brands[data["brand"]],
                    "is_active": True,
                },
            )
            products += 1

            sku_prefix = data["slug"].upper().replace("-", "")[:40]
            for index, (variant_name, price) in enumerate(
                self.build_variants(data), start=1
            ):
                stock = 0 if random.random() < 0.08 else random.randint(3, 90)
                ProductVariant.objects.update_or_create(
                    sku=f"{sku_prefix}-{index:02d}",
                    defaults={
                        "product": product,
                        "name": variant_name,
                        "price": Decimal(price),
                        "stock": stock,
                        "is_active": True,
                    },
                )
                variants += 1

            # فقط اگر محصول هنوز تصویری ندارد (اجرای دوباره فایل تکراری نسازد)
            if with_images and PILImage is not None and not product.images.exists():
                images += self.attach_images(product)

        return products, variants, images

    # ------------------------------------------------------------------
    def build_variants(self, data):
        """لیست (نام تنوع، قیمت) را برمی‌گرداند."""
        if "variants" in data:
            return [(name, price) for name, price in data["variants"]]

        price = Decimal(str(data["price"]))
        names = data.get("shades") or [data["name"]]
        return [(name, price) for name in names]

    # ------------------------------------------------------------------
    def build_description(self, data):
        category_slug = data["category"]
        base = CATEGORY_DESCRIPTIONS.get(category_slug, "")
        features = FEATURES.get(category_slug, [])
        features_text = "\n".join(f"• {item}" for item in features)

        return (
            f"{data['name']}\n\n"
            f"{base}\n\n"
            f"ویژگی‌های کلیدی:\n{features_text}\n\n"
            f"شرایط نگهداری: دور از تابش مستقیم نور خورشید و در دمای اتاق نگهداری شود."
        )

    # ------------------------------------------------------------------
    # تصاویر نمونه
    # ------------------------------------------------------------------
    def attach_images(self, product):
        base_color = CATEGORY_COLORS.get(
            product.category.slug, (205, 205, 205)
        )
        count = 3 if random.random() < 0.4 else 2
        created = 0

        for index in range(count):
            content = self.render_image(base_color)
            product_image = ProductImage(
                product=product,
                alt_text=f"{product.name} - تصویر {index + 1}",
                is_primary=(index == 0),
                sort_order=index,
            )
            product_image.image.save(
                f"{product.slug}-{index + 1}.jpg", content, save=False
            )
            product_image.save()
            created += 1

        return created

    # ------------------------------------------------------------------
    def render_image(self, base_color):
        """ساخت یک تصویر JPEG ساده با رنگ‌بندی مربوط به دسته‌بندی"""
        size = 900
        image = PILImage.new("RGB", (size, size), base_color)
        draw = ImageDraw.Draw(image)

        # دایره‌های محو برای جذاب‌تر شدن تصویر
        for _ in range(7):
            radius = random.randint(120, 380)
            cx = random.randint(-100, size + 100)
            cy = random.randint(-100, size + 100)
            tint = tuple(
                max(0, min(255, channel + random.randint(-45, 55)))
                for channel in base_color
            )
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                fill=tint,
            )

        # قاب سفید
        border = 40
        draw.rectangle(
            [border, border, size - border, size - border],
            outline=(255, 255, 255),
            width=8,
        )

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=88)
        return ContentFile(buffer.getvalue())