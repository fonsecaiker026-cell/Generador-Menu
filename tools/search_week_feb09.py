#!/usr/bin/env python3
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/app.db')
conn.row_factory = sqlite3.Row

def find(q):
    words = [w for w in q.lower().split() if len(w) > 3]
    r = conn.execute('SELECT id, name FROM dish WHERE active=1 AND LOWER(name) LIKE ? LIMIT 3',
                     (f'%{q.lower()[:28]}%',)).fetchall()
    if r: return [(x['id'], x['name']) for x in r]
    if len(words) >= 2:
        r = conn.execute('SELECT id, name FROM dish WHERE active=1 AND LOWER(name) LIKE ? AND LOWER(name) LIKE ? LIMIT 3',
                         (f'%{words[0]}%', f'%{words[1]}%')).fetchall()
        if r: return [(x['id'], x['name']) for x in r]
    if words:
        r = conn.execute('SELECT id, name FROM dish WHERE active=1 AND LOWER(name) LIKE ? LIMIT 3',
                         (f'%{words[0]}%',)).fetchall()
        if r: return [(x['id'], x['name']) for x in r[:2]]
    return []

dishes = [
    # LUNES
    ('L entrada_no_comal', 'Taco de Rajas con Crema'),
    ('L crema',            'Crema de Calabaza'),
    ('L sopa',             'Sopa de Champiñones'),
    ('L pasta',            'Sopa de Pasta con Almeja'),
    ('L ensalada_A',       'Ensalada de Betabel con Naranja'),
    ('L molcajete',        'Molcajete de Carne Enchilada'),
    ('L fuerte_res',       'Arrachera Tex-Mex'),
    ('L fuerte_pollo',     'Pechuga de Pollo Primavera'),
    ('L fuerte_camaron',   'Camarones Costa Brava'),
    ('L fuerte_pescado',   'Filete de Pescado al Chiltepin'),
    ('L complemento',      'Enchiladas Mineras'),
    # MARTES
    ('Ma entrada_no_comal','Taco Placero'),
    ('Ma crema',           'Crema de Jalapeno con Queso'),
    ('Ma sopa',            'Sopa de Ajo'),
    ('Ma pasta',           'Espagueti a las Finas Hierbas'),
    ('Ma ensalada_B',      'Ensalada de Espinaca con Manzana'),
    ('Ma fuerte_res',      'Huarache con Costilla de Res'),
    ('Ma fuerte_cerdo',    'Chuleta de Cerdo Ahumada con Ensalada y Papas'),
    ('Ma fuerte_camaron',  'Tacos de Camaron con Guacamole'),
    ('Ma fuerte_pescado',  'Filete de Pescado Zarandeado'),
    ('Ma complemento',     'Croquetas de Atun con Ensalada'),
    # MIERCOLES
    ('Mi entrada_no_comal','Aros de Cebolla'),
    ('Mi crema',           'Crema de Setas con Epazote'),
    ('Mi sopa',            'Frijoles Charros'),
    ('Mi pasta',           'Fusilli a las Finas Hierbas con Aceite de Olivo'),
    ('Mi ensalada_C',      'Ensalada de Jitomate Cantinera'),
    ('Mi fuerte_res',      'Parrillada de Agujas Nortenas'),
    ('Mi fuerte_cerdo',    'Cerdo en Salsa de Chile Morita con Nopales'),
    ('Mi fuerte_pollo',    'Pechuga Rellena de Huitlacoche'),
    ('Mi fuerte_camaron',  'Camarones a la Talla'),
    ('Mi fuerte_pescado',  'Filete de Pescado en Salsa de Aceituna Negra'),
    ('Mi complemento',     'Tortitas de Espinaca Rellenas de Queso en Salsa Verde'),
    # JUEVES
    ('J entrada_no_comal', 'Montadito de Espinaca con Queso'),
    ('J crema',            'Crema de Cilantro'),
    ('J sopa',             'Caldo de Papa con Queso'),
    ('J pasta',            'Fetuccini al Pesto'),
    ('J ensalada_A',       'Ensalada de Betabel con Naranja'),
    ('J fuerte_res',       'Bistec de Res Encebollado'),
    ('J fuerte_cerdo',     'Cerdo en Pipian'),
    ('J fuerte_pollo',     'Pollo a la Barbacoa'),
    ('J fuerte_camaron',   'Camarones a la Diabla'),
    ('J fuerte_pescado',   'Filete de Pescado a la Mantequilla Vaquera'),
    ('J complemento',      'Torta de Jamon con Frijoles Queso Jitomate'),
    # VIERNES
    ('V entrada_no_comal', 'Gordita de Frijol'),
    ('V crema',            'Crema de Chicharron'),
    ('V sopa',             'Jugo de Carne'),
    ('V pasta',            'Fideo Seco con Mole'),
    ('V ensalada_B',       'Ensalada de Espinaca con Manzana'),
    ('V fuerte_res',       'Albondigas al Chipotle'),
    ('V fuerte_cerdo',     'Oreja de Elefante con Ensalada'),
    ('V fuerte_pollo',     'Tortitas de Pollo en Salsa Verde'),
    ('V fuerte_camaron',   'Aguacate Relleno de Atun'),
    ('V fuerte_pescado',   'Filete de Pescado en Salsa Cremosa de Espinaca'),
    ('V complemento',      'Chile Relleno de Queso'),
    # SABADO
    ('S entrada_no_comal', 'Empanada Argentina de Espinacas con Queso'),
    ('S crema',            'Crema de Queso con Uvas'),
    ('S sopa_pollo',       'Pozole de Cerdo'),
    ('S pasta',            'Fusilli a las Finas Hierbas con Aceite de Olivo'),
    ('S ensalada_C',       'Ensalada Paraiso Espinaca Lechuga Fresa'),
    ('S fuerte_res',       'Rib Eye a la Parrilla con Chiles Toreados'),
    ('S fuerte_cerdo',     'Medallones de Cerdo a los Tres Chiles'),
    ('S fuerte_camaron',   'Camarones al Coco con Dip de Mango'),
    ('S fuerte_pollo',     'Pechuga Cordon Bleu'),
    ('S pescado_al_gusto', 'Filete de Pescado al Vino Blanco con Almejas'),
    ('S camaron_al_gusto', 'Tostada de Ceviche de Pescado'),
    ('S enchiladas',       'Enchiladas Rojas'),  # need to find Saturday enchiladas
]

print(f'{"Día/Slot":<22} {"Buscado":<42} Encontrado')
print('-' * 120)
no_found = []
for slot, name in dishes:
    results = find(name)
    if results:
        found_str = '  |  '.join(f'[{r[0]}] {r[1]}' for r in results[:2])
        print(f'{slot:<22} {name:<42} {found_str}')
    else:
        print(f'{slot:<22} {name:<42} *** NO ENCONTRADO ***')
        no_found.append((slot, name))

print(f'\nNo encontrados: {len(no_found)}')
for s, n in no_found:
    print(f'  {s}: {n}')
