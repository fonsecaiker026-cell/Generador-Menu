import type {
  Dish,
  MenuRow,
  WeekMeta,
  WeekData,
  WeekReport,
  ShoppingSummary,
  CatalogHealth,
} from '../types'

// ─── Dish catalog (80+ dishes) ────────────────────────────────

let nextDishId = 1
const d = (
  name: string,
  course_group: Dish['course_group'],
  protein: Dish['protein'],
  style_tag: string | null = null,
  sauce_tag: string | null = null,
  active = true,
): Dish => ({
  id: nextDishId++,
  name,
  course_group,
  protein,
  style_tag,
  sauce_tag,
  active,
})

export const MOCK_DISHES: Dish[] = [
  // ── Sopas ──────────────────────────────────────────────────
  d('Antojitos del Comal', 'entrada', 'none', 'entrada_comal_fija'),
  d('Arroz al Gusto', 'arroz', 'none', 'arroz_al_gusto_fijo'),
  d('Sopa de Lima', 'sopa', 'pollo', 'sopa_lima', 'salsa_lima'),
  d('Sopa de Tortilla', 'sopa', 'none', 'sopa_tortilla', 'salsa_chile'),
  d('Caldo de Res', 'sopa', 'res', 'caldo_res', null),
  d('Sopa de Médula', 'sopa', 'res', 'sopa_medula', null),
  d('Sopa de Pasta', 'sopa', 'none', 'sopa_pasta', null),
  d('Sopa Azteca', 'sopa', 'none', 'sopa_azteca', 'salsa_chile'),
  d('Pozole Rojo', 'sopa', 'cerdo', 'pozole', 'salsa_guajillo'),
  d('Sopa de Hongo con Epazote', 'sopa', 'none', 'sopa_hongo', null),
  d('Sopa Tarasca', 'sopa', 'none', 'sopa_tarasca', 'salsa_frijol'),
  d('Sopa de Lentejas con Chorizo', 'sopa', 'cerdo', 'sopa_lentejas', null),
  d('Caldo Tlalpeño', 'sopa', 'pollo', 'caldo_tlalpeno', 'chipotle'),
  d('Sopa de Flor de Calabaza', 'sopa', 'none', 'sopa_flor_calabaza', null),
  d('Sopa de Ajo', 'sopa', 'none', 'sopa_ajo', null),
  d('Chilpachole de Jaiba', 'sopa', 'pescado', 'chilpachole', 'chipotle'),
  d('Puchero de Res', 'sopa', 'res', 'puchero', null),
  d('Sopa de Mariscos', 'sopa', 'pescado', 'sopa_mariscos', null),
  d('Fabada Asturiana', 'sopa', 'cerdo', 'fabada', null),
  d('Sopa Negra de Frijol', 'sopa', 'none', 'sopa_negra', null),
  d('Caldo de Pollo con Verduras', 'sopa', 'pollo', 'caldo_pollo', null),

  // ── Cremas ─────────────────────────────────────────────────
  d('Crema de Elote', 'crema', 'none', 'crema_elote', null),
  d('Crema de Brócoli con Chipotle', 'crema', 'none', 'crema_brocoli', 'chipotle'),
  d('Crema de Champiñón', 'crema', 'none', 'crema_champinon', null),
  d('Crema de Zanahoria con Jengibre', 'crema', 'none', 'crema_zanahoria', null),
  d('Crema de Pimiento Rojo', 'crema', 'none', 'crema_pimiento', null),
  d('Crema Poblana', 'crema', 'none', 'crema_poblana', 'salsa_poblano'),
  d('Crema de Elote con Rajas', 'crema', 'none', 'crema_elote_rajas', 'salsa_poblano'),
  d('Crema de Almeja', 'crema', 'pescado', 'crema_almeja', null),
  d('Crema de Garbanzo', 'crema', 'none', 'crema_garbanzo', null),
  d('Crema de Coliflor con Queso', 'crema', 'none', 'crema_coliflor', null),

  // ── Pastas ─────────────────────────────────────────────────
  d('Espagueti al Pesto con Champiñones', 'pasta', 'none', 'pasta_pesto', 'salsa_pesto'),
  d('Espagueti a la Boloñesa', 'pasta', 'res', 'pasta_bolonesa', 'salsa_tomate'),
  d('Fettuccine Alfredo con Pollo', 'pasta', 'pollo', 'pasta_alfredo', 'crema_ajo'),
  d('Penne a la Arrabbiata', 'pasta', 'none', 'pasta_arrabbiata', 'salsa_picante'),
  d('Espagueti con Almejas', 'pasta', 'pescado', 'pasta_almejas', null),
  d('Espagueti con Salsa Rosa', 'pasta', 'none', 'pasta_rosa', 'salsa_rosa'),
  d('Rigatoni con Ragú de Cordero', 'pasta', 'res', 'pasta_ragu', 'salsa_ragu'),
  d('Linguine al Vongole', 'pasta', 'pescado', 'pasta_vongole', null),
  d('Penne con Pollo y Albahaca', 'pasta', 'pollo', 'pasta_pollo_albahaca', 'salsa_pesto'),
  d('Tagliatelle Carbonara', 'pasta', 'cerdo', 'pasta_carbonara', 'crema_huevo'),

  // ── Ensaladas ──────────────────────────────────────────────
  d('Ensalada de Betabel con Naranja', 'ensalada', 'none', 'ensalada_betabel', null),
  d('Ensalada César con Aderezo Casero', 'ensalada', 'none', 'ensalada_cesar', null),
  d('Ensalada de Nopales con Chile Serrano', 'ensalada', 'none', 'ensalada_nopales', null),
  d('Ensalada Caprese con Albahaca', 'ensalada', 'none', 'ensalada_caprese', null),
  d('Ensalada de Espinaca con Vinagreta', 'ensalada', 'none', 'ensalada_espinaca', null),
  d('Ensalada Mixta con Aderezo de Limón', 'ensalada', 'none', 'ensalada_mixta', null),

  // ── Entradas ───────────────────────────────────────────────
  d('Quesadillas de Flor de Calabaza', 'entrada', 'none', 'quesadilla_flor', null),
  d('Sopes de Picadillo', 'entrada', 'res', 'sopes_picadillo', null),
  d('Tostadas de Tinga de Pollo', 'entrada', 'pollo', 'tostadas_tinga', 'salsa_chipotle'),
  d('Gorditas de Chicharrón Prensado', 'entrada', 'cerdo', 'gorditas_chicharron', null),
  d('Empanadas de Maíz con Rajas', 'entrada', 'none', 'empanadas_rajas', null),
  d('Tostadas de Aguacate con Cebolla Morada', 'entrada', 'none', 'tostadas_aguacate', null),
  d('Tacos de Canasta de Guisado', 'entrada', 'none', 'tacos_canasta', null),

  // ── Fuertes: Res ───────────────────────────────────────────
  d('Molcajete de Res con Nopales', 'fuerte', 'res', 'monday_molcajete', 'salsa_molcajete'),
  d('Bistec a la Mexicana', 'fuerte', 'res', 'bistec_mexicana', 'salsa_mexicana'),
  d('Arrachera a las Brasas', 'fuerte', 'res', 'arrachera_brasas', null),
  d('Entrecot a la Pimienta', 'fuerte', 'res', 'entrecot_pimienta', 'pimienta_negra'),
  d('T-Bone al Carbón', 'fuerte', 'res', 'tbone_carbon', null),
  d('Rib Eye a la Parrilla', 'fuerte', 'res', 'ribeye_parrilla', null),
  d('Milanesa de Res Empanizada', 'fuerte', 'res', 'milanesa_res', null),
  d('Carne Asada con Guacamole', 'fuerte', 'res', 'carne_asada', null),
  d('Estofado de Res con Verduras', 'fuerte', 'res', 'estofado_res', 'salsa_tomate'),
  d('Barbacoa de Res Estilo Hidalgo', 'fuerte', 'res', 'barbacoa', null),
  d('Retazo de Res en Caldillo Verde', 'fuerte', 'res', 'retazo_verde', 'salsa_verde'),

  // ── Fuertes: Pollo ─────────────────────────────────────────
  d('Pollo en Salsa Verde Cremosa', 'fuerte', 'pollo', 'pollo_verde_cremoso', 'salsa_verde'),
  d('Pollo al Ajillo con Papas', 'fuerte', 'pollo', 'pollo_ajillo', 'ajo_aceite'),
  d('Pechugas a la Plancha con Mostaza', 'fuerte', 'pollo', 'pechuga_mostaza', null),
  d('Muslos de Pollo en Mole Negro', 'fuerte', 'pollo', 'pollo_mole_negro', 'mole_negro'),
  d('Pollo en Chile Pasilla con Frutas', 'fuerte', 'pollo', 'pollo_pasilla', 'salsa_pasilla'),
  d('Pollo Rostizado con Limón y Hierbas', 'fuerte', 'pollo', 'pollo_rostizado', null),
  d('Pollo al Chipotle con Papas', 'fuerte', 'pollo', 'pollo_chipotle', 'chipotle'),
  d('Pierna de Pollo Glaseada', 'fuerte', 'pollo', 'pollo_glaseado', null),
  d('Pollo Encacahuatado', 'fuerte', 'pollo', 'pollo_cacahuate', 'salsa_cacahuate'),

  // ── Fuertes: Cerdo ─────────────────────────────────────────
  d('Lomo de Cerdo en Chile Ancho', 'fuerte', 'cerdo', 'lomo_chile_ancho', 'salsa_ancho'),
  d('Costillas de Cerdo a la BBQ', 'fuerte', 'cerdo', 'costillas_bbq', 'bbq'),
  d('Puerco en Salsa Verde con Nopales', 'fuerte', 'cerdo', 'puerco_verde', 'salsa_verde'),
  d('Carnitas Estilo Michoacán', 'fuerte', 'cerdo', 'carnitas', null),
  d('Ribs de Cerdo Glaseados con Miel', 'fuerte', 'cerdo', 'ribs_miel', 'miel_mostaza'),
  d('Pierna de Cerdo al Horno con Hierbas', 'fuerte', 'cerdo', 'pierna_cerdo', null),
  d('Chuleta de Cerdo en Salsa de Chile Guajillo', 'fuerte', 'cerdo', 'chuleta_guajillo', 'salsa_guajillo'),
  d('Chamorro al Horno Estilo Tradicional', 'fuerte', 'cerdo', 'friday_chamorro', null),

  // ── Fuertes: Pescado ───────────────────────────────────────
  d('Filete de Robalo a la Veracruzana', 'fuerte', 'pescado', 'robalo_veracruzana', 'salsa_veracruzana'),
  d('Filete de Tilapia en Salsa de Guajillo', 'fuerte', 'pescado', 'tilapia_guajillo', 'salsa_guajillo'),
  d('Huachinango a la Veracruzana', 'fuerte', 'pescado', 'huachinango_veracruz', 'salsa_veracruzana'),
  d('Trucha a la Plancha con Hiervas', 'fuerte', 'pescado', 'trucha_plancha', null),
  d('Salmón con Mantequilla de Alcaparras', 'fuerte', 'pescado', 'salmon_alcaparras', null),
  d('Atún Sellado con Ajonjolí', 'fuerte', 'pescado', 'atun_ajonjoli', null),
  d('Mojarra Frita con Arroz Verde', 'fuerte', 'pescado', 'mojarra_frita', null),

  // ── Fuertes: Camarón ───────────────────────────────────────
  d('Camarones al Ajillo', 'fuerte', 'camaron', 'camaron_ajillo', 'ajo_aceite'),
  d('Camarones en Crema de Chipotle', 'fuerte', 'camaron', 'camaron_chipotle', 'chipotle'),
  d('Camarones en Aguachile Verde', 'fuerte', 'camaron', 'camaron_aguachile', 'aguachile'),
  d('Camarones a la Diabla', 'fuerte', 'camaron', 'camaron_diabla', 'salsa_diabla'),
  d('Camarones al Mojo de Ajo', 'fuerte', 'camaron', 'camaron_mojo', 'ajo_aceite'),
  d('Camarones Jumbo al Coco', 'fuerte', 'camaron', 'camaron_coco', null),
  d('Callo de Hacha con Mantequilla', 'fuerte', 'pescado', 'callo_mantequilla', null),

  // ── Complementos ───────────────────────────────────────────
  d('Milanesa de Pollo', 'complemento', 'pollo', 'milanesa_pollo', null),
  d('Chiles Rellenos de Queso', 'complemento', 'none', 'chile_relleno_queso', 'caldillo_jitomate'),
  d('Enchiladas Suizas', 'complemento', 'pollo', 'enchiladas_suizas', 'salsa_verde'),
  d('Torta de Milanesa', 'complemento', 'res', 'torta_milanesa', null),
  d('Tacos de Pibil de Cerdo', 'complemento', 'cerdo', 'tacos_pibil', 'achiote'),
  d('Quesadilla de Rajas con Crema', 'complemento', 'none', 'quesadilla_rajas', null),
  d('Flautas de Pollo con Guacamole', 'complemento', 'pollo', 'flautas_pollo', null),
  d('Tostadas de Ceviche de Sierra', 'complemento', 'pescado', 'tostadas_ceviche', 'limón'),

  // ── Especiales sábado ──────────────────────────────────────
  d('Pancita de Res en Caldo', 'especial', 'res', 'pancita_fija', null),
  d('Paella Española', 'especial', 'camaron', 'paella_fija', null),
  d('Nuggets de Pollo con Papas', 'especial', 'pollo', 'nuggets_fijo', null),
  d('Filete de Huachinango al Mojo', 'especial', 'pescado', 'pescado_al_gusto', null),
  d('Camarones Jumbo Enteros', 'especial', 'camaron', 'camaron_al_gusto', null),
  d('Enchiladas Verdes con Pollo', 'especial', 'pollo', 'sat_enchiladas', 'salsa_verde'),
  d('Caldo Tlalpeño Estilo Tradicional', 'sopa', 'pollo', 'sopa_pollo_sat', null),

  // Inactive dishes
  d('Sopa de Médula Antigua', 'sopa', 'res', null, null, false),
  d('Chuleta de Res Vieja', 'fuerte', 'res', null, null, false),
]

// ─── Helper to find dish by ID ────────────────────────────────

export function getDishById(id: number): Dish | undefined {
  return MOCK_DISHES.find((d) => d.id === id)
}

// ─── Fixed slot dish IDs ──────────────────────────────────────

const ID_ANTOJITOS = 1    // Antojitos del Comal
const ID_ARROZ = 2        // Arroz al Gusto
const ID_PANCITA = 105    // Pancita de Res en Caldo
const ID_PAELLA = 106     // Paella Española
const ID_NUGGETS = 107    // Nuggets de Pollo con Papas
const ID_CALDO_TLALPENO_SAT = 111  // Caldo Tlalpeño (sopa_pollo Saturday)

// ─── Week meta ────────────────────────────────────────────────

export const MOCK_WEEK_META: WeekMeta = {
  id: 42,
  week_start_date: '2026-03-09',
  generated_at: '2026-03-07T10:23:11',
  finalized: false,
  notes: null,
}

// ─── Menu rows for the week ───────────────────────────────────

const row = (
  date: string,
  slot: string,
  dishId: number,
  opts: Partial<Pick<MenuRow, 'is_forced' | 'was_exception' | 'exception_reason' | 'explanation'>> = {},
): MenuRow => {
  const dish = getDishById(dishId)
  if (!dish) throw new Error(`Dish ${dishId} not found`)
  return {
    menu_date: date,
    slot,
    dish_id: dishId,
    dish_name: dish.name,
    course_group: dish.course_group,
    protein: dish.protein,
    style_tag: dish.style_tag,
    is_forced: opts.is_forced ?? false,
    was_exception: opts.was_exception ?? false,
    exception_reason: opts.exception_reason ?? null,
    explanation: opts.explanation ?? null,
  }
}

export const MOCK_MENU_ROWS: MenuRow[] = [
  // ── Lunes 09 Mar ──────────────────────────────────────────
  row('2026-03-09', 'entrada_comal', ID_ANTOJITOS, { is_forced: true }),
  row('2026-03-09', 'entrada_no_comal', 48),   // Quesadillas de Flor de Calabaza
  row('2026-03-09', 'sopa', 3),                // Sopa de Lima
  row('2026-03-09', 'crema', 22),              // Crema de Elote
  row('2026-03-09', 'pasta', 32),              // Espagueti al Pesto
  row('2026-03-09', 'ensalada_A', 42),         // Betabel con Naranja
  row('2026-03-09', 'arroz', ID_ARROZ, { is_forced: true }),
  row('2026-03-09', 'molcajete', 55),          // Molcajete de Res
  row('2026-03-09', 'fuerte_pollo', 66),       // Pollo Salsa Verde Cremosa
  row('2026-03-09', 'fuerte_cerdo', 75),       // Lomo Cerdo Chile Ancho
  row('2026-03-09', 'fuerte_pescado', 83),     // Robalo Veracruzana
  row('2026-03-09', 'fuerte_camaron', 90),     // Camarones Ajillo
  row('2026-03-09', 'complemento', 97),        // Milanesa de Pollo

  // ── Martes 10 Mar ─────────────────────────────────────────
  row('2026-03-10', 'entrada_comal', ID_ANTOJITOS, { is_forced: true }),
  row('2026-03-10', 'entrada_no_comal', 49),   // Sopes de Picadillo
  row('2026-03-10', 'sopa', 4),                // Sopa de Tortilla
  row('2026-03-10', 'crema', 23),              // Crema Brócoli con Chipotle
  row('2026-03-10', 'pasta', 33),              // Espagueti a la Boloñesa
  row('2026-03-10', 'ensalada_B', 43),         // César con Aderezo Casero
  row('2026-03-10', 'arroz', ID_ARROZ, { is_forced: true }),
  row('2026-03-10', 'fuerte_res', 56),         // Bistec a la Mexicana
  row('2026-03-10', 'fuerte_pollo', 67),       // Pollo al Ajillo
  row('2026-03-10', 'fuerte_cerdo', 76),       // Costillas BBQ
  row('2026-03-10', 'fuerte_pescado', 84),     // Tilapia Guajillo
  row('2026-03-10', 'fuerte_camaron', 91),     // Camarones en Crema de Chipotle
  row('2026-03-10', 'complemento', 98),        // Chiles Rellenos de Queso

  // ── Miércoles 11 Mar ──────────────────────────────────────
  row('2026-03-11', 'entrada_comal', ID_ANTOJITOS, { is_forced: true }),
  row('2026-03-11', 'entrada_no_comal', 50),   // Tostadas de Tinga
  row('2026-03-11', 'sopa', 9, { was_exception: true, exception_reason: 'WINDOW_RELAXED: ventana 20→12 días' }),
  row('2026-03-11', 'crema', 24),              // Crema de Champiñón
  row('2026-03-11', 'pasta', 34),              // Fettuccine Alfredo con Pollo
  row('2026-03-11', 'ensalada_C', 44),         // Nopales con Chile Serrano
  row('2026-03-11', 'arroz', ID_ARROZ, { is_forced: true }),
  row('2026-03-11', 'fuerte_res', 57, { is_forced: true }),  // Arrachera (override forzado)
  row('2026-03-11', 'fuerte_pollo', 68),       // Pechugas a la Plancha con Mostaza
  row('2026-03-11', 'fuerte_cerdo', 77),       // Puerco en Salsa Verde
  row('2026-03-11', 'fuerte_pescado', 85),     // Huachinango a la Veracruzana
  row('2026-03-11', 'fuerte_camaron', 92),     // Camarones en Aguachile Verde
  row('2026-03-11', 'complemento', 99),        // Enchiladas Suizas

  // ── Jueves 12 Mar ─────────────────────────────────────────
  row('2026-03-12', 'entrada_comal', ID_ANTOJITOS, { is_forced: true }),
  row('2026-03-12', 'entrada_no_comal', 51),   // Gorditas de Chicharrón
  row('2026-03-12', 'sopa', 5),                // Caldo de Res
  row('2026-03-12', 'crema', 25),              // Crema de Zanahoria con Jengibre
  row('2026-03-12', 'pasta', 35),              // Penne a la Arrabbiata
  row('2026-03-12', 'ensalada_A', 42),         // Betabel (igual que lunes)
  row('2026-03-12', 'arroz', ID_ARROZ, { is_forced: true }),
  row('2026-03-12', 'fuerte_res', 58),         // Entrecot a la Pimienta
  row('2026-03-12', 'fuerte_pollo', 69),       // Muslos de Pollo en Mole Negro
  row('2026-03-12', 'fuerte_cerdo', 78),       // Carnitas Estilo Michoacán
  row('2026-03-12', 'fuerte_pescado', 86),     // Trucha a la Plancha
  row('2026-03-12', 'fuerte_camaron', 93),     // Camarones a la Diabla
  row('2026-03-12', 'complemento', 100),       // Torta de Milanesa

  // ── Viernes 13 Mar ────────────────────────────────────────
  row('2026-03-13', 'entrada_comal', ID_ANTOJITOS, { is_forced: true }),
  row('2026-03-13', 'entrada_no_comal', 52),   // Empanadas de Maíz con Rajas
  row('2026-03-13', 'sopa', 6),                // Sopa de Médula
  row('2026-03-13', 'crema', 26),              // Crema de Pimiento Rojo
  row('2026-03-13', 'pasta', 36),              // Espagueti con Almejas
  row('2026-03-13', 'ensalada_B', 43),         // César (igual que martes)
  row('2026-03-13', 'arroz', ID_ARROZ, { is_forced: true }),
  row('2026-03-13', 'chamorro', 82),           // Chamorro al Horno
  row('2026-03-13', 'fuerte_res', 59),         // T-Bone al Carbón
  row('2026-03-13', 'fuerte_pollo', 70),       // Pollo en Chile Pasilla
  row('2026-03-13', 'fuerte_cerdo', 79),       // Ribs de Cerdo Glaseados
  row('2026-03-13', 'fuerte_pescado', 87),     // Salmón con Mantequilla
  row('2026-03-13', 'fuerte_camaron', 94),     // Camarones al Mojo de Ajo
  row('2026-03-13', 'complemento', 103),       // Flautas de Pollo con Guacamole

  // ── Sábado 14 Mar ─────────────────────────────────────────
  row('2026-03-14', 'entrada_comal', ID_ANTOJITOS, { is_forced: true }),
  row('2026-03-14', 'entrada_no_comal', 53),   // Tostadas de Aguacate
  row('2026-03-14', 'pancita', ID_PANCITA, { is_forced: true }),
  row('2026-03-14', 'crema', 28),              // Crema de Elote con Rajas
  row('2026-03-14', 'sopa_pollo', ID_CALDO_TLALPENO_SAT),
  row('2026-03-14', 'ensalada_C', 44),         // Nopales (igual que miércoles)
  row('2026-03-14', 'pasta', 37),              // Espagueti con Salsa Rosa
  row('2026-03-14', 'fuerte_res', 60),         // Rib Eye a la Parrilla
  row('2026-03-14', 'fuerte_pollo', 71),       // Pollo Rostizado con Limón
  row('2026-03-14', 'fuerte_cerdo', 80),       // Pierna de Cerdo al Horno
  row('2026-03-14', 'paella', ID_PAELLA, { is_forced: true }),
  row('2026-03-14', 'pescado_al_gusto', 108),  // Filete de Huachinango al Mojo
  row('2026-03-14', 'camaron_al_gusto', 109),  // Camarones Jumbo Enteros
  row('2026-03-14', 'nuggets', ID_NUGGETS, { is_forced: true }),
  row('2026-03-14', 'enchiladas', 110),        // Enchiladas Verdes con Pollo
]

// ─── Mock week data ───────────────────────────────────────────

export const MOCK_WEEK_DATA: WeekData = {
  week: MOCK_WEEK_META,
  rows: MOCK_MENU_ROWS,
}

// ─── Week quality report ──────────────────────────────────────

export const MOCK_WEEK_REPORT: WeekReport = {
  week_start: '2026-03-09',
  week_id: 42,
  days: [
    { date: '2026-03-09', day_name: 'Lunes', slots: [] },
    { date: '2026-03-10', day_name: 'Martes', slots: [] },
    { date: '2026-03-11', day_name: 'Miércoles', slots: [] },
    { date: '2026-03-12', day_name: 'Jueves', slots: [] },
    { date: '2026-03-13', day_name: 'Viernes', slots: [] },
    { date: '2026-03-14', day_name: 'Sábado', slots: [] },
  ],
  sauces_used: [
    'ajo_aceite', 'bbq', 'chipotle', 'crema_ajo', 'miel_mostaza',
    'pimienta_negra', 'salsa_guajillo', 'salsa_lima', 'salsa_mexicana',
    'salsa_molcajete', 'salsa_pasilla', 'salsa_pesto', 'salsa_poblano',
    'salsa_tomate', 'salsa_verde', 'salsa_veracruzana',
  ],
  proteins_by_day: {
    '2026-03-09': { res: 1, pollo: 2, cerdo: 1, pescado: 1, camaron: 1 },
    '2026-03-10': { res: 1, pollo: 2, cerdo: 1, pescado: 1, camaron: 1 },
    '2026-03-11': { res: 2, pollo: 1, cerdo: 1, pescado: 2 },
    '2026-03-12': { res: 1, pollo: 2, cerdo: 1, pescado: 1, camaron: 1 },
    '2026-03-13': { res: 1, pollo: 2, cerdo: 1, pescado: 2, camaron: 1 },
    '2026-03-14': { res: 1, pollo: 3, cerdo: 1, pescado: 1, camaron: 2 },
  },
  exceptions: [
    {
      date: '2026-03-11',
      slot: 'sopa',
      reason: 'WINDOW_RELAXED: ventana reducida 20→12 días',
      dish: 'Pozole Rojo',
    },
  ],
  warnings: [
    '1 slot(s) usaron un platillo repetido antes de 20 días.',
    '1 slot(s) tienen override manual forzado.',
  ],
  score: 88,
  totals: {
    dishes: 83,
    with_sauce_tag: 52,
    exceptions: 1,
    forced_overrides: 1,
    sauces_unique: 16,
  },
}

// ─── Shopping summary ─────────────────────────────────────────

export const MOCK_SHOPPING_SUMMARY: ShoppingSummary = {
  week_start: '2026-03-09',
  by_protein: {
    res: [
      { date: '2026-03-09', slot: 'molcajete', dish: 'Molcajete de Res con Nopales' },
      { date: '2026-03-10', slot: 'fuerte_res', dish: 'Bistec a la Mexicana' },
      { date: '2026-03-11', slot: 'fuerte_res', dish: 'Arrachera a las Brasas' },
      { date: '2026-03-12', slot: 'fuerte_res', dish: 'Entrecot a la Pimienta' },
      { date: '2026-03-13', slot: 'fuerte_res', dish: 'T-Bone al Carbón' },
      { date: '2026-03-14', slot: 'fuerte_res', dish: 'Rib Eye a la Parrilla' },
    ],
    pollo: [
      { date: '2026-03-09', slot: 'fuerte_pollo', dish: 'Pollo en Salsa Verde Cremosa' },
      { date: '2026-03-10', slot: 'fuerte_pollo', dish: 'Pollo al Ajillo con Papas' },
      { date: '2026-03-11', slot: 'fuerte_pollo', dish: 'Pechugas a la Plancha con Mostaza' },
      { date: '2026-03-12', slot: 'fuerte_pollo', dish: 'Muslos de Pollo en Mole Negro' },
      { date: '2026-03-13', slot: 'fuerte_pollo', dish: 'Pollo en Chile Pasilla con Frutas' },
      { date: '2026-03-14', slot: 'fuerte_pollo', dish: 'Pollo Rostizado con Limón y Hierbas' },
      { date: '2026-03-14', slot: 'sopa_pollo', dish: 'Caldo Tlalpeño Estilo Tradicional' },
    ],
    cerdo: [
      { date: '2026-03-09', slot: 'fuerte_cerdo', dish: 'Lomo de Cerdo en Chile Ancho' },
      { date: '2026-03-10', slot: 'fuerte_cerdo', dish: 'Costillas de Cerdo a la BBQ' },
      { date: '2026-03-11', slot: 'fuerte_cerdo', dish: 'Puerco en Salsa Verde con Nopales' },
      { date: '2026-03-12', slot: 'fuerte_cerdo', dish: 'Carnitas Estilo Michoacán' },
      { date: '2026-03-13', slot: 'fuerte_cerdo', dish: 'Ribs de Cerdo Glaseados con Miel' },
      { date: '2026-03-14', slot: 'fuerte_cerdo', dish: 'Pierna de Cerdo al Horno' },
    ],
    pescado: [
      { date: '2026-03-09', slot: 'fuerte_pescado', dish: 'Filete de Robalo a la Veracruzana' },
      { date: '2026-03-10', slot: 'fuerte_pescado', dish: 'Filete de Tilapia en Salsa de Guajillo' },
      { date: '2026-03-12', slot: 'fuerte_pescado', dish: 'Huachinango a la Veracruzana' },
      { date: '2026-03-13', slot: 'fuerte_pescado', dish: 'Huachinango a la Veracruzana' },
      { date: '2026-03-14', slot: 'pescado_al_gusto', dish: 'Filete de Huachinango al Mojo' },
    ],
    camaron: [
      { date: '2026-03-09', slot: 'fuerte_camaron', dish: 'Camarones al Ajillo' },
      { date: '2026-03-10', slot: 'fuerte_camaron', dish: 'Camarones en Crema de Chipotle' },
      { date: '2026-03-11', slot: 'fuerte_pescado', dish: 'Camarones en Aguachile Verde' },
      { date: '2026-03-12', slot: 'fuerte_camaron', dish: 'Camarones a la Diabla' },
      { date: '2026-03-13', slot: 'fuerte_camaron', dish: 'Camarones al Mojo de Ajo' },
      { date: '2026-03-14', slot: 'camaron_al_gusto', dish: 'Camarones Jumbo Enteros' },
    ],
  } as any,
  counts: { res: 6, pollo: 7, cerdo: 6, pescado: 5, camaron: 6 },
  daily_breakdown: {
    '2026-03-09': { res: 1, pollo: 1, cerdo: 1, pescado: 1, camaron: 1 },
    '2026-03-10': { res: 1, pollo: 1, cerdo: 1, pescado: 1, camaron: 1 },
    '2026-03-11': { res: 1, pollo: 1, cerdo: 1, camaron: 2 },
    '2026-03-12': { res: 1, pollo: 1, cerdo: 1, pescado: 1, camaron: 1 },
    '2026-03-13': { res: 1, pollo: 1, cerdo: 1, pescado: 2, camaron: 1 },
    '2026-03-14': { res: 1, pollo: 2, cerdo: 1, pescado: 1, camaron: 1 },
  },
}

// ─── Catalog health ───────────────────────────────────────────

export const MOCK_CATALOG_HEALTH: CatalogHealth = {
  generated_at: '2026-03-09',
  since_days: 60,
  total_active: MOCK_DISHES.filter((d) => d.active).length,
  never_used: [
    { id: 37, name: 'Rigatoni con Ragú de Cordero', course_group: 'pasta', protein: 'res' },
    { id: 38, name: 'Linguine al Vongole', course_group: 'pasta', protein: 'pescado' },
    { id: 46, name: 'Ensalada Mixta con Aderezo de Limón', course_group: 'ensalada', protein: 'none' },
    { id: 69, name: 'Pollo Encacahuatado', course_group: 'fuerte', protein: 'pollo' },
    { id: 85, name: 'Atún Sellado con Ajonjolí', course_group: 'fuerte', protein: 'pescado' },
    { id: 91, name: 'Camarones Jumbo al Coco', course_group: 'fuerte', protein: 'camaron' },
    { id: 101, name: 'Tacos de Pibil de Cerdo', course_group: 'complemento', protein: 'cerdo' },
    { id: 102, name: 'Quesadilla de Rajas con Crema', course_group: 'complemento', protein: 'none' },
  ],
  dormant: [
    { id: 11, name: 'Sopa Tarasca', course_group: 'sopa', protein: 'none', last_used: '2026-01-07', days_ago: 61, uses: 3 },
    { id: 18, name: 'Fabada Asturiana', course_group: 'sopa', protein: 'cerdo', last_used: '2026-01-05', days_ago: 63, uses: 2 },
    { id: 44, name: 'Ensalada Caprese con Albahaca', course_group: 'ensalada', protein: 'none', last_used: '2025-12-20', days_ago: 79, uses: 5 },
    { id: 68, name: 'Pierna de Pollo Glaseada', course_group: 'fuerte', protein: 'pollo', last_used: '2025-12-15', days_ago: 84, uses: 4 },
    { id: 77, name: 'Chuleta de Cerdo en Salsa de Chile Guajillo', course_group: 'fuerte', protein: 'cerdo', last_used: '2026-01-10', days_ago: 58, uses: 6 },
    { id: 83, name: 'Salmón con Mantequilla de Alcaparras', course_group: 'fuerte', protein: 'pescado', last_used: '2025-12-28', days_ago: 71, uses: 3 },
  ],
  overused: [
    { id: 3, name: 'Sopa de Lima', course_group: 'sopa', protein: 'pollo', uses: 14 },
    { id: 42, name: 'Ensalada César con Aderezo Casero', course_group: 'ensalada', protein: 'none', uses: 13 },
    { id: 62, name: 'Pollo en Salsa Verde Cremosa', course_group: 'fuerte', protein: 'pollo', uses: 12 },
    { id: 74, name: 'Carnitas Estilo Michoacán', course_group: 'fuerte', protein: 'cerdo', uses: 11 },
  ],
  by_group: {
    arroz: { total: 1, never: 0, dormant: 0, overused: 0 },
    complemento: { total: 8, never: 2, dormant: 0, overused: 0 },
    crema: { total: 10, never: 0, dormant: 1, overused: 0 },
    ensalada: { total: 6, never: 1, dormant: 1, overused: 1 },
    entrada: { total: 8, never: 0, dormant: 0, overused: 0 },
    especial: { total: 7, never: 0, dormant: 0, overused: 0 },
    fuerte: { total: 36, never: 3, dormant: 3, overused: 2 },
    pasta: { total: 10, never: 2, dormant: 0, overused: 0 },
    sopa: { total: 21, never: 0, dormant: 2, overused: 1 },
  },
}

// ─── Mutable mock store ───────────────────────────────────────

interface MockStore {
  weeks: Map<string, WeekData>
  dishes: Dish[]
}

export const mockStore: MockStore = {
  weeks: new Map([['2026-03-09', { ...MOCK_WEEK_DATA, rows: [...MOCK_MENU_ROWS] }]]),
  dishes: [...MOCK_DISHES],
}

export function getMockWeek(weekStart: string): WeekData {
  return mockStore.weeks.get(weekStart) ?? { week: null, rows: [] }
}

export function setMockWeek(weekStart: string, data: WeekData): void {
  mockStore.weeks.set(weekStart, data)
}
