from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db_models import ChefProfileEntity, DishEntity, DriverProfileEntity, UserEntity


DEMO_CHEFS = [
    {
        "id": UUID("10000000-0000-0000-0000-000000000001"),
        "phone": "+201000000001",
        "display_name": "مطبخ أم يوسف",
        "specialty": "محاشي وطواجن",
        "area": "6 أكتوبر",
        "rating": 4.9,
        "is_open_today": True,
    },
    {
        "id": UUID("10000000-0000-0000-0000-000000000002"),
        "phone": "+201000000002",
        "display_name": "بيت مريم",
        "specialty": "أكل مصري بيتي",
        "area": "6 أكتوبر",
        "rating": 4.8,
        "is_open_today": True,
    },
    {
        "id": UUID("10000000-0000-0000-0000-000000000003"),
        "phone": "+201000000003",
        "display_name": "مطبخ الحاجة سعاد",
        "specialty": "أكلات شرقية",
        "area": "6 أكتوبر",
        "rating": 4.7,
        "is_open_today": False,
    },
]


def seed_demo_data(db: Session) -> None:
    for item in DEMO_CHEFS:
        user = db.get(UserEntity, item["id"])
        if user is None:
            user = UserEntity(
                id=item["id"],
                phone=item["phone"],
                role="chef",
                is_active=True,
            )
            db.add(user)
            db.flush()

        chef = db.get(ChefProfileEntity, item["id"])
        if chef is None:
            db.add(
                ChefProfileEntity(
                    user_id=item["id"],
                    display_name=item["display_name"],
                    specialty=item["specialty"],
                    area=item["area"],
                    status="active",
                    rating=item["rating"],
                    is_verified=True,
                    is_open_today=item["is_open_today"],
                )
            )

    db.flush()

    demo_dishes = [
        (
            UUID("10000000-0000-0000-0000-000000000001"),
            "محشي مشكل",
            "محشي كرنب وورق عنب وكوسة بطعم بيتي.",
            "محاشي",
            18000,
            24,
        ),
        (
            UUID("10000000-0000-0000-0000-000000000001"),
            "طاجن بامية باللحمة",
            "طاجن بامية باللحمة مع رز أبيض.",
            "طواجن",
            22000,
            24,
        ),
        (
            UUID("10000000-0000-0000-0000-000000000002"),
            "ملوخية وفراخ",
            "وجبة ملوخية وفراخ ورز.",
            "أكل مصري",
            21000,
            24,
        ),
    ]

    for chef_id, name, description, category, price, notice in demo_dishes:
        existing = db.scalar(
            select(DishEntity).where(
                DishEntity.chef_id == chef_id,
                DishEntity.name == name,
            )
        )
        if existing is None:
            db.add(
                DishEntity(
                    chef_id=chef_id,
                    name=name,
                    description=description,
                    category=category,
                    base_price_minor=price,
                    prep_notice_hours=notice,
                    is_special_order_available=True,
                    is_active=True,
                )
            )

    demo_drivers = [
        (
            UUID("30000000-0000-0000-0000-000000000001"),
            "+201090000001",
            4.9,
        ),
        (
            UUID("30000000-0000-0000-0000-000000000002"),
            "+201090000002",
            4.8,
        ),
    ]

    for driver_id, phone, rating in demo_drivers:
        driver_user = db.get(UserEntity, driver_id)
        if driver_user is None:
            driver_user = UserEntity(
                id=driver_id,
                phone=phone,
                role="driver",
                is_active=True,
            )
            db.add(driver_user)
            db.flush()

        profile = db.get(DriverProfileEntity, driver_id)
        if profile is None:
            db.add(
                DriverProfileEntity(
                    user_id=driver_id,
                    status="offline",
                    rating=rating,
                )
            )

    db.commit()
