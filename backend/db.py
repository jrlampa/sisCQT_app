# siscqt_db.py
import sqlite3
import threading
import logging
import pandas as pd
from datetime import datetime
from typing import Tuple, Dict
from backend.constantes import (
    DB_FILE,
    DEFAULT_CABOS,
    DEFAULT_IPS,
    DEFAULT_TRAFOS_LISTA,
    DEFAULT_PERFIS,
    DEFAULT_PARAMS,
)
from backend.engine import ElectricalEngine

logger = logging.getLogger("SisCQT")


class DatabaseManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._init_db()
        return cls._instance

    def _get_conn(self):
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            with conn:
                # Tabelas de Projeto
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS projetos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    data_criacao TEXT
                )"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cenarios_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    projeto_id INTEGER NOT NULL,
                    nome_cenario TEXT NOT NULL,
                    trafo_kva INTEGER,
                    classe_tipo TEXT,
                    classe_manual TEXT,
                    fp_ip REAL DEFAULT 0.92,
                    perfil TEXT DEFAULT 'Padrão (Urbano)', 
                    FOREIGN KEY(projeto_id) REFERENCES projetos(id) ON DELETE CASCADE,
                    UNIQUE(projeto_id, nome_cenario)
                )"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS trechos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    projeto_id INTEGER NOT NULL,
                    nome_cenario TEXT NOT NULL,
                    ponto TEXT NOT NULL, montante TEXT, metros REAL, cabo TEXT,
                    mono INTEGER, bi INTEGER, tri INTEGER, tri_esp INTEGER,
                    carga_esp REAL, tipo_ip TEXT, qtd_ip INTEGER,
                    FOREIGN KEY(projeto_id) REFERENCES projetos(id) ON DELETE CASCADE,
                    UNIQUE(projeto_id, nome_cenario, ponto)
                )"""
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_trechos_proj_cenario ON trechos(projeto_id, nome_cenario)"
                )

                # Configs Tables (AGORA COM PREÇO)
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cfg_cabos (
                    nome TEXT PRIMARY KEY, 
                    coeficiente REAL NOT NULL,
                    preco REAL DEFAULT 0.0
                )"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cfg_ips (
                    nome TEXT PRIMARY KEY, 
                    potencia_watts REAL NOT NULL,
                    preco REAL DEFAULT 0.0
                )"""
                )

                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cfg_trafos (kva REAL PRIMARY KEY)"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cfg_perfis (nome TEXT PRIMARY KEY, cqt_max REAL, sobrecarga_max REAL, metros_max REAL, clientes_max INTEGER)"""
                )

                self._seed_defaults(conn)
        except Exception:
            pass
        finally:
            conn.close()

    def _seed_defaults(self, conn):
        if not conn.execute("SELECT 1 FROM cfg_cabos").fetchone():
            data = [(k, v, 0.0) for k, v in DEFAULT_CABOS.items()]
            conn.executemany(
                "INSERT INTO cfg_cabos (nome, coeficiente, preco) VALUES (?,?,?)", data
            )

        if not conn.execute("SELECT 1 FROM cfg_ips").fetchone():
            data = [(k, v, 0.0) for k, v in DEFAULT_IPS.items()]
            conn.executemany(
                "INSERT INTO cfg_ips (nome, potencia_watts, preco) VALUES (?,?,?)", data
            )

        if not conn.execute("SELECT 1 FROM cfg_trafos").fetchone():
            data = [(t,) for t in DEFAULT_TRAFOS_LISTA]
            conn.executemany("INSERT INTO cfg_trafos (kva) VALUES (?)", data)
        if not conn.execute("SELECT 1 FROM cfg_perfis").fetchone():
            conn.executemany(
                "INSERT INTO cfg_perfis (nome, cqt_max, sobrecarga_max, metros_max, clientes_max) VALUES (?,?,?,?,?)",
                DEFAULT_PERFIS,
            )

    def load_configs(self):
        conn = self._get_conn()
        try:
            # Carrega Preços também
            cabos = {
                r["nome"]: {"coef": r["coeficiente"], "preco": r["preco"]}
                for r in conn.execute("SELECT * FROM cfg_cabos").fetchall()
            }
            ips = {
                r["nome"]: {"pot": r["potencia_watts"], "preco": r["preco"]}
                for r in conn.execute("SELECT * FROM cfg_ips").fetchall()
            }

            trafos = [
                r["kva"]
                for r in conn.execute(
                    "SELECT * FROM cfg_trafos ORDER BY kva"
                ).fetchall()
            ]

            perfis_raw = conn.execute("SELECT * FROM cfg_perfis").fetchall()
            perfis = {}
            for r in perfis_raw:
                perfis[r["nome"]] = {
                    "cqt_max": r["cqt_max"],
                    "sobrecarga_max": r["sobrecarga_max"],
                    "metros_max": r["metros_max"],
                    "clientes_max": r["clientes_max"],
                }
            return cabos, ips, trafos, perfis
        finally:
            conn.close()

    def update_configs(self, type_key, df):
        conn = self._get_conn()
        try:
            with self._lock:
                conn.execute("BEGIN IMMEDIATE")
                if type_key == "cabos":
                    conn.execute("DELETE FROM cfg_cabos")
                    conn.executemany(
                        "INSERT INTO cfg_cabos (nome, coeficiente, preco) VALUES (?,?,?)",
                        df[["nome", "coeficiente", "preco"]].values.tolist(),
                    )
                elif type_key == "ips":
                    conn.execute("DELETE FROM cfg_ips")
                    conn.executemany(
                        "INSERT INTO cfg_ips (nome, potencia_watts, preco) VALUES (?,?,?)",
                        df[["nome", "potencia_watts", "preco"]].values.tolist(),
                    )
                elif type_key == "trafos":
                    conn.execute("DELETE FROM cfg_trafos")
                    conn.executemany(
                        "INSERT INTO cfg_trafos (kva) VALUES (?)",
                        df[["kva"]].values.tolist(),
                    )
                elif type_key == "perfis":
                    conn.execute("DELETE FROM cfg_perfis")
                    conn.executemany(
                        "INSERT INTO cfg_perfis (nome, cqt_max, sobrecarga_max, metros_max, clientes_max) VALUES (?,?,?,?,?)",
                        df[
                            [
                                "nome",
                                "cqt_max",
                                "sobrecarga_max",
                                "metros_max",
                                "clientes_max",
                            ]
                        ].values.tolist(),
                    )
                conn.commit()
            return True, "Configurações salvas!"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def salvar_projeto(
        self, nome: str, dados_dict: Dict, params_dict: Dict, overwrite_id: int = None
    ) -> Tuple[bool, str]:
        conn = self._get_conn()

        def safe_float(v):
            try:
                return float(pd.to_numeric(v, errors="coerce") or 0.0)
            except:
                return 0.0

        def safe_int(v):
            try:
                return int(pd.to_numeric(v, errors="coerce") or 0)
            except:
                return 0

        def safe_str(v):
            if v is None or pd.isna(v):
                return ""
            return str(v).strip()

        try:
            with self._lock:
                conn.execute("BEGIN IMMEDIATE")
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if overwrite_id:
                    pid = overwrite_id
                    conn.execute(
                        "UPDATE projetos SET data_criacao=? WHERE id=?", (ts, pid)
                    )
                    conn.execute(
                        "DELETE FROM cenarios_config WHERE projeto_id=?", (pid,)
                    )
                    conn.execute("DELETE FROM trechos WHERE projeto_id=?", (pid,))
                    msg = "atualizado"
                else:
                    exists = conn.execute(
                        "SELECT 1 FROM projetos WHERE nome=?", (nome,)
                    ).fetchone()
                    if exists:
                        raise ValueError("Nome de projeto já existe.")
                    cur = conn.execute(
                        "INSERT INTO projetos (nome, data_criacao) VALUES (?, ?)",
                        (nome, ts),
                    )
                    pid = cur.lastrowid
                    msg = "criado"

                cfgs, data = [], []
                for aba, df in dados_dict.items():
                    df_safe = df.copy()
                    if df_safe.empty:
                        continue

                    p = params_dict.get(aba, DEFAULT_PARAMS)
                    perfil = p.get("perfil", "Padrão (Urbano)")

                    cfgs.append(
                        (
                            pid,
                            aba,
                            p["trafo_kva"],
                            p["classe_tipo"],
                            p["classe_manual"],
                            p.get("fp_ip", 0.92),
                            perfil,
                        )
                    )

                    df_valid = df_safe[
                        (df_safe["PONTO"].astype(str).str.strip() != "")
                        & (df_safe["PONTO"] != "TRAFO")
                    ]
                    if df_valid["PONTO"].duplicated().any():
                        dup = df_valid[df_valid["PONTO"].duplicated()]["PONTO"].tolist()
                        raise ValueError(
                            f"Aborted: Pontos duplicados na aba '{aba}': {dup}"
                        )

                    for _, r in df_safe.iterrows():
                        ponto = safe_str(r["PONTO"])
                        if not ponto:
                            continue

                        data.append(
                            (
                                pid,
                                aba,
                                ponto,
                                safe_str(r["MONTANTE"]),
                                safe_float(r["METROS"]),
                                safe_str(r["CABO"]),
                                safe_int(r["MONO"]),
                                safe_int(r["BIFÁSICO"]),
                                safe_int(r["TRIFÁSICO"]),
                                safe_int(r["TRI ESPECIAL"]),
                                safe_float(r["CARGA_ESP_KVA"]),
                                safe_str(r["TIPO_IP"]),
                                safe_int(r["QTD_IP"]),
                            )
                        )

                conn.executemany(
                    "INSERT INTO cenarios_config (projeto_id, nome_cenario, trafo_kva, classe_tipo, classe_manual, fp_ip, perfil) VALUES (?,?,?,?,?,?,?)",
                    cfgs,
                )
                conn.executemany(
                    "INSERT INTO trechos (projeto_id, nome_cenario, ponto, montante, metros, cabo, mono, bi, tri, tri_esp, carga_esp, tipo_ip, qtd_ip) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    data,
                )

                conn.commit()
                return True, f"Projeto '{nome}' {msg}!"

        except (sqlite3.IntegrityError, ValueError) as e:
            conn.rollback()
            return False, f"Erro: {str(e)}"
        except Exception as e:
            conn.rollback()
            logger.error(f"DB Error: {e}", exc_info=True)
            return False, f"Erro interno: {str(e)}"
        finally:
            conn.close()

    def carregar_projeto(self, pid: int):
        conn = self._get_conn()
        try:
            conn.execute("BEGIN DEFERRED")
            proj = conn.execute("SELECT * FROM projetos WHERE id=?", (pid,)).fetchone()
            if not proj:
                return None, None, "Projeto não encontrado"

            cfg_rows = conn.execute(
                "SELECT * FROM cenarios_config WHERE projeto_id=?", (pid,)
            ).fetchall()
            trecho_rows = conn.execute(
                "SELECT * FROM trechos WHERE projeto_id=? ORDER BY id ASC", (pid,)
            ).fetchall()
            conn.commit()

            trecho_data = []
            for r in trecho_rows:
                # Mantém as chaves em minúsculo para compatibilidade com app.py
                trecho_data.append(
                    {
                        "nome_cenario": r["nome_cenario"],
                        "ponto": r["ponto"],
                        "montante": r["montante"],
                        "metros": r["metros"],
                        "cabo": r["cabo"],
                        "mono": r["mono"],
                        "bi": r["bi"],
                        "tri": r["tri"],
                        "tri_esp": r["tri_esp"],
                        "carga_esp": r["carga_esp"],
                        "tipo_ip": r["tipo_ip"],
                        "qtd_ip": r["qtd_ip"],
                    }
                )

            return cfg_rows, trecho_data, proj["nome"]
        except Exception as e:
            conn.rollback()
            return None, None, str(e)
        finally:
            conn.close()

    def listar_projetos(self):
        conn = self._get_conn()
        try:
            return conn.execute(
                "SELECT id, nome, data_criacao FROM projetos ORDER BY data_criacao DESC"
            ).fetchall()
        finally:
            conn.close()

    def excluir_projeto(self, pid):
        conn = self._get_conn()
        try:
            with self._lock:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("DELETE FROM projetos WHERE id=?", (pid,))
                conn.commit()
            return True, "Excluído"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def check_nome(self, nome):
        conn = self._get_conn()
        try:
            res = conn.execute(
                "SELECT id FROM projetos WHERE nome=?", (nome.strip(),)
            ).fetchone()
            return res["id"] if res else None
        finally:
            conn.close()
