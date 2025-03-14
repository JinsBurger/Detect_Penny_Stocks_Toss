import sqlite3
import os

def open_sqlite3(db_path, create=False):
    if not create and not os.path.exists(db_path):
        raise f"Failed to open {db_path}"
    elif create and os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    return cur, conn

def read_stocks_from_db(dbcur):
    dbcur.execute("SELECT * FROM stocks")
    result = {}
    for st in dbcur.fetchall():
        result[st["stock_code"]] = {
            "stock_code": st["stock_code"],
            "stock_name": st["stock_name"],
            "avg_volume": int(st["avg_volume"]),
            "comments_count": int(st["comments_count"]),
            "recent_comments_json": st["recent_comments_json"],
            "price": float(st["price"]),
        }

    return result

def record_stock_log(db_path, stock_code, last_comment, cur_volume, cur_price, is_penny):
    db_cur, db_conn = open_sqlite3(db_path, create=False)
    db_cur.execute(
        "INSERT INTO stock_log (stock_code, timestamp, last_comment, volume, price, is_penny)\
        VALUES (?, DATETIME('now', 'localtime'), ?, ?, ?, ?)",
        (stock_code, last_comment, cur_volume, cur_price, is_penny)
    )
    db_conn.commit()
    db_conn.close()