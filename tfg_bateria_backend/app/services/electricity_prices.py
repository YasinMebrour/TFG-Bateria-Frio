from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import requests
import pandas as pd
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from ..db.models import PreciosLuz

def fetch_prices(start: datetime, end: datetime) -> pd.DataFrame:
    url = 'https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real'
    headers = {'User-Agent': 'Mozilla/5.0'}
    params = {
        'start_date': start.strftime('%Y-%m-%dT%H:%M'),
        'end_date':   end.strftime('%Y-%m-%dT%H:%M'),
        'time_trunc': 'hour'
    }
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    vals = r.json()['included'][0]['attributes']['values']
    df = pd.DataFrame(vals)
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True).dt.tz_convert(None)
    df.rename(columns={'value':'precio_MWh'}, inplace=True)
    df['precio_kWh'] = df['precio_MWh'] / 1000
    df = df[['datetime','precio_kWh']].rename(columns={'datetime':'hora'})
    return df

def store_missing(db: Session, df):
    if df.empty:
        return
    t0, t1 = df['hora'].min(), df['hora'].max()
    existentes = { h for (h,) in db.query(PreciosLuz.hora)
                        .filter(and_(PreciosLuz.hora>=t0, PreciosLuz.hora<=t1))
                        .all() }
    nuevos = [
        PreciosLuz(hora=row.hora, kwh=row.precio_kWh)
        for row in df.itertuples() if row.hora not in existentes
    ]
    if nuevos:
        db.bulk_save_objects(nuevos)
        db.commit()


def generate_month_ranges(start: datetime, end: datetime):
    """
    start y end deben ser tz-aware en UTC.
    current hereda start.tzinfo para que las comparaciones sean válidas.
    """
    tz = start.tzinfo
    # arrancamos en día 1 del mes de 'start', manteniendo tzinfo
    current = datetime(start.year, start.month, 1, tzinfo=tz)
    while current < end:
        end_of_month = current + relativedelta(months=1) - timedelta(minutes=1)
        yield (max(start, current), min(end, end_of_month))
        current += relativedelta(months=1)

def actualizar_precios(db: Session):
    # 1) determinar 'inicio' (UTC-aware)
    last = db.query(func.max(PreciosLuz.hora)).scalar()
    if last:
        # asumimos que 'last' es UTC naive; lo marcamos como UTC
        inicio = last.replace(tzinfo=timezone.utc) + timedelta(hours=1)
    else:
        inicio = datetime(2025, 1, 1, tzinfo=timezone.utc)

    ahora = datetime.now(timezone.utc)

    # 2) histórico: sólo si inicio < ahora
    if inicio < ahora:
        for s, e in generate_month_ranges(inicio, ahora):
            if s > e:
                continue
            df = fetch_prices(s, e)
            store_missing(db, df)
    elif inicio == ahora:
        # un único instante
        df = fetch_prices(inicio, ahora)
        store_missing(db, df)

    # 3) predicción para mañana (rango UTC-aware)
    manana = (ahora + timedelta(days=1)).date()
    inicio_m = datetime.combine(manana, datetime.min.time()).replace(tzinfo=timezone.utc)
    fin_m    = datetime.combine(manana, datetime.max.time()).replace(tzinfo=timezone.utc)
    dfm = fetch_prices(inicio_m, fin_m)
    store_missing(db, dfm)

def fetch_and_store_tomorrow_prediction(db: Session):
    ahora = datetime.now(timezone.utc)
    manana = (ahora + timedelta(days=1)).date()
    inicio = datetime.combine(manana, datetime.min.time()).replace(tzinfo=timezone.utc)
    fin    = datetime.combine(manana, datetime.max.time()).replace(tzinfo=timezone.utc)
    df = fetch_prices(inicio, fin)
    store_missing(db, df)

