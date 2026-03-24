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
    ('L entrada_no_comal', 'Quesadilla Frita de Requeson'),
    ('L crema',            'Crema de Papa con Tocino'),
    ('L sopa',             'Sopa de Nopal'),
    ('L pasta',            'Codito Frio'),
    ('L ensalada_A',       'Ensalada Verde con Mango'),
    ('L molcajete',        'Molcajete de Agujas Nortenas'),
    ('L fuerte_cerdo',     'Cerdo en Guajillo con Nopales'),
    ('L fuerte_pollo',     'Pechuga de Pollo Rellena de Elote con Queso'),
    ('L fuerte_camaron',   'Camarones al Tequila'),
    ('L fuerte_pescado',   'Filete de Pescado en Salsa de Aguacate'),
    ('L complemento',      'Croquetas de Atun con Ensalada'),
    # MARTES
    ('Ma entrada_no_comal','Gordita de Chicharron'),
    ('Ma crema',           'Crema de Flor de Calabaza'),
    ('Ma sopa',            'Sopa Poblana'),
    ('Ma pasta',           'Fusilli Pesto'),
    ('Ma ensalada_B',      'Ensalada de Piña con Arandanos'),
    ('Ma fuerte_res',      'Tacos de Gaonera'),
    ('Ma fuerte_cerdo',    'Longaniza en Salsa Verde con Frijoles de la Olla'),
    ('Ma fuerte_pollo',    'Pollo en Salsa Tatemada'),
    ('Ma fuerte_camaron',  'Camarones con Jalapeno'),
    ('Ma fuerte_pescado',  'Filete de Pescado a la Mantequilla Negra con Pure de Papa'),
    ('Ma complemento',     'Enchiladas Mineras'),
    # MIERCOLES
    ('Mi entrada_no_comal','Taco Placero'),
    ('Mi crema',           'Crema de Zanahoria'),
    ('Mi sopa',            'Sopa de Alubias'),
    ('Mi pasta',           'Espagueti al Mojo'),
    ('Mi ensalada_C',      'Calabacitas Grill'),
    ('Mi fuerte_res',      'Colita de Res en Adobo'),
    ('Mi fuerte_cerdo',    'Pierna de Cerdo al Horno con Pure de Papa'),
    ('Mi fuerte_pollo',    'Pollo en Salsa Borracha'),
    ('Mi fuerte_camaron',  'Tacos Gobernador'),
    ('Mi fuerte_pescado',  'Filete de Pescado en Salsa Cremosa de Champiñones'),
    ('Mi complemento',     'Nopal Empanizado Relleno de Queso en Espejo de Guajillo'),
    # JUEVES
    ('J entrada_no_comal', 'Tlacoyo de Frijol'),
    ('J crema',            'Crema de Espinaca con Nuez'),
    ('J sopa',             'Sopa de Cebolla'),
    ('J pasta',            'Sopa de Pasta Municion'),
    ('J ensalada_A',       'Ensalada Verde con Mango'),
    ('J fuerte_res',       'Costilla de Res con Chilaquiles Rojos'),
    ('J fuerte_cerdo',     'Carne Enchilada con Guacamole y Frijoles de la Olla'),
    ('J fuerte_pollo',     'Pollo a la Barbacoa'),
    ('J fuerte_camaron',   'Alambre de Camaron'),
    ('J fuerte_pescado',   'Filete de Pescado Sol con Ensalada'),
    ('J complemento',      'Tortitas de Espinaca Rellenas de Queso en Salsa Verde'),
    # VIERNES
    ('V entrada_no_comal', 'Mini Tostadas de Surimi'),
    ('V crema',            'Crema Conde'),
    ('V sopa',             'Chilpachole de Jaiba'),
    ('V pasta',            'Fetuccini al Aglio Olio'),
    ('V ensalada_B',       'Ensalada de Piña con Arandanos'),
    ('V fuerte_res',       'Entomatado de Res'),
    ('V fuerte_cerdo',     'Machitos de Carnero con Guacamole'),
    ('V fuerte_pollo',     'Pechuga de Pollo al Chimichurri'),
    ('V fuerte_camaron',   'Tortitas de Atun en Salsa de Chile Pasilla'),
    ('V fuerte_pescado',   'Filete de Pescado Empanizado con Ensalada'),
    ('V complemento',      'Torta de Queso de Puerco'),
    # SABADO
    ('S entrada_no_comal', 'Pambacito'),
    ('S crema',            'Crema de Esquites'),
    ('S sopa_pollo',       'Consome Ranchero'),
    ('S pasta',            'Espagueti a los Tres Quesos'),
    ('S ensalada_C',       'Calabacitas Grill'),
    ('S fuerte_res',       'Hamburguesa Tradicional con Tocino'),
    ('S fuerte_cerdo',     'Costillas BBQ'),
    ('S fuerte_pollo',     'Pechuga de Pollo Oaxaqueña'),
    ('S camaron_al_gusto', 'Aguachile de Camaron al Gusto'),
    ('S pescado_al_gusto', 'Filete de Pescado al Gusto'),
    ('S enchiladas',       'Enchiladas Suizas'),
]

print(f'{"Día/Slot":<22} {"Buscado":<50} Encontrado')
print('-'*130)
for slot, name in dishes:
    r = find(name)
    found = '  |  '.join(f'[{x[0]}] {x[1]}' for x in r[:2]) if r else '*** NO ENCONTRADO ***'
    print(f'{slot:<22} {name:<50} {found}')
