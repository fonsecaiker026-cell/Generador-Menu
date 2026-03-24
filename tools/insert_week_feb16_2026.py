#!/usr/bin/env python3
"""Inserta semana 2026-02-16 (mismas IDs que 2025-02-16, menu identico)"""
import sqlite3, sys
from datetime import date, timedelta, datetime

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/app.db')
conn.row_factory = sqlite3.Row
conn.execute('PRAGMA foreign_keys = ON')

def gid(name):
    r = conn.execute('SELECT id FROM dish WHERE LOWER(name)=LOWER(?)', (name,)).fetchone()
    if not r:
        print(f'  ERROR no encontrado: "{name}"'); return None
    return r['id']

COMAL_ID    = 202
ARROZ_ID    = 1596
PANCITA_ID  = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%pancita%' AND active=1 LIMIT 1").fetchone()['id']
PAELLA_ID   = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%paella%' AND active=1 LIMIT 1").fetchone()['id']
NUGGETS_ID  = conn.execute("SELECT id FROM dish WHERE LOWER(name) LIKE '%nuggets%' AND active=1 LIMIT 1").fetchone()['id']
CHAMORRO_ID = conn.execute("SELECT d.id FROM dish d JOIN dish_tag dt ON d.id=dt.dish_id WHERE dt.tag='friday_chamorro' AND d.active=1 LIMIT 1").fetchone()['id']

print('\n=== INSERTAR SEMANA 2026-02-16 ===')
WEEK_START = date(2026, 2, 16)
existing = conn.execute('SELECT id FROM menu_week WHERE week_start_date=?', (str(WEEK_START),)).fetchone()
if existing:
    print(f'  Ya existe id={existing["id"]}, abortando'); conn.close(); sys.exit(0)

week_id = conn.execute(
    'INSERT INTO menu_week (week_start_date, generated_at, finalized) VALUES (?,?,1)',
    (str(WEEK_START), datetime.now().isoformat())
).lastrowid
print(f'  week_id={week_id}')

def item(d, slot, dish_id):
    if dish_id is None: return
    conn.execute('INSERT INTO menu_item (menu_week_id,menu_date,slot,dish_id,was_exception) VALUES (?,?,?,?,0)',
                 (week_id, str(d), slot, dish_id))

mon,tue,wed,thu,fri,sat = [WEEK_START + timedelta(i) for i in range(6)]

# LUNES — molcajete=res → sin fuerte_res
item(mon,'entrada_comal',    COMAL_ID)
item(mon,'entrada_no_comal', 1380)               # Rollito de Jamón Empanizado Relleno de Queso
item(mon,'crema',            1381)               # Crema de Perejil
item(mon,'sopa',             156)                # Sopa de Verduras
item(mon,'pasta',            gid('Pasta Pluma con Atún'))
item(mon,'ensalada_A',       gid('Ensalada de Espinaca, Pepino y Mango'))
item(mon,'arroz',            ARROZ_ID)
item(mon,'molcajete',        1521)               # Molcajete de Costilla de Res
item(mon,'fuerte_cerdo',     1663)               # Tacos de Chuleta con Nopales y Cebolla
item(mon,'fuerte_pollo',     1550)               # Pechuga de Pollo a la Crema
item(mon,'fuerte_camaron',   1498)               # Camarones a la Mexicana
item(mon,'fuerte_pescado',   685)                # Filete de Pescado en Salsa de Alcaparras
item(mon,'complemento',      1087)               # Tacos Dorados de Papa con Chorizo

# MARTES
item(tue,'entrada_comal',    COMAL_ID)
item(tue,'entrada_no_comal', 1251)               # Chalupas Mixtas
item(tue,'crema',            504)                # Crema de Calabaza
item(tue,'sopa',             431)                # Sopa Alemana
item(tue,'pasta',            gid('Espagueti a la Florentina'))
item(tue,'ensalada_B',       gid('Ensalada de Arándanos con Nuez y Aderezo de Fresa'))
item(tue,'arroz',            ARROZ_ID)
item(tue,'fuerte_res',       1538)               # Tacos Villamelón
item(tue,'fuerte_cerdo',     777)                # Cerdo en Adobo
item(tue,'fuerte_pollo',     gid('Pollo en Salsa Cremosa de Champiñones'))
item(tue,'fuerte_camaron',   1292)               # Camarones Rellenos con Sofrito
item(tue,'fuerte_pescado',   1585)               # Filete de Pescado al Ajo, Limón y Especias con Puré de Papa
item(tue,'complemento',      1101)               # Enchiladas Potosinas

# MIÉRCOLES
item(wed,'entrada_comal',    COMAL_ID)
item(wed,'entrada_no_comal', 1490)               # Rollito Primavera
item(wed,'crema',            164)                # Crema de Elote
item(wed,'sopa',             447)                # Sopa de Huitlacoche
item(wed,'pasta',            1536)               # Sopa Blanca Asturiana
item(wed,'ensalada_C',       gid('Ensalada Argentina (Lechugas, Cebolla Morada, Aceite de Olivo)'))
item(wed,'arroz',            ARROZ_ID)
item(wed,'fuerte_res',       gid('Arrachera con Chilaquiles'))
item(wed,'fuerte_cerdo',     892)                # Torta de Pierna Española
item(wed,'fuerte_pollo',     1540)               # Pechuga de Pollo Rellena de Quintoniles
item(wed,'fuerte_camaron',   1588)               # Camarones Enchilados al Sartén con Queso
item(wed,'fuerte_pescado',   1293)               # Filete de Pescado a la Veracruzana
item(wed,'complemento',      1561)               # Hígado Encebollado

# JUEVES
item(thu,'entrada_comal',    COMAL_ID)
item(thu,'entrada_no_comal', 1544)               # Tacos de Rellena
item(thu,'crema',            gid('Crema de Jitomate Rostizado con Queso de Cabra y Aceite de Olivo'))
item(thu,'sopa',             426)                # Sopa de Lentejas
item(thu,'pasta',            gid('Macarrones con Queso'))
item(thu,'ensalada_A',       gid('Ensalada de Espinaca, Pepino y Mango'))
item(thu,'arroz',            ARROZ_ID)
item(thu,'fuerte_res',       1583)               # Sabanita de Res Invierno
item(thu,'fuerte_cerdo',     1681)               # Costilla de Cerdo en Salsa de Chile Morita con Papas
item(thu,'fuerte_pollo',     1678)               # Pollo en Salsa Cremosa de Chipotle
item(thu,'fuerte_camaron',   758)                # Camarones al Ajillo
item(thu,'fuerte_pescado',   1551)               # Filete de Pescado a los Tres Quesos
item(thu,'complemento',      1336)               # Tortitas de Coliflor Rellenas de Queso en Caldillo

# VIERNES
item(fri,'entrada_comal',    COMAL_ID)
item(fri,'entrada_no_comal', 1501)               # Tostada de Pata
item(fri,'crema',            163)                # Crema Poblana
item(fri,'sopa',             1503)               # Consomé de Birria de Res
item(fri,'pasta',            1424)               # Espagueti Rojo Cremoso
item(fri,'ensalada_B',       gid('Ensalada de Arándanos con Nuez y Aderezo de Fresa'))
item(fri,'arroz',            ARROZ_ID)
item(fri,'chamorro',         CHAMORRO_ID)
item(fri,'fuerte_res',       962)                # Tacos de Birria de Res
item(fri,'fuerte_cerdo',     gid('Espinazo de Cerdo en Salsa de Chile de Árbol'))
item(fri,'fuerte_pollo',     1363)               # Pollo en Mole Verde
item(fri,'fuerte_camaron',   731)                # Camarones Empanizados
item(fri,'fuerte_pescado',   gid('Filete de Pescado a la Mantequilla con Puré de Camote'))
item(fri,'complemento',      1072)               # Tortitas de Papa con Ensalada

# SÁBADO
item(sat,'entrada_comal',    COMAL_ID)
item(sat,'entrada_no_comal', 1326)               # Tlacoyo de Chicharrón
item(sat,'pancita',          PANCITA_ID)
item(sat,'crema',            1563)               # Crema de Coliflor con un Toque de Miel
item(sat,'sopa_pollo',       544)                # Caldo Loco
item(sat,'ensalada_C',       gid('Ensalada Argentina (Lechugas, Cebolla Morada, Aceite de Olivo)'))
item(sat,'pasta',            gid('Fettuccino Alfredo'))
item(sat,'fuerte_res',       901)                # Flautas de Res
item(sat,'fuerte_cerdo',     855)                # Chorizo Argentino con Papas Fritas y Chiles Toreados
item(sat,'fuerte_pollo',     1300)               # Pechuga de Pollo Parmesana
item(sat,'paella',           PAELLA_ID)
item(sat,'pescado_al_gusto', 1310)               # Filete de Pescado al Gusto
item(sat,'camaron_al_gusto', 1417)               # Camarones al Tamarindo Habanero o al Gusto
item(sat,'nuggets',          NUGGETS_ID)
item(sat,'enchiladas',       1419)               # Enchiladas Entomatadas Cremosas

conn.commit()

total = conn.execute('SELECT COUNT(*) FROM menu_item WHERE menu_week_id=?', (week_id,)).fetchone()[0]
print(f'\n  ✓ Semana 2026-02-16 insertada — {total} items')
for d_str in ['2026-02-16','2026-02-17','2026-02-18','2026-02-19','2026-02-20','2026-02-21']:
    n = conn.execute('SELECT COUNT(*) FROM menu_item WHERE menu_week_id=? AND menu_date=?',
                     (week_id, d_str)).fetchone()[0]
    print(f'  {d_str}: {n} slots')

conn.close()
print('\nDone.')
