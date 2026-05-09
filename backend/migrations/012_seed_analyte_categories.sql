-- Migration: 012_seed_analyte_categories
-- Description: Базовые категории анализов. Без них seed_analyte_mappings_from_csv.py
-- определяет категорию через detect_category(), но не находит запись в analyte_categories
-- и складывает все стандарты в "Другие анализы".
-- Date: 2026-05-09

INSERT INTO analyte_categories (id, name, icon, sort_order, is_active) VALUES
  (gen_random_uuid(), 'Общий анализ крови',       '🩸',  1, TRUE),
  (gen_random_uuid(), 'Биохимия крови',           '🧪',  2, TRUE),
  (gen_random_uuid(), 'Липидный профиль',         '🍔',  3, TRUE),
  (gen_random_uuid(), 'Коагулограмма',            '🩹',  4, TRUE),
  (gen_random_uuid(), 'Гормоны',                  '🧬',  5, TRUE),
  (gen_random_uuid(), 'Витамины и микроэлементы', '💊',  6, TRUE),
  (gen_random_uuid(), 'Маркеры воспаления',       '🔥',  7, TRUE),
  (gen_random_uuid(), 'Общий анализ мочи',        '💧',  8, TRUE),
  (gen_random_uuid(), 'Инфекции',                 '🦠',  9, TRUE),
  (gen_random_uuid(), 'Микробиология',            '🔬', 10, TRUE),
  (gen_random_uuid(), 'Другие анализы',           '📋', 999, TRUE)
ON CONFLICT (name) DO NOTHING;
