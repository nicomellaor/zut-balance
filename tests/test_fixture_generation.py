from pathlib import Path

from zut_balance.pdf_validation import extract_pdf_text

from fixtures.generate_banco_chile_cuenta_vista import generate_fixtures


def test_generator_creates_readable_synthetic_statement_fixtures(tmp_path: Path) -> None:
    generate_fixtures(tmp_path)

    expected_pages = {
        "cartola_banco_chile_multipagina.pdf": 3,
        "cartola_banco_chile_cruce_anio.pdf": 1,
        "cartola_banco_chile_columnas_desplazadas.pdf": 1,
        "cartola_banco_chile_metadatos_reordenados.pdf": 1,
    }
    generated_paths = {path.name: path for path in tmp_path.glob("*.pdf")}

    assert generated_paths.keys() == expected_pages.keys()
    for name, page_count in expected_pages.items():
        pages = extract_pdf_text(generated_paths[name].read_bytes())

        assert len(pages) == page_count
        assert "BANCO DE CHILE" in pages[0]
        assert "CUENTA VISTA" in pages[0]
