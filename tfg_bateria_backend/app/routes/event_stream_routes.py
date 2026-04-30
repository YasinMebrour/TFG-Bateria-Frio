"""Manejo de eventos críticos y su transmisión por WebSocket."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Set

import io
import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    status,
)
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import EventoCritico, Usuario
from app.redis.publisher import publicar_evento
from app.routes.authentication_routes import get_current_user

router = APIRouter(prefix="/eventos", tags=["eventos"])

# ——————————————————  WebSocket —————————————————— #

_clients: Set[WebSocket] = set()


def crear_y_emitir_evento(
    db: Session,
    fecha: str,
    tipo: str,
    descripcion: Optional[str] = None,
    **extra: object,
) -> None:
    """Crea un EventoCritico y lo publica vía Redis + WebSocket."""
    evento = EventoCritico(fecha=fecha, tipo=tipo, descripcion=descripcion)
    db.add(evento)
    db.commit()
    db.refresh(evento)

    evento_data: dict[str, object] = {
        "id": evento.id,
        "fecha": evento.fecha.isoformat(timespec="seconds"),
        "tipo": evento.tipo,
        "descripcion": evento.descripcion,
    }
    if extra:
        evento_data.update(extra)

    publicar_evento(evento_data)


def _get_eventos_de_fecha(db: Session, fecha_str: str) -> list[EventoCritico]:
    """Eventos de un día (YYYY-MM-DD)."""
    inicio = datetime.strptime(fecha_str, "%Y-%m-%d")
    fin = inicio + timedelta(days=1)
    return (
        db.query(EventoCritico)
        .filter(EventoCritico.fecha >= inicio, EventoCritico.fecha < fin)
        .order_by(EventoCritico.fecha)
        .all()
    )


@router.websocket("/ws")
async def ws_eventos(ws: WebSocket, token: str = Query(...)) -> None:
    db: Session = next(get_db())
    try:
        _ = get_current_user(token, db)
    except HTTPException:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws.accept()
    _clients.add(ws)

    try:
        # —──── recibir petición opcional de historial —──── #
        msg = await ws.receive_text()
        data = json.loads(msg)
        if isinstance(data, dict) and data.get("accion") == "historial":
            fecha_req: str = data.get("fecha", "")
            eventos = _get_eventos_de_fecha(db, fecha_req)
            await ws.send_json(
                [
                    {
                        "id": e.id,
                        "fecha": e.fecha.isoformat(timespec="seconds"),
                        "tipo": e.tipo,
                        "descripcion": e.descripcion,
                    }
                    for e in eventos
                ]
            )
        else:
            await ws.send_json([])

        # —──── mantener viva la conexión —──── #
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        _clients.discard(ws)
        db.close()

# ——————————————————  REST  —————————————————— #

@router.get("/rango", dependencies=[Depends(get_current_user)])
def rango_eventos(db: Session = Depends(get_db)) -> dict[str, str]:
    """Fecha del primer y último evento registrado."""
    primero = db.query(EventoCritico).order_by(EventoCritico.fecha).first()
    ultimo = db.query(EventoCritico).order_by(EventoCritico.fecha.desc()).first()

    ahora = datetime.now()
    if not primero or not ultimo:
        return {"inicio": ahora.isoformat(), "fin": ahora.isoformat()}

    return {
        "inicio": primero.fecha.isoformat(),
        "fin": ultimo.fecha.isoformat(),
    }

# ——————————————————  PDF  —————————————————— #

W_FECHA = 38   # mm
W_TIPO  = 45
W_DESC  = 112  # 38 + 45 + 112 ≈ 195 (A4-portrait = 210 mm → margen izq/der ≈7.5 mm)

class PDFInforme(FPDF):
    """Informe con encabezado, pie y tabla."""
    _body_font: str = "Arial"  # se fija en _cargar_fuentes

    def header(self) -> None:
        self.set_font(self._body_font, "B", 14)
        self.cell(0, 10, "Informe de eventos", ln=1, align="C")

        self.set_font(self._body_font, "", 10)
        self.cell(
            0,
            7,
            f"Desde {self.inicio:%Y-%m-%d %H:%M}   "
            f"Hasta {self.fin:%Y-%m-%d %H:%M}",
            ln=1,
            align="C",
        )
        self.ln(3)

        # cabecera de tabla
        self.set_font(self._body_font, "B", 9)
        self.set_fill_color(230, 230, 230)
        for w, txt in zip((W_FECHA, W_TIPO, W_DESC), ("Fecha", "Tipo", "Descripción")):
            self.cell(w, 7, txt, border=1, align="C", fill=True)
        self.ln()

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font(self._body_font, "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

# ——————————————————  helper para una fila —————————————————— #
def _fila_evento(pdf: FPDF, ev: EventoCritico, zebra: bool) -> None:
    x0, y0 = pdf.get_x(), pdf.get_y()
    h_line = 6

    ln_f, h_f = _wrap(pdf, W_FECHA, ev.fecha.strftime("%Y-%m-%d %H:%M"), h_line)
    ln_t, h_t = _wrap(pdf, W_TIPO,  ev.tipo,                           h_line)
    ln_d, h_d = _wrap(pdf, W_DESC,  ev.descripcion or "",              h_line)
    h_row = max(h_f, h_t, h_d)

    # ——— salto de página manual ———
    if pdf.will_page_break(h_row):
        pdf.add_page()
        x0, y0 = pdf.get_x(), pdf.get_y()

    # ——— dibujar marco único ———
    pdf.set_fill_color(245, 245, 245) if zebra else pdf.set_fill_color(255, 255, 255)
    for offset, width in zip((0, W_FECHA, W_FECHA + W_TIPO), (W_FECHA, W_TIPO, W_DESC)):
        pdf.rect(x0 + offset, y0, width, h_row, style="DF")

    # ——— escribir texto ———
    pdf.set_xy(x0, y0)
    pdf.multi_cell(W_FECHA, h_line, "\n".join(ln_f), border=0)
    pdf.set_xy(x0 + W_FECHA, y0)
    pdf.multi_cell(W_TIPO,  h_line, "\n".join(ln_t), border=0)
    pdf.set_xy(x0 + W_FECHA + W_TIPO, y0)
    pdf.multi_cell(W_DESC,  h_line, "\n".join(ln_d), border=0)

    pdf.set_xy(x0, y0 + h_row)




def _cargar_fuentes(pdf: FPDF) -> str:
    """Carga DejaVu si existe; si no, retorna 'Arial'."""
    base = Path(__file__).with_name("DejaVuSans.ttf")
    try:
        pdf.add_font("DejaVu", "", str(base), uni=True)
        pdf.add_font("DejaVu", "B", str(base.with_name("DejaVuSans-Bold.ttf")), uni=True)
        return "DejaVu"
    except (RuntimeError, FileNotFoundError):
        # Arial ya está integrada; no necesita add_font
        return "Arial"

# ——————————————————  compatibilidad split_only —————————————————— #
def _wrap(pdf: FPDF, w: int, txt: str, h_line: int) -> tuple[list[str], float]:
    """
    Devuelve (líneas, alto_total_mm) sin requerir split_only.
    """
    try:
        # fpdf2 ≥ 2.7
        lines = pdf.multi_cell(w, h_line, txt, split_only=True)
    except TypeError:
        # fpdf2 < 2.7 — hacemos un split rápido por palabras
        words, lines, line = txt.split(), [], ""
        for word in words:
            test = f"{line} {word}".strip()
            if pdf.get_string_width(test) <= w:
                line = test
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines, len(lines) * h_line


# ——————————————————  generación del PDF —————————————————— #
def _generar_pdf(
    eventos: list[EventoCritico],
    inicio: datetime,
    fin: datetime,
) -> bytes:
    """
    Devuelve un PDF (en memoria) con los eventos del intervalo indicado.
    """
    pdf = PDFInforme(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)

    # fuente (DejaVu si los .ttf existen, Arial integrada en caso contrario)
    pdf._body_font = _cargar_fuentes(pdf)

    pdf.inicio, pdf.fin = inicio, fin
    pdf.add_page()
    pdf.set_font(pdf._body_font, "", 9)

    for idx, ev in enumerate(eventos):
        zebra = idx % 2 == 0        # fondo gris claro en filas pares
        _fila_evento(pdf, ev, zebra)

    return pdf.output(dest="S")     # bytes



@router.get("/reporte", dependencies=[Depends(get_current_user)])
def reporte_eventos(
    inicio: Optional[datetime] = None,
    fin: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Descarga un PDF con los eventos entre *inicio* y *fin* (ambos inclusive)."""
    if inicio is None or fin is None:
        rango = rango_eventos(db)
        if inicio is None:
            inicio = datetime.fromisoformat(rango["inicio"])
        if fin is None:
            fin = datetime.fromisoformat(rango["fin"])

    eventos = (
        db.query(EventoCritico)
        .filter(EventoCritico.fecha >= inicio, EventoCritico.fecha <= fin)
        .order_by(EventoCritico.fecha)
        .all()
    )

    import logging
    logger = logging.getLogger("eventos.pdf")

    try:
        pdf_bytes = _generar_pdf(eventos, inicio, fin)
    except Exception:
        logger.exception("Error generando informe PDF")   # <- deja rastro completo
        raise HTTPException(status_code=500, detail="No se pudo generar el PDF")


    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)
    nombre = f"eventos_{inicio:%Y%m%d}_{fin:%Y%m%d}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{nombre}"'}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
