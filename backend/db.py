# backend/db.py
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
    DEFAULT_COL_ORDER,
)

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
        # check_same_thread=False é necessário para FastAPI/Streamlit,
        # mas o _lock garante a segurança de escrita.
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Melhor concorrência
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            with conn:
                # Tabelas do Projeto (Mantidas)
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS projetos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, data_criacao TEXT)"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cenarios_config (id INTEGER PRIMARY KEY, projeto_id INTEGER, nome_cenario TEXT, trafo_kva INTEGER, classe_tipo TEXT, classe_manual TEXT, fp_ip REAL, perfil TEXT, FOREIGN KEY(projeto_id) REFERENCES projetos(id) ON DELETE CASCADE, UNIQUE(projeto_id, nome_cenario))"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS trechos (id INTEGER PRIMARY KEY, projeto_id INTEGER, nome_cenario TEXT, ponto TEXT, montante TEXT, metros REAL, cabo TEXT, mono INTEGER, bi INTEGER, tri INTEGER, tri_esp INTEGER, carga_esp REAL, tipo_ip TEXT, qtd_ip INTEGER, FOREIGN KEY(projeto_id) REFERENCES projetos(id) ON DELETE CASCADE)"""
                )

                # Tabelas de Configuração
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cfg_cabos (nome TEXT PRIMARY KEY, coeficiente REAL, preco REAL)"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cfg_ips (nome TEXT PRIMARY KEY, potencia_watts REAL, preco REAL)"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cfg_trafos (kva REAL PRIMARY KEY)"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cfg_perfis (nome TEXT PRIMARY KEY, cqt_max REAL, sobrecarga_max REAL, metros_max REAL, clientes_max INTEGER)"""
                )

                # [MELHORIA] Nova Tabela de Demandas (Configurável)
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS cfg_demandas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    min_cli INTEGER, max_cli INTEGER, 
                    fator_a REAL, fator_b REAL, fator_c REAL, fator_d REAL
                )"""
                )

                self._seed_defaults(conn)
        except:
            pass
        finally:
            conn.close()

    def _seed_defaults(self, conn):
        # Seed Trafos
        if not conn.execute("SELECT 1 FROM cfg_trafos").fetchone():
            conn.executemany(
                "INSERT INTO cfg_trafos (kva) VALUES (?)",
                [(t,) for t in DEFAULT_TRAFOS_LISTA],
            )
        # Seed Perfis
        if not conn.execute("SELECT 1 FROM cfg_perfis").fetchone():
            data = []
            for p in DEFAULT_PERFIS:
                if len(p) == 5:
                    data.append(p)
                else:
                    data.append((p[0], p[1], p[2], 3000.0, 2000))
            conn.executemany("INSERT INTO cfg_perfis VALUES (?,?,?,?,?)", data)

        # [MELHORIA] Seed Demandas
        if not conn.execute("SELECT 1 FROM cfg_demandas").fetchone():
            # TABELA_DEMANDA format: (De, Até, A, B, C, D)
            conn.executemany(
                "INSERT INTO cfg_demandas (min_cli, max_cli, fator_a, fator_b, fator_c, fator_d) VALUES (?,?,?,?,?,?)",
                TABELA_DEMANDA,
            )

    def load_configs(self):
        conn = self._get_conn()
        try:
            # Carrega Cabos e IPs (com fallback em memória se vazio)
            db_cabos = conn.execute("SELECT * FROM cfg_cabos").fetchall()
            cabos = (
                {
                    r["nome"]: {"coef": r["coeficiente"], "preco": r["preco"]}
                    for r in db_cabos
                }
                if db_cabos
                else {
                    k: {"coef": v if not isinstance(v, list) else v[0], "preco": 0.0}
                    for k, v in DEFAULT_CABOS.items()
                }
            )

            db_ips = conn.execute("SELECT * FROM cfg_ips").fetchall()
            ips = (
                {
                    r["nome"]: {"pot": r["potencia_watts"], "preco": r["preco"]}
                    for r in db_ips
                }
                if db_ips
                else {k: {"pot": v, "preco": 0.0} for k, v in DEFAULT_IPS.items()}
            )

            trafos = [
                r["kva"]
                for r in conn.execute(
                    "SELECT * FROM cfg_trafos ORDER BY kva"
                ).fetchall()
            ]
            perfis = {
                r["nome"]: {
                    "cqt_max": r["cqt_max"],
                    "sobrecarga_max": r["sobrecarga_max"],
                }
                for r in conn.execute("SELECT * FROM cfg_perfis").fetchall()
            }

            # [MELHORIA] Carrega Demandas
            demandas = conn.execute(
                "SELECT min_cli, max_cli, fator_a, fator_b, fator_c, fator_d FROM cfg_demandas ORDER BY min_cli"
            ).fetchall()
            # Converte para lista de tuplas compatível com o engine
            demandas_list = [
                (
                    r["min_cli"],
                    r["max_cli"],
                    r["fator_a"],
                    r["fator_b"],
                    r["fator_c"],
                    r["fator_d"],
                )
                for r in demandas
            ]

            return cabos, ips, trafos, perfis, demandas_list
        finally:
            conn.close()

    def check_needs_setup(self) -> bool:
        conn = self._get_conn()
        try:
            has_cabos = conn.execute("SELECT 1 FROM cfg_cabos LIMIT 1").fetchone()
            return not has_cabos
        finally:
            conn.close()

    def update_configs(self, type_key, df):
        conn = self._get_conn()
        try:
            with self._lock:
                conn.execute("BEGIN IMMEDIATE")
                if type_key == "cabos":
                    conn.execute("DELETE FROM cfg_cabos")
                    data = df[["nome", "coeficiente", "preco"]].values.tolist()
                    conn.executemany(
                        "INSERT INTO cfg_cabos (nome, coeficiente, preco) VALUES (?,?,?)",
                        data,
                    )
                elif type_key == "ips":
                    conn.execute("DELETE FROM cfg_ips")
                    data = df[["nome", "potencia_watts", "preco"]].values.tolist()
                    conn.executemany(
                        "INSERT INTO cfg_ips (nome, potencia_watts, preco) VALUES (?,?,?)",
                        data,
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
            return True, "Configurações salvas e aplicadas!"
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

                exist_id = None
                row = conn.execute(
                    "SELECT id FROM projetos WHERE nome=?", (nome,)
                ).fetchone()
                if row:
                    exist_id = row["id"]

                if overwrite_id:
                    pid = overwrite_id
                    if exist_id and exist_id != pid:
                        raise ValueError(
                            f"O nome '{nome}' já está em uso por outro projeto."
                        )
                    conn.execute(
                        "UPDATE projetos SET nome=?, data_criacao=? WHERE id=?",
                        (nome, ts, pid),
                    )
                    conn.execute(
                        "DELETE FROM cenarios_config WHERE projeto_id=?", (pid,)
                    )
                    conn.execute("DELETE FROM trechos WHERE projeto_id=?", (pid,))
                    msg = "atualizado"
                else:
                    if exist_id:
                        pid = exist_id
                        conn.execute(
                            "UPDATE projetos SET data_criacao=? WHERE id=?", (ts, pid)
                        )
                        conn.execute(
                            "DELETE FROM cenarios_config WHERE projeto_id=?", (pid,)
                        )
                        conn.execute("DELETE FROM trechos WHERE projeto_id=?", (pid,))
                        msg = "atualizado (sobrescrito)"
                    else:
                        cur = conn.execute(
                            "INSERT INTO projetos (nome, data_criacao) VALUES (?, ?)",
                            (nome, ts),
                        )
                        pid = cur.lastrowid
                        msg = "criado"

                cfgs_data, trechos_data = [], []

                for aba, df in dados_dict.items():
                    if df.empty:
                        continue
                    df_safe = df.copy()
                    for col in [
                        "PONTO",
                        "MONTANTE",
                        "CABO",
                        "TIPO_IP",
                        "METROS",
                        "MONO",
                        "BIFÁSICO",
                        "TRIFÁSICO",
                        "TRI ESPECIAL",
                        "CARGA_ESP_KVA",
                        "QTD_IP",
                    ]:
                        if col not in df_safe.columns:
                            df_safe[col] = (
                                0
                                if col not in ["PONTO", "MONTANTE", "CABO", "TIPO_IP"]
                                else ""
                            )

                    p = params_dict.get(aba, DEFAULT_PARAMS)
                    cfgs_data.append(
                        (
                            pid,
                            aba,
                            p["trafo_kva"],
                            p["classe_tipo"],
                            p["classe_manual"],
                            p.get("fp_ip", 0.92),
                            p.get("perfil", ""),
                        )
                    )

                    for _, r in df_safe.iterrows():
                        ponto = safe_str(r["PONTO"])
                        if not ponto:
                            continue  # Salva TRAFO também

                        trechos_data.append(
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
                    cfgs_data,
                )
                conn.executemany(
                    "INSERT INTO trechos (projeto_id, nome_cenario, ponto, montante, metros, cabo, mono, bi, tri, tri_esp, carga_esp, tipo_ip, qtd_ip) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    trechos_data,
                )
                conn.commit()
                return True, f"Projeto '{nome}' {msg}!"
        except Exception as e:
            conn.rollback()
            return False, str(e)
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

    def carregar_projeto(self, pid: int):
        conn = self._get_conn()
        try:
            proj = conn.execute(
                "SELECT nome FROM projetos WHERE id=?", (pid,)
            ).fetchone()
            if not proj:
                return None, None, "Projeto não encontrado"

            cfg_rows = conn.execute(
                "SELECT * FROM cenarios_config WHERE projeto_id=?", (pid,)
            ).fetchall()
            trecho_rows = conn.execute(
                "SELECT * FROM trechos WHERE projeto_id=? ORDER BY id ASC", (pid,)
            ).fetchall()
            trecho_data = [dict(r) for r in trecho_rows]
            return cfg_rows, trecho_data, proj["nome"]
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

    def excluir_projeto(self, pid: int) -> Tuple[bool, str]:
        conn = self._get_conn()
        try:
            with self._lock:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("DELETE FROM projetos WHERE id=?", (pid,))
                conn.commit()
            return True, "Projeto excluído com sucesso."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
