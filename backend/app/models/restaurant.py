from app.core.types import UTCDateTime
"""
Restoran, Sozlamalar va Dizayn Temalari modellari
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    Text, ForeignKey, func, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL uchun
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)

    # Developer komissiyasi
    commission_percent = Column(Float, default=5.0)
    total_revenue = Column(Float, default=0.0)       # Umumiy daromad
    total_commission = Column(Float, default=0.0)    # To'langan komissiya

    created_at = Column(UTCDateTime(), server_default=func.now())
    updated_at = Column(UTCDateTime(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="restaurant", foreign_keys="User.restaurant_id")
    tables = relationship("Table", back_populates="restaurant", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="restaurant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="restaurant")
    settings = relationship("RestaurantSettings", back_populates="restaurant", uselist=False,
                           cascade="all, delete-orphan")
    commission_logs = relationship("CommissionLog", back_populates="restaurant")
    debts = relationship("Debt", back_populates="restaurant", cascade="all, delete-orphan")
    receipt_archives = relationship("ReceiptArchive", back_populates="restaurant", cascade="all, delete-orphan")
    shift_reports = relationship("ShiftReport", back_populates="restaurant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Restaurant {self.name}>"


class RestaurantSettings(Base):
    __tablename__ = "restaurant_settings"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"),
                          unique=True, nullable=False)

    # Narxlarni ko'rsatish/yashirish
    show_prices = Column(Boolean, default=True)

    # Buyurtma berish imkoni (QR menyudan mijoz buyurtma bera oladimi)
    allow_orders = Column(Boolean, default=False)
    allow_orders_from_qr = Column(Boolean, default=False)

    # Ofitsiant chaqirish imkoni
    allow_call_waiter = Column(Boolean, default=True)

    # Izoh qoldirish imkoni
    allow_reviews = Column(Boolean, default=True)

    # Xizmat haqi foizi (Admin paneldan o'zgartiriladi: masalan 12%, 13%)
    service_fee_percent = Column(Float, default=12.0)

    # Chek sozlamalari (Xprinter uchun)
    receipt_header = Column(String(200), default="Dunyo Choyxonasi", nullable=True)
    receipt_footer = Column(String(500), default="Tashrifingiz uchun rahmat! Dunyo Choyxonasi (+998884593400)")
    receipt_address = Column(String(500), default="Xorazm viloyati, Xiva tumani", nullable=True)
    receipt_phone = Column(String(50), default="+998884593400", nullable=True)
    receipt_wifi_pass = Column(String(100), nullable=True)
    # Kirill kod sahifasi raqami (ESC t n). Epson standartida PC866 = 17,
    # lekin ba'zi Xprinter modellarida boshqacha. Chek tushunarsiz yoki
    # ieroglif bo'lib chiqsa, shu raqamni o'zgartirib ko'riladi.
    printer_codepage = Column(Integer, default=17)
    printer_paper_width = Column(Integer, default=80)  # 58 yoki 80 mm
    # Chek shrifti o'lchami: "normal" | "katta" | "juda_katta"
    # Keksa odamlar o'qiy olishi uchun "katta" tavsiya etiladi.
    printer_font_size = Column(String(20), default="katta", nullable=True)
    # Harflar orasidagi masofa (nuqta). Termal printerda harflar
    # bir-biriga yopishib chiqadi — keksa odamga o'qish qiyin.
    printer_char_spacing = Column(Integer, default=1, nullable=True)
    # Qatorlar orasidagi masofa: zich / oddiy / keng / juda_keng
    printer_line_spacing = Column(String(20), default="oddiy", nullable=True)

    # Cheklar arxivini saqlash muddati (yillarda, default: 3 yil)
    archive_retention_years = Column(Integer, default=3)

    # Qarz (Nasiya) tizimini yoqish/o'chirish
    allow_debt_payment = Column(Boolean, default=True)

    # Telegram bot orqali bildirishnomalar (Ofitsiant chaqiruvlari & buyurtmalar)
    enable_telegram_notifications = Column(Boolean, default=False)
    telegram_bot_token = Column(String(255), nullable=True)
    telegram_chat_id = Column(String(100), nullable=True)

    # SMS eslatma tizimi (Qarzdorlarga SMS yuborish)
    enable_sms_reminders = Column(Boolean, default=False)
    sms_provider_api_key = Column(String(255), nullable=True)
    sms_template = Column(Text, default="Hurmatli {name}, {restaurant} restoranidagi {amount} so'm qarzingizni to'lashingizni so'raymiz.")

    # 3 ta Chek Printerlari va Oshxona Routing Sozlamalari
    printer_customer_name = Column(String(100), default=None, nullable=True)      # 1-Printer: Mijoz kassa cheki (USB)
    printer_kitchen1_name = Column(String(100), default=None, nullable=True)       # 2-Printer: 1-Oshxona (USB nomi yoki LAN IP)
    printer_kitchen2_name = Column(String(100), default=None, nullable=True)       # 3-Printer: 2-Oshxona (USB nomi yoki LAN IP)
    kitchen1_title = Column(String(100), default="1-Oshxona (Qozon taomlari)", nullable=True)
    kitchen2_title = Column(String(100), default="2-Oshxona (Baliq / Somsa)", nullable=True)
    # 4-Printer: BAR (choy, suv, ichimliklar). Bo'sh qoldirilsa bar
    # cheklari kassa printeridan chiqadi — oshxonaga YUBORILMAYDI.
    printer_bar_name = Column(String(100), default="", nullable=True)
    bar_title = Column(String(100), default="BAR (Ichimliklar)", nullable=True)
    auto_print_kitchen = Column(Boolean, default=True)            # Ofitsiant yuborganda avtomatik printerga chiqarish
    auto_print_customer_bill = Column(Boolean, default=True)      # Hisob yopilganda mijoz chekini avtomatik chiqarish
    direct_qr_access = Column(Boolean, default=True)              # QR kod skanerlanganda ruxsatsiz to'g'ridan-to'g'ri menyuga kirish
    enable_chef_kds = Column(Boolean, default=False)              # Oshpaz KDS ekrani (planshet) yoqilganmi (o'chirilsa faqat printer ishlaydi)

    # Til sozlamasi
    language = Column(String(10), default="uz")

    # Qo'shimcha sozlamalar (JSON)
    extra_settings = Column(JSON, nullable=True)

    updated_at = Column(UTCDateTime(), onupdate=func.now())

    # Relationships
    restaurant = relationship("Restaurant", back_populates="settings")
