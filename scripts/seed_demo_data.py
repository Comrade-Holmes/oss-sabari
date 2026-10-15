#!/usr/bin/env python3
"""
AllerGraph - Idempotent Demo Data Seeding Script
Populates restaurants, dishes, ingredients, allergens, and graph relationships.
Never deletes unrelated records.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database import db
from app.security import hash_password

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def seed_demo_data():
    print("=" * 60)
    print("AllerGraph: Seeding Idempotent Demo Food & Graph Data")
    print("=" * 60)

    now = now_iso()

    # 1. Allergens (9 Major Allergens)
    allergens = [
        {"id": "alg-peanuts", "name": "Peanuts", "description": "Legumes growing underground, distinct from tree nuts.", "category": "Major"},
        {"id": "alg-tree-nuts", "name": "Tree Nuts", "description": "Includes walnuts, almonds, hazelnuts, pecans, cashews, pistachios, pine nuts.", "category": "Major"},
        {"id": "alg-dairy", "name": "Milk & Dairy", "description": "Cow's milk protein including casein and whey.", "category": "Major"},
        {"id": "alg-eggs", "name": "Eggs", "description": "Egg proteins present in yolk and whites.", "category": "Major"},
        {"id": "alg-wheat", "name": "Wheat & Gluten", "description": "Wheat, barley, rye and derived gluten proteins.", "category": "Major"},
        {"id": "alg-soy", "name": "Soybeans", "description": "Soy protein, edamame, and unrefined soy derivatives.", "category": "Major"},
        {"id": "alg-fish", "name": "Fish", "description": "Finned fish including salmon, cod, tuna, tilapia.", "category": "Major"},
        {"id": "alg-shellfish", "name": "Crustacean Shellfish", "description": "Prawns, shrimp, crab, lobster, crawfish.", "category": "Major"},
        {"id": "alg-sesame", "name": "Sesame", "description": "Sesame seeds, tahini, and cold-pressed sesame oil.", "category": "Major"},
    ]

    for a in allergens:
        query = """
        MERGE (alg:Allergen {id: $id})
        ON CREATE SET 
            alg.name = $name,
            alg.description = $description,
            alg.allergen_category = $category,
            alg.created_at = $now,
            alg.updated_at = $now
        ON MATCH SET
            alg.name = $name,
            alg.description = $description,
            alg.allergen_category = $category,
            alg.updated_at = $now
        """
        db.execute_write(query, {**a, "now": now})
    print(f"  ✓ Seeded {len(allergens)} Allergens")

    # 2. Restaurants (4 Fictional Dining Spots)
    restaurants = [
        {
            "id": "rest-sage-thyme",
            "name": "The Sage & Thyme Kitchen",
            "description": "Artisanal Mediterranean and farm-to-table culinary experiences with hyper-local sourcing.",
            "address": "402 Pine Street, Downtown",
            "city": "Seattle",
            "phone": "+1 (206) 555-0142",
            "email": "dining@sageandthyme.local",
            "cuisine_type": "Mediterranean Farm-to-Table",
            "status": "ACTIVE"
        },
        {
            "id": "rest-verdant-hearth",
            "name": "Verdant Hearth Bistro",
            "description": "Modern European bistro celebrating seasonal produce and hand-crafted hearth pastas.",
            "address": "128 NW 13th Avenue, Pearl District",
            "city": "Portland",
            "phone": "+1 (503) 555-0198",
            "email": "chef@verdanthearth.local",
            "cuisine_type": "Modern European",
            "status": "ACTIVE"
        },
        {
            "id": "rest-spice-harmony",
            "name": "Spice Harmony Table",
            "description": "Vibrant Pan-Asian fusion highlighting wok aromatics, clean curries, and heritage spices.",
            "address": "780 Valencia Street, Mission",
            "city": "San Francisco",
            "phone": "+1 (415) 555-0177",
            "email": "hello@spiceharmony.local",
            "cuisine_type": "Pan-Asian Fusion",
            "status": "ACTIVE"
        },
        {
            "id": "rest-bayside-harvest",
            "name": "Bayside Harvest Trattoria",
            "description": "Coastal Italian dining focusing on fresh coastal catch, house focaccia, and wood-fired mains.",
            "address": "920 Harbor Boulevard, Waterfront",
            "city": "San Diego",
            "phone": "+1 (619) 555-0163",
            "email": "reservations@baysideharvest.local",
            "cuisine_type": "Coastal Italian",
            "status": "ACTIVE"
        }
    ]

    for r in restaurants:
        query = """
        MERGE (rest:Restaurant {id: $id})
        ON CREATE SET
            rest.name = $name,
            rest.description = $description,
            rest.address = $address,
            rest.city = $city,
            rest.phone = $phone,
            rest.email = $email,
            rest.cuisine_type = $cuisine_type,
            rest.status = $status,
            rest.created_at = $now,
            rest.updated_at = $now
        ON MATCH SET
            rest.name = $name,
            rest.description = $description,
            rest.address = $address,
            rest.city = $city,
            rest.phone = $phone,
            rest.email = $email,
            rest.cuisine_type = $cuisine_type,
            rest.status = $status,
            rest.updated_at = $now
        """
        db.execute_write(query, {**r, "now": now})
    print(f"  ✓ Seeded {len(restaurants)} Restaurants")

    # 3. Ingredients (28 ingredients with allergen links and status)
    ingredients = [
        # (id, name, desc, category, status, source, [allergen_ids])
        ("ing-arborio-rice", "Arborio Rice", "Italian short-grain rice high in amylopectin starch.", "Grains", "VERIFIED", "Supplier Spec Sheet v2.1", []),
        ("ing-wild-mushrooms", "Wild Forest Mushrooms", "Foraged chanterelles and cremini mushrooms.", "Produce", "VERIFIED", "Pacific Forage Co.", []),
        ("ing-heavy-cream", "Organic Heavy Cream", "Pasteurized dairy cream with 36% milkfat.", "Dairy", "VERIFIED", "Valley Creamery Certificate", ["alg-dairy"]),
        ("ing-parmesan", "Parmigiano-Reggiano DOP", "Aged hard cheese made from cow's milk.", "Dairy", "VERIFIED", "Consorzio Parmigiano Reggiano", ["alg-dairy"]),
        ("ing-garlic", "Fresh Garlic", "Locally grown minced purple garlic cloves.", "Produce", "VERIFIED", "Organic Farm Direct", []),
        ("ing-olive-oil", "Extra Virgin Olive Oil", "Cold pressed estate olive oil.", "Oils", "VERIFIED", "Estate Bottling Lab Test", []),
        ("ing-salmon-fillet", "Wild Sockeye Salmon", "Sustainably caught Pacific salmon fillet.", "Seafood", "VERIFIED", "Marine Stewardship Council", ["alg-fish"]),
        ("ing-sesame-oil", "Toasted Sesame Oil", "Pure toasted cold-pressed sesame seed oil.", "Oils", "VERIFIED", "Manufacturer Spec Allergen Statement", ["alg-sesame"]),
        ("ing-soy-sauce", "Brewed Tamari Soy Sauce", "Traditional naturally fermented soybean sauce containing trace wheat.", "Condiments", "VERIFIED", "Brewery QA Sheet", ["alg-soy", "alg-wheat"]),
        ("ing-fresh-ginger", "Young Ginger Root", "Freshly grated ginger root.", "Produce", "VERIFIED", "Produce Wholesaler Spec", []),
        ("ing-fresh-basil", "Genovese Sweet Basil", "Fresh organic greenhouse basil leaves.", "Herbs", "VERIFIED", "Greenhouse Cert", []),
        ("ing-walnuts", "California English Walnuts", "Shelled raw halved walnuts.", "Nuts", "VERIFIED", "Nut Growers Association Spec", ["alg-tree-nuts"]),
        ("ing-pine-nuts", "Mediterranean Pine Nuts", "Harvested edible seeds of pine trees.", "Nuts", "VERIFIED", "Import Inspection", ["alg-tree-nuts"]),
        ("ing-wheat-flour", "Semolina & Wheat Flour Blend", "Enriched unbleached wheat flour.", "Baking", "VERIFIED", "Mill Certificate of Analysis", ["alg-wheat"]),
        ("ing-red-lentils", "Split Red Lentils", "Decorticated red lentils.", "Legumes", "VERIFIED", "Organic Grain Exchange", []),
        ("ing-coconut-milk", "Rich Coconut Milk", "Pressed coconut pulp extract in water.", "Dairy Alternatives", "VERIFIED", "Coconut Processing Spec", []),
        ("ing-roma-tomatoes", "San Marzano Style Tomatoes", "Sun-ripened vine tomatoes and puree.", "Produce", "VERIFIED", "Farm Collective Cert", []),
        ("ing-fior-di-latte", "Fresh Fior di Latte Mozzarella", "Fresh soft cow's milk curd cheese in brine.", "Dairy", "VERIFIED", "Artisan Dairy QA", ["alg-dairy"]),
        ("ing-peanuts", "Roasted Crushed Peanuts", "Dry-roasted Virginia cultivar peanuts.", "Legumes", "VERIFIED", "Roaster Allergen Audit", ["alg-peanuts"]),
        ("ing-firm-tofu", "Non-GMO Firm Tofu", "Pressed soybean curd in spring water.", "Soy Products", "VERIFIED", "Organic Tofu Lab Analysis", ["alg-soy"]),
        ("ing-tiger-prawns", "Wild Tiger Prawns", "Cleaned, peeled coastal marine prawns.", "Seafood", "VERIFIED", "Fishery Safety Audit", ["alg-shellfish"]),
        ("ing-almond-flour", "Blanched Almond Meal", "Finely ground blanched California almonds.", "Baking", "VERIFIED", "Nut Mill Cert", ["alg-tree-nuts"]),
        ("ing-pasture-eggs", "Pasture-Raised Eggs", "Grade A fresh whole hen eggs.", "Eggs", "VERIFIED", "Poultry Cooperative Spec", ["alg-eggs"]),
        ("ing-chia-seeds", "Organic Black Chia Seeds", "Salvia hispanica botanical seeds.", "Seeds", "VERIFIED", "Seed Importer Spec", []),
        ("ing-truffle-oil-commercial", "Commercial Truffle Oil Blend", "Olive oil blend with synthetic aroma essence.", "Oils", "UNVERIFIED", "Supplier spec pending verification", []),
        ("ing-house-seasoning", "Chef Secret Spice Seasoning Mix", "Proprietary spice blend mixed in-house.", "Spices", "IN_REVIEW", "Awaiting full allergen declaration", []),
        ("ing-honey", "Raw Wildflower Honey", "Unfiltered natural bee honey.", "Sweeteners", "VERIFIED", "Apiary Certificate", []),
        ("ing-butter", "Unsalted Cultured Butter", "High-fat European-style churned cow butter.", "Dairy", "VERIFIED", "Dairy Lab Test", ["alg-dairy"])
    ]

    for ing_id, name, desc, category, v_status, source, alg_ids in ingredients:
        last_v = now if v_status == "VERIFIED" else None
        query = """
        MERGE (i:Ingredient {id: $id})
        ON CREATE SET
            i.name = $name,
            i.description = $desc,
            i.category = $category,
            i.verification_status = $status,
            i.source_reference = $source,
            i.last_verified_at = $last_v,
            i.created_at = $now,
            i.updated_at = $now
        ON MATCH SET
            i.name = $name,
            i.description = $desc,
            i.category = $category,
            i.verification_status = $status,
            i.source_reference = $source,
            i.last_verified_at = $last_v,
            i.updated_at = $now
        WITH i
        // Clear and link allergens
        OPTIONAL MATCH (i)-[rel:CONTAINS_ALLERGEN]->(:Allergen)
        DELETE rel
        WITH i
        UNWIND (CASE WHEN size($alg_ids) > 0 THEN $alg_ids ELSE [] END) as a_id
        MATCH (alg:Allergen {id: a_id})
        MERGE (i)-[:CONTAINS_ALLERGEN]->(alg)
        """
        db.execute_write(query, {
            "id": ing_id,
            "name": name,
            "desc": desc,
            "category": category,
            "status": v_status,
            "source": source,
            "last_v": last_v,
            "now": now,
            "alg_ids": alg_ids
        })
    print(f"  ✓ Seeded {len(ingredients)} Ingredients with Allergen Links & Verification Metadata")

    # 4. Dishes (16 Dishes across 4 restaurants with ingredients and precautionary links)
    dishes = [
        {
            "id": "dish-risotto",
            "name": "Creamy Wild Mushroom Risotto",
            "description": "Slow-simmered carnaroli rice with wild forest mushrooms, finished with parmigiano-reggiano and cultured butter.",
            "category": "Main Course",
            "price": 24.50,
            "vegetarian": True,
            "vegan": False,
            "preparation_notes": "Stirred continuously in copper pans. Prepared on a line adjacent to nut-crusted poultry.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-sage-thyme", "rest-verdant-hearth"],
            "ingredient_ids": ["ing-arborio-rice", "ing-wild-mushrooms", "ing-heavy-cream", "ing-parmesan", "ing-garlic", "ing-butter"],
            "may_contain_allergen_ids": ["alg-tree-nuts"]  # Precautionary cross-contact
        },
        {
            "id": "dish-salmon-teriyaki",
            "name": "Sesame Ginger Glazed Salmon",
            "description": "Pan-seared wild sockeye salmon coated with reduction of ginger, tamari soy, and toasted sesame aromatics.",
            "category": "Main Course",
            "price": 28.00,
            "vegetarian": False,
            "vegan": False,
            "preparation_notes": "Flashed on cast iron skillet with toasted sesame oil.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-spice-harmony"],
            "ingredient_ids": ["ing-salmon-fillet", "ing-sesame-oil", "ing-soy-sauce", "ing-fresh-ginger", "ing-garlic"],
            "may_contain_allergen_ids": []
        },
        {
            "id": "dish-pesto-pasta",
            "name": "Walnut & Basil Pesto Pappardelle",
            "description": "House ribbon pasta tossed with fresh crushed Genovese basil, toasted English walnuts, and aged parmesan.",
            "category": "Main Course",
            "price": 22.00,
            "vegetarian": True,
            "vegan": False,
            "preparation_notes": "Contains crushed tree nuts in mortar. Pesto made fresh daily.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-verdant-hearth", "rest-bayside-harvest"],
            "ingredient_ids": ["ing-wheat-flour", "ing-fresh-basil", "ing-walnuts", "ing-parmesan", "ing-garlic", "ing-olive-oil"],
            "may_contain_allergen_ids": ["alg-pine-nuts"]
        },
        {
            "id": "dish-lentil-dal",
            "name": "Spiced Red Lentil Dal with Coconut",
            "description": "Slow-simmered organic red lentils infused with young ginger, turmeric, cumin, and velvety coconut cream.",
            "category": "Main Course",
            "price": 18.50,
            "vegetarian": True,
            "vegan": True,
            "preparation_notes": "100% plant-based recipe prepared in dedicated vegan cookware.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-spice-harmony", "rest-sage-thyme"],
            "ingredient_ids": ["ing-red-lentils", "ing-coconut-milk", "ing-fresh-ginger", "ing-garlic", "ing-olive-oil"],
            "may_contain_allergen_ids": []
        },
        {
            "id": "dish-margherita-pizza",
            "name": "Classic Margherita Pizza with Fior di Latte",
            "description": "48-hour fermented wheat dough topped with San Marzano tomatoes, torn fior di latte mozzarella, and fresh basil.",
            "category": "Pizza & Flatbreads",
            "price": 19.00,
            "vegetarian": True,
            "vegan": False,
            "preparation_notes": "Baked in 800-degree wood-fired hearth oven.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-bayside-harvest"],
            "ingredient_ids": ["ing-wheat-flour", "ing-roma-tomatoes", "ing-fior-di-latte", "ing-fresh-basil", "ing-olive-oil"],
            "may_contain_allergen_ids": []
        },
        {
            "id": "dish-peanut-salad",
            "name": "Thai Peanut Crunch Salad",
            "description": "Shredded crisp vegetables tossed with toasted crushed peanuts and spicy ginger sesame dressing.",
            "category": "Salads",
            "price": 16.00,
            "vegetarian": True,
            "vegan": True,
            "preparation_notes": "High concentration of crushed peanuts. Dressing prepared with tamari soy.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-spice-harmony"],
            "ingredient_ids": ["ing-peanuts", "ing-sesame-oil", "ing-fresh-ginger", "ing-soy-sauce", "ing-garlic"],
            "may_contain_allergen_ids": []
        },
        {
            "id": "dish-tofu-bowl",
            "name": "Golden Turmeric Tofu Bowl",
            "description": "Pan-crisped non-GMO firm tofu glazed with tamari reduction, served with coconut ginger rice.",
            "category": "Bowls",
            "price": 19.50,
            "vegetarian": True,
            "vegan": True,
            "preparation_notes": "Cooked on a dedicated wok.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-spice-harmony"],
            "ingredient_ids": ["ing-firm-tofu", "ing-soy-sauce", "ing-coconut-milk", "ing-arborio-rice", "ing-fresh-ginger"],
            "may_contain_allergen_ids": ["alg-peanuts"]
        },
        {
            "id": "dish-tiger-prawns",
            "name": "Crispy Tempura Tiger Prawns",
            "description": "Flash-fried jumbo tiger prawns coated in light semolina tempura batter with ginger dipping dip.",
            "category": "Appetizers",
            "price": 17.50,
            "vegetarian": False,
            "vegan": False,
            "preparation_notes": "Deep fried in common fryer also used for vegetable tempura.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-spice-harmony", "rest-bayside-harvest"],
            "ingredient_ids": ["ing-tiger-prawns", "ing-wheat-flour", "ing-pasture-eggs", "ing-soy-sauce", "ing-fresh-ginger"],
            "may_contain_allergen_ids": ["alg-sesame"]
        },
        {
            "id": "dish-almond-torte",
            "name": "Decadent Dark Chocolate Almond Torte",
            "description": "Flourless European chocolate cake made with finely ground almond flour, pasture eggs, and cultured butter.",
            "category": "Desserts",
            "price": 12.00,
            "vegetarian": True,
            "vegan": False,
            "preparation_notes": "Contains dense almond tree nut flour and egg whites.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-verdant-hearth", "rest-sage-thyme"],
            "ingredient_ids": ["ing-almond-flour", "ing-pasture-eggs", "ing-butter", "ing-heavy-cream"],
            "may_contain_allergen_ids": ["alg-peanuts"]
        },
        {
            "id": "dish-garlic-focaccia",
            "name": "Rosemary Garlic Hearth Focaccia",
            "description": "Warm, dimpled sea-salt focaccia drizzled with cold-pressed olive oil, fresh rosemary, and roasted garlic.",
            "category": "Breads",
            "price": 9.50,
            "vegetarian": True,
            "vegan": True,
            "preparation_notes": "Baked in stone oven where sesame seed loaves are also fired.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-bayside-harvest", "rest-verdant-hearth"],
            "ingredient_ids": ["ing-wheat-flour", "ing-olive-oil", "ing-garlic"],
            "may_contain_allergen_ids": ["alg-sesame"]
        },
        {
            "id": "dish-chia-pudding",
            "name": "Coconut Mango Chia Seed Parfait",
            "description": "Chilled organic chia seeds bloomed in rich coconut milk, layered with fresh mango puree and wildflower honey.",
            "category": "Desserts",
            "price": 10.50,
            "vegetarian": True,
            "vegan": False,
            "preparation_notes": "Dairy-free, gluten-free recipe sweetened with raw honey.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-sage-thyme"],
            "ingredient_ids": ["ing-chia-seeds", "ing-coconut-milk", "ing-honey"],
            "may_contain_allergen_ids": []
        },
        {
            "id": "dish-truffle-polenta-fries",
            "name": "Truffle Parmesan Polenta Fries",
            "description": "Crispy golden polenta batons tossed with commercial truffle oil blend, shaved parmesan, and garlic aioli.",
            "category": "Appetizers",
            "price": 14.00,
            "vegetarian": True,
            "vegan": False,
            "preparation_notes": "Uses commercial truffle oil awaiting supplier verification.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "PARTIAL",
            "restaurant_ids": ["rest-verdant-hearth"],
            "ingredient_ids": ["ing-parmesan", "ing-truffle-oil-commercial", "ing-garlic", "ing-butter"],
            "may_contain_allergen_ids": []
        },
        {
            "id": "dish-chef-soup",
            "name": "Chef's Special Farmhouse Kettle Soup",
            "description": "Daily rotating seasonal kettle soup prepared using market vegetables and house seasoning.",
            "category": "Soups",
            "price": 11.00,
            "vegetarian": False,
            "vegan": False,
            "preparation_notes": "Ingredients change daily based on farm delivery. Full ingredient audit incomplete.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "INCOMPLETE",
            "restaurant_ids": ["rest-sage-thyme"],
            "ingredient_ids": ["ing-house-seasoning"],
            "may_contain_allergen_ids": ["alg-wheat", "alg-dairy"]
        },
        {
            "id": "dish-seafood-paella",
            "name": "Traditional Coastal Paella",
            "description": "Saffron-scented arborio rice with tiger prawns, wild sockeye salmon, tomatoes, and garlic.",
            "category": "Main Course",
            "price": 32.00,
            "vegetarian": False,
            "vegan": False,
            "preparation_notes": "Cooked in traditional wide carbon-steel paella pan.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-bayside-harvest"],
            "ingredient_ids": ["ing-arborio-rice", "ing-tiger-prawns", "ing-salmon-fillet", "ing-roma-tomatoes", "ing-garlic", "ing-olive-oil"],
            "may_contain_allergen_ids": []
        },
        {
            "id": "dish-mezze-platter",
            "name": "Mediterranean Mezze Platter",
            "description": "Artisan spread of marinated wild mushrooms, warm focaccia slices, kalamata olives, and fresh basil.",
            "category": "Appetizers",
            "price": 18.00,
            "vegetarian": True,
            "vegan": True,
            "preparation_notes": "Served family-style with shared serving utensils.",
            "availability_status": "AVAILABLE",
            "ingredient_data_status": "COMPLETE",
            "restaurant_ids": ["rest-sage-thyme", "rest-bayside-harvest"],
            "ingredient_ids": ["ing-wild-mushrooms", "ing-wheat-flour", "ing-olive-oil", "ing-garlic", "ing-fresh-basil"],
            "may_contain_allergen_ids": ["alg-sesame"]
        },
        {
            "id": "dish-unlisted-special",
            "name": "Market Catch Mystery Stew",
            "description": "Unlisted test stew with preliminary recipe card.",
            "category": "Soups",
            "price": 15.00,
            "vegetarian": False,
            "vegan": False,
            "preparation_notes": "Recipe in testing phase. Ingredients not yet linked to database.",
            "availability_status": "UNAVAILABLE",
            "ingredient_data_status": "INCOMPLETE",
            "restaurant_ids": ["rest-bayside-harvest"],
            "ingredient_ids": [],
            "may_contain_allergen_ids": []
        }
    ]

    for d in dishes:
        query = """
        MERGE (dish:Dish {id: $id})
        ON CREATE SET
            dish.name = $name,
            dish.description = $description,
            dish.category = $category,
            dish.price = $price,
            dish.vegetarian = $vegetarian,
            dish.vegan = $vegan,
            dish.preparation_notes = $preparation_notes,
            dish.availability_status = $availability_status,
            dish.ingredient_data_status = $ingredient_data_status,
            dish.created_at = $now,
            dish.updated_at = $now
        ON MATCH SET
            dish.name = $name,
            dish.description = $description,
            dish.category = $category,
            dish.price = $price,
            dish.vegetarian = $vegetarian,
            dish.vegan = $vegan,
            dish.preparation_notes = $preparation_notes,
            dish.availability_status = $availability_status,
            dish.ingredient_data_status = $ingredient_data_status,
            dish.updated_at = $now
        WITH dish
        // Clear old relations to maintain idempotency
        OPTIONAL MATCH (r_old:Restaurant)-[r_rel:OFFERS]->(dish)
        DELETE r_rel
        WITH dish
        OPTIONAL MATCH (dish)-[c_rel:CONTAINS]->(i_old:Ingredient)
        DELETE c_rel
        WITH dish
        OPTIONAL MATCH (dish)-[mc_rel:MAY_CONTAIN]->(a_old:Allergen)
        DELETE mc_rel
        WITH dish
        UNWIND (CASE WHEN size($restaurant_ids) > 0 THEN $restaurant_ids ELSE [] END) as r_id
        MATCH (r:Restaurant {id: r_id})
        MERGE (r)-[:OFFERS]->(dish)
        WITH dish
        UNWIND (CASE WHEN size($ingredient_ids) > 0 THEN $ingredient_ids ELSE [] END) as i_id
        MATCH (i:Ingredient {id: i_id})
        MERGE (dish)-[:CONTAINS]->(i)
        WITH dish
        UNWIND (CASE WHEN size($may_contain_allergen_ids) > 0 THEN $may_contain_allergen_ids ELSE [] END) as mc_id
        MATCH (mc:Allergen {id: mc_id})
        MERGE (dish)-[:MAY_CONTAIN]->(mc)
        """
        db.execute_write(query, {
            "id": d["id"],
            "name": d["name"],
            "description": d["description"],
            "category": d["category"],
            "price": d["price"],
            "vegetarian": d["vegetarian"],
            "vegan": d["vegan"],
            "preparation_notes": d["preparation_notes"],
            "availability_status": d["availability_status"],
            "ingredient_data_status": d["ingredient_data_status"],
            "now": now,
            "restaurant_ids": d["restaurant_ids"],
            "ingredient_ids": d["ingredient_ids"],
            "may_contain_allergen_ids": d["may_contain_allergen_ids"]
        })
    print(f"  ✓ Seeded {len(dishes)} Dishes with Restaurant & Ingredient Links")

    # 5. Seed non-admin demo roles for quick evaluation (EDITOR and VIEWER)
    # Note: As required, we do NOT seed a default public administrator account here.
    demo_users = [
        {
            "id": "user-demo-editor",
            "full_name": "Elena Rostova (Lead Editor)",
            "email": "editor@allergraph.local",
            "password_hash": hash_password("AllerGraph2026!"),
            "role": "EDITOR",
            "is_active": True
        },
        {
            "id": "user-demo-viewer",
            "full_name": "Marcus Vance (Community Viewer)",
            "email": "viewer@allergraph.local",
            "password_hash": hash_password("AllerGraph2026!"),
            "role": "VIEWER",
            "is_active": True
        }
    ]

    for u in demo_users:
        query = """
        MERGE (usr:User {id: $id})
        ON CREATE SET
            usr.full_name = $full_name,
            usr.email = toLower($email),
            usr.password_hash = $password_hash,
            usr.role = $role,
            usr.is_active = $is_active,
            usr.created_at = $now,
            usr.updated_at = $now
        ON MATCH SET
            usr.full_name = $full_name,
            usr.password_hash = $password_hash,
            usr.role = $role,
            usr.is_active = $is_active,
            usr.updated_at = $now
        """
        db.execute_write(query, {**u, "now": now})
    print("  ✓ Seeded Demo Accounts: editor@allergraph.local and viewer@allergraph.local (Pass: AllerGraph2026!)")

    print("\n" + "=" * 60)
    print("AllerGraph: Seeding Completed Successfully!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        seed_demo_data()
    except Exception as e:
        print(f"[ERROR] Seeding failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()
