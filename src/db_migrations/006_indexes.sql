-- Índices de rendimiento para las queries más frecuentes del motor de rotación.
-- Aplicar una sola vez con apply_migrations.py (idempotente).

-- menu_item: buscado por (menu_date, slot) en rotación cross-semanas
CREATE INDEX IF NOT EXISTS idx_menu_item_date_slot
    ON menu_item(menu_date, slot);

-- menu_item: buscado por (menu_week_id, slot) en intra-week beef cut / pasta tipo
CREATE INDEX IF NOT EXISTS idx_menu_item_week_slot
    ON menu_item(menu_week_id, slot);

-- menu_item: buscado por (menu_week_id, menu_date) en recompute_day / clear_day_items
CREATE INDEX IF NOT EXISTS idx_menu_item_week_date
    ON menu_item(menu_week_id, menu_date);

-- dish_tag: buscado por tag (only_sat, only_fri, monday_molcajete, pasta_tipo_*, …)
CREATE INDEX IF NOT EXISTS idx_dish_tag_tag
    ON dish_tag(tag);

-- dish_tag: buscado por (dish_id, tag) en filtros combinados
CREATE INDEX IF NOT EXISTS idx_dish_tag_dish_tag
    ON dish_tag(dish_id, tag);

-- dish: buscado por sauce_tag en rotación cross-slot
CREATE INDEX IF NOT EXISTS idx_dish_sauce_tag
    ON dish(sauce_tag)
    WHERE sauce_tag IS NOT NULL;

-- dish_beef_cut: buscado por beef_cut_id al filtrar cortes bloqueados
CREATE INDEX IF NOT EXISTS idx_dish_beef_cut_cut
    ON dish_beef_cut(beef_cut_id);

-- menu_override: buscado por (menu_date, slot) en cada slot generado
CREATE INDEX IF NOT EXISTS idx_menu_override_date_slot
    ON menu_override(menu_date, slot);
