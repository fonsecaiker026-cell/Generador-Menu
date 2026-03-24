#!/usr/bin/env python3
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/app.db'); conn.row_factory = sqlite3.Row

def find(q):
    words = [w for w in q.lower().split() if len(w) > 3]
    r = conn.execute('SELECT id,name FROM dish WHERE active=1 AND LOWER(name) LIKE ? LIMIT 3',
                     (f'%{q.lower()[:30]}%',)).fetchall()
    if r: return [(x['id'],x['name']) for x in r]
    if len(words) >= 2:
        r = conn.execute('SELECT id,name FROM dish WHERE active=1 AND LOWER(name) LIKE ? AND LOWER(name) LIKE ? LIMIT 3',
                         (f'%{words[0]}%',f'%{words[1]}%')).fetchall()
        if r: return [(x['id'],x['name']) for x in r]
    if words:
        r = conn.execute('SELECT id,name FROM dish WHERE active=1 AND LOWER(name) LIKE ? LIMIT 3',
                         (f'%{words[0]}%',)).fetchall()
        return [(x['id'],x['name']) for x in r[:2]]
    return []

dishes = [
    # LUNES
    ('L entrada_no_comal', 'Rollito de Jamon Empanizado Relleno de Queso'),
    ('L crema',            'Crema de Perejil'),
    ('L sopa',             'Sopa de Verduras'),
    ('L pasta',            'Pasta Pluma con Atun'),
    ('L ensalada_A',       'Ensalada de Espinaca Pepino y Mango'),
    ('L molcajete',        'Molcajete de Costilla de Res'),
    ('L fuerte_cerdo',     'Tacos de Chuleta de Cerdo con Nopales y Cebolla Cambray'),
    ('L fuerte_pollo',     'Pechuga de Pollo a la Crema'),
    ('L fuerte_camaron',   'Camarones a la Mexicana'),
    ('L fuerte_pescado',   'Filete de Pescado en Salsa Cremosa de Alcaparras'),
    ('L complemento',      'Tacos Dorados de Papa con Chorizo'),
    # MARTES
    ('Ma entrada_no_comal','Chalupas Mixtas'),
    ('Ma crema',           'Crema de Calabaza'),
    ('Ma sopa',            'Sopa Alemana'),
    ('Ma pasta',           'Espagueti a la Florentina'),
    ('Ma ensalada_B',      'Ensalada de Arandanos con Nuez y Aderezo de Fresa'),
    ('Ma fuerte_res',      'Tacos Villamelon'),
    ('Ma fuerte_cerdo',    'Cerdo en Adobo'),
    ('Ma fuerte_pollo',    'Pollo en Salsa Cremosa de Champiñones'),
    ('Ma fuerte_camaron',  'Camarones Rellenos Sofrito Cebolla Serrano en Tocino'),
    ('Ma fuerte_pescado',  'Filete de Pescado al Ajo Limon y Especias'),
    ('Ma complemento',     'Enchiladas Potosinas'),
    # MIERCOLES
    ('Mi entrada_no_comal','Rollito Primavera'),
    ('Mi crema',           'Crema de Elote'),
    ('Mi sopa',            'Sopa de Huitlacoche'),
    ('Mi pasta',           'Sopa Blanca Asturiana'),
    ('Mi ensalada_C',      'Ensalada Argentina Mix Lechugas Cebolla Morada'),
    ('Mi fuerte_res',      'Arrachera con Chilaquiles'),
    ('Mi fuerte_cerdo',    'Torta de Pierna Española'),
    ('Mi fuerte_pollo',    'Pechuga de Pollo Rellena de Quintoniles'),
    ('Mi fuerte_camaron',  'Camarones Enchilados al Sarten con Queso'),
    ('Mi fuerte_pescado',  'Filete de Pescado a la Veracruzana'),
    ('Mi complemento',     'Higado Encebollado'),
    # JUEVES
    ('J entrada_no_comal', 'Tacos de Rellena'),
    ('J crema',            'Crema de Jitomate Rostizado con Queso de Cabra'),
    ('J sopa',             'Sopa de Lentejas'),
    ('J pasta',            'Macarrones con Queso'),
    ('J ensalada_A',       'Ensalada de Espinaca Pepino y Mango'),
    ('J fuerte_res',       'Sabanita de Res Invierno'),
    ('J fuerte_cerdo',     'Costilla de Cerdo en Salsa de Chile Morita con Papas'),
    ('J fuerte_pollo',     'Pollo en Salsa Cremosa de Chipotle'),
    ('J fuerte_camaron',   'Camarones al Ajillo'),
    ('J fuerte_pescado',   'Filete de Pescado a los Tres Quesos'),
    ('J complemento',      'Tortitas de Coliflor Capeadas Rellenas de Queso en Caldillo'),
    # VIERNES
    ('V entrada_no_comal', 'Tostada de Pata'),
    ('V crema',            'Crema Poblana'),
    ('V sopa',             'Consome de Birria de Res'),
    ('V pasta',            'Espagueti Rojo Cremoso'),
    ('V ensalada_B',       'Ensalada de Arandanos con Nuez y Aderezo de Fresa'),
    ('V fuerte_res',       'Tacos de Birria de Res'),
    ('V fuerte_cerdo',     'Espinazo de Cerdo en Salsa de Chile de Arbol'),
    ('V fuerte_pollo',     'Pollo en Mole Verde'),
    ('V fuerte_camaron',   'Camarones Empanizados'),
    ('V fuerte_pescado',   'Filete de Pescado a la Mantequilla con Pure de Camote'),
    ('V complemento',      'Tortitas de Papa con Ensalada'),
    # SABADO
    ('S entrada_no_comal', 'Tlacoyo de Chicharron'),
    ('S crema',            'Crema de Coliflor con un Toque de Miel'),
    ('S sopa_pollo',       'Caldo Loco'),
    ('S pasta',            'Fetuccino Alfredo'),
    ('S ensalada_C',       'Ensalada Argentina Mix Lechugas Cebolla Morada'),
    ('S fuerte_res',       'Flautas de Res'),
    ('S fuerte_cerdo',     'Chorizo Argentino con Papas a la Francesa'),
    ('S fuerte_pollo',     'Pechuga de Pollo Parmesana'),
    ('S camaron_al_gusto', 'Camarones al Tamarindo Habanero al Gusto'),
    ('S pescado_al_gusto', 'Filete de Pescado al Gusto'),
    ('S enchiladas',       'Enchiladas Entomatadas Cremosas'),
]

print(f'{"Día/Slot":<22} {"Buscado":<50} Encontrado')
print('-'*130)
no_found = []
for slot, name in dishes:
    r = find(name)
    found = '  |  '.join(f'[{x[0]}] {x[1]}' for x in r[:2]) if r else '*** NO ENCONTRADO ***'
    print(f'{slot:<22} {name:<50} {found}')
    if not r:
        no_found.append((slot, name))

print(f'\nNo encontrados: {len(no_found)}')
for s, n in no_found:
    print(f'  {s}: {n}')
