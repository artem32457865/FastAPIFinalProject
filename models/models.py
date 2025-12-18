import datetime as dt
from enum import Enum

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from settings import Base


class RequestStatus(str, Enum):
    NEW = "Нова"
    IN_PROGRESS = "В обробці"
    MESSAGE = "Повідомлення"
    COMPLETED = "Завершено"
    CANCELLED = "Скасовано"


# Модель Note
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Зберігаємо хеш пароля

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    repair_requests: Mapped[list["RepairRequest"]] = relationship(
        "RepairRequest",
        back_populates="user",
        foreign_keys="RepairRequest.user_id",
        lazy="selectin",
    )

    assigned_repairs: Mapped[list["RepairRequest"]] = relationship(
        "RepairRequest",
        back_populates="admin",
        foreign_keys="RepairRequest.admin_id",
        lazy="selectin",
    )

    admin_messages: Mapped[list["AdminMessage"]] = relationship(
        "AdminMessage",
        back_populates="admin",
        foreign_keys="AdminMessage.admin_id",
        lazy="selectin",
    )

    def __str__(self):
        return f"<User> з {self.id} та {self.username}"


class RepairRequest(Base):
    __tablename__ = "repair_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    photo_url: Mapped[str] = mapped_column(String(255), nullable=True)

    required_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        SQLEnum(RequestStatus, name="request_status"),
        default=RequestStatus.NEW.value
    )

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="repair_requests",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    admin: Mapped["User"] = relationship(
        "User",
        back_populates="assigned_repairs",
        foreign_keys=[admin_id],
        lazy="selectin",
    )

    messages: Mapped[list["AdminMessage"]] = relationship(
        "AdminMessage",
        back_populates="repair_request",
        foreign_keys="AdminMessage.request_id",
        lazy="selectin",
    )

    def __str__(self):
        return f"<RepairRequest> з {self.id} та статусом {self.status}"


class AdminMessage(Base):
    __tablename__ = "admin_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )

    request_id: Mapped[int] = mapped_column(
        ForeignKey("repair_requests.id"), nullable=False
    )
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # зв’язки
    repair_request: Mapped["RepairRequest"] = relationship(
        "RepairRequest",
        back_populates="messages",
        foreign_keys=[request_id],
    )

    admin: Mapped["User"] = relationship(
        "User",
        back_populates="admin_messages",
        foreign_keys=[admin_id],
    )


class Rewiews(Base):
    __tablename__ = "rewiews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())


class ProductCategory(str, Enum):
    VACUUM_CLEANER = "Пилососи"
    REFRIGERATOR = "Холодильники"
    COMPUTER = "Комп'ютери"
    TV = "Телевізори"
    SMARTPHONE = "Смартфони"
    KITCHEN = "Кухонна техніка"
    OTHER = "Інше"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(nullable=False)
    category: Mapped[ProductCategory] = mapped_column(
        SQLEnum(ProductCategory, name="product_category"),
        default=ProductCategory.OTHER.value
    )
    image_url: Mapped[str] = mapped_column(String(255), nullable=True)
    stock_quantity: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())

    def __str__(self):
        return f"<Product> {self.name} - {self.price} грн"


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(default=1)
    added_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship("User", backref="cart_items")
    product: Mapped["Product"] = relationship("Product")


class OrderStatus(str, Enum):
    NEW = "Новий"
    PROCESSING = "В обробці"
    CONFIRMED = "Підтверджено"
    PREPARING = "Готується"
    READY = "Готовий"
    ON_THE_WAY = "В дорозі"
    DELIVERED = "Доставлено"
    CANCELLED = "Скасовано"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    total_amount: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="order_status"),
        default=OrderStatus.NEW.value
    )
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", backref="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    def __str__(self):
        return f"<Order #{self.id} - {self.status}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(default=1)
    price: Mapped[float] = mapped_column(nullable=False)  # Цена на момент покупки

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product")

    def __str__(self):
        return f"<OrderItem {self.product_id} x{self.quantity}>"