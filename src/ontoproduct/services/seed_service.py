from ontoproduct.schemas.product import NormalizedProduct


def seed_products(repository):
    results = []
    for name, voltage, power, speed in [("DM-500A", 24, 500, 3000), ("DM-510", 24, 510, 3200), ("MX-500", 48, 500, 2800)]:
        product = NormalizedProduct(product_name=name, product_class="BLDCMotor", attributes={
            "manufacturer": {"value": "ABC Motors", "provenance": "RULE"},
            "rated_voltage": {"value": voltage, "unit": "V", "provenance": "RULE"},
            "rated_power": {"value": power, "unit": "W", "provenance": "RULE"},
            "rated_speed": {"value": speed, "unit": "rpm", "provenance": "RULE"},
        }).model_dump(mode="json")
        results.append(repository.save(f"seed:{name}", product, origin="SEED"))
    return results
