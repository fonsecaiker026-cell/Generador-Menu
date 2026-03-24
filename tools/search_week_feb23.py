#!/usr/bin/env python3
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/app.db')
conn.row_factory = sqlite3.Row

def find(q):
    words = [w for w in q.lower().split() if len(w) > 3]
    r = conn.execute('SELECT id, name FROM dish WHERE active=1 AND LOWER(name) LIKE ? LIMIT 3',
                     (f'%{q.lower()[:30]}%',)).fetchall()
    if r: return [(x['id'], x['name']) for x in r]
    if len(words) >= 2:
        r = conn.execute('SELECT id, name FROM dish WHERE active=1 AND LOWER(name) LIKE ? AND LOWER(name) LIKE ? LIMIT 3',
                         (f'%{words[0]}%', f'%{words[1]}%')).fetchall()
        if r: return [(x['id'], x['name']) for x in r]
    if words:
        r = conn.execute('SELECT id, name FROM dish WHERE active=1 AND LOWER(name) LIKE ? LIMIT 3',
                         (f'%{words[0]}%',)).fetchall()
        return [(x['id'], x['name']) for x in r[:2]]
    return []

dishes = [
    # LUNES
    ('L entrada_no_comal', 'Dobladita de Papa con Epazote'),
    ('L crema',            'Crema de Jalapeño con Queso'),
    ('L sopa',             'Sopa de Setas'),
    ('L pasta',            'Espagueti al Ajillo'),
    ('L ensalada_A',       'Ensalada de Pepino a la Vinagreta'),
    ('L molcajete',        'Molcajete de Arrachera'),
    ('L fuerte_cerdo',     'Cerdo en Salsa de Chile Pasilla'),
    ('L fuerte_pollo',     'Pechuga de Pollo al Chimichurri'),
    ('L fuerte_camaron',   'Camarones al Cilantro y Chile Limon'),
    ('L fuerte_pescado',   'Filete de Pescado en Salsa Cremosa de Poblano con Elote'),
    ('L complemento',      'Enchiladas Queretanas de Queso'),
    # MARTES
    ('Ma entrada_no_comal','Mini Tostadas de Tinga de Res'),
    ('Ma crema',           'Crema de Brocoli'),
    ('Ma sopa',            'Sopa de Calabacitas con Poblano'),
    ('Ma pasta',           'Fusilli con Verduras a la Crema'),
    ('Ma ensalada_B',      'Ensalada Cesar'),
    ('Ma fuerte_res',      'Mole de Olla'),
    ('Ma fuerte_cerdo',    'Chuleta de Cerdo en Salsa de Pina y Chipotle con Pure de Papa'),
    ('Ma fuerte_pollo',    'Pollo al Pibil'),
    ('Ma fuerte_camaron',  'Tacos de Camaron Tradicional'),
    ('Ma fuerte_pescado',  'Filete de Pescado en Salsa de Bechamel'),
    ('Ma complemento',     'Chilaquiles Arrieros con Pollo o Huevo'),
    # MIERCOLES
    ('Mi entrada_no_comal','Nopal Tradicional'),
    ('Mi crema',           'Crema de Pimiento'),
    ('Mi sopa',            'Sopa de Poro y Papa'),
    ('Mi pasta',           'Codito con Espinaca'),
    ('Mi ensalada_C',      'Ensalada de Espinaca con Melon'),
    ('Mi fuerte_res',      'Agujas Nortenas con Guacamole y Frijoles Refritos'),
    ('Mi fuerte_cerdo',    'Torta de Cochinita'),
    ('Mi fuerte_pollo',    'Pechuga de Pollo al Romero con Pure de Papa'),
    ('Mi fuerte_camaron',  'Bombas de Camaron'),
    ('Mi fuerte_pescado',  'Filete de Pescado al Pastor'),
    ('Mi complemento',     'Tortitas de Huauzontle en Caldillo de Jitomate'),
    # JUEVES
    ('J entrada_no_comal', 'Huevo Relleno de Atun'),
    ('J crema',            'Crema de Champiñon'),
    ('J sopa',             'Sopa Campesina'),
    ('J pasta',            'Pasta Pluma Pomodoro'),
    ('J ensalada_A',       'Ensalada de Pepino a la Vinagreta'),
    ('J fuerte_res',       'Tacos de Suadero'),
    ('J fuerte_cerdo',     'Chicharron en Salsa Verde con Nopales'),
    ('J fuerte_pollo',     'Pollo Asado Enchilado'),
    ('J fuerte_camaron',   'Chile Relleno de Camaron'),
    ('J fuerte_pescado',   'Filete de Pescado Empapelado con Chile Ancho'),
    ('J complemento',      'Tacos Dorados Mixtos'),
    # VIERNES
    ('V entrada_no_comal', 'Cuaresmeño Relleno de Queso'),
    ('V crema',            'Crema de Almeja'),
    ('V sopa',             'Sopa de Habas'),
    ('V pasta',            'Sopa de Fideo'),
    ('V ensalada_B',       'Ensalada de Zanahoria'),
    ('V fuerte_res',       'Milanesa de Res con Ensalada'),
    ('V fuerte_cerdo',     'Costilla de Cerdo en Salsa Verde con Verdolagas'),
    ('V fuerte_pollo',     'Pechuga de Pollo Rellena de Espinacas con Queso'),
    ('V fuerte_camaron',   'Camarones Roca'),
    ('V fuerte_pescado',   'Filete de Pescado en Salsa Cremosa de Cilantro'),
    ('V complemento',      'Romeritos'),
    # SABADO
    ('S entrada_no_comal', 'Pescaditos Rebozados'),
    ('S crema',            'Crema de Champiñones'),
    ('S sopa_pollo',       'Consome de Pollo con Chile de Arbol'),
    ('S pasta',            'Espagueti Verde'),
    ('S ensalada_C',       'Ensalada de Espinaca con Melon'),
    ('S fuerte_res',       'Arrachera con Frijoles y Pico de Gallo'),
    ('S fuerte_cerdo',     'Tacos de Chuleta con Nopales y Cebolla'),
    ('S fuerte_pollo',     'Pechuga de Pollo Empanizada con Ensalada'),
    ('S camaron_al_gusto', 'Camarones Hawaianos al Gusto'),
    ('S pescado_al_gusto', 'Filete de Pescado al Gusto Mojo Ajillo Empanizado Diabla'),
    ('S enchiladas',       'Enchiladas de Mole Poblano'),
]

print(f'{"Día/Slot":<22} {"Buscado":<48} Encontrado')
print('-' * 130)
no_found = []
for slot, name in dishes:
    results = find(name)
    if results:
        found_str = '  |  '.join(f'[{r[0]}] {r[1]}' for r in results[:2])
        print(f'{slot:<22} {name:<48} {found_str}')
    else:
        print(f'{slot:<22} {name:<48} *** NO ENCONTRADO ***')
        no_found.append((slot, name))

print(f'\nNo encontrados: {len(no_found)}')
for s, n in no_found:
    print(f'  {s}: {n}')
