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
    ('L entrada_no_comal', 'Montadito de Espinaca con Champiñones y Queso'),
    ('L crema',            'Crema de Cilantro'),
    ('L sopa',             'Sopa de Milpa'),
    ('L pasta',            'Espagueti Alfredo'),
    ('L ensalada_A',       'Ensalada de Espinaca con Naranja'),
    ('L molcajete',        'Molcajete de Oreja de Elefante'),
    ('L fuerte_res',       'Flautas de Res'),
    ('L fuerte_pollo',     'Pollo en Salsa Cremosa de Chipotle'),
    ('L fuerte_camaron',   'Camarones a la Talla'),
    ('L fuerte_pescado',   'Filete de Pescado en Salsa de Aceituna Negra'),
    ('L complemento',      'Enfrijoladas Veracruzanas'),
    # MARTES
    ('Ma entrada_no_comal','Quesadilla Frita de Frijol'),
    ('Ma crema',           'Crema de Calabaza con Chile Ancho'),
    ('Ma sopa',            'Sopa de Verduras'),
    ('Ma pasta',           'Fusilli a las Finas Hierbas'),
    ('Ma ensalada_B',      'Ensalada Rusa con Atun'),
    ('Ma fuerte_res',      'Picana a la Parrilla con Chiles Toreados'),
    ('Ma fuerte_cerdo',    'Torta de Pierna'),
    ('Ma fuerte_pollo',    'Pechuga de Pollo Napolitana'),
    ('Ma fuerte_camaron',  'Camarones Costa Brava'),
    ('Ma fuerte_pescado',  'Filete de Pescado al Ajillo'),
    ('Ma complemento',     'Enchiladas Potosinas'),
    # MIERCOLES
    ('Mi entrada_no_comal','Tetela de Queso'),
    ('Mi crema',           'Crema de Chicharron'),
    ('Mi sopa',            'Sopa de Champiñones'),
    ('Mi pasta',           'Sopa Minestrone'),
    ('Mi ensalada_C',      'Ensalada de Melon Zanahoria y Nuez'),
    ('Mi fuerte_res',      'Parrillada de Arrachera'),
    ('Mi fuerte_cerdo',    'Espinazo en Pipian'),
    ('Mi fuerte_pollo',    'Pollo en Salsa Molcajeteada'),
    ('Mi fuerte_camaron',  'Camarones al Vino Blanco'),
    ('Mi fuerte_pescado',  'Tacos de Pescado Estilo Ensenada'),
    ('Mi complemento',     'Chilaquiles Lenador con Pollo o Huevo'),
    # JUEVES
    ('J entrada_no_comal', 'Rollitos de Jamon con Guacamole'),
    ('J crema',            'Sopa Tarasca'),
    ('J sopa',             'Sopa de Ajo'),
    ('J pasta',            'Codito Frio'),
    ('J ensalada_A',       'Ensalada de Espinaca con Naranja'),
    ('J fuerte_res',       'Bistec de Res Encebollado con Frijoles'),
    ('J fuerte_cerdo',     'Costilla de Cerdo en Salsa de Chile Morita con Papas'),
    ('J fuerte_pollo',     'Huarache de Tinga de Pollo'),
    ('J fuerte_camaron',   'Camarones Enchilados al Sarten con Queso'),
    ('J fuerte_pescado',   'Filete de Pescado al Ajo Limon y Especias con Pure de Papa'),
    ('J complemento',      'Tacos Dorados de Papa Ahogados'),
    # VIERNES
    ('V entrada_no_comal', 'Pescadillas'),
    ('V crema',            'Crema de Coliflor con un Toque de Miel'),
    ('V sopa',             'Sopa Azteca'),
    ('V pasta',            'Pasta Pluma con Jalapeno'),
    ('V ensalada_B',       'Ensalada Rusa con Atun'),
    ('V fuerte_res',       'Albondigas al Chipotle'),
    ('V fuerte_cerdo',     'Chicharro en Salsa Verde con Frijoles de la Olla'),
    ('V fuerte_pollo',     'Pechuga de Pollo Empanizada con Ensalada'),
    ('V fuerte_camaron',   'Camarones a la Diabla'),
    ('V fuerte_pescado',   'Filete de Pescado Rockefeller'),
    ('V complemento',      'Chile Relleno de Queso'),
    # SABADO
    ('S entrada_no_comal', 'Chalupas Mixtas'),
    ('S crema',            'Crema Poblana'),
    ('S sopa_pollo',       'Caldo Tlalpeno'),
    ('S pasta',            'Espagueti al Burro'),
    ('S ensalada_C',       'Ensalada de Melon Zanahoria y Nuez'),
    ('S fuerte_res',       'Tacos de Suadero'),
    ('S fuerte_cerdo',     'Carne Enchilada con Chilaquiles'),
    ('S fuerte_pollo',     'Pechuga de Pollo Rellena de Espinacas con Queso'),
    ('S camaron_al_gusto', 'Camarones al Coco con Dip de Mango'),
    ('S pescado_al_gusto', 'Filete de Pescado al Gusto'),
    ('S enchiladas',       'Enchiladas Divorciadas'),
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
