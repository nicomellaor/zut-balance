"""Generate deterministic synthetic Banco de Chile statement fixtures."""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas


FIXTURE_DIRECTORY = Path(__file__).parent
PAGE_WIDTH, PAGE_HEIGHT = letter
X = {
    "date": 36,
    "description": 100,
    "document": 285,
    "channel": 360,
    "debit": 445,
    "credit": 510,
    "balance": 580,
}


def _text(canvas: Canvas, value: str, x: int, y: int) -> None:
    canvas.drawString(x, y, value)


def _header(
    canvas: Canvas,
    *,
    page: int,
    total_pages: int,
    period_start: str,
    period_end: str,
    reordered: bool = False,
) -> int:
    canvas.setFont("Courier", 9)
    lines = [
        "BANCO DE CHILE",
        "ESTADO DE CUENTA",
        "CUENTA VISTA",
        "N° DE CUENTA: XXXXXXXX",
        "MONEDA: PESOS",
        f"DESDE: {period_start}",
        f"HASTA: {period_end}",
        f"N° DE PAGINA: {page} DE {total_pages}",
    ]
    if reordered:
        lines[4:7] = [lines[6], lines[4], lines[5]]
    y = PAGE_HEIGHT - 48
    for line in lines:
        _text(canvas, line, 36, y)
        y -= 14
    return y - 12


def _table_header(canvas: Canvas, y: int, *, shift: int = 0) -> int:
    canvas.setFont("Courier", 7)
    _text(canvas, "DIA/MES", X["date"], y)
    _text(canvas, "DETALLE DE TRANSACCION", X["description"] + shift, y)
    _text(canvas, "N° DOCTO", X["document"] + shift, y)
    _text(canvas, "SUCURSAL", X["channel"] + shift, y)
    _text(canvas, "CARGOS", X["debit"] + shift, y)
    _text(canvas, "O ABONOS", X["credit"] + shift, y)
    _text(canvas, "SALDO", X["balance"] + shift, y)
    return y - 18


def _transaction(
    canvas: Canvas,
    y: int,
    *,
    day_month: str,
    description: str,
    amount: str,
    balance: str,
    credit: bool,
    document: str = "",
    channel: str = "INTERNET",
    shift: int = 0,
) -> int:
    _text(canvas, day_month, X["date"], y)
    _text(canvas, description, X["description"] + shift, y)
    _text(canvas, document, X["document"] + shift, y)
    _text(canvas, channel, X["channel"] + shift, y)
    _text(canvas, amount, (X["credit"] if credit else X["debit"]) + shift, y)
    _text(canvas, balance, X["balance"] + shift, y)
    return y - 14


def _summary(canvas: Canvas, y: int, *, opening: str, closing: str, count: int, debits: str, credits: str) -> None:
    _text(canvas, f"15/12 SALDO INICIAL {opening}", 36, y)
    y -= 14
    _text(canvas, f"15/01 SALDO FINAL {closing}", 36, y)
    y -= 14
    _text(canvas, "RETENCION A 1 DIA RETENCION A MAS DE 1 DIA SALDO DISPONIBLE A LA FECHA", 36, y)
    y -= 14
    _text(canvas, f"0 0 {closing}", 36, y)
    y -= 14
    _text(canvas, f"TOTAL MOVIMIENTOS: {count}", 36, y)
    y -= 14
    _text(canvas, f"TOTAL CARGOS: {debits}", 36, y)
    y -= 14
    _text(canvas, f"TOTAL ABONOS: {credits}", 36, y)


def _save_multipage(path: Path) -> None:
    canvas = Canvas(str(path), pagesize=letter, pageCompression=0, invariant=1)
    y = _header(canvas, page=1, total_pages=3, period_start="15/12/2026", period_end="15/01/2027")
    _text(canvas, "RESUMEN DE CARTOLA", 36, y)
    canvas.showPage()

    y = _header(canvas, page=2, total_pages=3, period_start="15/12/2026", period_end="15/01/2027")
    y = _table_header(canvas, y)
    y = _transaction(canvas, y, day_month="16/12", description="PAGO SERVICIO", amount="10.000", balance="90.000", credit=False, document="101")
    _text(canvas, "MUESTRA DIDACTICA", X["description"], y)
    y -= 14
    _transaction(canvas, y, day_month="20/12", description="TRANSFERENCIA", amount="5.000", balance="85.000", credit=False, document="102")
    _text(canvas, "INFORMESE SOBRE LA GARANTIA ESTATAL", 36, y - 8)
    canvas.showPage()

    y = _header(canvas, page=3, total_pages=3, period_start="15/12/2026", period_end="15/01/2027")
    y = _table_header(canvas, y)
    y = _transaction(canvas, y, day_month="05/01", description="ABONO NOMINA", amount="20.000", balance="105.000", credit=True, document="103")
    _text(canvas, "CONTINUACION", X["description"], y)
    y -= 14
    y = _transaction(canvas, y, day_month="10/01", description="PAGO", amount="5.000", balance="100.000", credit=False, document="104")
    _text(canvas, "COMERCIO", X["description"], y)
    y -= 22
    _summary(canvas, y, opening="100.000", closing="100.000", count=4, debits="20.000", credits="20.000")
    canvas.save()


def _save_single_page(path: Path, *, shifted: bool = False, reordered: bool = False) -> None:
    canvas = Canvas(str(path), pagesize=letter, pageCompression=0, invariant=1)
    y = _header(canvas, page=1, total_pages=1, period_start="01/08/2026", period_end="31/08/2026", reordered=reordered)
    shift = 24 if shifted else 0
    y = _table_header(canvas, y, shift=shift)
    y = _transaction(canvas, y, day_month="04/08", description="PAGO BASE", amount="10.000", balance="90.000", credit=False, document="201", shift=shift)
    y = _transaction(canvas, y, day_month="08/08", description="ABONO BASE", amount="20.000", balance="110.000", credit=True, document="202", shift=shift)
    _summary(canvas, y - 14, opening="100.000", closing="110.000", count=2, debits="10.000", credits="20.000")
    canvas.save()


def _save_cross_year(path: Path) -> None:
    canvas = Canvas(str(path), pagesize=letter, pageCompression=0, invariant=1)
    y = _header(canvas, page=1, total_pages=1, period_start="15/12/2026", period_end="15/01/2027")
    y = _table_header(canvas, y)
    y = _transaction(canvas, y, day_month="20/12", description="PAGO DICIEMBRE", amount="10.000", balance="90.000", credit=False, document="301")
    y = _transaction(canvas, y, day_month="10/01", description="ABONO ENERO", amount="20.000", balance="110.000", credit=True, document="302")
    _summary(canvas, y - 14, opening="100.000", closing="110.000", count=2, debits="10.000", credits="20.000")
    canvas.save()


def generate_fixtures(directory: Path = FIXTURE_DIRECTORY) -> None:
    directory.mkdir(exist_ok=True)
    _save_multipage(directory / "cartola_banco_chile_multipagina.pdf")
    _save_cross_year(directory / "cartola_banco_chile_cruce_anio.pdf")
    _save_single_page(directory / "cartola_banco_chile_columnas_desplazadas.pdf", shifted=True)
    _save_single_page(directory / "cartola_banco_chile_metadatos_reordenados.pdf", reordered=True)


if __name__ == "__main__":
    generate_fixtures()
