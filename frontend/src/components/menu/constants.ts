// Slot display labels
export const SLOT_LABELS: Record<string, string> = {
  entrada_comal: 'Del Comal',
  entrada_no_comal: 'Entrada',
  sopa: 'Sopa',
  crema: 'Crema',
  pasta: 'Pasta',
  arroz: 'Arroz',
  ensalada_A: 'Ensalada',
  ensalada_B: 'Ensalada',
  ensalada_C: 'Ensalada',
  molcajete: 'Molcajete',
  fuerte_res: 'Res',
  fuerte_pollo: 'Pollo',
  fuerte_cerdo: 'Cerdo',
  fuerte_pescado: 'Pescado',
  fuerte_camaron: 'Camarón',
  chamorro: 'Chamorro al horno pibil o al albañil',
  complemento: 'Complemento',
  pancita: 'Pancita',
  paella: 'Paella',
  nuggets: 'Nuggets',
  pescado_al_gusto: 'Pescado al gusto',
  camaron_al_gusto: 'Camarón al gusto',
  enchiladas: 'Enchiladas',
  sopa_pollo: 'Sopa de Pollo',
}

// Protein colors
export const PROTEIN_DOT: Record<string, string> = {
  res: 'bg-red-400',
  pollo: 'bg-amber-400',
  cerdo: 'bg-orange-400',
  pescado: 'bg-blue-400',
  camaron: 'bg-cyan-400',
  atun: 'bg-sky-400',
  none: 'bg-warm-300',
}

export const PROTEIN_LABELS: Record<string, string> = {
  res: 'Res',
  pollo: 'Pollo',
  cerdo: 'Cerdo',
  pescado: 'Pescado',
  camaron: 'Camarón',
  atun: 'Atún',
  none: '—',
}

export const COURSE_GROUP_LABELS: Record<string, string> = {
  sopa: 'Sopa',
  crema: 'Crema',
  pasta: 'Pasta',
  entrada_no_comal: 'Entrada',
  entrada: 'Entrada',
  ensalada: 'Ensalada',
  arroz: 'Arroz',
  fuerte: 'Plato fuerte',
  complemento: 'Complemento',
  especial: 'Especial',
}

// Fixed slots (not editable by user)
// - entrada_comal, arroz, paella, nuggets, pancita: dish hardcoded in DB (ID fijo)
// - chamorro: regla de negocio — siempre el mismo platillo los viernes (tag friday_chamorro)
export const FIXED_SLOTS = new Set([
  'entrada_comal',
  'arroz',
  'chamorro',
  'paella',
  'nuggets',
  'pancita',
])

// Slots per section
export const SECTION_SLOTS = {
  Entradas: ['entrada_no_comal', 'entrada_comal'],
  'Sopas & Cremas': ['sopa', 'crema', 'pasta', 'pancita', 'sopa_pollo'],
  'Arroz & Ensalada': ['arroz', 'ensalada_A', 'ensalada_B', 'ensalada_C'],
  'Platos Fuertes': [
    'chamorro',
    'paella',
    'molcajete',
    'fuerte_res',
    'fuerte_pollo',
    'fuerte_cerdo',
    'fuerte_pescado',
    'fuerte_camaron',
  ],
  'Especiales & Complementos': [
    'complemento',
    'pescado_al_gusto',
    'camaron_al_gusto',
    'nuggets',
    'enchiladas',
  ],
}

export const ALL_SECTION_NAMES = Object.keys(SECTION_SLOTS) as Array<keyof typeof SECTION_SLOTS>
