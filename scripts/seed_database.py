from ontoproduct.repositories.database import Database
from ontoproduct.repositories.product_repository import ProductRepository
from ontoproduct.services.application_paths import ApplicationPaths
from ontoproduct.services.seed_service import seed_products


def main():
    paths = ApplicationPaths.from_environment()
    products = ProductRepository(Database(paths.product_db))
    for result in seed_products(products):
        print(result["status"], result["record"]["product"]["product_name"])
    print(f"Products: {products.count()} | Database: {paths.product_db}")


if __name__ == "__main__":
    main()
