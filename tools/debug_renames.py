import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
DB = 'data/app.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

renames = [
    (632,  'Filete de Pescado al Ajillo'),
    (1127, 'Tortitas de Coliflor Rellenas de Queso en Caldillo de Jitomate'),
    (1432, 'Cuaresmeño Relleno de Chorizo con Queso'),
    (451,  'Sopa de Flor de Calabaza con Pollo'),
    (723,  'Alambre de Camarón'),
    (1365, 'Aguachile de Camarón al Gusto'),
]
for dish_id, new_name in renames:
    old = conn.execute('SELECT name FROM dish WHERE id=?', (dish_id,)).fetchone()
    old_name = old[0] if old else '?'
    print(f'Trying {dish_id}: {repr(old_name)} -> {repr(new_name)}')
    try:
        conn.execute('UPDATE dish SET name=? WHERE id=?', (new_name, dish_id))
        print('  OK')
    except Exception as e:
        print(f'  FAIL: {e}')
        conflict = conn.execute('SELECT id, name FROM dish WHERE name=?', (new_name,)).fetchall()
        print(f'  conflict rows: {[dict(r) for r in conflict]}')
conn.rollback()
print('done')
