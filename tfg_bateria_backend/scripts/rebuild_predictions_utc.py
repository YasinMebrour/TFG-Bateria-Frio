from app.db.database import SessionLocal
from app.db.models import PrediccionXGBoost
import pandas as pd


def main() -> None:
    session = SessionLocal()
    try:
        rows = session.query(PrediccionXGBoost).all()
        for row in rows:
            row.hora = (
                pd.to_datetime(row.hora)
                .tz_localize("Europe/Madrid")
                .tz_convert("UTC")
                .tz_localize(None)
            )
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()
