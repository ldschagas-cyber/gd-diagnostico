"""CLI — cria (ou reseta a senha de) um usuário do Portal do Cliente (v6.18.0).

Provisionamento é manual nesta versão (PRD v6.18.0 §6 — "Fora de escopo":
onboarding self-service) — a equipe GD Conecta roda este script para o
piloto, apontando para uma empresa já cadastrada e diagnosticada.

Idempotente: se o e-mail já existir, atualiza nome/senha/empresa em vez de
duplicar. Mesmo padrão de scripts/backfill_*.py (SessionLocal direto, sem
passar pela API/contexto de requisição).

Uso:
    python scripts/seed_portal_cliente_piloto.py --empresa-id 12 \\
        --nome "Diretoria Cliente Piloto" --email diretoria@clientepiloto.com.br \\
        --senha "Cliente@123"

Requisitos: rodar com a MESMA variável DATABASE_URL do ambiente-alvo.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # permite rodar sem -m

from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.infrastructure.database.models import ClientePortalUserModel, EmpresaModel  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--empresa-id", type=int, required=True, help="ID da empresa já cadastrada")
    parser.add_argument("--nome", required=True, help="Nome do usuário-executivo")
    parser.add_argument("--email", required=True, help="E-mail de login (globalmente único no Portal)")
    parser.add_argument("--senha", required=True, help="Senha inicial (o usuário pode trocar depois)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        empresa = db.get(EmpresaModel, args.empresa_id)
        if empresa is None:
            print(f"[erro] Empresa {args.empresa_id} não encontrada — crie/importe a empresa antes.")
            return

        existente = db.scalar(
            select(ClientePortalUserModel).where(ClientePortalUserModel.email == args.email)
        )
        if existente:
            if existente.empresa_id != args.empresa_id:
                print(
                    f"[erro] O e-mail {args.email} já pertence a outra empresa (id={existente.empresa_id}). "
                    "E-mail é globalmente único no Portal — escolha outro."
                )
                return
            existente.nome = args.nome
            existente.hashed_password = hash_password(args.senha)
            existente.ativo = True
            db.commit()
            print(f"[atualizado] Usuário do Portal {args.email} (empresa {args.empresa_id}).")
            return

        db.add(ClientePortalUserModel(
            empresa_id=args.empresa_id, nome=args.nome, email=args.email,
            hashed_password=hash_password(args.senha), ativo=True,
        ))
        db.commit()
        print(
            f"[criado] Usuário do Portal {args.email} para "
            f"{empresa.nome_fantasia or empresa.razao_social} (empresa {args.empresa_id})."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
