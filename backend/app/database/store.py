import json, sqlite3
from app.core.config import db_path

def connect():
    con=sqlite3.connect(db_path())
    con.execute("CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind,id))")
    con.commit()
    return con

def save(kind: str, ident: str, payload: dict):
    con=connect()
    con.execute("INSERT OR REPLACE INTO records(kind,id,payload) VALUES(?,?,?)",(kind,ident,json.dumps(payload,default=str)))
    con.commit(); con.close()

def get(kind: str, ident: str):
    con=connect(); row=con.execute("SELECT payload FROM records WHERE kind=? AND id=?",(kind,ident)).fetchone(); con.close()
    return json.loads(row[0]) if row else None

def list_kind(kind: str):
    con=connect(); rows=con.execute("SELECT payload FROM records WHERE kind=? ORDER BY rowid",(kind,)).fetchall(); con.close()
    return [json.loads(x[0]) for x in rows]
