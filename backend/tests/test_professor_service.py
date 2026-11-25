from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.app.services import professor_service


ALUNOS = [
    {"ClienteId": 3, "Nome": "Zuleica", "Professor": "Prof A", "Status": "ATIVO", "Turno": "NOITE", "Plano": "ACESSORIA FIXO", "Modalidade": "MUSCULAÇÃO"},
    {"ClienteId": 1, "Nome": "Aluno A", "Professor": "Prof A", "Status": "ATIVO", "Turno": "MANHÃ", "Plano": "CONSULTORIA LIVRE", "Modalidade": "MUSCULAÇÃO"},
    {"ClienteId": 4, "Nome": "Aluno Sem Turno", "Professor": "Prof A", "Status": "ATIVO", "Turno": "", "Plano": "HYROX CT", "Modalidade": "HYROX"},
    {"ClienteId": 5, "Nome": "Aluno Inativo", "Professor": "Prof A", "Status": "INATIVO", "Turno": "TARDE"},
    {"ClienteId": 2, "Nome": "Aluno B", "Professor": "Prof B", "Status": "ATIVO", "Turno": "NOITE"},
]
REGISTROS = [
    {"ClienteId": 1, "Nome": "Aluno A", "Professor": "Prof A", "SemanaInicio": "2026-07-20", "Frequencia": 0, "Desempenho": "", "Relato": ""},
]


class ProfessorServiceTests(unittest.TestCase):
    @patch.object(professor_service, "_registros", return_value=REGISTROS)
    @patch.object(professor_service, "_alunos", return_value=ALUNOS)
    def test_zero_frequency_counts_as_completed(self, _alunos, _registros) -> None:
        payload = professor_service.week_payload(
            {"role": "professor", "name": "Prof A"}, None, "2026-07-20"
        )
        self.assertEqual(payload["summary"]["completed"], 1)
        self.assertEqual(payload["students"][0]["frequency"], "0")

    @patch.object(professor_service, "_alunos", return_value=ALUNOS)
    def test_professor_cannot_select_another_portfolio(self, _alunos) -> None:
        selected = professor_service.resolve_professor(
            {"role": "professor", "name": "Prof A"}, "Prof B"
        )
        self.assertEqual(selected, "Prof A")

    @patch.object(professor_service, "_alunos", return_value=ALUNOS)
    def test_students_payload_returns_only_active_students_sorted_for_professor(self, _alunos) -> None:
        payload = professor_service.students_payload(
            {"role": "professor", "name": "Prof A"}, "Prof B"
        )
        self.assertEqual(payload["professor"], "Prof A")
        self.assertEqual(payload["professors"], ["Prof A"])
        self.assertEqual(payload["total"], 3)
        self.assertEqual(
            [item["name"] for item in payload["students"]],
            ["Aluno A", "Aluno Sem Turno", "Zuleica"],
        )
        self.assertEqual(payload["summary"], {
            "total": 3,
            "morning": 1,
            "afternoon": 0,
            "evening": 1,
            "unassigned": 1,
        })

    @patch.object(professor_service, "_alunos", return_value=ALUNOS)
    def test_students_payload_allows_admin_to_select_professor(self, _alunos) -> None:
        payload = professor_service.students_payload(
            {"role": "admin", "name": "Administrador"}, "Prof B"
        )
        self.assertEqual(payload["professor"], "Prof B")
        self.assertEqual(payload["professors"], ["Prof A", "Prof B"])
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["students"][0]["name"], "Aluno B")

    @patch.object(professor_service.cache, "invalidate")
    @patch.object(professor_service, "_alunos", return_value=ALUNOS)
    def test_students_payload_refresh_invalidates_cache(self, _alunos, invalidate) -> None:
        professor_service.students_payload(
            {"role": "professor", "name": "Prof A"}, refresh=True
        )
        invalidate.assert_called_once_with("controle:alunos")


if __name__ == "__main__":
    unittest.main()
