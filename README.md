# Setup Instructions

1. Create MySQL database: Open MySQL Workbench (or use CLI) and then Create a database named: ecommerce_api

2. Create & activate Python virtual env:

   bash:

   python3 -m venv venv

   source venv/bin/activate            # mac/linux

   or

   venv\Scripts\activate                # windows

3. Install dependencies:

   bash:

   pip install Flask Flask-SQLAlchemy Flask-Marshmallow marshmallow-sqlalchemy mysql-connector-python

4. Edit app.py and replace <YOUR_PASSWORD> with your MySQL password or set environment variables:

   bash: 

   export ECO_DB_PASS="mypassword"
   export ECO_DB_USER="root"
   export ECO_DB_NAME="ecommerce_api"

 5. Run:
    
    bash:

    python app.py

    The app listens on http://0.0.0.0:5000

  6. Verify tables are created using MySQL Workbench: users, orders, products, order_product.
    
