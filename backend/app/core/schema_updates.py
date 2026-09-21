"""Small, idempotent upgrade for existing device tables; never recreate the database."""
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text

OPTIONAL_DEVICE_COLUMNS = ("asset_number", "model", "ip_address")


def ensure_optional_device_fields(engine):
    columns = {column["name"]: column for column in inspect(engine).get_columns("devices")}
    required = [name for name in OPTIONAL_DEVICE_COLUMNS if not columns[name]["nullable"]]
    if engine.dialect.name == "sqlite" and required:
        _upgrade_sqlite_devices(engine, required)
    elif required and engine.dialect.name != "postgresql":
        raise RuntimeError("设备可选字段升级仅支持 SQLite 和 PostgreSQL")

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            for name in required:
                connection.execute(text(f'ALTER TABLE devices ALTER COLUMN "{name}" DROP NOT NULL'))
        for name in OPTIONAL_DEVICE_COLUMNS:
            connection.execute(text(f'UPDATE devices SET "{name}" = NULL WHERE trim("{name}") = \'\''))


def _upgrade_sqlite_devices(engine, required):
    # SQLite cannot drop NOT NULL directly. Preserve columns, constraints, indexes,
    # triggers and IDs when rebuilding this table; dependent tables are not deleted.
    connection = engine.raw_connection()
    foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    try:
        path = connection.execute("PRAGMA database_list").fetchone()[2]
        if path:
            backup_path = Path(path + ".before-device-optionals-" + datetime.now().strftime("%Y%m%d%H%M%S%f") + ".bak")
            backup_path.touch(mode=0o600, exist_ok=False)
            with sqlite3.connect(str(backup_path)) as backup:
                connection.driver_connection.backup(backup)
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        prior_violations = set(connection.execute("PRAGMA foreign_key_check").fetchall())
        ddl = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='devices'").fetchone()[0]
        for name in required:
            ddl, count = re.subn(
                r'(["`\[]?' + name + r'["`\]]?\s+\w+(?:\([^)]*\))?)\s+NOT\s+NULL\b',
                r'\1', ddl, count=1, flags=re.IGNORECASE,
            )
            if count != 1:
                raise RuntimeError(f"无法安全修改 devices.{name}，已保留原表")
        ddl, count = re.subn(r'^(CREATE\s+TABLE\s+)(?:IF\s+NOT\s+EXISTS\s+)?[^\s(]+',
                            r'\1"devices_optional_new"', ddl, count=1, flags=re.IGNORECASE)
        if count != 1:
            raise RuntimeError("无法识别设备表结构，已保留原表")
        objects = connection.execute("SELECT sql FROM sqlite_master WHERE tbl_name='devices' AND type IN ('index','trigger') AND sql IS NOT NULL").fetchall()
        names = [row[1] for row in connection.execute("PRAGMA table_info(devices)")]
        fields = ", ".join('"' + name.replace('"', '""') + '"' for name in names)
        connection.execute(ddl)
        connection.execute(f"INSERT INTO devices_optional_new ({fields}) SELECT {fields} FROM devices")
        connection.execute("DROP TABLE devices")
        connection.execute("ALTER TABLE devices_optional_new RENAME TO devices")
        for (sql,) in objects:
            connection.execute(sql)
        if set(connection.execute("PRAGMA foreign_key_check").fetchall()) - prior_violations:
            raise RuntimeError("设备表升级外键校验失败，已回滚")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute(f"PRAGMA foreign_keys={int(foreign_keys)}")
        connection.close()
