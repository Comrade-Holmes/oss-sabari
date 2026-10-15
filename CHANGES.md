# CRUD fixes

1. **Update crashed for Restaurants, Dishes and Allergens** – the Cypher `MATCH (x {id: $id})` sat inside an
   f-string without escaped braces (`TypeError: unsupported format string`). Now `{{id: $id}}`.
2. **Dish create/update dropped relationships** – chained `UNWIND`s stop the query when a list is empty, so a dish
   with no restaurant lost its ingredients and "may contain" allergens, and edits could half-apply. Relationships
   are now replaced per kind inside one transaction (`None` = leave alone, `[]` = clear).
3. **Ingredient create/update** – same relationship fix; enum values coerced to plain strings; updating a missing
   ingredient now returns 404 instead of silently continuing.
4. **Renaming an allergen to an existing name** hit the unique constraint and returned a 500; it is now rejected
   with a message (HTML) / 400 (API).
5. **`/users/api/users` returned `password_hash`** for every user – removed.
6. **Edit-form pick lists were capped (50/100 items)**; saving an edit silently deleted links to anything past the
   cap. Caps raised to 500–1000.

New tests: `tests/test_crud_offline.py` (no Neo4j needed) and `tests/test_crud_write_operations.py` (live Neo4j).

7. **Allergy checker never showed results** – the page only renders results when `has_searched` is set, but the
   router never passed it, so clicking *Execute Graph Screening* just redisplayed the form. Also fixed: the
   Restaurant filter was ignored (form sends `restaurant`, router read `restaurant_id`), the selected restaurant
   wasn't re-selected after searching, and dish categories not in the hard-coded list couldn't be filtered.
