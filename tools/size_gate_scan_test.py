"""Seam: the size gate's scan tests (literal scan, suspect literals, skip markers); size_gate_test.py the rest.
Canonical as dev-rules tools/size_gate_scan_test.py, copied unchanged to scripts/size_gate_scan_test.py.
"""

import codecs

from size_gate_test import RepositoryCase


class ScanTest(RepositoryCase):
    def test_literal_scan_finds_test_data_in_product_code(self) -> None:
        self.write({"tests/data/seed.sql": "INSERT INTO account (code, balance) VALUES ('Z900', 77.25);\n"})
        self.assert_gate(0)
        for literal in ['"A001"', '"EUR"', 'row["currency"]', "10.50", '"Z900"', "77.25"]:
            with self.subTest(literal):
                self.write({"src/extra.py": f"VALUE = {literal}\n"})
                self.assert_gate(1, says="hard-coded test-data value")

    def test_literal_scan_reads_each_test_data_form(self) -> None:
        self.budget(max_test_data_files=10)
        self.write(
            {
                "tests/data/seed.sql": "INSERT INTO account (code, balance, age) VALUES ('Z900', 77.25, 640);\n",
                "tests/data/semicolon.csv": codecs.BOM_UTF8.decode("utf-8") + "Kode;Menge\nB777;5\n",
                "tests/data/rows.tsv": "city\tzone\nOslo\tT001\n",
                "tests/data/target.json": '{"table": "dbo.Customer"}\n',
                "tests/data/broken.json": '{"code": "Q777",\n',
            }
        )
        self.assert_gate(0)
        literals = [
            ("Kode", "BOM stripped, semicolon delimiter"),
            ("Menge", "semicolon delimiter"),
            ('"Oslo"', "TSV cell"),
            ("Customer", "dotted part"),
            ('"Q777"', "quoted string in invalid JSON"),
            ("10.50m", "C# decimal suffix"),
            ("640L", "C# long suffix"),
            ("77.25f", "C# float suffix"),
        ]
        for literal, name in literals:
            with self.subTest(name):
                self.write({"src/extra.py": f"VALUE = {literal}\n"})
                self.assert_gate(1, says="hard-coded test-data value")
        self.write({"src/extra.py": "VALUE = 10.505\n"})
        self.assert_gate(0)

    def test_suspect_product_literals_fail(self) -> None:
        # Split so that secret scanners do not flag this file.
        literals = [
            '"Server=db;Database=app;"',
            '"postgres' + '://db/app"',
            '"/home/alice/input.csv"',
            '"10.0.0.7"',
            '"' + "ab" * 32 + '"',
            "PASS" + 'WORD = "hunter' + '22"',
            '"-----BEGIN RSA ' + 'PRIVATE KEY-----"',
        ]
        for literal in literals:
            with self.subTest(literal):
                self.write({"src/extra.py": f"VALUE = {literal}\n"})
                self.assert_gate(1, says="suspect")

    def test_skip_and_focus_markers_in_test_code_fail(self) -> None:
        markers = [
            't.Skip("later")',
            '[Fact(Skip = "later")]',
            'Assert.Skip("later")',
            "@pytest.mark.skip",
            'pytest.skip("later")',
            "@pytest.mark.xfail",
            "it.skip('x')",
            "it.only('x')",
            "it.todo('x')",
        ]
        for marker in markers:
            with self.subTest(marker):
                self.write({"tests/extra_test.py": f"{marker}\n"})
                self.assert_gate(1, says="tests/extra_test.py:1: skip or focus marker")
        (self.root / "tests/extra_test.py").unlink()
        self.write({"tests/app.bats": '@test "sums" {\n  skip\n}\n'})
        self.assert_gate(1, says="tests/app.bats:2: skip or focus marker")
